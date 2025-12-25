# spotify2mp3

### Setup
pip install -r requirements.txt

spotdl --install-ffmpeg

venv/Scripts/activate


### Project
#### spotify_download.py
download_spotify_track: downloads mp3 of given spotify track link to specified path

download_spotify_playlist: downloads mp3s of given spotify playlist link to specified path

download_spotify_album: downloads mp3s of given spotify album link to specified path




### Iterations
Each iteration builds on the previous.


#### Iteration 1: MVP (uses existing framework , spot-dl)
Console-based. 
Download MP3 files to specific output folder. 
Support spotify links for tracks, playlists, and albums. 
Using spot-dl. 


#### Iteration 2: Relies on minimal external frameworks
Console-based. 
Replace spot-dl with ytp-dl, ffmpeg.


#### Iteration 3: Global tool, file type options
Global console tool. 
Download as MP3, ... (iPod support). 
Includes album/playlist/track art. 