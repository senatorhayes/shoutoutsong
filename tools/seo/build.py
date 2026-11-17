#!/usr/bin/env python3
"""Generate Shoutout Song landing pages, hubs, sitemap.xml, robots.txt and llms.txt.

Usage:  python3 tools/seo/build.py
Writes into frontend/. Safe to re-run; it only overwrites files it generates.

Pages are written as flat files (frontend/<slug>.html). The live Render static
site already serves /privacy -> privacy.html, so /<slug> resolves the same way.
"""
import datetime
import html
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).parent))
from pages_data import ADULT, ALL_PAGES, KID_OCCASIONS, KIDS, SHARED_FAQS  # noqa: E402

SITE = "https://shoutoutsong.com"
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "frontend"
TODAY = datetime.date.today().isoformat()
PRICE = "4.99"
BY_SLUG = {p["slug"]: p for p in ALL_PAGES}

PLAUSIBLE = """  <script async src="https://plausible.io/js/pa-Lr_14gVhbTd58se5r3yzQ.js"></script>
  <script>window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};plausible.init()</script>"""

HUBS = {
    "kids-songs": dict(
        title="Custom Kids Songs With Your Child's Name | Shoutout Song",
        desc="Personalized songs for kids about anything they love: dinosaurs, unicorns, trucks, space and more. With their name, ready in about a minute.",
        h1="Custom songs for kids, starring your kid",
        intro="Pick what your child is into, or type anything at all. Every song is written fresh with their name and sung as a finished track in about a minute.",
        groups=[("Songs by occasion", KID_OCCASIONS), ("Songs by what they love", KIDS)],
    ),
    "song-gifts": dict(
        title="Personalized Song Gifts for Any Occasion | Shoutout Song",
        desc="Custom songs for birthdays, anniversaries, retirements, roasts and more. Your details, any of 36 genres, ready in about a minute. $4.99.",
        h1="Personalized song gifts for any occasion",
        intro="Tell us who it's for and a few details. Shoutout Song writes the lyrics, sings them in the genre you pick, and hands you an MP3 in about a minute.",
        groups=[("Song gifts for grown-ups", ADULT)],
    ),
}

ROBOTS = f"""# Shoutout Song
User-agent: *
Allow: /
Disallow: /success
Disallow: /cancel
Disallow: /share.html

# AI search and assistant crawlers are welcome
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

Sitemap: {SITE}/sitemap.xml
"""


def e(s):
    return html.escape(s, quote=True)


def cta_href(page):
    params = {k: v for k, v in page["prefill"].items()}
    if page["kind"] == "kid":
        params.setdefault("tab", "kid")
    return "/?" + urlencode(params) + "#create" if params else "/#create"


