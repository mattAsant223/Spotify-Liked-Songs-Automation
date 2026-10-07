from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import base64
import secrets
from urllib.parse import urlencode, urlparse
import time
import os

import requests
from dotenv import load_dotenv
from Spotify_Liked_Songs_main import parse_playlist_id, sync_playlist

load_dotenv()
CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:5000/callback")
SCOPE = "user-library-read playlist-read-private playlist-modify-public playlist-modify-private"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(24)


@app.before_request
def use_redirect_host():
    # the session cookie is tied to the host name, so if the app is opened on a different
    # host than the redirect URI (e.g. localhost vs 127.0.0.1) the login would be lost
    redirect_host = urlparse(REDIRECT_URI).netloc
    if request.host != redirect_host:
        return redirect(request.url.replace(request.host, redirect_host, 1))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/authorize', methods=['POST'])
def authorize():
    session['playlist_id'] = parse_playlist_id(request.form['playlist_id'])
    session['remove_unliked'] = 'remove_unliked' in request.form
    # random state value protects the callback against forged requests
    session['oauth_state'] = secrets.token_urlsafe(16)

    query = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": session['oauth_state'],
    }
    return redirect("https://accounts.spotify.com/authorize?" + urlencode(query))


@app.route('/callback')
def callback():
    if request.args.get('error'):
        return render_template('callback.html', error=f"Spotify authorization failed: {request.args['error']}")
    if not request.args.get('state') or request.args.get('state') != session.pop('oauth_state', None):
        return render_template('callback.html', error="Authorization state mismatch. Please try again.")

    # exchange the authorization code for an access token
    auth_header = base64.b64encode((CLIENT_ID + ':' + CLIENT_SECRET).encode())
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic {}".format(auth_header.decode("ascii"))
    }
    body = {
        "grant_type": "authorization_code",
        "code": request.args.get('code'),
        "redirect_uri": REDIRECT_URI,
    }
    try:
        response = requests.post("https://accounts.spotify.com/api/token",
                                 headers=headers, data=body, timeout=15)
    except requests.RequestException:
        return render_template('callback.html', error="Failed to connect to Spotify. Please try again.")
    if response.status_code != 200:
        print(f"Failed to get access token: {response.status_code} - {response.text}")
        return render_template('callback.html', error="Failed to get access token.")

    session['access_token'] = response.json()["access_token"]
    # the page runs the sync in the background and shows the result
    return render_template('callback.html')


@app.route('/sync', methods=['POST'])
def sync():
    access_token = session.get('access_token')
    playlist_id = session.get('playlist_id')
    if not access_token or not playlist_id:
        return jsonify({"error": "Not authorized. Please start again."}), 401

    try:
        start_time = time.time()
        added, removed = sync_playlist(access_token, playlist_id, session.get('remove_unliked', False))
        execution_time = time.time() - start_time
    except requests.Timeout:
        print("Request timed out")  # Log the timeout
        return jsonify({"error": "Request timed out. Please try again."}), 504
    except requests.ConnectionError:
        print("Connection error")  # Log the connection error
        return jsonify({"error": "Failed to connect to Spotify API. Please check your internet connection."}), 502
    except requests.HTTPError as e:
        print(f"Spotify API error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 404:
            return jsonify({"error": "Playlist not found. Check the playlist ID."}), 404
        if e.response.status_code == 403:
            return jsonify({"error": "You don't have permission to edit this playlist."}), 403
        return jsonify({"error": f"Spotify API error ({e.response.status_code})."}), 502

    message = f"Playlist synchronized successfully! {added} tracks were added"
    message += f" and {removed} were removed." if session.get('remove_unliked') else "."
    return jsonify({
        "success": True,
        "execution_time": f"{execution_time:.2f} seconds",
        "message": message,
        "playlist_url": f"https://open.spotify.com/playlist/{playlist_id}",
    })


if __name__ == '__main__':
    host = urlparse(REDIRECT_URI)
    app.run(debug=True, host=host.hostname, port=host.port or 5000)
