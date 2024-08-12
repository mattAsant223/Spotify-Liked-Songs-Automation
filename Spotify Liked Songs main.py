import requests
import base64
from urllib.parse import urlencode
import webbrowser

# most of these are generated once you fill out the spotify web api app and create it for your project
# your playistid is located in the url when you create a playlist, or you can use api as well!
from Secret import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, PLAYLIST_ID


# this function retrieves a token for us to be authorized to let spotify get information within the
# scope we identify
def get_token():
    query = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "user-library-read playlist-modify-public playlist-modify-private"
    }

    webbrowser.open("https://accounts.spotify.com/authorize?" + urlencode(query))

    # Prompt the user to enter the authorization code after being redirected
    auth_code = input("After authorizing this application, enter the authorization code: ")
    url = "https://accounts.spotify.com/api/token"

    auth_header = base64.urlsafe_b64encode((CLIENT_ID + ':' + CLIENT_SECRET).encode())
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic {}".format(auth_header.decode("ascii"))
    }
    body = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
    }
    response = requests.post(url, headers=headers, data=body)
    return response.json()["access_token"]


# simple function that shorthands the header for authorization
def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

# we get the tracks that are in the playlist so we don't duplicate tracks!
# this will be the same method for grabbing the uri's we DO want to add later in the next function
def get_playlist_tracks(token, playlist_id):
    playListUris = []
    offsetVariable = 0
    # we add the offset and limit variables to sift through our tracks
    # spotify api's max track return is 50
    url = ("https://api.spotify.com/v1/playlists/" + playlist_id + "/tracks?offset=" +
           str(offsetVariable) + "&limit=50")
    headers = get_auth_header(token)
    playlistTracks = requests.get(url, headers=headers)
    playlistTracksJson = playlistTracks.json()
    # classic fencing problem. calculate how many times we iterate by 50 tracks then deal with
    # grabbing the leftovers later.
    playlistTotal = playlistTracksJson["total"]
    modularPlaylistTotal = playlistTotal % 50
    playListIterativeSteps = playlistTotal // 50

    # loop through 50 tracks at a time through updating the url's offset variable by 50 to get the
    # 50 next tracks
    for i in range(0, playListIterativeSteps):
        url = ("https://api.spotify.com/v1/playlists/" + playlist_id + "/tracks?offset=" +
               str(offsetVariable) + "&limit=50")
        playlistTracks = requests.get(url, headers=headers)
        playlistTracksJson = playlistTracks.json()

        for j in range(0, 50):
            playListUris.append(str(playlistTracksJson["items"][j]["track"]["uri"]))
        offsetVariable += 50

    # once the loop is finished, add those last few tracks that we
    # identified through getting the remainder
    url = ("https://api.spotify.com/v1/playlists/" + playlist_id + "/tracks?offset=" +
           str(offsetVariable) + "&limit=50")
    playlistTracks = requests.get(url, headers=headers)
    playlistTracksJson = playlistTracks.json()
    for k in range(0, modularPlaylistTotal):
        playListUris.append(str(playlistTracksJson["items"][k]["track"]["uri"]))

    # return the list to now compare what needs to be added to the playlist!
    return playListUris


# get the songs in the liked playlist

