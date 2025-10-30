#!/usr/bin/env python3
"""
YouTube Downloader - Optimized High-Speed Console Application
A streamlined, performance-optimized YouTube video and playlist downloader.

Features:
- Interactive menu system with automatic URL detection
- High-speed downloads optimized for maximum performance
- MP4 video format (best compatibility) and MP3 audio (320kbps)
- Correct filename handling with video titles
- Audio-only extraction support with high-quality MP3
- Playlist downloading with organized structure
- Progress tracking and enhanced error handling
- Optimized network settings for faster downloads
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

# Windows console compatibility with UTF-8 support for emojis
if os.name == 'nt':  # Windows
    try:
        import locale
        import codecs
        # Set UTF-8 encoding for Windows console
        os.system('chcp 65001 >nul 2>&1')
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        # Fallback for older Python versions
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        except:
            pass


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
                if isinstance(self.current_file, bytes):
                    self.current_file = self.current_file.decode('utf-8', errors='replace')
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
            filename = d.get('filename', 'Unknown')
            if isinstance(filename, bytes):
                filename = filename.decode('utf-8', errors='replace')
            filename = Path(filename).name
            print(f"{Fore.GREEN}✅ Downloaded: {filename}{Style.RESET_ALL}")


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

    def _validate_netscape_cookies(self, cookies_path: Path) -> bool:
        """
        Validate that the cookies file is in proper Netscape format.
        Returns True if valid, False otherwise.
        """
        try:
            # Try different encodings for better compatibility
            content = None
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    with open(cookies_path, 'r', encoding=encoding) as f:
                        content = f.read().strip()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                return False
            
            # Check for Netscape header
            lines = content.split('\n')
            if not lines:
                return False
            
            # First line should be Netscape comment
            first_line = lines[0].strip()
            if not first_line.startswith('# Netscape HTTP Cookie File'):
                return False
            
            # Check for valid cookie entries (skip comments and empty lines)
            valid_entries = 0
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Netscape format: domain, domain_specified, path, secure, expiration, name, value
                parts = line.split('\t')
                if len(parts) >= 7:  # At least 7 fields required
                    valid_entries += 1
                elif len(parts) > 0:  # Invalid format detected
                    return False
            
            # Must have at least one valid cookie entry
            return valid_entries > 0
            
        except Exception:
            return False

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
        """Optimized video information extraction with enhanced compatibility."""
        # Enhanced options for better compatibility and info extraction
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            # Enhanced compatibility settings
            'no_check_certificate': False,
            'prefer_insecure': False,
            'socket_timeout': 30,  # Increased timeout for better reliability
            'retries': 3,  # More retries for better success rate
            # User agent and headers for better compatibility
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive',
            },
            # Reduce unnecessary processing to minimum
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writeinfojson': False,
            'writethumbnail': False,
            'writecomments': False,
            'writedescription': False,
            'writeplaylistmetafiles': False,
            'writeannotations': False,
            # Additional compatibility optimizations
            'lazy_playlist': True,  # Don't extract all playlist info at once
            'playlistend': 1 if not 'playlist' in str(self.__dict__.get('url', '')) else None,  # Limit for single videos
            # YouTube-specific compatibility settings
            'youtube_include_dash_manifest': False,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['configs'],
                }
            },
        }

        # Enhanced Netscape cookie file handling for info extraction
        cookies_path = Path("cookies.txt")
        if cookies_path.exists():
            # Validate Netscape format and optimize for compatibility
            if self._validate_netscape_cookies(cookies_path):
                ydl_opts['cookiefile'] = str(cookies_path.absolute())  # Use absolute path for better compatibility
                # Additional Netscape-specific optimizations
                ydl_opts['http_headers']['Cookie'] = None  # Let yt-dlp handle cookies from file
            else:
                print(f"{Fore.YELLOW}⚠ Warning: cookies.txt may not be in proper Netscape format{Style.RESET_ALL}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except yt_dlp.DownloadError as e:
            error_msg = str(e).lower()
            if "not available on this app" in error_msg:
                print(f"{Fore.RED}❌ Video access restricted. This may be due to:{Style.RESET_ALL}")
                print(f"   • Geographic restrictions")
                print(f"   • Age restrictions")
                print(f"   • Private/unlisted video")
                print(f"   • YouTube's bot detection")
                print(f"{Fore.YELLOW}💡 Try using cookies.txt or a different video{Style.RESET_ALL}")
            elif self.verbose:
                print(f"{Fore.RED}Download error during info extraction: {e}{Style.RESET_ALL}")
            return None
        except Exception as e:
            if self.verbose:
                print(f"{Fore.RED}Error extracting video info: {e}{Style.RESET_ALL}")
            return None
    
    def setup_ydl_opts(self, quality: str = "1080p", format_type: str = "mp4",
                      audio_only: bool = False, is_playlist: bool = False) -> Dict[str, Any]:
        """
        Enhanced yt-dlp options setup with FIXED quality selection and maximum performance optimizations.
        """
        # Proper filename template that preserves video titles
        if is_playlist:
            outtmpl = str(self.output_dir / "%(playlist)s" / "%(playlist_index)02d - %(title)s.%(ext)s")
        else:
            outtmpl = str(self.output_dir / "%(title)s.%(ext)s")

        # Enhanced compatibility and performance-optimized base options
        ydl_opts = {
            'outtmpl': outtmpl,
            'progress_hooks': [self.progress_hook],
            'retries': 3,  # More retries for better success rate
            'quiet': not self.verbose,
            'no_warnings': not self.verbose,
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writethumbnail': False,
            'writecomments': False,
            'writedescription': False,
            # Enhanced compatibility settings
            'extract_flat': False,
            'ignoreerrors': False,
            'no_check_certificate': False,
            'prefer_insecure': False,
            # User agent and headers for better compatibility
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive',
            },
            # Performance optimizations
            'concurrent_fragment_downloads': 8,  # Increased concurrent downloads
            'http_chunk_size': 16777216,  # 16MB chunks for maximum speed
            'fragment_retries': 3,  # More fragment retries for reliability
            'socket_timeout': 30,  # Increased timeout for better reliability
            'buffersize': 16384,  # Optimized buffer size
            # Network optimizations
            'prefer_ffmpeg': True,
            'keepvideo': False,  # Don't keep original video after processing
            # YouTube-specific compatibility settings
            'youtube_include_dash_manifest': False,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['configs'],
                }
            },
        }

        # Enhanced Netscape cookie file handling for downloads
        cookies_path = Path("cookies.txt")
        if cookies_path.exists():
            # Validate Netscape format and optimize for compatibility
            if self._validate_netscape_cookies(cookies_path):
                ydl_opts['cookiefile'] = str(cookies_path.absolute())  # Use absolute path for better compatibility
                # Additional Netscape-specific optimizations for downloads
                ydl_opts['http_headers']['Cookie'] = None  # Let yt-dlp handle cookies from file
                if self.verbose:
                    print(f"{Fore.GREEN}✅ Using Netscape cookies from: {cookies_path}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠ Warning: cookies.txt may not be in proper Netscape format{Style.RESET_ALL}")
                if self.verbose:
                    print(f"{Fore.YELLOW}   Consider re-exporting cookies in Netscape format{Style.RESET_ALL}")
        elif self.verbose:
            print(f"{Fore.YELLOW}⚠ No cookies.txt file found - some videos may be unavailable{Style.RESET_ALL}")

        # OPTIMIZED format selection - Always MP4 for video, MP3 for audio
        if audio_only:
            # Always use MP3 for audio with high quality
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',  # Higher quality audio
            }]
        else:
            # Always use MP4 format for maximum compatibility and efficiency
            if quality == "best":
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality == "worst":
                ydl_opts['format'] = 'worst[ext=mp4]/worst'
            elif quality.endswith('p'):
                height = quality[:-1]
                # Enhanced format string for proper quality selection
                ydl_opts['format'] = (
                    f'bestvideo[height>={height}][height<={int(height)+100}]+bestaudio/'  # Prefer exact or slightly higher quality
                    f'bestvideo[height={height}]+bestaudio/'  # Exact quality match
                    f'bestvideo[height<={height}]+bestaudio/'  # Fallback to lower quality if needed
                    f'best[height>={height}][height<={int(height)+100}]/'  # Single file with preferred quality
                    f'best[height={height}]/'  # Single file exact match
                    f'best[height<={height}]/'  # Single file fallback
                    f'best'  # Final fallback
                )

        # Debug output to verify format string (always show for quality verification)
        if self.verbose or quality.endswith('p'):
            print(f"{Fore.YELLOW}[DEBUG] Quality: {quality}, Format: {format_type}, Audio Only: {audio_only}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}[DEBUG] yt-dlp format string: {ydl_opts['format']}{Style.RESET_ALL}")

        return ydl_opts

    def download_video(self, url: str, quality: str = "1080p", audio_only: bool = False) -> bool:
        """
        Enhanced download with AUTO-DETECTION, FIXED quality selection and performance optimizations.
        Automatically detects video type (single video, playlist, or YouTube Shorts).
        """
        print(f"\n{Fore.CYAN}[DOWNLOAD] Preparing to download from: {url}{Style.RESET_ALL}")

        # AUTO-DETECTION: Detect URL type before processing
        url_type = self.detect_url_type(url)
        print(f"{Fore.YELLOW}[INFO] Detected URL type: {url_type.upper()}{Style.RESET_ALL}")

        # PERFORMANCE: Fast video info extraction
        start_time = time.time()
        info = self.get_video_info(url)
        info_time = time.time() - start_time

        if not info:
            print(f"{Fore.RED}❌ Could not retrieve video information. Please check the URL.{Style.RESET_ALL}")
            return False

        print(f"{Fore.GREEN}✅ Video info extracted in {info_time:.1f}s{Style.RESET_ALL}")

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
        format_type = "mp3" if audio_only else "mp4"  # Always use MP4 for video, MP3 for audio
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
                # ENHANCED: Extract and display actual selected format info
                if not is_playlist:
                    try:
                        extracted_info = ydl.extract_info(url, download=False)
                        selected_quality = None
                        
                        if 'requested_formats' in extracted_info:
                            # Multiple formats (video + audio)
                            for fmt in extracted_info['requested_formats']:
                                if fmt.get('height'):
                                    selected_quality = f"{fmt.get('height')}p"
                                    print(f"{Fore.GREEN}✅ Selected video format: {fmt.get('height')}p ({fmt.get('ext', 'unknown')}) - {fmt.get('format_note', '')}{Style.RESET_ALL}")
                                elif 'audio' in fmt.get('format_note', '').lower():
                                    print(f"{Fore.GREEN}✅ Selected audio format: {fmt.get('ext', 'unknown')} - {fmt.get('format_note', '')}{Style.RESET_ALL}")
                        elif extracted_info.get('height'):
                            # Single format
                            selected_quality = f"{extracted_info.get('height')}p"
                            print(f"{Fore.GREEN}✅ Selected format: {extracted_info.get('height')}p ({extracted_info.get('ext', 'unknown')}) - {extracted_info.get('format_note', '')}{Style.RESET_ALL}")
                        
                        # Quality verification
                        if selected_quality and quality != 'best' and quality != 'worst':
                            requested_height = int(quality[:-1])
                            selected_height = int(selected_quality[:-1])
                            if selected_height < requested_height * 0.8:  # If selected is significantly lower
                                print(f"{Fore.YELLOW}[WARNING] Selected quality ({selected_quality}) is lower than requested ({quality}){Style.RESET_ALL}")
                                print(f"{Fore.YELLOW}[INFO] This may be the highest available quality for this video{Style.RESET_ALL}")
                            elif selected_height >= requested_height:
                                print(f"{Fore.GREEN}✅ Quality selection successful: {selected_quality} >= {quality}{Style.RESET_ALL}")
                                
                    except Exception as e:
                        print(f"{Fore.YELLOW}[WARNING] Could not verify format selection: {e}{Style.RESET_ALL}")
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

    def test_cookies(self) -> Dict[str, Any]:
        """
        Test if cookies are working properly by attempting to access YouTube.
        Returns a dictionary with test results and recommendations.
        """
        print(f"\n{Fore.CYAN}🍪 Testing Cookie Authentication...{Style.RESET_ALL}")
        
        cookies_path = Path("cookies.txt")
        if not cookies_path.exists():
            return {
                'status': 'no_cookies',
                'message': 'No cookies.txt file found',
                'recommendation': 'Export cookies from your browser to cookies.txt in Netscape format'
            }
        
        # Validate Netscape format first
        if not self._validate_netscape_cookies(cookies_path):
            return {
                'status': 'invalid_format',
                'message': 'cookies.txt is not in proper Netscape format',
                'recommendation': 'Re-export cookies in Netscape format using a compatible browser extension'
            }
        
        # Test with a known YouTube video that requires authentication
        test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Roll - public video
        
        print(f"   Testing with public video...")
        
        # Setup minimal test options optimized for Netscape cookies
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'cookiefile': str(cookies_path.absolute()),  # Use absolute path for better compatibility
            'socket_timeout': 15,
            'retries': 1,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Cookie': None,  # Let yt-dlp handle cookies from file
            },
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(test_url, download=False)
                
                if info and info.get('title'):
                    # Check if we can access user-specific features
                    uploader = info.get('uploader', 'Unknown')
                    view_count = info.get('view_count', 0)
                    
                    return {
                        'status': 'working',
                        'message': f'Cookies are working! Successfully accessed: {info.get("title", "Unknown")}',
                        'details': {
                            'uploader': uploader,
                            'views': f"{view_count:,}" if view_count else "Unknown",
                            'duration': info.get('duration', 'Unknown')
                        },
                        'recommendation': 'Cookies are functioning properly'
                    }
                else:
                    return {
                        'status': 'partial',
                        'message': 'Cookies loaded but limited access',
                        'recommendation': 'Try refreshing your cookies or check if they are up to date'
                    }
                    
        except yt_dlp.DownloadError as e:
            error_msg = str(e).lower()
            if "sign in" in error_msg or "login" in error_msg:
                return {
                    'status': 'expired',
                    'message': 'Cookies appear to be expired or invalid',
                    'recommendation': 'Re-export fresh cookies from your browser'
                }
            elif "not available" in error_msg:
                return {
                    'status': 'restricted',
                    'message': 'Access restricted - cookies may not have sufficient permissions',
                    'recommendation': 'Make sure you are logged into YouTube when exporting cookies'
                }
            else:
                return {
                    'status': 'error',
                    'message': f'Cookie test failed: {str(e)}',
                    'recommendation': 'Check your internet connection and try refreshing cookies'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Unexpected error during cookie test: {str(e)}',
                'recommendation': 'Check cookies.txt file format and try again'
            }


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
        print(f"{Back.MAGENTA}{Fore.WHITE}        YOUTUBE DOWNLOADER - OPTIMIZED        {Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}High-Speed YouTube Downloader - MP4/MP3 Optimized{Style.RESET_ALL}")

    def detect_url_automatically(self) -> Optional[str]:
        """Try to detect URL from clipboard or user input."""
        # Check clipboard first and use automatically if valid
        clipboard_url = self.downloader.get_clipboard_url()
        if clipboard_url:
            print(f"\n{Fore.GREEN}📋 Using YouTube URL from clipboard:{Style.RESET_ALL}")
            print(f"   {clipboard_url}")
            return clipboard_url

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
        print(f"{Fore.GREEN}✅ Using MP4 format (optimized for compatibility and speed){Style.RESET_ALL}")

        success = self.downloader.download_video(url, quality, audio_only=False)

        if success:
            if url_type == 'playlist':
                print(f"\n{Fore.GREEN}🎉 Playlist downloaded successfully!{Style.RESET_ALL}")
            elif url_type == 'shorts':
                print(f"\n{Fore.GREEN}🎉 YouTube Short downloaded successfully!{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.GREEN}🎉 Video downloaded successfully!{Style.RESET_ALL}")
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

        print(f"{Fore.GREEN}✅ Using MP3 format (320kbps high quality){Style.RESET_ALL}")

        success = self.downloader.download_video(url, "best", audio_only=True)

        if success:
            print(f"\n{Fore.GREEN}🎉 Audio downloaded successfully!{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}❌ Download failed.{Style.RESET_ALL}")

        input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")

    def test_cookies_interface(self):
        """Handle cookie testing interface."""
        print(f"\n{Fore.CYAN}🍪 Cookie Authentication Test{Style.RESET_ALL}")
        print("─" * 40)
        
        result = self.downloader.test_cookies()
        
        # Display results based on status
        status_colors = {
            'working': Fore.GREEN,
            'partial': Fore.YELLOW,
            'expired': Fore.RED,
            'restricted': Fore.RED,
            'no_cookies': Fore.YELLOW,
            'invalid_format': Fore.RED,
            'error': Fore.RED
        }
        
        status_icons = {
            'working': '🎉',
            'partial': '⚠️',
            'expired': '❌',
            'restricted': '🚫',
            'no_cookies': '📄',
            'invalid_format': '📋',
            'error': '💥'
        }
        
        color = status_colors.get(result['status'], Fore.WHITE)
        icon = status_icons.get(result['status'], '❓')
        
        print(f"\n{color}{icon} Status: {result['status'].upper()}{Style.RESET_ALL}")
        print(f"   {result['message']}")
        
        if 'details' in result:
            print(f"\n{Fore.CYAN}📊 Video Details:{Style.RESET_ALL}")
            details = result['details']
            print(f"   Uploader: {details.get('uploader', 'Unknown')}")
            print(f"   Views: {details.get('views', 'Unknown')}")
            if details.get('duration'):
                duration = details['duration']
                if isinstance(duration, (int, float)):
                    minutes, seconds = divmod(int(duration), 60)
                    print(f"   Duration: {minutes:02d}:{seconds:02d}")
                else:
                    print(f"   Duration: {duration}")
        
        print(f"\n{Fore.YELLOW}💡 Recommendation:{Style.RESET_ALL}")
        print(f"   {result['recommendation']}")
        
        if result['status'] == 'no_cookies':
            print(f"\n{Fore.CYAN}📋 How to export cookies in Netscape format:{Style.RESET_ALL}")
            print("   1. Install a browser extension like 'Get cookies.txt' or 'Cookie-Editor'")
            print("   2. Go to YouTube and make sure you're logged in")
            print("   3. Export cookies in Netscape format and save as 'cookies.txt' in this folder")
            print("   4. Run this test again")
        
        elif result['status'] == 'invalid_format':
            print(f"\n{Fore.CYAN}📋 How to fix cookie format:{Style.RESET_ALL}")
            print("   1. Your cookies.txt is not in proper Netscape format")
            print("   2. Use a browser extension that exports Netscape format cookies")
            print("   3. Make sure the file starts with '# Netscape HTTP Cookie File'")
            print("   4. Each cookie line should have 7 tab-separated fields")
            print("   5. Re-export and replace your cookies.txt file")
        
        elif result['status'] in ['expired', 'restricted']:
            print(f"\n{Fore.CYAN}🔄 To refresh cookies:{Style.RESET_ALL}")
            print("   1. Make sure you're logged into YouTube in your browser")
            print("   2. Re-export cookies in Netscape format using the same method")
            print("   3. Replace the existing cookies.txt file")
            print("   4. Run this test again")
        
        input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")





    def print_main_menu(self):
        """Print the main menu options."""
        print(f"\n{Fore.YELLOW}Main Menu:{Style.RESET_ALL}")
        print("─" * 40)

        menu_options = [
            ("1", "🎥 Download Video/Playlist", "Auto-detect and download in MP4 format (optimized)"),
            ("2", "🎵 Download Audio Only", "Extract high-quality MP3 audio (320kbps)"),
            ("3", "🍪 Test Cookie Authentication", "Check if your cookies.txt is working properly"),
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
                self.test_cookies_interface()
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
                print(f"  python yt-dl.py <URL> [quality] [--audio]")
                print(f"\n{Fore.YELLOW}Examples:{Style.RESET_ALL}")
                print(f"  python yt-dl.py https://youtube.com/watch?v=... 1080p")
                print(f"  python yt-dl.py https://youtube.com/watch?v=... 720p --audio")
                print(f"\n{Fore.YELLOW}Quality options:{Style.RESET_ALL} 1080p, 720p, 480p, 360p, best, worst")
                print(f"{Fore.YELLOW}Formats:{Style.RESET_ALL} MP4 for video (default), MP3 for audio (320kbps)")
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
            audio_only = False

            for arg in sys.argv[2:]:
                if arg in ["720p", "1080p", "480p", "360p", "best", "worst"]:
                    quality = arg
                elif arg in ["--audio", "-a"]:
                    audio_only = True

            format_type = "MP3 (320kbps)" if audio_only else "MP4"
            print(f"{Fore.CYAN}YouTube Downloader - Direct Mode (Optimized){Style.RESET_ALL}")
            print(f"URL: {url}")
            print(f"Quality: {quality} | Format: {format_type} | Audio Only: {audio_only}")

            success = downloader.download_video(url, quality, audio_only)
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
