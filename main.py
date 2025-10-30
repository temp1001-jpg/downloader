#!/usr/bin/env python3
"""
All-in-One Media Downloader
Unified GUI for YouTube, Spotify, Instagram, and SoundCloud
"""

import sys
import os

# Add the downloader directory to the path
sys.path.insert(0, os.path.dirname(__file__))

try:
    import customtkinter as ctk
except ImportError:
    print("Error: CustomTkinter is required")
    print("Install with: pip install customtkinter")
    sys.exit(1)

from gui.main_window import MainWindow


def main():
    """Main entry point for the application"""
    # Set appearance mode and color theme
    ctk.set_appearance_mode("dark")  # "dark" or "light"
    ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"

    # Create and run application
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
