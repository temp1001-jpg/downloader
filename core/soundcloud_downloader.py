"""
SoundCloud Downloader Core - GUI-compatible
Refactored from CLI version for GUI integration
"""

import re
from pathlib import Path
from typing import Optional, Callable, Dict, Any

try:
    import yt_dlp
except ImportError:
    raise ImportError("yt-dlp is required. Install with: pip install yt-dlp")


class SoundCloudDownloader:
    """SoundCloud downloader with GUI callback support"""

    def __init__(self, output_dir: str = "downloads", cookies=None,
                 audio_format: str = "mp3", audio_quality: str = "best"):
        """
        Initialize SoundCloud downloader

        Args:
            output_dir: Directory to save downloads
            cookies: Cookie file path from cookie_manager
            audio_format: Audio format (mp3, m4a, wav)
            audio_quality: Audio quality (best, 192 kbps, 128 kbps)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.cookies_file = cookies
        self.audio_format = audio_format
        self.audio_quality = audio_quality

    def validate_url(self, url: str) -> bool:
        """
        Validate SoundCloud URL

        Returns:
            True if valid SoundCloud URL, False otherwise
        """
        soundcloud_patterns = [
            r'https?://soundcloud\.com/.+',
            r'https?://m\.soundcloud\.com/.+',
            r'https?://www\.soundcloud\.com/.+'
        ]
        return any(re.match(pattern, url.strip()) for pattern in soundcloud_patterns)

    def get_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get track/playlist information without downloading

        Returns:
            Info dict or None if failed
        """
        if not self.validate_url(url):
            return None

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'lazy_playlist': True,
            'socket_timeout': 15,
        }

        if self.cookies_file and Path(self.cookies_file).exists():
            ydl_opts['cookiefile'] = str(Path(self.cookies_file).absolute())

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception:
            return None

    def download(self, url: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Download track or playlist from SoundCloud

        Args:
            url: SoundCloud URL
            progress_callback: Function(dict) called with progress updates
                              dict contains: 'status', 'downloaded_bytes', 'total_bytes', 'filename'

        Returns:
            True if successful, False otherwise
        """
        if not self.validate_url(url):
            raise ValueError("Invalid SoundCloud URL")

        # Setup quality
        quality = '320' if self.audio_quality == 'best' else self.audio_quality.replace(' kbps', '')

        # Setup yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(self.output_dir / '%(uploader)s - %(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'concurrent_fragments': 4,
            'lazy_playlist': True,
            'buffersize': 16384,
            'http_chunk_size': 10485760,
            'retries': 3,
            'socket_timeout': 15,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.audio_format,
                'preferredquality': quality,
            }],
        }

        # Add progress hook if callback provided
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]

        # Add cookies if available
        if self.cookies_file and Path(self.cookies_file).exists():
            ydl_opts['cookiefile'] = str(Path(self.cookies_file).absolute())

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            raise Exception(f"Download failed: {e}")
