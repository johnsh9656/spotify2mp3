import subprocess

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
        subprocess.run([
            "spotdl",
            "download",
            spotify_url,
            "--output",
            f"{output_path}/",
            "--format",
            "mp3"
        ], check=True)
        print(f"Completed downloading playlist as MP3...")
    except Exception as e:
        print(f"An error occurred: {e}")

def download_spotify_album(spotify_url: str, output_path: str) -> None:
    try:
        print(f"Downloading album from {spotify_url} as MP3...")
        subprocess.run([
            "spotdl",
            "download",
            spotify_url,
            "--output",
            f"{output_path}/",
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