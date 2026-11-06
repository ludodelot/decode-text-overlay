#!/usr/bin/env python3
"""decode-text-overlay: render a "decoding" monospace text overlay.

Text grows from the center outward as random glyphs, then resolves letter by letter (random order) into the target
phrase, holds, then scrambles into the next phrase (loop optional).

Examples
  # transparent overlay (ProRes 4444 with alpha) for any video editor
  decode_overlay.py -t "MIDNIGHT SESSIONS" -t "OUT NOW" -o overlay.mov

  # burn it onto a photo or a video
  decode_overlay.py -t "SUMMER EDIT" --bg photo.jpg -o story.mp4
  decode_overlay.py -t "OUT NOW" --bg clip.mp4 --loop -o clip_text.mp4

Use "\\n" inside a text for a two-line caption: -t "STUDIO ONE\\nLIVE SET"
The animation is deterministic (same --seed = same frames) and mirrors
web/decode-text.js.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    sys.exit("Pillow missing. Run: python3 -m venv .venv && .venv/bin/pip install pillow")

CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789*?!/#+<>=-_$%&¡¿"  # custom pool for --charset
LETTERS, DIGITS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "0123456789"


def glyph_pool(ch, o):
    """Scramble glyphs matching the target character: letters scramble as letters, digits as digits.
    Punctuation is not scrambled (returns ''), which keeps the line calm. A custom o['charset'] overrides this."""
    if o.get("charset"):
        return o["charset"]
    if ch.isdigit():
        return DIGITS
    if ch.isalpha():
        return LETTERS
    return ""
SKILL_DIR = Path(__file__).resolve().parents[1]
FONT_NAME = "SpaceMono-Regular.ttf"
FONT_CANDIDATES = [
    SKILL_DIR / "fonts" / FONT_NAME,                                   # skill folder is self-contained
    Path(sys.prefix) / "share" / "decode-text-overlay" / "fonts" / FONT_NAME,  # pip install
    Path("/System/Library/Fonts/Menlo.ttc"), Path("/Library/Fonts/Courier New.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    Path("C:/Windows/Fonts/consola.ttf"),
]
BUNDLED_FONTS = {  # --font NAME works without a path
    "space-mono": "SpaceMono-Regular.ttf",
    "dm-mono": "DMMono-Regular.ttf",
    "dm-mono-light": "DMMono-Light.ttf",
    "dm-sans": "DMSans-Variable.ttf",  # proportional: rendered with the slot layout; use --weight 100-1000
}


def resolve_font(value):
    """Bundled font alias, or a path to any monospace .ttf/.otf."""
    key = str(value).lower()
    if key in BUNDLED_FONTS:
        for base in (SKILL_DIR / "fonts", Path(sys.prefix) / "share" / "decode-text-overlay" / "fonts"):
            if (base / BUNDLED_FONTS[key]).exists():
                return base / BUNDLED_FONTS[key]
    return Path(value)


DEFAULT_FONT = next((f for f in FONT_CANDIDATES if f.exists()), FONT_CANDIDATES[0])


# ---------- animation core (kept identical to web/decode-text.js) ----------
def hash32(a, b, c):
    h = (a * 374761393 + b * 668265263 + c * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return (h ^ (h >> 16)) & 0xFFFFFFFF


def rnd(a, b, c):
    return hash32(a, b, c) / 4294967296.0


def pad_center(s, n):
    total = n - len(s)
    left = total // 2
    return " " * left + s + " " * (total - left)


def wrap_balanced(s, maxlen):
    """Split a long phrase into two balanced lines at the space nearest the middle."""
    if maxlen <= 0 or "\n" in s or len(s) <= maxlen:
        return s
    spaces = [i for i, c in enumerate(s) if c == " "]
    if not spaces:
        return s
    mid = len(s) / 2
    k = min(spaces, key=lambda i: (abs(i - mid), i))
    return s[:k] + "\n" + s[k + 1:]


def frame_text(prev, target, t, o):
    """Text shown t seconds after a phrase starts. The phrase grows from the
    center outward as random glyphs, then each glyph resolves in random order.
    (prev is unused: phrases are hard-cut, like the reference.)"""
    out = []
    grow = o["decode"] * 0.40
    for li, line in enumerate(target.split("\n")):
        n = len(line)
        c = (n - 1) / 2
        chars = []
        for i, ch in enumerate(line):
            if ch == " ":
                chars.append(" ")
                continue
            j = rnd(o["seed"], li * 97 + i, 1)
            d = abs(i - c) / c if c > 0 else 0.0
            g = grow * d * (0.85 + 0.30 * j)
            order = o.get("order", "random")
            if order == "ltr":
                u = i / (n - 1) if n > 1 else 0.0
            elif order == "center":
                u = d
            else:
                u = rnd(o["seed"], li * 97 + i, 2)
            r = o["decode"] * (0.35 + 0.65 * u)
            r = min(o["decode"], max(r, g + o["decode"] * 0.12))
            if t >= r:
                chars.append(ch)
            elif t < g:
                chars.append(" ")
            else:
                cs = glyph_pool(ch, o)
                tick = int(t / o["tick"])
                chars.append(cs[int(rnd(o["seed"] + tick, li * 97 + i, 3) * len(cs))] if cs else ch)
        out.append("".join(chars))
    return "\n".join(out)


def timeline(texts, o):
    """List of (start, prev, target); returns segments and total duration."""
    segs, t, prev = [], 0.0, ""
    for tx in texts:
        segs.append((t, prev, tx))
        t += o["decode"] + o["hold"] + o.get("exit", 0.0)
        prev = tx
    return segs, t


def segment_at(segs, total, t, o, loop):
    """The (start, prev, target) segment on screen at time t, or None when the layer is empty."""
    t -= o.get("delay", 0.0)
    if t < 0:
        return None
    if loop:
        t %= total
    elif o.get("exit", 0.0) > 0 and t >= total:
        return None
    seg = segs[0]
    for s_ in segs:
        if t >= s_[0]:
            seg = s_
    return seg


def text_at(segs, total, t, o, loop):
    ex_all = o.get("exit", 0.0)
    t -= o.get("delay", 0.0)
    if t < 0:
        return ""
    if loop:
        t = t % total
    elif ex_all > 0 and t >= total:
        return ""
    seg = segs[0]
    for s in segs:
        if t >= s[0]:
            seg = s
    local = t - seg[0]
    live = o["decode"] + o["hold"]
    ex = o.get("exit", 0.0)
    if local < live or ex <= 0:
        return frame_text(seg[1], seg[2], local, o)
    u = (local - live) / ex
    if u >= 1:
        return ""  # after the exit the layer is empty
    # exit = the decode played backwards: text dissolves into glyphs and shrinks to the center
    return frame_text(seg[1], seg[2], o["decode"] * (1 - u), o)


PRESETS = {
    "story": {},
    "minimal": dict(size=0.028, tracking=0.30, opacity=0.85, shadow=0.20, decode=1.1, hold=1.6, exit=0.5),
    "cinematic": dict(size=0.030, tracking=0.45, opacity=0.90, shadow=0.30, decode=1.6, hold=2.2, exit=0.8, order="center"),
    "poster": dict(size=0.075, tracking=0.12, shadow=0.50, decode=1.4, hold=1.8),
    "terminal": dict(size=0.040, tracking=0.02, color="#7CFFB2", shadow=0.0, order="ltr", decode=0.8, hold=1.4,
                     charset="01#$%&*+=<>/\\|"),
    "lowerthird": dict(size=0.030, tracking=0.20, y=0.86, order="ltr", exit=0.5, decode=0.8, hold=2.5),
}


def pick_auto_color(bg, is_video, W, H, args):
    """Sample the background under the text box; dark text on bright areas, white otherwise."""
    from PIL import ImageStat
    import tempfile
    path = str(bg)
    tmp = None
    if is_video:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "0.5", "-i", path, "-frames:v", "1", tmp], check=False)
        path = tmp
    try:
        im = Image.open(path).convert("L")
    except Exception:
        return "#FFFFFF"
    iw, ih = im.size
    box = (int(iw * (args.x - 0.35)), int(ih * (args.y - 0.07)), int(iw * (args.x + 0.35)), int(ih * (args.y + 0.07)))
    box = (max(0, box[0]), max(0, box[1]), min(iw, box[2]), min(ih, box[3]))
    lum = ImageStat.Stat(im.crop(box)).mean[0]
    if tmp:
        os.unlink(tmp)
    return "#111111" if lum > 150 else "#FFFFFF"


def make_scrim(specs, W, H, color=(0, 0, 0)):
    """Dark gradient layer(s) between the photo and the text.
    spec = kind@opacity:extent[:center]   kind: top | bottom | full | band
      top/bottom: gradient from the edge, `extent` = fraction of the height it covers
      band: soft horizontal band, `extent` = band height, `center` = its y (default 0.5)
      full: flat veil over everything. Examples: top@0.7:0.4  bottom@0.75:0.45  band@0.6:0.2:0.5  full@0.25"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for spec in specs:
        kind, _, rest = spec.partition("@")
        nums = [float(v) for v in rest.split(":")] if rest else []
        op = nums[0] if nums else 0.5
        ext = nums[1] if len(nums) > 1 else 0.4
        cen = nums[2] if len(nums) > 2 else 0.5
        grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for y in range(H):
            v = y / H
            if kind == "top":
                f = max(0.0, 1 - v / ext)
            elif kind == "bottom":
                f = max(0.0, 1 - (1 - v) / ext)
            elif kind == "band":
                f = max(0.0, 1 - abs(v - cen) / (ext / 2))
            elif kind == "full":
                f = 1.0
            else:
                sys.exit(f"unknown scrim kind: {kind}")
            f = f * f * (3 - 2 * f) if kind != "full" else f  # smoothstep
            if f > 0:
                gd.line([(0, y), (W, y)], fill=tuple(color) + (int(255 * op * f),))
        layer = Image.alpha_composite(layer, grad)
    return layer


