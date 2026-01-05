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

def _default_config_path() -> Path:
    # based on windows-standard config location : %APPDATA%/playlist-maker/config.ini
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "playlist-maker" / "config.ini"

    # fallback (rare)
    return Path.home() / ".playlist-maker" / "config.ini"

def load_config():
    candidates: list[Path] = []
    
    env_path = os.environ.get("PLAYLIST_MAKER_CONFIG")
    if env_path:
        candidates.append(Path(env_path))

    candidates.append(_default_config_path())
    
    candidates.append(Path.cwd() / "config.ini") # dev fallback

    cfg = next((p for p in candidates if p.exists()), None)
    if not cfg:
        raise FileNotFoundError(
            "config.ini not found.\n"
            "Expected one of:\n"
            "  %APPDATA%/playlist-maker/config.ini\n"
            "  ./config.ini\n"
            "Or pass --config <path> / set PLAYLIST_MAKER_CONFIG"
        )
    
    config = configparser.ConfigParser()
    config.read(cfg)

    spotify_creds = SpotifyCreds(
        client_id=config.get("SpotifyCreds", "client_id"),
        client_secret=config.get("SpotifyCreds", "client_secret"),
        username=config.get("SpotifyCreds", "username")
    )

    download_settings = Download(
        output_path=config.get("Download", "output_path")
    )

    return spotify_creds, download_settings