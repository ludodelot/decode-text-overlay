#!/usr/bin/env python3
"""Generates the animated SVGs used by the README (pure SMIL, no JS, no fonts to load).
Run: .venv/bin/python assets/make_assets.py
The banner is rendered with the project's own animation core."""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "skills" / "decode-text-overlay" / "scripts"))
import decode_overlay as d  # noqa: E402

BG, PANEL, LINE = "#0f0b12", "#1a131f", "#33283b"
ROSE, TEXT, MUTED, MINT = "#e9aaa0", "#f4eae6", "#8f8498", "#9fd8c0"
MONO = '"Space Mono","SF Mono",ui-monospace,Menlo,Consolas,monospace'
SANS = 'system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif'


def seq(texts, fps, o, loop=True):
    segs, total = d.timeline(texts, o)
    n = int(round(total * fps))
    return [d.text_at(segs, total, i / fps, o, loop) for i in range(n)], n / fps


def anim_text(frames, dur, fps, cx, cy, size, tracking, color, line_h=1.18, anchor="middle"):
    uniq = {}
    for i, t in enumerate(frames):
        uniq.setdefault(t, set()).add(i)
    n, out = len(frames), []
    for txt, idx in uniq.items():
        lines = txt.split("\n")
        y0 = cy - size * line_h * (len(lines) - 1) / 2
        ts = "".join(f'<tspan x="{cx + tracking * size / 2:.1f}" y="{y0 + li * size * line_h:.1f}" xml:space="preserve">{escape(l)}</tspan>'
                     for li, l in enumerate(lines))
        kt, vv, last = [], [], None
        for i in range(n):
            v = "visible" if i in idx else "hidden"
            if v != last:
                kt.append(f"{i / n:.5f}"); vv.append(v); last = v
        if kt[0] != "0.00000":
            kt.insert(0, "0"); vv.insert(0, "hidden")
        out.append(f'<text class="m" style="font-size:{size}px;letter-spacing:{tracking}em;fill:{color}" text-anchor="{anchor}">{ts}'
                   f'<animate attributeName="visibility" calcMode="discrete" dur="{dur:.3f}s" repeatCount="indefinite" '
                   f'keyTimes="{";".join(kt)}" values="{";".join(vv)}"/></text>')
    return "".join(out)


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title><style>.m{{font-family:{MONO};white-space:pre;visibility:hidden}}'
            f'.s{{font-family:{SANS}}}.mono{{font-family:{MONO}}}</style>{body}</svg>')


# ---------------------------------------------------------------- banner
def banner():
    W, H, fps = 1280, 400, 24
    o = dict(decode=1.3, hold=2.8, tick=1 / 20, seed=11, charset=d.CHARSET)
    fr, dur = seq([d.wrap_balanced("DECODE TEXT OVERLAY", 12)], fps, o)
    grid = "".join(f'<path d="M{x} 0V{H}" />' for x in range(0, W, 64)) + "".join(f'<path d="M0 {y}H{W}" />' for y in range(0, H, 64))
    body = (
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2b1d33"/>'
        f'<stop offset=".55" stop-color="#0f0b12"/><stop offset="1" stop-color="#3a1f2b"/></linearGradient>'
        f'<radialGradient id="r" cx=".5" cy=".5" r=".6"><stop offset="0" stop-color="{ROSE}" stop-opacity=".22"/>'
        f'<stop offset="1" stop-color="{ROSE}" stop-opacity="0"/></radialGradient></defs>'
        f'<rect width="{W}" height="{H}" fill="url(#g)"/><g stroke="#ffffff" stroke-opacity=".035">{grid}</g>'
        f'<ellipse cx="{W / 2}" cy="170" rx="520" ry="150" fill="url(#r)"><animate attributeName="opacity" values=".6;1;.6" dur="5s" repeatCount="indefinite"/></ellipse>'
        + anim_text(fr, dur, fps, W / 2, 170, 54, 0.22, TEXT)
        + f'<text class="s" x="{W / 2}" y="290" text-anchor="middle" font-size="19" fill="{MUTED}" letter-spacing=".02em">'
          f'Animated text layers for photos, videos and websites</text>'
          f'<text class="mono" x="{W / 2}" y="332" text-anchor="middle" font-size="14" fill="{ROSE}" letter-spacing=".18em">'
          f'CLAUDE CODE SKILL  ·  CODEX  ·  CLI  ·  WEB COMPONENT</text>'
    )
    (HERE / "banner.svg").write_text(svg(W, H, body, "decode-text-overlay banner"), encoding="utf-8")


