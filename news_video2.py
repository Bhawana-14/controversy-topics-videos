#!/usr/bin/env python3
"""Realistic TV-studio style Hindi news roundup (faceless anchor silhouette).
Usage: python3 news_video2.py script.json OUTDIR   (PREVIEW=1 for stills only, RESUME=1 to reuse segments)
"""
import json, math, os, subprocess, sys, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

ASSETS = os.environ.get("KAHANI_ASSETS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))
W, H, FPS, SR = 1280, 720, 30, 24000
VOICE, SPEED = "hm_omega", 1.05
GAP = 0.25
CH_NAME = "CONTROVERSY TOPICS"
RED, DRED, YEL, WHITE, INK = (200, 16, 30), (130, 8, 18), (255, 204, 0), (255, 255, 255), (18, 20, 28)
WALL = (520, 78, 1250, 478)  # x0,y0,x1,y1
MIRROR = False
BG_TOP, BG_BOT = (10, 18, 44), (3, 5, 14)
LIGHT = (120, 170, 255)
THEMES = {
    "red":    dict(RED=(200, 16, 30), DRED=(130, 8, 18), YEL=(255, 204, 0), BG_TOP=(10, 18, 44), BG_BOT=(3, 5, 14), LIGHT=(120, 170, 255)),
    "blue":   dict(RED=(0, 92, 200), DRED=(0, 50, 120), YEL=(0, 220, 255), BG_TOP=(4, 22, 40), BG_BOT=(1, 6, 12), LIGHT=(80, 220, 255)),
    "purple": dict(RED=(120, 30, 200), DRED=(70, 10, 120), YEL=(255, 190, 40), BG_TOP=(26, 8, 40), BG_BOT=(6, 2, 12), LIGHT=(200, 120, 255)),
    "orange": dict(RED=(230, 90, 0), DRED=(150, 50, 0), YEL=(255, 230, 120), BG_TOP=(30, 16, 8), BG_BOT=(8, 4, 2), LIGHT=(255, 170, 90)),
}
def apply_theme(name, mirror):
    global RED, DRED, YEL, BG_TOP, BG_BOT, LIGHT, WALL, MIRROR
    for k, v in THEMES[name].items():
        globals()[k] = v
    MIRROR = mirror
    WALL = (30, 78, 760, 478) if mirror else (520, 78, 1250, 478)
def DESKX():
    return (720, W) if MIRROR else (0, 560)
def desk_pts():
    a, b = DESKX(); w = b - a
    return [(a, 545), (a + w * .21, 528), (a + w * .54, 522), (a + w * .86, 528), (b, 545), (b, H), (a, H)]

_f = {}
def F(name, size):
    k = (name, size)
    if k not in _f:
        _f[k] = ImageFont.truetype(os.path.join(ASSETS, "fonts", name), size, layout_engine=ImageFont.Layout.RAQM)
    return _f[k]
HB = lambda s: F("Hind_700Bold.ttf", s)
HS = lambda s: F("Hind_600SemiBold.ttf", s)
HM = lambda s: F("Hind_500Medium.ttf", s)
OS = lambda s: F("Oswald_700Bold.ttf", s)

def wrap(text, f, maxw):
    d = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            if cur: out.append(cur)
            cur = w
    if cur: out.append(cur)
    return out

def tl(d, s, f):
    return d.textlength(s, font=f)

# ---------------- studio ----------------
def studio_bg():
    rnd = random.Random(7)
    y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
    base = np.zeros((H, W, 3), np.float32)
    top = np.array(BG_TOP); bot = np.array(BG_BOT)
    base[:] = (top * (1 - y[..., None]) + bot * y[..., None])
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    # bokeh city lights
    bok = Image.new("RGB", (W, H), (0, 0, 0)); d = ImageDraw.Draw(bok)
    for _ in range(140):
        cx, cy, r = rnd.randint(0, W), rnd.randint(40, 520), rnd.choice([4, 6, 8, 10, 14, 18])
        c = rnd.choice([(255, 170, 80), (90, 150, 255), (255, 60, 70), (200, 220, 255)])
        a = rnd.uniform(0.15, 0.55)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=tuple(int(v * a) for v in c))
    bok = bok.filter(ImageFilter.GaussianBlur(6))
    img = ImageChops.add(img, bok)
    d = ImageDraw.Draw(img, "RGBA")
    # vertical light columns
    for xx in ((18, 810, 1240) if MIRROR else (40, 470, 1262)):
        col = Image.new("RGBA", (60, H), (0, 0, 0, 0))
        ImageDraw.Draw(col).rectangle([24, 0, 36, H], fill=LIGHT + (70,))
        img.paste(col.filter(ImageFilter.GaussianBlur(10)), (xx - 30, 0), col.filter(ImageFilter.GaussianBlur(10)))
    # floor + reflection
    fl = Image.new("RGBA", (W, H - 470), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fl)
    for i in range(H - 470):
        fd.line([0, i, W, i], fill=(20, 40, 90, int(40 * (1 - i / (H - 470)))))
    img.paste(fl, (0, 470), fl)
    # video wall bezel + glass
    x0, y0, x1, y1 = WALL
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rectangle([x0 - 8, y0 - 8, x1 + 8, y1 + 8], fill=LIGHT + (90,))
    img.paste(glow.filter(ImageFilter.GaussianBlur(18)), (0, 0), glow.filter(ImageFilter.GaussianBlur(18)))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([x0 - 6, y0 - 6, x1 + 6, y1 + 6], fill=(14, 16, 22))
    # desk (curved, glossy)
    desk = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(desk)
    dd.polygon(desk_pts(), fill=(22, 28, 44, 255))
    img.paste(desk, (0, 0), desk)
    # vignette
    vx = (x - 0.5) ** 2; vy = (y - 0.5) ** 2
    v = 1 - np.clip((vx + vy) * 1.1, 0, 0.6)
    arr = np.asarray(img).astype(np.float32) * v[..., None]
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8)).convert("RGBA")

