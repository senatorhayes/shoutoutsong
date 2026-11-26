#!/usr/bin/env python3
"""Make one example song, turn it into a vertical video, publish its page, and post it.

Runs daily from .github/workflows/daily-song-video.yml. Can also run locally:

    python3 tools/marketing/daily.py                 # next name/theme in the queue
    python3 tools/marketing/daily.py --name Olivia --theme dinosaurs
    python3 tools/marketing/daily.py --no-post       # never post, just build

Environment:
    SHOUTOUT_API          backend URL (default https://shoutoutsong.onrender.com)
    UPLOAD_POST_API_KEY   Upload-Post API key (posting is skipped without it)
    UPLOAD_POST_USER      Upload-Post profile name holding the connected accounts
    AUTO_POST             must be "true" to actually post
    PLATFORMS             comma list, default tiktok,instagram,youtube,facebook
    YT_MADE_FOR_KIDS      "true" (default) or "false"
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config  # noqa: E402
from pages import FRONT, ROOT, SITE, build_all, lower_label  # noqa: E402
from render_video import render, require_ffmpeg  # noqa: E402

API = os.getenv("SHOUTOUT_API", "https://shoutoutsong.onrender.com").rstrip("/")
STATE = HERE / "state.json"
MANIFEST = HERE / "songs.json"
OUT = HERE / "out"


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ---------------------------------------------------------------- song
def generate_song(name, love):
    # timeout allows for the backend queueing behind other songs (it retries ~2.5 min)
    r = requests.post(f"{API}/generate-kid-song",
                      json={"child_name": name, "theme": love, "duration_seconds": config.SONG_SECONDS},
                      timeout=300)
    r.raise_for_status()
    data = r.json()
    task_id, lyrics = data["task_id"], data.get("lyrics", "")
    print(f"Song task {task_id} started")
    return task_id, lyrics, poll_song(task_id)


def poll_song(task_id):
    deadline = time.time() + 15 * 60
    while time.time() < deadline:
        time.sleep(10)
        s = requests.get(f"{API}/song-status/{task_id}", timeout=60)
        s.raise_for_status()
        st = s.json()
        status = st.get("status")
        if status == "succeeded" and st.get("choices"):
            return st["choices"][0]
        if status in ("failed", "error", "timeouted", "cancelled"):
            raise SystemExit(f"Song generation {status}: {json.dumps(st)[:500]}")
        print(f"  status: {status}")
    raise SystemExit("Song generation timed out")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def ms(v):
    return v / 1000 if isinstance(v, (int, float)) else None


def chorus_start(choice):
    for sec in choice.get("lyrics_sections") or []:
        if str(sec.get("section_type", "")).lower() == "chorus" and ms(sec.get("start")) is not None:
            return ms(sec["start"])
    return 0.0


def timed_lines(choice):
    """Lyric lines with start/end seconds, if the generator returned them."""
    lines = []
    for sec in choice.get("lyrics_sections") or []:
        for ln in sec.get("lines") or []:
            text = (ln.get("text") or ln.get("line") or "").strip()
            start = ms(ln.get("start"))
            if text and start is not None:
                lines.append([start, ms(ln.get("end")), text])
    lines.sort()
    for i, ln in enumerate(lines):
        if ln[1] is None:
            ln[1] = lines[i + 1][0] if i + 1 < len(lines) else ln[0] + 3
    return lines


def chorus_text(lyrics):
    block, inside = [], False
    for raw in lyrics.splitlines():
        line = raw.strip()
        if re.match(r"^chorus\b", line, re.I):
            inside = True
            continue
        if inside:
            if not line or re.match(r"^(verse|bridge|outro|intro)\b", line, re.I):
                if block:
                    break
                continue
            block.append(line)
    return block


def build_captions(choice, lyrics, start, length):
    lines = timed_lines(choice)
    caps = []
    for s, e_, text in lines:
        if e_ <= start or s >= start + length:
            continue
        caps.append((max(0.0, s - start), min(length, e_ - start), text))
    if caps:
        return caps
    # No timing from the generator: show the chorus two lines at a time, evenly spaced.
    chorus = chorus_text(lyrics)
    pairs = [" ".join(chorus[i:i + 2]) for i in range(0, len(chorus), 2)] or [""]
    step = length / len(pairs)
    return [(i * step, (i + 1) * step, p) for i, p in enumerate(pairs) if p]


# ---------------------------------------------------------------- themes
def easter(year):
    """Western Easter date (anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return datetime.date(year, month, day)


def in_window(today, season):
    if season.get("easter"):
        e = easter(today.year)
        return e - datetime.timedelta(days=season.get("days_before", 21)) <= today <= e
    sm, sd = map(int, season["start"].split("-"))
    em, ed = map(int, season["end"].split("-"))
    start = (sm, sd)
    end = (em, ed)
    now = (today.month, today.day)
    return start <= now <= end if start <= end else (now >= start or now <= end)


def rotation():
    """Themes in posting order; weight-2 themes (vehicles, dinosaurs...) get a second turn
    in the back half of each cycle."""
    heavy = [t for t in config.THEMES if t.get("weight", 1) >= 2]
    return list(config.THEMES) + heavy


def pick_theme(i, today):
    rot = rotation()
    for season in config.SEASONS:
        if in_window(today, season):
            if i % 3 < round(config.SEASON_SHARE * 3):
                return season["theme"]
            return rot[(i // 3) % len(rot)]
    return rot[i % len(rot)]


# ---------------------------------------------------------------- clips
CLIPS = HERE / "clips"
VIDEO_EXT = (".mp4", ".mov", ".webm")


def clip_files(folder):
    return sorted(p for p in (CLIPS / folder).glob("*") if p.suffix.lower() in VIDEO_EXT)


def make_clip(theme, folder):
    """Generate a new cartoon clip on fal.ai and save it (compressed) into clips/<folder>/."""
    key = os.getenv("FAL_KEY")
    if not key:
        return None
    n = len(clip_files(folder))
    subject = theme.get("scene") or f"happy {theme['love']}"
    prompt = config.CLIP_PROMPT.format(subject=subject, action=config.CLIP_ACTIONS[n % len(config.CLIP_ACTIONS)])
    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    body = {"prompt": prompt, "duration": "5", "aspect_ratio": "16:9",
            "negative_prompt": config.CLIP_NEGATIVE, "generate_audio": False}
    print(f"Making a new cartoon clip for '{folder}': {prompt[:90]}...")
    r = requests.post(f"https://queue.fal.run/{config.CLIP_MODEL}", headers=headers, json=body, timeout=60)
    r.raise_for_status()
    sub = r.json()
    deadline = time.time() + 10 * 60
    while time.time() < deadline:
        time.sleep(8)
        st = requests.get(sub["status_url"], headers=headers, timeout=60).json()
        if st.get("status") == "COMPLETED":
            if st.get("error"):
                raise RuntimeError(f"fal error: {st.get('error')}")
            break
    else:
        raise RuntimeError("clip generation timed out")
    res = requests.get(sub["response_url"], headers=headers, timeout=60).json()
    raw = OUT / f"clip-raw-{folder}.mp4"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(requests.get(res["video"]["url"], timeout=120).content)
    dest = CLIPS / folder / f"{folder}-{n + 1}.mp4"
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-an",
                    "-vf", "scale=1080:-2,fps=30", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dest)], check=True)
    return dest