def parse_block(spec, base, parser_defaults):
    """'TEXT1|TEXT2;y=0.2;size=0.07;delay=0.5;preset=cinematic' -> namespace based on `base`."""
    import copy
    parts = spec.split(";")
    ns = copy.copy(base)
    ns.text = parts[0].split("|")
    kv = dict(x.split("=", 1) for x in parts[1:] if "=" in x)
    if "preset" in kv:
        for k, v in PRESETS[kv.pop("preset")].items():
            setattr(ns, k, v)
    for k, v in kv.items():
        k = k.strip().replace("-", "_")
        if not hasattr(ns, k):
            sys.exit(f"unknown block option: {k}")
        cur = getattr(ns, k)
        setattr(ns, k, type(cur)(v) if isinstance(cur, (int, float)) and not isinstance(cur, bool) else v)
    return ns


# ---------- rendering ----------
def load_font(args, size):
    font = ImageFont.truetype(str(resolve_font(args.font)), size)
    try:
        axes = font.get_variation_axes()
    except Exception:
        axes = []
    if axes:
        vals = []
        for ax in axes:
            name = ax["name"].decode() if isinstance(ax["name"], bytes) else ax["name"]
            v = ax["default"]
            if "weight" in name.lower() and args.weight:
                v = args.weight
            elif "optical" in name.lower():
                v = min(ax["maximum"], max(ax["minimum"], size / 2))
            vals.append(max(ax["minimum"], min(ax["maximum"], v)))
        font.set_variation_by_axes(vals)
    return font


