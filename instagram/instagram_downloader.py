#!/usr/bin/env python3
"""
Instagram Video Downloader
A single-file Python application for downloading Instagram videos and extracting audio.
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp is required. Install it with: pip install yt-dlp")
    sys.exit(1)


class InstagramDownloader:
    """Main application class for Instagram video downloading."""
    
    def __init__(self):
        self.settings_file = "instagram_downloader_settings.json"
        self.settings = self.load_settings()
        
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file or create default settings."""
        default_settings = {
            "download_directory": str(Path.home() / "Downloads" / "Instagram"),
            "video_quality": "best",
            "audio_format": "mp3",
            "audio_quality": "192"
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                # Merge with defaults to ensure all keys exist
                for key, value in default_settings.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load settings ({e}). Using defaults.")
        
        return default_settings
    
    def save_settings(self):
        """Save current settings to JSON file."""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save settings ({e}).")
    
    def validate_instagram_url(self, url: str) -> bool:
        """Validate if the URL is a valid Instagram URL."""
        instagram_patterns = [
            r'https?://(?:www\.)?instagram\.com/p/[A-Za-z0-9_-]+',
            r'https?://(?:www\.)?instagram\.com/reel/[A-Za-z0-9_-]+',
            r'https?://(?:www\.)?instagram\.com/tv/[A-Za-z0-9_-]+',
            r'https?://(?:www\.)?instagram\.com/stories/[A-Za-z0-9_.-]+/[0-9]+',
        ]
        
        return any(re.match(pattern, url.strip()) for pattern in instagram_patterns)
    
    def progress_hook(self, d):
        """Progress hook for yt-dlp downloads."""
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                print(f"\rDownloading... {percent:.1f}% "
                      f"({d['downloaded_bytes']}/{d['total_bytes']} bytes)", end='')
            elif '_percent_str' in d:
                print(f"\rDownloading... {d['_percent_str']}", end='')
            else:
                print(f"\rDownloading... {d.get('downloaded_bytes', 0)} bytes", end='')
        elif d['status'] == 'finished':
            print(f"\n✅ Download completed: {d['filename']}")
        elif d['status'] == 'error':
            print(f"\n❌ Download error: {d.get('error', 'Unknown error')}")
    
    def download_video(self, url: str) -> bool:
        """Download Instagram video."""
        if not self.validate_instagram_url(url):
            print("❌ Invalid Instagram URL. Please provide a valid Instagram post/reel/TV URL.")
            return False
        
        # Ensure download directory exists
        os.makedirs(self.settings["download_directory"], exist_ok=True)
        
        ydl_opts = {
            'outtmpl': os.path.join(self.settings["download_directory"], 
                                  '%(uploader)s_%(title)s.%(ext)s'),
            'format': self.settings["video_quality"],
            'progress_hooks': [self.progress_hook],
            'no_warnings': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"📥 Starting video download from: {url}")
                ydl.download([url])
                return True
        except Exception as e:
            print(f"❌ Error downloading video: {str(e)}")
            return False
    
    def download_audio(self, url: str) -> bool:
        """Download and extract audio from Instagram video."""
        if not self.validate_instagram_url(url):
            print("❌ Invalid Instagram URL. Please provide a valid Instagram post/reel/TV URL.")
            return False
        
        # Ensure download directory exists
        os.makedirs(self.settings["download_directory"], exist_ok=True)
        
        ydl_opts = {
            'outtmpl': os.path.join(self.settings["download_directory"], 
                                  '%(uploader)s_%(title)s.%(ext)s'),
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.settings["audio_format"],
                'preferredquality': self.settings["audio_quality"],
            }],
            'progress_hooks': [self.progress_hook],
            'no_warnings': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"🎵 Starting audio extraction from: {url}")
                ydl.download([url])
                return True
        except Exception as e:
            print(f"❌ Error extracting audio: {str(e)}")
            return False
    
    def clear_screen(self):
        """Clear the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_main_menu(self):
        """Display the main menu."""
        print("📷 Instagram Video Downloader")
        print("=" * 50)
        print()
        print("📋 Main Menu:")
        print("1. Download videos")
        print("2. Settings")
        print("3. Exit")
        print()
    
    def display_download_menu(self):
        """Display the download submenu."""
        print("📥 Download Options:")
        print("=" * 50)
        print()
        print("1. Download video (full video file)")
        print("2. Download audio only (extract audio track from video)")
        print("3. Back to main menu")
        print()
    
    def display_settings_menu(self):
        """Display the settings menu."""
        print("⚙️  Settings:")
        print("=" * 50)
        print()
        print(f"1. Download directory: {self.settings['download_directory']}")
        print(f"2. Video quality: {self.settings['video_quality']}")
        print(f"3. Audio format: {self.settings['audio_format']}")
        print(f"4. Audio quality: {self.settings['audio_quality']} kbps")
        print("5. Back to main menu")
        print()
    
    def get_user_input(self, prompt: str, valid_options: list) -> str:
        """Get validated user input."""
        while True:
            try:
                choice = input(prompt).strip()
                if choice in valid_options:
                    return choice
                print(f"❌ Invalid option. Please choose from: {', '.join(valid_options)}")
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                sys.exit(0)
            except EOFError:
                print("\n\n👋 Goodbye!")
                sys.exit(0)
    
    def get_instagram_url(self) -> Optional[str]:
        """Get Instagram URL from user."""
        print("📎 Enter Instagram URL (or 'back' to return to menu):")
        try:
            url = input("URL: ").strip()
            if url.lower() == 'back':
                return None
            return url
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 Goodbye!")
            sys.exit(0)
    
    def handle_download_menu(self):
        """Handle download menu interactions."""
        while True:
            self.clear_screen()
            self.display_download_menu()
            
            choice = self.get_user_input("Select an option (1-3): ", ['1', '2', '3'])
            
            if choice == '3':
                break
            
            url = self.get_instagram_url()
            if url is None:
                continue
            
            print()  # Add spacing
            
            if choice == '1':
                success = self.download_video(url)
            elif choice == '2':
                success = self.download_audio(url)
            
            if success:
                print(f"\n✅ Download saved to: {self.settings['download_directory']}")
            
            input("\nPress Enter to continue...")
    
    def handle_settings_menu(self):
        """Handle settings menu interactions."""
        while True:
            self.clear_screen()
            self.display_settings_menu()
            
            choice = self.get_user_input("Select an option (1-5): ", ['1', '2', '3', '4', '5'])
            
            if choice == '5':
                break
            elif choice == '1':
                self.change_download_directory()
            elif choice == '2':
                self.change_video_quality()
            elif choice == '3':
                self.change_audio_format()
            elif choice == '4':
                self.change_audio_quality()
    
    def change_download_directory(self):
        """Change download directory setting."""
        print(f"\nCurrent directory: {self.settings['download_directory']}")
        print("Enter new download directory (or press Enter to keep current):")
        try:
            new_dir = input("Directory: ").strip()
            if new_dir:
                # Expand user path and resolve
                new_dir = str(Path(new_dir).expanduser().resolve())
                self.settings['download_directory'] = new_dir
                self.save_settings()
                print(f"✅ Download directory updated to: {new_dir}")
            input("\nPress Enter to continue...")
        except (KeyboardInterrupt, EOFError):
            pass
    
    def change_video_quality(self):
        """Change video quality setting."""
        print("\nVideo Quality Options:")
        print("1. best (highest quality)")
        print("2. worst (lowest quality)")
        print("3. best[height<=720] (720p or lower)")
        print("4. best[height<=480] (480p or lower)")
        
        quality_map = {
            '1': 'best',
            '2': 'worst', 
            '3': 'best[height<=720]',
            '4': 'best[height<=480]'
        }
        
        choice = self.get_user_input("Select quality (1-4): ", ['1', '2', '3', '4'])
        self.settings['video_quality'] = quality_map[choice]
        self.save_settings()
        print(f"✅ Video quality updated to: {quality_map[choice]}")
        input("\nPress Enter to continue...")
    
    def change_audio_format(self):
        """Change audio format setting."""
        print("\nAudio Format Options:")
        print("1. mp3")
        print("2. m4a") 
        print("3. wav")
        print("4. flac")
        
        format_map = {'1': 'mp3', '2': 'm4a', '3': 'wav', '4': 'flac'}
        
        choice = self.get_user_input("Select format (1-4): ", ['1', '2', '3', '4'])
        self.settings['audio_format'] = format_map[choice]
        self.save_settings()
        print(f"✅ Audio format updated to: {format_map[choice]}")
        input("\nPress Enter to continue...")
    
    def change_audio_quality(self):
        """Change audio quality setting."""
        print("\nAudio Quality Options:")
        print("1. 128 kbps")
        print("2. 192 kbps")
        print("3. 256 kbps")
        print("4. 320 kbps")
        
        quality_map = {'1': '128', '2': '192', '3': '256', '4': '320'}
        
        choice = self.get_user_input("Select quality (1-4): ", ['1', '2', '3', '4'])
        self.settings['audio_quality'] = quality_map[choice]
        self.save_settings()
        print(f"✅ Audio quality updated to: {quality_map[choice]} kbps")
        input("\nPress Enter to continue...")
    
    def run(self):
        """Main application loop."""
        try:
            while True:
                self.clear_screen()
                self.display_main_menu()
                
                choice = self.get_user_input("Select an option (1-3): ", ['1', '2', '3'])
                
                if choice == '1':
                    self.handle_download_menu()
                elif choice == '2':
                    self.handle_settings_menu()
                elif choice == '3':
                    print("\n👋 Thank you for using Instagram Video Downloader!")
                    break
                    
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {e}")
            print("Please report this issue if it persists.")


def main():
    """Entry point of the application."""
    print("🚀 Initializing Instagram Video Downloader...")
    
    # Check if ffmpeg is available (required for audio extraction)
    try:
        import subprocess
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️  Warning: FFmpeg not found. Audio extraction may not work.")
        print("   Install FFmpeg from: https://ffmpeg.org/download.html")
        input("   Press Enter to continue anyway...")
    
    app = InstagramDownloader()
    app.run()


if __name__ == "__main__":
    main()