# ---------------------------------------------------------------- how it works
def how_it_works():
    W, H = 1200, 470
    o = dict(decode=1.0, hold=1.0, tick=1 / 24, seed=7, charset=d.CHARSET)
    steps = [(0.06, "1", "Start at the center"), (0.20, "2", "Grow outward"), (0.38, "3", "Glyphs keep changing"),
             (0.62, "4", "Resolve in random order"), (1.00, "5", "Hold, then cut to next")]
    phrase = "MIDNIGHT\nSESSIONS"
    pw, gap, x0 = 210, 22, 36
    cycle = 9.0
    body = [f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>',
            f'<text class="s" x="36" y="52" font-size="24" font-weight="700" fill="{TEXT}">How the effect works</text>',
            f'<text class="s" x="36" y="80" font-size="15" fill="{MUTED}">Every character gets its own appear time and resolve time. Frames below are real output of the renderer.</text>']
    n = len(steps)
    for k, (t, num, label) in enumerate(steps):
        x = x0 + k * (pw + gap)
        txt = d.frame_text("", phrase, t, o)
        # active highlight via discrete opacity animation
        kt = [f"{j / n:.4f}" for j in range(n)] + ["1"]
        vals = []
        for j in range(n):
            vals.append("1" if j == k else ".35")
        vals.append(vals[-1])
        # build keyTimes so that step k is bright during its slot
        kts = ";".join(kt); vs = ";".join(".35" if j != k else "1" for j in range(n)) + ";" + (".35" if n - 1 != k else "1")
        body.append(f'<g opacity=".35"><animate attributeName="opacity" calcMode="discrete" dur="{cycle}s" repeatCount="indefinite" keyTimes="{kts}" values="{vs}"/>'
                    f'<rect x="{x}" y="112" width="{pw}" height="220" rx="14" fill="{PANEL}" stroke="{LINE}"/>'
                    f'<circle cx="{x + 28}" cy="142" r="13" fill="{ROSE}"/><text class="s" x="{x + 28}" y="147" text-anchor="middle" font-size="14" font-weight="700" fill="{BG}">{num}</text>'
                    f'<text class="s" x="{x + 52}" y="147" font-size="14.5" font-weight="600" fill="{TEXT}">{escape(label)}</text>')
        lines = txt.split("\n")
        for li, ln in enumerate(lines):
            body.append(f'<text class="mono" xml:space="preserve" x="{x + pw / 2 + 2}" y="{236 + li * 30}" text-anchor="middle" font-size="22" letter-spacing=".16em" fill="{TEXT}" style="white-space:pre">{escape(ln)}</text>')
        body.append('</g>')
    # playhead
    track_w = n * pw + (n - 1) * gap
    body.append(f'<rect x="{x0}" y="362" width="{track_w}" height="6" rx="3" fill="{LINE}"/>'
                f'<rect x="{x0}" y="362" width="0" height="6" rx="3" fill="{ROSE}"><animate attributeName="width" values="0;{track_w}" dur="{cycle}s" repeatCount="indefinite"/></rect>'
                f'<circle cy="365" r="9" fill="{TEXT}"><animate attributeName="cx" values="{x0};{x0 + track_w}" dur="{cycle}s" repeatCount="indefinite"/></circle>')
    body.append(f'<text class="s" x="{x0}" y="404" font-size="14" fill="{MUTED}">0 s</text>'
                f'<text class="s" x="{x0 + track_w}" y="404" text-anchor="end" font-size="14" fill="{MUTED}">--decode seconds (default 0.9) + --hold (default 1.3)</text>')
    body.append(f'<text class="mono" x="{x0}" y="432" font-size="13.5" fill="{ROSE}">appear  = grow × distance_from_center × jitter</text>'
                f'<text class="mono" x="{x0}" y="452" font-size="13.5" fill="{ROSE}">resolve = decode × (0.35 + 0.65 × random)</text>')
    (HERE / "how-it-works.svg").write_text(svg(W, H, "".join(body), "How the decode effect works"), encoding="utf-8")


