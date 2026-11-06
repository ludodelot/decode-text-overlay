#!/usr/bin/env bash
# Regenerates the example GIFs/SVG in this folder from procedural mountain backdrops.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}; D=skills/decode-text-overlay/scripts/decode_overlay.py; T=$(mktemp -d)
$PY examples/make_bg.py $T/story.png 1080x1920 5
$PY examples/make_bg.py $T/wide.png 1600x900 8
$PY $D --preset cinematic -t "EVEREST\n8,849 M" -t "27.9881° N\n86.9250° E" -t "NEPAL · CHINA" \
  --bg $T/story.png --width 480 --fps 20 --size 0.05 --y 0.42 --loop --duration 8 -o examples/story.gif
$PY $D -t "K2 · 8,611 M" -t "35.8825° N 76.5133° E" --bg $T/wide.png --width 720 --fps 20 --size 0.034 --y 0.4 \
  --loop --duration 5.2 -o examples/wide.gif
$PY $D -t "KANGCHENJUNGA\n8,586 M" -t "27.7025° N 88.1475° E" --size-px 1200x400 --size 0.034 --fps 24 --loop \
  --svg-bg "#16101a" -o examples/overlay.svg
$PY examples/make_bg.py web/mountains.jpg 540x960 5
