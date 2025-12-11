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

    resp = requests.post(url, json=payload, headers=headers)

    if resp.status_code != 200:
        raise ValueError(f"Mureka song generation failed: {resp.status_code} {resp.text}")

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

    resp = requests.get(url, headers=headers)

    # Mureka returns 200 + JSON always if valid
    if resp.status_code != 200:
        raise ValueError(f"Mureka status check failed: {resp.status_code} {resp.text}")

    return resp.json()
