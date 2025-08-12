import requests

# this function retrieves a token for us to be authorized to let spotify get information within the
# scope we identify, logic was transferred to the app.py file
# def get_token():
#     query = {
#         "client_id": CLIENT_ID,
#         "response_type": "code",
#         "redirect_uri": REDIRECT_URI,
#         "scope": "user-library-read playlist-modify-public playlist-modify-private"
#     }

#     webbrowser.open("https://accounts.spotify.com/authorize?" + urlencode(query))

#     # Prompt the user to enter the authorization code after being redirected
#     auth_code = input("After authorizing this application, enter the authorization code: ")
#     url = "https://accounts.spotify.com/api/token"

#     auth_header = base64.urlsafe_b64encode((CLIENT_ID + ':' + CLIENT_SECRET).encode())
#     headers = {
#         "Content-Type": "application/x-www-form-urlencoded",
#         "Authorization": "Basic {}".format(auth_header.decode("ascii"))
#     }
#     body = {
#         "grant_type": "authorization_code",
#         "code": auth_code,
#         "redirect_uri": REDIRECT_URI,
#     }
#     response = requests.post(url, headers=headers, data=body)
#     return response.json()["access_token"]


# simple function that shorthands the header for authorization
def get_auth_header(token):
    return {"Authorization": "Bearer " + token}


def get_playlist_tracks(token, playlist_id):
    offset_variable = 0    # spotify api's max track return is 50
    url = ("https://api.spotify.com/v1/playlists/" + playlist_id + "/tracks?offset=" +
           str(offset_variable) + "&limit=50")
    headers = get_auth_header(token)
    playlist_tracks = requests.get(url, headers=headers)
    playlist_tracks_json = playlist_tracks.json()
    # grabbing the total num for speed assuming you dont have duplicates or added errors, if you want to check each track 
    # you can implement a map here and iterate through the playlist 
    # to check if the uri exists in get songs
    playlist_total = playlist_tracks_json["total"]
    return playlist_total

# get the songs in the liked playlist

def get_songs(token, playlist_total):

    # keep track also of how much were offsetting to grab every track possible
    offset_variable = 0
    # plug in offset variable in the url, and we want the limit to be as large as possible
    # spotify api's max is 50
    urll = "https://api.spotify.com/v1/me/tracks?offset=" + str(0) + "&limit=50"
    headers = get_auth_header(token)
    tracks = requests.get(urll, headers=headers)
    tracks_json = tracks.json()
    # create variable to get how much total tracks were going to add
    liked_songs_total = tracks_json["total"] - playlist_total
    modular_total = liked_songs_total % 50
    iterative_steps = liked_songs_total // 50

    # use a stack to conviently keep order of the tracks we want to add
    track_stack = []
    for i in range(0, iterative_steps):
        urll = "https://api.spotify.com/v1/me/tracks?offset=" + str(offset_variable) + "&limit=50"
        tracks = requests.get(urll, headers=headers)
        tracks_json = tracks.json()
        track_uris = []
        for j in range(0, 50):
            track_uris.append(str(tracks_json["items"][j]["track"]["uri"]))
        track_stack.append(track_uris)
        offset_variable += 50

    # once the loop is finished, add those last few tracks that we identified through getting the remainder
    urll = "https://api.spotify.com/v1/me/tracks?offset=" + str(offset_variable) + "&limit=50"
    tracks = requests.get(urll, headers=headers)
    tracks_json = tracks.json()
    if (modular_total != 0):
        track_uris = []
        for k in range(0, modular_total):
            track_uris.append(str(tracks_json["items"][k]["track"]["uri"]))
        track_stack.append(track_uris)
    # return stack to populate playlist function
    return track_stack


# populating the playlist
def populate_playlists(token, PLAYLIST_ID, playlist_total, track_stack):
    uri_string = ""
    url = "https://api.spotify.com/v1/playlists/" + PLAYLIST_ID + "/tracks?uris=" + uri_string
    headers = get_auth_header(token)

    head = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(token),
    }

    # we can now just pop the track_stack and add the tracks
    liked_songs_total = 0
    while len(track_stack) != 0:
        # create substrings of the list of uris because spotify only takes so much at once,
        # in this case 50 was a workable number for spotify
        sub_track_uris = track_stack.pop()
        # join each uri with %2C and replace colons with %3A
        subtrack_uri_string = "%2C".join(sub_track_uris)
        while subtrack_uri_string.find(":") != -1:
            subtrack_uri_string = subtrack_uri_string.replace(":", "%3A")

        uri_string = subtrack_uri_string
        # update the url with the new uri_strings
        url = ("https://api.spotify.com/v1/playlists/" + PLAYLIST_ID + "/tracks?uris=" + uri_string
               + "&position=0")

        response = requests.post(url, headers=head)
        if response.status_code == 201:
            print(len(sub_track_uris))
            liked_songs_total += len(sub_track_uris)
            print('Tracks added successfully')
        else:
            print(f'Failed to add tracks: {response.status_code} - {response.text}')
    # return total tracks added successfully
    return liked_songs_total
