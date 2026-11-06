<p align="center"><img src="assets/banner.svg" alt="decode-text-overlay" width="100%"></p>

<p align="center">
  <b>Text that grows from the center as random glyphs, then resolves into your phrase.</b><br>
  The look of music-release stories, as a layer for photos, videos and websites.
</p>

<p align="center">
  <a href="https://ludodelot.github.io/decode-text-overlay/web/demo.html">Live demo</a> ·
  <a href="#use-it-with-claude-code">Claude Code</a> ·
  <a href="#use-it-with-codex">Codex</a> ·
  <a href="#cli">CLI</a> ·
  <a href="#on-a-website">Website</a>
</p>

<p align="center"><img src="examples/story.gif" alt="Decoding text over a gradient, 9:16" width="250"></p>

## How it works

<img src="assets/how-it-works.svg" alt="How the decode effect works" width="100%">

The phrase is laid out in a monospace grid and centered, so it can grow outward from the middle. Each character has two random moments: when it appears and when it resolves. Between them it shows a glyph that changes about 24 times a second. The randomness is a hash of seed, position and tick, so the same seed always gives the same animation, in Python and in JavaScript.

## One input, six outputs

<img src="assets/outputs.svg" alt="Inputs and outputs" width="100%">

| You want | Add this | Result |
|---|---|---|
| Text burned onto a photo or video | `--bg photo.jpg -o story.mp4` | final mp4, video audio kept |
| A layer for Premiere, CapCut or DaVinci | `-o overlay.mov` | ProRes 4444 with alpha (`.webm` = VP9 alpha) |
| A GIF for chat or docs | `--bg photo.jpg --width 480 -o text.gif` | looping GIF |
| An animated SVG, no JS | `-o text.svg --svg-bg "#16101a"` | tiny file that plays inside `<img>` |
| PNG frames | `-o frames/` | `frame_00000.png`... |
| A website | `web/decode-text.js` | `<decode-text>` web component |

<p align="center">
  <img src="examples/wide.gif" alt="16:9 example" width="48%">
  <img src="examples/overlay.svg" alt="Animated SVG example" width="48%">
</p>

## Install

You need Python 3, `ffmpeg` and [Pillow](https://pypi.org/project/pillow/).

```bash
git clone https://github.com/ludodelot/decode-text-overlay && cd decode-text-overlay
python3 -m venv .venv && .venv/bin/pip install pillow
```

## Use it with Claude Code

<img src="assets/agents.svg" alt="Claude Code and Codex terminals" width="100%">

Inside this repo the skill is already wired: `.claude/skills/decode-text-overlay` points to `skills/decode-text-overlay`. Start `claude` here and ask in plain language.

To use it from any project, install it globally. The skill folder is self-contained (script and font included):

```bash
mkdir -p ~/.claude/skills
cp -R skills/decode-text-overlay ~/.claude/skills/
```

Then try:

- *"Put a decoding text 'OUT NOW' over beach.jpg, 9:16."*
- *"Make a transparent overlay that says STUDIO ONE / LIVE SET, I will use it in CapCut."*
- *"Add a `<decode-text>` caption to the hero of my landing page."*

Claude reads `SKILL.md`, runs the script, extracts a frame and checks legibility before it answers.

## Use it with Codex

Codex reads [`AGENTS.md`](AGENTS.md) at the repo root, which tells it how to run the renderer. Open Codex in this repo and ask:

```bash
codex "put a decode text saying OUT NOW over beach.jpg and export an mp4"
```

To use it from another project, copy `AGENTS.md` into that project (or paste its "Render" section into your own `AGENTS.md`) and point the script path at where you cloned this repo. If your Codex version supports skills, copying `skills/decode-text-overlay` into its skills folder works too, since the folder is self-contained.

## CLI

```bash
.venv/bin/python skills/decode-text-overlay/scripts/decode_overlay.py \
  -t "MIDNIGHT SESSIONS" -t "STUDIO ONE\nLIVE SET" -t "OUT NOW" \
  --bg photo.jpg -o story.mp4
```

Each `-t` is one phrase, shown in order. Phrases over 12 characters split into two balanced lines (`--wrap 0` disables it); `\n` chooses the break yourself.

| Option | Default | Meaning |
|---|---|---|
| `--decode` / `--hold` | 0.9 / 1.3 | seconds to resolve a phrase / to keep it |
| `--loop`, `--duration` | off | repeat the sequence; total length |
| `--size`, `--tracking` | 0.036, 0.18 | font size (fraction of width), letter spacing (em) |
| `--x`, `--y` | 0.5, 0.5 | text center, 0 to 1 |
| `--color`, `--shadow`, `--opacity` | white, 0.35, 0.95 | on light photos use `--color "#111" --shadow 0` |
| `--font` | Space Mono | any monospace `.ttf` |
| `--width`, `--fps`, `--seed` | none, 30, 7 | downscale (GIFs), frame rate, same seed = same animation |

`--help` lists everything. Regenerate the examples with `examples/make_examples.sh` and the README graphics with `assets/make_assets.py`.

## On a website

```html
<div style="position:relative">
  <img src="photo.jpg" alt="">
  <decode-text loop texts="MIDNIGHT SESSIONS|OUT NOW"></decode-text>
</div>
<script src="decode-text.js"></script>
```

Attributes: `texts` (`|` separates phrases), `wrap`, `decode`, `hold`, `tick`, `seed`, `loop`, `paused`. Style it with the CSS variables `--dt-font`, `--dt-size`, `--dt-tracking`, `--dt-color`, `--dt-shadow`. It fires `decode-end` when the last phrase resolves, shows the final text when the visitor prefers reduced motion, and works over `<video>` too.

## Good defaults

- Keep it small, around 3 to 4 percent of the width. The motion carries the effect.
- One or two lines, up to about 24 characters each.
- On a busy or bright photo, raise `--shadow` or switch to a dark `--color`.

## License

MIT. Bundled font: Space Mono (SIL OFL 1.1, see `skills/decode-text-overlay/fonts/OFL.txt`).
