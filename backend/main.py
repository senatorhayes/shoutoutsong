import os
import time
import secrets
import re
import requests

import stripe
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from lyrics_ai import generate_kid_lyrics, generate_adult_lyrics
from mureka_api import start_song_generation, query_song_status

# Genre-specific prompts for better audio generation
def get_genre_prompt(genre: str) -> str:
    """Return detailed prompt for each genre"""
    prompts = {
        "pop": "Upbeat pop song with catchy melody, modern production, radio-friendly hooks",
        "rock": "Energetic rock song with electric guitars, driving drums, powerful vocals",
        "hiphop": "Hip hop track with rhythmic flow, bass-heavy beat, urban production, confident delivery",
        "rap": "Rap song with clever wordplay, strong beat, dynamic flow, modern hip hop production",
        "country": "Heartfelt country song with acoustic guitar, storytelling lyrics, warm vocals",
        "reggae": "Laid-back reggae track with offbeat rhythm, island vibes, relaxed groove",
        "reggaeton": "Latin reggaeton with dembow rhythm, Spanish flair, tropical beats, danceable energy",
        "metal": "Heavy metal song with distorted guitars, aggressive drums, powerful energy",
        "punk": "Fast-paced punk rock with raw energy, simple power chords, rebellious attitude",
        "grunge": "Grunge rock with heavy distortion, angst-filled vocals, 90s Seattle sound, raw production",
        "alternative": "Alternative rock with indie sensibility, creative arrangements, atmospheric guitars, introspective vocals",
        "indie": "Indie rock with jangly guitars, melodic hooks, DIY aesthetic, heartfelt vocals",
        "emo": "Emo rock with emotional vocals, power chords, confessional lyrics, 2000s pop punk energy",
        "edm": "Electronic dance music with pulsing beats, synth drops, festival energy",
        "house": "Feel-good house music track with four-on-the-floor beat, groovy bassline, catchy vocal topline, uplifting club energy",
        "techno": "Driving techno track with pulsing synths, steady hypnotic beat, minimal vocals, underground club atmosphere",
        "ballad": "Emotional ballad with piano or strings, heartfelt vocals, slow build, touching melody",
        "folk": "Warm acoustic folk song with gentle guitar or piano, organic production, intimate vocals, campfire-style storytelling",
        "rnb": "Smooth R&B soul track with expressive vocals, warm chords, laid-back groove, emotional delivery",
        "gospel": "Uplifting gospel-inspired song with powerful soulful vocals, choir harmonies, piano and organ, joyful message",
        "jazz": "Smooth jazz-inspired song with expressive vocals, swing or lounge feel, warm instrumentation, classy and relaxed tone",
        "blues": "Blues song with soulful vocals, guitar bends, emotional delivery, classic 12-bar structure",
        "classical": "Classical-inspired piece with orchestral arrangements, elegant melodies, sophisticated harmonies",
        "disco": "Disco track with funky bass, four-on-the-floor beat, strings, 70s dance floor energy",
        "funk": "Funk song with groovy bassline, tight rhythm section, syncopated guitars, infectious groove",
        "kpop": "K-pop song with catchy hooks, polished production, dynamic energy, modern pop sensibility",
        "mariachi": "Mariachi song with trumpets, violins, guitars, festive Mexican spirit, celebratory vocals",
        "ska": "Ska song with upbeat tempo, offbeat guitar, horn section, Caribbean-influenced energy",
        "lofi": "Lo-fi track with mellow beats, jazzy chords, nostalgic samples, relaxed study vibes",
        "seashanty": "Sea shanty with maritime themes, call-and-response vocals, rhythmic chanting, nautical spirit",
        "50s": "1950s rock and roll with doo-wop vocals, simple chord progressions, vintage production, nostalgic charm",
        "70s": "1970s classic with funk influence, warm analog sound, groovy rhythms, retro production",
        "80s": "1980s synth pop with electronic drums, synthesizers, reverb-heavy production, new wave energy",
        "90s": "1990s hit with era-appropriate production, nostalgic sound, pop or rock sensibility",
        "1920s": "1920s jazz age with swing rhythm, big band horns, vintage vocals, speakeasy atmosphere",
        "musical": "Broadway musical style with theatrical vocals, orchestral backing, dramatic storytelling, show tune energy",
    }
    return prompts.get(genre.lower(), f"{genre} song")

# Import email sender (will handle gracefully if not configured)
try:
    from email_sender import send_song_email
    EMAIL_ENABLED = True
except ImportError:
    print("⚠️ email_sender.py not found - emails disabled")
    EMAIL_ENABLED = False

# Import Klaviyo for email collection
try:
    from klaviyo_api import KlaviyoAPI
    KLAVIYO_API_KEY = os.getenv("KLAVIYO_API_KEY")
    klaviyo = KlaviyoAPI(KLAVIYO_API_KEY) if KLAVIYO_API_KEY else None
    if klaviyo:
        print("✅ Klaviyo initialized")
    else:
        print("⚠️ KLAVIYO_API_KEY not set - email collection disabled")
