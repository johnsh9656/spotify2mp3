import subprocess

def download_spotify_track(spotify_url: str, output_path: str) -> None:
    """
    Docstring for download_spotify_track
    
    :param spotify_url: Description
    :type spotify_url: str
    :param output_path: Description
    :type output_path: str
    """
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


def download_spotify_playlist(spotify_url: str, outputh_path: str) -> None:
    """
    Docstring for download_spotify_playlist
    
    :param spotify_url: Description
    :type spotify_url: str
    :param outputh_path: Description
    :type outputh_path: str
    """

def download_spotify_album(spotify_url: str, output_path: str) -> None:
    """
    Docstring for download_spotify_album
    
    :param spotify_url: Description
    :type spotify_url: str
    :param output_path: Description
    :type output_path: str
    """


if __name__ == "__main__":
    print("run spotify_download.py ...")
    
    content_type = "track"  # track, playlist, album
    spotify_url = "https://open.spotify.com/track/2KD5l5X4ZK0D9cfepm1Krn?si=61e2c20a39664ecd"
    output_path = "C:/Users/harri/Documents/playlist-maker/test_output"

    download_spotify_track(spotify_url, output_path)