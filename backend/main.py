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

# Import email sender (will handle gracefully if not configured)
try:
    from email_sender import send_song_email
    EMAIL_ENABLED = True
except ImportError:
    print("⚠️ email_sender.py not found - emails disabled")
    EMAIL_ENABLED = False

# =====================================================
# PERSISTENT SHARE STORE (JSON file)
# =====================================================
import json
from pathlib import Path

SHARE_FILE = Path("/opt/render/project/data/share_store.json")  # Persistent disk on Render
SHARE_TTL_SECONDS = 60 * 60 * 24 * 365 * 2  # 2 years


def _load_share_store():
    """Load share store from file"""
    if not SHARE_FILE.exists():
        return {}
    try:
        with open(SHARE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}


def _save_share_store(store):
    """Save share store to file"""
    try:
        # Ensure directory exists
        SHARE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SHARE_FILE, 'w') as f:
            json.dump(store, f)
    except Exception as e:
        print(f"Error saving share store: {e}")


def _cleanup_share_store(store):
    """Remove expired shares"""
    now = time.time()
    expired = [
        token for token, rec in store.items()
        if now - rec.get("created_at", now) > SHARE_TTL_SECONDS
    ]
    for token in expired:
        del store[token]
    return store


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

if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
    print("⚠️ Stripe is NOT configured")

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
    recipient_name: str | None = None
    subject: str | None = None


# =====================================================
# HEALTH (GET + HEAD)
# =====================================================
@app.get("/")
def root():
    return {"status": "ok", "message": "Shoutout Song API"}


@app.head("/")
def head_root():
    return


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
# STRIPE CHECKOUT (🔥 THIS WAS MISSING)
# =====================================================
@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    body = await request.json() or {}
    song_id = body.get("song_id")
    recipient_name = body.get("recipient_name", "")
    subject = body.get("subject", "")

    if not song_id:
        raise HTTPException(status_code=400, detail="Missing song_id")

    # Build success URL with name and subject
    from urllib.parse import quote
    success_url = f"https://shoutoutsong.com/success?song_id={song_id}"
    if recipient_name:
        success_url += f"&name={quote(recipient_name)}"
    if subject:
        success_url += f"&subject={quote(subject)}"

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=success_url,
            cancel_url="https://shoutoutsong.com/cancel",
            client_reference_id=song_id,
            metadata={
                "song_id": song_id,
                "recipient_name": recipient_name,
                "subject": subject,
            },
            customer_email=None,  # Let Stripe collect it
        )
        return {"checkout_url": session.url}
    except Exception as e:
        print("Stripe error:", e)
        raise HTTPException(status_code=500, detail="Stripe checkout failed")


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
    store = _load_share_store()
    store = _cleanup_share_store(store)

    status = query_song_status(req.song_id)
    choices = status.get("choices", [])
    if not choices:
        raise HTTPException(status_code=404, detail="Song not ready")

    audio_url = choices[0].get("url") or choices[0].get("audio_url")
    if not audio_url:
        raise HTTPException(status_code=404, detail="Audio not ready")

    token = secrets.token_urlsafe(16)

    store[token] = {
        "song_id": req.song_id,
        "audio_url": audio_url,
        "title": req.title or "A Shoutout Song 🎵",
        "subtitle": "Made with Shoutout Song",
        "recipient_name": req.recipient_name or "",
        "subject": req.subject or "",
        "created_at": time.time(),
    }

    _save_share_store(store)
    return {"share_url": f"https://shoutoutsong.com/share.html?t={token}"}


@app.get("/share/{token}")
def get_share(token: str):
    store = _load_share_store()
    store = _cleanup_share_store(store)
    rec = store.get(token)
    if not rec:
        raise HTTPException(status_code=404, detail="Expired")
    return rec


@app.get("/s/{token}", response_class=HTMLResponse)
def share_unfurl(token: str):
    # Load share data to get name and subject
    store = _load_share_store()
    rec = store.get(token)
    
    # Default values if share not found
    if rec:
        recipient_name = rec.get("recipient_name", "someone special")
        subject = rec.get("subject", "something special")
        og_title = f"Shoutout Song - {recipient_name} and their love for {subject} 🎵"
        og_description = f"Listen to this custom shoutout song about {recipient_name}!"
    else:
        og_title = "A Shoutout Song 🎵"
        og_description = "Listen to this custom shoutout song"
    
    viewer = f"https://shoutoutsong.com/share.html?t={token}"
    return HTMLResponse(
        f"""
        <html>
        <head>
          <meta property="og:title" content="{og_title}"/>
          <meta property="og:description" content="{og_description}"/>
          <meta property="og:image" content="https://shoutoutsong.com/assets/share-default.png"/>
          <meta property="og:type" content="music.song"/>
          <meta property="og:url" content="{viewer}"/>
          <meta name="twitter:card" content="summary_large_image"/>
          <meta name="twitter:title" content="{og_title}"/>
          <meta name="twitter:description" content="{og_description}"/>
          <meta http-equiv="refresh" content="0; url={viewer}" />
        </head>
        <body></body>
        </html>
        """
    )


# =====================================================
# STRIPE WEBHOOK (EMAIL DELIVERY)
# =====================================================
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events.
    Sends email after successful payment.
    """
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not STRIPE_WEBHOOK_SECRET:
        print("⚠️ STRIPE_WEBHOOK_SECRET not configured")
        return {"status": "webhook secret not configured"}
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle successful payment
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        
        # Extract metadata
        song_id = session.get("metadata", {}).get("song_id")
        recipient_name = session.get("metadata", {}).get("recipient_name", "someone special")
        subject = session.get("metadata", {}).get("subject", "something special")
        customer_email = session.get("customer_details", {}).get("email")
        
        if not customer_email:
            print("⚠️ No customer email in webhook")
            return {"status": "no email"}
        
        if not song_id:
            print("⚠️ No song_id in webhook")
            return {"status": "no song_id"}
        
        # Create share link first
        try:
            store = _load_share_store()
            status = query_song_status(song_id)
            choices = status.get("choices", [])
            
            if choices:
                audio_url = choices[0].get("url") or choices[0].get("audio_url")
                if audio_url:
                    token = secrets.token_urlsafe(16)
                    store[token] = {
                        "song_id": song_id,
                        "audio_url": audio_url,
                        "title": f"A song for {recipient_name}",
                        "subtitle": "Made with Shoutout Song",
                        "recipient_name": recipient_name,
                        "subject": subject,
                        "created_at": time.time(),
                    }
                    _save_share_store(store)
                    
                    share_url = f"https://shoutoutsong.com/share.html?t={token}"
                    download_url = f"https://shoutoutsong.onrender.com/full-audio/{song_id}"
                    
                    # Send email
                    if EMAIL_ENABLED:
                        send_song_email(
                            to_email=customer_email,
                            recipient_name=recipient_name,
                            subject=subject,
                            download_url=download_url,
                            share_url=share_url
                        )
                        print(f"✅ Email sent to {customer_email}")
                    else:
                        print("⚠️ Email not sent - EMAIL_ENABLED is False")
        
        except Exception as e:
            print(f"❌ Error in webhook: {e}")
    
    return {"status": "success"}