# same idea as the previous function but now with the actual liked songs collection
def get_songs(token, playlistUris):
    # start off with empty list that we will add the spotify uri's to
    trackuris = []
    # keep track also of how much were offsetting to grab every track possible
    offsetVariable = 0
    # plug in offset variable in the url, and we want the limit to be as large as possible
    # spotify api's max is 50
    urll = "https://api.spotify.com/v1/me/tracks?offset=" + str(offsetVariable) + "&limit=50"
    headers = get_auth_header(token)
    tracks = requests.get(urll, headers=headers)
    tracksJson = tracks.json()
    # create variable to get amount of tracks in liked songs collection
    likedSongsTotal = tracksJson["total"]
    # create variable to see whatever the total is remainder 50, so we know how many songs are left over
    # after the last iterative 50 step
    modularTotal = likedSongsTotal % 50
    # create variable to identify how many times will we have to loop 50 tracks at a time?
    # making sure its floor division, so we don't go over and get index errors later
    iterativeSteps = likedSongsTotal // 50

    # loop through 50 tracks at a time through updating the url's offset variable by 50 to get the
    # 50 next tracks
    for i in range(0, iterativeSteps):
        urll = "https://api.spotify.com/v1/me/tracks?offset=" + str(offsetVariable) + "&limit=50"
        tracks = requests.get(urll, headers=headers)
        tracksJson = tracks.json()

        for j in range(0, 50):
            # important conditional: if this uri is already in the playlist, don't add it!
            if tracksJson["items"][j]["track"]["uri"] in playlistUris:
                continue
            else:
                trackuris.append(str(tracksJson["items"][j]["track"]["uri"]))
        offsetVariable += 50

    # once the loop is finished, add those last few tracks that we identified through getting the remainder
    urll = "https://api.spotify.com/v1/me/tracks?offset=" + str(offsetVariable) + "&limit=50"
    tracks = requests.get(urll, headers=headers)
    tracksJson = tracks.json()
    for k in range(0, modularTotal):
        # same conditional but for the leftover tracks
        if tracksJson["items"][k]["track"]["uri"] in playlistUris:
            continue
        else:
            trackuris.append(str(tracksJson["items"][k]["track"]["uri"]))

    # return the list to now populate the playlist!
    return trackuris


# populating the playlist: parameters are the list of trackuris we created from get_songs,
# the playlist id, the token we were authorized with, and the list of tracks from the playlist
def populate_playlists(token, PLAYLIST_ID, playlistUris, trackuris):
    uriString = ""
    url = "https://api.spotify.com/v1/playlists/" + PLAYLIST_ID + "/tracks?uris=" + uriString
    headers = get_auth_header(token)

    head = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(token),
    }

    # once again grab how many tracks we have from the previous function
    spliceTotal = len(trackuris)
    spliceModulo = spliceTotal % 50
    spliceTotal //= 50

    # one based indexing, because multiplying by 0 is always 0
    for i in range(1, spliceTotal + 1):
        # create substrings of the list of uris because spotify only takes so much at once,
        # in this case 50 was a workable number for spotify
        subTrackuri = trackuris[(i - 1) * 50:i * 50]
        # join each uri with %2C and replace colons with %3A
        subTrackuriString = "%2C".join(subTrackuri)
        while subTrackuriString.find(":") != -1:
            subTrackuriString = subTrackuriString.replace(":", "%3A")

        uriString = subTrackuriString
        # update the url with the new uriStrings and continue to loop through the tracks!

        if len(playlistUris) != 0:
            url = ("https://api.spotify.com/v1/playlists/" + PLAYLIST_ID + "/tracks?uris=" + uriString
                   + "&position=0")
        else:
            url = ("https://api.spotify.com/v1/playlists/" + PLAYLIST_ID + "/tracks?uris=" + uriString)

        response = requests.post(url, headers=head)
        if response.status_code == 201:
            print('Tracks added successfully')
        else:
            print(f'Failed to add tracks: {response.status_code} - {response.text}')

    # exact same idea but with the leftover tracks
    # clever way to get the last few tracks without having to keep track of
    # how many splices we've made. We know because of our remainder calculation it will be this
    # amount of tracks everytime
    subTrackuri = trackuris[(-spliceModulo):]
    subTrackuriString = "%2C".join(subTrackuri)
    while subTrackuriString.find(":") != -1:
        subTrackuriString = subTrackuriString.replace(":", "%3A")
    uriString = subTrackuriString
    # small detail, if the playlist already had tracks, and were only
    # adding a few tracks that doesn't exceed the remainder, we send the latest ones to the top
    if len(playlistUris) != 0:
        url = ("https://api.spotify.com/v1/playlists/" + PLAYLIST_ID + "/tracks?uris=" + uriString
               + "&position=0")
    else:
        url = ("https://api.spotify.com/v1/playlists/" + PLAYLIST_ID + "/tracks?uris=" + uriString)

    response = requests.post(url, headers=head)
    if response.status_code == 201:
        print('Tracks added successfully')
    else:
        print(f'Failed to add tracks: {response.status_code} - {response.text}')


# run what we have! enjoy!
token = get_token()
playlistSongs = get_playlist_tracks(token, PLAYLIST_ID)
song_list = get_songs(token, playlistSongs)
populate_playlists(token, PLAYLIST_ID, playlistSongs, song_list)
