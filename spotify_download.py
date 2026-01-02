import re
import os
import configparser
import csv
import tempfile
import time
import shutil

from config import load_config
from spotify_client import convert_from_spotify_url
from csv_io import write_tracklist_csv
from youtube_handler import convert_csv_to_media 


# settings
transcode_mp3 = True
generate_m3u = False
deepSearch = False

def main():
    creds, download_settings = load_config()
    output_path = download_settings.output_path
    print(output_path)

    client_id = creds.client_id
    client_secret = creds.client_secret

    spotify_url = input("Enter Spotify URL: ").strip()

    # if spotify url
        # convert_from_spotify_url
    # else if youtube url program
        # convert_from_youtube_url
    # else
        # invalid url, end

    # check for tag to set sort_mode="keep"
    sort_mode = "keep"
    
    playlist_title, playlist_artists, release_date, tracks = convert_from_spotify_url(client_id, client_secret, spotify_url)

    fd, csv_path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)

    try:
        write_tracklist_csv(csv_path, playlist_title, tracks, playlist_artists, release_date, sort_mode="keep")
        convert_csv_to_media(csv_path, output_path, playlist_title, numbered_tracks=True)
    finally:
        # delete temp csv file
        try:
            if os.path.exists(csv_path):
                os.remove(csv_path)
        except Exception as e:
            print(f"Warning: could not delete temporary file {csv_path}: {e}")



if __name__ == "__main__":
    main()
    