# lyrics_ai.py
import os
import random
from dotenv import load_dotenv
from openai import OpenAI

# Load .env so OPENAI_API_KEY is available
load_dotenv()

client = OpenAI()  # will read OPENAI_API_KEY from env


# ------------------------------------------------------------
# Kids lyrics generator
# ------------------------------------------------------------

# ------------------------------------------------------------
# Kids song sound. Every kids song keeps the same happy sing-along style;
# each one randomly gets one of a few instrument mixes so a page of songs
# doesn't sound identical.
#
# ORIGINAL (before Nov 23 2026) — every kids song used exactly this prompt.
# To go back, have main.py use ORIGINAL_KID_MUSIC_PROMPT instead of style["music"],
# or restore git commit 8b763da.
# ------------------------------------------------------------
ORIGINAL_KID_MUSIC_PROMPT = ("Upbeat children's song with catchy singalong melody, bright acoustic instrumentation "
                             "(guitar, ukulele, hand drums, bells), cheerful vocals, playful and fun energy, "
                             "repeated chorus, high-quality production")

_BASE = "Upbeat children's song with catchy singalong melody, cheerful vocals, playful and fun energy"

KID_STYLES = [
    dict(name="acoustic guitar", feel="classic acoustic sing-along",
         music=f"{_BASE}, strummed acoustic guitar, hand claps, shaker, warm and bouncy"),
    dict(name="ukulele", feel="sunny, bouncy ukulele sing-along",
         music=f"{_BASE}, bright ukulele, hand claps, light bongos, sunny and bouncy"),
    dict(name="piano and glockenspiel", feel="bouncy piano sing-along",
         music=f"{_BASE}, bouncy piano, glockenspiel, light drums, playful and sparkly"),
    dict(name="banjo and fiddle", feel="foot-tapping sing-along",
         music=f"{_BASE}, light banjo and fiddle, foot-tapping rhythm, hand claps, friendly and fun"),
]
HOLIDAY_STYLE = dict(name="jingle bells", feel="cozy, festive holiday sing-along",
                     music=f"{_BASE}, jingle bells, sleigh bells, bouncy piano, warm and festive")

# Theme-matched flavors (still happy kids sing-alongs, just with a sound that fits).
THEME_STYLES = [
    (["monster truck", "truck", "race car", "car", "dinosaur", "dino", "construction", "digger",
      "superhero", "robot", "fire truck"],
     dict(name="kid rock", feel="loud, energetic stomp-and-roar sing-along with sound effects like VROOM and ROAR",
          music="High-energy kids rock song, crunchy electric guitars, big pounding drums, hand claps, shout-along chorus, "
                "enthusiastic friendly vocal, exciting and loud but kid-friendly")),
    (["unicorn", "princess", "fairy", "ballet", "rainbow", "mermaid", "butterfl"],
     dict(name="sparkly pop", feel="magical, sparkly sing-along",
          music=f"{_BASE}, twinkling chimes and bells, sparkly synths, light strings, bouncy pop beat, magical and dreamy")),
    (["space", "rocket", "planet", "astronaut", "airplane", "plane"],
     dict(name="space pop", feel="exciting countdown sing-along with whooshes and beeps",
          music=f"{_BASE}, bouncy beat, bubbly synths, whoosh and beep sound effects, adventurous and bright")),
    (["pirate", "ship", "boat"],
     dict(name="pirate stomp", feel="jolly stomp-along with 'heave-ho' group shouts",
          music=f"{_BASE}, accordion, stomping drums, hand claps, rowdy group 'yo-ho' vocals, jolly adventure")),
    (["shark", "ocean", "sea", "fish", "beach"],
     dict(name="steel drum sunshine", feel="sunny under-the-sea sing-along",
          music=f"{_BASE}, steel drums, marimba, bouncy bass, shakers, sunny and splashy")),
    (["farm", "horse", "pony", "train", "tractor", "cow"],
     dict(name="banjo hoedown", feel="foot-tapping farmyard sing-along with animal sounds",
          music=f"{_BASE}, banjo and fiddle, foot-stomping rhythm, hand claps, yee-haw shouts, playful")),
    (["soccer", "sport", "football", "basketball"],
     dict(name="stadium chant", feel="cheering stadium chant sing-along",
          music=f"{_BASE}, stomp-stomp-clap stadium beat, crowd chants, electric guitar, triumphant and energetic")),
]


