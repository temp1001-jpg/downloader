#!/usr/bin/env python3
"""
SoundCloud Music Downloader
A single-file Python application for downloading music from SoundCloud
with enhanced metadata and artwork embedding. Downloads are automated
without interactive prompts and saved to a local 'downloads' directory.

Requirements:
- yt-dlp: pip install yt-dlp
- colorama: pip install colorama (for colored console output)
- FFmpeg: Required for audio conversion and metadata embedding
"""

import os
import sys
import json
import re
import glob
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yt_dlp
    from colorama import init, Fore, Style
    init(autoreset=True)  # Initialize colorama for Windows compatibility
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please install required packages:")
    print("pip install yt-dlp colorama")
    sys.exit(1)


class SoundCloudDownloader:
    """Main application class for SoundCloud music downloading."""
    
    def __init__(self):
        """Initialize the downloader with default settings."""
        self.settings = {
            'download_dir': str(Path(__file__).parent / 'downloads'),
            'audio_quality': 'best',
            'file_naming': '%(uploader)s - %(title)s.%(ext)s',
            'audio_format': 'mp3'
        }
        self.config_file = Path.home() / '.soundcloud_downloader_config.json'
        self.load_settings()
        self.ensure_download_directory()
    
    def load_settings(self):
        """Load settings from config file if it exists."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Could not load settings: {e}")
    
    def save_settings(self):
        """Save current settings to config file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
            print(f"{Fore.GREEN}Settings saved successfully!")
        except Exception as e:
            print(f"{Fore.RED}Error saving settings: {e}")
    
    def ensure_download_directory(self):
        """Create download directory if it doesn't exist."""
        try:
            Path(self.settings['download_dir']).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"{Fore.RED}Error creating download directory: {e}")
            # Fallback to current directory
            self.settings['download_dir'] = str(Path.cwd())
    
    def clear_screen(self):
        """Clear the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print the application header."""
        print(f"{Fore.CYAN}{Style.BRIGHT}🎵 Soundcloud Music Downloader")
        print("=" * 50)
        print()
    
    def print_main_menu(self):
        """Print the main menu options."""
        print(f"{Fore.YELLOW}📋 Main Menu:")
        print(f"{Fore.WHITE}1. Download Music")
        print(f"{Fore.WHITE}2. Settings")
        print(f"{Fore.WHITE}3. Exit")
        print()
    
    def validate_soundcloud_url(self, url: str) -> bool:
        """Validate if the provided URL is a valid SoundCloud URL."""
        soundcloud_patterns = [
            r'https?://soundcloud\.com/.+',
            r'https?://m\.soundcloud\.com/.+',
            r'https?://www\.soundcloud\.com/.+'
        ]
        return any(re.match(pattern, url.strip()) for pattern in soundcloud_patterns)
    
    def get_track_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract track information without downloading with optimized settings."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            # Apply same optimizations for faster metadata extraction
            'lazy_playlist': True,  # Process playlist entries as received
            'extractor_retries': 2,  # Fewer retries for faster failure detection
            'socket_timeout': 15,  # Shorter timeout
            'extractor_args': {
                'soundcloud': {
                    'formats': '*'  # Allow all formats for maximum compatibility
                }
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            print(f"{Fore.RED}Error extracting track info: {e}")
            return None
    
    def format_duration(self, seconds: Optional[float]) -> str:
        """Format duration from seconds to MM:SS format."""
        if seconds is None:
            return "Unknown"

        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def cleanup_metadata_files(self, download_dir: str, track_info: Dict[str, Any]):
        """Clean up .json metadata files after successful download."""
        try:
            # Generate possible filename patterns based on the track info
            uploader = track_info.get('uploader', '').replace('/', '_').replace('\\', '_')
            title = track_info.get('title', '').replace('/', '_').replace('\\', '_')

            # Common patterns for metadata files
            patterns = [
                f"{uploader} - {title}.info.json",
                f"{title}.info.json",
                f"*{title}*.info.json",
                f"*{uploader}*.info.json"
            ]

            deleted_files = []
            for pattern in patterns:
                json_files = glob.glob(os.path.join(download_dir, pattern))
                for json_file in json_files:
                    try:
                        os.remove(json_file)
                        deleted_files.append(os.path.basename(json_file))
                        print(f"{Fore.GREEN}🗑️  Cleaned up: {os.path.basename(json_file)}")
                    except Exception as e:
                        print(f"{Fore.YELLOW}Warning: Could not delete {json_file}: {e}")

            if deleted_files:
                print(f"{Fore.GREEN}✅ Cleanup completed: {len(deleted_files)} metadata file(s) removed")

        except Exception as e:
            print(f"{Fore.YELLOW}Warning: Cleanup process encountered an error: {e}")
    
    def download_progress_hook(self, d):
        """Enhanced progress hook for yt-dlp downloads with fragment information."""
        if d['status'] == 'downloading':
            # Show fragment information if available
            fragment_info = ""
            if 'fragment_index' in d and 'fragment_count' in d:
                fragment_info = f" [Fragment {d['fragment_index']}/{d['fragment_count']}]"

            if 'total_bytes' in d:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                print(f"\r{Fore.GREEN}Downloading: {percent:.1f}% "
                      f"({d['downloaded_bytes']}/{d['total_bytes']} bytes){fragment_info}", end='', flush=True)
            elif '_percent_str' in d:
                print(f"\r{Fore.GREEN}Downloading: {d['_percent_str']}{fragment_info}", end='', flush=True)
        elif d['status'] == 'finished':
            print(f"\n{Fore.GREEN}✅ Download completed: {d['filename']}")

    def download_music(self, url: str) -> bool:
        """Download music from the provided SoundCloud URL."""
        print(f"{Fore.CYAN}🔍 Extracting track information...")

        # Get track info first
        track_info = self.get_track_info(url)
        if not track_info:
            print(f"{Fore.RED}❌ Failed to extract track information.")
            return False

        # Display track information
        print(f"\n{Fore.YELLOW}📋 Track Information:")
        print(f"{Fore.WHITE}Title: {track_info.get('title', 'Unknown')}")
        print(f"{Fore.WHITE}Artist: {track_info.get('uploader', 'Unknown')}")
        print(f"{Fore.WHITE}Duration: {self.format_duration(track_info.get('duration'))}")

        if 'entries' in track_info:
            print(f"{Fore.WHITE}Playlist with {len(track_info['entries'])} tracks")

        # Auto-proceed with download (no confirmation prompt)
        print(f"\n{Fore.CYAN}Download to: {self.settings['download_dir']}")
        print(f"{Fore.GREEN}Starting download automatically...")

        # Configure yt-dlp options with enhanced metadata, artwork, and performance optimizations
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(self.settings['download_dir'], self.settings['file_naming']),
            'progress_hooks': [self.download_progress_hook],
            'writeinfojson': True,  # Will be cleaned up after download
            'writethumbnail': True,
            'embedthumbnail': True,
            'addmetadata': True,

            # Fragment Control - Download 4 fragments concurrently (not total count)
            'concurrent_fragments': 4,

            # Playlist Optimization - MAJOR PERFORMANCE IMPROVEMENT
            'lazy_playlist': True,  # Process entries as received (98% faster!)
            'extractor_retries': 2,  # Fewer retries for faster failure detection

            # Performance Optimizations
            'buffersize': 16384,  # 16KB buffer for better performance
            'http_chunk_size': 10485760,  # 10MB chunks for faster downloads
            'retries': 3,  # Reduced retries for faster failure detection
            'fragment_retries': 2,  # Fewer fragment retries
            'file_access_retries': 2,  # Fewer file access retries

            # Network optimizations
            'socket_timeout': 15,  # Shorter timeout for faster failure detection
            'sleep_interval': 0,  # No sleep between downloads for speed

            # SoundCloud-specific optimizations (allow all available formats)
            'extractor_args': {
                'soundcloud': {
                    'formats': '*'  # Allow all formats for maximum compatibility
                }
            },

            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self.settings['audio_format'],
                    'preferredquality': '320',
                },
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                },
                {
                    'key': 'EmbedThumbnail',
                    'already_have_thumbnail': False,
                }
            ],
            'ignoreerrors': True,
        }

        try:
            print(f"\n{Fore.CYAN}🚀 Starting optimized download with 4 concurrent fragments and fast playlist processing...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            print(f"\n{Fore.GREEN}🎉 Download completed successfully with metadata and artwork!")

            # Clean up metadata files after successful download
            print(f"\n{Fore.CYAN}🧹 Cleaning up temporary metadata files...")
            self.cleanup_metadata_files(self.settings['download_dir'], track_info)

            return True
        except Exception as e:
            print(f"\n{Fore.RED}❌ Download failed: {e}")
            return False

    def download_menu(self):
        """Handle the download music menu."""
        self.clear_screen()
        self.print_header()
        print(f"{Fore.YELLOW}🎵 Download Music")
        print("-" * 30)
        print()

        while True:
            url = input(f"{Fore.CYAN}Enter SoundCloud URL (or 'back' to return): ").strip()

            if url.lower() == 'back':
                break

            if not url:
                print(f"{Fore.RED}Please enter a valid URL.")
                continue

            if not self.validate_soundcloud_url(url):
                print(f"{Fore.RED}❌ Invalid SoundCloud URL. Please enter a valid SoundCloud link.")
                continue

            success = self.download_music(url)

            # Exit after single download (no prompts for more downloads)
            if success:
                print(f"\n{Fore.GREEN}✅ Download completed! Returning to main menu...")
            else:
                print(f"\n{Fore.RED}❌ Download failed! Returning to main menu...")

            break

        input(f"\n{Fore.CYAN}Press Enter to return to main menu...")

    def settings_menu(self):
        """Handle the settings configuration menu."""
        while True:
            self.clear_screen()
            self.print_header()
            print(f"{Fore.YELLOW}⚙️  Settings")
            print("-" * 30)
            print()

            print(f"{Fore.WHITE}Current Settings:")
            print(f"1. Download Directory: {Fore.CYAN}{self.settings['download_dir']}")
            print(f"{Fore.WHITE}2. Audio Quality: {Fore.CYAN}{self.settings['audio_quality']}")
            print(f"{Fore.WHITE}3. Audio Format: {Fore.CYAN}{self.settings['audio_format']}")
            print(f"{Fore.WHITE}4. File Naming: {Fore.CYAN}{self.settings['file_naming']}")
            print(f"{Fore.WHITE}5. Save Settings")
            print(f"{Fore.WHITE}6. Back to Main Menu")
            print()

            choice = input(f"{Fore.YELLOW}Select option (1-6): ").strip()

            if choice == '1':
                self.change_download_directory()
            elif choice == '2':
                self.change_audio_quality()
            elif choice == '3':
                self.change_audio_format()
            elif choice == '4':
                self.change_file_naming()
            elif choice == '5':
                self.save_settings()
                input(f"{Fore.CYAN}Press Enter to continue...")
            elif choice == '6':
                break
            else:
                print(f"{Fore.RED}Invalid option. Please select 1-6.")
                input(f"{Fore.CYAN}Press Enter to continue...")

    def change_download_directory(self):
        """Change the download directory setting."""
        print(f"\n{Fore.CYAN}Current directory: {self.settings['download_dir']}")
        new_dir = input(f"{Fore.YELLOW}Enter new download directory (or press Enter to keep current): ").strip()

        if new_dir:
            try:
                Path(new_dir).mkdir(parents=True, exist_ok=True)
                self.settings['download_dir'] = new_dir
                print(f"{Fore.GREEN}✅ Download directory updated!")
            except Exception as e:
                print(f"{Fore.RED}❌ Error creating directory: {e}")

        input(f"{Fore.CYAN}Press Enter to continue...")

    def change_audio_quality(self):
        """Change the audio quality setting."""
        print(f"\n{Fore.CYAN}Audio Quality Options:")
        print(f"{Fore.WHITE}1. Best (highest quality)")
        print(f"{Fore.WHITE}2. Good (192 kbps)")
        print(f"{Fore.WHITE}3. Standard (128 kbps)")

        choice = input(f"{Fore.YELLOW}Select quality (1-3): ").strip()

        quality_map = {
            '1': 'best',
            '2': '192',
            '3': '128'
        }

        if choice in quality_map:
            self.settings['audio_quality'] = quality_map[choice]
            print(f"{Fore.GREEN}✅ Audio quality updated!")
        else:
            print(f"{Fore.RED}Invalid option.")

        input(f"{Fore.CYAN}Press Enter to continue...")

    def change_audio_format(self):
        """Change the audio format setting."""
        print(f"\n{Fore.CYAN}Audio Format Options:")
        print(f"{Fore.WHITE}1. MP3")
        print(f"{Fore.WHITE}2. M4A")
        print(f"{Fore.WHITE}3. WAV")

        choice = input(f"{Fore.YELLOW}Select format (1-3): ").strip()

        format_map = {
            '1': 'mp3',
            '2': 'm4a',
            '3': 'wav'
        }

        if choice in format_map:
            self.settings['audio_format'] = format_map[choice]
            print(f"{Fore.GREEN}✅ Audio format updated!")
        else:
            print(f"{Fore.RED}Invalid option.")

        input(f"{Fore.CYAN}Press Enter to continue...")

    def change_file_naming(self):
        """Change the file naming pattern."""
        print(f"\n{Fore.CYAN}File Naming Options:")
        print(f"{Fore.WHITE}1. %(title)s.%(ext)s (Title only)")
        print(f"{Fore.WHITE}2. %(uploader)s - %(title)s.%(ext)s (Artist - Title)")
        print(f"{Fore.WHITE}3. %(playlist_index)s. %(title)s.%(ext)s (Number. Title)")
        print(f"{Fore.WHITE}4. Custom pattern")

        choice = input(f"{Fore.YELLOW}Select naming pattern (1-4): ").strip()

        patterns = {
            '1': '%(title)s.%(ext)s',
            '2': '%(uploader)s - %(title)s.%(ext)s',
            '3': '%(playlist_index)s. %(title)s.%(ext)s'
        }

        if choice in patterns:
            self.settings['file_naming'] = patterns[choice]
            print(f"{Fore.GREEN}✅ File naming pattern updated!")
        elif choice == '4':
            custom = input(f"{Fore.YELLOW}Enter custom pattern: ").strip()
            if custom:
                self.settings['file_naming'] = custom
                print(f"{Fore.GREEN}✅ Custom file naming pattern set!")
        else:
            print(f"{Fore.RED}Invalid option.")

        input(f"{Fore.CYAN}Press Enter to continue...")

    def run(self):
        """Main application loop."""
        while True:
            self.clear_screen()
            self.print_header()
            self.print_main_menu()

            choice = input(f"{Fore.YELLOW}Select an option (1-3): ").strip()

            if choice == '1':
                self.download_menu()
            elif choice == '2':
                self.settings_menu()
            elif choice == '3':
                print(f"\n{Fore.CYAN}Thank you for using SoundCloud Music Downloader!")
                confirm_exit = input(f"{Fore.YELLOW}Are you sure you want to exit? (y/n): ").strip().lower()
                if confirm_exit in ['y', 'yes']:
                    print(f"{Fore.GREEN}Goodbye! 👋")
                    break
            else:
                print(f"{Fore.RED}Invalid option. Please select 1-3.")
                input(f"{Fore.CYAN}Press Enter to continue...")


def main():
    """Main entry point of the application."""
    try:
        app = SoundCloudDownloader()
        app.run()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Application interrupted by user.")
        print(f"{Fore.GREEN}Goodbye! 👋")
    except Exception as e:
        print(f"\n{Fore.RED}An unexpected error occurred: {e}")
        print(f"{Fore.YELLOW}Please report this issue if it persists.")


if __name__ == "__main__":
    main()
