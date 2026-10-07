import re
import time

import requests

API_BASE = "https://api.spotify.com/v1"
REQUEST_TIMEOUT = 15   # seconds per HTTP request
MAX_RETRIES = 5


# simple function that shorthands the header for authorization
def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def parse_playlist_id(value):
    """Accept a raw playlist ID, a playlist URL, or a spotify:playlist: URI."""
    value = value.strip()
    match = re.search(r"playlist[/:]([A-Za-z0-9]+)", value)
    return match.group(1) if match else value


def spotify_request(method, url, token, **kwargs):
    """Make a Spotify API call, waiting and retrying when rate limited (HTTP 429)."""
    for _ in range(MAX_RETRIES):
        response = requests.request(method, url, headers=get_auth_header(token),
                                    timeout=REQUEST_TIMEOUT, **kwargs)
        if response.status_code != 429:
            response.raise_for_status()
            return response
        time.sleep(int(response.headers.get("Retry-After", 1)))
    response.raise_for_status()


def get_all_items(token, url):
    """Follow Spotify's paging 'next' links and return every item."""
    items = []
    while url:
        page = spotify_request("GET", url, token).json()
        items.extend(page["items"])
        url = page["next"]
    return items


def track_uris(items):
    # skip removed/unavailable tracks (track is None) and local files, which the API can't add
    return [item["track"]["uri"] for item in items
            if item.get("track") and not item.get("is_local")]


# get the songs in the liked songs collection, newest first
def get_liked_songs(token):
    return track_uris(get_all_items(token, API_BASE + "/me/tracks?limit=50"))


# get the songs currently in the playlist, in playlist order
def get_playlist_tracks(token, playlist_id):
    url = (API_BASE + "/playlists/" + playlist_id +
           "/tracks?limit=100&fields=items(is_local,track(uri)),next")
    return track_uris(get_all_items(token, url))


def chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def add_tracks(token, playlist_id, uris):
    # uris are newest first, so inserting each batch right after the previous one
    # puts the newest likes at the top of the playlist in the same order as Liked Songs
    url = API_BASE + "/playlists/" + playlist_id + "/tracks"
    for position, batch in zip(range(0, len(uris), 100), chunks(uris, 100)):
        spotify_request("POST", url, token, json={"uris": batch, "position": position})


def remove_tracks(token, playlist_id, uris):
    url = API_BASE + "/playlists/" + playlist_id + "/tracks"
    for batch in chunks(uris, 100):
        spotify_request("DELETE", url, token, json={"tracks": [{"uri": uri} for uri in batch]})


def sync_playlist(token, playlist_id, remove_unliked=False):
    """Make the playlist contain every liked song by comparing actual tracks, not counts.

    Liked songs missing from the playlist are added at the top. If remove_unliked is set,
    songs in the playlist that are no longer liked are removed.
    Returns (added_count, removed_count).
    """
    liked = get_liked_songs(token)
    in_playlist = set(get_playlist_tracks(token, playlist_id))

    to_add = [uri for uri in dict.fromkeys(liked) if uri not in in_playlist]
    add_tracks(token, playlist_id, to_add)

    to_remove = []
    if remove_unliked:
        liked_set = set(liked)
        to_remove = [uri for uri in in_playlist if uri not in liked_set]
        remove_tracks(token, playlist_id, to_remove)

    return len(to_add), len(to_remove)
