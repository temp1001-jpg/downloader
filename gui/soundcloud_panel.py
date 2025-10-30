"""
SoundCloud Panel - GUI for SoundCloud downloads
"""

import customtkinter as ctk
import threading
from pathlib import Path
from core.soundcloud_downloader import SoundCloudDownloader


class SoundCloudPanel(ctk.CTkFrame):
    """SoundCloud downloader panel"""

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
            text="SoundCloud Downloader",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        header.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # URL input
        url_label = ctk.CTkLabel(self, text="SoundCloud URL:")
        url_label.grid(row=1, column=0, padx=20, pady=(10, 5), sticky="w")

        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="https://soundcloud.com/..."
        )
        self.url_entry.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        # Audio format
        format_label = ctk.CTkLabel(self, text="Audio Format:")
        format_label.grid(row=3, column=0, padx=20, pady=(15, 5), sticky="w")

        self.format_var = ctk.StringVar(value="MP3")
        format_menu = ctk.CTkOptionMenu(
            self,
            values=["MP3", "M4A", "WAV"],
            variable=self.format_var,
            width=150
        )
        format_menu.grid(row=4, column=0, padx=20, pady=5, sticky="w")

        # Audio quality
        quality_label = ctk.CTkLabel(self, text="Audio Quality:")
        quality_label.grid(row=5, column=0, padx=20, pady=(15, 5), sticky="w")

        self.quality_var = ctk.StringVar(value="Best")
        quality_menu = ctk.CTkOptionMenu(
            self,
            values=["Best", "192 kbps", "128 kbps"],
            variable=self.quality_var,
            width=150
        )
        quality_menu.grid(row=6, column=0, padx=20, pady=5, sticky="w")

        # Download button
        self.download_btn = ctk.CTkButton(
            self,
            text="Download",
            command=self.start_download,
            height=40
        )
        self.download_btn.grid(row=7, column=0, padx=20, pady=10, sticky="ew")

        # Status label
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color="gray")
        self.status_label.grid(row=8, column=0, padx=20, pady=5, sticky="w")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, mode="determinate")
        self.progress_bar.grid(row=9, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar.set(0)

        # Info text area
        self.info_text = ctk.CTkTextbox(self, height=200)
        self.info_text.grid(row=10, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self.grid_rowconfigure(10, weight=1)

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
                cookies_file = self.cookie_manager.cookies_to_netscape('.soundcloud.com')
            except Exception as e:
                self.after(0, lambda: self.info_text.insert("end", f"Warning: Could not load cookies: {e}\n"))

            # Create downloader
            download_dir = self.config.get("download_directory", "./downloads")

            self.downloader = SoundCloudDownloader(
                output_dir=download_dir,
                cookies=cookies_file,
                audio_format=self.format_var.get().lower(),
                audio_quality=self.quality_var.get()
            )

            # Validate URL
            if not self.downloader.validate_url(url):
                self.after(0, lambda: self.update_status("Invalid SoundCloud URL", error=True))
                return

            # Get info
            self.after(0, lambda: self.update_status("Fetching track info..."))
            info = self.downloader.get_info(url)

            if info:
                info_text = f"Title: {info.get('title', 'Unknown')}\n"
                info_text += f"Artist: {info.get('uploader', 'Unknown')}\n"
                duration = info.get('duration')
                if duration:
                    minutes, seconds = divmod(duration, 60)
                    info_text += f"Duration: {minutes:02d}:{seconds:02d}\n"

                self.after(0, lambda: self.info_text.insert("end", info_text + "\n"))

            # Download
            self.after(0, lambda: self.update_status("Downloading..."))

            def progress_callback(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d and d['total_bytes']:
                        progress = d['downloaded_bytes'] / d['total_bytes']
                        self.after(0, lambda: self.progress_bar.set(progress))
                elif d['status'] == 'finished':
                    self.after(0, lambda: self.progress_bar.set(1.0))

            success = self.downloader.download(url, progress_callback=progress_callback)

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
