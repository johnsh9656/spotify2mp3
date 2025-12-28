import re
import os
import spotipy
import spotipy.oauth2 as oauth2
import configparser
import csv
import time
import shutil
from yt_dlp import YoutubeDL
import tempfile
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TRCK, TPOS, TDRC, COMM, TCON
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4


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

artist_genre_cache = {}
def get_primary_genre(spotify, artist_id: str) -> str:
    cached = artist_genre_cache.get(artist_id)
    if cached is not None:
        return cached[0] if cached else ""
    try:
        artist = spotify.artist(artist_id)
        genres = artist.get("genres", [])
        if not isinstance(genres, list):
            genres = []
        genres = [genre.capitalize() for genre in genres]
            
        artist_genre_cache[artist_id] = genres

        print(f"Fetched genres for artist {artist_id}: {genres}")
        return genres[0] if genres else ""
    except Exception:
        artist_genre_cache[artist_id] = []
        return ""

def tag_audio_file(file_path: str, meta: dict):
    title = (meta.get("Track Name") or "").strip()
    artists = [a.strip() for a in (meta.get("Artist Name(s)") or "").split(";") if a.strip()]
    album = (meta.get("Album Name") or "").strip()
    album_artists = [a.strip() for a in (meta.get("Album Artist(s)") or "").split(";") if a.strip()]

    release_date = (meta.get("Release Date") or "").strip()
    track_number = (meta.get("Track Number") or "").strip()
    disc_number = (meta.get("Disc Number") or "").strip()
    genre = (meta.get("Genre") or "").strip()

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".mp3":
        audio = MP3(file_path, ID3=ID3)
        # if audio.tags is None:
        #     audio.add_tags()

        # # wipe relevant frames so YouTube junk doesn't linger
        # for key in ("TIT2","TPE1","TPE2","TALB","TRCK","TPOS","TDRC","COMM"):
        #     audio.tags.delall(key)

        if title:
            audio.tags.add(TIT2(encoding=3, text=title))
        if artists:         # contributing artists
            audio.tags.add(TPE1(encoding=3, text=artists))
        if album_artists:   # album artist
            audio.tags.add(TPE2(encoding=3, text=album_artists))
        if album:
            audio.tags.add(TALB(encoding=3, text=album))
        if track_number:
            audio.tags.add(TRCK(encoding=3, text=track_number))
        if disc_number:
            audio.tags.add(TPOS(encoding=3, text=disc_number))
        if release_date:     # release year
            audio.tags.add(TDRC(encoding=3, text=release_date[:4]))  
        if genre:
            audio.tags.add(TCON(encoding=3, text=genre))

        # Optional: store source URL in Comments so you can trace it
        yt_url = (meta.get("YouTube URL") or "").strip()
        if yt_url:
            audio.tags.add(COMM(encoding=3, lang="eng", desc="Comment", text=yt_url))

        audio.save(v2_version=3)  # ID3v2.3 = best compatibility
    elif ext in (".m4a", ".mp4"):
        audio = MP4(file_path)
        if title: audio["\xa9nam"] = [title]
        if artists: audio["\xa9ART"] = artists
        if album: audio["\xa9alb"] = [album]
        if album_artists: audio["aART"] = album_artists  # album artist
        if release_date: audio["\xa9day"] = [release_date]
        if track_number:
            try:
                audio["trkn"] = [(int(track_number), 0)]
            except ValueError:
                pass
        if disc_number:
            try:
                audio["disk"] = [(int(disc_number), 0)]
            except ValueError:
                pass
        if genre: audio["\xa9gen"] = [genre]
        audio.save()

def find_downloaded_audio(output_dir: str, base_prefix: str):
    candidates = []
    for fn in os.listdir(output_dir):
        if fn.startswith(base_prefix) and fn.lower().endswith((".mp3", ".m4a")):
            candidates.append(os.path.join(output_dir, fn))
    return max(candidates, key=os.path.getmtime) if candidates else None


def parse_spotify_url(url: str):
    m = SPOTIFY_RE.search(url)
    if not m:
        raise ValueError("Invalid Spotify URL")
    content_type = m.group(1).lower()
    spotify_id = m.group(2)
    return content_type, spotify_id

