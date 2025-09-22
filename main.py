from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from tools import parse_llm_response, filter_tracks, clean_user_input


load_dotenv() 

class SpotifySong(BaseModel):
    title: str
    artist: str
    album: str
    release_year: int

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

def interpret_user_request(user_input: str):
    prompt = ChatPromptTemplate.from_template(
        "Extract the mood, genre, artist style, and other relevant playlist parameters from: '{user_input}'. Respond in format: Mood: <mood>, Genre: <genre>, Artist: <artist>, Energy: <energy>, Popularity: <popularity>"
    )
    prompt_str = prompt.format(user_input=user_input)
    response = llm.invoke(prompt_str)
    return response.content

def search_spotify_tracks(params):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-modify-public"))
    query_parts = []
    if "genre" in params and params["genre"]:
        query_parts.append(f'genre:"{params["genre"]}"')
    if "artist" in params and params["artist"]:
        query_parts.append(f'artist:"{params["artist"]}"')
    if "mood" in params and params["mood"]:
        query_parts.append(params["mood"])
    query = " ".join(query_parts).strip()
    if not query:
        print("No valid search parameters found. Please try a more descriptive request.")
        return []
    results = sp.search(q=query, type="track", limit=20)
    tracks = results["tracks"]["items"]
    track_ids = [track["id"] for track in tracks]
    if not track_ids:
        print("No tracks found for the given parameters.")
        return []
    features = sp.audio_features(track_ids)
    for track, feature in zip(tracks, features):
        track["audio_features"] = feature if feature else {}
    min_energy = 0.5 if params.get("energy", "medium") == "high" else 0.2
    min_popularity = 70 if params.get("popularity", "medium") == "high" else 50
    filtered_tracks = filter_tracks(tracks, min_energy=min_energy, min_popularity=min_popularity)
    return filtered_tracks

def create_or_update_playlist(tracks, playlist_name="AI Playlist"):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-modify-public"))
    user_id = sp.current_user()["id"]
    playlist = sp.user_playlist_create(user_id, playlist_name)
    track_ids = [track["id"] for track in tracks]
    if track_ids:
        sp.playlist_add_items(playlist["id"], track_ids)
    return playlist["external_urls"]["spotify"]


if __name__ == "__main__":
    user_input = input("Describe your playlist: ")
    cleaned_input = clean_user_input(user_input)
    llm_response = interpret_user_request(cleaned_input)
    params = parse_llm_response(llm_response)
    tracks = search_spotify_tracks(params)
    if tracks:
        playlist_url = create_or_update_playlist(tracks)
        print(f"Your playlist: {playlist_url}")
    else:
        print("No tracks found for the given parameters.")

