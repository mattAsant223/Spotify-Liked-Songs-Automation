import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests

API_BASE = "https://api.spotify.com/v1"
REQUEST_TIMEOUT = 15   # seconds per HTTP request
MAX_RETRIES = 5
MAX_WORKERS = 8        # parallel page fetches; kept modest to avoid Spotify rate limits

# reuse connections across requests instead of a new TLS handshake for every call
session = requests.Session()
session.mount("https://", requests.adapters.HTTPAdapter(pool_maxsize=MAX_WORKERS))


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
        response = session.request(method, url, headers=get_auth_header(token),
                                   timeout=REQUEST_TIMEOUT, **kwargs)
        if response.status_code != 429:
            response.raise_for_status()
            return response
        time.sleep(int(response.headers.get("Retry-After", 1)))
    response.raise_for_status()


def get_page(token, url, offset, limit):
    return spotify_request("GET", url, token, params={"offset": offset, "limit": limit}).json()


def get_pages(token, url, offsets, limit, pool):
    """Fetch several pages at once; results come back in the same order as offsets."""
    return list(pool.map(lambda offset: get_page(token, url, offset, limit)["items"], offsets))


def track_uris(items):
    # skip removed/unavailable tracks (track is None) and local files, which the API can't add
    return [item["track"]["uri"] for item in items
            if item.get("track") and not item.get("is_local")]


# get the songs currently in the playlist, in playlist order
def get_playlist_tracks(token, playlist_id, pool):
    url = (API_BASE + "/playlists/" + playlist_id +
           "/tracks?fields=items(is_local,track(uri)),next,total")
    # the first page tells us the total, so every other page offset is known up front
    first = get_page(token, url, 0, 100)
    pages = [first["items"]] + get_pages(token, url, range(100, first["total"], 100), 100, pool)
    return [uri for page in pages for uri in track_uris(page)]


# get the songs in the liked songs collection, newest first
def get_liked_songs(token, pool, already_synced=None):
    """If already_synced (a set of URIs) is given, stop fetching once a whole page of
    liked songs is in it: liked songs are newest first, so everything older is synced too.
    Pages are fetched in waves that double in size, so a small update only needs a request
    or two, while a first-time sync of a big library still loads mostly in parallel.
    """
    url = API_BASE + "/me/tracks"
    first = get_page(token, url, 0, 50)
    pages = [track_uris(first["items"])]
    offsets = list(range(50, first["total"], 50))

    def fully_synced(page):
        return already_synced is not None and page and all(uri in already_synced for uri in page)

    wave_size = 1
    while offsets and not fully_synced(pages[-1]):
        wave, offsets = offsets[:wave_size], offsets[wave_size:]
        for items in get_pages(token, url, wave, 50, pool):
            pages.append(track_uris(items))
            if fully_synced(pages[-1]):
                break
        wave_size *= 2

    return [uri for page in pages for uri in page]


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
    songs in the playlist that are no longer liked are removed (this needs the full
    liked songs list, so it skips the early stop).
    Returns (added_count, removed_count).
    """
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        in_playlist = set(get_playlist_tracks(token, playlist_id, pool))
        liked = get_liked_songs(token, pool, None if remove_unliked else in_playlist)

    to_add = [uri for uri in dict.fromkeys(liked) if uri not in in_playlist]
    add_tracks(token, playlist_id, to_add)

    to_remove = []
    if remove_unliked:
        liked_set = set(liked)
        to_remove = [uri for uri in in_playlist if uri not in liked_set]
        remove_tracks(token, playlist_id, to_remove)

    return len(to_add), len(to_remove)
