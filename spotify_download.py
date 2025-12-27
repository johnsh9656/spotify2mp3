import subprocess
import re
import os
import spotipy
import spotipy.oauth2 as oauth2
import yt_dlp
import configparser
from pathlib import Path
import csv
import time
import shutil
from yt_dlp import YoutubeDL

# settings
transcode_mp3 = True
generate_m3u = False
deepSearch = False

# windows filename safety
def safe_filename(name: str, max_len: int = 120) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name[:max_len].rstrip(' .')

SPOTIFY_RE = re.compile(r"open\.spotify\.com/(track|playlist|album)/([a-zA-Z0-9]+)", re.IGNORECASE)

def parse_spotify_url(url: str):
    m = SPOTIFY_RE.search(url)
    if not m:
        raise ValueError("Invalid Spotify URL")
    content_type = m.group(1).lower()
    spotify_id = m.group(2)
    return content_type, spotify_id

def handle_spotify_track(spotify, track_id):
    track = spotify.track(track_id)
    album = track["album"]
    track_info = {
        'title': track['name'],
        'artists': [a['name'] for a in track['artists']],
        'album': track['album']['name'],
        'duration_ms': track['duration_ms'],
        'explicit': track['explicit'],
        'spotify_id': track['id'],
        'spotify_uri': track['uri'],
        'spotify_url': track['external_urls']['spotify'],
        'isrc': track.get('external_ids', {}).get('isrc'),
        'album': {
            'spotify_id': album['id'],
            'spotify_uri': album['uri'],
            'spotify_url': album['external_urls']['spotify'],
            'title': album['name'],
            'artists': [a['name'] for a in album['artists']],
            'release_date': album.get('release_date'),
            'images': album.get('images', []),
        }
    }
    return track_info

def handle_spotify_album(spotify, album_id):
    album = spotify.album(album_id)
    album_title = album['name']

    album_artists = [a['name'] for a in album['artists']]
    release_date = album['release_date']
    total_tracks = album['total_tracks']
    images = album['images']
    album_url = album['external_urls']['spotify']

    # pagination, spotify returns max 50 trackers per request
    tracks = []
    results = spotify.album_tracks(album_id, limit=50)
    while results:
        tracks.extend(results['items'])
        results = spotify.next(results) if results['next'] else None

    album_tracks = []
    for t in tracks:
        album_tracks.append({
            'track_number': t['track_number'],
            'disc_number': t['disc_number'],
            'title': t['name'],
            'artists': [a['name'] for a in t['artists']],
            'duration_ms': t['duration_ms'],
            'explicit': t['explicit'],
            'spotify_id': t['id'],
            'spotify_url': t['external_urls']['spotify']
        })
    
    csv_path = safe_filename(f".{album_title}_tracklist.csv")
    write_tracklist_csv(csv_path, album_title, album_tracks)
    convert_playlist(csv_path, "C:/Users/harri/Documents/playlist-maker/test_output", album_title)

def write_tracklist_csv(csv_path, list_title, list_tracks):
    fieldnames = [
        "Track Name",
        "Artist Name(s)",
        "Album Name",
        "Duration (ms)",
        "Track Number",
        "Spotify Track ID",
        "Spotify Track URL",
    ]

    tracks_sorted = sorted(list_tracks, key=lambda x: (x["disc_number"], x["track_number"]))

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for t in tracks_sorted:
            w.writerow({
                "Track Name": t["title"],
                "Artist Name(s)": "; ".join(t["artists"]),
                "Album Name": list_title,
                "Duration (ms)": t["duration_ms"],
                "Track Number": t["track_number"],
                "Spotify Track ID": t["spotify_id"],
                "Spotify Track URL": t["spotify_url"],
            })

