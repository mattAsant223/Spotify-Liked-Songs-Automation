import requests
import base64
from urllib.parse import urlencode
import webbrowser
import time

# most of these are generated once you fill out the spotify web api app and create it for your project
# your playistid is located in the url when you create a playlist, or you can use api as well!
from Liked_Songs_Secret import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, PLAYLIST_ID


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
    return playlistTotal


    

# get the songs in the liked playlist

# same idea as the previous function but now with the actual liked songs collection
def get_songs(token, playlistTotal):

    # keep track also of how much were offsetting to grab every track possible
    offsetVariable = 0
    # plug in offset variable in the url, and we want the limit to be as large as possible
    # spotify api's max is 50
    urll = "https://api.spotify.com/v1/me/tracks?offset=" + str(0) + "&limit=50"
    headers = get_auth_header(token)
    tracks = requests.get(urll, headers=headers)
    tracksJson = tracks.json()
    # create variable to get amount of tracks in liked songs collection
    likedSongsTotal = tracksJson["total"] - playlistTotal
    # create variable to see whatever the total is remainder 50, so we know how many songs are left over
    # after the last iterative 50 step
    modularTotal = likedSongsTotal % 50
    # create variable to identify how many times will we have to loop 50 tracks at a time?
    # making sure its floor division, so we don't go over and get index errors later
    iterativeSteps = likedSongsTotal // 50

    # loop through 50 tracks at a time through updating the url's offset variable by 50 to get the
    # 50 next tracks
    trackStack = []
    # use a stack to conviently keep order of the tracks we want to add and in the 50 song increments as well
    for i in range(0, iterativeSteps):
        urll = "https://api.spotify.com/v1/me/tracks?offset=" + str(offsetVariable) + "&limit=50"
        tracks = requests.get(urll, headers=headers)
        tracksJson = tracks.json()
        trackuris = []
        for j in range(0, 50):
            trackuris.append(str(tracksJson["items"][j]["track"]["uri"]))
        trackStack.append(trackuris)
        offsetVariable += 50

    # once the loop is finished, add those last few tracks that we identified through getting the remainder
    urll = "https://api.spotify.com/v1/me/tracks?offset=" + str(offsetVariable) + "&limit=50"
    tracks = requests.get(urll, headers=headers)
    tracksJson = tracks.json()
    if (modularTotal != 0):

        trackuris = []
        for k in range(0, modularTotal):

            # same idea but now we are only getting the leftover tracks
            trackuris.append(str(tracksJson["items"][k]["track"]["uri"]))
        trackStack.append(trackuris)
    # return the list to now populate the playlist!
    return trackStack


# populating the playlist: parameters are the list of trackuris we created from get_songs,
# the playlist id, the token we were authorized with, and the list of tracks from the playlist
def populate_playlists(token, PLAYLIST_ID, playlistTotal, trackStack):
    uriString = ""
    url = "https://api.spotify.com/v1/playlists/" + PLAYLIST_ID + "/tracks?uris=" + uriString
    headers = get_auth_header(token)

    head = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(token),
    }

    # we can now just pop the trackStack and add the tracks in increments of 50
    # we do this so we don't have to worry about how many tracks are in the liked
    # songs collection, nor the order since the stack maintains it

    while len(trackStack) != 0:
        # create substrings of the list of uris because spotify only takes so much at once,
        # in this case 50 was a workable number for spotify
        subTrackuri = trackStack.pop()
        # join each uri with %2C and replace colons with %3A
        subTrackuriString = "%2C".join(subTrackuri)
        while subTrackuriString.find(":") != -1:
            subTrackuriString = subTrackuriString.replace(":", "%3A")

        uriString = subTrackuriString
        # update the url with the new uriStrings and continue to loop through the tracks!
        url = ("https://api.spotify.com/v1/playlists/" + PLAYLIST_ID + "/tracks?uris=" + uriString
               + "&position=0")

        response = requests.post(url, headers=head)
        if response.status_code == 201:
            print('Tracks added successfully')
        else:
            print(f'Failed to add tracks: {response.status_code} - {response.text}')




# run what we have! enjoy!
token = get_token()
playlistParseTime = time.perf_counter()
playlistSongs = get_playlist_tracks(token, PLAYLIST_ID)
playlistParseTimeend = time.perf_counter()
print("time for parsing original automated playlist: " + str(playlistParseTimeend - playlistParseTime))
likedSongsParseTime = time.perf_counter()
song_list = get_songs(token, playlistSongs)
likedSongsParseTimeend = time.perf_counter()
print("time for parsing liked songs collection: " + str(likedSongsParseTimeend - likedSongsParseTime))
postingSongsParseTime = time.perf_counter()
populate_playlists(token, PLAYLIST_ID, playlistSongs, song_list)
postingSongsParseTimeend = time.perf_counter()
print("time for populating automated playlist: " + str(postingSongsParseTimeend - postingSongsParseTime))


