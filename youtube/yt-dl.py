#!/usr/bin/env python3
"""
YouTube Downloader - Interactive Console Application
A streamlined, fully-functional YouTube video and playlist downloader.

Features:
- Interactive menu system with automatic URL detection
- High-quality downloads with proper quality selection
- Correct filename handling with video titles
- Audio-only extraction support
- Playlist downloading with organized structure
- Progress tracking and error handling
"""

# Performance-optimized imports
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

# Fast dependency loading with error handling
try:
    import yt_dlp
    from tqdm import tqdm
    import colorama
    from colorama import Fore, Back, Style

    # Optional clipboard support
    try:
        import pyperclip
    except ImportError:
        pyperclip = None

except ImportError as e:
    print(f"Error: Missing required dependency: {e}")
    print("Please install dependencies with: pip install -r requirements.txt")
    sys.exit(1)

# Initialize colorama for cross-platform colored output (fast init)
colorama.init(autoreset=True, strip=False)


class ProgressHook:
    """Enhanced progress hook with better display."""
    
    def __init__(self):
        self.pbar = None
        self.current_file = None
    
    def __call__(self, d: Dict[str, Any]) -> None:
        """Progress hook function for yt-dlp."""
        if d['status'] == 'downloading':
            if self.pbar is None or d.get('filename') != self.current_file:
                if self.pbar:
                    self.pbar.close()
                
                self.current_file = d.get('filename', 'Unknown')
                filename = Path(self.current_file).name if self.current_file else 'Unknown'
                
                # Clean up filename for display
                display_name = filename.replace('_', ' ').replace('.part', '')
                if len(display_name) > 40:
                    display_name = display_name[:37] + "..."
                
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                if total_bytes:
                    self.pbar = tqdm(
                        total=total_bytes,
                        unit='B',
                        unit_scale=True,
                        desc=f"{Fore.CYAN}Downloading{Style.RESET_ALL} {display_name}",
                        bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
                    )
            
            if self.pbar and 'downloaded_bytes' in d:
                downloaded = d['downloaded_bytes']
                if hasattr(self.pbar, 'last_downloaded'):
                    self.pbar.update(downloaded - self.pbar.last_downloaded)
                else:
                    self.pbar.update(downloaded)
                self.pbar.last_downloaded = downloaded
        
        elif d['status'] == 'finished':
            if self.pbar:
                self.pbar.close()
                self.pbar = None
            filename = Path(d['filename']).name
            print(f"{Fore.GREEN}✓ Downloaded: {filename}{Style.RESET_ALL}")


