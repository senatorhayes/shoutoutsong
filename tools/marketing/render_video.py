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


# Layout with an animated cartoon clip (16:9) under the brand row
CLIP_Y, CLIP_H = 230, 608
CLIP_CAP_Y = 1120


def draw_static(name, label, love, out_png, clip=False):
    if clip:
        return draw_static_clip(name, love, out_png)
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

    centered(d, 390, "a custom song for", font(FONT_MED, 56), MUTED)
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
    centered(d, 1450, "Create and preview for free on:", font(FONT_MED, 40), WHITE)
    centered(d, 1510, "ShoutOutSong.com", font(FONT_BOLD, 60), CYAN)
    img.save(out_png)


def brand_row(img, y, size, logo_size):
    d = ImageDraw.Draw(img)
    brand_f = font(FONT_BOLD, size)
    brand = "ShoutOutSong.com"
    tw = d.textlength(brand, font=brand_f)
    gap = 14
    has_logo = LOGO.exists()
    x0 = (W - (tw + (logo_size + gap if has_logo else 0))) / 2
    if has_logo:
        logo = Image.open(LOGO).convert("RGBA").resize((logo_size, logo_size))
        img.paste(logo, (int(x0), int(y)), logo)
        x0 += logo_size + gap
    d.text((x0, y + logo_size / 2), brand, font=brand_f, fill=WHITE, anchor="lm")


def draw_static_clip(name, love, out_png):
    img = background()
    brand_row(img, 150, 40, 60)
    d = ImageDraw.Draw(img)
    # soft frame behind the clip
    d.rounded_rectangle([-10, CLIP_Y - 6, W + 10, CLIP_Y + CLIP_H + 6], radius=0, fill=(20, 16, 40))
    centered(d, 860, "a custom song for", font(FONT_MED, 48), MUTED)
    name_f = fit_font(d, name, FONT_BOLD, 150, SAFE_R - SAFE_L)
    gradient_text(img, 905, name, name_f)
    d = ImageDraw.Draw(img)
    loves = f"who loves {love}"
    centered(d, 1075, loves, fit_font(d, loves, FONT_MED, 50, SAFE_R - SAFE_L), WHITE)
    cta = "Make one with YOUR kid's name"
    cta_f = fit_font(d, cta, FONT_BOLD, 48, SAFE_R - SAFE_L - 80)
    cw = d.textlength(cta, font=cta_f)
    cx = W / 2
    d.rounded_rectangle([cx - cw / 2 - 40, 1355, cx + cw / 2 + 40, 1445], radius=45, fill=ORANGE)
    d.text((cx, 1400), cta, font=cta_f, fill=(26, 13, 5), anchor="mm")
    centered(d, 1465, "Create and preview for free on:", font(FONT_MED, 38), WHITE)
    centered(d, 1515, "ShoutOutSong.com", font(FONT_BOLD, 56), CYAN)
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


def render(name, label, love, audio_path, captions, out_mp4, workdir, clip_path=None):
    """captions: list of (start_s, end_s, text) relative to the clip start.
    clip_path: optional cartoon video; looped above the name instead of the waveform."""
    if clip_path:
        return render_card(name, love, audio_path, captions, out_mp4, workdir, clip_path)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    bg = workdir / "bg.png"
    draw_static(name, label, love, bg)

    inputs = ["-loop", "1", "-framerate", "30", "-i", str(bg), "-i", str(audio_path)]
    if clip_path:
        inputs += ["-stream_loop", "-1", "-i", str(clip_path)]
        filters = [
            f"[2:v]scale={W}:{CLIP_H}:force_original_aspect_ratio=increase,crop={W}:{CLIP_H},fps=30,setsar=1[clip]",
            f"[0:v][clip]overlay=0:{CLIP_Y}:shortest=0[v0]",
        ]
        first_cap, cap_y = 3, CLIP_CAP_Y
    else:
        filters = [
            f"[1:a]showwaves=s=820x{WAVE_H}:mode=cline:rate=30:scale=sqrt:draw=full:colors=0xff8a3c|0xff4dd2,format=rgba[wave]",
            f"[0:v][wave]overlay={(W - 820) // 2}:{WAVE_Y}[v0]",
        ]
        first_cap, cap_y = 2, CAP_Y
    last = "v0"
    for i, (start, end, text) in enumerate(captions):
        png = workdir / f"cap{i}.png"
        draw_caption(text, png)
        inputs += ["-i", str(png)]
        idx = first_cap + i
        nxt = f"v{i + 1}"
        filters.append(f"[{last}][{idx}:v]overlay=0:{cap_y}:enable='between(t,{start:.2f},{end:.2f})'[{nxt}]")
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


