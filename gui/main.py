#!/usr/bin/env python3
"""
Universal Media Downloader (Windows GUI)
- Combines YouTube, Spotify, Instagram, and SoundCloud downloaders into one beautiful GUI
- Single .exe packaging target (Windows 10/11) with PyInstaller
- Shared cookies between YouTube and Spotify (uses youtube/cookies.txt by default)
- Settings screen to configure download directory, audio/video defaults, and custom cookies path

Notes:
- Spotify API credentials are auto-loaded from /app/spotify/.env, with optional override in Settings
- Long-running downloads are executed in background threads to keep UI responsive
- Console output from underlying modules is redirected into the GUI log panes
"""

import os
import sys
import json
import traceback
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

# -------------------------
# Utilities & Settings
# -------------------------
APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COOKIES = APP_ROOT / "youtube" / "cookies.txt"
SPOTIFY_ENV = APP_ROOT / "spotify" / ".env"
CONFIG_PATH = APP_ROOT / "app_settings.json"


def load_spotify_env_into_process():
    try:
        if SPOTIFY_ENV.exists():
            for line in SPOTIFY_ENV.read_text(encoding="utf-8").splitlines():
                if line.strip() and not line.strip().startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    os.environ[k] = v
    except Exception:
        pass


class AppSettings:
    def __init__(self):
        self.data = {
            "download_dir": str((APP_ROOT / "downloads").resolve()),
            "youtube_quality": "1080p",
            "youtube_format": "mp4",
            "youtube_audio_only": False,
            "cookies_path": str(DEFAULT_COOKIES),
            "spotify_client_id": "",
            "spotify_client_secret": "",
        }
        self.load()

    def load(self):
        if CONFIG_PATH.exists():
            try:
                self.data.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
            except Exception:
                pass
        # Fallback to spotify .env if not present in config
        if not self.data.get("spotify_client_id") or not self.data.get("spotify_client_secret"):
            load_spotify_env_into_process()
            self.data["spotify_client_id"] = os.environ.get("SPOTIFY_CLIENT_ID", self.data.get("spotify_client_id", ""))
            self.data["spotify_client_secret"] = os.environ.get("SPOTIFY_CLIENT_SECRET", self.data.get("spotify_client_secret", ""))

    def save(self):
        try:
            CONFIG_PATH.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except Exception:
            pass

    @property
    def download_dir(self):
        return Path(self.data["download_dir"]).expanduser().resolve()

    @property
    def cookies_path(self) -> Path:
        return Path(self.data["cookies_path"]).expanduser().resolve()


# -------------------------
# Import helpers
# -------------------------
import importlib.util


