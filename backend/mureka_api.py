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

    # Mureka requires duration between 120 and 300 seconds
    duration = max(120, min(300, int(duration)))

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

    if resp.status_code != 200:
        # Log the real reason from Mureka (server logs only, never shown to users)
        print(
            f"❌ Mureka generate failed: status={resp.status_code} "
            f"body={resp.text[:1000]} "
            f"payload_keys={list(payload.keys())} model={payload.get('model')} "
            f"key_set={bool(MUREKA_API_KEY)}"
        )

    if resp.status_code == 429:
        raise ValueError("Too many song requests right now. Please try again in a moment.")
    elif resp.status_code == 503:
        raise ValueError("Song generation service is temporarily busy. Please try again in 30 seconds.")
    elif resp.status_code != 200:
        raise ValueError(f"Song generation failed. Please try again. (Error {resp.status_code})")

    data = resp.json()
    return data["id"]


# ---------------------------------------------------------
# QUERY STATUS
# ---------------------------------------------------------
def query_song_status(task_id):
    """
    Query Mureka for status + final audio URLs.
    """

    url = f"{BASE_URL}/song/query/{task_id}"

    headers = {
        "Authorization": f"Bearer {MUREKA_API_KEY}",
        "Content-Type": "application/json",
    }

    resp = requests.get(url, headers=headers, timeout=10)

    if resp.status_code != 200:
        print(f"❌ Mureka status query failed: status={resp.status_code} body={resp.text[:500]}")
        raise ValueError(f"Unable to check song status. (Error {resp.status_code})")

    return resp.json()
