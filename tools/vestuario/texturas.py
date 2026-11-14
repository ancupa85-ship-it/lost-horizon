"""Texturas de tela generadas con numpy (sin descargas): color y relieve, repetibles en las dos direcciones."""
import numpy as np
from PIL import Image

N = 512


def ruido(beta, seed, n=N, ax=1.0, ay=1.0):
    """Ruido fractal periódico en [0,1]; beta alto = manchas grandes; ax, ay estiran (vetas)."""
    rng = np.random.default_rng(seed)
    f = np.fft.fft2(rng.standard_normal((n, n)))
    fy, fx = np.meshgrid(np.fft.fftfreq(n) * n, np.fft.fftfreq(n) * n, indexing='ij')
    k = np.hypot(fx * ax, fy * ay)
    k[0, 0] = 1.0
    a = np.real(np.fft.ifft2(f / k ** beta))
    return (a - a.min()) / (a.max() - a.min())


def _xy(n=N):
    y, x = np.meshgrid(np.arange(n) / n, np.arange(n) / n, indexing='ij')
    return x, y


def color(base, mod):
    """base sRGB 0-255; mod = factor por píxel alrededor de 1."""
    a = np.clip(np.array(base, float)[None, None, :] * mod[:, :, None], 0, 255)
    return Image.fromarray(a.astype('uint8'))


def relieve(h, fuerza):
    dx = np.roll(h, -1, 1) - np.roll(h, 1, 1)
    dy = np.roll(h, -1, 0) - np.roll(h, 1, 0)
    n = np.dstack([-dx * fuerza, dy * fuerza, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).astype('uint8'))


def capote():
    """Lona engomada verde gris: trama fina, manchas grandes de humedad y regueros verticales."""
    x, y = _xy()
    trama = np.sin(2 * np.pi * x * 128) * np.sin(2 * np.pi * y * 128)
    manchas = ruido(1.9, 11)
    regueros = ruido(1.5, 12, ax=6.0, ay=0.35)
    arrugas = ruido(1.7, 13)
    mod = 1.0 + 0.035 * trama + 0.30 * (manchas - 0.5) - 0.22 * np.clip(regueros - 0.55, 0, 1) + 0.12 * (arrugas - 0.5)
    return color((50, 54, 40), mod), relieve(arrugas * 2.2 + trama * 0.10 + ruido(1.0, 14) * 0.25, 1.4)


def pano(base=(58, 61, 43)):
    """Sarga de uniforme: trama diagonal y desgaste."""
    x, y = _xy()
    sarga = np.sin(2 * np.pi * (x + y) * 96)
    hilo = np.sin(2 * np.pi * x * 192) * 0.5
    desg = ruido(1.8, 21)
    mod = 1.0 + 0.05 * sarga + 0.02 * hilo + 0.28 * (desg - 0.5)
    return color(base, mod), relieve(sarga * 0.22 + ruido(1.6, 22) * 5.0, 2.0)


def lana():
    """Punto de lana oscuro (pasamontañas, braga): canalé vertical."""
    x, y = _xy()
    canale = np.abs(np.sin(np.pi * x * 64))
    punto = np.sin(2 * np.pi * y * 96 + np.pi * np.floor(x * 64))
    pelusa = ruido(0.8, 31)
    mod = 0.82 + 0.30 * canale + 0.06 * punto + 0.14 * (pelusa - 0.5) + 0.2 * (ruido(1.8, 32) - 0.5)
    return color((44, 46, 40), mod), relieve(canale * 0.9 + punto * 0.2 + pelusa * 0.3, 3.0)


def casco():
    """Acero pintado de verde oliva mate: desconchones, arañazos y piel de naranja."""
    manchas = ruido(1.7, 41)
    fino = ruido(0.6, 42)
    chip = np.clip((ruido(1.2, 43) - 0.74) * 14, 0, 1)        # desconchones: se ve el metal oscuro
    ara = np.clip((ruido(1.1, 44, ax=0.15, ay=5.0) - 0.72) * 9, 0, 1)   # arañazos largos
    mod = 1.0 + 0.24 * (manchas - 0.5) + 0.06 * (fino - 0.5)
    a = np.array((62, 68, 46), float)[None, None, :] * mod[:, :, None]
    metal = np.array((40, 36, 32), float)[None, None, :] * (0.8 + 0.5 * fino[:, :, None])
    k = np.clip(chip + 0.6 * ara, 0, 1)[:, :, None]
    a = a * (1 - k) + metal * k
    return Image.fromarray(np.clip(a, 0, 255).astype('uint8')), relieve(fino * 0.35 - chip * 0.5 - ara * 0.3, 2.0)


def lona():
    """Cinta de lona caqui del correaje: tejido grueso."""
    x, y = _xy()
    t = np.sign(np.sin(2 * np.pi * x * 48)) * np.sign(np.sin(2 * np.pi * y * 48))
    s = np.abs(np.sin(2 * np.pi * x * 48)) * np.abs(np.sin(2 * np.pi * y * 48))
    suc = ruido(1.8, 51)
    mod = 1.0 + 0.06 * t + 0.10 * (s - 0.4) + 0.34 * (suc - 0.5)
    return color((92, 88, 60), mod), relieve(s * 0.8 + t * 0.15 + ruido(1.2, 52) * 1.2, 2.5)


def cuero():
    grano = ruido(0.9, 61)
    desg = ruido(1.9, 62)
    mod = 1.0 + 0.25 * (grano - 0.5) + 0.5 * (desg - 0.5)
    return color((36, 30, 26), mod), relieve(grano * 0.6 + desg * 2.0, 2.0)


def retinte(im, destino=(58, 61, 43), mezcla=0.85):
    """Lleva la textura del traje de MakeHuman (camisa y pantalón verdes) al verde oliva del uniforme, más sufrido."""
    a = np.asarray(im.convert('RGB')).astype(float)
    lum = a @ np.array([0.299, 0.587, 0.114])
    lum = lum / max(lum.mean(), 1.0)
    lum = 1.0 + (lum - 1.0) * 1.1
    b = np.array(destino, float)[None, None, :] * lum[:, :, None]
    medio = a.reshape(-1, 3).mean(0)
    orig = a * (np.array(destino, float).mean() / max(medio.mean(), 1.0))
    out = mezcla * b + (1 - mezcla) * orig
    desg = ruido(1.8, 71, n=a.shape[0]) if a.shape[0] == a.shape[1] else 0.5
    out = out * (1.0 + 0.22 * (desg - 0.5))[:, :, None] if not np.isscalar(desg) else out
    return Image.fromarray(np.clip(out, 0, 255).astype('uint8'))