def head(title, desc, path, jsonld):
    url = SITE + path
    ld = "\n".join(
        f'  <script type="application/ld+json">{json.dumps(block, ensure_ascii=False)}</script>' for block in jsonld
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{e(title)}</title>
  <meta name="description" content="{e(desc)}" />
  <link rel="canonical" href="{url}" />
  <link rel="icon" type="image/x-icon" href="/favicon.ico" />
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Shoutout Song" />
  <meta property="og:title" content="{e(title)}" />
  <meta property="og:description" content="{e(desc)}" />
  <meta property="og:url" content="{url}" />
  <meta property="og:image" content="{SITE}/logo.png" />
  <meta name="twitter:card" content="summary" />
  <link rel="stylesheet" href="/seo.css" />
{ld}
{PLAUSIBLE}
</head>
<body>
  <header class="top">
    <a class="brand" href="/"><img src="/logo.png" alt="" width="36" height="36" /> Shoutout Song</a>
    <nav><a href="/kids-songs">Kids songs</a><a href="/song-gifts">Song gifts</a><a href="/faq">FAQ</a></nav>
  </header>
"""


FOOT = """  <footer class="foot">
    <nav>
      <a href="/">Make a song</a><a href="/kids-songs">Kids songs</a><a href="/song-gifts">Song gifts</a><a href="/faq">FAQ</a>
    </nav>
    <nav class="legal">
      <a href="/terms.html">Terms</a><a href="/privacy.html">Privacy</a><a href="/refund.html">Refunds</a><a href="/content-policy.html">Content</a>
    </nav>
    <p>Shoutout Song · Custom songs written and sung in about a minute.</p>
  </footer>
</body>
</html>
"""


def breadcrumb(items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": SITE + path}
            for i, (name, path) in enumerate(items)
        ],
    }


def faq_ld(faqs):
    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs
        ],
    }


def product_ld(page):
    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": page["h1"],
        "description": page["desc"],
        "brand": {"@type": "Brand", "name": "Shoutout Song"},
        "image": SITE + "/logo.png",
        "url": SITE + "/" + page["slug"],
        "offers": {
            "@type": "Offer",
            "price": PRICE,
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "url": SITE + "/" + page["slug"],
        },
    }


def faq_html(faqs):
    return "\n".join(
        f"      <details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faqs
    )


def build_page(page):
    hub = ("Kids songs", "/kids-songs") if page["kind"] == "kid" else ("Song gifts", "/song-gifts")
    faqs = page["faqs"] + SHARED_FAQS
    name, lines = page["sample"]
    path = "/" + page["slug"]
    href = cta_href(page)
    btn = "Make their song" if page["kind"] == "kid" else "Make the song"
    related = "\n".join(
        f'        <li><a href="/{s}">{e(BY_SLUG[s]["h1"])}</a></li>' for s in page["related"] if s in BY_SLUG
    )
    body = f"""  <main class="wrap">
    <nav class="crumbs"><a href="/">Home</a> › <a href="{hub[1]}">{hub[0]}</a></nav>
    <section class="hero">
      <h1>{e(page["h1"])}</h1>
{"".join(f'      <p class="lead">{e(p)}</p>{chr(10)}' for p in page["intro"])}      <p class="facts"><span>Free 15-second preview</span><span>Full song $4.99</span><span>Ready in about a minute</span></p>
      <a class="cta" href="{e(href)}">{btn} →</a>
    </section>

    <section class="card">
      <h2>Sample verse</h2>
      <p class="muted">Written for this page with the example name “{e(name)}”. Your song is written fresh from your details.</p>
      <blockquote class="lyrics">{"<br />".join(e(l) for l in lines)}</blockquote>
    </section>

    <section class="card">
      <h2>Make it personal</h2>
      <ul class="ideas">
{"".join(f"        <li>{e(i)}</li>{chr(10)}" for i in page["ideas"])}      </ul>
      <ol class="how">
        <li><b>Type the name and what they love.</b> Add as many details as you like.</li>
        <li><b>Pick a voice{" and vibe" if page["kind"] == "adult" else ""}.</b> {"Funny, happy, emotional or hype, in 36 genres." if page["kind"] == "adult" else "Boy, girl, child-like, or surprise me."}</li>
        <li><b>Preview free, then download.</b> Get the full MP3 and a share link for $4.99.</li>
      </ol>
      <a class="cta" href="{e(href)}">{btn} →</a>
    </section>

    <section class="card">
      <h2>Questions</h2>
{faq_html(faqs)}
    </section>

    <section class="card">
      <h2>More song ideas</h2>
      <ul class="links">
{related}
      </ul>
    </section>
  </main>
"""
    ld = [breadcrumb([("Home", "/"), hub, (page["h1"], path)]), product_ld(page), faq_ld(faqs)]
    return head(page["title"], page["desc"], path, ld) + body + FOOT


def build_hub(slug, hub):
    path = "/" + slug
    groups = ""
    items = []
    for heading, pages in hub["groups"]:
        lis = "\n".join(
            f'        <li><a href="/{p["slug"]}"><b>{e(p["h1"])}</b><span>{e(p["desc"])}</span></a></li>' for p in pages
        )
        items += pages
        groups += f"""    <section class="card">
      <h2>{e(heading)}</h2>
      <ul class="grid">
{lis}
      </ul>
    </section>
"""
    first = hub["groups"][0][1][0]
    href = "/?tab=adult#create" if first["kind"] == "adult" else "/?tab=kid#create"
    body = f"""  <main class="wrap">
    <section class="hero">
      <h1>{e(hub["h1"])}</h1>
      <p class="lead">{e(hub["intro"])}</p>
      <p class="facts"><span>Free 15-second preview</span><span>Full song $4.99</span><span>Ready in about a minute</span></p>
      <a class="cta" href="{href}">Make a song →</a>
    </section>
{groups}  </main>
"""
    ld = [
        breadcrumb([("Home", "/"), (hub["h1"], path)]),
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": SITE + "/" + p["slug"], "name": p["h1"]}
                for i, p in enumerate(items)
            ],
        },
    ]
    return head(hub["title"], hub["desc"], path, ld) + body + FOOT


def build_faq():
    faqs = SHARED_FAQS + [
        ("Who is Shoutout Song for?", "Parents, grandparents, friends and coworkers who want a fast, personal gift: kids' birthday songs, songs about a child's favorite things, anniversary songs, roasts, retirement send-offs and more."),
        ("Can I make a song for a child?", "Yes. Use the Kids song form: enter the child's first name, what they love, the occasion and a voice. Kids songs are upbeat, family-friendly sing-alongs."),
        ("What genres can I choose?", "Adult and special-occasion songs come in 36 genres, including pop, rock, country, hip hop, R&B, EDM, musical, sea shanty, 80's synth pop and 1920's jazz."),
        ("What if I don't like the song?", "Listen to the free preview first. If it's not right, use \"Try another\" to generate a new version before you buy. See the refund policy for purchased songs."),
        ("Can I use the song in a video?", "Yes, for personal use: party slideshows, family videos and posts. See the terms for details."),
        ("Are songs copied from real artists or shows?", "No. Songs are original AI-generated works. They don't copy existing songs or use characters from movies or shows."),
    ]
    body = f"""  <main class="wrap">
    <section class="hero">
      <h1>Shoutout Song FAQ</h1>
      <p class="lead">Shoutout Song makes custom songs in about a minute. Type a name and a few details, preview 15 seconds for free, and get the full MP3 for $4.99.</p>
      <a class="cta" href="/#create">Make a song →</a>
    </section>
    <section class="card">
{faq_html(faqs)}
    </section>
  </main>
"""
    ld = [breadcrumb([("Home", "/"), ("FAQ", "/faq")]), faq_ld(faqs)]
    return head("FAQ – Custom Songs in a Minute | Shoutout Song", "Answers about Shoutout Song: price, how long it takes, kids songs, genres, previews, and how songs are made.", "/faq", ld) + body + FOOT


def build_llms():
    lines = [
        "# Shoutout Song",
        "",
        "> Shoutout Song (shoutoutsong.com) makes custom, personalized songs in about a minute. "
        "Enter a name and what the person loves; it writes the lyrics with AI and sings and produces a full track. "
        "Free 15-second preview; the full MP3 with a share link is $4.99, no subscription.",
        "",
        "- Kids songs: upbeat, family-friendly sing-alongs with the child's name and favorite things (dinosaurs, trucks, unicorns, space, etc.). Voices: boy, girl, child-like.",
        "- Adult and special-occasion songs: birthdays, anniversaries, roasts, retirements, graduations, Mother's Day, Father's Day. Vibes: funny, happy, emotional, hype. 36 genres.",
        "- Songs are original AI-generated works; they don't copy existing songs or use movie/TV characters.",
        "",
        "## Main pages",
        f"- [Make a song]({SITE}/): the song generator",
        f"- [Kids songs]({SITE}/kids-songs): personalized songs for children",
        f"- [Song gifts]({SITE}/song-gifts): personalized songs for adults and occasions",
        f"- [FAQ]({SITE}/faq): price, timing, genres, previews",
        "",
        "## Kids songs",
    ]
    lines += [f"- [{p['h1']}]({SITE}/{p['slug']}): {p['desc']}" for p in KID_OCCASIONS + KIDS]
    lines += ["", "## Song gifts"]
    lines += [f"- [{p['h1']}]({SITE}/{p['slug']}): {p['desc']}" for p in ADULT]
    lines += ["", "## Optional", f"- [Terms]({SITE}/terms.html)", f"- [Refund policy]({SITE}/refund.html)", f"- [Content policy]({SITE}/content-policy.html)", ""]
    return "\n".join(lines)


def build_sitemap(paths):
    urls = "\n".join(
        f"  <url><loc>{SITE}{p}</loc><lastmod>{TODAY}</lastmod></url>" for p in paths
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
"""


def main():
    seen = set()
    for p in ALL_PAGES:
        assert p["slug"] not in seen, f"duplicate slug {p['slug']}"
        seen.add(p["slug"])
        for r in p["related"]:
            assert r in BY_SLUG, f"{p['slug']}: unknown related slug {r}"
        (OUT / f"{p['slug']}.html").write_text(build_page(p))
    for slug, hub in HUBS.items():
        (OUT / f"{slug}.html").write_text(build_hub(slug, hub))
    (OUT / "faq.html").write_text(build_faq())
    paths = ["/", "/kids-songs", "/song-gifts", "/faq"] + ["/" + p["slug"] for p in ALL_PAGES]
    # Example songs made by tools/marketing/daily.py
    examples = ROOT / "tools" / "marketing" / "songs.json"
    if examples.exists():
        songs = json.loads(examples.read_text())
        if songs:
            paths += ["/example-songs"] + ["/" + s["slug"] for s in songs]
    (OUT / "sitemap.xml").write_text(build_sitemap(paths))
    (OUT / "robots.txt").write_text(ROBOTS)
    (OUT / "llms.txt").write_text(build_llms())
    print(f"Built {len(ALL_PAGES)} pages + {len(HUBS)} hubs + faq; sitemap has {len(paths)} URLs")


if __name__ == "__main__":
    main()
