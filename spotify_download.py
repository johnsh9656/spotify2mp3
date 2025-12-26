import subprocess
import re
import os

def download_spotify_track(spotify_url: str, output_path: str) -> None:
    try:
        print(f"Downloading track from {spotify_url} as MP3...")
        subprocess.run([
            "spotdl",
            "download",
            spotify_url,
            "--output",
            f"{output_path}/",
            "--format",
            "mp3"
        ], check=True)
        print(f"Completed downloading track as MP3...")
    except Exception as e:
        print(f"An error occurred: {e}")


def download_spotify_playlist(spotify_url: str, output_path: str) -> None:
    try:
        print(f"Downloading playlist from {spotify_url} as MP3...")

        # playlist name is id from url
        playlist_name = spotify_url.split('/playlist/')[-1].split('?')[0]

        # check if folder already exists in output_path
        playlist_path = os.path.join(output_path, playlist_name)
        if os.path.exists(playlist_path):
            print(f"Playlist folder '{playlist_name}' already exists. Skipping download.")
            return

        subprocess.run([
            "spotdl",
            "download",
            spotify_url,
            "--output",
            f"{output_path}/{playlist_name}",
            "--format",
            "mp3"
        ], check=True)
        print(f"Completed downloading playlist as MP3...")
    except Exception as e:
        print(f"An error occurred: {e}")

def download_spotify_album(spotify_url: str, output_path: str) -> None:
    try:
        print(f"Downloading album from {spotify_url} as MP3...")

        # album name is id from url
        album_name = spotify_url.split('/album/')[-1].split('?')[0]

        # check if folder already exists in output_path
        album_path = os.path.join(output_path, album_name)
        if os.path.exists(album_path):
            print(f"Album folder '{album_name}' already exists. Skipping download.")
            return

        subprocess.run([
            "spotdl",
            "download",
            spotify_url,
            "--output",
            f"{output_path}/{album_name}",
            "--format",
            "mp3"
        ], check=True)
        print(f"Completed downloading album as MP3...")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    print("------------ DOWNLOADING SPOTIFY TO MP3 ------------")    

    content_type = input("Enter content type (track/playlist/album): ").strip().lower()
    if content_type not in ["track", "playlist", "album"]:
        print("Invalid content type. Please enter 'track', 'playlist', or 'album'.")
        exit(1)

    spotify_url = input("Enter Spotify URL: ").strip()
    output_path = "C:/Users/harri/Documents/playlist-maker/test_output"

    try:
        if content_type == "track":
            download_spotify_track(spotify_url, output_path)
        elif content_type == "playlist":
            download_spotify_playlist(spotify_url, output_path)
        elif content_type == "album":
            download_spotify_album(spotify_url, output_path)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")