def pick_kid_style(theme: str) -> dict:
    """Theme-matched flavor when the theme fits one, otherwise a random instrument mix.
    Jingle bells only for Christmas-type themes."""
    t = (theme or "").lower()
    if any(k in t for k in ("christmas", "santa", "reindeer", "holiday")):
        return HOLIDAY_STYLE
    for keywords, style in THEME_STYLES:
        if any(k in t for k in keywords):
            return style
    return random.choice(KID_STYLES)



LYRIC_DEVICES = [
    "call-and-response: the singer asks a question and the kids shout the answer back",
    "action song: tell the listener to stomp, clap, jump, spin or wiggle in each verse",
    "counting: count up (1, 2, 3...) with something from the theme",
    "sound effects: fun noises from the theme (roar, vroom, splash, beep-boop) as part of the chorus",
    "echo lines: the singer sings a line and it is echoed back",
    "a tiny story: the child goes on a short adventure with a beginning, middle and happy ending",
    "silly made-up words in the chorus that are fun to say out loud",
]


def generate_kid_lyrics(
    child_name: str,
    theme: str,
    occasion: str = "everyday",
    vibe: str = "sunny_kids",
    voice_type: str = "any",
    style: dict = None,
) -> str:
    """
    Generate fun, kid-safe lyrics for ages ~3–8.

    Matches main.py:
      generate_kid_lyrics(
          child_name=req.child_name,
          theme=req.theme,
          occasion=req.occasion,
          vibe=req.vibe,
          voice_type=req.voice_type,
      )
    """

    # Turn our internal vibe flag into some language
    if vibe == "sunny_kids":
        vibe_desc = "bright, upbeat, playful kids song with a catchy chorus"
    elif vibe == "lullaby":
        vibe_desc = "gentle, soothing lullaby with calm, simple lines"
    elif vibe == "pop_kids":
        vibe_desc = "modern, bouncy pop song for kids with a strong hook"
    elif vibe == "party_kids":
        vibe_desc = "high-energy kids party song that makes you want to dance"
    else:
        vibe_desc = "fun, melodic kids song"

    # Voice hint (we only use this in the instructions; actual voice is handled by Mureka)
    if voice_type == "male":
        voice_hint = "Imagine a friendly dad / big brother style voice."
    elif voice_type == "female":
        voice_hint = "Imagine a warm mom / big sister style voice."
    elif voice_type == "child":
        voice_hint = "Imagine a natural, child-like singing voice (not squeaky)."
    else:
        voice_hint = "Use a neutral, friendly singing voice."

    # Simple description of the occasion for the model
    occasion_text = {
        "everyday": "This is for everyday listening, a fun surprise for the child.",
        "birthday": "This is for their birthday – mention celebration and turning a new age (but don't guess the exact age).",
        "holiday": "This is for a holiday – make it cozy and festive, without naming specific religious details.",
        "milestone": "This is for a big milestone like school, sports, or learning something new.",
        "custom": "This is for a special custom moment chosen by the parent.",
    }.get(occasion, "This is a fun song they can enjoy any day.")

    style = style or pick_kid_style(theme)
    device = random.choice(LYRIC_DEVICES)

    user_prompt = f"""
Write original, kid-safe song lyrics for a child named {child_name}.

Theme: {theme}
Occasion: {occasion}
Occasion description: {occasion_text}
Song feel: upbeat, happy kids sing-along ({style["feel"]})
Songwriting trick to build the song around: {device}
Voice hint: {voice_hint}

Make it feel like a real, classic kids song that families sing in the car, not a generic jingle:
- Paint specific, vivid, funny little pictures from the theme (what {child_name} sees, hears and does), not general praise like "you're so great" or "you're the best".
- Make the chorus short, very catchy and easy to shout along to, with {child_name}'s name in it.
- Use playful rhythm and rhymes that fit the musical style.
- A touch of gentle humor or surprise is great.

Guidelines:
- Age target: roughly 2–6 years old. Very simple, positive words.
- Include the child's name {child_name} several times, especially in the chorus.
- Do NOT mention AI, technology, or that this is generated.
- Do NOT use any brand names or characters from movies, TV or books; describe things generically.
- Avoid anything scary, violent, mean, or romantic.

Structure:
- Verse 1 (4 short lines)
- Chorus (4 short lines)
- Verse 2 (4 short lines)
- Chorus

Output format:
Write plain lyrics with labeled sections like:
Verse 1:
...
Chorus:
...
Verse 2:
...
Chorus:
...

Do NOT use markdown formatting like **bold** or bullet points.
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Fixed: was "gpt-4.1-mini"
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an award-winning children's songwriter in the tradition of classic family sing-along music. "
                    "You write short, joyful, playful lyrics that kids love to sing and parents don't mind hearing again."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
        max_tokens=400,
    )

    lyrics = response.choices[0].message.content.strip()
    return lyrics


# ------------------------------------------------------------
# Adult / special-occasion lyrics generator
# ------------------------------------------------------------
def generate_adult_lyrics(
    recipient_name: str,
    relationship: str,
    occasion: str,
    story_or_details: str,
    genre: str = "pop",
    vibe: str = "fun",
    voice_type: str = "any",
) -> str:
    """
    Generate lyrics for adult / special occasion songs.

    Matches main.py:
      generate_adult_lyrics(
          recipient_name=req.recipient_name,
          relationship=req.relationship,
          occasion=req.occasion,
          story_or_details=req.story_or_details,
          genre=req.genre,
          vibe=req.vibe,
          voice_type=req.voice_type,
      )
    """

    # Map vibe to tone description
    vibe_desc = {
        "fun": "fun, upbeat, playful, light-hearted",
        "heartfelt": "emotional, sincere, warm, grateful",
        "epic": "big, cinematic, anthemic, inspiring",
        "silly": "funny roast style - make fun of them playfully! Tease them about quirks, habits, or funny things about them. Keep it affectionate but definitely roast them",
        "romantic": "tender, intimate, loving, romantic",
    }.get(vibe, "engaging and modern")

    # Voice hint (for wording only)
    if voice_type == "male":
        voice_hint = "Imagine a natural male singer performing this."
    elif voice_type == "female":
        voice_hint = "Imagine a natural female singer performing this."
    else:
        voice_hint = "The vocal style is flexible, any expressive voice that fits the genre."

    user_prompt = f"""
