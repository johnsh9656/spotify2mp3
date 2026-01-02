import os
import configparser
from dataclasses import dataclass

@dataclass
class SpotifyCreds:
    client_id: str
    client_secret: str
    username: str

@dataclass
class Download:
    output_path: str

def load_config(config_file: str = "config.ini"):
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"{config_file} file not found. Please create one with your Spotify credentials.")
    
    config = configparser.ConfigParser()
    config.read(config_file)

    spotify_creds = SpotifyCreds(
        client_id=config.get("SpotifyCreds", "client_id"),
        client_secret=config.get("SpotifyCreds", "client_secret"),
        username=config.get("SpotifyCreds", "username")
    )

    download_settings = Download(
        output_path=config.get("Download", "output_path")
    )

    return spotify_creds, download_settings