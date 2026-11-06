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

CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789*?!/#+<>=-_$%&¡¿"
SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_FONT = SKILL_DIR / "fonts" / "SpaceMono-Regular.ttf"  # bundled, so the skill folder is self-contained


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
            r = o["decode"] * (0.35 + 0.65 * rnd(o["seed"], li * 97 + i, 2))
            r = min(o["decode"], max(r, g + o["decode"] * 0.12))
            if t >= r:
                chars.append(ch)
            elif t < g:
                chars.append(" ")
            else:
                cs = o["charset"]
                tick = int(t / o["tick"])
                chars.append(cs[int(rnd(o["seed"] + tick, li * 97 + i, 3) * len(cs))])
        out.append("".join(chars))
    return "\n".join(out)


def timeline(texts, o):
    """List of (start, prev, target); returns segments and total duration."""
    segs, t, prev = [], 0.0, ""
    for tx in texts:
        segs.append((t, prev, tx))
        t += o["decode"] + o["hold"]
        prev = tx
    return segs, t


def text_at(segs, total, t, o, loop):
    if loop:
        t = t % total
    seg = segs[0]
    for s in segs:
        if t >= s[0]:
            seg = s
    return frame_text(seg[1], seg[2], t - seg[0], o)


# ---------- rendering ----------
def make_renderer(args, W, H):
    size = max(8, int(W * args.size))
    font = ImageFont.truetype(str(args.font), size)
    adv = font.getlength("M") + args.tracking * size
    line_h = int(size * args.line_height)
    cx = W * args.x
    cy = H * args.y
    color = tuple(int(args.color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))

    def render(text):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lines = text.split("\n")
        block_h = line_h * len(lines)
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0)) if args.shadow > 0 else None
        d = ImageDraw.Draw(img)
        sd = ImageDraw.Draw(shadow) if shadow else None
        for li, ln in enumerate(lines):
            w = adv * len(ln) - args.tracking * size
            x0 = cx - w / 2
            y = cy - block_h / 2 + li * line_h
            for ci, ch in enumerate(ln):
                if ch == " ":
                    continue
                x = x0 + ci * adv
                if sd:
                    sd.text((x, y), ch, font=font, fill=(0, 0, 0, int(255 * args.shadow)))
                d.text((x, y), ch, font=font, fill=color + (int(255 * args.opacity),))
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
    p.add_argument("-t", "--text", action="append", required=True, help="phrase (repeat for a sequence; \\n = new line)")
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
    p.add_argument("--loop", action="store_true", help="repeat the sequence until duration")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--wrap", type=int, default=12, help="phrases longer than this split into 2 balanced lines (0 = never)")
    p.add_argument("--font", type=Path, default=DEFAULT_FONT)
    p.add_argument("--size", type=float, default=0.036, help="font size as fraction of width")
    p.add_argument("--tracking", type=float, default=0.18, help="extra letter spacing (em)")
    p.add_argument("--line-height", type=float, default=1.15)
    p.add_argument("--color", default="#FFFFFF")
    p.add_argument("--opacity", type=float, default=0.95)
    p.add_argument("--shadow", type=float, default=0.35, help="soft shadow strength 0-1 (helps legibility)")
    p.add_argument("--x", type=float, default=0.5, help="center x, 0-1")
    p.add_argument("--y", type=float, default=0.5, help="center y, 0-1")
    p.add_argument("--charset", default=CHARSET)
    p.add_argument("--svg-bg", help="solid background color for .svg output, e.g. '#1a1216' (default: transparent)")
    a = p.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found")
    if not Path(a.font).exists():
        sys.exit(f"font not found: {a.font}")
    texts = [wrap_balanced(t.replace("\\n", "\n"), a.wrap) for t in a.text]
    o = dict(decode=a.decode, hold=a.hold, tick=a.tick, seed=a.seed, charset=a.charset)
    segs, total = timeline(texts, o)

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
    render = make_renderer(a, W, H)
    nframes = max(1, int(round(dur * a.fps)))
    loop = a.loop

    out = Path(a.out)
    ext = out.suffix.lower()
    is_seq = ext == ""
    cache = {}

    def frames():
        for f in range(nframes):
            txt = text_at(segs, total, f / a.fps, o, loop)
            if txt not in cache:
                if len(cache) > 400:
                    cache.clear()
                cache[txt] = render(txt)
            yield f, cache[txt]

    if is_seq:
        out.mkdir(parents=True, exist_ok=True)
        for f, im in frames():
            im.save(out / f"frame_{f:05d}.png")
        print(f"{nframes} PNG frames -> {out}/")
        return

    if ext == ".svg":
        write_svg(out, a, W, H, nframes, frames_text=[text_at(segs, total, f / a.fps, o, loop) for f in range(nframes)])
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
              f"[b][1:v]overlay=shortest=1,format=yuv420p[v]")
        cmd += ["-filter_complex", fc, "-map", "[v]"]
        if bg_is_video:
            cmd += ["-map", "0:a?", "-c:a", "copy"]
        if ext == ".gif":
            cmd[cmd.index("-filter_complex") + 1] = fc.replace("format=yuv420p[v]", "split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4[v]")
            cmd += ["-t", f"{dur:.3f}", "-loop", "0"]
        elif ext == ".mp4":
            cmd += ["-t", f"{dur:.3f}", "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-movflags", "+faststart"]
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
