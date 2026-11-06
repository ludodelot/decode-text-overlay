# Changelog

## 0.3.0
- Bundled DM Mono (Regular and Light, SIL OFL): `--font dm-mono` / `dm-mono-light` / `space-mono`, also per block (`font=dm-mono-light`).
- `--block "TEXT;y=0.2;size=0.07;delay=0.5;preset=cinematic"` (repeatable): stack several texts in one render, each with its own position, style and timing.
- `--scrim top|bottom|band|full@opacity:extent`: dark gradients between the photo and the text, for legible overlays on busy photos.
- `--delay` (and a `delay` attribute on `<decode-text>`), covered by the JS/Python parity test.
- Tested end to end with a 9:16 Instagram story layout.

## 0.2.0
- Text now grows from the center outward and resolves in random order (matches the reference look).
- Long phrases wrap into two balanced lines (`--wrap`, `wrap` attribute).
- New: `--preset` (story, minimal, cinematic, poster, terminal, lowerthird), `--order random|center|ltr`, `--exit` (dissolve back to glyphs), `--color auto` (white or dark from the background).
- New outputs: animated SVG, GIF over a background, `--width` downscale.
- Web component: `order`, `exit`, `wrap` attributes; live demo with controls.
- Tests for JS/Python parity and real renders, GitHub Actions CI.
- Installable with pip (`decode-text-overlay` command), npm-ready web component, Claude Code plugin manifest, `AGENTS.md` for Codex.
- Skill folder is self-contained (script and font included).

## 0.1.0
- First release: CLI renderer and `<decode-text>` web component.
