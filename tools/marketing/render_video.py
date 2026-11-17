"""Render a 1080x1920 vertical video for one example song.

Pillow draws the still layers (background, title, captions, call to action) and
ffmpeg adds the animated waveform, times the lyric captions and muxes the audio.
Content is kept out of the areas TikTok/Reels/Shorts cover with their own UI.
"""
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FONT_BOLD = str(HERE / "fonts" / "Poppins-Bold.ttf")
FONT_MED = str(HERE / "fonts" / "Poppins-Medium.ttf")
LOGO = ROOT / "frontend" / "logo.png"

W, H = 1080, 1920
SAFE_L, SAFE_R = 130, 950  # centered on the frame; right edge clear of the like/comment buttons
BG = (5, 7, 19)
ORANGE = (255, 138, 60)
PINK = (255, 77, 210)
CYAN = (77, 220, 255)
WHITE = (247, 247, 255)
MUTED = (156, 163, 199)

WAVE_Y, WAVE_H = 800, 200
CAP_Y, CAP_H = 1040, 230


def font(path, size):
    return ImageFont.truetype(path, size)


def fit_font(draw, text, path, max_size, max_width):
    size = max_size
    while size > 40:
        f = font(path, size)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size -= 6
    return font(path, size)


def wrap(draw, text, f, max_width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if draw.textlength(test, font=f) <= max_width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def centered(draw, y, text, f, fill):
    cx = W / 2
    draw.text((cx, y), text, font=f, fill=fill, anchor="ma")


def gradient_text(img, y, text, f):
    """Orange→pink gradient text, centered in the safe area."""
    d = ImageDraw.Draw(img)
    cx = W / 2
    l, t, r, b = d.textbbox((cx, y), text, font=f, anchor="ma")
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).text((cx, y), text, font=f, fill=255, anchor="ma")
    grad = Image.new("RGB", img.size)
    gd = ImageDraw.Draw(grad)
    span = max(1, r - l)
    for x in range(W):
        k = min(1.0, max(0.0, (x - l) / span))
        col = tuple(int(ORANGE[i] + (PINK[i] - ORANGE[i]) * k) for i in range(3))
        gd.line([(x, 0), (x, H)], fill=col)
    glow = mask.filter(ImageFilter.GaussianBlur(22)).point(lambda v: int(v * 0.5))
    img.paste(grad, (0, 0), glow)
    img.paste(grad, (0, 0), mask)


def background():
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    for (x, y, r, c) in [(150, 300, 520, (40, 30, 90)), (950, 900, 600, (70, 20, 70)), (300, 1650, 650, (60, 35, 20))]:
        gd.ellipse([x - r, y - r, x + r, y + r], fill=c)
    return Image.blend(img, glow.filter(ImageFilter.GaussianBlur(160)), 0.9)


def draw_static(name, label, love, out_png):
    img = background()
    d = ImageDraw.Draw(img)

    # Brand row: logo + name, centered together as one group
    brand_f = font(FONT_BOLD, 50)
    brand = "ShoutOutSong.com"
    tw = d.textlength(brand, font=brand_f)
    logo_size, gap = 76, 16
    has_logo = LOGO.exists()
    total = tw + (logo_size + gap if has_logo else 0)
    x0 = (W - total) / 2
    if has_logo:
        logo = Image.open(LOGO).convert("RGBA").resize((logo_size, logo_size))
        img.paste(logo, (int(x0), 220), logo)
        x0 += logo_size + gap
    d.text((x0, 220 + logo_size / 2), brand, font=brand_f, fill=WHITE, anchor="lm")

    centered(d, 390, "a song for", font(FONT_MED, 56), MUTED)
    name_f = fit_font(d, name, FONT_BOLD, 220, SAFE_R - SAFE_L)
    gradient_text(img, 450, name, name_f)
    d = ImageDraw.Draw(img)
    loves = f"who loves {love}"
    centered(d, 700, loves, fit_font(d, loves, FONT_MED, 58, SAFE_R - SAFE_L), WHITE)

    # Call to action
    cta_f = font(FONT_BOLD, 50)
    cta = "Make one with YOUR kid's name"
    cta_f = fit_font(d, cta, FONT_BOLD, 50, SAFE_R - SAFE_L - 80)
    cw = d.textlength(cta, font=cta_f)
    cx = W / 2
    d.rounded_rectangle([cx - cw / 2 - 40, 1320, cx + cw / 2 + 40, 1420], radius=50, fill=ORANGE)
    d.text((cx, 1370), cta, font=cta_f, fill=(26, 13, 5), anchor="mm")
    centered(d, 1450, "ShoutOutSong.com", font(FONT_BOLD, 60), CYAN)
    centered(d, 1540, "Generate and hear the preview 100% free", font(FONT_MED, 38), WHITE)
    img.save(out_png)


def draw_caption(text, out_png):
    img = Image.new("RGBA", (W, CAP_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(FONT_BOLD, 64)
    lines = wrap(d, text, f, SAFE_R - SAFE_L)
    if len(lines) > 2:
        f = font(FONT_BOLD, 52)
        lines = wrap(d, text, f, SAFE_R - SAFE_L)[:3]
    lh = f.size * 1.2
    y = (CAP_H - lh * len(lines)) / 2
    cx = W / 2
    for ln in lines:
        d.text((cx, y), ln, font=f, fill=WHITE, anchor="ma", stroke_width=5, stroke_fill=(10, 8, 25))
        y += lh
    img.save(out_png)


def render(name, label, love, audio_path, captions, out_mp4, workdir):
    """captions: list of (start_s, end_s, text) relative to the clip start."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    bg = workdir / "bg.png"
    draw_static(name, label, love, bg)

    inputs = ["-loop", "1", "-framerate", "30", "-i", str(bg), "-i", str(audio_path)]
    filters = [
        f"[1:a]showwaves=s=820x{WAVE_H}:mode=cline:rate=30:scale=sqrt:draw=full:colors=0xff8a3c|0xff4dd2,format=rgba[wave]",
        f"[0:v][wave]overlay={(W - 820) // 2}:{WAVE_Y}[v0]",
    ]
    last = "v0"
    for i, (start, end, text) in enumerate(captions):
        png = workdir / f"cap{i}.png"
        draw_caption(text, png)
        inputs += ["-i", str(png)]
        idx = 2 + i
        nxt = f"v{i + 1}"
        filters.append(f"[{last}][{idx}:v]overlay=0:{CAP_Y}:enable='between(t,{start:.2f},{end:.2f})'[{nxt}]")
        last = nxt

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", *inputs,
        "-filter_complex", ";".join(filters),
        "-map", f"[{last}]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)
    return out_mp4


def require_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("ffmpeg/ffprobe not found")
