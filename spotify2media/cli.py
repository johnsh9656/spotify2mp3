import argparse
import os
import tempfile

from .config import load_config
from .spotify_client import convert_from_spotify_url
from .csv_io import write_tracklist_csv
from .youtube_handler import convert_csv_to_media


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="playlist-maker",
        description="Download Spotify media via YouTube and tag metadata."
    )

    p.add_argument("url", help="Spotify URL (track / album / playlist)")

    sort_group = p.add_mutually_exclusive_group()
    sort_group.add_argument("-keep", action="store_true", help="Keep order of playlist")
    sort_group.add_argument("-album", action="store_true", help="Keep each track's original album ordering #")

    p.add_argument(
        "-o", "--output",
        default=None,
        help="Override output path from config"
    )

    p.add_argument(
        "--format",
        default="mp3",
        choices=["mp3", "wav", "flac", "m4a"],
        help="Output audio format (default: mp3)"
    )

    p.add_argument(
        "-n", "--no-numbering",
        action="store_true",
        default=False,
        help="Do not prefix filenames with track numbers"
    )

    return p

def run(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    creds, download_settings = load_config()

    output_path = args.output or download_settings.output_path
    url = args.url.strip()

    # sort_mode
    if args.keep:
        sort_mode = "keep"
    else:
        sort_mode = "album"

    numbered_tracks = not args.no_numbering

    tracklist_title, tracklist_artists, release_date, tracks = convert_from_spotify_url(
        creds.client_id,
        creds.client_secret,
        url,
        sort_mode
    )

    fd, csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)

    try:
        write_tracklist_csv(csv_path, tracklist_title, tracks, tracklist_artists, release_date, sort_mode)
        convert_csv_to_media(csv_path, output_path, tracklist_title, numbered_tracks)
    finally:
        try:
            if os.path.exists(csv_path):
                os.remove(csv_path)
        except Exception as e:
            print(f"Warning: could not delete temporary file {csv_path}: {e}")

if __name__ == "__main__":
    raise SystemExit(run())