import os
import configparser
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SpotifyCreds:
    client_id: str
    client_secret: str
    username: str

@dataclass
class Download:
    output_path: str

def load_config():
    root = Path(__file__).resolve().parent.parent
    config_path = root / "config.ini"

    if not config_path.exists():
        raise FileNotFoundError("config.ini not found")
    
    config = configparser.ConfigParser()
    config.read(config_path)

    spotify_creds = SpotifyCreds(
        client_id=config.get("SpotifyCreds", "client_id"),
        client_secret=config.get("SpotifyCreds", "client_secret"),
        username=config.get("SpotifyCreds", "username")
    )

    download_settings = Download(
        output_path=config.get("Download", "output_path")
    )

    return spotify_creds, download_settings