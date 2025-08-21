#!/usr/bin/env python3
"""
Spotify Music Downloader
A comprehensive Python-based Spotify music downloader with CLI interface.

Features:
- Download individual tracks from Spotify URLs
- Download entire playlists from Spotify playlist URLs
- Console-based user interface (CLI) for interaction
- Proper error handling for network issues, invalid URLs, and missing tracks
- Support for MP3 and FLAC audio formats
- Metadata tagging (artist, album, title, artwork) for downloaded files
- Organized folder structure (Artist/Album/Track)
- Download progress with progress bars
- Configuration file support for default settings
- Logging for debugging and tracking downloads

Requirements:
- spotipy (pip install spotipy)
- yt-dlp (pip install yt-dlp)
- mutagen (pip install mutagen)
- requests (pip install requests)
- tqdm (pip install tqdm)

Setup:
1. Create a Spotify app at https://developer.spotify.com/dashboard
2. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables
3. Run the script and follow the prompts
"""

import os
import sys
import json
import re
import logging
import configparser
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Dict, List, Optional, Tuple
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

# Lazy imports - only import when needed to improve startup time
def lazy_import_spotify():
    """Lazy import Spotify libraries."""
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials
        return spotipy, SpotifyClientCredentials
    except ImportError as e:
        print(f"Missing Spotify dependency: {e}")
        print("Please install: pip install spotipy")
        sys.exit(1)

def lazy_import_ytdlp():
    """Lazy import yt-dlp."""
    try:
        import yt_dlp
        return yt_dlp
    except ImportError as e:
        print(f"Missing yt-dlp dependency: {e}")
        print("Please install: pip install yt-dlp")
        sys.exit(1)

def lazy_import_mutagen():
    """Lazy import mutagen libraries."""
    try:
        from mutagen.mp3 import MP3
        from mutagen.flac import FLAC
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC
        from mutagen.flac import Picture
        return MP3, FLAC, ID3, TIT2, TPE1, TALB, TDRC, APIC, Picture
    except ImportError as e:
        print(f"Missing mutagen dependency: {e}")
        print("Please install: pip install mutagen")
        sys.exit(1)

def lazy_import_requests():
    """Lazy import requests with session for connection pooling."""
    try:
        import requests
        from tqdm import tqdm
        return requests, tqdm
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install: pip install requests tqdm")
        sys.exit(1)


def load_env_file():
    """Load environment variables from .env file if it exists."""
    env_file = Path('.env')
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        os.environ[key] = value
            # Credentials loaded successfully
        except Exception as e:
            print(f"⚠️  Warning: Could not load .env file: {e}")


