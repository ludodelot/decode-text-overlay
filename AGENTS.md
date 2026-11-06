# Agent instructions (Codex and other AGENTS.md-aware tools)

This repo renders **decoding text overlays**: monospace text that grows from the center as random glyphs and resolves into a phrase. Use it when the user wants animated text on a photo, a video or a web page.

Full skill instructions: `skills/decode-text-overlay/SKILL.md` (read it first).

## Setup (once)
```bash
python3 -m venv .venv && .venv/bin/pip install pillow   # ffmpeg must be installed
```

## Render
```bash
.venv/bin/python skills/decode-text-overlay/scripts/decode_overlay.py \
  -t "PHRASE ONE" -t "PHRASE TWO" --bg input.jpg -o output.mp4
```
(If installed with pip or pipx the command is `decode-text-overlay`.)
- Several texts in one render: repeat `--block "TEXT;y=0.2;size=0.07;delay=0.5;order=ltr"` (any flag works as `key=value`); darken photo areas with `--scrim "top@0.9:0.42"` / `bottom` / `band` / `full`. For Instagram stories keep text between 13% and 87% of the height.
- Style: `--preset story|minimal|cinematic|poster|terminal|lowerthird`, `--color auto` (white or dark from the background), `--order random|center|ltr`, `--exit 0.5` (dissolve back out), `--loop`, `--width` (downscale GIFs).
- Output by extension: `.mp4` (with `--bg`), `.mov`/`.webm` (transparent layer), `.gif`, `.svg`, or a folder for PNG frames.
- `\n` inside a phrase forces a line break; phrases over 12 characters wrap into two balanced lines.
- On light backgrounds use `--color "#111111" --shadow 0`.
- Web: `web/decode-text.js` provides `<decode-text texts="A|B" loop>`.

## Rules
- Always extract and look at one frame before reporting success (`ffmpeg -i out.mp4 -frames:v 1 check.png`).
- Never invent text (dates, names) the user did not give.
- The JS and Python animations must stay identical: change both or neither. `python -m unittest discover -s tests` checks this.
