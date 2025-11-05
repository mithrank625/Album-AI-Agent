from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tools import parse_llm_response, filter_tracks, clean_user_input
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os

load_dotenv() 

class SpotifySong(BaseModel):
    title: str
    artist: str
    album: str
    release_year: int
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    llm = None
else:
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, api_key=openai_api_key)

def interpret_user_request(user_input: str):
    if llm is None:
        return f"Mood: {user_input.lower()}, Genre: pop, Artist: , Energy: medium, Popularity: medium"
    
    prompt = ChatPromptTemplate.from_template(
        "Extract the mood, genre, artist style, and other relevant playlist parameters from: '{user_input}'. Respond in format: Mood: <mood>, Genre: <genre>, Artist: <artist>, Energy: <energy>, Popularity: <popularity>"
    )
    prompt_str = prompt.format(user_input=user_input)
    response = llm.invoke(prompt_str)
    return response.content

def search_spotify_tracks(params):
    try:
        client_id = os.getenv("SPOTIPY_CLIENT_ID")
        client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:5000/callback")
        
        if not client_id or not client_secret:
            raise Exception("Spotify API credentials not configured. Please set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET in your .env file.")
        
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-modify-public user-read-private user-read-email"
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        query_parts = []
        if "genre" in params and params["genre"]:
            query_parts.append(f'genre:"{params["genre"]}"')
        if "artist" in params and params["artist"]:
            query_parts.append(f'artist:"{params["artist"]}"')
        if "mood" in params and params["mood"]:
            query_parts.append(params["mood"])
        
        if not query_parts:
            query = params.get("mood", "popular")
        else:
            query = " ".join(query_parts).strip()
        
        song_count = params.get("song_count", 20)
        limit = min(song_count, 50)
        
        results = sp.search(q=query, type="track", limit=limit)
        tracks = results["tracks"]["items"]
        
        if len(tracks) < song_count and results["tracks"]["next"]:
            offset = len(tracks)
            while len(tracks) < song_count and offset < 1000: 
                remaining = min(song_count - len(tracks), 50)
                additional_results = sp.search(q=query, type="track", limit=remaining, offset=offset)
                additional_tracks = additional_results["tracks"]["items"]
                if not additional_tracks:
                    break
                tracks.extend(additional_tracks)
                offset += len(additional_tracks)
        
        if not tracks:
            results = sp.search(q=params.get("mood", "music"), type="track", limit=limit)
            tracks = results["tracks"]["items"]
            
            # If we need more tracks, make additional requests
            if len(tracks) < song_count and results["tracks"]["next"]:
                offset = len(tracks)
                while len(tracks) < song_count and offset < 1000:
                    remaining = min(song_count - len(tracks), 50)
                    additional_results = sp.search(q=params.get("mood", "music"), type="track", limit=remaining, offset=offset)
                    additional_tracks = additional_results["tracks"]["items"]
                    if not additional_tracks:
                        break
                    tracks.extend(additional_tracks)
                    offset += len(additional_tracks)
        
        if not tracks:
            return []
        
        track_ids = [track["id"] for track in tracks]
        try:
            features = sp.audio_features(track_ids)
            for track, feature in zip(tracks, features):
                track["audio_features"] = feature if feature else {}
        except Exception as e:
            print(f"Warning: Could not get audio features: {e}")
            for track in tracks:
                track["audio_features"] = {}
        
        min_energy = 0.5 if params.get("energy", "medium") == "high" else 0.2
        min_popularity = 70 if params.get("popularity", "medium") == "high" else 50
        filtered_tracks = filter_tracks(tracks, min_energy=min_energy, min_popularity=min_popularity)
        
        return filtered_tracks
        
    except Exception as e:
        print(f"Error searching Spotify tracks: {str(e)}")
        return []

def create_or_update_playlist(tracks, playlist_name="AI Playlist"):
    try:
        client_id = os.getenv("SPOTIPY_CLIENT_ID")
        client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:5000/callback")
        
        if not client_id or not client_secret:
            raise Exception("Spotify API credentials not configured.")
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="playlist-modify-public user-read-private user-read-email"
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        user_id = sp.current_user()["id"]
        playlist = sp.user_playlist_create(user_id, playlist_name)
        
        track_ids = [track["id"] for track in tracks]
        if track_ids:
            sp.playlist_add_items(playlist["id"], track_ids)
        
        return playlist["external_urls"]["spotify"]
        
    except Exception as e:
        print(f"Error creating playlist: {str(e)}")
        return "https://open.spotify.com/playlist/demo"

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/callback')
def callback():
    """Handle Spotify OAuth callback"""
    return redirect(url_for('index'))

@app.route('/create_playlist', methods=['POST'])
def create_playlist():
    """Create playlist when user clicks the link"""
    try:
        if 'pending_tracks' not in session or not session['pending_tracks']:
            return jsonify({
                'success': False,
                'error': 'No pending tracks found. Please generate a playlist first.'
            })
        
        pending_tracks = session['pending_tracks']
        playlist_name = session.get('playlist_name', 'AI Playlist')
        
        track_objects = [{'id': track['id']} for track in pending_tracks]
        playlist_url = create_or_update_playlist(track_objects, playlist_name)
        
        session.pop('pending_tracks', None)
        session.pop('playlist_name', None)
        
        return jsonify({
            'success': True,
            'playlist_url': playlist_url
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An error occurred while creating the playlist: {str(e)}'
        })

@app.route('/generate_playlist', methods=['POST'])
def generate_playlist():
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided in request.'
            })
        
        vibe = data.get('vibe', '').strip()
        popularity = data.get('popularity', 'medium')
        song_count = int(data.get('song_count', 10))
        
        if not vibe:
            return jsonify({
                'success': False,
                'error': 'Please provide a vibe or mood for your playlist.'
            })
        
        if song_count < 1 or song_count > 50:
            song_count = min(max(song_count, 1), 50)

        user_input = f"Create a {vibe} playlist with {song_count} songs, popularity level: {popularity}"
        
        cleaned_input = clean_user_input(user_input)
        llm_response = interpret_user_request(cleaned_input)
        params = parse_llm_response(llm_response)

        params['song_count'] = song_count
        
        tracks = search_spotify_tracks(params)
        
        if tracks:
            tracks = tracks[:song_count]

            track_data = [{'id': track['id'], 'name': track['name'], 'artist': track['artists'][0]['name']} for track in tracks]
            session['pending_tracks'] = track_data
            session['playlist_name'] = f"{vibe.title()} Playlist"
            return jsonify({
                'success': True,
                'playlist_url': None,
                'track_count': len(tracks),
                'tracks': [{'name': track['name'], 'artist': track['artists'][0]['name']} for track in tracks]
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No tracks found for the given parameters. Please try a different vibe or check your Spotify API configuration.'
            })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Invalid input parameters. Please check your song count and try again.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'An error occurred: {str(e)}'
        })

if __name__ == "__main__":
    app.run(debug=True)
