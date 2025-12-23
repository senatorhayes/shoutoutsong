# mureka_api.py
import os
import requests

MUREKA_API_KEY = os.getenv("MUREKA_API_KEY")
BASE_URL = "https://api.mureka.ai/v1"


# ---------------------------------------------------------
# START GENERATION
# ---------------------------------------------------------
def start_song_generation(lyrics, prompt, duration, genre="pop"):
    """
    Send a generation request to Mureka.
    Returns: task_id string
    """

    payload = {
        "model": "auto",
        "lyrics": lyrics,
        "prompt": prompt,
        "duration": duration,
        "genre": genre,
    }

    headers = {
        "Authorization": f"Bearer {MUREKA_API_KEY}",
        "Content-Type": "application/json",
    }

    url = f"{BASE_URL}/song/generate"

    resp = requests.post(url, json=payload, headers=headers, timeout=30)

    if resp.status_code == 429:
        # Rate limit hit
        raise ValueError("Too many song requests right now. Please try again in a moment.")
    elif resp.status_code == 503:
        # Service unavailable
        raise ValueError("Song generation service is temporarily busy. Please try again in 30 seconds.")
    elif resp.status_code != 200:
        # Other error
        raise ValueError(f"Song generation failed. Please try again. (Error {resp.status_code})")

    data = resp.json()
    return data["id"]


# ---------------------------------------------------------
# QUERY STATUS
# ---------------------------------------------------------
def query_song_status(task_id):
    """
    Query Mureka for status + final audio URLs.
    Uses the new working endpoint discovered through testing.
    """

    url = f"{BASE_URL}/song/query/{task_id}"

    headers = {
        "Authorization": f"Bearer {MUREKA_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.get(url, headers=headers, timeout=10)

    # Mureka returns 200 + JSON always if valid
    if resp.status_code != 200:
        raise ValueError(f"Unable to check song status. (Error {resp.status_code})")

    return resp.json()
