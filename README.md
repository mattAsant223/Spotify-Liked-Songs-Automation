# Spotify-Liked-Songs-Automation
Spotify Liked Songs Automation

The main purpose of this application was to make retrieving tracks from your liked songs into a playlist automated which is an much easier process. Why would you want to do this? Main reason is allowing other spotify users to see your liked songs playlist, and to have the rest of the features that come with spotify playlist rather than just downloading tracks, which is the only function of the liked songs collection.

This app is not deployed, so you have to run it locally. The front end is built with Flask.

## Setup

1. Create an app in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and add this Redirect URI in its settings:
   `http://127.0.0.1:5000/callback`
2. Copy `.env.example` to `.env` and fill in your Client ID and Client Secret. `.env` is git-ignored, so your keys stay out of the repo.
3. Install dependencies and run:
   ```
   pip install -r requirements.txt
   python app.py
   ```
4. Open http://127.0.0.1:5000, paste a playlist link or ID, and log in with Spotify. You're redirected back automatically and the sync runs.

The sync compares the actual tracks in your Liked Songs and the playlist. Missing liked songs are added at the top, newest first, and running it again only adds what's new. Tick the checkbox to also remove songs you've since unliked.

Hope you enjoy the program and making life using spotify easier!