class SpotifyDownloader:
    """Main Spotify downloader class with CLI interface."""

    def __init__(self):
        # Load .env file first
        load_env_file()

        self.config = self.load_config()
        self.setup_logging()
        self.spotify = self.setup_spotify_client()
        self.download_dir = Path(self.config.get('download_dir', './downloads'))
        self.audio_format = self.config.get('audio_format', 'mp3')
        self.audio_quality = self.config.get('audio_quality', 'high')

        # Create download directory
        self.download_dir.mkdir(parents=True, exist_ok=True)

        # Setup yt-dlp options
        self.setup_ytdlp_options()

        # Initialize caches for performance
        self.metadata_cache = {}  # Cache for track metadata
        self.artwork_cache = {}   # Cache for downloaded artwork
        self.youtube_cache = {}   # Cache for YouTube search results
        self.failed_tracks = set()  # Track failed downloads to avoid retries
        self.completed_tracks = set()  # Track completed downloads for resume capability

        # Initialize HTTP session for connection pooling
        # Cookie file path used by yt-dlp (shared with YouTube module by default)
        self.cookie_file = Path(__file__).parent.parent / 'youtube' / 'cookies.txt'
        if not self.cookie_file.exists():
            # Fallback to local path
            self.cookie_file = Path('cookies.txt')

        self.session = None  # Lazy initialize when needed
    
    def load_config(self) -> Dict:
        """Load configuration from file or create default."""
        config_file = Path('spotify_downloader.conf')
        config = configparser.ConfigParser()
        
        # Default configuration
        defaults = {
            'download_dir': './downloads',
            'audio_format': 'mp3',  # mp3 or flac
            'audio_quality': 'high',  # low, medium, high
            'rate_limit_delay': '1.0',
            'max_retries': '3',
            'timeout': '30',
            'embed_metadata': 'true',
            'embed_artwork': 'true'
        }
        
        if config_file.exists():
            config.read(config_file)
            if 'DEFAULT' in config:
                return dict(config['DEFAULT'])
        
        # Create default config file
        config['DEFAULT'] = defaults
        with open(config_file, 'w') as f:
            config.write(f)
        
        return defaults

    def save_config(self):
        """Save current configuration to file."""
        config_file = Path('spotify_downloader.conf')
        config = configparser.ConfigParser()

        # Update config with current settings
        current_config = {
            'download_dir': str(self.download_dir),
            'audio_format': self.audio_format,
            'audio_quality': self.audio_quality,
            'rate_limit_delay': self.config.get('rate_limit_delay', '1.0'),
            'max_retries': self.config.get('max_retries', '3'),
            'timeout': self.config.get('timeout', '30'),
            'embed_metadata': self.config.get('embed_metadata', 'true'),
            'embed_artwork': self.config.get('embed_artwork', 'true')
        }

        config['DEFAULT'] = current_config

        try:
            with open(config_file, 'w') as f:
                config.write(f)
        except Exception as e:
            print(f"⚠️  Warning: Could not save configuration: {e}")

    def get_session(self):
        """Get HTTP session with connection pooling."""
        if self.session is None:
            requests, _ = lazy_import_requests()
            self.session = requests.Session()
            # Configure session for better performance
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=20,
                max_retries=3
            )
            self.session.mount('http://', adapter)
            self.session.mount('https://', adapter)
        return self.session

    def save_download_progress(self, playlist_id: str, completed_tracks: set, failed_tracks: set):
        """Save download progress for resume capability."""
        progress_file = Path(f'download_progress_{playlist_id}.json')
        try:
            progress_data = {
                'completed': list(completed_tracks),
                'failed': list(failed_tracks),
                'timestamp': time.time()
            }
            with open(progress_file, 'w') as f:
                json.dump(progress_data, f)
        except Exception as e:
            self.logger.warning(f"Could not save download progress: {e}")

    def load_download_progress(self, playlist_id: str) -> Tuple[set, set]:
        """Load download progress for resume capability."""
        progress_file = Path(f'download_progress_{playlist_id}.json')
        if not progress_file.exists():
            return set(), set()

        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)

            # Check if progress is recent (within 24 hours)
            if time.time() - progress_data.get('timestamp', 0) > 86400:
                progress_file.unlink()  # Remove old progress file
                return set(), set()

            completed = set(progress_data.get('completed', []))
            failed = set(progress_data.get('failed', []))
            return completed, failed

        except Exception as e:
            self.logger.warning(f"Could not load download progress: {e}")
            return set(), set()

    def cleanup_progress_file(self, playlist_id: str):
        """Clean up progress file after successful completion."""
        progress_file = Path(f'download_progress_{playlist_id}.json')
        try:
            if progress_file.exists():
                progress_file.unlink()
        except Exception as e:
            self.logger.warning(f"Could not cleanup progress file: {e}")
    
    def setup_logging(self):
        """Setup logging configuration - console only."""
        log_level = logging.INFO
        if self.config.get('debug', 'false').lower() == 'true':
            log_level = logging.DEBUG

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()  # Only console logging, no file
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_spotify_client(self):
        """Setup Spotify API client with lazy loading."""
        client_id = os.getenv('SPOTIFY_CLIENT_ID')
        client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

        if not client_id or not client_secret:
            print("Error: Spotify API credentials not found!")
            print("Please set the following environment variables:")
            print("- SPOTIFY_CLIENT_ID")
            print("- SPOTIFY_CLIENT_SECRET")
            print("\nGet these from: https://developer.spotify.com/dashboard")
            sys.exit(1)

        try:
            spotipy, SpotifyClientCredentials = lazy_import_spotify()
            client_credentials_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            return spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        except Exception as e:
            self.logger.error(f"Failed to setup Spotify client: {e}")
            sys.exit(1)
    
    def setup_ytdlp_options(self):
        """Setup yt-dlp options based on configuration."""
        self.ytdl_opts = {
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': self.audio_format,
            'audioquality': self.audio_quality,
            'outtmpl': str(self.download_dir / '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'retries': int(self.config.get('max_retries', 3)),
            'socket_timeout': int(self.config.get('timeout', 30)),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.audio_format,
                'preferredquality': '320' if self.audio_quality == 'high' else '192',
            }]
        }
        # Try to load cookies by default if present
        try:
            from pathlib import Path as _Path
            default_cookie = _Path(__file__).parent.parent / 'youtube' / 'cookies.txt'
            if default_cookie.exists():
                self.cookie_file = default_cookie
        except Exception:
            pass
    
    def validate_spotify_url(self, url: str) -> Tuple[str, str]:
        """Validate Spotify URL and extract type and ID."""
        patterns = {
            'track': r'spotify\.com/track/([a-zA-Z0-9]+)',
            'playlist': r'spotify\.com/playlist/([a-zA-Z0-9]+)',
            'album': r'spotify\.com/album/([a-zA-Z0-9]+)'
        }
        
        for url_type, pattern in patterns.items():
            match = re.search(pattern, url)
            if match:
                return url_type, match.group(1)
        
        raise ValueError("Invalid Spotify URL. Please provide a valid track, playlist, or album URL.")

    def search_youtube(self, query: str) -> Optional[str]:
        """Search for a track on YouTube with caching and improved efficiency."""
        # Check cache first
        cache_key = hashlib.md5(query.encode()).hexdigest()
        if cache_key in self.youtube_cache:
            return self.youtube_cache[cache_key]

        yt_dlp = lazy_import_ytdlp()

        try:
            # Try multiple search variations for better results
            search_variations = [
                f"{query}",  # Original query
                f"{query} official",  # Try with "official"
                f"{query} audio",  # Try with "audio"
                f"{query.replace(' - ', ' ')}"  # Remove dashes
            ]

            for search_query in search_variations:
                try:
                    opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'extract_flat': False,
                        'default_search': 'ytsearch3:'  # Get top 3 results for better matching
                    }
                    # Attach cookies if available
                    try:
                        from pathlib import Path as _Path
                        if getattr(self, 'cookie_file', None) and _Path(self.cookie_file).exists():
                            opts['cookiefile'] = str(self.cookie_file)
                    except Exception:
                        pass
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(f"ytsearch3:{search_query}", download=False)

                        if info and 'entries' in info and info['entries']:
                            # Filter results to find the best match
                            for entry in info['entries']:
                                if entry:
                                    title = entry.get('title', '').lower()
                                    duration = entry.get('duration', 0)

                                    # Skip very short or very long videos (likely not music)
                                    if duration and (duration < 30 or duration > 600):
                                        continue

                                    # Skip videos with certain keywords that indicate non-music content
                                    skip_keywords = ['interview', 'reaction', 'review', 'tutorial', 'live stream']
                                    if any(keyword in title for keyword in skip_keywords):
                                        continue

                                    url = entry['webpage_url']
                                    # Cache the successful result
                                    self.youtube_cache[cache_key] = url
                                    return url

                except Exception as e:
                    self.logger.debug(f"Search variation failed for '{search_query}': {e}")
                    continue

        except Exception as e:
            self.logger.error(f"YouTube search failed for '{query}': {e}")

        # Cache negative result to avoid repeated failed searches
        self.youtube_cache[cache_key] = None
        return None

    def download_audio(self, youtube_url: str, track_info: Dict) -> Optional[str]:
        """Download audio from YouTube URL."""
        try:
            # Always use flat structure - save directly to downloads folder
            output_dir = self.download_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            # Set output template
            filename = self.sanitize_filename(f"{track_info['artist']} - {track_info['name']}")
            output_template = str(output_dir / f"{filename}.%(ext)s")

            # Update yt-dlp options
            opts = self.ytdl_opts.copy()
            opts['outtmpl'] = output_template

            yt_dlp = lazy_import_ytdlp()
            # Attach cookies for restricted videos if available
            try:
                if getattr(self, 'cookie_file', None) and Path(self.cookie_file).exists():
                    opts['cookiefile'] = str(self.cookie_file)
            except Exception:
                pass
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([youtube_url])

            # Find the downloaded file
            expected_file = output_dir / f"{filename}.{self.audio_format}"
            if expected_file.exists():
                return str(expected_file)

            # Fallback: search for any audio file with similar name
            for file in output_dir.glob(f"{filename}.*"):
                if file.suffix.lower() in ['.mp3', '.flac', '.m4a', '.ogg']:
                    return str(file)

        except Exception as e:
            self.logger.error(f"Download failed for '{track_info['name']}': {e}")

        return None

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')

        # Limit length
        if len(filename) > 200:
            filename = filename[:200]

        return filename or "Unknown"

    def embed_metadata(self, file_path: str, track_info: Dict):
        """Embed metadata into audio file."""
        if self.config.get('embed_metadata', 'true').lower() != 'true':
            return

        print(f"🏷️  Embedding metadata for: {track_info.get('name', 'Unknown')}")

        try:
            if file_path.lower().endswith('.mp3'):
                self._embed_mp3_metadata(file_path, track_info)
            elif file_path.lower().endswith('.flac'):
                self._embed_flac_metadata(file_path, track_info)
            else:
                print(f"⚠️  Unsupported file format for metadata: {file_path}")
        except Exception as e:
            print(f"❌ Failed to embed metadata for {file_path}: {e}")
            self.logger.error(f"Failed to embed metadata for {file_path}: {e}")

    def _embed_mp3_metadata(self, file_path: str, track_info: Dict):
        """Embed metadata into MP3 file with lazy imports."""
        MP3, FLAC, ID3, TIT2, TPE1, TALB, TDRC, APIC, Picture = lazy_import_mutagen()

        audio = MP3(file_path, ID3=ID3)

        # Add ID3 tag if it doesn't exist
        if audio.tags is None:
            audio.add_tags()

        # Set comprehensive metadata
        audio.tags.add(TIT2(encoding=3, text=track_info['name']))  # Title
        audio.tags.add(TPE1(encoding=3, text=track_info['artist']))  # Artist
        audio.tags.add(TALB(encoding=3, text=track_info.get('album', '')))  # Album

        # Add release date/year
        if 'release_date' in track_info and track_info['release_date']:
            audio.tags.add(TDRC(encoding=3, text=track_info['release_date'][:4]))

        # Add track number if available
        if 'track_number' in track_info:
            from mutagen.id3 import TRCK
            audio.tags.add(TRCK(encoding=3, text=str(track_info['track_number'])))

        # Add genre if available
        if 'genre' in track_info:
            from mutagen.id3 import TCON
            audio.tags.add(TCON(encoding=3, text=track_info['genre']))

        # Add duration if available
        if 'duration_ms' in track_info:
            from mutagen.id3 import TLEN
            audio.tags.add(TLEN(encoding=3, text=str(track_info['duration_ms'])))

        # Save basic metadata first
        audio.save()

        # Add album artwork with verification
        if 'image_url' in track_info:
            self._add_mp3_artwork(file_path, track_info['image_url'], track_info.get('name', ''))

    def _embed_flac_metadata(self, file_path: str, track_info: Dict):
        """Embed metadata into FLAC file with lazy imports."""
        _, FLAC, _, _, _, _, _, _, _ = lazy_import_mutagen()

        audio = FLAC(file_path)

        # Set comprehensive metadata
        audio['TITLE'] = track_info['name']
        audio['ARTIST'] = track_info['artist']
        audio['ALBUM'] = track_info.get('album', '')

        # Add release date/year
        if 'release_date' in track_info and track_info['release_date']:
            audio['DATE'] = track_info['release_date'][:4]

        # Add track number if available
        if 'track_number' in track_info:
            audio['TRACKNUMBER'] = str(track_info['track_number'])

        # Add genre if available
        if 'genre' in track_info:
            audio['GENRE'] = track_info['genre']

        # Add duration if available (FLAC uses seconds, not milliseconds)
        if 'duration_ms' in track_info:
            audio['LENGTH'] = str(track_info['duration_ms'] // 1000)

        # Save basic metadata first
        audio.save()

        # Add album artwork with verification
        if 'image_url' in track_info:
            self._add_flac_artwork(file_path, track_info['image_url'], track_info.get('name', ''))

    def _download_artwork(self, image_url: str, track_name: str = "") -> Optional[bytes]:
        """Download artwork with caching and optimized HTTP requests."""
        if not image_url:
            return None

        # Check cache first
        cache_key = hashlib.md5(image_url.encode()).hexdigest()
        if cache_key in self.artwork_cache:
            return self.artwork_cache[cache_key]

        try:
            session = self.get_session()

            # Set comprehensive headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://open.spotify.com/',
                'Sec-Fetch-Dest': 'image',
                'Sec-Fetch-Mode': 'no-cors',
                'Sec-Fetch-Site': 'cross-site'
            }

            # Use session for connection pooling
            response = session.get(image_url, timeout=15, headers=headers)
            response.raise_for_status()

            content = response.content

            if len(content) == 0:
                return None

            # Quick format validation
            is_jpeg = content.startswith(b'\xff\xd8\xff')
            is_png = content.startswith(b'\x89PNG\r\n\x1a\n')
            is_webp = content.startswith(b'RIFF') and b'WEBP' in content[:12]

            if not (is_jpeg or is_png or is_webp):
                return None

            # Cache the successful download
            self.artwork_cache[cache_key] = content
            return content

        except Exception as e:
            self.logger.debug(f"Artwork download failed for {track_name}: {e}")
            return None

    def _add_mp3_artwork(self, file_path: str, image_url: str, track_name: str = ""):
        """Add artwork to MP3 file with optimized processing."""
        if not self.config.get('embed_artwork', 'true').lower() == 'true':
            return False

        artwork_data = self._download_artwork(image_url, track_name)
        if not artwork_data:
            return False

        try:
            MP3, _, ID3, _, _, _, _, APIC, _ = lazy_import_mutagen()

            # Quick file validation
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return False

            # Load and process MP3 file
            audio = MP3(file_path, ID3=ID3)

            if audio.tags is None:
                audio.add_tags()

            # Determine MIME type
            mime_type = 'image/jpeg'
            if artwork_data.startswith(b'\x89PNG'):
                mime_type = 'image/png'
            elif artwork_data.startswith(b'RIFF') and b'WEBP' in artwork_data[:12]:
                mime_type = 'image/webp'

            # Remove existing artwork and add new
            audio.tags.delall('APIC')
            audio.tags.add(APIC(
                encoding=3,
                mime=mime_type,
                type=3,
                desc='Cover',
                data=artwork_data
            ))

            # Save with compatible version
            try:
                audio.save(v2_version=3)
            except:
                audio.save(v2_version=4)

            # Quick verification
            verify_audio = MP3(file_path, ID3=ID3)
            if verify_audio.tags and verify_audio.tags.getall('APIC'):
                apic_frames = verify_audio.tags.getall('APIC')
                if apic_frames and len(apic_frames[0].data) > 0:
                    print(f"✅ Artwork embedded: {len(artwork_data)} bytes")
                    return True

            return False

        except Exception as e:
            self.logger.debug(f"MP3 artwork embedding failed for {track_name}: {e}")
            return False

    def _add_flac_artwork(self, file_path: str, image_url: str, track_name: str = ""):
        """Add artwork to FLAC file with optimized processing."""
        if not self.config.get('embed_artwork', 'true').lower() == 'true':
            return False

        artwork_data = self._download_artwork(image_url, track_name)
        if not artwork_data:
            return False

        try:
            _, FLAC, _, _, _, _, _, _, Picture = lazy_import_mutagen()

            # Quick file validation
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                return False

            # Load and process FLAC file
            audio = FLAC(file_path)

            # Determine MIME type
            mime_type = 'image/jpeg'
            if artwork_data.startswith(b'\x89PNG'):
                mime_type = 'image/png'
            elif artwork_data.startswith(b'RIFF') and b'WEBP' in artwork_data[:12]:
                mime_type = 'image/webp'

            # Clear existing and add new picture
            audio.clear_pictures()
            picture = Picture()
            picture.type = 3
            picture.desc = 'Cover'
            picture.mime = mime_type
            picture.data = artwork_data
            picture.width = 0
            picture.height = 0
            picture.depth = 24
            picture.colors = 0

            audio.add_picture(picture)
            audio.save()

            # Quick verification
            verify_audio = FLAC(file_path)
            if verify_audio.pictures and len(verify_audio.pictures) > 0:
                embedded_size = len(verify_audio.pictures[0].data)
                if embedded_size > 0:
                    print(f"✅ Artwork embedded: {len(artwork_data)} bytes")
                    return True

            return False

        except Exception as e:
            self.logger.debug(f"FLAC artwork embedding failed for {track_name}: {e}")
            return False



    def get_track_info(self, track_id: str) -> Dict:
        """Get track information from Spotify API with caching."""
        # Check cache first
        if track_id in self.metadata_cache:
            return self.metadata_cache[track_id]

        try:
            track = self.spotify.track(track_id)

            # Extract basic info
            track_info = {
                'id': track['id'],
                'name': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'release_date': track['album']['release_date'],
                'duration_ms': track['duration_ms'],
                'popularity': track['popularity'],
                'preview_url': track['preview_url'],
                'track_number': track.get('track_number', 1)
            }

            # Get the highest quality album artwork available
            if track['album']['images']:
                # Sort images by size (largest first) and get the best quality
                images = sorted(track['album']['images'], key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
                track_info['image_url'] = images[0]['url']

                # Also store alternative sizes for fallback
                track_info['image_urls'] = [img['url'] for img in images]

            # Cache the result
            self.metadata_cache[track_id] = track_info
            return track_info

        except Exception as e:
            self.logger.error(f"Failed to get track info for {track_id}: {e}")
            raise

    def get_playlist_info(self, playlist_id: str) -> Dict:
        """Get playlist information from Spotify API."""
        try:
            playlist = self.spotify.playlist(playlist_id)

            playlist_info = {
                'id': playlist['id'],
                'name': playlist['name'],
                'description': playlist['description'],
                'owner': playlist['owner']['display_name'],
                'total_tracks': playlist['tracks']['total'],
                'public': playlist['public'],
                'collaborative': playlist['collaborative']
            }

            # Get playlist image
            if playlist['images']:
                playlist_info['image_url'] = playlist['images'][0]['url']

            return playlist_info

        except Exception as e:
            self.logger.error(f"Failed to get playlist info for {playlist_id}: {e}")
            raise

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        """Get all tracks from a playlist with caching."""
        tracks = []
        try:
            results = self.spotify.playlist_tracks(playlist_id)

            while results:
                for item in results['items']:
                    if item['track'] and item['track']['type'] == 'track':
                        track = item['track']
                        track_id = track['id']

                        # Check cache first
                        if track_id in self.metadata_cache:
                            tracks.append(self.metadata_cache[track_id])
                            continue

                        track_info = {
                            'id': track_id,
                            'name': track['name'],
                            'artist': ', '.join([artist['name'] for artist in track['artists']]),
                            'album': track['album']['name'],
                            'release_date': track['album']['release_date'],
                            'duration_ms': track['duration_ms'],
                            'popularity': track['popularity'],
                            'preview_url': track['preview_url'],
                            'track_number': track.get('track_number', 1)
                        }

                        # Get the highest quality album artwork available
                        if track['album']['images']:
                            images = sorted(track['album']['images'], key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
                            track_info['image_url'] = images[0]['url']
                            track_info['image_urls'] = [img['url'] for img in images]

                        # Cache the track info
                        self.metadata_cache[track_id] = track_info
                        tracks.append(track_info)

                # Get next batch
                results = self.spotify.next(results) if results['next'] else None

        except Exception as e:
            self.logger.error(f"Failed to get playlist tracks for {playlist_id}: {e}")
            raise

        return tracks

    def download_track(self, track_id: str) -> bool:
        """Download a single track."""
        try:
            # Get track info
            track_info = self.get_track_info(track_id)

            print(f"\n📀 Track Information:")
            print(f"   Title: {track_info['name']}")
            print(f"   Artist: {track_info['artist']}")
            print(f"   Album: {track_info['album']}")
            print(f"   Duration: {self.format_duration(track_info['duration_ms'])}")

            # Start download immediately without confirmation

            # Search on YouTube
            search_query = f"{track_info['artist']} {track_info['name']}"
            print(f"\n🔍 Searching YouTube for: {search_query}")

            youtube_url = self.search_youtube(search_query)
            if not youtube_url:
                print("❌ Could not find track on YouTube")
                return False

            print(f"✅ Found: {youtube_url}")

            # Download audio
            print("⬇️  Downloading audio...")
            file_path = self.download_audio(youtube_url, track_info)

            if not file_path:
                print("❌ Download failed")
                return False

            # Embed metadata
            print("🏷️  Adding metadata...")
            self.embed_metadata(file_path, track_info)

            # Mark as completed
            self.completed_tracks.add(track_id)

            print(f"✅ Successfully downloaded: {track_info['name']}")
            print(f"   Saved to: {file_path}")

            # Reduced delay for better performance (only for single downloads)
            time.sleep(0.5)

            return True

        except Exception as e:
            self.logger.error(f"Failed to download track {track_id}: {e}")
            print(f"❌ Error downloading track: {e}")
            return False

    def download_playlist(self, playlist_id: str) -> bool:
        """Download all tracks from a playlist."""
        try:
            # Get playlist info
            playlist_info = self.get_playlist_info(playlist_id)

            print(f"\n📋 Playlist Information:")
            print(f"   Name: {playlist_info['name']}")
            print(f"   Owner: {playlist_info['owner']}")
            print(f"   Total Tracks: {playlist_info['total_tracks']}")
            print(f"   Description: {playlist_info.get('description', 'No description')[:100]}...")

            # Start download immediately without confirmation

            # Get all tracks
            print("\n📥 Fetching playlist tracks...")
            tracks = self.get_playlist_tracks(playlist_id)

            if not tracks:
                print("❌ No tracks found in playlist")
                return False

            print(f"✅ Found {len(tracks)} tracks")

            # Load previous download progress for resume capability
            completed_tracks, failed_tracks = self.load_download_progress(playlist_id)
            self.completed_tracks.update(completed_tracks)
            self.failed_tracks.update(failed_tracks)

            # Filter out already completed tracks
            remaining_tracks = [track for track in tracks if track['id'] not in self.completed_tracks]

            if len(remaining_tracks) < len(tracks):
                already_downloaded = len(tracks) - len(remaining_tracks)
                print(f"📁 Resuming download: {already_downloaded} tracks already completed")

            if not remaining_tracks:
                print("✅ All tracks already downloaded!")
                return True

            # Download remaining tracks with concurrent processing
            successful_downloads = len(self.completed_tracks)
            failed_downloads = len(self.failed_tracks)

            # Use ThreadPoolExecutor for concurrent downloads - optimized for speed
            max_workers = min(8, len(remaining_tracks))  # Increased from 3 to 8 for faster downloads

            def download_single_track(track_info):
                """Download a single track - used for concurrent processing."""
                try:
                    track_id = track_info['id']

                    # Skip if already failed
                    if track_id in self.failed_tracks:
                        return False, f"Previously failed: {track_info['name']}"

                    # Search on YouTube
                    search_query = f"{track_info['artist']} {track_info['name']}"
                    youtube_url = self.search_youtube(search_query)

                    if not youtube_url:
                        self.failed_tracks.add(track_id)
                        return False, f"Could not find on YouTube: {search_query}"

                    # Download audio
                    file_path = self.download_audio(youtube_url, track_info)

                    if file_path:
                        # Embed metadata
                        self.embed_metadata(file_path, track_info)
                        self.completed_tracks.add(track_id)
                        return True, f"Successfully downloaded: {track_info['name']}"
                    else:
                        self.failed_tracks.add(track_id)
                        return False, f"Download failed: {track_info['name']}"

                except Exception as e:
                    self.failed_tracks.add(track_info['id'])
                    return False, f"Error downloading {track_info['name']}: {e}"

            # Process downloads concurrently
            _, tqdm = lazy_import_requests()
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                with tqdm(total=len(remaining_tracks), desc="Downloading", unit="track") as pbar:
                    # Submit all download tasks
                    future_to_track = {executor.submit(download_single_track, track): track for track in remaining_tracks}

                    # Process completed downloads
                    for future in as_completed(future_to_track):
                        track = future_to_track[future]
                        pbar.set_description(f"Processing: {track['name'][:30]}...")

                        try:
                            success, message = future.result()
                            if success:
                                successful_downloads += 1
                            else:
                                failed_downloads += 1
                                self.logger.warning(message)
                        except Exception as e:
                            failed_downloads += 1
                            self.logger.error(f"Task failed for {track['name']}: {e}")

                        pbar.update(1)

                        # Save progress periodically (reduced frequency for performance)
                        if (successful_downloads + failed_downloads) % 10 == 0:
                            self.save_download_progress(playlist_id, self.completed_tracks, self.failed_tracks)

            # Save final progress
            self.save_download_progress(playlist_id, self.completed_tracks, self.failed_tracks)

            # Summary
            print(f"\n📊 Download Summary:")
            print(f"   ✅ Successful: {successful_downloads}")
            print(f"   ❌ Failed: {failed_downloads}")
            print(f"   📁 Saved to: {self.download_dir}")

            # Clean up progress file if all downloads completed successfully
            if failed_downloads == 0:
                self.cleanup_progress_file(playlist_id)
                print("🎉 All downloads completed successfully!")
            elif successful_downloads > 0:
                print("📝 Progress saved - you can resume this download later")

            return successful_downloads > 0

        except Exception as e:
            self.logger.error(f"Failed to download playlist {playlist_id}: {e}")
            print(f"❌ Error downloading playlist: {e}")
            return False

    def format_duration(self, duration_ms: int) -> str:
        """Format duration from milliseconds to MM:SS."""
        seconds = duration_ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"



    def handle_settings(self):
        """Handle settings display and modification."""
        while True:
            print("\n⚙️  Current Settings:")
            print(f"   Download Directory: {self.download_dir}")
            print(f"   Audio Format: {self.audio_format}")
            print(f"   Audio Quality: {self.audio_quality}")
            print(f"   File Organization: Flat structure (all files in downloads/)")
            print(f"   Embed Metadata: {self.config.get('embed_metadata', 'true')}")
            print(f"   Embed Artwork: {self.config.get('embed_artwork', 'true')}")
            print(f"   Rate Limit Delay: {self.config.get('rate_limit_delay', '1.0')}s")

            print("\n📝 Change Settings:")
            print("1. Download Directory")
            print("2. Audio Format (mp3/flac)")
            print("3. Audio Quality (low/medium/high)")
            print("4. Back to main menu")

            choice = input("\nSelect setting to change (1-4): ").strip()

            if choice == '1':
                new_dir = input(f"Enter new download directory [{self.download_dir}]: ").strip()
                if new_dir:
                    self.download_dir = Path(new_dir)
                    self.download_dir.mkdir(parents=True, exist_ok=True)
                    self.save_config()  # Save to file
                    print(f"✅ Download directory changed to: {self.download_dir}")

            elif choice == '2':
                print("Available formats: mp3, flac")
                new_format = input(f"Enter audio format [{self.audio_format}]: ").strip().lower()
                if new_format in ['mp3', 'flac']:
                    self.audio_format = new_format
                    self.setup_ytdlp_options()  # Update yt-dlp options
                    self.save_config()  # Save to file
                    print(f"✅ Audio format changed to: {self.audio_format}")
                elif new_format:
                    print("❌ Invalid format. Please choose 'mp3' or 'flac'")

            elif choice == '3':
                print("Available qualities: low, medium, high")
                new_quality = input(f"Enter audio quality [{self.audio_quality}]: ").strip().lower()
                if new_quality in ['low', 'medium', 'high']:
                    self.audio_quality = new_quality
                    self.setup_ytdlp_options()  # Update yt-dlp options
                    self.save_config()  # Save to file
                    print(f"✅ Audio quality changed to: {self.audio_quality}")
                elif new_quality:
                    print("❌ Invalid quality. Please choose 'low', 'medium', or 'high'")

            elif choice == '4':
                break

            else:
                print("❌ Invalid choice. Please select 1-4.")

    def run_cli(self):
        """Run the command-line interface."""
        print("🎵 Spotify Music Downloader")
        print("=" * 50)

        while True:
            print("\n📋 Main Menu:")
            print("1. Download Music")
            print("2. Settings")
            print("3. Exit")

            choice = input("\nSelect an option (1-3): ").strip()

            if choice == '1':
                self.handle_music_download()
            elif choice == '2':
                self.handle_settings()
            elif choice == '3':
                print("\n👋 Thank you for using Spotify Music Downloader!")
                break
            else:
                print("❌ Invalid choice. Please select 1-3.")

    def handle_music_download(self):
        """Handle music download - automatically detects track or playlist."""
        print("\n🎵 Music Download")
        print("-" * 20)

        url = input("Enter Spotify URL (track or playlist): ").strip()

        if not url:
            print("❌ No URL provided")
            return

        try:
            url_type, item_id = self.validate_spotify_url(url)

            if url_type == 'track':
                print("🎵 Detected: Single Track")
                self.download_track(item_id)
            elif url_type == 'playlist':
                print("📋 Detected: Playlist")
                self.download_playlist(item_id)
            elif url_type == 'album':
                print("💿 Detected: Album")
                print("⚠️  Album downloads not yet supported. Please use individual track URLs.")
            else:
                print("❌ Unsupported URL type")

        except ValueError as e:
            print(f"❌ {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
            self.logger.error(f"Music download error: {e}")


def main():
    """Main function to run the Spotify downloader."""
    try:
        downloader = SpotifyDownloader()
        downloader.run_cli()
    except KeyboardInterrupt:
        print("\n\n⏹️  Download interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
