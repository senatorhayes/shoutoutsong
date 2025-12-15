# main.py
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
# TEMP SHARE STORE (ephemeral)
# =====================================================
SHARE_STORE = {}
SHARE_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def _cleanup_share_store():
    now = time.time()
    expired = [
        token
        for token, rec in SHARE_STORE.items()
        if now - rec.get("created_at", now) > SHARE_TTL_SECONDS
    ]
    for token in expired:
        del SHARE_STORE[token]


# =====================================================
# APP SETUP
# =====================================================
app = FastAPI(title="Shoutout Song API 🎵")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# STRIPE CONFIG
# =====================================================
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# =====================================================
# REQUEST MODELS
# =====================================================
class KidSongRequest(BaseModel):
    child_name: str
    theme: str
    occasion: str = "everyday"
    vibe: str = "sunny_kids"
    voice_type: str = "any"
    duration_seconds: int = Field(60, ge=20, le=180)


class AdultSongRequest(BaseModel):
    recipient_name: str
    relationship: str = "friend"
    occasion: str = "birthday"
    story_or_details: str
    genre: str = "pop"
    vibe: str = "fun"
    voice_type: str = "any"
    duration_seconds: int = Field(75, ge=30, le=240)


class CreateShareLinkRequest(BaseModel):
    song_id: str
    title: str | None = None


# =====================================================
# HEALTH CHECK
# =====================================================
@app.get("/")
def root():
    return {"message": "Shoutout Song backend is running 🎵"}


# =====================================================
# SONG GENERATION
# =====================================================
@app.post("/generate-kid-song")
def generate_kid_song(req: KidSongRequest):
    lyrics = generate_kid_lyrics(
        child_name=req.child_name,
        theme=req.theme,
        occasion=req.occasion,
        vibe=req.vibe,
        voice_type=req.voice_type,
    )

    task_id = start_song_generation(
        lyrics=lyrics,
        prompt=f"Bright playful kids song for {req.child_name}",
        duration=req.duration_seconds,
        genre="pop",
    )

    return {
        "status": "pending",
        "task_id": task_id,
        "lyrics": lyrics,
        "kind": "kid",
    }


@app.post("/generate-adult-song")
def generate_adult_song(req: AdultSongRequest):
    lyrics = generate_adult_lyrics(
        recipient_name=req.recipient_name,
        relationship=req.relationship,
        occasion=req.occasion,
        story_or_details=req.story_or_details,
        genre=req.genre,
        vibe=req.vibe,
        voice_type=req.voice_type,
    )

    task_id = start_song_generation(
        lyrics=lyrics,
        prompt=f"{req.genre} song for {req.recipient_name}",
        duration=req.duration_seconds,
        genre=req.genre,
    )

    return {
        "status": "pending",
        "task_id": task_id,
        "lyrics": lyrics,
        "kind": "adult",
    }


# =====================================================
# POLLING
# =====================================================
@app.get("/song-status/{task_id}")
def song_status(task_id: str):
    return query_song_status(task_id)


# =====================================================
# STRIPE CHECKOUT
# =====================================================
@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    body = await request.json()
    song_id = body.get("song_id")

    if not song_id:
        raise HTTPException(status_code=400, detail="Missing song_id")

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        success_url=f"https://shoutoutsong.com/success?song_id={song_id}",
        cancel_url="https://shoutoutsong.com/cancel",
        client_reference_id=song_id,
        metadata={"song_id": song_id},
    )

    return {"checkout_url": session.url}


# =====================================================
# AUDIO ACCESS (MUREKA HOSTED)
# =====================================================
@app.get("/preview-audio/{task_id}")
def preview_audio(task_id: str):
    result = query_song_status(task_id)
    choices = result.get("choices", [])

    if not choices:
        raise HTTPException(status_code=404, detail="Preview not ready")

    preview_url = choices[0].get("preview_url")
    if not preview_url:
        raise HTTPException(status_code=404, detail="Preview not ready")

    return {"url": preview_url}


@app.get("/full-audio/{task_id}")
def full_audio(task_id: str):
    result = query_song_status(task_id)
    choices = result.get("choices", [])

    if not choices:
        raise HTTPException(status_code=404, detail="Audio not ready")

    audio_url = choices[0].get("url") or choices[0].get("audio_url")
    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio not ready")

    title = (
        result.get("title")
        or result.get("prompt")
        or "my-shoutout-song"
    )

    safe_title = re.sub(
        r"[^a-z0-9\-]+",
        "",
        title.lower().replace(" ", "-")
    )

    response = RedirectResponse(audio_url)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="{safe_title}.mp3"'
    )
    return response


# =====================================================
# SHARE LINKS (TOKEN-BASED)
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
        "song_id": req.song_id,
        "audio_url": audio_url,
        "title": req.title or "A custom shoutout song 🎵",
        "subtitle": "Made with Shoutout Song",
        "created_at": time.time(),
    }

    return {
        "share_url": f"https://shoutoutsong.com/s/{token}",
        "token": token,
    }


@app.get("/share/{token}")
def get_share(token: str):
    _cleanup_share_store()

    rec = SHARE_STORE.get(token)
    if not rec:
        raise HTTPException(status_code=404, detail="Invalid or expired share link")

    return rec


@app.get("/s/{token}", response_class=HTMLResponse)
def share_unfurl(token: str):
    _cleanup_share_store()

    rec = SHARE_STORE.get(token)
    if not rec:
        return HTMLResponse("Link expired", status_code=404)

    viewer = f"https://shoutoutsong.com/share.html?t={token}"

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{rec['title']}</title>
  <meta property="og:type" content="music.song" />
  <meta property="og:title" content="{rec['title']}" />
  <meta property="og:description" content="{rec['subtitle']}" />
  <meta property="og:image" content="https://shoutoutsong.com/assets/share-default.png" />
  <meta property="og:url" content="https://shoutoutsong.com/s/{token}" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta http-equiv="refresh" content="0; url={viewer}" />
</head>
<body>
  <script>window.location.replace("{viewer}")</script>
</body>
</html>
"""
    return HTMLResponse(html)
