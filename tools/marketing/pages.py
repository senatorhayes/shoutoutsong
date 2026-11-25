"""Landing pages for example songs.

- frontend/<slug>.html            one page per example song (e.g. /olivia-dinosaur-song)
- frontend/example-songs.html     hub listing every example
- frontend/audio/examples.json    latest few, read by the homepage "Hear an example" box
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
FRONT = ROOT / "frontend"
SITE = "https://shoutoutsong.com"

PLAUSIBLE = """  <script async src="https://plausible.io/js/pa-Lr_14gVhbTd58se5r3yzQ.js"></script>
  <script>window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};plausible.init()</script>"""

FOOT = """  <footer class="foot">
    <nav>
      <a href="/">Make a song</a><a href="/kids-songs">Kids songs</a><a href="/example-songs">Example songs</a><a href="/faq">FAQ</a>
    </nav>
    <nav class="legal">
      <a href="/terms.html">Terms</a><a href="/privacy.html">Privacy</a><a href="/refund.html">Refunds</a><a href="/content-policy.html">Content</a>
    </nav>
    <p>Shoutout Song · Custom songs written and sung in about a minute.</p>
  </footer>
</body>
</html>
"""


HOLIDAYS = ("Christmas", "New Year", "Valentine", "Easter", "Halloween")


def lower_label(label):
    """'dinosaur' but keep holiday names capitalized ('Christmas')."""
    return label if label in HOLIDAYS else label.lower()


def e(s):
    return html.escape(str(s), quote=True)


def head(title, desc, path, extra_ld=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}" />
  <link rel="canonical" href="{SITE}{path}" />
  <link rel="icon" type="image/x-icon" href="/favicon.ico" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Shoutout Song" />
  <meta property="og:title" content="{e(title)}" />
  <meta property="og:description" content="{e(desc)}" />
  <meta property="og:url" content="{SITE}{path}" />
  <meta property="og:image" content="{SITE}/logo.png" />
  <meta name="twitter:card" content="summary" />
  <link rel="stylesheet" href="/seo.css" />
{extra_ld}{PLAUSIBLE}
</head>
<body>
  <header class="top">
    <a class="brand" href="/"><img src="/logo.png" alt="" width="36" height="36" /> Shoutout Song</a>
    <nav><a href="/kids-songs">Kids songs</a><a href="/example-songs">Examples</a><a href="/faq">FAQ</a></nav>
  </header>
"""


def clean_lyrics(lyrics):
    """Drop section labels like 'Verse 1:' and return groups of lines."""
    groups, cur = [], []
    for raw in (lyrics or "").splitlines():
        line = raw.strip().strip("*").strip()
        if not line:
            if cur:
                groups.append(cur)
                cur = []
            continue
        if re.match(r"^(verse|chorus|bridge|intro|outro|pre-chorus|hook)\b[^:]*:?$", line, re.I):
            if cur:
                groups.append(cur)
                cur = []
            continue
        cur.append(line)
    if cur:
        groups.append(cur)
    return groups


def create_href(song):
    return "/?" + urlencode({"name": song["name"], "love": song["love"], "tab": "kid"}) + "#create"


