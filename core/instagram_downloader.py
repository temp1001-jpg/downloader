"""
Instagram Downloader Core - GUI-compatible
Refactored from CLI version for GUI integration
"""

import re
from pathlib import Path
from typing import Optional, Callable

try:
    import yt_dlp
except ImportError:
    raise ImportError("yt-dlp is required. Install with: pip install yt-dlp")


class InstagramDownloader:
    """Instagram downloader with GUI callback support"""

    def __init__(self, output_dir: str = "downloads", cookies=None, quality: str = "best",
                 audio_format: str = "mp3", audio_quality: str = "192"):
        """
        Initialize Instagram downloader

        Args:
            output_dir: Directory to save downloads
            cookies: Cookie file path from cookie_manager
            quality: Video quality (best, 720p, 480p, worst)
            audio_format: Audio format for audio-only mode (mp3, m4a, wav, flac)
            audio_quality: Audio quality in kbps (128, 192, 256, 320)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.cookies_file = cookies
        self.quality = quality
        self.audio_format = audio_format
        self.audio_quality = audio_quality

    def validate_url(self, url: str) -> bool:
        """
        Validate Instagram URL

        Returns:
            True if valid Instagram URL, False otherwise
        """
        instagram_patterns = [
            r'https?://(?:www\.)?instagram\.com/p/[A-Za-z0-9_-]+',
            r'https?://(?:www\.)?instagram\.com/reel/[A-Za-z0-9_-]+',
            r'https?://(?:www\.)?instagram\.com/tv/[A-Za-z0-9_-]+',
            r'https?://(?:www\.)?instagram\.com/stories/[A-Za-z0-9_.-]+/[0-9]+',
        ]

        return any(re.match(pattern, url.strip()) for pattern in instagram_patterns)

    def download(self, url: str, audio_only: bool = False,
                 progress_callback: Optional[Callable] = None) -> bool:
        """
        Download video or audio from Instagram

        Args:
            url: Instagram URL
            audio_only: If True, extract audio only
            progress_callback: Function(dict) called with progress updates
                              dict contains: 'status', 'downloaded_bytes', 'total_bytes', 'filename'

        Returns:
            True if successful, False otherwise
        """
        if not self.validate_url(url):
            raise ValueError("Invalid Instagram URL")

        # Setup yt-dlp options
        ydl_opts = {
            'outtmpl': str(self.output_dir / '%(uploader)s_%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }

        # Add progress hook if callback provided
        if progress_callback:
            ydl_opts['progress_hooks'] = [progress_callback]

        # Add cookies if available
        if self.cookies_file and Path(self.cookies_file).exists():
            ydl_opts['cookiefile'] = str(Path(self.cookies_file).absolute())

        # Setup format based on mode
        if audio_only:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['writethumbnail'] = True
            ydl_opts['postprocessors'] = [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self.audio_format,
                    'preferredquality': self.audio_quality,
                },
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                },
                {
                    'key': 'EmbedThumbnail',
                    'already_have_thumbnail': False,
                },
            ]
        else:
            # Video mode
            if self.quality == "best":
                ydl_opts['format'] = 'best'
            elif self.quality == "worst":
                ydl_opts['format'] = 'worst'
            elif self.quality == "720p":
                ydl_opts['format'] = 'best[height<=720]'
            elif self.quality == "480p":
                ydl_opts['format'] = 'best[height<=480]'
            else:
                ydl_opts['format'] = 'best'

            # Add metadata and thumbnail for video mode too
            ydl_opts['writethumbnail'] = True
            ydl_opts['postprocessors'] = [
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                },
                {
                    'key': 'EmbedThumbnail',
                    'already_have_thumbnail': False,
                },
            ]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            raise Exception(f"Download failed: {e}")

    def get_info(self, url: str) -> Optional[dict]:
        """
        Get video information without downloading

        Returns:
            Info dict or None if failed
        """
        if not self.validate_url(url):
            return None

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }

        if self.cookies_file and Path(self.cookies_file).exists():
            ydl_opts['cookiefile'] = str(Path(self.cookies_file).absolute())

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception:
            return None
