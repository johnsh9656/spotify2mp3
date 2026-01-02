import re
import os
import configparser
import csv
import time
import shutil
from yt_dlp import YoutubeDL
import tempfile
from mutagen.id3 import ID3, TIT2, TPE1, TPE2, TALB, TRCK, TPOS, TDRC, COMM, TCON
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from datetime import datetime
import io
import requests
from PIL import Image
from mutagen.id3 import APIC
from mutagen.id3 import ID3, ID3NoHeaderError


# windows filename safety
def safe_filename(name: str, max_len: int = 120) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name[:max_len].rstrip(' .')

def get_mp3_cover_dimensions(file_path: str):
    tags = ID3(file_path)
    apics = tags.getall("APIC")
    if not apics:
        return None
    img_bytes = apics[0].data
    im = Image.open(io.BytesIO(img_bytes))
    return im.size, im.format  # (width,height), "JPEG"/"PNG"

def download_image_bytes(url: str, timeout=20) -> bytes:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content

def normalize_cover_to_jpeg(img_bytes: bytes, max_size=(600, 600), quality=85) -> bytes:
    """
    Converts any image to a reasonably-sized JPEG for iPod friendliness.
    """
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    im.thumbnail(max_size)  # keeps aspect ratio
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=quality, optimize=False)
    return out.getvalue()

def embed_cover_mp3(file_path: str, jpeg_bytes: bytes):
    try:
        tags = ID3(file_path)
    except ID3NoHeaderError:
        tags = ID3()

    tags.delall("APIC")
    tags.add(APIC(
        encoding=3,
        mime="image/jpeg",
        type=3,
        desc="Cover",
        data=jpeg_bytes
    ))
    tags.save(file_path, v2_version=3)

def tag_audio_file(file_path: str, meta: dict):
    title = (meta.get("Track Name") or "").strip()
    artists = [a.strip() for a in (meta.get("Artist Name(s)") or "").split(";") if a.strip()]
    album = (meta.get("Album Name") or "").strip()
    album_artists = [a.strip() for a in (meta.get("Album Artist(s)") or "").split(";") if a.strip()]
    release_date = (meta.get("Release Date") or "").strip()
    track_number = (meta.get("Track Number") or "").strip()
    disc_number = (meta.get("Disc Number") or "").strip()
    genre = (meta.get("Genre") or "").strip()
    yt_url = (meta.get("YouTube URL") or "").strip()

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".mp3":
        audio = MP3(file_path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()

        if title: audio.tags.add(TIT2(encoding=3, text=title))
        if artists: audio.tags.add(TPE1(encoding=3, text=artists))
        if album_artists: audio.tags.add(TPE2(encoding=3, text=album_artists))
        if album: audio.tags.add(TALB(encoding=3, text=album))
        if track_number: audio.tags.add(TRCK(encoding=3, text=track_number))
        if disc_number: audio.tags.add(TPOS(encoding=3, text=disc_number))
        if release_date: audio.tags.add(TDRC(encoding=3, text=release_date[:4]))  
        if genre: audio.tags.add(TCON(encoding=3, text=genre))
        if yt_url: audio.tags.add(COMM(encoding=3, lang="eng", desc="Comment", text=yt_url))

        audio.save(v2_version=3)
    elif ext in (".m4a", ".mp4"):
        audio = MP4(file_path)
        if title: audio["\xa9nam"] = [title]
        if artists: audio["\xa9ART"] = artists
        if album: audio["\xa9alb"] = [album]
        if album_artists: audio["aART"] = album_artists
        if release_date: audio["\xa9day"] = [release_date]
        if track_number:
            try: audio["trkn"] = [(int(track_number), 0)]
            except ValueError: pass
        if disc_number:
            try: audio["disk"] = [(int(disc_number), 0)]
            except ValueError: pass
        if genre: audio["\xa9gen"] = [genre]

        audio.save()

def find_downloaded_audio(output_dir: str, base_prefix: str):
    candidates = []
    for fn in os.listdir(output_dir):
        if fn.startswith(base_prefix) and fn.lower().endswith((".mp3", ".m4a")):
            candidates.append(os.path.join(output_dir, fn))
    return max(candidates, key=os.path.getmtime) if candidates else None

# converts a CSV playlist export to mp3 files using youtube-dl / yt-dlp
def convert_csv_to_media(csv_path, output_path, tracklist_name, numbered_tracks: bool = True, transcode_mp3: bool = True):    
    start_time = time.time()
    output_dir = os.path.join(output_path, safe_filename(tracklist_name))
    os.makedirs(output_dir, exist_ok=True)

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
                    cover_url = (row.get("Cover URL") or "").strip()
                    if cover_url:
                        try:
                            raw = download_image_bytes(cover_url)
                            jpg = normalize_cover_to_jpeg(
                                raw,
                                max_size=(500, 500),
                                quality=85
                            )
                            embed_cover_mp3(final_path, jpg)
                        except Exception as e:
                            print(f"    Warning: failed to embed cover art: {e}")
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
        print(f"Tracks donwloaded to {output_dir}")
    except Exception as e:
        print(f"An error occurred: {e}")