def song_page(song, others):
    name, label, love = song["name"], song["label"], song["love"]
    path = "/" + song["slug"]
    title = f"{name}'s {label} Song – A Custom Kids Song With the Name {name}"
    desc = (f"Listen to an example {lower_label(label)} song for a kid named {name}. "
            f"Make your own with your child's name and what they love in about a minute. Free preview.")
    ld = {
        "@context": "https://schema.org", "@type": "MusicRecording",
        "name": f"{name}'s {label} Song", "url": SITE + path,
        "byArtist": {"@type": "MusicGroup", "name": "Shoutout Song"},
        "audio": {"@type": "AudioObject", "contentUrl": SITE + song["audio"], "encodingFormat": "audio/mpeg"},
    }
    extra = f'  <script type="application/ld+json">{json.dumps(ld)}</script>\n'
    verses = "".join(
        f'      <blockquote class="lyrics">{"<br />".join(e(l) for l in g)}</blockquote>\n'
        for g in clean_lyrics(song.get("lyrics"))
    )
    more = "".join(
        f'        <li><a href="/{e(o["slug"])}">{e(o["name"])}\'s {e(o["label"].lower())} song</a></li>\n'
        for o in others
    )
    return head(title, desc, path, extra) + f"""  <main class="wrap">
    <nav class="crumbs"><a href="/">Home</a> › <a href="/example-songs">Example songs</a></nav>
    <section class="hero">
      <h1>{e(name)}'s {e(lower_label(label))} song</h1>
      <p class="lead">Here's a short clip of an example song we made for the name {e(name)}, about a kid who loves {e(love)}. Your song gets written fresh with your child's name and whatever they're into.</p>
      <audio controls preload="none" src="{e(song['audio'])}" style="width:100%;margin:8px 0 14px"></audio>
      <p class="facts"><span>Free 15-second preview</span><span>Full song $4.99</span><span>Ready in about a minute</span></p>
      <a class="cta" href="{e(create_href(song))}">Make one for your {e(name)} →</a>
      <p class="muted" style="margin-top:14px">Example song made by Shoutout Song for the name {e(name)}, not a customer order.</p>
    </section>

    <section class="card">
      <h2>The lyrics</h2>
{verses}    </section>

    <section class="card">
      <h2>Make your own</h2>
      <ol class="how">
        <li><b>Type your kid's name and what they love.</b> Add as many details as you like.</li>
        <li><b>Pick a voice.</b> Boy, girl, child-like, or surprise me.</li>
        <li><b>Preview free, then download.</b> Get the full MP3 and a share link for $4.99.</li>
      </ol>
      <a class="cta" href="{e(create_href(song))}">Make their song →</a>
      <p style="margin-top:14px">More {e(lower_label(label))} ideas: <a href="/{e(song['page'])}">{e(label)} songs for kids</a></p>
    </section>

    <section class="card">
      <h2>More example songs</h2>
      <ul class="links">
{more}      </ul>
      <p><a href="/example-songs">See all example songs</a></p>
    </section>
  </main>
""" + FOOT


SITE_VIBE = {"silly": "funny", "fun": "happy", "heartfelt": "emotional", "romantic": "emotional", "epic": "hype"}


def adult_create_href(song):
    q = {"tab": "adult", "genre": song.get("genre", ""), "vibe": SITE_VIBE.get(song.get("vibe"), "funny"),
         "occasion": song.get("occasion", ""), "relationship": song.get("relationship", "")}
    return "/?" + urlencode({k: v for k, v in q.items() if v}) + "#create"


def adult_song_page(song, others):
    name, badge, line = song["name"], song["badge"], song["line"]
    path = "/" + song["slug"]
    title = f"{badge} Song for {name} – Example Custom Song | Shoutout Song"
    desc = (f"Listen to an example {badge.lower()} song for {name}, {line}. "
            f"Make a custom song for anyone in about a minute, in 36 genres. Free preview.")
    ld = {
        "@context": "https://schema.org", "@type": "MusicRecording",
        "name": f"{badge} song for {name}", "url": SITE + path,
        "byArtist": {"@type": "MusicGroup", "name": "Shoutout Song"},
        "audio": {"@type": "AudioObject", "contentUrl": SITE + song["audio"], "encodingFormat": "audio/mpeg"},
    }
    extra = f'  <script type="application/ld+json">{json.dumps(ld)}</script>\n'
    verses = "".join(
        f'      <blockquote class="lyrics">{"<br />".join(e(l) for l in g)}</blockquote>\n'
        for g in clean_lyrics(song.get("lyrics"))
    )
    more = "".join(
        f'        <li><a href="/{e(o["slug"])}">{e(o.get("badge") or o["label"])} song for {e(o["name"])}</a></li>\n'
        for o in others
    )
    return head(title, desc, path, extra) + f"""  <main class="wrap">
    <nav class="crumbs"><a href="/">Home</a> › <a href="/example-songs">Example songs</a></nav>
    <section class="hero">
      <h1>A {e(badge.lower())} song for {e(name)}</h1>
      <p class="lead">{e(name)}, {e(line)}. Here's a short clip of the example song we made. Yours gets written fresh from your own names, details and inside jokes, in any of 36 genres.</p>
      <audio controls preload="none" src="{e(song['audio'])}" style="width:100%;margin:8px 0 14px"></audio>
      <p class="facts"><span>Free 15-second preview</span><span>Full song $4.99</span><span>Ready in about a minute</span></p>
      <a class="cta" href="{e(adult_create_href(song))}">{e(song.get("cta") or "Make one for anyone")} →</a>
      <p class="muted" style="margin-top:14px">Example song made by Shoutout Song. {e(name)} is just an example name, not a customer.</p>
    </section>

    <section class="card">
      <h2>The lyrics</h2>
{verses}    </section>

    <section class="card">
      <h2>Make your own</h2>
      <ol class="how">
        <li><b>Type their name and the details.</b> Inside jokes, habits, how you met — the more the better.</li>
        <li><b>Pick a genre and a vibe.</b> Funny roast, happy, emotional or hype, in 36 genres.</li>
        <li><b>Preview free, then download.</b> Get the full MP3 and a share link for $4.99.</li>
      </ol>
      <a class="cta" href="{e(adult_create_href(song))}">Make their song →</a>
      <p style="margin-top:14px">More ideas: <a href="/{e(song['page'])}">{e(song['label'])} songs</a></p>
    </section>

    <section class="card">
      <h2>More example songs</h2>
      <ul class="links">
{more}      </ul>
      <p><a href="/example-songs">See all example songs</a></p>
    </section>
  </main>
""" + FOOT