except ImportError:
    print("⚠️ klaviyo-api not installed - email collection disabled")
    klaviyo = None

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
# KLAVIYO EMAIL COLLECTION
# =====================================================
def add_to_klaviyo(email: str, properties: dict, purchased: bool = False):
    """Add email to Klaviyo with properties. Returns True on success, False on failure."""
    if not klaviyo:
        print("⚠️ Klaviyo not configured - KLAVIYO_API_KEY missing")
        return False
    
    list_id = os.getenv("KLAVIYO_LIST_ID")
    
    try:
        # Step 1: Create/update profile
        try:
            klaviyo.Profiles.create_profile({
                "data": {
                    "type": "profile",
                    "attributes": {
                        "email": email,
                        "properties": {
                            **properties,
                            "source": "shoutoutsong",
                            "purchased": purchased
                        }
                    }
                }
            })
            print(f"✅ Created profile in Klaviyo: {email}")
        except Exception as create_error:
            if "409" in str(create_error) or "duplicate" in str(create_error).lower():
                print(f"✅ Profile already exists: {email}")
            else:
                raise create_error
        
        # Step 2: Subscribe them using direct API call
        if list_id and KLAVIYO_API_KEY:
            try:
                response = requests.post(
                    "https://a.klaviyo.com/api/profile-subscription-bulk-create-jobs/",
                    headers={
                        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
                        "Content-Type": "application/json",
                        "revision": "2025-10-15"
                    },
                    json={
                        "data": {
                            "type": "profile-subscription-bulk-create-job",
                            "attributes": {
                                "profiles": {
                                    "data": [{
                                        "type": "profile",
                                        "attributes": {
                                            "email": email,
                                            "subscriptions": {
                                                "email": {
                                                    "marketing": {
                                                        "consent": "SUBSCRIBED"
                                                    }
                                                }
                                            }
                                        }
                                    }]
                                }
                            },
                            "relationships": {
                                "list": {
                                    "data": {
                                        "type": "list",
                                        "id": list_id
                                    }
                                }
                            }
                        }
                    }
                )
                if response.status_code in [200, 201, 202]:
                    print(f"✅ Subscribed {email} to list {list_id}")
                else:
                    print(f"⚠️ Subscription failed ({response.status_code}): {response.text}")
            except Exception as sub_error:
                print(f"⚠️ Subscription error: {sub_error}")
        else:
            print(f"⚠️ KLAVIYO_LIST_ID not set")
        
        return True
    except Exception as e:
        print(f"❌ Klaviyo API error: {e}")
        return False


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
    lyrics: str | None = None


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
        prompt="Upbeat fun children's song with catchy melody, bright instrumentation, cheerful vocals, playful energy, high-quality production (not overly synthetic or cheesy)",
        duration=req.duration_seconds,
        genre="pop",  # Pop for upbeat energy
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
        prompt=get_genre_prompt(req.genre),
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
        checkout_params = {
            "mode": "payment",
            "line_items": [{"price": STRIPE_PRICE_ID, "quantity": 1}],
            "success_url": success_url,
            "cancel_url": "https://shoutoutsong.com/cancel",
            "client_reference_id": song_id,
            "metadata": {
                "song_id": song_id,
                "recipient_name": recipient_name,
                "subject": subject,
            },
            "customer_email": None,  # Let Stripe collect it
        }
        
        # Don't use consent collection - we add all purchasers to Klaviyo
        session = stripe.checkout.Session.create(**checkout_params)
        
        return {"checkout_url": session.url}
    except Exception as e:
        print(f"❌ Stripe error: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe checkout failed: {str(e)}")


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

    # Try to get name and subject from result metadata for better filename
    metadata = result.get("metadata", {})
    recipient_name = metadata.get("recipient_name", "")
    subject = metadata.get("subject", "")
    
    # Create filename: shoutoutsong-{name}-{subject}.mp3
    if recipient_name and subject:
        # Clean name and subject for filename
        clean_name = re.sub(r"[^a-z0-9]+", "", recipient_name.lower().replace(" ", ""))
        clean_subject = re.sub(r"[^a-z0-9]+", "", subject.lower().replace(" ", ""))
        safe_title = f"shoutoutsong-{clean_name}-{clean_subject}"
    else:
        safe_title = "shoutoutsong"

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
        "lyrics": req.lyrics or "",
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

# =====================================================
# EMAIL SUBSCRIPTION
# =====================================================
@app.post("/subscribe")
async def subscribe_email(request: Request):
    """Subscribe email to mailing list"""
    body = await request.json()
    email = body.get("email")
    source = body.get("source", "unknown")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    
    # Try to add to Klaviyo, but don't fail if it's down
    success = add_to_klaviyo(email, {
        "source": source,
        "subscribed_at": time.time()
    }, purchased=False)
    
    # Always return success to user (we'll retry Klaviyo later if it was down)
    return {"success": True, "klaviyo_added": success}


# =====================================================
# STRIPE WEBHOOK
# =====================================================
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
                    
                    # Add all purchasers to Klaviyo (they bought from you - they're interested!)
                    print(f"🔔 Attempting to add purchaser to Klaviyo: {customer_email}")
                    klaviyo_success = add_to_klaviyo(customer_email, {
                        "song_id": song_id,
                        "recipient_name": recipient_name,
                        "subject": subject,
                        "amount": 4.99,
                        "purchased_at": time.time(),
                        "share_url": share_url
                    }, purchased=True)
                    
                    if klaviyo_success:
                        print(f"✅ Successfully added purchaser to Klaviyo: {customer_email}")
                    else:
                        print(f"❌ Failed to add purchaser to Klaviyo: {customer_email}")
        
        except Exception as e:
            print(f"❌ Error in webhook: {e}")
    
    return {"status": "success"}
