# Universal Media Downloader (Windows GUI)

A single Windows 10/11 .exe that combines YouTube, Spotify, Instagram and SoundCloud downloaders.

How to run locally (dev):
1. python -m venv .venv &amp;&amp; .venv\Scripts\activate
2. pip install -r gui\requirements.txt
3. python gui\main.py

Build Windows .exe:
1. Ensure you are on Windows with Python 3.10+
2. pip install -r gui\requirements.txt
3. pip install pyinstaller
4. Run: gui\build_windows.bat

Cookies:
- The app uses youtube/cookies.txt by default (shared between YouTube and Spotify)
- You can choose a different cookies.txt from Settings and click "Copy cookies to youtube/cookies.txt"

Spotify credentials:
- Provided via spotify/.env (SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET)
- You can override and Save from Settings; it updates spotify/.env as well