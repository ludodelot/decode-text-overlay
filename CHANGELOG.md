# Changelog

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
