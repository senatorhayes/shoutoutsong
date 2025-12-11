# lyrics_ai.py
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env so OPENAI_API_KEY is available
load_dotenv()

client = OpenAI()  # will read OPENAI_API_KEY from env


# ------------------------------------------------------------
# Kids lyrics generator
# ------------------------------------------------------------
def generate_kid_lyrics(
    child_name: str,
    theme: str,
    occasion: str = "everyday",
    vibe: str = "sunny_kids",
    voice_type: str = "any",
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

    user_prompt = f"""
Write original, kid-safe song lyrics for a child named {child_name}.

Theme: {theme}
Occasion: {occasion}
Occasion description: {occasion_text}
Vibe: {vibe_desc}
Voice hint: {voice_hint}

Guidelines:
- Age target: roughly 3–8 years old.
- Keep language very simple and positive.
- Make it easy to sing along.
- Include the child's name {child_name} several times, especially in the chorus.
- Do NOT mention AI, technology, or that this is generated.
- Avoid anything scary, violent, mean, or romantic.

Structure:
- 1 short verse
- 1 very catchy chorus
- 1 more short verse
- Repeat the chorus at the end.

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
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional children's songwriter. "
                    "You write short, catchy, age-appropriate lyrics for kids."
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
        "silly": "very playful, comedic, goofy, roast-style but not cruel",
        "romantic": "tender, intimate, loving, romantic",
    }.get(vibe, "engaging and modern")

    # Voice hint (for wording only)
    if voice_type == "male":
        voice_hint = "Imagine a natural male pop singer performing this."
    elif voice_type == "female":
        voice_hint = "Imagine a natural female pop singer performing this."
    else:
        voice_hint = "The vocal style is flexible, any expressive pop voice."

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
- Lean into the tone: {vibe_desc}.
- Avoid explicit content, slurs, or cruel insults. Gentle roasting is OK if 'roast' or 'funny' is implied, but keep it light and affectionate.
- Do NOT mention AI, technology, or that this is generated.
- Keep it in a modern, singable style appropriate for a {genre} track.

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

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a professional pop songwriter who writes custom songs for people. "
                    "You focus on clear hooks, emotional impact, and singable, modern phrasing."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.95,
        max_tokens=600,
    )

    lyrics = response.choices[0].message.content.strip()
    return lyrics
