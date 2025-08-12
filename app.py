from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import base64
from urllib.parse import urlencode
import time
import os

import requests
from Liked_Songs_Secret import CLIENT_ID, CLIENT_SECRET
from Spotify_Liked_Songs_main import get_playlist_tracks, get_songs, populate_playlists

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/authorize', methods=['POST'])
def authorize():
    playlist_id = request.form['playlist_id']
    session['playlist_id'] = playlist_id
    
    query = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": "http://localhost:5000/callback",
        "scope": "user-library-read playlist-modify-public playlist-modify-private"
    }
    auth_url = "https://accounts.spotify.com/authorize?" + urlencode(query)
    return jsonify({"auth_url": auth_url})

@app.route('/callback')
def callback():
    auth_code = request.args.get('code')
    if auth_code:
        return render_template('callback.html', auth_code=auth_code)
    return redirect(url_for('index'))

@app.route('/process', methods=['POST'])
def process():
    auth_code = request.json['auth_code']
    playlist_id = session.get('playlist_id')

    try:
    # Get access token
        url = "https://accounts.spotify.com/api/token"
        auth_header = base64.urlsafe_b64encode((CLIENT_ID + ':' + CLIENT_SECRET).encode())
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Basic {}".format(auth_header.decode("ascii"))
        }
        body = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "http://localhost:5000/callback",
        }

        response = requests.post(url, headers=headers, data=body)
        if response.status_code != 200:
            error_message = f"Failed to get access token: {response.status_code} - {response.text}"
            print(error_message)  
            return jsonify({"error": "Failed to get access token"})
        
        access_token = response.json()["access_token"]
        start_time = time.time()
        playlist_songs = get_playlist_tracks(access_token, playlist_id)
        song_list = get_songs(access_token, playlist_songs)
        tracks_posted = populate_playlists(access_token, playlist_id, playlist_songs, song_list)
        end_time = time.time()
        execution_time = end_time - start_time
        
        return jsonify({
            "success": True,
            "execution_time": f"{execution_time:.2f} seconds",
            "message": f"Playlist synchronized successfully! {tracks_posted} tracks were added."
        })
    
    except requests.Timeout:
        print("Request timed out")  # Log the timeout
        return jsonify({
            "error": "Request timed out. Please try again."
        })
    except requests.ConnectionError:
        print("Connection error")  # Log the connection error
        return jsonify({
            "error": "Failed to connect to Spotify API. Please check your internet connection."
        })
    
    except Exception as e:
        return jsonify({
            "error": f"An error occurred: {str(e)}"
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)