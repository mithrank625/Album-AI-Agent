import re

def filter_tracks(tracks, min_energy=0.5, min_popularity=50):
    filtered = []
    for track in tracks:
        features = track.get("audio_features", {})
        if features.get("energy", 0) >= min_energy and track.get("popularity", 0) >= min_popularity:
            filtered.append(track)
    return filtered

def clean_user_input(user_input):
    return user_input.strip().lower()

def parse_llm_response(response):
    params = {}
    matches = re.findall(r'(\w+):\s*([^,]+)', response)
    for key, value in matches:
        params[key.strip().lower()] = value.strip().lower()
    return params

# Add more helper functions as needed