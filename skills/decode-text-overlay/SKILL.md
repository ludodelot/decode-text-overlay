---
name: decode-text-overlay
description: Genera un texto monoespaciado que se "descifra" (caracteres aleatorios que se resuelven letra a letra, estilo stories de lanzamientos musicales) para ponerlo como capa sobre fotos, vídeos o webs. Salidas - overlay con transparencia (.mov/.webm), PNG sequence, GIF, vídeo ya compuesto sobre tu foto/vídeo (.mp4) o web component <decode-text>. Úsalo cuando pidan texto animado glitch/scramble/decode/terminal sobre una imagen, un vídeo o una web, aunque no digan "skill".
---

# decode-text-overlay

Texto centrado, mayúsculas, monoespaciado, con tracking ancho. Crece desde el centro hacia fuera como caracteres basura y cada letra se resuelve en orden aleatorio hasta la frase final; aguanta y corta a la siguiente. Las frases de más de 12 caracteres se parten solas en dos líneas equilibradas (`--wrap 0` lo desactiva). Determinista (`--seed`).

## Cómo trabajar

1. Pregunta (o deduce) las frases, el destino (foto / vídeo / web / editor) y el formato (9:16 story por defecto).
2. Elige salida:
   - **Sobre una foto o vídeo ya listo** → `--bg archivo -o salida.mp4`
   - **Capa para un editor (Premiere, CapCut, DaVinci)** → `-o overlay.mov` (ProRes 4444 alfa) o `.webm`
   - **Frames** → `-o carpeta/` · **GIF** → `-o x.gif`
   - **Web** → `web/decode-text.js` + `<decode-text texts="A|B" loop>` dentro de un contenedor `position:relative`
3. Ejecuta y **mira siempre un fotograma** (extrae con ffmpeg) antes de entregar: legibilidad sobre el fondo real.

## CLI

```bash
python3 -m venv .venv && .venv/bin/pip install pillow     # una vez; requiere ffmpeg
.venv/bin/python skills/decode-text-overlay/scripts/decode_overlay.py --preset cinematic \
  -t "EVEREST\n8,849 M" -t "27.9881° N\n86.9250° E" --bg foto.jpg --color auto -o story.mp4
```
(Si está instalado con pip/pipx, el comando es `decode-text-overlay`.)

Presets (`--preset`): `story` (por defecto), `minimal`, `cinematic`, `poster`, `terminal`, `lowerthird`. Cualquier flag explícito gana sobre el preset.

Opciones útiles: `--decode 0.9` (s por frase) · `--hold 1.3` · `--exit 0.5` (el texto se disuelve de vuelta a glifos; 0 = corte) · `--order random|center|ltr` · `--loop` · `--size 0.036` (fracción del ancho) · `--tracking 0.18` · `--x/--y 0.5` · `--color "#FFFFFF"` o `auto` (blanco/oscuro según el fondo) · `--shadow 0.35` · `--wrap 12` · `--font ruta.ttf` · `--size-px 1080x1920` (sin fondo; para 4K usa 2160x3840) · `--width` (reduce, útil en GIF) · `--duration`.

## Criterio de diseño

- Tamaño pequeño y discreto (≈3–4 % del ancho); el efecto está en el movimiento, no en el tamaño.
- Una o dos líneas máximo, ≤ 24 caracteres por línea.
- Si el fondo es claro, sube `--shadow` o usa `--color "#111111" --shadow 0`.
- Fuente por defecto: Space Mono (OFL). Cualquier monoespaciada funciona.
- No inventes datos (fechas, nombres) que el usuario no haya dado.
