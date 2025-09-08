from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import spotipy
from spotipy.oauth2 import SpotifyOAuth


load_dotenv() 

class SpotifySong(BaseModel):
    title: str
    artist: str
    album: str
    release_year: int

llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
parser = PydanticOutputParser(pydantic_object=SpotifySong)

def interpret_user_request(user_input: str):
    prompt = ChatPromptTemplate.from_template(
        "Extract the mood, genre, artist style, and other relevant playlist parameters from: '{user_input}'"
    )
    response = llm(prompt.format(user_input=user_input))
    return response

def search_spotify_tracks(params):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-modify-public"))
    results = sp.search(q=params, type="track", limit=20)
    tracks = results["tracks"]["items"]
    return tracks

def create_or_update_playlist(tracks, playlist_name="AI Playlist"):
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-modify-public"))
    user_id = sp.current_user()["id"]
    playlist = sp.user_playlist_create(user_id, playlist_name)
    track_ids = [track["id"] for track in tracks]
    sp.playlist_add_items(playlist["id"], track_ids)
    return playlist["external_urls"]["spotify"]


if __name__ == "__main__":
    user_input = input("Describe your playlist: ")
    params = interpret_user_request(user_input)
    tracks = search_spotify_tracks(params)
    playlist_url = create_or_update_playlist(tracks)
    print(f"Your playlist: {playlist_url}")

