import spotipy
import spotipy.oauth2 as oauth2
import re
import os
import tempfile
import csv
from .youtube_handler import convert_csv_to_media

# cache for artist genres to minimize API calls
artist_genre_cache = {}
def get_primary_genre(spotify, artist_id: str) -> str:
    cached = artist_genre_cache.get(artist_id)
    if cached is not None:
        return cached[0] if cached else ""
    try:
        artist = spotify.artist(artist_id)
        genres = artist.get("genres", [])
        if not isinstance(genres, list):
            genres = []
        genres = [genre.capitalize() for genre in genres]
            
        artist_genre_cache[artist_id] = genres

        #print(f"Fetched genres for artist {artist_id}: {genres}")
        return genres[0] if genres else ""
    except Exception:
        artist_genre_cache[artist_id] = []
        return ""

def parse_spotify_url(url: str):
    m = re.compile(r"open\.spotify\.com/(track|playlist|album)/([a-zA-Z0-9]+)", re.IGNORECASE).search(url)
    if not m:
        raise ValueError("Invalid Spotify URL")
    content_type = m.group(1).lower()
    spotify_id = m.group(2)
    return content_type, spotify_id

def handle_spotify_track(spotify, track_id):
    track = spotify.track(track_id)
    track_number = track['track_number']
    disc_number = track['disc_number']
    track_name = track['name']
    artists = track['artists']
    artists_names = [a['name'] for a in artists]
    duration_ms = track['duration_ms']
    track_url = track['external_urls']['spotify']

    album = track['album']
    album_title = album['name']
    album_artists = [a['name'] for a in album['artists']]
    release_date = album['release_date']
    images = album['images'] or []

    artist_ids = [a["id"] for a in artists if a.get("id")]
    primary_artist_id = artist_ids[0] if artist_ids else None
    genre = get_primary_genre(spotify, primary_artist_id) if primary_artist_id else ""

    cover_url = images[0]['url'] if images else ""

    track_list = []
    track_list.append({
        'track_number': track_number,
        'disc_number': disc_number,
        'title': track_name,
        'artists': artists_names,
        'artists_ids': artist_ids,
        'genre': genre,
        'duration_ms': duration_ms,
        'spotify_id': track_id,
        'spotify_url': track_url,
        'album': {
            'name': album_title,
            'artists': album_artists,
            'release_date': release_date,
        },
        'cover_url': cover_url,
    })

    return track_name, artists_names, release_date, track_list
    
    # fd, csv_path = tempfile.mkstemp(suffix=".csv")
    # os.close(fd)

    # try:
    #     write_tracklist_csv(spotify, csv_path, track_name, track_list, artists_names, release_date)
    #     convert_csv_to_media(csv_path, output_path, track_name, numbered_tracks=False)
    # finally:
    #     # delete temp csv file
    #     try:
    #         if os.path.exists(csv_path):
    #             os.remove(csv_path)
    #     except Exception as e:
    #         print(f"Warning: could not delete temporary file {csv_path}: {e}")


def handle_spotify_album(spotify, album_id):
    album = spotify.album(album_id)
    album_title = album['name']
    album_artists = [a['name'] for a in album['artists']]
    release_date = album['release_date']
    images = album['images'] or []
    cover_url = images[0]['url'] if images else ""

    # pagination, spotify returns max 50 trackers per request
    tracks = []
    results = spotify.album_tracks(album_id, limit=50)
    while results:
        tracks.extend(results['items'])
        results = spotify.next(results) if results['next'] else None

    album_tracks = []
    for t in tracks:
        artist_objs = t.get("artists") or []
        artist_names = [a.get("name", "") for a in artist_objs if a.get("name")]
        artist_ids = [a.get("id") for a in artist_objs if a.get("id")]

        primary_artist_id = artist_ids[0] if artist_ids else None
        genre = get_primary_genre(spotify, primary_artist_id) if primary_artist_id else ""

        
        album_tracks.append({
            'track_number': t['track_number'],
            'disc_number': t['disc_number'],
            'title': t['name'],
            'artists': artist_names,
            'artists_ids': artist_ids,
            'genre': genre,
            'duration_ms': t['duration_ms'],
            'spotify_id': t['id'],
            'spotify_url': t['external_urls']['spotify'],
            'album': {
                'name': album_title,
                'artists': album_artists,
                'release_date': release_date,
            },
            'cover_url': cover_url,
        })
    
    return album_title, album_artists, release_date, album_tracks

    # fd, csv_path = tempfile.mkstemp(suffix=".csv")
    # os.close(fd)

    # try:
    #     write_tracklist_csv(spotify, csv_path, album_title, album_tracks, album_artists, release_date, sort_mode="album")
    #     convert_csv_to_media(csv_path, output_path, album_title, numbered_tracks=True)
    # finally:
    #     # delete temp csv file
    #     try:
    #         if os.path.exists(csv_path):
    #             os.remove(csv_path)
    #     except Exception as e:
    #         print(f"Warning: could not delete temporary file {csv_path}: {e}")