# ---------------------------------------------------------------- outputs flow
def outputs():
    W, H = 1200, 520
    ins = [("Phrases", '-t "MIDNIGHT SESSIONS"'), ("Photo or video", "--bg photo.jpg"), ("Style", "--size  --tracking  --color")]
    outs = [("story.mp4", "text burned onto photo/video"), ("overlay.mov / .webm", "transparent layer (alpha)"),
            ("text.gif", "looping GIF"), ("text.svg", "animated SVG, no JS"), ("frames/", "PNG sequence"),
            ("<decode-text>", "web component")]
    body = [f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>',
            f'<text class="s" x="36" y="52" font-size="24" font-weight="700" fill="{TEXT}">One input, six outputs</text>',
            f'<text class="s" x="36" y="80" font-size="15" fill="{MUTED}">Same animation everywhere. Python renders files, JavaScript renders the browser version.</text>']
    cx, cw, ch, cy = 470, 260, 130, 240
    for i, (t, sub) in enumerate(ins):
        y = 130 + i * 110
        body.append(f'<rect x="36" y="{y}" width="290" height="84" rx="12" fill="{PANEL}" stroke="{LINE}"/>'
                    f'<text class="s" x="58" y="{y + 34}" font-size="17" font-weight="600" fill="{TEXT}">{escape(t)}</text>'
                    f'<text class="mono" x="58" y="{y + 60}" font-size="13" fill="{ROSE}">{escape(sub)}</text>')
        body.append(f'<path d="M326 {y + 42} C400 {y + 42} 400 {cy + ch / 2} {cx} {cy + ch / 2}" fill="none" stroke="{ROSE}" stroke-opacity=".7" stroke-width="2" stroke-dasharray="6 8">'
                    f'<animate attributeName="stroke-dashoffset" from="28" to="0" dur="1.2s" repeatCount="indefinite"/></path>')
    body.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="16" fill="#2a1a2f" stroke="{ROSE}" stroke-width="1.5"/>'
                f'<text class="s" x="{cx + cw / 2}" y="{cy + 56}" text-anchor="middle" font-size="18" font-weight="700" fill="{TEXT}">decode-text-overlay</text>'
                f'<text class="mono" x="{cx + cw / 2}" y="{cy + 84}" text-anchor="middle" font-size="12.5" fill="{MUTED}">decode_overlay.py + ffmpeg</text>'
                f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="16" fill="none" stroke="{ROSE}" stroke-width="3" opacity="0">'
                f'<animate attributeName="opacity" values="0;.5;0" dur="2.4s" repeatCount="indefinite"/></rect>')
    for i, (t, sub) in enumerate(outs):
        y = 112 + i * 62
        body.append(f'<path d="M{cx + cw} {cy + ch / 2} C{cx + cw + 80} {cy + ch / 2} {cx + cw + 60} {y + 26} 800 {y + 26}" fill="none" stroke="{MINT}" stroke-opacity=".65" stroke-width="2" stroke-dasharray="6 8">'
                    f'<animate attributeName="stroke-dashoffset" from="28" to="0" dur="1.2s" repeatCount="indefinite"/></path>'
                    f'<rect x="800" y="{y}" width="364" height="52" rx="10" fill="{PANEL}" stroke="{LINE}"/>'
                    f'<text class="mono" x="820" y="{y + 23}" font-size="15" font-weight="700" fill="{TEXT}">{escape(t)}</text>'
                    f'<text class="s" x="820" y="{y + 42}" font-size="12.5" fill="{MUTED}">{escape(sub)}</text>')
    (HERE / "outputs.svg").write_text(svg(W, H, "".join(body), "Inputs and outputs of decode-text-overlay"), encoding="utf-8")


