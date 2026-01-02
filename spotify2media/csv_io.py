import csv

def write_tracklist_csv(csv_path, list_title, list_tracks, tracklist_artists, release_date, sort_mode: str = "keep"):
    # sort_mode: "keep" for playlist order, "album" for album order (ie by disc and track number)
    fieldnames = [
        "Track Name",
        "Artist Name(s)",
        "Genre",
        "Album Name",
        "Album Artist(s)",
        "Tracklist Name",
        "Tracklist Artist(s)",
        "Release Date",
        "Duration (ms)",
        "Disc Number",
        "Track Number",
        "Spotify Track ID",
        "Spotify Track URL",
        "Cover URL",
    ]

    tracklist_artists_str = "; ".join(tracklist_artists or [])

    if sort_mode == "album":
        #  safe sort even if None
        def k(x):
            d = x.get("disc_number") or 0
            n = x.get("track_number") or 0
            return (d, n)
        tracks_sorted = sorted(list_tracks, key=k)
    else:
        # keep incoming order (playlist order)
        tracks_sorted = list_tracks

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for t in tracks_sorted:
            album_obj = t.get("album") or {}
            album_name = album_obj.get("name") or "Unknown"
            album_artists = album_obj.get("artists") or (tracklist_artists or [])
            album_artists_str = "; ".join(album_artists)
            genre = (t.get("genre") or "").strip()

            w.writerow({
                "Track Name": t["title"] or "",
                "Artist Name(s)": "; ".join(t["artists"] or []),
                "Genre": genre,
                "Album Name": album_name,
                "Album Artist(s)": album_artists_str,
                "Tracklist Name": list_title,
                "Tracklist Artist(s)": tracklist_artists_str,
                "Release Date": album_obj.get("release_date") or release_date or "",
                "Duration (ms)": t["duration_ms"] or 0,
                "Disc Number": t["disc_number"] or "",
                "Track Number": t["track_number"] or "",
                "Spotify Track ID": t["spotify_id"] or "",
                "Spotify Track URL": t["spotify_url"] or "",
                "Cover URL": t.get("cover_url") or "",
            })

def read_tracklist_csv(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))