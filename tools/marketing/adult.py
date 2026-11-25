#!/usr/bin/env python3
"""Make one adult example song (mostly roasts), render a vertical video, publish its page, and post it.

Runs daily from .github/workflows/daily-song-video.yml (the evening schedule). Locally:

    python3 tools/marketing/adult.py                       # next in the rotation
    python3 tools/marketing/adult.py --occasion roast --genre metal --name Mike
    python3 tools/marketing/adult.py --no-post

Uses the same environment variables as daily.py.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import adult_config as cfg  # noqa: E402
from daily import (API, OUT, build_captions, chorus_start, duration, load, post_video,  # noqa: E402
                   slugify, poll_song)
from pages import FRONT, ROOT, SITE, build_all  # noqa: E402
from render_video import render_adult, require_ffmpeg  # noqa: E402

STATE = HERE / "adult_state.json"
MANIFEST = HERE / "adult_songs.json"
KIDS_MANIFEST = HERE / "songs.json"


# ---------------------------------------------------------------- picking
def nth_sunday(year, month, n):
    d = datetime.date(year, month, 1)
    d += datetime.timedelta(days=(6 - d.weekday()) % 7)
    return d + datetime.timedelta(weeks=n - 1)


def in_window(today, season):
    if season.get("mothers_day") or season.get("fathers_day"):
        day = nth_sunday(today.year, 5, 2) if season.get("mothers_day") else nth_sunday(today.year, 6, 3)
        return day - datetime.timedelta(days=season.get("days_before", 14)) <= today <= day
    sm, sd = map(int, season["start"].split("-"))
    em, ed = map(int, season["end"].split("-"))
    now = (today.month, today.day)
    return (sm, sd) <= now <= (em, ed) if (sm, sd) <= (em, ed) else (now >= (sm, sd) or now <= (em, ed))


def rotation():
    """Occasions spread out by weight, e.g. roast, birthday, roast, anniversary, roast..."""
    pool = []
    for occ in cfg.OCCASIONS:
        pool += [occ] * occ["weight"]
    roasts = [o for o in pool if o["key"] == "roast"]
    others = [o for o in pool if o["key"] != "roast"]
    out = []
    while roasts or others:
        if roasts:
            out.append(roasts.pop())
        if others and (len(out) % 2 == 1 or not roasts):
            out.append(others.pop(0))
    return out


def pick_occasion(i, today):
    rot = rotation()
    for season in cfg.SEASONS:
        if in_window(today, season):
            return season["occasion"] if i % 2 == 0 else rot[(i // 2) % len(rot)]
    return rot[i % len(rot)]


def pick(lst, i):
    return lst[i % len(lst)]


# ---------------------------------------------------------------- song
def generate_adult_song(name, occ, genre, detail):
    body = {
        "recipient_name": name,
        "story_or_details": f"{name} {detail}." if detail.startswith("who ") or occ["key"] == "roast" else detail,
        "genre": genre,
        "duration_seconds": cfg.SONG_SECONDS,
        "relationship": occ["relationship"],
        "occasion": occ["occasion"],
        "vibe": occ["vibe"],
        "voice_type": "any",
    }
    r = requests.post(f"{API}/generate-adult-song", json=body, timeout=300)
    r.raise_for_status()
    data = r.json()
    task_id, lyrics = data["task_id"], data.get("lyrics", "")
    print(f"Song task {task_id} started")
    return task_id, lyrics, poll_song(task_id)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name")
    ap.add_argument("--occasion", help="roast, birthday, anniversary, bestfriend, retirement, graduation, christmas...")
    ap.add_argument("--genre", help="e.g. metal, country, musical")
    ap.add_argument("--no-post", action="store_true")
    args = ap.parse_args()
    require_ffmpeg()

    state = load(STATE, {"next": 0})
    songs = load(MANIFEST, [])
    i = state["next"]
    today = datetime.date.today()

    occ = pick_occasion(i, today)
    if args.occasion:
        everything = cfg.OCCASIONS + [s["occasion"] for s in cfg.SEASONS]
        occ = next((o for o in everything if o["key"] == args.occasion.lower()), occ)
    # Each occasion keeps its own counter so genres/details rotate within it
    n = state.get(occ["key"], 0)
    name = args.name or pick(cfg.NAMES, i * 7)
    genre = args.genre or pick(occ["genres"], n)
    detail = pick(occ["details"], n * 3)  # *3 so consecutive videos don't reuse neighbouring lines
    g = cfg.GENRES.get(genre, dict(badge=genre.title(), tag=slugify(genre).replace("-", "")))
    badge = f"{g['badge']} {occ['label']}" if "Roast" in occ["label"] else f"{g['badge']} {occ['label']} Song"
    line = occ["line"].format(detail=detail)

    slug = f"{slugify(name)}-{slugify(g['badge'])}-{slugify(occ['label'])}-song"
    if any(s["slug"] == slug for s in songs):
        slug += "-" + today.strftime("%y%m%d")
    print(f"Making {slug}: {badge} for {name}, {line}")

    work = OUT / slug
    work.mkdir(parents=True, exist_ok=True)
    task_id, lyrics, choice = generate_adult_song(name, occ, genre, detail)
    audio_url = choice.get("url") or choice.get("audio_url")
    full = work / "full.mp3"
    full.write_bytes(requests.get(audio_url, timeout=120).content)
    (work / "song.json").write_text(json.dumps({"task_id": task_id, "lyrics": lyrics, "choice": choice}, indent=1))

    total = duration(full)
    length = min(cfg.CLIP_SECONDS, total)
    start = chorus_start(choice)
    if start + length > total:
        start = max(0.0, total - length)
    clip = FRONT / "audio" / f"{slug}.mp3"
    clip.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-t", f"{length:.2f}", "-i", str(full),
                    "-af", f"afade=t=in:d=0.4,afade=t=out:st={max(0, length - 1.5):.2f}:d=1.5",
                    "-b:a", "128k", str(clip)], check=True)

    caps = build_captions(choice, lyrics, start, length)
    video = work / f"{slug}.mp4"
    render_adult(name, badge, line, occ["cta"], genre, clip, caps, video, work)
    print(f"Video: {video}")

    page_url = f"{SITE}/{slug}"
    caption = pick(occ["captions"], n).format(name=name, detail=detail, genre=g["badge"].lower())
    tags = cfg.BASE_HASHTAGS + occ["tags"] + [g["tag"]]
    caption = f"{caption}\n\n{cfg.CAPTION_ENDING}\n\n" + " ".join("#" + t for t in tags)
    title = f"{badge} for {name} 🎶 Custom Song"[:100]
    description = (f"A {badge.lower()} for {name}, {line} 😂\n\n"
                   f"👉 Make one for anyone: {page_url}\n"
                   f"Free preview, ready in about a minute. 36 genres.\n\n"
                   + " ".join("#" + t for t in tags))

    song = dict(slug=slug, kind="adult", name=name, occasion=occ["occasion"], occasion_key=occ["key"],
                label=occ["label"], badge=badge, line=line, genre=genre, vibe=occ["vibe"],
                relationship=occ["relationship"], page=occ["page"], cta=occ["cta"],
                audio=f"/audio/{slug}.mp3", lyrics=lyrics, task_id=task_id,
                date=today.isoformat(), caption=caption)
    songs.append(song)
    MANIFEST.write_text(json.dumps(songs, indent=1))
    build_all(load(KIDS_MANIFEST, []), songs)
    subprocess.run([sys.executable, str(ROOT / "tools" / "seo" / "build.py")], check=True)
    if not (args.name or args.occasion or args.genre):
        state["next"] = i + 1
        state[occ["key"]] = n + 1
        STATE.write_text(json.dumps(state))

    if args.no_post or os.getenv("AUTO_POST", "").lower() != "true":
        print("AUTO_POST is not 'true': video built but not posted")
    else:
        try:
            song["posted"] = post_video(song, video, caption, title, description, made_for_kids="false")
        except Exception as exc:
            print(f"::warning::Posting failed: {exc}")
            song["posted"] = {"error": str(exc)[:300]}
        MANIFEST.write_text(json.dumps(songs, indent=1))

    gh_out = os.getenv("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"slug={slug}\nvideo={video}\n")


if __name__ == "__main__":
    main()
