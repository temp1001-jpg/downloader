"""
YouTube Panel - GUI for YouTube downloads
"""

import customtkinter as ctk
import threading
from pathlib import Path
from core.youtube_downloader import YouTubeDownloader


class YouTubePanel(ctk.CTkFrame):
    """YouTube downloader panel"""

    def __init__(self, parent, cookie_manager, config):
        super().__init__(parent)

        self.cookie_manager = cookie_manager
        self.config = config
        self.downloader = None
        self.downloading = False

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text="YouTube Downloader",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # URL input
        url_label = ctk.CTkLabel(self, text="YouTube URL:")
        url_label.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")

        url_frame = ctk.CTkFrame(self)
        url_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        url_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(url_frame, placeholder_text="https://www.youtube.com/watch?v=...")
        self.url_entry.grid(row=0, column=0, padx=(5, 5), pady=5, sticky="ew")

        paste_btn = ctk.CTkButton(url_frame, text="Paste", width=80, command=self.paste_from_clipboard)
        paste_btn.grid(row=0, column=1, padx=(0, 5), pady=5)

        # Quality selection
        quality_label = ctk.CTkLabel(self, text="Quality:")
        quality_label.grid(row=3, column=0, padx=20, pady=(15, 5), sticky="w")

        self.quality_var = ctk.StringVar(value="1080p")
        quality_menu = ctk.CTkOptionMenu(
            self,
            values=["1080p", "720p", "480p", "360p", "Best", "Worst"],
            variable=self.quality_var,
            width=150
        )
        quality_menu.grid(row=4, column=0, padx=20, pady=5, sticky="w")

        # Audio only checkbox
        self.audio_only_var = ctk.BooleanVar(value=False)
        audio_checkbox = ctk.CTkCheckBox(
            self,
            text="Audio Only (MP3 320kbps)",
            variable=self.audio_only_var
        )
        audio_checkbox.grid(row=5, column=0, padx=20, pady=10, sticky="w")

        # Download button
        self.download_btn = ctk.CTkButton(
            self,
            text="Download",
            command=self.start_download,
            height=40
        )
        self.download_btn.grid(row=6, column=0, padx=20, pady=10, sticky="ew")

        # Status label
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=7, column=0, padx=20, pady=5, sticky="w")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, mode="determinate")
        self.progress_bar.grid(row=8, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)

        # Info text area
        self.info_text = ctk.CTkTextbox(self, height=200)
        self.info_text.grid(row=9, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self.grid_rowconfigure(9, weight=1)

    def paste_from_clipboard(self):
        """Paste URL from clipboard"""
        try:
            import pyperclip
            clipboard_content = pyperclip.paste().strip()
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, clipboard_content)
        except:
            self.update_status("Could not access clipboard", error=True)

    def start_download(self):
        """Start download in background thread"""
        if self.downloading:
            self.update_status("Download already in progress", error=True)
            return

        url = self.url_entry.get().strip()
        if not url:
            self.update_status("Please enter a URL", error=True)
            return

        # Disable UI
        self.download_btn.configure(state="disabled")
        self.url_entry.configure(state="disabled")
        self.downloading = True

        # Start download thread
        thread = threading.Thread(target=self.download_worker, args=(url,), daemon=True)
        thread.start()

    def download_worker(self, url):
        """Background download worker"""
        try:
            # Update UI
            self.after(0, lambda: self.update_status("Validating URL..."))
            self.after(0, lambda: self.progress_bar.set(0))
            self.after(0, lambda: self.info_text.delete("1.0", "end"))

            # Get cookies
            cookies_file = None
            try:
                cookies_file = self.cookie_manager.cookies_to_netscape('.youtube.com')
            except Exception as e:
                self.after(0, lambda: self.info_text.insert("end", f"Warning: Could not load cookies: {e}\n"))

            # Create downloader
            download_dir = self.config.get("download_directory", "./downloads")
            self.downloader = YouTubeDownloader(
                output_dir=download_dir,
                cookies=cookies_file
            )

            # Validate URL
            if not self.downloader.validate_url(url):
                self.after(0, lambda: self.update_status("Invalid YouTube URL", error=True))
                return

            # Get video info
            self.after(0, lambda: self.update_status("Fetching video info..."))
            info = self.downloader.get_info(url)

            if not info:
                self.after(0, lambda: self.update_status("Could not fetch video info", error=True))
                return

            # Display info
            is_playlist = 'entries' in info
            if is_playlist:
                info_text = f"Playlist: {info.get('title', 'Unknown')}\n"
                info_text += f"Videos: {len(info['entries'])}\n"
            else:
                info_text = f"Title: {info.get('title', 'Unknown')}\n"
                info_text += f"Uploader: {info.get('uploader', 'Unknown')}\n"
                duration = info.get('duration')
                if duration:
                    minutes, seconds = divmod(duration, 60)
                    info_text += f"Duration: {minutes:02d}:{seconds:02d}\n"

            self.after(0, lambda: self.info_text.insert("end", info_text + "\n"))

            # Download
            quality = self.quality_var.get()
            audio_only = self.audio_only_var.get()

            self.after(0, lambda: self.update_status("Downloading..."))

            # Progress callback
            def progress_callback(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d and d['total_bytes']:
                        progress = d['downloaded_bytes'] / d['total_bytes']
                        self.after(0, lambda: self.progress_bar.set(progress))
                elif d['status'] == 'finished':
                    self.after(0, lambda: self.progress_bar.set(1.0))

            success = self.downloader.download(
                url,
                quality=quality,
                audio_only=audio_only,
                progress_callback=progress_callback
            )

            if success:
                self.after(0, lambda: self.update_status("Download complete!", success=True))
                self.after(0, lambda: self.info_text.insert("end", f"\nSaved to: {download_dir}\n"))
            else:
                self.after(0, lambda: self.update_status("Download failed", error=True))

        except Exception as e:
            self.after(0, lambda: self.update_status(f"Error: {str(e)}", error=True))
            self.after(0, lambda: self.info_text.insert("end", f"\nError: {str(e)}\n"))

        finally:
            # Re-enable UI
            self.after(0, lambda: self.download_btn.configure(state="normal"))
            self.after(0, lambda: self.url_entry.configure(state="normal"))
            self.downloading = False

    def update_status(self, message, error=False, success=False):
        """Update status label"""
        color = "red" if error else ("green" if success else "gray")
        self.status_label.configure(text=message, text_color=color)