def make_renderer(args, W, H):
    size = max(8, int(W * args.size))
    font = load_font(args, size)
    track = args.tracking * size
    mono = abs(font.getlength("i") - font.getlength("M")) < 0.5
    slot = args.layout == "slot" or (args.layout == "auto" and not mono)
    line_h = int(size * args.line_height)
    cx = W * args.x
    cy = H * args.y
    color = tuple(int(args.color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

    def advances(target_line, shown_line):
        """Per-character slot width. Monospace: one fixed cell. Slot layout (proportional fonts):
        each slot is as wide as the final character, so the line never jitters while glyphs scramble."""
        if not slot:
            return [font.getlength("M") + track] * len(shown_line)
        return [font.getlength(ch) + track for ch in target_line.ljust(len(shown_line))[:len(shown_line)]]

    def render(text, target=None):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lines = text.split("\n")
        tlines = (target or text).split("\n")
        block_h = line_h * len(lines)
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0)) if args.shadow > 0 else None
        d = ImageDraw.Draw(img)
        sd = ImageDraw.Draw(shadow) if shadow else None
        for li, ln in enumerate(lines):
            adv = advances(tlines[li] if li < len(tlines) else ln, ln)
            w = sum(adv) - track
            x = cx - w / 2
            y = cy - block_h / 2 + li * line_h
            for ci, ch in enumerate(ln):
                if ch != " ":
                    gx = x + (adv[ci] - track - font.getlength(ch)) / 2 if slot else x
                    if sd:
                        sd.text((gx, y), ch, font=font, fill=(0, 0, 0, int(255 * args.shadow)))
                    resolved = ci < len(tlines[li] if li < len(tlines) else ln) and (tlines[li] if li < len(tlines) else ln)[ci] == ch
                    op = args.opacity * (1.0 if resolved else args.scramble_opacity)
                    d.text((gx, y), ch, font=font, fill=color + (int(255 * op),))
                x += adv[ci]
        if shadow:
            shadow = shadow.filter(ImageFilter.GaussianBlur(size * 0.12))
            img = Image.alpha_composite(shadow, img)
        return img

    return render