Write original song lyrics for an adult listener.

Recipient: {recipient_name}
Relationship to the singer: {relationship}
Occasion: {occasion}
Genre: {genre}
Vibe: {vibe_desc}
Voice hint: {voice_hint}

Details to weave into the song:
{story_or_details}

Guidelines:
- Make this feel personal to {recipient_name}.
- Include their name several times, especially in the chorus.
- Lean into the tone: {vibe_desc}. If this is a roast/funny song, MAKE SURE to actually tease and make fun of them in a playful way!
- Avoid explicit content, slurs, or mean-spirited insults. But roasting, teasing, and playful mockery are ENCOURAGED for funny songs.
- Do NOT mention AI, technology, or that this is generated.
- Write it like a real {genre} song: use the genre's typical words, attitude and clichés (a country song mentions trucks and dirt roads, a metal song is epic and dramatic, a sea shanty has "heave-ho") — playing the genre straight is part of the joke for funny songs.
- Be specific and concrete: turn the details into vivid little scenes and real jokes, not generic lines. Each verse should escalate.
- Land punchlines at the end of lines. Never force a rhyme with a word that doesn't make sense; a near-rhyme is fine.
- Keep lines short and singable.

Structure:
- Short intro line (optional)
- Verse 1
- Chorus (big, memorable hook)
- Verse 2
- Chorus (slightly varied or repeated)
- Optional short bridge (2–4 lines)
- Final chorus

Output format:
Write plain lyrics with labeled sections like:
Intro:
...
Verse 1:
...
Chorus:
...
etc.

Do NOT use markdown formatting like **bold** or bullet points.
"""

    def _ask(model):
        return client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a versatile professional songwriter and comedy writer who writes custom songs in any genre. "
                        "Funny songs are genuinely funny, with sharp specific jokes; heartfelt songs are warm and sincere. "
                        "You write clear hooks and singable phrasing."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.95,
            max_tokens=600,
        
        )

    try:
        response = _ask("gpt-4o")  # better at funny, specific lyrics
    except Exception as exc:
        print(f"gpt-4o failed ({exc}); falling back to gpt-4o-mini")
        response = _ask("gpt-4o-mini")

    lyrics = response.choices[0].message.content.strip()
    return lyrics
