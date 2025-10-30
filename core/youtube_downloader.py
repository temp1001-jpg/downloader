"""
YouTube Downloader Core - GUI-compatible
Refactored from CLI version for GUI integration
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any, Callable


try:
    import yt_dlp
except ImportError:
    raise ImportError("yt-dlp is required. Install with: pip install yt-dlp")


class YouTubeDownloader:
    """YouTube downloader with GUI callback support"""

    def __init__(self, output_dir: str = "downloads", cookies=None, verbose: bool = False):
        """
        Initialize YouTube downloader

        Args:
            output_dir: Directory to save downloads
            cookies: Cookie string or file path from cookie_manager
            verbose: Enable verbose logging
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.verbose = verbose
        self.cookies_file = cookies  # Cookie file path from cookie_manager
        self.download_history = []

    def validate_url(self, url: str) -> bool:
        """
        Validate YouTube URL

        Args:
            url: YouTube URL to validate

        Returns:
            True if valid YouTube URL, False otherwise
        """
        if not url or len(url) < 10:
            return False

        # Pre-compiled patterns for better performance
        if not hasattr(self, '_url_patterns'):
            self._url_patterns = [
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?youtu\.be/[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/channel/[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/user/[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/c/[\w-]+', re.IGNORECASE),
                re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/@[\w-]+', re.IGNORECASE),
            ]

        return any(pattern.match(url) for pattern in self._url_patterns)

    def detect_url_type(self, url: str) -> str:
        """
        Detect the type of YouTube URL

        Returns:
            'playlist', 'shorts', or 'video'
        """
        url_lower = url.lower()

        if 'playlist?list=' in url_lower:
            return 'playlist'
        elif '/shorts/' in url_lower:
            return 'shorts'
        else:
            return 'video'

    def get_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get video/playlist information without downloading

        Args:
            url: YouTube URL

        Returns:
            Info dict from yt-dlp or None if failed
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'socket_timeout': 30,
            'retries': 3,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            },
        }

        # Add cookies if available
        if self.cookies_file and Path(self.cookies_file).exists():
            ydl_opts['cookiefile'] = str(Path(self.cookies_file).absolute())

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            if self.verbose:
                print(f"Error extracting video info: {e}")
            return None

    def download(self, url: str, quality: str = "1080p", audio_only: bool = False,
                 progress_callback: Optional[Callable] = None) -> bool:
        """
        Download video or audio from YouTube

        Args:
            url: YouTube URL
            quality: Video quality (1080p, 720p, 480p, 360p, Best, Worst)
            audio_only: Extract audio only (MP3 320kbps)
            progress_callback: Function(dict) called with progress updates
                              dict contains: 'status', 'downloaded_bytes', 'total_bytes', 'filename', 'eta'

        Returns:
            True if successful, False otherwise
        """
        if not self.validate_url(url):
            raise ValueError("Invalid YouTube URL")

        # Determine if playlist
        info = self.get_info(url)
        if not info:
            raise Exception("Could not retrieve video information")

        is_playlist = 'entries' in info

        # Setup download options
        ydl_opts = self._setup_ydl_opts(quality, audio_only, is_playlist, progress_callback)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except yt_dlp.DownloadError as e:
            raise Exception(f"Download error: {str(e)}")
        except Exception as e:
            raise Exception(f"Unexpected error: {str(e)}")

    def _setup_ydl_opts(self, quality: str, audio_only: bool, is_playlist: bool,
                       progress_callback: Optional[Callable]) -> Dict[str, Any]:
        """Setup yt-dlp options"""

        # Filename template
        if is_playlist:
            outtmpl = str(self.output_dir / "%(playlist)s" / "%(playlist_index)02d - %(title)s.%(ext)s")
        else:
            outtmpl = str(self.output_dir / "%(title)s.%(ext)s")

        ydl_opts = {
            'outtmpl': outtmpl,
            'retries': 3,
            'quiet': not self.verbose,
            'no_warnings': not self.verbose,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            },
            'concurrent_fragment_downloads': 8,
            'http_chunk_size': 16777216,
            'fragment_retries': 3,
            'socket_timeout': 30,
        }

        # Add progress hook if callback provided
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]

        # Add cookies if available
        if self.cookies_file and Path(self.cookies_file).exists():
            ydl_opts['cookiefile'] = str(Path(self.cookies_file).absolute())

        # Format selection
        if audio_only:
            ydl_opts['format'] = 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        else:
            if quality.lower() == "best":
                ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            elif quality.lower() == "worst":
                ydl_opts['format'] = 'worst[ext=mp4]/worst'
            elif quality.endswith('p'):
                height = quality[:-1]
                ydl_opts['format'] = (
                    f'bestvideo[height>={height}][height<={int(height)+100}]+bestaudio/'
                    f'bestvideo[height={height}]+bestaudio/'
                    f'bestvideo[height<={height}]+bestaudio/'
                    f'best[height>={height}][height<={int(height)+100}]/'
                    f'best[height={height}]/'
                    f'best[height<={height}]/'
                    f'best'
                )

        return ydl_opts