def write_svg(out, a, W, H, nframes, frames_text):
    """Animated SVG (SMIL, no JS): one <text> per distinct frame, toggled with discrete keyTimes.
    Font is a monospace stack (SVGs in <img> cannot load web fonts)."""
    from xml.sax.saxutils import escape
    size = W * a.size
    line_h = size * a.line_height
    dur = nframes / a.fps
    uniq = {}
    for i, t in enumerate(frames_text):
        uniq.setdefault(t, []).append(i)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    parts.append(f'<style>text{{font-family:"Space Mono","SF Mono",ui-monospace,Menlo,Consolas,monospace;font-size:{size:.1f}px;'
                 f'letter-spacing:{a.tracking:.2f}em;fill:{a.color};fill-opacity:{a.opacity};text-anchor:middle;white-space:pre;visibility:hidden}}</style>')
    if a.svg_bg:
        parts.append(f'<rect width="{W}" height="{H}" fill="{a.svg_bg}"/>')
    for txt, idxs in uniq.items():
        lines = txt.split("\n")
        y0 = H * a.y - line_h * (len(lines) - 1) / 2
        ts = "".join(
            f'<tspan x="{W * a.x + a.tracking * size / 2:.1f}" y="{y0 + li * line_h:.1f}" xml:space="preserve">{escape(l)}</tspan>'
            for li, l in enumerate(lines))
        # collapse to change points only
        kt, vv, last = [], [], None
        sidx = set(idxs)
        for i in range(nframes):
            v = "visible" if i in sidx else "hidden"
            if v != last:
                kt.append(f"{i / nframes:.5f}")
                vv.append(v)
                last = v
        if kt[0] != "0.00000":
            kt.insert(0, "0")
            vv.insert(0, "hidden")
        parts.append(f'<text>{ts}<animate attributeName="visibility" calcMode="discrete" dur="{dur:.3f}s" '
                     f'repeatCount="indefinite" keyTimes="{";".join(kt)}" values="{";".join(vv)}"/></text>')
    parts.append("</svg>")
    Path(out).write_text("".join(parts), encoding="utf-8")
    print(f"animated SVG, {len(uniq)} distinct frames, {dur:.2f}s -> {out}")


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True)
    j = json.loads(r.stdout)
    st = j["streams"][0]
    dur = float(j.get("format", {}).get("duration") or 0)
    return int(st["width"]), int(st["height"]), dur


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-t", "--text", action="append", help="phrase (repeat for a sequence; \\n = new line)")
    p.add_argument("--block", action="append", help="extra text block: 'A|B;y=0.2;size=0.07;delay=0.5;preset=cinematic' (repeat; "
                   "options are any flag below; lets one run stack several texts with their own position, style and timing)")
    p.add_argument("--scrim", action="append", help="dark gradient behind the text: kind@opacity:extent[:center], kind = top|bottom|full|band (repeat)")
    p.add_argument("--delay", type=float, default=0.0, help="seconds before this text starts")
    p.add_argument("-o", "--out", required=True,
                   help=".mp4 (opaque or composited) | .mov (ProRes 4444 alpha) | .webm (VP9 alpha) | .gif | folder/ (PNG sequence)")
    p.add_argument("--bg", help="photo or video to composite onto (output becomes opaque mp4)")
    p.add_argument("--size-px", help="WxH when there is no --bg (default 1080x1920)", default="1080x1920")
    p.add_argument("--width", type=int, help="downscale output to this width (handy for GIFs)")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--decode", type=float, default=0.9, help="seconds to resolve each phrase")
    p.add_argument("--hold", type=float, default=1.3, help="seconds a resolved phrase stays")
    p.add_argument("--tick", type=float, default=1 / 24, help="seconds between glyph changes while scrambling")
    p.add_argument("--duration", type=float, help="total seconds (default: timeline, or bg video length)")
    p.add_argument("--exit", type=float, default=0.0, help="seconds for the text to dissolve back to glyphs after the hold (0 = hard cut)")
    p.add_argument("--order", choices=["random", "center", "ltr"], default="random", help="order in which glyphs resolve")
    p.add_argument("--loop", action="store_true", help="repeat the sequence until duration")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--wrap", type=int, default=12, help="phrases longer than this split into 2 balanced lines (0 = never)")
    p.add_argument("--font", default=str(DEFAULT_FONT), help="bundled name (space-mono, dm-mono, dm-mono-light) or path to a monospace .ttf")
    p.add_argument("--size", type=float, default=0.036, help="font size as fraction of width")
    p.add_argument("--tracking", type=float, default=0.18, help="extra letter spacing (em)")
    p.add_argument("--line-height", type=float, default=1.15)
    p.add_argument("--weight", type=int, default=0, help="weight 100-1000 for variable fonts such as dm-sans")
    p.add_argument("--layout", choices=["auto", "mono", "slot"], default="auto",
                   help="slot = per-character slots sized to the final letters (proportional fonts); auto picks it for non-monospace fonts")
    p.add_argument("--scrim-color", default="#000000", help="color of the --scrim gradients, e.g. '#070A10'")
    p.add_argument("--color", default="#FFFFFF", help="#RRGGBB, or 'auto' to pick white/dark from the --bg under the text")
    p.add_argument("--opacity", type=float, default=0.95)
    p.add_argument("--shadow", type=float, default=0.35, help="soft shadow strength 0-1 (helps legibility)")
    p.add_argument("--x", type=float, default=0.5, help="center x, 0-1")
    p.add_argument("--y", type=float, default=0.5, help="center y, 0-1")
    p.add_argument("--charset", default=None, help="custom scramble glyphs for every character (default: letters scramble as letters, digits as digits)")
    p.add_argument("--scramble-opacity", type=float, default=0.55, help="opacity of glyphs that have not resolved yet, relative to --opacity")
    p.add_argument("--svg-bg", help="solid background color for .svg output, e.g. '#1a1216' (default: transparent)")
    p.add_argument("--preset", choices=sorted(PRESETS), default="story", help="starting point for style options; explicit flags override it")
    pre, _ = p.parse_known_args()
    p.set_defaults(**PRESETS[pre.preset])
    a = p.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found")
    for fv in [a.font] + [getattr(b, "font", a.font) for b in (parse_block(x, a, None) for x in (a.block or []))]:
        if not resolve_font(fv).exists():
            sys.exit(f"font not found: {fv} (bundled: {', '.join(BUNDLED_FONTS)})")
    if not a.text and not a.block:
        sys.exit("give at least one -t/--text or --block")
    blocks = [parse_block(b, a, None) for b in a.block] if a.block else []
    if a.text:
        blocks.insert(0, a)
    layers = []
    for b in blocks:
        texts = [wrap_balanced(t.replace("\\n", "\n"), b.wrap) for t in b.text]
        o = dict(decode=b.decode, hold=b.hold, exit=b.exit, order=b.order, tick=b.tick, seed=b.seed,
                 charset=b.charset, delay=b.delay)
        segs, total = timeline(texts, o)
        layers.append(dict(args=b, o=o, segs=segs, total=total + b.delay, texts=texts))
    total = max(l["total"] for l in layers)

    bg_is_video = False
    if a.bg:
        W, H, bdur = probe(a.bg)
        bg_is_video = Path(a.bg).suffix.lower() in {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
        dur = a.duration or (bdur if bg_is_video else total)
    else:
        W, H = (int(v) for v in a.size_px.lower().split("x"))
        dur = a.duration or total
    if a.width and a.width < W:
        H = round(H * a.width / W)
        W = a.width
    W -= W % 2
    H -= H % 2
    for l in layers:
        b = l["args"]
        if b.color.lower() == "auto":
            b.color = pick_auto_color(a.bg, bg_is_video, W, H, b) if a.bg else "#FFFFFF"
            if b.color == "#111111":
                b.shadow = 0.0
            print(f"auto color: {b.color}", file=sys.stderr)
        l["render"] = make_renderer(b, W, H)
    scrim = make_scrim(a.scrim, W, H, tuple(int(a.scrim_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))) if a.scrim else None
    nframes = max(1, int(round(dur * a.fps)))
    loop = a.loop

    out = Path(a.out)
    ext = out.suffix.lower()
    is_seq = ext == ""
    cache, texts_cache = {}, {}

    def layer_texts(f):
        return tuple(text_at(l["segs"], l["total"] - l["args"].delay, f / a.fps, l["o"], l["args"].loop) for l in layers)

    def frames():
        for f in range(nframes):
            key = layer_texts(f)
            if key not in cache:
                if len(cache) > 300:
                    cache.clear()
                img = scrim.copy() if scrim else Image.new("RGBA", (W, H), (0, 0, 0, 0))
                for i, (l, txt) in enumerate(zip(layers, key)):
                    if txt:
                        tk = (i, txt)
                        if tk not in texts_cache:
                            if len(texts_cache) > 600:
                                texts_cache.clear()
                            seg = segment_at(l["segs"], l["total"] - l["args"].delay, f / a.fps, l["o"], l["args"].loop)
                            texts_cache[tk] = l["render"](txt, seg[2] if seg else txt)
                        img = Image.alpha_composite(img, texts_cache[tk])
                cache[key] = img
            yield f, cache[key]

    if is_seq:
        out.mkdir(parents=True, exist_ok=True)
        for f, im in frames():
            im.save(out / f"frame_{f:05d}.png")
        print(f"{nframes} PNG frames -> {out}/")
        return

    if ext == ".svg":
        if len(layers) > 1 or scrim:
            sys.exit(".svg output supports a single text block and no --scrim")
        l = layers[0]
        write_svg(out, a, W, H, nframes, frames_text=[text_at(l["segs"], l["total"] - a.delay, f / a.fps, l["o"], a.loop) for f in range(nframes)])
        return

    cmd = ["ffmpeg", "-v", "error", "-y"]
    if a.bg:
        if not bg_is_video:
            cmd += ["-loop", "1", "-framerate", str(a.fps), "-t", f"{dur:.3f}"]
        elif a.loop and dur > bdur:
            cmd += ["-stream_loop", "-1"]
        cmd += ["-i", a.bg]
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(a.fps), "-i", "-"]
    if a.bg:
        fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={a.fps},setsar=1[b];"
              f"[b][1:v]overlay=shortest=1,scale=in_range=full:out_range=limited,format=yuv420p[v]")
        cmd += ["-filter_complex", fc, "-map", "[v]"]
        if bg_is_video:
            cmd += ["-map", "0:a?", "-c:a", "copy"]
        if ext == ".gif":
            cmd[cmd.index("-filter_complex") + 1] = fc.replace("scale=in_range=full:out_range=limited,format=yuv420p[v]", "split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4[v]")
            cmd += ["-t", f"{dur:.3f}", "-loop", "0"]
        elif ext == ".mp4":
            cmd += ["-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "15", "-preset", "slow", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-movflags", "+faststart"]
        else:
            sys.exit("with --bg the output must be .mp4 or .gif")
    elif ext == ".mov":
        cmd += ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"]
    elif ext == ".webm":
        cmd += ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "0", "-crf", "24"]
    elif ext == ".gif":
        cmd += ["-vf", "split[a][b];[a]palettegen=reserve_transparent=1[p];[b][p]paletteuse=alpha_threshold=96", "-loop", "0"]
    elif ext == ".mp4":
        cmd += ["-vf", "format=yuv420p", "-c:v", "libx264", "-crf", "16", "-movflags", "+faststart"]
        print("note: .mp4 has no alpha, text will sit on black. Use .mov/.webm for transparency.", file=sys.stderr)
    else:
        sys.exit(f"unsupported output: {ext}")
    cmd.append(str(out))

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for _, im in frames():
            proc.stdin.write(im.tobytes())
    except BrokenPipeError:
        pass
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"{nframes} frames, {dur:.2f}s, {W}x{H} -> {out}")


if __name__ == "__main__":
    main()
