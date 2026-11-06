#!/usr/bin/env python3
"""Procedural mountain backdrop (layered ridgelines, dawn sky, grain). Usage: make_bg.py out.png WxH [seed]"""
import math, random, sys
from PIL import Image, ImageDraw, ImageFilter

out, size = sys.argv[1], sys.argv[2]
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 5
W, H = (int(v) for v in size.lower().split("x"))
rnd = random.Random(seed)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


sky = Image.new("RGB", (W, H))
px = ImageDraw.Draw(sky)
top, mid, hor = (16, 22, 48), (92, 70, 110), (226, 150, 128)
for y in range(H):
    t = y / (H * 0.66)
    px.line([(0, y), (W, y)], fill=lerp(top, mid, t / 0.55) if t < 0.55 else lerp(mid, hor, min(1, (t - 0.55) / 0.45)))

layers = [  # (base y, amplitude, color, haze)
    (0.60, 0.17, (120, 104, 140), 0.55), (0.66, 0.15, (84, 76, 112), 0.40),
    (0.74, 0.13, (52, 50, 82), 0.25), (0.84, 0.10, (30, 30, 54), 0.10), (0.94, 0.07, (16, 16, 32), 0.0)]
img = sky.convert("RGBA")
for base, amp, col, haze in layers:
    ph = [rnd.uniform(0, 6.28) for _ in range(5)]
    pts = []
    for x in range(0, W + 4, 4):
        u = x / W
        v = sum(math.sin(u * f * 6.28 + p) / f for f, p in zip((1.3, 2.9, 5.7, 11.3, 23.1), ph))
        ridge = abs(v) * 0.6 + 0.25 * math.sin(u * 3 + ph[0])  # sharp peaks
        pts.append((x, H * base - ridge * H * amp))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(layer).polygon(pts + [(W, H), (0, H)], fill=col + (255,))
    fog = Image.new("RGBA", (W, H), hor + (int(255 * haze),))
    layer = Image.composite(Image.alpha_composite(layer, fog), layer, layer.split()[3])
    img = Image.alpha_composite(img, layer)
img = img.convert("RGB").filter(ImageFilter.GaussianBlur(0.6))
grain = Image.effect_noise((W, H), 14).convert("RGB")
Image.blend(img, grain, 0.05).save(out)
