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

from lyrics_ai import generate_kid_lyrics, generate_adult_lyrics, pick_kid_style
from mureka_api import start_song_generation, query_song_status

# Genre-specific prompts for better audio generation
def get_genre_prompt(genre: str) -> str:
    """Return detailed prompt for each genre"""
    prompts = {
        "pop": "Bright modern pop with punchy drums, glossy synths and guitars, big catchy sing-along chorus, polished radio production",
        "rock": "Classic rock with crunchy overdriven electric guitars, big riffs, driving drums and bass, confident raspy lead vocal, arena-sized chorus",
        "hiphop": "Modern hip hop with deep 808 bass, crisp trap hi-hats and snares, confident rhythmic rap delivery, catchy melodic hook",
        "rap": "Hip hop track with hard-hitting boom-bap drums and deep bass, confident rapid rap verses with punchlines, catchy chanted hook, not sung pop",
        "country": "Classic country with twangy telecaster guitar, pedal steel, fiddle, upright bass and train-beat drums, warm Southern vocal with a little twang, honky-tonk feel",
        "reggae": "Roots reggae with offbeat guitar skank, deep round bass, one-drop drum groove, organ bubble, warm laid-back island vocal",
        "reggaeton": "Reggaeton with dembow drum rhythm, deep bass, Latin percussion and synth plucks, smooth rhythmic vocal, party energy",
        "metal": "Heavy metal with crunchy distorted down-tuned guitars, double-kick drums, galloping riffs, gritty powerful vocals with a few screams, headbanging energy, not pop",
        "punk": "Fast loud punk rock, distorted power chords, pounding fast drums, snotty shouted vocals, gang-vocal chorus, raw garage production, under 180 bpm",
        "grunge": "90s grunge with sludgy distorted guitars, loud-quiet-loud dynamics, heavy drums, raspy angsty vocal",
        "alternative": "Alternative rock with layered atmospheric guitars, driving bass and drums, expressive vocal, big dynamic chorus",
        "indie": "Upbeat indie rock with jangly clean guitars, bouncy bass, handclaps, quirky charming vocal, catchy whistle-worthy hook",
        "emo": "2000s emo pop-punk with jangly then distorted guitars, driving drums, earnest over-dramatic vocals that crack with emotion, angsty sing-shout chorus",
        "edm": "Festival EDM with euphoric synth leads, pounding four-on-the-floor kick, build-ups and big drops, energetic vocal hook",
        "house": "Feel-good house with four-on-the-floor kick, groovy bassline, piano stabs, soulful vocal hook, uplifting club energy",
        "techno": "Driving techno with relentless kick, pulsing synth bass, hypnotic arpeggios, sparse chanted vocal, warehouse rave",
        "ballad": "Over-the-top 80s power ballad, soaring electric guitar solo, big gated drums, piano and synth pads, dramatic emotional vocal with huge final chorus",
        "folk": "Warm acoustic folk with fingerpicked guitar, banjo, gentle stomp and clap, intimate storytelling vocal and harmonies",
        "rnb": "Smooth modern R&B with silky vocals and harmonies, warm Rhodes keys, deep bass, laid-back groove",
        "gospel": "Joyful gospel with Hammond organ, piano, hand claps and a big call-and-response choir, powerful soulful lead vocal, church revival energy",
        "jazz": "Swinging big band jazz with walking upright bass, brushed drums, muted trumpet and saxophone section, smooth crooner vocal, 1950s lounge",
        "blues": "Slow Delta-meets-Chicago blues, shuffle rhythm, wailing harmonica, bending electric guitar licks, gravelly soulful vocal, classic 12-bar",
        "classical": "Elegant classical orchestral piece with strings, woodwinds and piano, operatic soprano or tenor lead vocal",
        "disco": "1970s disco with four-on-the-floor kick, octave-jumping funky bass, wah guitar, lush strings and horns, falsetto backing vocals, mirror-ball dance floor",
        "funk": "Tight 70s funk with slap bass, chicken-scratch guitar, punchy horn section, syncopated drums, soulful shouted vocal",
        "kpop": "High-energy K-pop with punchy EDM-pop production, rap breakdown, synth drops, tight group vocals and catchy English hook",
        "mariachi": "Traditional mariachi with blazing trumpets, violins, vihuela and guitarrón, festive grito shouts, passionate ranchera lead vocal",
        "ska": "Third-wave ska punk, fast upstroke offbeat guitar skank, walking bass, punchy trumpet and trombone horn stabs, energetic gang vocals, 90s ska, not pop",
        "lofi": "Lo-fi hip hop with dusty vinyl crackle, mellow jazzy piano chords, laid-back boom-bap beat, soft hushed vocal",
        "seashanty": "Traditional sea shanty with stomping boots, clapping, accordion and fiddle, rowdy group of sailors singing call-and-response, pub singalong",
        "50s": "1950s rock and roll with doo-wop vocals, simple chord progressions, vintage production, nostalgic charm",
        "70s": "1970s classic with funk influence, warm analog sound, groovy rhythms, retro production",
        "80s": "1980s synth pop with electronic drums, synthesizers, reverb-heavy production, new wave energy",
        "90s": "1990s hit with era-appropriate production, nostalgic sound, pop or rock sensibility",
        "1920s": "1920s jazz age with swing rhythm, big band horns, vintage vocals, speakeasy atmosphere",
        "musical": "Big Broadway show tune with full pit orchestra, brass and strings, dramatic theatrical lead vocal, key change before the last chorus, jazz hands energy",
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
    # Sent by the site's form; previously ignored (every adult song got "friend" / "fun")
    relationship: str = "friend"
    occasion: str = "occasion"
    vibe: str = "fun"
    voice_type: str = "any"


class CreateShareLinkRequest(BaseModel):
    song_id: str
    title: str | None = None
    recipient_name: str | None = None
    subject: str | None = None
    lyrics: str | None = None
    genre: str | None = None


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
    style = pick_kid_style(req.theme)
    lyrics = generate_kid_lyrics(req.child_name, req.theme, style=style)
    task_id = start_song_generation(
        lyrics=lyrics,
        prompt=style["music"] + ", repeated chorus, high-quality production",
        duration=req.duration_seconds,
        genre="pop",
    )
    return {"task_id": task_id, "lyrics": lyrics}


@app.post("/generate-adult-song")
def generate_adult_song(req: AdultSongRequest):
    lyrics = generate_adult_lyrics(
        req.recipient_name,
        req.relationship or "friend",
        req.occasion or "occasion",
        req.story_or_details,
        req.genre,
        req.vibe or "fun",
        req.voice_type or "any",
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
            "allow_promotion_codes": True,  # Enable discount/promo codes
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
        "genre": req.genre or "",
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
        og_title = f"A song for {recipient_name} 🎵"
        og_description = f"Listen to this custom song about {subject}"
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
        session_id = session.get("id")
        
        # Prevent duplicate processing - track processed sessions
        processed_file = Path("/opt/render/project/data/processed_webhooks.json")
        try:
            if processed_file.exists():
                with open(processed_file, 'r') as f:
                    processed = json.load(f)
            else:
                processed = []
            
            # Check if already processed
            if session_id in processed:
                print(f"⚠️ Webhook already processed: {session_id}")
                return {"status": "already_processed"}
            
            # Mark as processed
            processed.append(session_id)
            # Keep only last 1000 to prevent file growing forever
            processed = processed[-1000:]
            with open(processed_file, 'w') as f:
                json.dump(processed, f)
        except Exception as e:
            print(f"⚠️ Error checking duplicates: {e}")
        
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
                    
                    # Skip Klaviyo in webhook to avoid timeout (takes 1-2 seconds)
                    # TODO: Move to background job or collect from Stripe directly
                    # print(f"🔔 Attempting to add purchaser to Klaviyo: {customer_email}")
                    # klaviyo_success = add_to_klaviyo(customer_email, {
                    #     "song_id": song_id,
                    #     "recipient_name": recipient_name,
                    #     "subject": subject,
                    #     "amount": 4.99,
                    #     "purchased_at": time.time(),
                    #     "share_url": share_url
                    # }, purchased=True)
                    # 
                    # if klaviyo_success:
                    #     print(f"✅ Successfully added purchaser to Klaviyo: {customer_email}")
                    # else:
                    #     print(f"❌ Failed to add purchaser to Klaviyo: {customer_email}")
        
        except Exception as e:
            print(f"❌ Error in webhook: {e}")
    
    return {"status": "success"}
