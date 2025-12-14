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
    audio_url: str
    title: str | None = None
    subtitle: str | None = None


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

from fastapi.responses import HTMLResponse


@app.post("/create-share-link")
def create_share_link(req: CreateShareLinkRequest):
    _cleanup_share_store()

    token = secrets.token_urlsafe(16)

    SHARE_STORE[token] = {
        "song_id": req.song_id,
        "audio_url": req.audio_url,   # FULL song (Mureka hosted)
        "title": req.title or "A Shoutout Song 🎵",
        "subtitle": req.subtitle or "Made on Shoutout Song",
        "created_at": time.time(),
    }

    return {
        # Canonical share URL (used by social platforms)
        "share_url": f"https://shoutoutsong.com/s/{token}",

        # Human viewer page
        "viewer_url": f"https://shoutoutsong.com/share.html?t={token}",

        "token": token,
    }


@app.get("/share/{token}")
def get_share(token: str):
    _cleanup_share_store()

    rec = SHARE_STORE.get(token)
    if not rec:
        raise HTTPException(status_code=404, detail="Share link expired or invalid")

    return rec


@app.get("/s/{token}", response_class=HTMLResponse)
def share_unfurl(token: str):
    _cleanup_share_store()

    rec = SHARE_STORE.get(token)
    if not rec:
        return HTMLResponse("Link expired", status_code=404)

    title = rec["title"]
    subtitle = rec["subtitle"]
    image = "https://shoutoutsong.com/assets/share-default.png"  # placeholder
    viewer = f"https://shoutoutsong.com/share.html?t={token}"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>

  <!-- Open Graph -->
  <meta property="og:type" content="music.song" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{subtitle}" />
  <meta property="og:image" content="{image}" />
  <meta property="og:url" content="https://shoutoutsong.com/s/{token}" />

  <!-- Twitter -->
  <meta name="twitter:card" content="summary_large_image" />

  <!-- Redirect humans -->
  <meta http-equiv="refresh" content="0; url={viewer}" />
</head>
<body>
  <script>
    window.location.replace("{viewer}");
  </script>
</body>
</html>
"""
    return HTMLResponse(html)

# -------------------------------------------------------------------
# AUDIO ACCESS
# -------------------------------------------------------------------

@app.get("/preview-audio/{task_id}")
def preview_audio(task_id: str):
    """
    Returns a SHORT preview URL (handled by Mureka).
    This is safe to expose before purchase.
    """
    result = query_song_status(task_id)

    preview_url = result.get("preview_url")
    if not preview_url:
        raise HTTPException(status_code=404, detail="Preview not ready")

    return {"url": preview_url}


@app.get("/full-audio/{task_id}")
def full_audio(task_id: str):
    """
    Returns FULL audio URL.
    Should only be called AFTER successful payment.
    """
    # TODO later: verify Stripe session or receipt
    result = query_song_status(task_id)

    full_url = result.get("audio_url")
    if not full_url:
        raise HTTPException(status_code=404, detail="Audio not ready")

    return {"url": full_url}