def convert_playlist(csv_path, output_path, tracklist_name):
    def normalize(text: str) -> str:
        return re.sub(r"[^\w\s]", "", text.lower())
    
    def contains_keywords_in_order(candidate_title: str, keywords: list[str]) -> bool:
        text = normalize(candidate_title)
        pos = 0
        for kw in keywords:
            idx = text.find(kw, pos)
            if idx < 0:
                return False
            pos = idx + len(kw)
        return True
    
    start_time = time.time()
    output_dir = os.path.join(output_path, safe_filename(tracklist_name))
    if os.path.exists(output_dir):
        print(f"Output directory '{output_dir}' already exists. Skipping download.")
        return
    os.makedirs(output_dir, exist_ok=True)
    last_output_dir = output_dir

    downloaded = []
    not_found_tracks = []

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ffmpeg_exe = shutil.which("ffmpeg")
        yt_dlp_exe = shutil.which("yt-dlp")
        missing = []
        if not ffmpeg_exe:
            missing.append("ffmpeg")
        if not yt_dlp_exe:
            missing.append("yt-dlp")
        if missing:
            raise EnvironmentError(f"Missing required executables: {', '.join(missing)}. Please install them and ensure they are in your system PATH.")

        rows = list(csv.DictReader(open(csv_path, newline="", encoding="utf-8")))
        total = len(rows)
        archive_file = os.path.join(output_dir, 'downloaded.txt')
        variants = ['', 'audio', 'official audio']

        def make_ydl(outtmpl: str, mp3: bool = False):
            opts = {
                "quiet": True,
                "noplaylist": True,
                "download_archive": archive_file,
                "format": "bestaudio[ext=m4a]/bestaudio/best",
                "outtmpl": outtmpl,
            }
            if mp3:
                opts["postprocessors"] = [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"},
                    {"key": "FFmpegMetadata"},
                ]
            else:
                # keep as m4a where possible (remux)
                opts["postprocessors"] = [{"key": "FFmpegVideoRemuxer", "preferedformat": "m4a"}]
            return YoutubeDL(opts)

        for i, row in enumerate(rows, start=1):
            track_name = row.get("Track Name") or 'Unknown'
            artist_names = row.get("Artist Name(s)") or 'Unknown'
            album = row.get("Album Name") or 'Unknown'

            duration_ms_str = (row.get("Duration (ms)") or "").strip()
            duration_ms = int(duration_ms_str) if duration_ms_str.isdigit() else 0
            duration_s = duration_ms / 1000 if duration_ms else None

            safe_track_name = re.sub(r"[^\w\s]", '', track_name)
            artist_primary = artist_names.split(";")[0]
            safe_artist = re.sub(r"[^\w\s]", '', artist_primary)

            run_variants = variants.copy()
            if "instrumental" in safe_track_name.lower():
                run_variants.insert(0, "instrumental")

            success = False
            
            for variant in run_variants:
                parts = [safe_track_name]
                if safe_artist and safe_artist.lower() != 'unknown': 
                    parts.append(safe_artist)
                if variant: 
                    parts.append(variant)
                q = ' '.join(parts)
                print(f"[{i}/{total}] Searching: {q}")

    

                if deepSearch:
                    #deep search
                    pass
                else:
                    # fast mode
                    search_spec = f"ytsearch1:{q}"
                    
                    file_title = safe_track_name or f"Track_{i}"
                    base = f"{i:03d} - {file_title}" + (f" - {variant}" if variant else "")                
                    outtmpl = os.path.join(output_dir, base + ".%(ext)s")

                    try:
                        ydl = make_ydl(outtmpl, mp3=transcode_mp3)
                        info = ydl.extract_info(search_spec, download=False)
                        if 'entries' in info and info['entries']:
                            info = info['entries'][0]
                        
                        video_duration = info.get('duration')
                        if duration_s and video_duration:
                            if abs(video_duration - duration_s) > 30:
                                print(f"    Skipping due to duration mismatch (expected {duration_s}s, got {video_duration}s)")
                                continue
                        
                        # download
                        ydl.download([info['webpage_url']])
                        print(f"    Downloaded: {info.get('title')}")
                        downloaded.append({'Track Name': track_name, 'Artist Name(s)': artist_primary, 'Album Name': album, 'Track Number': i})
                        success = True
                        break
                    except Exception as e:
                        print(f"    Error during download: {e}")
                        continue
                
            if not success:
                not_found_tracks.append({'Track Name':track_name,'Artist Name(s)':artist_primary,'Album Name':album,'Track Number':i,'Error':'No valid download'})
                
            elapsed = time.time() - start_time
            avg_time = elapsed / i
            eta = avg_time * (total - i)
            print(f"Progress: {i}/{total} | ETA ~ {int(eta)}s")
        
        if not_found_tracks:
            nf_path = os.path.join(output_dir, f"{safe_filename(tracklist_name)}_not_found.csv")
            with open(nf_path, 'w', newline='', encoding='utf-8') as cf:
                writer = csv.DictWriter(cf, fieldnames=['Track Name','Artist Name(s)','Album Name','Track Number','Error'])
                writer.writeheader()
                writer.writerows(not_found_tracks)

        print(f"Download completed. {len(downloaded)} tracks downloaded, {len(not_found_tracks)} not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # load config file
    if os.path.exists("config.ini"):
        config = configparser.ConfigParser()
        config.read("config.ini")
        client_id = config.get("Settings", "client_id")
        client_secret = config.get("Settings", "client_secret")
        username = config.get("Settings", "username")
    else:
        raise FileNotFoundError("config.ini file not found. Please create one with your Spotify credentials.")
    
    # authenticate with Spotify
    auth_manager = oauth2.SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    spotify = spotipy.Spotify(auth_manager=auth_manager)

    # handle user input
    output_path = "C:/Users/harri/Documents/playlist-maker/test_output"
    spotify_url = input("Enter Spotify URL: ").strip()
    content_type, spotify_id = parse_spotify_url(spotify_url)


    if content_type == "track":
        #download_spotify_track(spotify_url, output_path)
        print("Track download not implemented yet.")
    elif content_type == "playlist":
        #download_spotify_playlist(spotify_url, output_path)
        print("Playlist download not implemented yet.")
    elif content_type == "album":
        handle_spotify_album(spotify, spotify_id)
    
    