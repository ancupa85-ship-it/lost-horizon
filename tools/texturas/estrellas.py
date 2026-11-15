"""Textura de estrellas para el cielo nocturno de Tarsis (tanda 25), repetible.

Puntos de brillo muy desigual (muchas débiles, pocas fuertes), cada uno una manchita gaussiana de 2-3 píxeles: a media
resolución y con el reescalado temporal del motor, un punto de un solo píxel parpadea o desaparece. Canal único (gris):
el color y la fuerza los pone el material M_Cielo (tools/unreal/cielo.py), que la repite sobre la bóveda.
Uso: python3 tools/texturas/estrellas.py   ->  assets/unreal/texturas_propias/estrellas.png
"""
import os
import numpy as np
from PIL import Image

N = 1024
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets', 'unreal', 'texturas_propias')


def generar(semilla=2525, cuantas=1500):
    rng = np.random.default_rng(semilla)
    a = np.zeros((N, N), np.float64)
    xs, ys = rng.uniform(0, N, cuantas), rng.uniform(0, N, cuantas)
    # brillo: ley de potencias (por cada estrella fuerte, muchas débiles); el tamaño crece poco con el brillo
    b = np.clip(0.07 / rng.uniform(0.0, 1.0, cuantas) ** 0.75, 0.07, 1.0)
    for x, y, k in zip(xs, ys, b):
        s = 0.75 + 0.75 * k
        r = int(np.ceil(s * 3.5))
        x0, y0 = int(np.floor(x)), int(np.floor(y))
        jj, ii = np.mgrid[y0 - r:y0 + r + 1, x0 - r:x0 + r + 1]
        g = k * np.exp(-((ii - x) ** 2 + (jj - y) ** 2) / (2.0 * s * s))
        a[jj % N, ii % N] = np.maximum(a[jj % N, ii % N], g)       # módulo: la textura casa por los cuatro lados
    return np.clip(a, 0.0, 1.0)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    a = generar()
    Image.fromarray((a * 255 + 0.5).astype(np.uint8), 'L').save(os.path.join(OUT, 'estrellas.png'), optimize=True)
    print('estrellas.png', a.shape, 'cubierto %.2f %%' % (100.0 * (a > 0.05).mean()))
