# All-in-One Media Downloader

A unified GUI application for downloading media from YouTube, Spotify, Instagram, and SoundCloud with automatic browser cookie extraction for authentication.

## Features

- **Unified GUI** - Single application with sidebar navigation for all platforms
- **Automatic Cookie Extraction** - Automatically extracts cookies from your browsers for authentication
- **Multiple Platforms**:
  - YouTube (videos, playlists, shorts, audio)
  - Spotify (tracks, playlists)
  - Instagram (posts, reels, stories)
  - SoundCloud (tracks, playlists)
- **Quality Selection** - Choose video/audio quality for downloads
- **Progress Tracking** - Real-time download progress bars
- **Modern UI** - Clean, dark/light theme support

## Installation

1. **Install Python dependencies:**
   ```bash
   cd downloader
   pip install -r requirements.txt
   ```

2. **Install FFmpeg** (required for audio conversion):
   - **Windows**: Download from https://ffmpeg.org/download.html
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` or `sudo yum install ffmpeg`

3. **Set up Spotify API credentials** (for Spotify downloads):
   - Create an app at https://developer.spotify.com/dashboard
   - Get your Client ID and Client Secret
   - Create a `.env` file in the `downloader` directory:
     ```
     SPOTIFY_CLIENT_ID=your_client_id_here
     SPOTIFY_CLIENT_SECRET=your_client_secret_here
     ```

## Usage

### Run the Application

```bash
cd downloader
python main.py
```

Or make it executable and run directly:
```bash
chmod +x main.py
./main.py
```

### Using the GUI

1. **Select a platform** from the sidebar (YouTube, Spotify, Instagram, SoundCloud)
2. **Enter the URL** of the content you want to download
3. **Choose quality/format** options as needed
4. **Click Download** and wait for completion
5. **Files are saved** to the downloads directory (default: `./downloads`)

### Cookie Management

The app automatically extracts cookies from your browsers on startup. This allows downloading:
- Age-restricted YouTube videos
- Private Instagram content
- Content requiring authentication

**Supported browsers:**
- Google Chrome
- Mozilla Firefox
- Microsoft Edge
- Safari (macOS)
- Brave, Opera, Vivaldi, Chromium

**To refresh cookies manually:**
- Click the "Refresh Cookies" button in the sidebar
- Useful if you've logged out/in or cookies have expired

### Settings

Click the "Settings" button in the sidebar to configure:
- Download directory
- Theme (dark/light)
- Other preferences

## Platform-Specific Notes

### YouTube
- Supports videos, playlists, and YouTube Shorts
- Quality options: 1080p, 720p, 480p, 360p, Best, Worst
- Audio-only option extracts MP3 at 320kbps
- Automatic cookie authentication for restricted content

### Spotify
- Requires API credentials (see Installation step 3)
- Supports individual tracks and playlists
- Audio formats: MP3, FLAC
- Quality options: Low, Medium, High
- Searches YouTube for audio (does not use Spotify streaming)

### Instagram
- Supports posts, reels, IGTV, and stories
- Video or audio-only modes
- Quality selection available
- Requires cookies for best results

### SoundCloud
- Supports tracks and playlists
- Audio formats: MP3, M4A, WAV
- Quality options: Best, 192 kbps, 128 kbps
- Includes metadata and artwork

## Troubleshooting

### "Could not load cookies"
- Make sure you're logged into the service in your browser
- Try the "Refresh Cookies" button
- Some browsers may be locked (close them and try again)

### "Spotify API credentials not found"
- Create a `.env` file with your Spotify API credentials
- See Installation step 3 above

### "FFmpeg not found"
- Audio extraction requires FFmpeg
- Install FFmpeg for your operating system

### Downloads failing
- Check your internet connection
- Verify the URL is correct and accessible
- Try refreshing cookies
- Some content may be geo-restricted or require premium accounts

## File Structure

```
downloader/
  ├── main.py                 # Main entry point
  ├── config.json            # Configuration file
  ├── requirements.txt       # Python dependencies
  ├── gui/                   # GUI components
  │   ├── main_window.py     # Main window with sidebar
  │   ├── youtube_panel.py   # YouTube panel
  │   ├── spotify_panel.py   # Spotify panel
  │   ├── instagram_panel.py # Instagram panel
  │   ├── soundcloud_panel.py # SoundCloud panel
  │   └── cookie_manager.py  # Cookie extraction
  ├── core/                  # Core download logic
  │   ├── youtube_downloader.py
  │   ├── spotify_downloader.py
  │   ├── instagram_downloader.py
  │   └── soundcloud_downloader.py
  └── downloads/             # Default download directory
```

## License

This is a personal project for educational purposes. Respect copyright laws and terms of service for each platform.

## Credits

Built using:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Universal video downloader
- [spotipy](https://github.com/plamere/spotipy) - Spotify API client
- [browser-cookie3](https://github.com/borisbabic/browser_cookie3) - Browser cookie extraction
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern GUI framework