# ======================================================================
# Card design: blurred cartoon background, the clip framed as a rounded
# card, kids' font for name and lyrics, yellow call-to-action button.
# ======================================================================
LILITA = str(HERE / "fonts" / "LilitaOne-Regular.ttf")
FREDOKA = str(HERE / "fonts" / "Fredoka-Variable.ttf")
YELLOW = (255, 210, 63)
PURPLE = (58, 20, 90)
HOTPINK = (255, 77, 170)
SHADOW = (30, 10, 50, 150)

CARD_W, CARD_H = 960, 540
CARD_X, CARD_Y = (W - CARD_W) // 2, 650
CARD_R, CARD_BORDER = 40, 10
LYRIC_Y, LYRIC_H = 1200, 190


def fredoka(size, weight="SemiBold"):
    f = ImageFont.truetype(FREDOKA, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def fit(draw, text, path_or_fn, max_size, max_width, min_size=40):
    size = max_size
    while size > min_size:
        f = path_or_fn(size) if callable(path_or_fn) else ImageFont.truetype(path_or_fn, size)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size -= 4
    return path_or_fn(size) if callable(path_or_fn) else ImageFont.truetype(path_or_fn, size)


def pop_text(d, y, text, f, fill, stroke, stroke_fill, shadow=True, x=None):
    x = W / 2 if x is None else x
    if shadow:
        d.text((x + 5, y + 7), text, font=f, fill=SHADOW, anchor="ma", stroke_width=stroke, stroke_fill=SHADOW)
    d.text((x, y), text, font=f, fill=fill, anchor="ma", stroke_width=stroke, stroke_fill=stroke_fill)


def card_background(frame_png):
    """Blurred, slightly darkened full-screen version of the clip's first frame."""
    fr = Image.open(frame_png).convert("RGB")
    scale = max(W / fr.width, H / fr.height)
    fr = fr.resize((int(fr.width * scale) + 1, int(fr.height * scale) + 1))
    left, top = (fr.width - W) // 2, (fr.height - H) // 2
    bg = fr.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(28)).convert("RGBA")
    tint = Image.new("RGBA", (W, H), (40, 15, 70, 70))
    return Image.alpha_composite(bg, tint)