def pick_clip(theme, n):
    """Cartoon clip for this theme. Grows the library up to CLIPS_PER_THEME with new AI clips,
    then rotates through what's there. Falls back to clips/any/, then to no clip."""
    folder = slugify(theme["label"])
    have = clip_files(folder)
    if len(have) < config.CLIPS_PER_THEME:
        try:
            made = make_clip(theme, folder)
            if made:
                return made
        except Exception as exc:
            print(f"::warning::Clip generation failed: {exc}")
    for f in (folder, slugify(theme["love"]), "any"):
        files = clip_files(f)
        if files:
            return files[n % len(files)]
    return None


# ---------------------------------------------------------------- posting
def scheduled_time():
    """POST_AT="HH:MM" (UTC) -> ISO time of the next occurrence, so posts go out at the
    planned time even when GitHub starts the job hours late. If we've just missed it
    (next occurrence is 20+ hours away), post right away instead."""
    at = os.getenv("POST_AT", "").strip()
    if not at:
        return None
    hh, mm = map(int, at.split(":"))
    now = datetime.datetime.now(datetime.timezone.utc)
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if target <= now + datetime.timedelta(minutes=10):
        target += datetime.timedelta(days=1)
    if target - now > datetime.timedelta(hours=20):
        return None
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")


def post_video(song, video_path, caption, title, description, made_for_kids=None):
    key, user = os.getenv("UPLOAD_POST_API_KEY"), os.getenv("UPLOAD_POST_USER")
    if not key or not user:
        print("Posting skipped: UPLOAD_POST_API_KEY / UPLOAD_POST_USER not set")
        return None
    platforms = [p.strip() for p in os.getenv("PLATFORMS", "tiktok,instagram,youtube,facebook").split(",") if p.strip()]
    # Instagram uses the generic description as its caption (links there are not clickable),
    # so the generic fields get the social caption; YouTube/Facebook get the version with the link.
    data = [("user", user), ("title", caption), ("description", caption),
            ("youtube_title", title), ("youtube_description", description),
            ("facebook_title", title), ("facebook_description", description),
            ("is_ai_generated", "true"), ("containsSyntheticMedia", "true"),
            ("selfDeclaredMadeForKids", made_for_kids or os.getenv("YT_MADE_FOR_KIDS", "true")),
            ("post_mode", "DIRECT_POST"), ("media_type", "REELS"),
            ("async_upload", "true")]
    data += [("platform[]", p) for p in platforms]
    when = scheduled_time()
    if when:
        data.append(("scheduled_date", when))
        print(f"Scheduling post for {when}")
    with open(video_path, "rb") as f:
        r = requests.post("https://api.upload-post.com/api/upload",
                          headers={"Authorization": f"Apikey {key}"},
                          data=data, files={"video": (video_path.name, f, "video/mp4")}, timeout=300)
    print(f"Upload-Post response {r.status_code}: {r.text[:800]}")
    r.raise_for_status()
    return {"platforms": platforms, "response": r.json()}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name")
    ap.add_argument("--theme", help="matches a THEMES 'love' or 'label' (e.g. dinosaurs)")
    ap.add_argument("--no-post", action="store_true")
    args = ap.parse_args()
    require_ffmpeg()

    state = load(STATE, {"next": 0})
    songs = load(MANIFEST, [])
    i = state["next"]
    name = args.name or config.NAMES[i % len(config.NAMES)]
    theme = pick_theme(i, datetime.date.today())
    if args.theme:
        q = args.theme.lower()
        theme = next((t for t in config.THEMES + [x["theme"] for x in config.SEASONS] if q in (t["love"].lower(), t["label"].lower())), None) \
            or dict(love=args.theme.lower(), label=args.theme.title(), page="kids-songs", tags=[slugify(args.theme).replace("-", "")])
    slug = f"{slugify(name)}-{slugify(theme['label'])}-song"
    if any(s["slug"] == slug for s in songs):
        slug += "-" + datetime.date.today().strftime("%y%m%d")
    print(f"Making {slug}: {name} loves {theme['love']}")

    work = OUT / slug
    work.mkdir(parents=True, exist_ok=True)
    task_id, lyrics, choice = generate_song(name, theme["love"])
    audio_url = choice.get("url") or choice.get("audio_url")
    full = work / "full.mp3"
    full.write_bytes(requests.get(audio_url, timeout=120).content)
    (work / "song.json").write_text(json.dumps({"task_id": task_id, "lyrics": lyrics, "choice": choice}, indent=1))

    total = duration(full)
    length = min(config.CLIP_SECONDS, total)
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
    cartoon = pick_clip(theme, len(songs))
    print(f"Cartoon clip: {cartoon.relative_to(ROOT) if cartoon else 'none (waveform layout)'}")
    render(name, theme["label"], theme["love"], clip, caps, video, work, clip_path=cartoon)
    print(f"Video: {video}")

    page_url = f"{SITE}/{slug}"
    n = len(songs)
    caption = config.CAPTIONS[n % len(config.CAPTIONS)].format(
        name=name, love=theme["love"], label=theme["label"], label_lower=lower_label(theme["label"]), url=page_url)
    tags = config.BASE_HASHTAGS + theme["tags"] + [f"{slugify(name).replace('-', '')}song"]
    caption = f"{caption}\n\n{config.CAPTION_ENDING}\n\n" + " ".join("#" + t for t in tags)
    title = f"{name}'s {theme['label']} Song 🎶 Custom Kids Song With Their Name"[:100]
    description = (f"{name}'s {lower_label(theme['label'])} song 🎶\n\n"
                   f"Every kid deserves a song all about them. This one's for every {name} who loves {theme['love']}.\n\n"
                   f"👉 Make one with your kid's name: {page_url}\n"
                   f"Free preview, ready in about a minute.\n\n"
                   + " ".join("#" + t for t in tags))

    song = dict(slug=slug, name=name, love=theme["love"], label=theme["label"], page=theme["page"],
                audio=f"/audio/{slug}.mp3", lyrics=lyrics, task_id=task_id,
                date=datetime.date.today().isoformat(), caption=caption)
    songs.append(song)
    MANIFEST.write_text(json.dumps(songs, indent=1))
    build_all(songs)
    subprocess.run([sys.executable, str(ROOT / "tools" / "seo" / "build.py")], check=True)
    if not args.name and not args.theme:
        STATE.write_text(json.dumps({"next": i + 1}))

    if args.no_post or os.getenv("AUTO_POST", "").lower() != "true":
        print("AUTO_POST is not 'true': video built but not posted")
    else:
        try:
            song["posted"] = post_video(song, video, caption, title, description)
        except Exception as exc:  # e.g. monthly upload limit reached: still publish the page
            print(f"::warning::Posting failed: {exc}")
            song["posted"] = {"error": str(exc)[:300]}
        MANIFEST.write_text(json.dumps(songs, indent=1))

    gh_out = os.getenv("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a") as f:
            f.write(f"slug={slug}\nvideo={video}\n")


if __name__ == "__main__":
    main()
