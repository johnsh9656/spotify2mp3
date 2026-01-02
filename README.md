# spotify2mp3

A command-line tool that converts **Spotify tracks, albums, and playlists** into locally downloaded audio files by searching Youtube and tagging metadata.

---

## Setup

```console
git clone https://github.com/johnsh9656/spotify2mp3.git
cd spotify2mp3
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt
```

Install `ffmpeg` and ensure it is on your PATH.


### Configuration

Update config.ini in the repository root:

```ini
[SpotifyCreds]
client_id = YOUR_CLIENT_ID
client_secret = YOUR_CLIENT_SECRET
username = user     # doesn't affect anything yet

[Download]
output_path = PATH_TO_DESIRED_OUTPUT_FOLDER
```

### CLI / Editable Install

```console
python -m pip install e .
```

This installs the global command:

```console
playlist-maker
```

---

## Usage

### Basic Usage

```bash
playlist-maker "<spotify-url>"
```

Supports **track**, **album**, and **playlist** URLS. Downloads the tracks from the URL as MP3 files to a new folder in the output folder specified in config.ini

### Options

**Sorting**
```bash
-keep           Keep playlist order, track number of each track is position in the given tracklist
-album          Use tracks' original album ordering, track number of each is their track number in their original album
```

**Output**
```bash
-o <path>       Override output directory
-n              Disable track number prefixes
```

**Format**
```bash
--format mp3|m4a|wav|flac
                Choose the type of audio file the media is downloaded as
```

### Example

```bash
playlist-maker "https://open.spotify.com/playlist/..." -keep -n -o "D:/Music" --format mp3
```

Downloads the playlist sorted by the tracklist order, without numbering, to `D:/Music` as MP3 files.

---

## Project Structure

spotify2mp3/
├── spotify2media/              # main Python package (installed as CLI tool)
│   ├── __init__.py             # marks spotify2media as a Python package, no functionality
│   ├── cli.py                  # CLI entry point (argparse, flags, user input handling)
│   ├── config.py               # loads and validates config.ini
│   ├── csv_io.py               # writes normalized track metadata to CSV files
│   ├── main.py                 # thin wrapper to run CLI module directly
│   ├── spotify_client.py       # Spotify API logic
│   └── youtube_handler.py      # yt-dlp + ffmpeg logic
├── config.ini                  # user configuration
├── pyproject.toml              # project metadata, dependencies, CLI entry definition
├── requirements.txt            # dependency list for non-CLI / non-editable installs
└── README.md                   # project overview, setup insturctions, usage, etc...

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
- Embed album / playlist / track artwork
- Improved metadata handling

#### Iteration 3: Global Tool & Format Options
- Global CLI tool
- Support multiple output formats (MP3, etc., including iPod-compatible formats)
- Handle lists, batches of inputs
- Handle Youtube links

---

## License

MIT  