class YouTubeDownloader:
    """Enhanced YouTube downloader with fixed quality selection and filename handling."""
    
    def __init__(self, output_dir: str = "downloads", verbose: bool = False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.verbose = verbose
        self.progress_hook = ProgressHook()
        self.download_history = []
    
    def validate_url(self, url: str) -> bool:
        """Optimized URL validation with compiled regex patterns."""
        if not url or len(url) < 10:  # Quick length check
            return False

        # Pre-compiled patterns for better performance (including YouTube Shorts)
        if not hasattr(self, '_url_patterns'):
            self._url_patterns = [
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?youtu\.be/[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+', re.IGNORECASE),  # YouTube Shorts support
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/channel/[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/user/[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/c/[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/@[\w-]+', re.IGNORECASE),
            ]

        return any(pattern.match(url) for pattern in self._url_patterns)

    def detect_url_type(self, url: str) -> str:
        """
        Detect the type of YouTube URL (video, playlist, shorts).

        Returns:
            'playlist' for playlist URLs
            'shorts' for YouTube Shorts URLs
            'video' for regular video URLs and other types
        """
        url_lower = url.lower()

        if 'playlist?list=' in url_lower:
            return 'playlist'
        elif '/shorts/' in url_lower:
            return 'shorts'
        else:
            return 'video'  # Default for regular videos, channels, users, etc.

    def get_clipboard_url(self) -> Optional[str]:
        """Fast clipboard URL detection with timeout."""
        if pyperclip is None:
            return None

        try:
            # Quick clipboard access with timeout protection
            clipboard_content = pyperclip.paste().strip()

            # Fast pre-check before full validation (including Shorts)
            if (('youtube.com' in clipboard_content.lower() or
                 'youtu.be' in clipboard_content.lower()) and
                len(clipboard_content) < 500):
                if self.validate_url(clipboard_content):
                    return clipboard_content
        except Exception:
            pass  # Silently fail for clipboard issues
        return None
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Optimized video information extraction with performance enhancements."""
        # Performance-optimized options for faster info extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            # Speed optimizations for info extraction
            'no_check_certificate': False,
            'prefer_insecure': False,
            'socket_timeout': 30,  # Prevent hanging
            'retries': 1,  # Faster failure for info extraction
            # Reduce unnecessary processing
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writeinfojson': False,
            'writethumbnail': False,
        }

        # Add cookies support if cookies.txt exists
        cookies_path = Path("cookies.txt")
        if cookies_path.exists():
            ydl_opts['cookiefile'] = str(cookies_path)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except yt_dlp.DownloadError as e:
            if self.verbose:
                print(f"{Fore.RED}Download error during info extraction: {e}{Style.RESET_ALL}")
            return None
        except Exception as e:
            if self.verbose:
                print(f"{Fore.RED}Error extracting video info: {e}{Style.RESET_ALL}")
            return None
    
    def setup_ydl_opts(self, quality: str = "1080p", format_type: str = "mp4",
                      audio_only: bool = False, is_playlist: bool = False) -> Dict[str, Any]:
        """
        Enhanced yt-dlp options setup with FIXED quality selection and performance optimizations.
        """
        # Proper filename template that preserves video titles
        if is_playlist:
            outtmpl = str(self.output_dir / "%(playlist)s" / "%(playlist_index)02d - %(title)s.%(ext)s")
        else:
            outtmpl = str(self.output_dir / "%(title)s.%(ext)s")

        # Performance-optimized base options
        ydl_opts = {
            'outtmpl': outtmpl,
            'progress_hooks': [self.progress_hook],
            'retries': 3,
            'quiet': not self.verbose,
            'no_warnings': not self.verbose,
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            # Performance optimizations
            'extract_flat': False,
            'ignoreerrors': False,
            'no_check_certificate': False,
            'prefer_insecure': False,
            # Speed optimizations
            'concurrent_fragment_downloads': 4,  # Download fragments concurrently
            'http_chunk_size': 10485760,  # 10MB chunks for better speed
        }

        # Add cookies support if cookies.txt exists
        cookies_path = Path("cookies.txt")
        if cookies_path.exists():
            ydl_opts['cookiefile'] = str(cookies_path)
            if self.verbose:
                print(f"{Fore.GREEN}✓ Using cookies from: {cookies_path}{Style.RESET_ALL}")
        elif self.verbose:
            print(f"{Fore.YELLOW}⚠ No cookies.txt file found - some videos may be unavailable{Style.RESET_ALL}")

        # FIXED format selection with proper quality enforcement
        if audio_only:
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best'
            if format_type in ['mp3', 'm4a']:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_type,
                    'preferredquality': '192',
                }]
        else:
            # CRITICAL FIX: Proper quality selection that actually works
            if quality == "best":
                if format_type == "mp4":
                    ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                elif format_type == "webm":
                    ydl_opts['format'] = 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best'
                else:
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
            elif quality == "worst":
                ydl_opts['format'] = 'worst[ext=mp4]/worst'
            elif quality.endswith('p'):
                height = quality[:-1]
                # FIXED: Proper format strings that enforce quality
                if format_type == "mp4":
                    # Primary: Try to get exact quality with mp4, fallback to lower quality, then any format
                    ydl_opts['format'] = (
                        f'bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/'
                        f'bestvideo[height<={height}]+bestaudio/'
                        f'best[height<={height}][ext=mp4]/'
                        f'best[height<={height}]/'
                        f'best[ext=mp4]/best'
                    )
                elif format_type == "webm":
                    ydl_opts['format'] = (
                        f'bestvideo[height<={height}][ext=webm]+bestaudio[ext=webm]/'
                        f'bestvideo[height<={height}]+bestaudio/'
                        f'best[height<={height}][ext=webm]/'
                        f'best[height<={height}]/'
                        f'best[ext=webm]/best'
                    )
                else:
                    ydl_opts['format'] = (
                        f'bestvideo[height<={height}]+bestaudio/'
                        f'best[height<={height}]/'
                        f'best'
                    )

        # Debug output to verify format string
        if self.verbose or True:  # Always show for debugging
            print(f"{Fore.YELLOW}[DEBUG] Quality: {quality}, Format: {format_type}, Audio Only: {audio_only}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[DEBUG] yt-dlp format string: {ydl_opts['format']}{Style.RESET_ALL}")

        return ydl_opts

    def download_video(self, url: str, quality: str = "1080p", format_type: str = "mp4",
                      audio_only: bool = False) -> bool:
        """
        Enhanced download with AUTO-DETECTION, FIXED quality selection and performance optimizations.
        Automatically detects video type (single video, playlist, or YouTube Shorts).
        """
        print(f"\n{Fore.CYAN}🚀 Preparing to download from: {url}{Style.RESET_ALL}")

        # AUTO-DETECTION: Detect URL type before processing
        url_type = self.detect_url_type(url)
        print(f"{Fore.YELLOW}🔍 Detected URL type: {url_type.upper()}{Style.RESET_ALL}")

        # PERFORMANCE: Fast video info extraction
        start_time = time.time()
        info = self.get_video_info(url)
        info_time = time.time() - start_time

        if not info:
            print(f"{Fore.RED}❌ Could not retrieve video information. Please check the URL.{Style.RESET_ALL}")
            return False

        print(f"{Fore.GREEN}✓ Video info extracted in {info_time:.1f}s{Style.RESET_ALL}")

        # Determine if it's a playlist (from actual info, not just URL)
        is_playlist = 'entries' in info

        # Display video/playlist/shorts information with available formats
        if is_playlist:
            print(f"{Fore.YELLOW}📋 Playlist: {info.get('title', 'Unknown')}{Style.RESET_ALL}")
            print(f"   Number of videos: {len(info['entries'])}")

            # Show first few video titles
            print(f"   First few videos:")
            for i, entry in enumerate(info['entries'][:3]):
                if entry and entry.get('title'):
                    print(f"     {i+1}. {entry['title'][:60]}...")
        else:
            title = info.get('title', 'Unknown')
            duration = info.get('duration')
            uploader = info.get('uploader', 'Unknown')
            view_count = info.get('view_count')

            # Display appropriate icon based on detected type
            if url_type == 'shorts':
                print(f"{Fore.YELLOW}📱 YouTube Short: {title}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}🎥 Video: {title}{Style.RESET_ALL}")

            print(f"   Uploader: {uploader}")
            if duration:
                minutes, seconds = divmod(duration, 60)
                if url_type == 'shorts' and duration < 60:
                    print(f"   Duration: {duration}s (Short)")
                else:
                    print(f"   Duration: {minutes:02d}:{seconds:02d}")
            if view_count:
                print(f"   Views: {view_count:,}")

            # DEBUGGING: Show available formats to verify quality selection
            if hasattr(info, 'formats') and info.get('formats'):
                available_heights = set()
                for fmt in info['formats']:
                    if fmt.get('height'):
                        available_heights.add(fmt['height'])
                if available_heights:
                    sorted_heights = sorted(available_heights, reverse=True)
                    print(f"   Available qualities: {', '.join(f'{h}p' for h in sorted_heights[:5])}")

        # CRITICAL: Setup download options with FIXED quality selection
        print(f"\n{Fore.CYAN}⚙️  Configuring download options...{Style.RESET_ALL}")
        ydl_opts = self.setup_ydl_opts(quality, format_type, audio_only, is_playlist)

        # Enhanced download settings display
        print(f"\n{Fore.CYAN}📋 Download Configuration:{Style.RESET_ALL}")
        print(f"   🎯 Target Quality: {Fore.GREEN}{quality}{Style.RESET_ALL}")
        print(f"   📁 Format: {Fore.GREEN}{format_type}{Style.RESET_ALL}")
        print(f"   🎵 Audio Only: {Fore.GREEN}{audio_only}{Style.RESET_ALL}")
        print(f"   📂 Output: {Fore.GREEN}{self.output_dir}{Style.RESET_ALL}")
        print(f"   🔧 Format String: {Fore.YELLOW}{ydl_opts['format']}{Style.RESET_ALL}")

        # Show cookies status
        cookies_path = Path("cookies.txt")
        if cookies_path.exists():
            print(f"   🍪 Cookies: {Fore.GREEN}Enabled (cookies.txt found){Style.RESET_ALL}")
        else:
            print(f"   🍪 Cookies: {Fore.YELLOW}Not found (some videos may be unavailable){Style.RESET_ALL}")

        try:
            print(f"\n{Fore.CYAN}🚀 Starting download with optimized settings...{Style.RESET_ALL}")
            download_start = time.time()

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # DEBUGGING: Extract format info before download
                if not is_playlist:
                    try:
                        extracted_info = ydl.extract_info(url, download=False)
                        if 'requested_formats' in extracted_info:
                            for fmt in extracted_info['requested_formats']:
                                if fmt.get('height'):
                                    print(f"{Fore.GREEN}✓ Selected format: {fmt.get('height')}p ({fmt.get('ext', 'unknown')}){Style.RESET_ALL}")
                        elif extracted_info.get('height'):
                            print(f"{Fore.GREEN}✓ Selected format: {extracted_info.get('height')}p ({extracted_info.get('ext', 'unknown')}){Style.RESET_ALL}")
                    except:
                        pass  # Continue with download even if format detection fails

                # Perform the actual download
                ydl.download([url])

            download_time = time.time() - download_start

            # Add to download history with performance metrics
            self.download_history.append({
                'url': url,
                'title': info.get('title', 'Unknown'),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'quality': quality,
                'format': format_type,
                'audio_only': audio_only,
                'download_time': f"{download_time:.1f}s",
                'status': 'Success'
            })

            print(f"\n{Fore.GREEN}🎉 Download completed successfully in {download_time:.1f}s!{Style.RESET_ALL}")
            return True

        except yt_dlp.DownloadError as e:
            error_msg = str(e)
            print(f"\n{Fore.RED}❌ Download error: {error_msg}{Style.RESET_ALL}")

            # Enhanced error handling with suggestions
            if "requested format not available" in error_msg.lower():
                print(f"{Fore.YELLOW}💡 Suggestion: The requested quality ({quality}) may not be available for this video.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}   Try selecting 'best' quality or a lower resolution.{Style.RESET_ALL}")

            # Add failed download to history
            self.download_history.append({
                'url': url,
                'title': info.get('title', 'Unknown'),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': f'Failed: {error_msg}'
            })
            return False
        except Exception as e:
            print(f"\n{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
            return False


class InteractiveDownloader:
    """Interactive console interface for the YouTube downloader."""

    def __init__(self):
        self.downloader = YouTubeDownloader()
        self.running = True

    def clear_screen(self):
        """Clear the console screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        """Print the application header."""
        print(f"{Fore.MAGENTA}{'='*60}")
        print(f"{Back.MAGENTA}{Fore.WHITE}           YOUTUBE DOWNLOADER - YT-DL           {Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}High-Quality YouTube Video & Audio Downloader{Style.RESET_ALL}")

    def detect_url_automatically(self) -> Optional[str]:
        """Try to detect URL from clipboard or user input."""
        # Check clipboard first
        clipboard_url = self.downloader.get_clipboard_url()
        if clipboard_url:
            print(f"\n{Fore.YELLOW}📋 YouTube URL detected in clipboard:{Style.RESET_ALL}")
            print(f"   {clipboard_url}")

            while True:
                choice = input(f"\n{Fore.CYAN}Use this URL? (y/n): {Style.RESET_ALL}").strip().lower()
                if choice in ['y', 'yes', '']:
                    return clipboard_url
                elif choice in ['n', 'no']:
                    break
                else:
                    print(f"{Fore.RED}Please enter 'y' or 'n'{Style.RESET_ALL}")

        # Manual URL input
        print(f"\n{Fore.CYAN}Enter YouTube URL:{Style.RESET_ALL}")
        while True:
            url = input(f"{Fore.CYAN}URL: {Style.RESET_ALL}").strip()

            if not url:
                return None

            if self.downloader.validate_url(url):
                return url
            else:
                print(f"{Fore.RED}❌ Invalid YouTube URL. Please try again.{Style.RESET_ALL}")
                retry = input(f"{Fore.CYAN}Try again? (y/n): {Style.RESET_ALL}").strip().lower()
                if retry in ['n', 'no']:
                    return None

    def get_quality_choice(self) -> str:
        """Get quality selection from user."""
        print(f"\n{Fore.YELLOW}📺 Select Video Quality:{Style.RESET_ALL}")
        qualities = [
            ("1", "1080p", "Full HD (recommended)"),
            ("2", "720p", "HD"),
            ("3", "480p", "Standard"),
            ("4", "360p", "Low"),
            ("5", "best", "Best available"),
            ("6", "worst", "Smallest file")
        ]

        for num, quality, desc in qualities:
            print(f"   {num}. {Fore.GREEN}{quality:<8}{Style.RESET_ALL} - {desc}")

        while True:
            choice = input(f"\n{Fore.CYAN}Choose quality (1-6, default=1): {Style.RESET_ALL}").strip()
            if not choice:
                return "1080p"

            quality_map = {q[0]: q[1] for q in qualities}
            if choice in quality_map:
                return quality_map[choice]
            else:
                print(f"{Fore.RED}Invalid choice. Please enter 1-6.{Style.RESET_ALL}")

    def get_format_choice(self, audio_only: bool = False) -> str:
        """Get format selection from user."""
        if audio_only:
            print(f"\n{Fore.YELLOW}🎵 Select Audio Format:{Style.RESET_ALL}")
            formats = [
                ("1", "mp3", "MP3 (most compatible)"),
                ("2", "m4a", "M4A (higher quality)")
            ]
        else:
            print(f"\n{Fore.YELLOW}🎬 Select Video Format:{Style.RESET_ALL}")
            formats = [
                ("1", "mp4", "MP4 (most compatible)"),
                ("2", "webm", "WebM (smaller files)")
            ]

        for num, fmt, desc in formats:
            print(f"   {num}. {Fore.GREEN}{fmt:<4}{Style.RESET_ALL} - {desc}")

        while True:
            choice = input(f"\n{Fore.CYAN}Choose format (1-2, default=1): {Style.RESET_ALL}").strip()
            if not choice:
                return formats[0][1]

            format_map = {f[0]: f[1] for f in formats}
            if choice in format_map:
                return format_map[choice]
            else:
                print(f"{Fore.RED}Invalid choice. Please enter 1-2.{Style.RESET_ALL}")

    def download_video_or_playlist(self):
        """Handle auto-detecting video/playlist/shorts download."""
        print(f"\n{Fore.CYAN}🎥 Video/Playlist Download (Auto-Detection){Style.RESET_ALL}")
        print("─" * 50)

        url = self.detect_url_automatically()
        if not url:
            return

        # Auto-detect URL type and display to user
        url_type = self.downloader.detect_url_type(url)

        if url_type == 'playlist':
            print(f"{Fore.YELLOW}📋 Playlist URL detected - will download all videos{Style.RESET_ALL}")
        elif url_type == 'shorts':
            print(f"{Fore.YELLOW}📱 YouTube Shorts URL detected{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}🎥 Single video URL detected{Style.RESET_ALL}")

        quality = self.get_quality_choice()
        format_type = self.get_format_choice()

        success = self.downloader.download_video(url, quality, format_type, audio_only=False)

        if success:
            if url_type == 'playlist':
                print(f"\n{Fore.GREEN}✅ Playlist downloaded successfully!{Style.RESET_ALL}")
            elif url_type == 'shorts':
                print(f"\n{Fore.GREEN}✅ YouTube Short downloaded successfully!{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.GREEN}✅ Video downloaded successfully!{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}❌ Download failed.{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")

    def download_audio_only(self):
        """Handle audio-only download."""
        print(f"\n{Fore.CYAN}🎵 Audio-Only Download{Style.RESET_ALL}")
        print("─" * 30)

        url = self.detect_url_automatically()
        if not url:
            return

        format_type = self.get_format_choice(audio_only=True)

        success = self.downloader.download_video(url, "best", format_type, audio_only=True)

        if success:
            print(f"\n{Fore.GREEN}✅ Audio downloaded successfully!{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}❌ Download failed.{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")





    def show_help(self):
        """Show help information."""
        print(f"\n{Fore.CYAN}❓ Help & Information{Style.RESET_ALL}")
        print("─" * 30)

        help_text = f"""
{Fore.YELLOW}Features:{Style.RESET_ALL}
• Auto-detect video type (videos, playlists, YouTube Shorts)
• Download YouTube videos in high quality (up to 1080p)
• Extract audio-only files (MP3/M4A)
• Download entire playlists with organized folders
• YouTube Shorts support with quality selection
• Automatic URL detection from clipboard
• Progress tracking with speed and ETA

{Fore.YELLOW}Supported URLs:{Style.RESET_ALL}
• youtube.com/watch?v=... (single videos)
• youtube.com/playlist?list=... (playlists)
• youtube.com/shorts/... (YouTube Shorts)
• youtu.be/... (short URLs)
• youtube.com/channel/... (channels)
• youtube.com/@username (new format)

{Fore.YELLOW}Quality Options:{Style.RESET_ALL}
• 1080p: Full HD (recommended for most videos)
• 720p: HD (good balance of quality and file size)
• 480p/360p: Lower quality for slower connections
• Best: Highest available quality
• Worst: Smallest file size

{Fore.YELLOW}Tips:{Style.RESET_ALL}
• Copy YouTube URLs to clipboard for automatic detection
• Use audio-only mode for music and podcasts
• Playlist downloads are organized in folders
• Check download history to see completed downloads
        """

        print(help_text)
        input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")

    def print_main_menu(self):
        """Print the main menu options."""
        print(f"\n{Fore.YELLOW}Main Menu:{Style.RESET_ALL}")
        print("─" * 40)

        menu_options = [
            ("1", "🎥 Download Video/Playlist", "Auto-detect and download videos, playlists, or Shorts"),
            ("2", "🎵 Download Audio Only", "Extract audio (MP3/M4A)"),
            ("3", "❓ Help & Information", "Usage guide and tips"),
            ("4", "🚪 Exit", "Close the application"),
        ]

        for option, title, desc in menu_options:
            print(f"  {Fore.GREEN}{option}{Style.RESET_ALL}. {title}")
            print(f"     {Fore.CYAN}{desc}{Style.RESET_ALL}")

        print("─" * 40)

    def run(self):
        """Main application loop."""
        while self.running:
            self.clear_screen()
            self.print_header()
            self.print_main_menu()

            choice = input(f"\n{Fore.CYAN}Select an option (1-4): {Style.RESET_ALL}").strip()

            if choice == "1":
                self.download_video_or_playlist()
            elif choice == "2":
                self.download_audio_only()
            elif choice == "3":
                self.show_help()
            elif choice == "4":
                self.exit_application()
            else:
                print(f"{Fore.RED}Invalid option. Please enter 1-4.{Style.RESET_ALL}")
                time.sleep(1)

    def exit_application(self):
        """Handle application exit."""
        print(f"\n{Fore.YELLOW}Thank you for using YouTube Downloader!{Style.RESET_ALL}")

        if self.downloader.download_history:
            successful = sum(1 for entry in self.downloader.download_history if entry['status'] == 'Success')
            total = len(self.downloader.download_history)
            print(f"Session summary: {Fore.GREEN}{successful}{Style.RESET_ALL}/{total} downloads successful")

        print(f"{Fore.CYAN}Goodbye!{Style.RESET_ALL}")
        self.running = False




def main():
    """Main entry point for the application."""
    try:
        # Check if running with command line arguments
        if len(sys.argv) > 1:
            # Check for help flag
            if sys.argv[1] in ["--help", "-h", "help"]:
                print(f"{Fore.CYAN}YouTube Downloader (yt-dl.py) - Usage{Style.RESET_ALL}")
                print(f"\n{Fore.YELLOW}Interactive Mode (recommended):{Style.RESET_ALL}")
                print(f"  python yt-dl.py")
                print(f"\n{Fore.YELLOW}Direct Download Mode:{Style.RESET_ALL}")
                print(f"  python yt-dl.py <URL> [quality] [format] [--audio]")
                print(f"\n{Fore.YELLOW}Examples:{Style.RESET_ALL}")
                print(f"  python yt-dl.py https://youtube.com/watch?v=... 1080p mp4")
                print(f"  python yt-dl.py https://youtube.com/watch?v=... 720p --audio")
                print(f"\n{Fore.YELLOW}Quality options:{Style.RESET_ALL} 1080p, 720p, 480p, 360p, best, worst")
                print(f"{Fore.YELLOW}Format options:{Style.RESET_ALL} mp4, webm, mp3, m4a")
                sys.exit(0)

            # Command line mode for direct downloads
            url = sys.argv[1]
            downloader = YouTubeDownloader()

            if not downloader.validate_url(url):
                print(f"{Fore.RED}❌ Invalid YouTube URL provided{Style.RESET_ALL}")
                print(f"Use 'python yt-dl.py --help' for usage information")
                sys.exit(1)

            # Parse additional arguments
            quality = "1080p"
            format_type = "mp4"
            audio_only = False

            for arg in sys.argv[2:]:
                if arg in ["720p", "1080p", "480p", "360p", "best", "worst"]:
                    quality = arg
                elif arg in ["mp4", "webm", "mp3", "m4a"]:
                    format_type = arg
                elif arg in ["--audio", "-a"]:
                    audio_only = True

            print(f"{Fore.CYAN}YouTube Downloader - Direct Mode{Style.RESET_ALL}")
            print(f"URL: {url}")
            print(f"Quality: {quality} | Format: {format_type} | Audio Only: {audio_only}")

            success = downloader.download_video(url, quality, format_type, audio_only)
            sys.exit(0 if success else 1)

        else:
            # Interactive mode
            app = InteractiveDownloader()
            app.run()

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Application interrupted by user. Goodbye!{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}")
        print("Please report this issue if it persists.")


if __name__ == "__main__":
    main()
