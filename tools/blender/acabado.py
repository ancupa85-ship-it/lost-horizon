"""Acabado de un render: resplandor suave en las luces, un poco de grano y viñeta. Uso: python3 acabado.py entrada.png salida.jpg"""
import sys
import numpy as np
from PIL import Image, ImageFilter
im = Image.open(sys.argv[1]).convert('RGB'); a = np.asarray(im).astype(np.float32) / 255
lum = a.max(axis=2, keepdims=True); bright = a * np.clip((lum - 0.72) / 0.28, 0, 1)
b = Image.fromarray((bright * 255).astype(np.uint8)); w = im.size[0]
glow = sum(np.asarray(b.filter(ImageFilter.GaussianBlur(w * r))).astype(np.float32) / 255 * k for r, k in ((0.004, 0.5), (0.015, 0.45), (0.05, 0.35)))
out = 1 - (1 - a) * (1 - np.clip(glow, 0, 1))
h, w_ = out.shape[:2]; yy, xx = np.mgrid[0:h, 0:w_]; d = ((xx / w_ - 0.5) ** 2 + (yy / h - 0.5) ** 2) ** 0.5
out *= (1 - 0.35 * np.clip(d - 0.35, 0, 1) ** 1.5 * 2)[..., None]
out += np.random.default_rng(7).normal(0, 0.008, out.shape[:2])[..., None]
Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).save(sys.argv[2], quality=93)
