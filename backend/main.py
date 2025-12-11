# main.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from lyrics_ai import generate_kid_lyrics, generate_adult_lyrics
from mureka_api import start_song_generation, query_song_status


app = FastAPI(title="Songprinter API 🎵")


# -------------------------------------------------------------------
# CORS – allow local dev
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------------
# Request Models
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
    return {"message": "Songprinter backend is running 🎵"}


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

        style_bits = []

        if req.vibe == "sunny_kids":
            style_bits.append(
                "bright, playful kids music with catchy melodies and fun energy"
            )
        elif req.vibe == "lullaby":
            style_bits.append(
                "gentle lullaby with soft instrumentation and soothing vocals"
            )
        elif req.vibe == "pop_kids":
            style_bits.append(
                "modern kid-friendly pop with a hooky chorus and bounce"
            )
        elif req.vibe == "party_kids":
            style_bits.append(
                "upbeat energetic kids party track with exciting builds"
            )
        else:
            style_bits.append("fun melodic kids music")

        vt = req.voice_type.lower()
        if vt == "male":
            style_bits.append("natural-sounding male vocal")
        elif vt == "female":
            style_bits.append("natural-sounding female vocal")
        elif vt == "child":
            style_bits.append("natural child-like expressive vocal")
        else:
            style_bits.append("natural expressive vocal")

        style_prompt = (
            f"Song for {req.child_name}. Theme: {req.theme}. Occasion: {req.occasion}. "
            + " ".join(style_bits)
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
# ADULT / SPECIAL OCCASION SONG GENERATION
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

        style_bits = []

        if req.vibe == "fun":
            style_bits.append("fun upbeat production with a catchy chorus")
        elif req.vibe == "heartfelt":
            style_bits.append("emotional heartfelt arrangement")
        elif req.vibe == "epic":
            style_bits.append("big cinematic anthemic production")
        elif req.vibe == "silly":
            style_bits.append("playful comedic timing")
        elif req.vibe == "romantic":
            style_bits.append("romantic intimate melodic")
        else:
            style_bits.append("modern engaging production")

        style_bits.append(f"genre: {req.genre}")

        vt = req.voice_type.lower()
        if vt == "male":
            style_bits.append("natural-sounding male vocal")
        elif vt == "female":
            style_bits.append("natural-sounding female vocal")
        else:
            style_bits.append("natural expressive vocal")

        style_prompt = (
            f"Song for {req.recipient_name} ({req.relationship}). "
            f"Occasion: {req.occasion}. Include provided details. "
            + " ".join(style_bits)
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
# MOCK CHECKOUT (Temporary until real Stripe account is connected)
# -------------------------------------------------------------------

from fastapi import Request

@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    """
    Fake checkout session so the frontend flow works
    even before Stripe is activated.
    No payments are processed.
    """
    body = await request.json()
    song_id = body.get("song_id", "unknown")
    price_cents = body.get("price_cents", 499)  # default $4.99

    # Generate a fake Stripe-style URL
    fake_url = (
        "https://checkout.stripe.com/pay/"
        f"mock_session_{song_id}_{price_cents}"
    )

    return {
        "checkout_url": fake_url,
        "mode": "mock",
        "message": "Mock checkout active — no real payments are being processed."
    }

