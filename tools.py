import re

def filter_tracks(tracks, min_energy=0.5, min_popularity=50):
    filtered = []
    for track in tracks:
        features = track.get("audio_features", {})
        popularity = track.get("popularity", 0)
        
        if not features:
            if popularity >= min_popularity:
                filtered.append(track)
            elif popularity >= min_popularity * 0.7: 
                filtered.append(track)
        else:
            energy = features.get("energy", 0)
            if energy >= min_energy and popularity >= min_popularity:
                filtered.append(track)
            elif energy >= min_energy * 0.8 and popularity >= min_popularity * 0.7: 
                filtered.append(track)
    
    if not filtered:
        return tracks
    
    return filtered

def clean_user_input(user_input): 
    return user_input.strip().lower()
def parse_llm_response(response):
    params = {}
    
    if not response:
        return {
            'mood': 'popular',
            'genre': 'pop',
            'energy': 'medium',
            'popularity': 'medium'
        }
    
    matches = re.findall(r'(\w+):\s*([^,]+)', response)
    for key, value in matches:
        params[key.strip().lower()] = value.strip().lower()
    
    if not params:
        mood_keywords = ['chill', 'energetic', 'happy', 'sad', 'romantic', 'workout', 'party', 'calm', 'upbeat', 'melancholy']
        response_lower = response.lower()
        for keyword in mood_keywords:
            if keyword in response_lower:
                params['mood'] = keyword
                break
    
    if not params:
        params = {
            'mood': 'popular',
            'genre': 'pop',
            'energy': 'medium',
            'popularity': 'medium'
        }
    
    return params