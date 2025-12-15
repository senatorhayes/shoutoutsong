import os
import time
import secrets
import re

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from lyrics_ai import generate_kid_lyrics, generate_adult_lyrics
from mureka_api import start_song_generation, query_song_status

# =====================================================
# TEMP SHARE STORE
# =====================================================
SHARE_STORE = {}
SHARE_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def _cleanup_share_store():
    now = time.time()
    expired = [
        token for token, rec in SHARE_STORE.items()
        if now - rec.get("created_at", now) > SHARE_TTL_SECONDS
    ]
    for token in expired:
        del SHARE_STORE[token]


# =====================================================
# APP SETUP
# =====================================================
app = FastAPI(title="Shoutout Song API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# STRIPE
# =====================================================
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# =====================================================
# MODELS
# =====================================================
class KidSongRequest(BaseModel):
    child_name: str
    theme: str
    duration_seconds: int = Field(60, ge=20, le=180)


class AdultSongRequest(BaseModel):
    recipient_name: str
    story_or_details: str
    genre: str = "pop"
    duration_seconds: int = Field(75, ge=30, le=240)


class CreateShareLinkRequest(BaseModel):
    song_id: str
    title: str | None = None


# =====================================================
# HEALTH
# =====================================================
@app.get("/")
def root():
    return {"status": "ok"}


# =====================================================
# SONG GENERATION
# =====================================================
@app.post("/generate-kid-song")
def generate_kid_song(req: KidSongRequest):
    lyrics = generate_kid_lyrics(req.child_name, req.theme)
    task_id = start_song_generation(
        lyrics=lyrics,
        prompt=f"Kids song for {req.child_name}",
        duration=req.duration_seconds,
        genre="pop",
    )
    return {"task_id": task_id, "lyrics": lyrics}


@app.post("/generate-adult-song")
def generate_adult_song(req: AdultSongRequest):
    lyrics = generate_adult_lyrics(
        req.recipient_name,
        "friend",
        "occasion",
        req.story_or_details,
        req.genre,
        "fun",
        "any",
    )
    task_id = start_song_generation(
        lyrics=lyrics,
        prompt=f"{req.genre} song",
        duration=req.duration_seconds,
        genre=req.genre,
    )
    return {"task_id": task_id, "lyrics": lyrics}


# =====================================================
# STATUS
# =====================================================
@app.get("/song-status/{task_id}")
def song_status(task_id: str):
    return query_song_status(task_id)


# =====================================================
# AUDIO (FULL)
# =====================================================
@app.get("/full-audio/{task_id}")
def full_audio(task_id: str):
    result = query_song_status(task_id)
    choices = result.get("choices", [])

    if not choices:
        raise HTTPException(status_code=404, detail="Audio not ready")

    audio_url = choices[0].get("url") or choices[0].get("audio_url")
    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio not ready")

    title = result.get("title") or "my-shoutout-song"
    safe_title = re.sub(r"[^a-z0-9\-]+", "", title.lower().replace(" ", "-"))

    response = RedirectResponse(audio_url)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{safe_title}.mp3"'
    )
    return response


# =====================================================
# SHARE LINKS
# =====================================================
@app.post("/create-share-link")
def create_share_link(req: CreateShareLinkRequest):
    _cleanup_share_store()

    status = query_song_status(req.song_id)
    choices = status.get("choices", [])
    if not choices:
        raise HTTPException(status_code=404, detail="Song not ready")

    audio_url = choices[0].get("url") or choices[0].get("audio_url")
    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio not ready")

    token = secrets.token_urlsafe(16)

    SHARE_STORE[token] = {
        "audio_url": audio_url,
        "title": req.title or "A Shoutout Song 🎵",
        "subtitle": "Made with Shoutout Song",
        "created_at": time.time(),
    }

    return {"share_url": f"https://shoutoutsong.com/s/{token}"}


@app.get("/share/{token}")
def get_share(token: str):
    _cleanup_share_store()
    rec = SHARE_STORE.get(token)
    if not rec:
        raise HTTPException(status_code=404, detail="Expired")
    return rec


@app.get("/s/{token}", response_class=HTMLResponse)
def share_unfurl(token: str):
    viewer = f"https://shoutoutsong.com/share.html?t={token}"
    return HTMLResponse(
        f"""
        <html>
        <head>
          <meta property="og:title" content="A Shoutout Song 🎵"/>
          <meta property="og:description" content="Listen to this custom shoutout song"/>
          <meta property="og:image" content="https://shoutoutsong.com/assets/share-default.png"/>
          <meta http-equiv="refresh" content="0; url={viewer}" />
        </head>
        <body></body>
        </html>
        """
    )
