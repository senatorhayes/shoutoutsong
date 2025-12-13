# main.py
import os
import time
import secrets

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from lyrics_ai import generate_kid_lyrics, generate_adult_lyrics
from mureka_api import start_song_generation, query_song_status


# =====================================================
# TEMP SHARE STORE (ephemeral, safe for now)
# =====================================================
SHARE_STORE = {}  # token -> record
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
app = FastAPI(title="Shoutout Song API 🎵")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for now
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
    preview_url: str | None = None
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
    try:
        lyrics = generate_kid_lyrics(
            child_name=req.child_name,
            theme=req.theme,
            occasion=req.occasion,
            vibe=req.vibe,
            voice_type=req.voice_type,
        )

        style_prompt = (
            f"Song for {req.child_name}. Theme: {req.theme}. "
            f"Occasion: {req.occasion}. Bright, playful kids music."
        )

        task_id = start_song_generation(
            lyrics=lyrics,
            prompt=style_prompt,
            duration=req.duration_seconds,
            genre="pop",
        )

        return {
            "status": "pending",
            "task_id": task_id,
            "lyrics": lyrics,
            "kind": "kid",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-adult-song")
def generate_adult_song(req: AdultSongRequest):
    try:
        lyrics = generate_adult_lyrics(
            recipient_name=req.recipient_name,
            relationship=req.relationship,
            occasion=req.occasion,
            story_or_details=req.story_or_details,
            genre=req.genre,
            vibe=req.vibe,
            voice_type=req.voice_type,
        )

        style_prompt = (
            f"Song for {req.recipient_name} ({req.relationship}). "
            f"Occasion: {req.occasion}. Genre: {req.genre}. Vibe: {req.vibe}."
        )

        task_id = start_song_generation(
            lyrics=lyrics,
            prompt=style_prompt,
            duration=req.duration_seconds,
            genre=req.genre,
        )

        return {
            "status": "pending",
            "task_id": task_id,
            "lyrics": lyrics,
            "kind": "adult",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# POLLING
# =====================================================
@app.get("/song-status/{task_id}")
def song_status(task_id: str):
    try:
        return query_song_status(task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# STRIPE CHECKOUT
# =====================================================
@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    body = await request.json()
    song_id = body.get("song_id", "unknown")

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
# SHARE LINKS (PREVIEW PAGE)
# =====================================================
@app.post("/create-share-link")
def create_share_link(req: CreateShareLinkRequest):
    _cleanup_share_store()

    token = "s_" + secrets.token_urlsafe(24)

    SHARE_STORE[token] = {
        "song_id": req.song_id,
        "preview_url": req.preview_url,
        "title": req.title,
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
        raise HTTPException(status_code=404, detail="Share link expired or invalid")

    return rec
