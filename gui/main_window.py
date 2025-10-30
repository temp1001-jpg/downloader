"""
Main Window - All-in-One Media Downloader GUI
Sidebar layout with platform selection
"""

import customtkinter as ctk
from .youtube_panel import YouTubePanel
from .spotify_panel import SpotifyPanel
from .instagram_panel import InstagramPanel
from .soundcloud_panel import SoundCloudPanel
from .cookie_manager import CookieManager
import json
from pathlib import Path


class MainWindow(ctk.CTk):
    """Main application window with sidebar navigation"""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("All-in-One Media Downloader")
        self.geometry("900x600")
        self.minsize(800, 500)

        # Load configuration
        self.config = self.load_config()

        # Apply saved theme
        ctk.set_appearance_mode(self.config.get("theme", "dark"))

        # Initialize cookie manager
        self.cookie_manager = CookieManager()

        # Create layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create sidebar
        self.sidebar = ctk.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)  # Push buttons to top

        # Sidebar title
        self.sidebar_title = ctk.CTkLabel(
            self.sidebar,
            text="Platforms",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.sidebar_title.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Platform buttons
        self.youtube_btn = ctk.CTkButton(
            self.sidebar,
            text="YouTube",
            command=lambda: self.show_panel("youtube")
        )
        self.youtube_btn.grid(row=1, column=0, padx=20, pady=8)

        self.spotify_btn = ctk.CTkButton(
            self.sidebar,
            text="Spotify",
            command=lambda: self.show_panel("spotify")
        )
        self.spotify_btn.grid(row=2, column=0, padx=20, pady=8)

        self.instagram_btn = ctk.CTkButton(
            self.sidebar,
            text="Instagram",
            command=lambda: self.show_panel("instagram")
        )
        self.instagram_btn.grid(row=3, column=0, padx=20, pady=8)

        self.soundcloud_btn = ctk.CTkButton(
            self.sidebar,
            text="SoundCloud",
            command=lambda: self.show_panel("soundcloud")
        )
        self.soundcloud_btn.grid(row=4, column=0, padx=20, pady=8)

        # Separator
        separator = ctk.CTkFrame(self.sidebar, height=2)
        separator.grid(row=5, column=0, padx=20, pady=20, sticky="ew")

        # Settings button
        self.settings_btn = ctk.CTkButton(
            self.sidebar,
            text="Settings",
            command=self.open_settings
        )
        self.settings_btn.grid(row=6, column=0, padx=20, pady=8)

        # Refresh Cookies button
        self.refresh_cookies_btn = ctk.CTkButton(
            self.sidebar,
            text="Refresh Cookies",
            command=self.refresh_cookies
        )
        self.refresh_cookies_btn.grid(row=7, column=0, padx=20, pady=8)

        # Content area
        self.content_frame = ctk.CTkFrame(self, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Create panels
        self.panels = {}
        self.panels["youtube"] = YouTubePanel(
            self.content_frame,
            self.cookie_manager,
            self.config
        )
        self.panels["spotify"] = SpotifyPanel(
            self.content_frame,
            self.config
        )
        self.panels["instagram"] = InstagramPanel(
            self.content_frame,
            self.cookie_manager,
            self.config
        )
        self.panels["soundcloud"] = SoundCloudPanel(
            self.content_frame,
            self.cookie_manager,
            self.config
        )

        # Place all panels in grid (only one will be visible at a time)
        for panel in self.panels.values():
            panel.grid(row=0, column=0, sticky="nsew")

        # Button reference map for highlighting
        self.buttons = {
            "youtube": self.youtube_btn,
            "spotify": self.spotify_btn,
            "instagram": self.instagram_btn,
            "soundcloud": self.soundcloud_btn
        }

        # Show YouTube panel by default
        self.current_panel = None
        self.show_panel("youtube")

    def load_config(self):
        """Load configuration from file"""
        config_file = Path("config.json")
        default_config = {
            "download_directory": "./downloads",
            "theme": "dark",
            "color_scheme": "blue"
        }

        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
        except Exception as e:
            print(f"Warning: Could not load config: {e}")

        return default_config

    def save_config(self):
        """Save configuration to file"""
        config_file = Path("config.json")
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                print(f"Settings saved to {config_file.absolute()}")
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    def show_panel(self, panel_name):
        """Switch to specified panel"""
        # Hide current panel
        if self.current_panel:
            self.panels[self.current_panel].grid_remove()
            # Reset previous button color
            self.buttons[self.current_panel].configure(fg_color=["#3B8ED0", "#1F6AA5"])

        # Show new panel
        self.panels[panel_name].grid()
        self.current_panel = panel_name

        # Highlight active button
        self.buttons[panel_name].configure(fg_color=["#2B7FC5", "#144870"])

    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.config)
        dialog.wait_window()
        self.save_config()

    def refresh_cookies(self):
        """Manually refresh browser cookies"""
        success = self.cookie_manager.refresh_cookies()
        if success:
            self.show_message("Cookies refreshed successfully!")
        else:
            self.show_message("Failed to refresh cookies. No browsers found.", error=True)

    def show_message(self, message, error=False):
        """Show temporary message (could be improved with custom dialog)"""
        print(f"{'ERROR' if error else 'INFO'}: {message}")


class SettingsDialog(ctk.CTkToplevel):
    """Settings dialog window"""

    def __init__(self, parent, config):
        super().__init__(parent)

        self.config = config
        self.title("Settings")
        self.geometry("500x400")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Create widgets
        self.create_widgets()

    def create_widgets(self):
        """Create settings widgets"""
        # Download Directory
        dir_label = ctk.CTkLabel(self, text="Download Directory:")
        dir_label.pack(pady=(20, 5), padx=20, anchor="w")

        dir_frame = ctk.CTkFrame(self)
        dir_frame.pack(pady=5, padx=20, fill="x")

        self.dir_entry = ctk.CTkEntry(dir_frame, width=350)
        self.dir_entry.insert(0, self.config.get("download_directory", "./downloads"))
        self.dir_entry.pack(side="left", padx=5, pady=5)

        browse_btn = ctk.CTkButton(dir_frame, text="Browse", width=80, command=self.browse_directory)
        browse_btn.pack(side="left", padx=5, pady=5)

        # Theme
        theme_label = ctk.CTkLabel(self, text="Theme:")
        theme_label.pack(pady=(20, 5), padx=20, anchor="w")

        self.theme_var = ctk.StringVar(value=self.config.get("theme", "dark"))
        theme_menu = ctk.CTkOptionMenu(
            self,
            values=["dark", "light"],
            variable=self.theme_var
        )
        theme_menu.pack(pady=5, padx=20, anchor="w")

        # Theme change warning
        theme_warning = ctk.CTkLabel(
            self,
            text="Note: Restart app after saving to apply theme",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        theme_warning.pack(pady=5, padx=20, anchor="w")

        # Spacer
        ctk.CTkLabel(self, text="").pack(pady=20)

        # Buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=20, side="bottom")

        save_btn = ctk.CTkButton(btn_frame, text="Save", command=self.save_settings, width=100)
        save_btn.pack(side="left", padx=10)

        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=100)
        cancel_btn.pack(side="left", padx=10)

    def browse_directory(self):
        """Browse for download directory"""
        from tkinter import filedialog
        directory = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)

    def save_settings(self):
        """Save settings and close dialog"""
        old_theme = self.config.get("theme", "dark")
        new_theme = self.theme_var.get()

        self.config["download_directory"] = self.dir_entry.get()
        self.config["theme"] = new_theme

        # Show restart message if theme changed
        if old_theme != new_theme:
            print("\n" + "="*60)
            print("⚠️  THEME CHANGED")
            print("="*60)
            print(f"Theme changed from '{old_theme}' to '{new_theme}'")
            print("\n👉 Please CLOSE and RESTART the app to see the new theme!")
            print("="*60 + "\n")

        self.destroy()