def load_module(name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module {name} from {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# -------------------------
# Logging redirection to GUI
# -------------------------
class GuiLogStream(QtCore.QObject):
    text_emitted = QtCore.Signal(str)

    def write(self, text):
        if text:
            self.text_emitted.emit(str(text))

    def flush(self):
        pass


class WorkerSignals(QtCore.QObject):
    message = QtCore.Signal(str)
    finished = QtCore.Signal(bool, str)


class DownloadWorker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @QtCore.Slot()
    def run(self):
        # Redirect stdout/stderr into GUI
        old_out, old_err = sys.stdout, sys.stderr
        redirect = GuiLogStream()
        redirect.text_emitted.connect(lambda s: self.signals.message.emit(s))
        sys.stdout = redirect
        sys.stderr = redirect
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(True, "Done")
        except Exception as e:
            tb = traceback.format_exc()
            self.signals.message.emit(f"\nERROR: {e}\n{tb}\n")
            self.signals.finished.emit(False, str(e))
        finally:
            sys.stdout = old_out
            sys.stderr = old_err


# -------------------------
# Core download functions used by GUI
# -------------------------

def ensure_ffmpeg_note():
    print("Note: FFmpeg is recommended for audio extraction and metadata embedding.")


def download_youtube(url: str, out_dir: Path, quality: str, fmt: str, audio_only: bool, cookies: Optional[Path]):
    ensure_ffmpeg_note()
    import yt_dlp

    out_dir.mkdir(parents=True, exist_ok=True)
    # Probe info first
    ydl_probe_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    if cookies and cookies.exists():
        ydl_probe_opts['cookiefile'] = str(cookies)

    with yt_dlp.YoutubeDL(ydl_probe_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        is_playlist = isinstance(info, dict) and 'entries' in info

    if audio_only:
        post = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3' if fmt not in ['mp3', 'm4a', 'flac', 'wav'] else fmt,
            'preferredquality': '192',
        }]
        fmt_selector = 'bestaudio/best'
        outtmpl = str(out_dir / '%(title)s.%(ext)s')
    else:
        post = []
        outtmpl = str(out_dir / ('%(playlist_index)02d - %(title)s.%(ext)s' if is_playlist else '%(title)s.%(ext)s'))
        if quality == 'best':
            if fmt == 'mp4':
                fmt_selector = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif fmt == 'webm':
                fmt_selector = 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best'
            else:
                fmt_selector = 'bestvideo+bestaudio/best'
        elif quality == 'worst':
            fmt_selector = 'worst[ext=mp4]/worst'
        elif quality.endswith('p'):
            height = quality[:-1]
            if fmt == 'mp4':
                fmt_selector = (
                    f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/'
                    f'best[height<={height}][ext=mp4]/best[height<={height}]/best'
                )
            elif fmt == 'webm':
                fmt_selector = (
                    f'bestvideo[height<={height}][ext=webm]+bestaudio[ext=webm]/'
                    f'best[height<={height}][ext=webm]/best[height<={height}]/best'
                )
            else:
                fmt_selector = (
                    f'bestvideo[height<={height}]+bestaudio/'
                    f'best[height<={height}]/best'
                )
        else:
            fmt_selector = 'best'

    ydl_opts = {
        'outtmpl': outtmpl,
        'format': fmt_selector,
        'retries': 3,
        'noplaylist': False,
        'progress_with_newline': True,
        'postprocessors': post,
        'concurrent_fragment_downloads': 4,
        'http_chunk_size': 10485760,
        'quiet': False,
        'no_warnings': False,
    }
    if cookies and cookies.exists():
        print(f"Using cookies: {cookies}")
        ydl_opts['cookiefile'] = str(cookies)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_spotify(url: str, out_dir: Path, cookies: Optional[Path]):
    # Load spotify_downloader module and run proper function
    sp_mod = load_module('spotify_downloader_gui', APP_ROOT / 'spotify' / 'spotify_downloader.py')
    downloader = sp_mod.SpotifyDownloader()

    # Override output dir and cookies
    downloader.download_dir = out_dir
    downloader.setup_ytdlp_options()
    if cookies and cookies.exists():
        downloader.cookie_file = cookies

    url_type, item_id = downloader.validate_spotify_url(url)
    if url_type == 'track':
        return downloader.download_track(item_id)
    elif url_type == 'playlist':
        return downloader.download_playlist(item_id)
    else:
        raise ValueError('Only track and playlist URLs are supported in GUI for now.')


def download_instagram(url: str, out_dir: Path, audio_only: bool):
    ig_mod = load_module('instagram_downloader_gui', APP_ROOT / 'instagram' / 'instagram_downloader.py')
    app = ig_mod.InstagramDownloader()
    app.settings['download_directory'] = str(out_dir)
    if audio_only:
        return app.download_audio(url)
    else:
        return app.download_video(url)


def download_soundcloud(url: str, out_dir: Path):
    sc_mod = load_module('soundcloud_downloader_gui', APP_ROOT / 'soundcloud' / 'soundcloud_downloader.py')
    app = sc_mod.SoundCloudDownloader()
    app.settings['download_dir'] = str(out_dir)
    return app.download_music(url)


# -------------------------
# GUI Tabs
# -------------------------
class BaseTab(QtWidgets.QWidget):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.thread_pool = QtCore.QThreadPool.globalInstance()
        self._build_ui()

    def _build_ui(self):
        self.v = QtWidgets.QVBoxLayout(self)
        self.form = QtWidgets.QFormLayout()
        self.v.addLayout(self.form)

        self.url = QtWidgets.QLineEdit()
        self.form.addRow("URL", self.url)

        self.dir_row = QtWidgets.QHBoxLayout()
        self.dir_edit = QtWidgets.QLineEdit(str(self.settings.download_dir))
        self.btn_browse = QtWidgets.QPushButton("Browse…")
        self.btn_browse.clicked.connect(self.pick_dir)
        self.dir_row.addWidget(self.dir_edit)
        self.dir_row.addWidget(self.btn_browse)
        self.form.addRow("Save to", self.dir_row)

        self.btn_download = QtWidgets.QPushButton("Download")
        self.btn_download.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_download.clicked.connect(self.on_download_clicked)
        self.v.addWidget(self.btn_download)

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(220)
        self.v.addWidget(self.log)

        self.v.addStretch(1)

    def append_log(self, text: str):
        self.log.moveCursor(QtGui.QTextCursor.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QtGui.QTextCursor.End)

    def pick_dir(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose download folder", self.dir_edit.text())
        if d:
            self.dir_edit.setText(d)

    def set_busy(self, busy: bool):
        self.btn_download.setEnabled(not busy)
        self.setCursor(QtCore.Qt.BusyCursor if busy else QtCore.Qt.ArrowCursor)

    # To be implemented in subclasses
    def on_download_clicked(self):
        pass


class YouTubeTab(BaseTab):
    def _build_ui(self):
        super()._build_ui()
        row = QtWidgets.QHBoxLayout()
        self.quality = QtWidgets.QComboBox()
        self.quality.addItems(["1080p", "720p", "480p", "360p", "best", "worst"])
        self.quality.setCurrentText(self.settings.data.get("youtube_quality", "1080p"))
        self.format = QtWidgets.QComboBox()
        self.format.addItems(["mp4", "webm"])
        self.format.setCurrentText(self.settings.data.get("youtube_format", "mp4"))
        self.audio_only = QtWidgets.QCheckBox("Audio only")
        self.audio_only.setChecked(self.settings.data.get("youtube_audio_only", False))
        row.addWidget(QtWidgets.QLabel("Quality"))
        row.addWidget(self.quality)
        row.addWidget(QtWidgets.QLabel("Format"))
        row.addWidget(self.format)
        row.addWidget(self.audio_only)
        self.v.insertLayout(1, row)

    def on_download_clicked(self):
        url = self.url.text().strip()
        if not url:
            QtWidgets.QMessageBox.warning(self, "Missing URL", "Please paste a YouTube URL.")
            return
        out_dir = Path(self.dir_edit.text()).expanduser()
        qual = self.quality.currentText()
        fmt = self.format.currentText()
        audio = self.audio_only.isChecked()
        cookies = self.settings.cookies_path if self.settings.cookies_path.exists() else None

        worker = DownloadWorker(download_youtube, url, out_dir, qual, fmt, audio, cookies)
        worker.signals.message.connect(self.append_log)
        worker.signals.finished.connect(lambda ok, msg: self.set_busy(False))
        self.set_busy(True)
        self.thread_pool.start(worker)


class SpotifyTab(BaseTab):
    def on_download_clicked(self):
        url = self.url.text().strip()
        if not url:
            QtWidgets.QMessageBox.warning(self, "Missing URL", "Please paste a Spotify track or playlist URL.")
            return
        out_dir = Path(self.dir_edit.text()).expanduser()
        cookies = self.settings.cookies_path if self.settings.cookies_path.exists() else None

        worker = DownloadWorker(download_spotify, url, out_dir, cookies)
        worker.signals.message.connect(self.append_log)
        worker.signals.finished.connect(lambda ok, msg: self.set_busy(False))
        self.set_busy(True)
        self.thread_pool.start(worker)


class InstagramTab(BaseTab):
    def _build_ui(self):
        super()._build_ui()
        row = QtWidgets.QHBoxLayout()
        self.audio_only = QtWidgets.QCheckBox("Audio only")
        row.addWidget(self.audio_only)
        self.v.insertLayout(1, row)

    def on_download_clicked(self):
        url = self.url.text().strip()
        if not url:
            QtWidgets.QMessageBox.warning(self, "Missing URL", "Please paste an Instagram URL.")
            return
        out_dir = Path(self.dir_edit.text()).expanduser()
        worker = DownloadWorker(download_instagram, url, out_dir, self.audio_only.isChecked())
        worker.signals.message.connect(self.append_log)
        worker.signals.finished.connect(lambda ok, msg: self.set_busy(False))
        self.set_busy(True)
        self.thread_pool.start(worker)


class SoundCloudTab(BaseTab):
    def on_download_clicked(self):
        url = self.url.text().strip()
        if not url:
            QtWidgets.QMessageBox.warning(self, "Missing URL", "Please paste a SoundCloud URL.")
            return
        out_dir = Path(self.dir_edit.text()).expanduser()
        worker = DownloadWorker(download_soundcloud, url, out_dir)
        worker.signals.message.connect(self.append_log)
        worker.signals.finished.connect(lambda ok, msg: self.set_busy(False))
        self.set_busy(True)
        self.thread_pool.start(worker)


class SettingsTab(QtWidgets.QWidget):
    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._build_ui()

    def _build_ui(self):
        v = QtWidgets.QVBoxLayout(self)

        # Download directory
        dir_row = QtWidgets.QHBoxLayout()
        self.dir_edit = QtWidgets.QLineEdit(self.settings.data.get("download_dir", str(self.settings.download_dir)))
        btn_dir = QtWidgets.QPushButton("Browse…")
        btn_dir.clicked.connect(self.pick_dir)
        dir_row.addWidget(self.dir_edit)
        dir_row.addWidget(btn_dir)
        v.addWidget(QtWidgets.QLabel("Default download directory"))
        v.addLayout(dir_row)

        # Cookies selector
        cookie_row = QtWidgets.QHBoxLayout()
        self.cookie_edit = QtWidgets.QLineEdit(self.settings.data.get("cookies_path", str(DEFAULT_COOKIES)))
        btn_cookie = QtWidgets.QPushButton("Choose cookies.txt…")
        btn_cookie.clicked.connect(self.pick_cookie)
        cookie_row.addWidget(self.cookie_edit)
        cookie_row.addWidget(btn_cookie)
        v.addWidget(QtWidgets.QLabel("Cookies file (also used by Spotify searches/downloads)"))
        v.addLayout(cookie_row)

        # Spotify creds
        grid = QtWidgets.QFormLayout()
        self.sp_id = QtWidgets.QLineEdit(self.settings.data.get("spotify_client_id", ""))
        self.sp_secret = QtWidgets.QLineEdit(self.settings.data.get("spotify_client_secret", ""))
        self.sp_secret.setEchoMode(QtWidgets.QLineEdit.Password)
        grid.addRow("Spotify Client ID", self.sp_id)
        grid.addRow("Spotify Client Secret", self.sp_secret)
        v.addLayout(grid)

        # Buttons
        buttons = QtWidgets.QHBoxLayout()
        self.btn_save = QtWidgets.QPushButton("Save Settings")
        self.btn_save.clicked.connect(self.save_settings)
        self.btn_sync = QtWidgets.QPushButton("Copy cookies to youtube/cookies.txt")
        self.btn_sync.clicked.connect(self.copy_cookies_to_youtube)
        buttons.addWidget(self.btn_save)
        buttons.addWidget(self.btn_sync)
        buttons.addStretch(1)
        v.addLayout(buttons)

        v.addStretch(1)

    def pick_dir(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose default download folder", self.dir_edit.text())
        if d:
            self.dir_edit.setText(d)

    def pick_cookie(self):
        f, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Choose cookies.txt", str(Path(self.cookie_edit.text()).parent), "Cookies (*.txt);;All files (*.*)")
        if f:
            self.cookie_edit.setText(f)

    def save_settings(self):
        self.settings.data["download_dir"] = self.dir_edit.text().strip()
        self.settings.data["cookies_path"] = self.cookie_edit.text().strip()
        self.settings.data["spotify_client_id"] = self.sp_id.text().strip()
        self.settings.data["spotify_client_secret"] = self.sp_secret.text().strip()
        self.settings.save()
        # Also update spotify/.env to persist for spotify_downloader
        try:
            SPOTIFY_ENV.write_text(
                f"SPOTIFY_CLIENT_ID={self.settings.data['spotify_client_id']}\nSPOTIFY_CLIENT_SECRET={self.settings.data['spotify_client_secret']}\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        QtWidgets.QMessageBox.information(self, "Saved", "Settings saved successfully.")

    def copy_cookies_to_youtube(self):
        src = Path(self.cookie_edit.text().strip()).expanduser()
        dst = DEFAULT_COOKIES
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not src.exists():
                QtWidgets.QMessageBox.warning(self, "Missing file", "Selected cookies file does not exist.")
                return
            dst.write_bytes(src.read_bytes())
            QtWidgets.QMessageBox.information(self, "Copied", f"Cookies copied to {dst}")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to copy cookies: {e}")


# -------------------------
# Main Window
# -------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal Media Downloader")
        self.setWindowIcon(QtGui.QIcon.fromTheme("download"))
        self.resize(1100, 700)

        self.settings = AppSettings()

        tabs = QtWidgets.QTabWidget()
        tabs.addTab(YouTubeTab(self.settings), "YouTube")
        tabs.addTab(SpotifyTab(self.settings), "Spotify")
        tabs.addTab(InstagramTab(self.settings), "Instagram")
        tabs.addTab(SoundCloudTab(self.settings), "SoundCloud")
        tabs.addTab(SettingsTab(self.settings), "Settings")
        self.setCentralWidget(tabs)

        self.apply_style()

    def apply_style(self):
        # Minimal modern QSS
        self.setStyleSheet("""
            QWidget { font-size: 13px; }
            QLineEdit, QTextEdit, QComboBox { padding: 6px 8px; }
            QPushButton { padding: 8px 14px; border-radius: 6px; background: #2563eb; color: white; }
            QPushButton:disabled { background: #93c5fd; }
            QTabWidget::pane { border: 1px solid #e5e7eb; }
            QTabBar::tab { padding: 8px 12px; }
            QLabel { color: #111827; }
        """)


def main():
    load_spotify_env_into_process()
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()