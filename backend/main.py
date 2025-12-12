# main.py
import os

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from lyrics_ai import generate_kid_lyrics, generate_adult_lyrics
from mureka_api import start_song_generation, query_song_status


# -------------------------------------------------------------------
# APP SETUP
# -------------------------------------------------------------------
app = FastAPI(title="Shoutout Song API 🎵")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# STRIPE CONFIG
# -------------------------------------------------------------------
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# -------------------------------------------------------------------
# REQUEST MODELS
# -------------------------------------------------------------------
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


# -------------------------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------------------------
@app.get("/")
def root():
    return {"message": "Shoutout Song backend is running 🎵"}


# -------------------------------------------------------------------
# KIDS SONG GENERATION
# -------------------------------------------------------------------
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
            f"Occasion: {req.occasion}. Fun, playful kids music."
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


# -------------------------------------------------------------------
# ADULT SONG GENERATION
# -------------------------------------------------------------------
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


# -------------------------------------------------------------------
# POLLING ENDPOINT
# -------------------------------------------------------------------
@app.get("/song-status/{task_id}")
def song_status(task_id: str):
    try:
        return query_song_status(task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------------------
# STRIPE CHECKOUT (TEST MODE, SAFE FALLBACK)
# -------------------------------------------------------------------
@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    """
    Creates a Stripe Checkout Session (TEST MODE).
    Falls back to mock checkout if Stripe is not configured.
    """
    body = await request.json()
    song_id = body.get("song_id", "unknown")

    # Safe fallback (local dev / missing env vars)
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        return {
            "checkout_url": "https://checkout.stripe.com/pay/mock_session",
            "mode": "mock",
            "message": "Stripe not configured — mock checkout used.",
        }

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }
        ],
        success_url=f"https://shoutoutsong.com/success?song_id={song_id}",
        cancel_url="https://shoutoutsong.com/cancel",
        metadata={"song_id": song_id},
    )

    return {
        "checkout_url": session.url,
        "mode": "stripe_test",
    }