def hub_page(songs, adult_songs=()):
    adult_items = "".join(
        f'      <li><a href="/{e(s["slug"])}"><b>{e(s["name"])}</b><br /><span class="muted">{e(s["badge"])} song</span></a></li>\n'
        for s in adult_songs
    )
    adult_section = f"""    <section class="card">
      <h2>Roasts, birthdays &amp; more</h2>
      <ul class="grid">
{adult_items}      </ul>
    </section>
""" if adult_songs else ""
    items = "".join(
        f'      <li><a href="/{e(s["slug"])}"><b>{e(s["name"])}</b><br /><span class="muted">{e(s["label"])} song</span></a></li>\n'
        for s in songs
    )
    return head(
        "Example Custom Songs With Names | Shoutout Song",
        "Listen to example personalized songs: kids songs, roasts, birthday and anniversary songs, each starring a different name. Make one in about a minute.",
        "/example-songs",
    ) + f"""  <main class="wrap">
    <nav class="crumbs"><a href="/">Home</a> › Example songs</nav>
    <section class="hero">
      <h1>Example songs, starring different names</h1>
      <p class="lead">Each of these is an example we made to show what Shoutout Song sounds like. Find a name you know, or make a brand-new one in about a minute.</p>
      <a class="cta" href="/#create">Make a song →</a>
    </section>
    <section class="card">
      <h2>Kids songs</h2>
      <ul class="grid">
{items}      </ul>
    </section>
{adult_section}  </main>
""" + FOOT


ADULT_MANIFEST = Path(__file__).resolve().parent / "adult_songs.json"


def build_all(songs, adult_songs=None):
    """songs: kids manifest list, oldest first. Adult songs are read from adult_songs.json."""
    if adult_songs is None:
        adult_songs = json.loads(ADULT_MANIFEST.read_text()) if ADULT_MANIFEST.exists() else []
    newest = list(reversed(songs))
    newest_adult = list(reversed(adult_songs))
    for s in songs:
        others = [o for o in newest if o["slug"] != s["slug"]][:6]
        (FRONT / f"{s['slug']}.html").write_text(song_page(s, others))
    for s in adult_songs:
        others = [o for o in newest_adult if o["slug"] != s["slug"]][:6]
        (FRONT / f"{s['slug']}.html").write_text(adult_song_page(s, others))
    (FRONT / "example-songs.html").write_text(hub_page(newest, newest_adult))
    (FRONT / "audio").mkdir(exist_ok=True)
    both = sorted(songs + adult_songs, key=lambda s: s.get("date", ""), reverse=True)
    latest = [dict(name=s["name"], label=s.get("badge") or s["label"], audio=s["audio"], url="/" + s["slug"])
              for s in both[:3]]
    (FRONT / "audio" / "examples.json").write_text(json.dumps(latest, indent=1))
