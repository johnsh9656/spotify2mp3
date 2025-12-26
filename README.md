# spotify2mp3

A command-line tool for downloading Spotify tracks, playlists, and albums as MP3 files.

---

## Setup

Run the following in the console in the repository.

```console
pip install -r requirements.txt

spotdl --install-ffmpeg

venv/Scripts/activate
```

---

## Project Structure

### spotify_download.py

Core download logic for Spotify content:

- download_spotify_track: downloads mp3 of given spotify track link to specified path

- download_spotify_playlist: downloads mp3s of given spotify playlist link to specified path

- download_spotify_album: downloads mp3s of given spotify album link to specified path

---

## Development Iterations
Each iteration builds on the previous. This section will be updated over time.

### Iteration 1: MVP (spotDL-based)
- Console-based
- Download MP3 files to specific output folder 
- Support Spotify track, playlist, and album links
- Uses the spot-dl framework

#### Iteration 2: Minimal External Dependencies
- Automatically detect Spotify content type (track / playlist / album)
- Replace spot-dl with yt-dlp and ffmpeg
- More control over download pipeline

#### Iteration 3: Global Tool & Format Options
- Global CLI tool
- Support multiple output formats (MP3, etc., including iPod-compatible formats)
- Embed album / playlist / track artwork
- Improved metadata handling
