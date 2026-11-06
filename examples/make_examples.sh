#!/usr/bin/env bash
# Regenerates the example GIFs/SVG in this folder from synthetic backgrounds.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}; D=skills/decode-text-overlay/scripts/decode_overlay.py; T=$(mktemp -d)
ffmpeg -v error -y -f lavfi -i "gradients=s=1080x1920:c0=0x2b1d33:c1=0x9a5a68:c2=0xc98a88:n=3:x0=0:y0=0:x1=150:y1=1920:d=1" -vf "noise=alls=14:allf=u" -frames:v 1 $T/story.png
ffmpeg -v error -y -f lavfi -i "gradients=s=1600x900:c0=0x10202e:c1=0x4a7186:c2=0x8fb0b8:n=3:x0=0:y0=0:x1=250:y1=900:d=1" -vf "noise=alls=14:allf=u" -frames:v 1 $T/wide.png
$PY $D -t "MIDNIGHT SESSIONS" -t "STUDIO ONE\nLIVE SET" -t "OUT NOW" --bg $T/story.png --width 480 --fps 20 --size 0.046 --loop --duration 8 -o examples/story.gif
$PY $D -t "GOLDEN HOUR" -t "LISBON, 2026" --bg $T/wide.png --width 720 --fps 20 --size 0.034 --loop --duration 5.2 -o examples/wide.gif
$PY $D -t "NEW COLLECTION" -t "AVAILABLE SOON" --size-px 1200x400 --size 0.034 --fps 24 --loop --svg-bg "#16101a" -o examples/overlay.svg