# ---------------------------------------------------------------- agents (terminal demos)
def term(x, title, accent, lines, w=560, h=330, cycle=12.0):
    body = [f'<g transform="translate({x},0)"><rect y="104" width="{w}" height="{h}" rx="14" fill="#0b080e" stroke="{LINE}"/>'
            f'<rect y="104" width="{w}" height="38" rx="14" fill="{PANEL}"/><rect y="124" width="{w}" height="18" fill="{PANEL}"/>'
            f'<circle cx="24" cy="123" r="6" fill="#ff5f57"/><circle cx="44" cy="123" r="6" fill="#febc2e"/><circle cx="64" cy="123" r="6" fill="#28c840"/>'
            f'<text class="mono" x="{w / 2}" y="128" text-anchor="middle" font-size="13" fill="{accent}">{escape(title)}</text>']
    n = len(lines)
    for i, (kind, txt) in enumerate(lines):
        start = i / (n + 1)
        kt = f"0;{start:.4f};1"
        col = {"user": TEXT, "tool": MUTED, "ok": MINT}[kind]
        pre = {"user": "&gt; ", "tool": "● ", "ok": "✓ "}[kind]
        y = 176 + i * 40
        body.append(f'<text class="mono" x="24" y="{y}" font-size="13.5" fill="{col}" opacity="0" xml:space="preserve">{pre}{escape(txt)}'
                    f'<animate attributeName="opacity" calcMode="discrete" dur="{cycle}s" repeatCount="indefinite" keyTimes="{kt}" values="0;1;1"/></text>')
    body.append(f'<rect x="24" y="{176 + n * 40 - 14}" width="9" height="16" fill="{accent}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect></g>')
    return "".join(body)


def agents():
    W, H = 1200, 470
    claude = [("user", 'put a decoding text "OUT NOW" over beach.jpg'),
              ("tool", "decode-text-overlay skill loaded"),
              ("tool", 'decode_overlay.py -t "OUT NOW" --bg beach.jpg'),
              ("tool", "      -o beach_text.mp4"),
              ("ok", "132 frames, 4.4s -> beach_text.mp4")]
    codex = [("user", "add a decode text layer saying OUT NOW to beach.jpg"),
             ("tool", "reads AGENTS.md in the repo"),
             ("tool", 'decode_overlay.py -t "OUT NOW" --bg beach.jpg'),
             ("tool", "      -o beach_text.mp4"),
             ("ok", "132 frames, 4.4s -> beach_text.mp4")]
    body = [f'<rect width="{W}" height="{H}" rx="18" fill="{BG}"/>',
            f'<text class="s" x="36" y="52" font-size="24" font-weight="700" fill="{TEXT}">Ask your agent in plain language</text>',
            f'<text class="s" x="36" y="80" font-size="15" fill="{MUTED}">Claude Code loads the skill. Codex follows AGENTS.md. Both call the same script.</text>',
            term(36, "Claude Code", ROSE, claude), term(604, "Codex CLI", MINT, codex)]
    (HERE / "agents.svg").write_text(svg(W, H, "".join(body), "Using decode-text-overlay with Claude Code and Codex"), encoding="utf-8")


if __name__ == "__main__":
    banner(); how_it_works(); outputs(); agents()
    for f in sorted(HERE.glob("*.svg")):
        print(f.name, f.stat().st_size // 1024, "KB")
