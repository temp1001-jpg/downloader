"""
Spotify Downloader Core - GUI-compatible
Refactored from CLI version for GUI integration
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except ImportError:
    raise ImportError("spotipy is required. Install with: pip install spotipy")

try:
    import yt_dlp
except ImportError:
    raise ImportError("yt-dlp is required. Install with: pip install yt-dlp")


class SpotifyDownloader:
    """Spotify downloader with GUI callback support"""

    def __init__(self, output_dir: str = "downloads", client_id: str = None,
                 client_secret: str = None, audio_format: str = "mp3",
                 audio_quality: str = "high"):
        """
        Initialize Spotify downloader

        Args:
            output_dir: Directory to save downloads
            client_id: Spotify API client ID
            client_secret: Spotify API client secret
            audio_format: Audio format (mp3 or flac)
            audio_quality: Audio quality (low, medium, high)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.audio_format = audio_format
        self.audio_quality = audio_quality

        # Load credentials from environment if not provided
        if not client_id:
            client_id = os.getenv('SPOTIFY_CLIENT_ID')
        if not client_secret:
            client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

        if not client_id or not client_secret:
            raise ValueError("Spotify API credentials not found. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")

        # Setup Spotify client
        try:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret
            )
            self.spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        except Exception as e:
            raise Exception(f"Failed to setup Spotify client: {e}")

    def validate_url(self, url: str) -> Tuple[str, str]:
        """
        Validate Spotify URL and extract type and ID

        Returns:
            Tuple of (type, id) where type is 'track' or 'playlist'
        """
        patterns = {
            'track': r'spotify\.com/track/([a-zA-Z0-9]+)',
            'playlist': r'spotify\.com/playlist/([a-zA-Z0-9]+)',
            'album': r'spotify\.com/album/([a-zA-Z0-9]+)'
        }

        for url_type, pattern in patterns.items():
            match = re.search(pattern, url)
            if match:
                return url_type, match.group(1)

        raise ValueError("Invalid Spotify URL")

    def get_track_info(self, track_id: str) -> Optional[Dict]:
        """
        Get track information from Spotify API

        Returns:
            Dict with track info or None if failed
        """
        try:
            track = self.spotify.track(track_id)

            track_info = {
                'id': track['id'],
                'name': track['name'],
                'artist': ', '.join([artist['name'] for artist in track['artists']]),
                'album': track['album']['name'],
                'release_date': track['album']['release_date'],
                'duration_ms': track['duration_ms'],
                'track_number': track.get('track_number', 1)
            }

            # Get album artwork
            if track['album']['images']:
                images = sorted(track['album']['images'],
                              key=lambda x: x.get('width', 0) * x.get('height', 0),
                              reverse=True)
                track_info['image_url'] = images[0]['url']

            return track_info

        except Exception as e:
            raise Exception(f"Failed to get track info: {e}")

    def get_playlist_info(self, playlist_id: str) -> Optional[Dict]:
        """Get playlist information"""
        try:
            playlist = self.spotify.playlist(playlist_id)

            playlist_info = {
                'id': playlist['id'],
                'name': playlist['name'],
                'description': playlist.get('description', ''),
                'owner': playlist['owner']['display_name'],
                'total_tracks': playlist['tracks']['total'],
            }

            return playlist_info

        except Exception as e:
            raise Exception(f"Failed to get playlist info: {e}")

    def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        """Get all tracks from a playlist"""
        tracks = []
        try:
            results = self.spotify.playlist_tracks(playlist_id)

            while results:
                for item in results['items']:
                    if item['track'] and item['track']['type'] == 'track':
                        track = item['track']
                        track_info = {
                            'id': track['id'],
                            'name': track['name'],
                            'artist': ', '.join([artist['name'] for artist in track['artists']]),
                            'album': track['album']['name'],
                            'release_date': track['album']['release_date'],
                            'duration_ms': track['duration_ms'],
                        }

                        if track['album']['images']:
                            images = sorted(track['album']['images'],
                                          key=lambda x: x.get('width', 0) * x.get('height', 0),
                                          reverse=True)
                            track_info['image_url'] = images[0]['url']

                        tracks.append(track_info)

                results = self.spotify.next(results) if results['next'] else None

        except Exception as e:
            raise Exception(f"Failed to get playlist tracks: {e}")

        return tracks

    def download(self, url: str, progress_callback: Optional[Callable] = None) -> bool:
        """
        Download track or playlist from Spotify

        Args:
            url: Spotify URL (track or playlist)
            progress_callback: Function(current, total, status, track_name) for progress updates

        Returns:
            True if successful, False otherwise
        """
        try:
            url_type, item_id = self.validate_url(url)

            if url_type == 'track':
                return self._download_track(item_id, progress_callback)
            elif url_type == 'playlist':
                return self._download_playlist(item_id, progress_callback)
            else:
                raise ValueError(f"Unsupported URL type: {url_type}")

        except Exception as e:
            raise Exception(f"Download failed: {e}")

    def _download_track(self, track_id: str, progress_callback: Optional[Callable] = None) -> bool:
        """Download a single track"""
        try:
            # Get track info
            if progress_callback:
                progress_callback(0, 1, "Fetching track info...", "")

            track_info = self.get_track_info(track_id)

            # Search YouTube
            if progress_callback:
                progress_callback(0, 1, f"Searching for {track_info['name']}...", track_info['name'])

            search_query = f"{track_info['artist']} {track_info['name']}"
            youtube_url = self._search_youtube(search_query)

            if not youtube_url:
                raise Exception("Could not find track on YouTube")

            # Download
            if progress_callback:
                progress_callback(0, 1, f"Downloading {track_info['name']}...", track_info['name'])

            filename = self._sanitize_filename(f"{track_info['artist']} - {track_info['name']}")
            output_file = self.output_dir / f"{filename}.{self.audio_format}"

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(output_file.with_suffix('.%(ext)s')),
                'quiet': True,
                'no_warnings': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': self.audio_format,
                    'preferredquality': '320' if self.audio_quality == 'high' else '192',
                }]
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])

            if progress_callback:
                progress_callback(1, 1, "Download complete!", track_info['name'])

            return True

        except Exception as e:
            raise Exception(f"Track download failed: {e}")

    def _download_playlist(self, playlist_id: str, progress_callback: Optional[Callable] = None) -> bool:
        """Download all tracks from playlist"""
        try:
            # Get playlist info
            if progress_callback:
                progress_callback(0, 1, "Fetching playlist info...", "")

            playlist_info = self.get_playlist_info(playlist_id)
            tracks = self.get_playlist_tracks(playlist_id)

            if not tracks:
                raise Exception("No tracks found in playlist")

            total = len(tracks)

            # Download each track
            for i, track_info in enumerate(tracks):
                if progress_callback:
                    progress_callback(i, total, f"Downloading {track_info['name']}...", track_info['name'])

                try:
                    # Search YouTube
                    search_query = f"{track_info['artist']} {track_info['name']}"
                    youtube_url = self._search_youtube(search_query)

                    if youtube_url:
                        filename = self._sanitize_filename(f"{track_info['artist']} - {track_info['name']}")
                        output_file = self.output_dir / f"{filename}.{self.audio_format}"

                        ydl_opts = {
                            'format': 'bestaudio/best',
                            'outtmpl': str(output_file.with_suffix('.%(ext)s')),
                            'quiet': True,
                            'no_warnings': True,
                            'postprocessors': [{
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': self.audio_format,
                                'preferredquality': '320' if self.audio_quality == 'high' else '192',
                            }]
                        }

                        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                            ydl.download([youtube_url])

                except Exception as e:
                    # Continue with next track on error
                    if progress_callback:
                        progress_callback(i, total, f"Failed: {track_info['name']}", track_info['name'])
                    continue

            if progress_callback:
                progress_callback(total, total, "Playlist download complete!", "")

            return True

        except Exception as e:
            raise Exception(f"Playlist download failed: {e}")

    def _search_youtube(self, query: str) -> Optional[str]:
        """Search for track on YouTube"""
        try:
            with yt_dlp.YoutubeDL({
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'default_search': 'ytsearch1:'
            }) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)

                if info and 'entries' in info and info['entries']:
                    return info['entries'][0]['webpage_url']

        except Exception:
            pass

        return None

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        filename = filename.strip(' .')

        if len(filename) > 200:
            filename = filename[:200]

        return filename or "Unknown"