def card_top_layer(bg, name, love, out_png, cta="Make one with YOUR kid's name"):
    """Everything drawn over the playing clip: card corners + border, texts, brand, button."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # Card corners: copy background pixels outside the rounded rectangle so the clip looks rounded.
    hole = Image.new("L", (W, H), 0)
    ImageDraw.Draw(hole).rounded_rectangle([CARD_X, CARD_Y, CARD_X + CARD_W, CARD_Y + CARD_H], radius=CARD_R, fill=255)
    box = Image.new("L", (W, H), 0)
    ImageDraw.Draw(box).rectangle([CARD_X, CARD_Y, CARD_X + CARD_W, CARD_Y + CARD_H], fill=255)
    corners = Image.composite(box, Image.new("L", (W, H), 0), Image.eval(hole, lambda v: 255 - v))
    layer.paste(bg, (0, 0), corners)
    d = ImageDraw.Draw(layer)
    b = CARD_BORDER
    d.rounded_rectangle([CARD_X - b, CARD_Y - b, CARD_X + CARD_W + b, CARD_Y + CARD_H + b],
                        radius=CARD_R + b, outline=(255, 255, 255), width=b)

    # Brand pill at the top
    bf = ImageFont.truetype(LILITA, 46)
    brand = "ShoutOutSong.com"
    tw = d.textlength(brand, font=bf)
    ls, gap, padx = 58, 12, 26
    pw = ls + gap + tw + padx * 2
    px, py = (W - pw) / 2, 150
    d.rounded_rectangle([px + 4, py + 6, px + pw + 4, py + 82], radius=40, fill=SHADOW)
    d.rounded_rectangle([px, py, px + pw, py + 76], radius=38, fill=(255, 255, 255))
    if LOGO.exists():
        logo = Image.open(LOGO).convert("RGBA").resize((ls, ls))
        layer.alpha_composite(logo, (int(px + padx), int(py + 9)))
    d.text((px + padx + ls + gap, py + 38), brand, font=bf, fill=PURPLE, anchor="lm")

    # Title
    pop_text(d, 268, "a custom song for", fredoka(54), (255, 255, 255), 6, PURPLE, shadow=False)
    nf = fit(d, name, LILITA, 200, 900)
    pop_text(d, 330, name, nf, (255, 255, 255), 14, HOTPINK)
    loves = f"who loves {love}"
    pop_text(d, 548, loves, fit(d, loves, fredoka, 56, 900), (255, 255, 255), 6, PURPLE, shadow=False)

    # Call to action
    cf = fit(d, cta, LILITA, 52, 860)
    cw = d.textlength(cta, font=cf)
    x0, y0 = W / 2 - cw / 2 - 44, 1410
    d.rounded_rectangle([x0 + 6, y0 + 8, W - x0 + 6, y0 + 104], radius=50, fill=SHADOW)
    d.rounded_rectangle([x0, y0, W - x0, y0 + 96], radius=48, fill=YELLOW)
    d.text((W / 2, y0 + 48), cta, font=cf, fill=PURPLE, anchor="mm")
    pop_text(d, y0 + 118, "Free preview at ShoutOutSong.com", fredoka(46, "Bold"), (255, 255, 255), 5, PURPLE, shadow=False)
    layer.save(out_png)


def card_caption(text, out_png):
    img = Image.new("RGBA", (W, LYRIC_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(LILITA, 74)
    lines = wrap(d, text, f, 900)
    if len(lines) > 2:
        f = ImageFont.truetype(LILITA, 60)
        lines = wrap(d, text, f, 900)[:2]
    lh = f.size * 1.12
    y = (LYRIC_H - lh * len(lines)) / 2
    for i, ln in enumerate(lines):
        pop_text(d, y, ln, f, YELLOW if i == 0 else (255, 255, 255), 8, PURPLE)
        y += lh
    img.save(out_png)


def render_card(name, love, audio_path, captions, out_mp4, workdir, clip_path):
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    first = workdir / "first.png"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "0.5", "-i", str(clip_path),
                    "-frames:v", "1", str(first)], check=True)
    bg = card_background(first)
    bg_png, top_png = workdir / "card_bg.png", workdir / "card_top.png"
    bg.convert("RGB").save(bg_png)
    card_top_layer(bg, name, love, top_png)

    inputs = ["-loop", "1", "-framerate", "30", "-i", str(bg_png), "-i", str(audio_path),
              "-stream_loop", "-1", "-i", str(clip_path), "-loop", "1", "-framerate", "30", "-i", str(top_png)]
    filters = [
        f"[2:v]scale={CARD_W}:{CARD_H}:force_original_aspect_ratio=increase,crop={CARD_W}:{CARD_H},fps=30,setsar=1[clip]",
        f"[0:v][clip]overlay={CARD_X}:{CARD_Y}[a]",
        "[a][3:v]overlay=0:0[v0]",
    ]
    last = "v0"
    for i, (start, end, text) in enumerate(captions):
        png = workdir / f"lyric{i}.png"
        card_caption(text, png)
        inputs += ["-i", str(png)]
        nxt = f"v{i + 1}"
        filters.append(f"[{last}][{4 + i}:v]overlay=0:{LYRIC_Y}:enable='between(t,{start:.2f},{end:.2f})'[{nxt}]")
        last = nxt
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
           "-map", f"[{last}]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out_mp4)]
    subprocess.run(cmd, check=True)
    return out_mp4
