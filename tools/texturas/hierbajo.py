"""Textura de hierbajos (los que crecen al pie de las vallas y los muros y en las juntas del camino), con el hueco en el
canal alfa. Cuatro matas en una cuadrícula de 2 x 2 (256 px cada una, la raíz en el centro del borde de abajo):
  0 (arriba izda.) mata alta de hierba seca      1 (arriba dcha.) mata baja y verde con alguna espiga
  2 (abajo izda.)  cardo: tallos altos y hojas   3 (abajo dcha.)  roseta pegada al suelo
En Unreal la usa el material M_Hierbajo (tools/unreal/montar_base.py), recortado, sobre los planos cruzados de la malla
«hierbajos» (tools/unreal/exportar_base.py).
Uso: python3 tools/texturas/hierbajo.py   ->  assets/unreal/texturas_propias/hierbajo.png
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw

N = 512            # píxeles de lado (2 x 2 matas)
SS = 4             # sobremuestreo
C = N // 2 * SS    # lado de una mata, sobremuestreado
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets', 'unreal', 'texturas_propias')

# tanda 23: paleta más apagada (bajo una farola las matas de paja salían como recortes claros) y briznas muertas, grises
PAJA, OLIVA, VERDE, OSCURO, PARDO, MUERTA = (138, 122, 80), (88, 98, 54), (60, 86, 42), (32, 44, 24), (96, 78, 50), (104, 98, 82)

def mezcla(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def hoja(d, x0, y0, x1, y1, curva, ancho, c0, c1, n=12, punta=0.35):
    """Brizna: curva de Bézier de la raíz (x0, y0) a la punta, más ancha abajo; el color va de c0 (raíz) a c1 (punta)."""
    cx, cy = (x0 + x1) / 2 + curva, (y0 + y1) / 2 - abs(curva) * 0.15
    izq, der = [], []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
        tx = 2 * (1 - t) * (cx - x0) + 2 * t * (x1 - cx); ty = 2 * (1 - t) * (cy - y0) + 2 * t * (y1 - cy)
        l = math.hypot(tx, ty) or 1.0
        w = ancho * ((1 - t) ** 0.7) + punta * SS
        izq.append((x - ty / l * w / 2, y + tx / l * w / 2)); der.append((x + ty / l * w / 2, y - tx / l * w / 2))
    for i in range(n):
        d.polygon([izq[i], izq[i + 1], der[i + 1], der[i]], fill=mezcla(c0, c1, i / (n - 1)) + (255,))

def mata(variante, rng):
    im = Image.new('RGBA', (C, C), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    bx, by = C / 2, C - 2 * SS          # la raíz
    M = 7 * SS                          # margen: nada toca el borde de la casilla
    def brizna(alto, abre, ancho, c0, c1, curva=0.25, raiz=0.1):
        a = rng.gauss(0, abre); h = alto * rng.uniform(0.55, 1.0)
        x1 = min(C - M, max(M, bx + math.sin(a) * h)); y1 = max(M, by - math.cos(a) * h)
        hoja(d, bx + rng.uniform(-raiz, raiz) * C, by, x1, y1, rng.uniform(-curva, curva) * h, ancho * SS * rng.uniform(0.7, 1.3), c0, c1)
    if variante == 0:      # hierba seca alta
        for _ in range(70):
            k = rng.random(); punta = MUERTA if rng.random() < 0.3 else mezcla(OLIVA, PAJA, min(1.0, k + 0.3))
            brizna(C * 0.9, 0.3, 2.4, mezcla(OSCURO, PARDO, k), punta, 0.3, 0.08)
        for _ in range(7):   # espigas
            a = rng.gauss(0, 0.2); h = C * rng.uniform(0.7, 0.9); x1 = min(C - M * 1.5, max(M * 1.5, bx + math.sin(a) * h)); y1 = max(M * 1.6, by - math.cos(a) * h)
            hoja(d, bx + rng.uniform(-0.04, 0.04) * C, by, x1, y1, rng.uniform(-0.15, 0.15) * h, 1.6 * SS, PARDO, PAJA)
            d.ellipse([x1 - 2.2 * SS, y1 - 7 * SS, x1 + 2.2 * SS, y1 + 5 * SS], fill=mezcla(PAJA, (190, 170, 110), rng.random()) + (255,))
    elif variante == 1:    # mata baja y verde
        for _ in range(90):
            k = rng.random(); punta = mezcla(PARDO, MUERTA, rng.random()) if rng.random() < 0.18 else mezcla(VERDE, OLIVA, k)
            brizna(C * 0.62, 0.55, 3.0, mezcla(OSCURO, VERDE, k * 0.6), punta, 0.35, 0.16)
        for _ in range(4):
            a = rng.gauss(0, 0.3); h = C * rng.uniform(0.55, 0.8); x1 = min(C - M * 1.5, max(M * 1.5, bx + math.sin(a) * h)); y1 = max(M * 1.6, by - math.cos(a) * h)
            hoja(d, bx, by, x1, y1, rng.uniform(-0.12, 0.12) * h, 1.4 * SS, OLIVA, PAJA)
            d.ellipse([x1 - 2 * SS, y1 - 5 * SS, x1 + 2 * SS, y1 + 4 * SS], fill=PAJA + (255,))
    elif variante == 2:    # cardo
        for _ in range(5):
            a = rng.gauss(0, 0.22); h = C * rng.uniform(0.6, 0.92); x1 = min(C - M * 2, max(M * 2, bx + math.sin(a) * h)); y1 = max(M * 2.2, by - math.cos(a) * h)
            x0 = bx + rng.uniform(-0.05, 0.05) * C; cur = rng.uniform(-0.1, 0.1) * h
            hoja(d, x0, by, x1, y1, cur, 3.4 * SS, mezcla(OSCURO, PARDO, 0.5), mezcla(OLIVA, PARDO, 0.4), punta=0.8)
            for k in range(7):   # hojas espinosas a los lados del tallo
                t = 0.12 + 0.11 * k; px = x0 + (x1 - x0) * t + cur * 2 * t * (1 - t); py = by + (y1 - by) * t
                s = 1 if k % 2 else -1; L = C * rng.uniform(0.07, 0.16) * (1 - t * 0.6)
                hoja(d, px, py, min(C - M, max(M, px + s * L)), py - L * rng.uniform(0.2, 0.7), s * L * 0.2, 5.0 * SS, mezcla(OSCURO, VERDE, 0.5), mezcla(VERDE, OLIVA, rng.random()), 6)
            r = rng.uniform(3.2, 4.6) * SS
            d.ellipse([x1 - r, y1 - r, x1 + r, y1 + r], fill=mezcla(PARDO, (120, 92, 110), rng.random() * 0.6) + (255,))
            for k in range(9):   # las púas de la cabeza
                b = -math.pi / 2 + (k - 4) * 0.33; d.line([x1, y1, x1 + math.cos(b) * r * 1.7, y1 + math.sin(b) * r * 1.7], fill=PAJA + (255,), width=max(1, SS // 2 + 1))
        for _ in range(26):
            brizna(C * 0.3, 0.7, 2.6, OSCURO, mezcla(VERDE, OLIVA, rng.random()), 0.3, 0.14)
    else:                  # roseta pegada al suelo
        for _ in range(26):
            a = rng.uniform(-1.45, 1.45); L = C * rng.uniform(0.2, 0.44)
            x1 = min(C - M, max(M, bx + math.sin(a) * L)); y1 = by - math.cos(a) * L * 0.55 - C * 0.02
            hoja(d, bx + rng.uniform(-0.03, 0.03) * C, by, x1, y1, rng.uniform(-0.12, 0.12) * L, 9.0 * SS * rng.uniform(0.7, 1.2), mezcla(OSCURO, VERDE, 0.4), mezcla(VERDE, OLIVA, rng.random() * 0.7), 8, punta=1.2)
        for _ in range(3):
            a = rng.gauss(0, 0.25); h = C * rng.uniform(0.3, 0.52); x1 = bx + math.sin(a) * h; y1 = by - math.cos(a) * h
            hoja(d, bx, by, x1, y1, rng.uniform(-0.1, 0.1) * h, 1.3 * SS, OLIVA, PAJA)
            d.ellipse([x1 - 2.6 * SS, y1 - 2.6 * SS, x1 + 2.6 * SS, y1 + 2.6 * SS], fill=(176, 160, 70, 255))
    return im

def generar():
    rng = random.Random(22)
    big = Image.new('RGBA', (N * SS, N * SS), (0, 0, 0, 0))
    for v in range(4):
        big.paste(mata(v, rng), ((v % 2) * C, (v // 2) * C))
    a = np.asarray(big).astype(np.float64) / 255.0
    pre = a[..., :3] * a[..., 3:4]
    pre = pre.reshape(N, SS, N, SS, 3).mean((1, 3)); alfa = a[..., 3].reshape(N, SS, N, SS).mean((1, 3))
    rgb = np.where(alfa[..., None] > 0.004, pre / np.maximum(alfa[..., None], 1e-6), 0.0)
    # sombreado: más oscuro hacia la raíz de cada mata (las briznas se tapan unas a otras) y algo de mota
    yy = (np.arange(N) % (N // 2)) / (N // 2)
    rgb *= (0.4 + 0.6 * (1.0 - yy) ** 0.7)[:, None, None]
    rgb *= 0.86 + 0.28 * np.random.default_rng(22).random((N, N, 1))
    # el color se extiende a los huecos (alfa 0): al reducir la textura no entra negro por los bordes de las briznas
    lleno = alfa > 0.02; col = rgb.copy()
    for _ in range(24):
        if lleno.all(): break
        s = np.zeros_like(col); c = np.zeros(lleno.shape)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            s += np.roll(col * lleno[..., None], (dy, dx), (0, 1)); c += np.roll(lleno, (dy, dx), (0, 1))
        nuevo = (~lleno) & (c > 0)
        col[nuevo] = s[nuevo] / c[nuevo][:, None]; lleno = lleno | nuevo
    col[~lleno] = np.array([0.3, 0.36, 0.18])
    return (np.clip(np.concatenate([col, alfa[..., None]], -1), 0, 1) * 255 + 0.5).astype(np.uint8)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    im = generar()
    p = os.path.join(OUT, 'hierbajo.png')
    Image.fromarray(im, 'RGBA').save(p, optimize=True)
    print('hierbajo.png', os.path.getsize(p) // 1024, 'KB, cubre', round(float((im[..., 3] > 102).mean()) * 100, 1), '% de la superficie')