def handle_spotify_playlist(spotify, playlist_id, keep_sort, use_album_name=False):
    playlist = spotify.playlist(playlist_id)
    playlist_title = playlist['name']
    playlist_owner = playlist['owner']['display_name'] or playlist['owner']['id']

    # pagination, spotify returns max 50 trackers per request
    items = []
    results = spotify.playlist_items(playlist_id, limit=50)
    while results:
        items.extend(results['items'])
        results = spotify.next(results) if results['next'] else None

    playlist_tracks = []
    added_dates = []

    trackNum = 0

    for item in items:
        track = item.get('track')
        if not track:
            continue # skip local or unavailable tracks

        added_at = item.get('added_at')
        if added_at:
            added_dates.append(added_at)
        
        album = track.get('album', {})

        images = album['images'] or []
        cover_url = images[0]['url'] if images else ""

        artists = [a['name'] for a in track['artists']]
        artist_ids = [a.get("id") for a in (track.get("artists") or []) if a.get("id")]
        primary_artist_id = artist_ids[0] if artist_ids else None
        genre = get_primary_genre(spotify, primary_artist_id) if primary_artist_id else ""

        trackNum += 1

        playlist_tracks.append({
            'track_number': keep_sort and trackNum or track['track_number'],
            'disc_number': keep_sort and 1 or track['disc_number'] ,
            'title': track['name'],
            'artists': artists,
            'artists_ids': artist_ids,
            'genre': genre,
            'duration_ms': track['duration_ms'],
            'spotify_id': track['id'],
            'spotify_url': track['external_urls']['spotify'],
            'album': {
                'name': (use_album_name and album.get('name')) or playlist_title,
                'artists': [a['name'] for a in album.get('artists', [])],
                'release_date': album.get('release_date'),
            },
            'cover_url': cover_url,
        })
    
    # determine playlist release date as the latest added_at date
    playlist_date = ""
    if added_dates:
        playlist_date = max(added_dates)[:10]
        
    return playlist_title, playlist_owner, playlist_date, playlist_tracks

    # fd, csv_path = tempfile.mkstemp(suffix=".csv")
    # os.close(fd)

    # try:
    #     write_tracklist_csv(spotify, csv_path, playlist_title, playlist_tracks, [playlist_owner], playlist_date, sort_mode="keep")
    #     convert_csv_to_media(csv_path, output_path, playlist_title, numbered_tracks=True)
    # finally:
    #     # delete temp csv file
    #     try:
    #         if os.path.exists(csv_path):
    #             os.remove(csv_path)
    #     except Exception as e:
    #         print(f"Warning: could not delete temporary file {csv_path}: {e}")


def convert_from_spotify_url(client_id, client_secret, url: str, sort_mode: str):
    # authenticate with Spotify
    auth_manager = oauth2.SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    spotify = spotipy.Spotify(auth_manager=auth_manager)

    content_type, spotify_id = parse_spotify_url(url)
    if content_type == "track":
        return handle_spotify_track(spotify, spotify_id)
    elif content_type == "album":
        return handle_spotify_album(spotify, spotify_id)
    elif content_type == "playlist":
        keep_sort = sort_mode == "keep"
        return handle_spotify_playlist(spotify, spotify_id, keep_sort=keep_sort)
    else:
        raise ValueError("Unsupported Spotify content type")