def anchor_sprite():
    """Faceless anchor: dark silhouette with rim light (head + shoulders + suit)."""
    S = 2  # supersample
    w, h = 600 * S, 470 * S
    sil = Image.new("L", (w, h), 0); d = ImageDraw.Draw(sil)
    cx = w // 2
    # head + hair
    d.ellipse([cx - 78 * S, 40 * S, cx + 78 * S, 230 * S], fill=255)
    d.ellipse([cx - 84 * S, 26 * S, cx + 84 * S, 150 * S], fill=255)
    # ears
    d.ellipse([cx - 92 * S, 120 * S, cx - 66 * S, 170 * S], fill=255)
    d.ellipse([cx + 66 * S, 120 * S, cx + 92 * S, 170 * S], fill=255)
    # neck
    d.polygon([(cx - 44 * S, 200 * S), (cx + 44 * S, 200 * S), (cx + 52 * S, 280 * S), (cx - 52 * S, 280 * S)], fill=255)
    # shoulders / suit
    d.polygon([(cx - 60 * S, 262 * S), (cx - 190 * S, 300 * S), (cx - 225 * S, 350 * S), (cx - 230 * S, h), (cx + 230 * S, h),
               (cx + 225 * S, 350 * S), (cx + 190 * S, 300 * S), (cx + 60 * S, 262 * S)], fill=255)
    sil = sil.filter(ImageFilter.GaussianBlur(1.2 * S))
    body = Image.new("RGBA", (w, h), (12, 14, 22, 255)); body.putalpha(sil)
    # suit details: shirt V, tie, lapels (slightly lighter)
    det = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dd = ImageDraw.Draw(det)
    dd.polygon([(cx - 46 * S, 272 * S), (cx + 46 * S, 272 * S), (cx, 400 * S)], fill=(150, 155, 170, 255))
    dd.polygon([(cx - 14 * S, 285 * S), (cx + 14 * S, 285 * S), (cx + 20 * S, 420 * S), (cx, 450 * S), (cx - 20 * S, 420 * S)], fill=(120, 14, 24, 255))
    dd.polygon([(cx - 46 * S, 272 * S), (cx - 100 * S, 300 * S), (cx - 30 * S, 470 * S), (cx - 8 * S, 400 * S)], fill=(22, 26, 38, 255))
    dd.polygon([(cx + 46 * S, 272 * S), (cx + 100 * S, 300 * S), (cx + 30 * S, 470 * S), (cx + 8 * S, 400 * S)], fill=(22, 26, 38, 255))
    body.alpha_composite(det)
    # rim light: edge = sil - eroded sil, shifted
    er = sil.filter(ImageFilter.MinFilter(9))
    edge = ImageChops.subtract(sil, er).filter(ImageFilter.GaussianBlur(3 * S))
    rimL = Image.new("RGBA", (w, h), (255, 170, 110, 0)); rimL.putalpha(edge.point(lambda v: int(v * 0.7)))
    rimR = Image.new("RGBA", (w, h), (120, 170, 255, 0)); rimR.putalpha(edge)
    mL = Image.linear_gradient("L").rotate(90).resize((w, h))  # left bright
    mR = ImageChops.invert(mL)
    rimL.putalpha(ImageChops.multiply(rimL.getchannel("A"), mL))
    rimR.putalpha(ImageChops.multiply(rimR.getchannel("A"), mR))
    body.alpha_composite(rimL); body.alpha_composite(rimR)
    # soft back glow
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gl = Image.new("RGBA", (w, h), (70, 110, 220, 0)); gl.putalpha(sil.filter(ImageFilter.GaussianBlur(30 * S)).point(lambda v: int(v * 0.45)))
    out.alpha_composite(gl); out.alpha_composite(body)
    return out.resize((w // S, h // S), Image.LANCZOS)

def mic_sprite():
    m = Image.new("RGBA", (60, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(m)
    d.rounded_rectangle([18, 0, 42, 40], 12, fill=(40, 42, 50), outline=(130, 140, 160), width=2)
    d.rectangle([28, 40, 32, 100], fill=(70, 72, 80))
    d.ellipse([10, 96, 50, 116], fill=(30, 32, 40))
    return m

# ---------------- map ----------------
_land = None
def land():
    global _land
    if _land is None:
        _land = json.load(open(os.path.join(ASSETS, "southasia_land.json")))
    return _land

def map_view(w, h, clon, clat, span):
    """Render coastline map (no political borders) centred on clon/clat, `span` degrees wide."""
    img = Image.new("RGB", (w, h), (8, 22, 42)); d = ImageDraw.Draw(img)
    sx = w / span; kx = math.cos(math.radians(clat))
    def P(lo, la):
        return ((lo - clon) * sx * kx + w / 2, (clat - la) * sx + h / 2)
    for g in range(-180, 181, 2):
        a = P(g, clat + 60); b = P(g, clat - 60); d.line([a, b], fill=(18, 40, 70), width=1)
    for g in range(-80, 81, 2):
        a = P(clon - 90, g); b = P(clon + 90, g); d.line([a, b], fill=(18, 40, 70), width=1)
    for ring in land():
        pts = [P(lo, la) for lo, la in ring]
        d.polygon(pts, fill=(34, 58, 88), outline=(90, 150, 210))
    return img

# ---------------- wall content ----------------
FORMAT = "roundup"
def chip(idx, total):
    if FORMAT == "countdown":
        return f"#{total - idx + 1}"
    if FORMAT == "deepdive":
        return f"PART {idx}/{total}"
    if FORMAT == "factcheck":
        return f"CLAIM {idx}/{total}"
    return f"NEWS {idx}/{total}"

def stamp(pan, verdict):
    """Fact-check verdict stamp: सच / अफवाह / अधूरा सच"""
    col = {"सच": (20, 150, 60), "अफवाह": (200, 20, 30)}.get(verdict, (220, 140, 0))
    st = Image.new("RGBA", (300, 110), (0, 0, 0, 0)); d = ImageDraw.Draw(st)
    d.rounded_rectangle([4, 4, 296, 106], 14, outline=col + (255,), width=7)
    d.text((150, 58), verdict, font=HB(56), fill=col + (255,), anchor="mm")
    st = st.rotate(-12, expand=True, resample=Image.BICUBIC)
    pan.alpha_composite(st, (pan.width - st.width - 10, pan.height - st.height - 30))

def wall_article(story, idx, total, shown):
    x0, y0, x1, y1 = WALL; w, h = x1 - x0, y1 - y0
    pan = Image.new("RGBA", (w, h), (232, 230, 224, 255)); d = ImageDraw.Draw(pan)
    d.rectangle([0, 0, w, 46], fill=(20, 22, 30))
    d.text((18, 23), "CT REPORT", font=OS(24), fill=YEL, anchor="lm")
    d.text((w - 18, 23), chip(idx, total), font=OS(22), fill=WHITE, anchor="rm")
    y = 62
    for ln in wrap(story["name"], OS(46), w - 40)[:2]:
        d.text((20, y), ln, font=OS(46), fill=DRED); y += 56
    for ln in wrap(story["headline"], HB(30), w - 40)[:2]:
        d.text((20, y), ln, font=HB(30), fill=INK); y += 40
    d.line([20, y + 4, w - 20, y + 4], fill=(180, 176, 168), width=2); y += 16
    for pt in story.get("points", [])[:shown]:
        for j, ln in enumerate(wrap(pt, HM(25), w - 70)[:2]):
            if j == 0:
                d.rectangle([22, y + 12, 32, y + 22], fill=RED)
            d.text((44, y), ln, font=HM(25), fill=(40, 42, 50)); y += 32
        y += 6
    d.text((20, h - 16), "स्रोत: " + ", ".join(story.get("sources", [])), font=HM(18), fill=(110, 110, 120), anchor="lb")
    if story.get("verdict") and shown >= len(story.get("points", [])):
        stamp(pan, story["verdict"])
    return pan

def wall_map(story, idx, total, shown, t, dur):
    x0, y0, x1, y1 = WALL; w, h = x1 - x0, y1 - y0
    loc = story["location"]
    k = min(1, t / max(1, dur * 0.6)); k = k * k * (3 - 2 * k)
    span = 34 * (1 - k) + 12 * k
    mw = int(w * 0.56)
    m = map_view(mw, h, loc["lon"] * k + 80 * (1 - k), loc["lat"] * k + 22 * (1 - k), span).convert("RGBA")
    d = ImageDraw.Draw(m)
    kx = math.cos(math.radians(loc["lat"] * k + 22 * (1 - k)))
    px = (loc["lon"] - (loc["lon"] * k + 80 * (1 - k))) * (mw / span) * kx + mw / 2
    py = ((loc["lat"] * k + 22 * (1 - k)) - loc["lat"]) * (mw / span) + h / 2
    r = 10 + 14 * ((t * 1.2) % 1)
    d.ellipse([px - r, py - r, px + r, py + r], outline=(255, 60, 60, int(255 * (1 - (t * 1.2) % 1))), width=3)
    d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(255, 40, 40), outline=WHITE, width=2)
    lab = loc["name"]; f = HB(24)
    lw = tl(d, lab, f)
    bx = min(max(10, px + 14), mw - lw - 30)
    d.rectangle([bx, py - 44, bx + lw + 20, py - 12], fill=(200, 16, 30, 235))
    d.text((bx + 10, py - 28), lab, font=f, fill=WHITE, anchor="lm")
    pan = Image.new("RGBA", (w, h), (10, 14, 26, 255)); pd = ImageDraw.Draw(pan)
    pan.alpha_composite(m, (w - mw, 0))
    pd.rectangle([0, 0, w - mw, h], fill=(12, 16, 30, 245))
    pd.rectangle([0, 0, w - mw, 40], fill=RED)
    pd.text((14, 20), chip(idx, total), font=OS(22), fill=WHITE, anchor="lm")
    y = 52; cw = w - mw - 28
    for ln in wrap(story["name"], OS(36), cw)[:3]:
        pd.text((14, y), ln, font=OS(36), fill=YEL); y += 44
    y += 6
    for pt in story.get("points", [])[:shown]:
        for j, ln in enumerate(wrap(pt, HM(22), cw - 18)[:3]):
            if j == 0: pd.rectangle([14, y + 10, 22, y + 18], fill=RED)
            pd.text((30, y), ln, font=HM(22), fill=WHITE); y += 28
        y += 8
    pd.text((14, h - 12), "स्रोत: " + ", ".join(story.get("sources", [])[:3]), font=HM(16), fill=(160, 170, 190), anchor="lb")
    return pan

def wall_list(sc, title):
    x0, y0, x1, y1 = WALL; w, h = x1 - x0, y1 - y0
    pan = Image.new("RGBA", (w, h), (10, 14, 28, 255)); d = ImageDraw.Draw(pan)
    d.rectangle([0, 0, w, 56], fill=RED)
    d.text((20, 28), title, font=HB(34), fill=WHITE, anchor="lm")
    y = 74
    for i, s in enumerate(sc["stories"][:6]):
        d.rectangle([20, y, 62, y + 42], fill=YEL)
        d.text((41, y + 21), str(i + 1), font=OS(28), fill=INK, anchor="mm")
        d.text((78, y + 21), s["name"], font=OS(30), fill=WHITE, anchor="lm")
        y += 54
    return pan

# ---------------- overlays ----------------
def chrome(date_label):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    # logo bug
    d.rectangle([22, 20, 74, 64], fill=RED)
    d.text((48, 42), "CT", font=OS(30), fill=WHITE, anchor="mm")
    d.rectangle([74, 20, 74 + tl(d, CH_NAME, OS(24)) + 24, 64], fill=(10, 12, 20, 220))
    d.text((86, 42), CH_NAME, font=OS(24), fill=WHITE, anchor="lm")
    d.rectangle([W - 260, 22, W - 190, 50], fill=RED)
    d.text((W - 225, 36), "LIVE", font=OS(20), fill=WHITE, anchor="mm")
    d.text((W - 22, 36), date_label, font=HM(20), fill=WHITE, anchor="rm")
    # ticker bar
    d.rectangle([0, H - 38, W, H], fill=(10, 12, 20, 245))
    return lay

def lower_third(tag, headline):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    y0, y1 = 594, 676
    f = OS(26); tw = tl(d, tag, f) + 36
    d.rectangle([0, y0, W, y1], fill=(245, 245, 245, 250))
    d.polygon([(0, y0), (tw + 30, y0), (tw, y1), (0, y1)], fill=RED)
    d.text((18, (y0 + y1) // 2), tag, font=f, fill=WHITE, anchor="lm")
    hf = HB(34)
    ln = wrap(headline, hf, W - tw - 70)
    if len(ln) > 1:
        hf = HB(28); ln = wrap(headline, hf, W - tw - 70)[:2]
    for i, l in enumerate(ln):
        yy = (y0 + y1) // 2 + (i - (len(ln) - 1) / 2) * 32
        d.text((tw + 40, yy), l, font=hf, fill=INK, anchor="lm")
    d.rectangle([0, y1, W, y1 + 4], fill=YEL)
    return lay

def caption(text):
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    f = HS(27)
    lines = wrap(text, f, WALL[2] - WALL[0] - 20)[-2:]
    y = 588 - 36 * len(lines) - 4
    for i, l in enumerate(lines):
        w2 = tl(d, l, f); x = (WALL[0] + WALL[2]) / 2 - w2 / 2
        d.rectangle([x - 10, y + i * 36 - 1, x + w2 + 10, y + i * 36 + 35], fill=(0, 0, 0, 175))
        d.text((x, y + i * 36 + 2), l, font=f, fill=WHITE)
    return lay

def grain_frames(n=4):
    out = []
    for i in range(n):
        g = np.random.RandomState(i).normal(0, 9, (H // 2, W // 2)).astype(np.int16)
        im = Image.fromarray((g + 128).clip(0, 255).astype(np.uint8)).resize((W, H))
        out.append(im)
    return out

# ---------------- audio ----------------
_k = None
def tts(text):
    global _k
    if _k is None:
        from kokoro_onnx import Kokoro
        _k = Kokoro(os.path.join(ASSETS, "kokoro.onnx"), os.path.join(ASSETS, "voices.bin"))
    s, sr = _k.create(text, voice=VOICE, speed=SPEED, lang="hi")
    return s.astype(np.float32)

def bed(sec):
    n = int(sec * SR); t = np.arange(n) / SR
    out = np.zeros(n, np.float32); beat = 0.6
    prog = [55.0, 55.0, 49.0, 41.2]
    for i in range(int(sec / beat) + 1):
        st = int(i * beat * SR); L = int(beat * SR); tt = np.arange(L) / SR
        f = prog[(i // 4) % 4]
        tone = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 6)
        e = min(n, st + L); out[st:e] += tone[: e - st] * 0.8
    out += (sum(np.sin(2 * np.pi * f * 2 * t) for f in (110, 138.6, 164.8)) * 0.05).astype(np.float32)
    return out / (np.abs(out).max() + 1e-6)

def envelope(audios, bounds, dur):
    n = int(dur * 50) + 1; env = np.zeros(n, np.float32); hop = SR // 50
    for a, (st, _) in zip(audios, bounds):
        for i in range(0, len(a), hop):
            j = int(st * 50) + i // hop
            if j < n: env[j] = float(np.sqrt(np.mean(a[i:i + hop] ** 2)))
    return np.clip(env / (env.max() + 1e-6) * 1.3, 0, 1)

# ---------------- render ----------------
class Ctx: pass

def render_segment(i, seg, sents, env, work, C, t0):
    bounds, t = [], 0.2
    for s in sents:
        bounds.append((t, t + s["dur"])); t += s["dur"] + GAP
    dur = t + 0.15; nf = int(round(dur * FPS))
    out = os.path.join(work, f"seg{i:03d}.mp4"); tmp = out[:-4] + ".tmp.mp4"
    PREV = os.environ.get("PREVIEW")
    if not PREV and os.environ.get("RESUME") and os.path.exists(out) and os.path.getsize(out) > 1000:
        return out, bounds, dur
    caps = [caption(s["text"]) for s in sents]
    lt = lower_third(seg["tag"], seg["headline"])
    static_walls = {}
    if not PREV:
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    tf = HS(22); tick = C.ticker; tw = int(tl(ImageDraw.Draw(Image.new("RGB", (4, 4))), tick, tf))
    x0, y0, x1, y1 = WALL
    for fi in range(nf):
        if PREV and fi != int(nf * 0.8):
            continue
        t = fi / FPS; gt = t0 + t
        k = 0
        for j, (a, b) in enumerate(bounds):
            if t >= a - 0.1: k = j
        frame = C.bg.copy()
        # wall content with slow push-in
        if seg["kind"] == "map":
            pan = seg["wall"](k, t, dur)
        else:
            if k not in static_walls: static_walls[k] = seg["wall"](k)
            pan = static_walls[k]
        z = 1.0 + 0.03 * (t / dur)
        pw, ph = pan.size
        cw, chh = pw / z, ph / z
        pan2 = pan.resize((pw, ph), Image.BILINEAR, box=((pw - cw) / 2, (ph - chh) / 2, (pw + cw) / 2, (ph + chh) / 2)) if seg["kind"] != "map" else pan
        frame.alpha_composite(pan2, (x0, y0))
        # glass sheen sweep
        sx = int(((gt * 0.15) % 1.6) * (x1 - x0 + 600)) - 300
        frame.alpha_composite(C.sheen, (x0 + sx, y0)) if 0 < sx + 300 < (x1 - x0 + 300) else None
        frame.alpha_composite(C.wallmask)
        # anchor (breathing + talking nod)
        lv = env[min(len(env) - 1, int(t * 50))]
        dy = int(2 * math.sin(gt * 1.4) + 3 * lv)
        frame.alpha_composite(C.anchor, ((W - C.anchor.width + 30) if MIRROR else -30, 108 + dy))
        frame.alpha_composite(C.desk_front)
        frame.alpha_composite(C.mic, (790 if MIRROR else 420, 452))
        frame.alpha_composite(caps[k])
        frame.alpha_composite(lt)
        frame.alpha_composite(C.chrome)
        d = ImageDraw.Draw(frame)
        tx = 150 - int(gt * 80) % tw
        while tx < W:
            d.text((tx, H - 19), tick, font=tf, fill=WHITE, anchor="lm"); tx += tw
        d.rectangle([0, H - 38, 140, H], fill=YEL)
        d.text((70, H - 19), "TOP NEWS", font=OS(20), fill=INK, anchor="mm")
        rgb = frame.convert("RGB")
        rgb = Image.blend(rgb, ImageChops.overlay(rgb, C.grain[fi % 4].convert("RGB")), 0.35)
        if t < 0.25:
            rgb = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), rgb, t / 0.25)
        if PREV:
            rgb.save(os.path.join(work, f"prev{i:03d}.jpg"), quality=90); continue
        p.stdin.write(rgb.tobytes())
    if PREV:
        return out, bounds, dur
    p.stdin.close()
    if p.wait() != 0: raise RuntimeError("ffmpeg failed")
    os.replace(tmp, out)
    return out, bounds, dur

def build(path, outdir):
    sc = json.load(open(path, encoding="utf-8"))
    global FORMAT
    FORMAT = sc.get("format", "roundup")
    apply_theme(sc.get("theme", "red"), bool(sc.get("mirror", False)))
    work = os.path.join(outdir, "work2"); os.makedirs(work, exist_ok=True)
    C = Ctx()
    C.bg = studio_bg()
    C.anchor = anchor_sprite()
    # desk front piece to overlap anchor's lower body
    C.desk_front = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(C.desk_front)
    pts = desk_pts(); a, b = DESKX()
    dd.polygon(pts, fill=(22, 28, 44, 255))
    dd.line(pts[:5], fill=LIGHT + (220,), width=3)
    dd.rectangle([a, 552, b, 556], fill=RED + (220,))
    dd.text(((a + b) // 2, 572), CH_NAME, font=OS(22), fill=(150, 170, 210), anchor="mm")
    C.mic = mic_sprite()
    C.chrome = chrome(sc["date_label"])
    C.ticker = "   |   ".join(s["name"] + ": " + s["headline"] for s in sc["stories"]) + "   |   "
    C.grain = grain_frames()
    sh = Image.new("RGBA", (300, WALL[3] - WALL[1]), (0, 0, 0, 0))
    for xx in range(300):
        a = int(28 * math.exp(-((xx - 150) / 60) ** 2))
        ImageDraw.Draw(sh).line([xx, 0, xx, sh.height], fill=(255, 255, 255, a))
    C.sheen = sh
    # mask to clip sheen outside wall: draw bezel over area right of wall
    C.wallmask = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    total = len(sc["stories"])
    segs = [{"kind": "list", "lines": sc["intro"], "tag": "BREAKING NEWS", "headline": sc.get("intro_headline", "आज की बड़ी खबरें"),
             "wall": lambda k: wall_list(sc, sc.get("list_title", "आज की बड़ी खबरें"))}]
    for i, st in enumerate(sc["stories"]):
        npts, nl = len(st.get("points", [])), len(st["lines"])
        shown = (lambda npts, nl: (lambda k: min(npts, 1 + k * npts // max(1, nl))))(npts, nl)
        if st.get("location"):
            segs.append({"kind": "map", "lines": st["lines"], "tag": st["name"], "headline": st["headline"],
                         "wall": (lambda st, i, shown: (lambda k, t, dur: wall_map(st, i + 1, total, shown(k), t, dur)))(st, i, shown)})
        else:
            segs.append({"kind": "article", "lines": st["lines"], "tag": st["name"], "headline": st["headline"],
                         "wall": (lambda st, i, shown: (lambda k: wall_article(st, i + 1, total, shown(k))))(st, i, shown)})
    segs.append({"kind": "list", "lines": sc["outro"], "tag": "CONTROVERSY TOPICS", "headline": "रोज़ की खबरों के लिए सब्सक्राइब करें",
                 "wall": lambda k: wall_list(sc, "आज की खबरें")})
    files, tracks, t0 = [], [], 0.0
    for i, seg in enumerate(segs):
        audios = [tts(l) for l in seg["lines"]]
        sents = [{"text": l, "dur": len(a) / SR} for l, a in zip(seg["lines"], audios)]
        bounds, t = [], 0.2
        for s in sents:
            bounds.append((t, t + s["dur"])); t += s["dur"] + GAP
        env = envelope(audios, bounds, t + 0.15)
        f, bounds, dur = render_segment(i, seg, sents, env, work, C, t0)
        nfr = int(round(dur * FPS)); tr = np.zeros(nfr * SR // FPS, np.float32)
        for a, (st, _) in zip(audios, bounds):
            s0 = int(st * SR); tr[s0:s0 + len(a)] += a[: max(0, len(tr) - s0)]
        tracks.append(tr); files.append(f); t0 += nfr / FPS
        print(f"segment {i+1}/{len(segs)} {dur:.1f}s", flush=True)
    make_thumb(sc, C, os.path.join(outdir, "thumb2.jpg"))
    if os.environ.get("PREVIEW"):
        print("preview done"); return
    voice = np.concatenate(tracks)
    mix = voice / (np.abs(voice).max() + 1e-6) * 0.95 + bed(len(voice) / SR + 1)[: len(voice)] * 0.05
    import soundfile as sf
    wav = os.path.join(work, "audio.wav"); sf.write(wav, np.clip(mix, -1, 1), SR)
    lst = os.path.join(work, "list.txt")
    open(lst, "w").write("".join(f"file '{os.path.abspath(f)}'\n" for f in files))
    joined = os.path.join(work, "joined.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined], check=True)
    tmp = os.path.join(outdir, "video2.tmp.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", joined, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, os.path.join(outdir, "video2.mp4"))
    chap, acc = [], 0.0
    names = ["Intro"] + [s["name"] for s in sc["stories"]] + ["Outro"]
    for nm, tr in zip(names, tracks):
        chap.append(f"{int(acc//60)}:{int(acc%60):02d} {nm}"); acc += len(tr) / SR
    srcs = "\n".join(f"{s['name']} -\n" + "\n".join("• " + u for u in s.get("links", [])) for s in sc["stories"])
    desc = (sc["description"] + "\n\n⏱️ Chapters\n" + "\n".join(chap) + "\n\n📰 Sources -\n" + srcs +
            "\n\nDISCLAIMER - यह वीडियो सिर्फ़ जानकारी के लिए है। सभी खबरें ऊपर दिए गए न्यूज़ सोर्स पर आधारित हैं; जिन मामलों की जाँच चल रही है उनमें आरोप साबित नहीं हुए हैं। "
            "इस वीडियो में किसी और की कॉपीराइटेड फुटेज या फोटो इस्तेमाल नहीं की गई है। Voice: AI generated. Map data: Natural Earth (public domain).\n\n" + " ".join(sc["hashtags"]))
    json.dump({"title": sc["title"], "description": desc, "tags": sc["tags"], "made_for_kids": False, "altered_content": True,
               "duration": round(len(voice) / SR, 1)}, open(os.path.join(outdir, "meta2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("DONE", f"{len(voice)/SR:.1f}s")

def make_thumb(sc, C, path):
    img = C.bg.copy()
    a = C.anchor.resize((int(C.anchor.width * 1.25), int(C.anchor.height * 1.25)), Image.LANCZOS)
    img.alpha_composite(a, (W - a.width + 90, H - a.height + 10))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 110], fill=RED)
    d.text((30, 55), sc["thumb"]["top"], font=OS(78), fill=WHITE, anchor="lm", stroke_width=2, stroke_fill=DRED)
    y = 150
    for i, ln in enumerate(sc["thumb"]["lines"]):
        f = OS(96 if i == 0 else 74)
        d.text((34, y), ln, font=f, fill=YEL if i % 2 == 0 else WHITE, stroke_width=6, stroke_fill=(0, 0, 0))
        y += 128 if i == 0 else 98
    d.rectangle([0, H - 70, W, H], fill=(10, 12, 20))
    d.text((30, H - 35), "BREAKING  |  " + CH_NAME, font=OS(34), fill=YEL, anchor="lm")
    img.convert("RGB").save(path, quality=92)

if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
