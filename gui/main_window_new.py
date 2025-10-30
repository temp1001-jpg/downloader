"""
Main Window - Blockchain-style UI for Media Downloader
Exact replica of the blockchain dashboard design
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
    """Main application window with blockchain-inspired design"""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Blify")
        self.geometry("1400x800")
        self.minsize(1200, 700)

        # Load configuration
        self.config = self.load_config()

        # Apply saved theme (force light mode for this design)
        ctk.set_appearance_mode("light")

        # Load Spotify credentials
        import os
        if self.config.get("spotify_client_id"):
            os.environ["SPOTIFY_CLIENT_ID"] = self.config["spotify_client_id"]
        if self.config.get("spotify_client_secret"):
            os.environ["SPOTIFY_CLIENT_SECRET"] = self.config["spotify_client_secret"]

        # Initialize cookie manager
        self.cookie_manager = CookieManager()

        # Create main container
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Create UI
        self.create_sidebar()
        self.create_main_content()

    def create_sidebar(self):
        """Create left sidebar with gradient and profile"""
        # Sidebar with gradient effect (simulated with single color)
        self.sidebar = ctk.CTkFrame(
            self,
            width=240,
            corner_radius=0,
            fg_color="#D4F4F4"  # Light mint color
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo and title at top
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(30, 10), padx=20)

        logo_icon = ctk.CTkLabel(
            logo_frame,
            text="🌀",
            font=ctk.CTkFont(size=32)
        )
        logo_icon.pack(side="left")

        logo_text = ctk.CTkLabel(
            logo_frame,
            text="  Blify",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="#1F2937"
        )
        logo_text.pack(side="left")

        # Profile section
        profile_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )
        profile_frame.pack(pady=(30, 20), padx=20)

        # Profile picture (circular frame)
        profile_pic = ctk.CTkLabel(
            profile_frame,
            text="👤",
            font=ctk.CTkFont(size=48),
            width=80,
            height=80,
            fg_color="#A0D8D8",
            corner_radius=40
        )
        profile_pic.pack()

        profile_name = ctk.CTkLabel(
            profile_frame,
            text="User",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1F2937"
        )
        profile_name.pack(pady=(10, 0))

        edit_profile_btn = ctk.CTkButton(
            profile_frame,
            text="Edit Profile",
            width=120,
            height=28,
            fg_color="transparent",
            text_color="#6B7280",
            hover_color="#E5E7EB",
            border_width=0,
            font=ctk.CTkFont(size=12)
        )
        edit_profile_btn.pack(pady=(5, 0))

        # Navigation menu
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="both", expand=True, padx=20, pady=(20, 0))

        # Menu items
        menu_items = [
            ("⊞", "Dashboard"),
            ("💡", "Insights"),
            ("📦", "Assets"),
            ("👥", "Network"),
            ("⚙️", "Settings")
        ]

        self.nav_buttons = {}
        for icon, text in menu_items:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"{icon}  {text}",
                anchor="w",
                width=180,
                height=45,
                corner_radius=8,
                fg_color="transparent",
                text_color="#6B7280",
                hover_color="#E5E7EB",
                font=ctk.CTkFont(size=14),
                border_width=0,
                command=lambda t=text: self.nav_clicked(t)
            )
            btn.pack(pady=5)
            self.nav_buttons[text] = btn

        # Highlight Dashboard by default
        self.nav_buttons["Dashboard"].configure(
            fg_color="#FFFFFF",
            text_color="#1F2937"
        )

        # Log Out button at bottom with gradient background
        logout_frame = ctk.CTkFrame(
            self.sidebar,
            height=80,
            fg_color="#7DD3C0"  # Turquoise gradient bottom
        )
        logout_frame.pack(side="bottom", fill="x")

        logout_btn = ctk.CTkButton(
            logout_frame,
            text="⊗  Log Out",
            width=180,
            height=45,
            corner_radius=8,
            fg_color="transparent",
            text_color="#1F2937",
            hover_color="#6BB8A6",
            font=ctk.CTkFont(size=14, weight="bold"),
            border_width=0,
            command=self.quit
        )
        logout_btn.pack(pady=20, padx=20)

    def create_main_content(self):
        """Create main content area with header and dashboard"""
        # Main content frame
        main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#F3F4F6")
        main_frame.grid(row=0, column=1, sticky="nsew")
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Header
        self.create_header(main_frame)

        # Dashboard content (scrollable)
        self.content_container = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="#F3F4F6",
            corner_radius=0
        )
        self.content_container.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)
        self.content_container.grid_columnconfigure(0, weight=1)

        # Create dashboard view
        self.create_dashboard()

    def create_header(self, parent):
        """Create top header bar"""
        header = ctk.CTkFrame(
            parent,
            height=80,
            corner_radius=0,
            fg_color="#FFFFFF"
        )
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        # Left side - Greeting
        left_frame = ctk.CTkFrame(header, fg_color="transparent")
        left_frame.pack(side="left", padx=30, pady=20)

        greeting = ctk.CTkLabel(
            left_frame,
            text="Hello, Fernando Dies",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#1F2937"
        )
        greeting.pack(side="left")

        access_level = ctk.CTkLabel(
            left_frame,
            text="  |  Access Level: Member",
            font=ctk.CTkFont(size=14),
            text_color="#6B7280"
        )
        access_level.pack(side="left")

        # Right side - Actions
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right", padx=30, pady=20)

        # Bell icon button
        bell_btn = ctk.CTkButton(
            right_frame,
            text="🔔",
            width=40,
            height=40,
            corner_radius=8,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#1F2937",
            font=ctk.CTkFont(size=18)
        )
        bell_btn.pack(side="left", padx=5)

        # Lightning icon button
        lightning_btn = ctk.CTkButton(
            right_frame,
            text="⚡",
            width=40,
            height=40,
            corner_radius=8,
            fg_color="#F3F4F6",
            hover_color="#E5E7EB",
            text_color="#1F2937",
            font=ctk.CTkFont(size=18)
        )
        lightning_btn.pack(side="left", padx=5)

        # Switch Network button
        switch_btn = ctk.CTkButton(
            right_frame,
            text="Switch Network",
            width=140,
            height=40,
            corner_radius=8,
            fg_color="#14B8A6",
            hover_color="#0D9488",
            text_color="#FFFFFF",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        switch_btn.pack(side="left", padx=5)

    def create_dashboard(self):
        """Create dashboard with stats cards and activity log"""
        # Title section
        title_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        title_label = ctk.CTkLabel(
            title_frame,
            text="My Blockchain Evolution",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#1F2937",
            anchor="w"
        )
        title_label.pack(side="left")

        # XP indicator
        xp_frame = ctk.CTkFrame(title_frame, fg_color="transparent")
        xp_frame.pack(side="left", padx=20)

        xp_number = ctk.CTkLabel(
            xp_frame,
            text="18",
            font=ctk.CTkFont(size=72, weight="bold"),
            text_color="#1F2937"
        )
        xp_number.pack()

        xp_badge = ctk.CTkLabel(
            xp_frame,
            text="+2 XP Today",
            font=ctk.CTkFont(size=12),
            text_color="#10B981",
            fg_color="#D1FAE5",
            corner_radius=12,
            padx=12,
            pady=6
        )
        xp_badge.place(relx=1.0, rely=0.0, anchor="ne")

        # Stats cards row
        cards_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="ew", pady=(0, 30))
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Card 1: Assets Analytics
        self.create_card_1(cards_frame)

        # Card 2: Validator Activity
        self.create_card_2(cards_frame)

        # Card 3: Smart Contracts
        self.create_card_3(cards_frame)

        # Bottom section with charts and logs
        bottom_frame = ctk.CTkFrame(self.content_container, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 20))
        bottom_frame.grid_columnconfigure(1, weight=1)

        # Daily Interactions chart
        self.create_daily_interactions(bottom_frame)

        # Smart Interaction Log table
        self.create_interaction_log(bottom_frame)

    def create_card_1(self, parent):
        """Assets Analytics card with gradient"""
        card = ctk.CTkFrame(
            parent,
            corner_radius=16,
            fg_color="#34D399",  # Gradient green
            border_width=0
        )
        card.grid(row=0, column=0, sticky="nsew", padx=10)

        # Card content
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=25)

        # Icon and title
        icon = ctk.CTkLabel(
            content,
            text="📊",
            font=ctk.CTkFont(size=28)
        )
        icon.pack(anchor="w")

        title = ctk.CTkLabel(
            content,
            text="ASSETS ANALYTICS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#FFFFFF"
        )
        title.pack(anchor="w", pady=(5, 15))

        # Stats
        stat1_frame = ctk.CTkFrame(content, fg_color="transparent")
        stat1_frame.pack(fill="x", pady=5)

        stat1_label = ctk.CTkLabel(
            stat1_frame,
            text="Total Assets",
            font=ctk.CTkFont(size=13),
            text_color="#FFFFFF"
        )
        stat1_label.pack(side="left")

        stat1_value = ctk.CTkLabel(
            stat1_frame,
            text="23",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FFFFFF"
        )
        stat1_value.pack(side="right")

        stat2_frame = ctk.CTkFrame(content, fg_color="transparent")
        stat2_frame.pack(fill="x", pady=5)

        stat2_label = ctk.CTkLabel(
            stat2_frame,
            text="Value Change",
            font=ctk.CTkFont(size=13),
            text_color="#FFFFFF"
        )
        stat2_label.pack(side="left")

        stat2_value = ctk.CTkLabel(
            stat2_frame,
            text="+ 3,2%",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FFFFFF"
        )
        stat2_value.pack(side="right")

        # Button
        btn = ctk.CTkButton(
            content,
            text="View Details",
            corner_radius=8,
            fg_color="#FFFFFF",
            text_color="#34D399",
            hover_color="#F3F4F6",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=35
        )
        btn.pack(fill="x", pady=(15, 0))

    def create_card_2(self, parent):
        """Validator Activity card"""
        card = ctk.CTkFrame(
            parent,
            corner_radius=16,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E5E7EB"
        )
        card.grid(row=0, column=1, sticky="nsew", padx=10)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=25)

        # Icon and title
        icon = ctk.CTkLabel(
            content,
            text="◈",
            font=ctk.CTkFont(size=28),
            text_color="#14B8A6"
        )
        icon.pack(anchor="w")

        title = ctk.CTkLabel(
            content,
            text="VALIDATOR ACTIVITY",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#6B7280"
        )
        title.pack(anchor="w", pady=(5, 15))

        # Badge
        badge = ctk.CTkLabel(
            content,
            text="2 Days Ago",
            font=ctk.CTkFont(size=11),
            text_color="#14B8A6",
            fg_color="#D1FAE5",
            corner_radius=12,
            padx=12,
            pady=6
        )
        badge.pack(anchor="w", pady=(0, 15))

        # Network info
        network_label = ctk.CTkLabel(
            content,
            text="Ethereum • Polygon",
            font=ctk.CTkFont(size=13),
            text_color="#1F2937"
        )
        network_label.pack(anchor="w")

        # Button
        btn = ctk.CTkButton(
            content,
            text="View Details",
            corner_radius=8,
            fg_color="#F3F4F6",
            text_color="#1F2937",
            hover_color="#E5E7EB",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=35
        )
        btn.pack(fill="x", pady=(15, 0))

    def create_card_3(self, parent):
        """Smart Contracts card"""
        card = ctk.CTkFrame(
            parent,
            corner_radius=16,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E5E7EB"
        )
        card.grid(row=0, column=2, sticky="nsew", padx=10)

        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=25, pady=25)

        # Icon and title
        icon = ctk.CTkLabel(
            content,
            text="🔒",
            font=ctk.CTkFont(size=28)
        )
        icon.pack(anchor="w")

        title = ctk.CTkLabel(
            content,
            text="SMART CONTRACTS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#6B7280"
        )
        title.pack(anchor="w", pady=(5, 15))

        # Stats
        stat1_frame = ctk.CTkFrame(content, fg_color="transparent")
        stat1_frame.pack(fill="x", pady=5)

        stat1_label = ctk.CTkLabel(
            stat1_frame,
            text="Active Contracts",
            font=ctk.CTkFont(size=13),
            text_color="#6B7280"
        )
        stat1_label.pack(side="left")

        stat1_value = ctk.CTkLabel(
            stat1_frame,
            text="6",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1F2937"
        )
        stat1_value.pack(side="right")

        stat2_frame = ctk.CTkFrame(content, fg_color="transparent")
        stat2_frame.pack(fill="x", pady=5)

        stat2_label = ctk.CTkLabel(
            stat2_frame,
            text="Gas Spent",
            font=ctk.CTkFont(size=13),
            text_color="#6B7280"
        )
        stat2_label.pack(side="left")

        stat2_value = ctk.CTkLabel(
            stat2_frame,
            text="0.004 ETH",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#1F2937"
        )
        stat2_value.pack(side="right")

        # Button
        btn = ctk.CTkButton(
            content,
            text="Manage Contracts",
            corner_radius=8,
            fg_color="#F3F4F6",
            text_color="#1F2937",
            hover_color="#E5E7EB",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=35
        )
        btn.pack(fill="x", pady=(15, 0))

    def create_daily_interactions(self, parent):
        """Daily Interactions chart"""
        chart_card = ctk.CTkFrame(
            parent,
            corner_radius=16,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E5E7EB",
            width=350
        )
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        # Title
        title_frame = ctk.CTkFrame(chart_card, fg_color="transparent")
        title_frame.pack(fill="x", padx=25, pady=(20, 10))

        title = ctk.CTkLabel(
            title_frame,
            text="Daily Interactions",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1F2937"
        )
        title.pack(side="left")

        menu_btn = ctk.CTkLabel(
            title_frame,
            text="⋯",
            font=ctk.CTkFont(size=20),
            text_color="#6B7280"
        )
        menu_btn.pack(side="right")

        # Simple bar chart representation
        chart_frame = ctk.CTkFrame(chart_card, fg_color="transparent")
        chart_frame.pack(fill="both", expand=True, padx=25, pady=(10, 20))

        # Chart bar (simplified)
        bar_container = ctk.CTkFrame(chart_frame, fg_color="transparent", height=200)
        bar_container.pack(fill="x", pady=(20, 0))

        # Highlight bar with label
        highlight_bar = ctk.CTkFrame(
            bar_container,
            width=60,
            height=150,
            fg_color="#60A5FA",
            corner_radius=8
        )
        highlight_bar.place(relx=0.5, rely=0.5, anchor="center")

        bar_label = ctk.CTkLabel(
            highlight_bar,
            text="18",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#FFFFFF"
        )
        bar_label.place(relx=0.5, rely=0.1, anchor="center")

        # Weekday labels
        days_frame = ctk.CTkFrame(chart_frame, fg_color="transparent")
        days_frame.pack(fill="x")

        days = ["MON", "TUE", "WED", "THU", "FRI"]
        for day in days:
            label = ctk.CTkLabel(
                days_frame,
                text=day,
                font=ctk.CTkFont(size=10),
                text_color="#9CA3AF"
            )
            label.pack(side="left", expand=True)

    def create_interaction_log(self, parent):
        """Smart Interaction Log table"""
        log_card = ctk.CTkFrame(
            parent,
            corner_radius=16,
            fg_color="#FFFFFF",
            border_width=1,
            border_color="#E5E7EB"
        )
        log_card.grid(row=0, column=1, sticky="nsew")

        # Title
        title_frame = ctk.CTkFrame(log_card, fg_color="transparent")
        title_frame.pack(fill="x", padx=25, pady=(20, 10))

        title = ctk.CTkLabel(
            title_frame,
            text="Smart Interaction Log",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#1F2937"
        )
        title.pack(side="left")

        filter_btn = ctk.CTkButton(
            title_frame,
            text="All Types ▾",
            width=100,
            height=28,
            corner_radius=6,
            fg_color="#F3F4F6",
            text_color="#6B7280",
            hover_color="#E5E7EB",
            font=ctk.CTkFont(size=12)
        )
        filter_btn.pack(side="right")

        # Table headers
        headers_frame = ctk.CTkFrame(log_card, fg_color="transparent")
        headers_frame.pack(fill="x", padx=25, pady=(10, 5))

        headers = ["STATUS", "ASSET", "NETWORK", "ACTION", "RESULT"]
        for header in headers:
            label = ctk.CTkLabel(
                headers_frame,
                text=header,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#9CA3AF",
                anchor="w"
            )
            label.pack(side="left", expand=True, padx=5)

        # Table rows
        rows_data = [
            ("✓", "Confirmed", "Token XYZ", "⬆ Ethereum", "Sent 150 Units", "Success", "#10B981"),
            ("⊙", "Pending", "Orbify NFT", "🔷 Tezos", "Created NFT #128", "Awaiting", "#F59E0B"),
            ("✓", "Confirmed", "Token ABC", "⚫ Arbitrum", "Cast Governance Vote", "Success", "#10B981"),
            ("✗", "Failed", "Token DEF", "🔺 Avalanche", "Updated Metadata", "Reverted", "#EF4444"),
        ]

        for status_icon, status_text, asset, network, action, result, color in rows_data:
            row = ctk.CTkFrame(log_card, fg_color="#F9FAFB", corner_radius=8, height=50)
            row.pack(fill="x", padx=25, pady=3)

            # Status
            status_frame = ctk.CTkFrame(row, fg_color="transparent")
            status_frame.pack(side="left", expand=True, padx=5)

            status_label = ctk.CTkLabel(
                status_frame,
                text=f"{status_icon}  {status_text}",
                font=ctk.CTkFont(size=12),
                text_color="#1F2937"
            )
            status_label.pack(anchor="w")

            # Asset
            asset_label = ctk.CTkLabel(
                row,
                text=asset,
                font=ctk.CTkFont(size=12),
                text_color="#1F2937"
            )
            asset_label.pack(side="left", expand=True, padx=5)

            # Network
            network_label = ctk.CTkLabel(
                row,
                text=network,
                font=ctk.CTkFont(size=12),
                text_color="#1F2937"
            )
            network_label.pack(side="left", expand=True, padx=5)

            # Action
            action_label = ctk.CTkLabel(
                row,
                text=action,
                font=ctk.CTkFont(size=12),
                text_color="#1F2937"
            )
            action_label.pack(side="left", expand=True, padx=5)

            # Result badge
            result_badge = ctk.CTkLabel(
                row,
                text=result,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=color,
                fg_color=f"{color}15",  # Light version
                corner_radius=12,
                padx=12,
                pady=6
            )
            result_badge.pack(side="left", padx=5)

    def nav_clicked(self, item_name):
        """Handle navigation menu clicks"""
        # Reset all buttons
        for btn in self.nav_buttons.values():
            btn.configure(
                fg_color="transparent",
                text_color="#6B7280"
            )

        # Highlight clicked button
        self.nav_buttons[item_name].configure(
            fg_color="#FFFFFF",
            text_color="#1F2937"
        )

        # Show appropriate panel
        if item_name == "Settings":
            self.open_settings()

    def open_settings(self):
        """Open settings dialog"""
        from .main_window import SettingsDialog
        dialog = SettingsDialog(self, self.config, self.cookie_manager)
        dialog.wait_window()
        self.save_config()

    def load_config(self):
        """Load configuration from file"""
        config_file = Path("config.json")
        default_config = {
            "download_directory": "./downloads",
            "theme": "light",
            "spotify_client_id": "",
            "spotify_client_secret": "",
            "cookies_file": ""
        }

        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
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
        except Exception as e:
            print(f"Warning: Could not save config: {e}")