def handle_spotify_track(spotify, track_id, output_path="output"):
    track = spotify.track(track_id)
    track_number = track['track_number']
    disc_number = track['disc_number']
    track_name = track['name']
    artists = track['artists']
    artists_names = [a['name'] for a in artists]
    duration_ms = track['duration_ms']
    track_url = track['external_urls']['spotify']

    album = track['album']
    album_title = album['name']
    release_date = album['release_date']
    images = album['images']


    track_list = []
    track_list.append({
        'track_number': track_number,
        'disc_number': disc_number,
        'title': track_name,
        'artists': artists_names,
        'artists_ids': [a['id'] for a in artists],
        'duration_ms': duration_ms,
        'spotify_id': track_id,
        'spotify_url': track_url,
    })
    
    fd, csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)

    try:
        write_tracklist_csv(spotify, csv_path, track_name, track_list, artists_names, release_date)
        #spotify, csv_path, list_title, list_tracks, tracklist_artists, release_date
        convert_playlist(csv_path, output_path, track_name, numbered_tracks=False)
    finally:
        # delete temp csv file
        try:
            if os.path.exists(csv_path):
                os.remove(csv_path)
        except Exception as e:
            print(f"Warning: could not delete temporary file {csv_path}: {e}")

def handle_spotify_album(spotify, album_id, output_path="output"):
    album = spotify.album(album_id)
    album_title = album['name']
    album_artists = [a['name'] for a in album['artists']]
    release_date = album['release_date']
    images = album['images']

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
            'artists_ids': [a['id'] for a in t['artists']],
            'duration_ms': t['duration_ms'],
            'spotify_id': t['id'],
            'spotify_url': t['external_urls']['spotify'],
        })
    
    fd, csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)

    try:
        write_tracklist_csv(spotify, csv_path, album_title, album_tracks, album_artists, release_date)
        convert_playlist(csv_path, output_path, album_title, numbered_tracks=True)
    finally:
        # delete temp csv file
        try:
            if os.path.exists(csv_path):
                os.remove(csv_path)
        except Exception as e:
            print(f"Warning: could not delete temporary file {csv_path}: {e}")


def write_tracklist_csv(spotify, csv_path, list_title, list_tracks, tracklist_artists, release_date):
    fieldnames = [
        "Track Name",
        "Artist Name(s)",
        "Genre",
        "Album Name",
        "Album Artist(s)",
        "Tracklist Name",
        "Tracklist Artist(s)",
        "Release Date",
        "Duration (ms)",
        "Disc Number",
        "Track Number",
        "Spotify Track ID",
        "Spotify Track URL",
    ]

    tracks_sorted = sorted(list_tracks, key=lambda x: (x["disc_number"], x["track_number"]))
    tracklist_artists_str = "; ".join(tracklist_artists or [])

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for t in tracks_sorted:
            album_obj = t.get("album") or {}
            album_name = album_obj.get("name") or list_title
            album_artists = album_obj.get("artists") or (tracklist_artists or [])
            album_artists_str = "; ".join(album_artists)

            artist_ids = t.get("artists_ids") or []
            primary_artist_id = artist_ids[0] if artist_ids else None
            genre = get_primary_genre(spotify, primary_artist_id) if primary_artist_id else ""


            w.writerow({
                "Track Name": t["title"],
                "Artist Name(s)": "; ".join(t["artists"]),
                "Genre": genre,
                "Album Name": album_name,
                "Album Artist(s)": album_artists_str,
                "Tracklist Name": list_title,
                "Tracklist Artist(s)": tracklist_artists_str,
                "Release Date": album_obj.get("release_date") or release_date or "",
                "Duration (ms)": t["duration_ms"],
                "Disc Number": t["disc_number"],
                "Track Number": t["track_number"],
                "Spotify Track ID": t["spotify_id"],
                "Spotify Track URL": t["spotify_url"],
            })

def convert_playlist(csv_path, output_path, tracklist_name, numbered_tracks: bool = True):
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
                
                "no_warnings": True,
            }
            if mp3:
                opts["postprocessors"] = [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"},
                    #{"key": "FFmpegMetadata"},
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
                    if (numbered_tracks):
                        base = f"{i:03d} - {file_title}" + (f" - {variant}" if variant else "")                
                    else:
                        base = f"{file_title}" + (f" - {variant}" if variant else "")
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
                        final_path = find_downloaded_audio(output_dir, base)
                        if not final_path:
                            raise RuntimeError("Downloaded file not found after download.")
                        tag_audio_file(final_path, row)
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
        handle_spotify_track(spotify, spotify_id, output_path)
    elif content_type == "playlist":
        #download_spotify_playlist(spotify_url, output_path)
        print("Playlist download not implemented yet.")
    elif content_type == "album":
        handle_spotify_album(spotify, spotify_id, output_path)
    
    