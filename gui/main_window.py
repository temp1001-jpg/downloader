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
            "color_scheme": "blue",
            "spotify_client_id": "",
            "spotify_client_secret": "",
            "cookies_file": ""
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
        dialog = SettingsDialog(self, self.config, self.cookie_manager)
        dialog.wait_window()
        self.save_config()

    def show_message(self, message, error=False):
        """Show temporary message (could be improved with custom dialog)"""
        print(f"{'ERROR' if error else 'INFO'}: {message}")


class SettingsDialog(ctk.CTkToplevel):
    """Settings dialog window"""

    def __init__(self, parent, config, cookie_manager):
        super().__init__(parent)

        self.config = config
        self.cookie_manager = cookie_manager
        self.title("Settings")
        self.geometry("650x700")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        self.grab_set()

        # Create scrollable frame for settings
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=600, height=650)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create widgets
        self.create_widgets()

    def create_widgets(self):
        """Create settings widgets"""
        parent = self.scrollable_frame

        # ===== GENERAL SETTINGS =====
        general_header = ctk.CTkLabel(
            parent,
            text="⚙️ General Settings",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        general_header.pack(pady=(10, 10), padx=20, anchor="w")

        # Download Directory
        dir_label = ctk.CTkLabel(parent, text="Download Directory:")
        dir_label.pack(pady=(10, 5), padx=20, anchor="w")

        dir_frame = ctk.CTkFrame(parent)
        dir_frame.pack(pady=5, padx=20, fill="x")

        self.dir_entry = ctk.CTkEntry(dir_frame, width=450)
        self.dir_entry.insert(0, self.config.get("download_directory", "./downloads"))
        self.dir_entry.pack(side="left", padx=5, pady=5)

        browse_btn = ctk.CTkButton(dir_frame, text="Browse", width=80, command=self.browse_directory)
        browse_btn.pack(side="left", padx=5, pady=5)

        # Theme
        theme_label = ctk.CTkLabel(parent, text="Theme:")
        theme_label.pack(pady=(15, 5), padx=20, anchor="w")

        self.theme_var = ctk.StringVar(value=self.config.get("theme", "dark"))
        theme_menu = ctk.CTkOptionMenu(
            parent,
            values=["dark", "light"],
            variable=self.theme_var,
            width=200
        )
        theme_menu.pack(pady=5, padx=20, anchor="w")

        # Theme change warning
        theme_warning = ctk.CTkLabel(
            parent,
            text="⚠️ Restart app after saving to apply theme",
            font=ctk.CTkFont(size=11),
            text_color="orange"
        )
        theme_warning.pack(pady=5, padx=20, anchor="w")

        # Separator
        ctk.CTkFrame(parent, height=2).pack(pady=20, padx=20, fill="x")

        # ===== SPOTIFY CREDENTIALS =====
        spotify_header = ctk.CTkLabel(
            parent,
            text="🎵 Spotify API Credentials",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        spotify_header.pack(pady=(10, 5), padx=20, anchor="w")

        # Instructions
        spotify_instructions = ctk.CTkLabel(
            parent,
            text="1. Go to https://developer.spotify.com/dashboard\n"
                 "2. Create an app (or use existing one)\n"
                 "3. Copy your Client ID and Client Secret\n"
                 "4. Paste them below:",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        )
        spotify_instructions.pack(pady=5, padx=20, anchor="w")

        # Spotify Client ID
        client_id_label = ctk.CTkLabel(parent, text="Spotify Client ID:")
        client_id_label.pack(pady=(10, 5), padx=20, anchor="w")

        self.spotify_client_id_entry = ctk.CTkEntry(parent, width=550, placeholder_text="Enter your Spotify Client ID")
        self.spotify_client_id_entry.insert(0, self.config.get("spotify_client_id", ""))
        self.spotify_client_id_entry.pack(pady=5, padx=20, anchor="w")

        # Spotify Client Secret
        client_secret_label = ctk.CTkLabel(parent, text="Spotify Client Secret:")
        client_secret_label.pack(pady=(10, 5), padx=20, anchor="w")

        self.spotify_client_secret_entry = ctk.CTkEntry(parent, width=550, placeholder_text="Enter your Spotify Client Secret", show="*")
        self.spotify_client_secret_entry.insert(0, self.config.get("spotify_client_secret", ""))
        self.spotify_client_secret_entry.pack(pady=5, padx=20, anchor="w")

        # Separator
        ctk.CTkFrame(parent, height=2).pack(pady=20, padx=20, fill="x")

        # ===== COOKIES CONFIGURATION =====
        cookies_header = ctk.CTkLabel(
            parent,
            text="🍪 Cookies Configuration",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        cookies_header.pack(pady=(10, 5), padx=20, anchor="w")

        # Instructions
        cookies_instructions = ctk.CTkLabel(
            parent,
            text="For age-restricted or private content, you need browser cookies:\n\n"
                 "Option 1: Automatic (Recommended)\n"
                 "  - Close all browsers completely\n"
                 "  - Open this app - it will auto-detect cookies\n\n"
                 "Option 2: Manual (If automatic fails)\n"
                 "  1. Install browser extension: 'Get cookies.txt LOCALLY'\n"
                 "  2. Go to youtube.com, instagram.com, or soundcloud.com\n"
                 "  3. Click extension and export cookies\n"
                 "  4. Save as 'cookies.txt' in app folder or enter path below:",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left"
        )
        cookies_instructions.pack(pady=5, padx=20, anchor="w")

        # Cookies file path
        cookies_label = ctk.CTkLabel(parent, text="Cookies File Path (optional):")
        cookies_label.pack(pady=(10, 5), padx=20, anchor="w")

        cookies_frame = ctk.CTkFrame(parent)
        cookies_frame.pack(pady=5, padx=20, fill="x")

        self.cookies_entry = ctk.CTkEntry(cookies_frame, width=450, placeholder_text="cookies.txt")
        self.cookies_entry.insert(0, self.config.get("cookies_file", ""))
        self.cookies_entry.pack(side="left", padx=5, pady=5)

        browse_cookies_btn = ctk.CTkButton(cookies_frame, text="Browse", width=80, command=self.browse_cookies)
        browse_cookies_btn.pack(side="left", padx=5, pady=5)

        # Cookie status
        cookie_status = "✓ Cookies loaded" if self.cookie_manager.has_cookies() else "⚠️ No cookies detected"
        self.cookie_status_label = ctk.CTkLabel(
            parent,
            text=cookie_status,
            font=ctk.CTkFont(size=11),
            text_color="green" if self.cookie_manager.has_cookies() else "orange"
        )
        self.cookie_status_label.pack(pady=5, padx=20, anchor="w")

        # Spacer
        ctk.CTkLabel(parent, text="").pack(pady=20)

        # ===== BUTTONS =====
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10, side="bottom")

        save_btn = ctk.CTkButton(btn_frame, text="Save Settings", command=self.save_settings, width=120)
        save_btn.pack(side="left", padx=10)

        cancel_btn = ctk.CTkButton(btn_frame, text="Cancel", command=self.destroy, width=120)
        cancel_btn.pack(side="left", padx=10)

    def browse_directory(self):
        """Browse for download directory"""
        from tkinter import filedialog
        directory = filedialog.askdirectory(initialdir=self.dir_entry.get())
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)

    def browse_cookies(self):
        """Browse for cookies file"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(
            initialdir=".",
            title="Select Cookies File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.cookies_entry.delete(0, "end")
            self.cookies_entry.insert(0, filename)

    def save_settings(self):
        """Save settings and close dialog"""
        old_theme = self.config.get("theme", "dark")
        new_theme = self.theme_var.get()

        # Save all settings
        self.config["download_directory"] = self.dir_entry.get()
        self.config["theme"] = new_theme
        self.config["spotify_client_id"] = self.spotify_client_id_entry.get().strip()
        self.config["spotify_client_secret"] = self.spotify_client_secret_entry.get().strip()
        self.config["cookies_file"] = self.cookies_entry.get().strip()

        # Update environment variables for Spotify
        import os
        if self.config["spotify_client_id"]:
            os.environ["SPOTIFY_CLIENT_ID"] = self.config["spotify_client_id"]
        if self.config["spotify_client_secret"]:
            os.environ["SPOTIFY_CLIENT_SECRET"] = self.config["spotify_client_secret"]

        # Update cookie manager if cookies file specified
        if self.config["cookies_file"]:
            cookies_path = Path(self.config["cookies_file"])
            if cookies_path.exists():
                try:
                    from http.cookiejar import MozillaCookieJar
                    jar = MozillaCookieJar(str(cookies_path))
                    jar.load(ignore_discard=True, ignore_expires=True)
                    self.cookie_manager.cookie_jar = jar
                    self.cookie_manager._organize_cookies()
                    print(f"✓ Loaded cookies from: {cookies_path}")
                except Exception as e:
                    print(f"Warning: Could not load cookies: {e}")

        # Show restart message if theme changed
        if old_theme != new_theme:
            print("\n" + "="*60)
            print("⚠️  THEME CHANGED")
            print("="*60)
            print(f"Theme changed from '{old_theme}' to '{new_theme}'")
            print("\n👉 Please CLOSE and RESTART the app to see the new theme!")
            print("="*60 + "\n")

        print("\n✓ Settings saved successfully!\n")
        self.destroy()
