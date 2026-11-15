"""Textura de estrellas para el cielo nocturno de Tarsis (tanda 25), repetible.

La primera versión salió de papel pintado: 1500 puntos gordos y casi todos igual de visibles, repetidos diez veces
sobre la bóveda. Un cielo de verdad es al revés: por cada estrella que se ve bien hay decenas que apenas se adivinan
(el número crece como el brillo elevado a -1,25), y ninguna es un disco. Aquí:
  - 2048 px para una sola repetición de casi todo el cielo (no se ve el dibujo repetido);
  - brillo por ley de potencias: de 5200 puntos, unos 20 fuertes, 150 medianos y el resto un polvillo;
  - cada punto, una manchita gaussiana de poco más de un píxel (a media resolución y con el reescalado temporal del
    motor, un punto de un solo píxel parpadea), que casi no crece con el brillo;
  - el canal guarda la RAÍZ del brillo (8 bits no dan para el polvillo en lineal): el material la eleva al cuadrado.
Canal único (gris): el color y la fuerza los pone M_Cielo (tools/unreal/cielo.py).
Uso: python3 tools/texturas/estrellas.py   ->  assets/unreal/texturas_propias/estrellas.png
"""
import os
import numpy as np
from PIL import Image

N = 2048
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets', 'unreal', 'texturas_propias')


def generar(semilla=2526, cuantas=5200, minimo=0.005):
    """Devuelve el brillo lineal (0-1) de cada píxel."""
    rng = np.random.default_rng(semilla)
    a = np.zeros((N, N), np.float64)
    xs, ys = rng.uniform(0, N, cuantas), rng.uniform(0, N, cuantas)
    # brillo: N(>F) ~ F^-1,25 (cada magnitud más débil hay unas 3 veces más estrellas)
    b = np.clip(minimo / rng.uniform(0.0, 1.0, cuantas) ** 0.8, minimo, 1.0)
    for x, y, k in zip(xs, ys, b):
        s = 0.60 + 0.20 * k ** 0.5       # 0,80 + 0,45 hasta el ajuste 25c: las fuertes salían discos de 8 a 10 px
        r = int(np.ceil(s * 3.5))
        x0, y0 = int(np.floor(x)), int(np.floor(y))
        jj, ii = np.mgrid[y0 - r:y0 + r + 1, x0 - r:x0 + r + 1]
        g = k * np.exp(-((ii - x) ** 2 + (jj - y) ** 2) / (2.0 * s * s))
        a[jj % N, ii % N] = np.maximum(a[jj % N, ii % N], g)       # módulo: la textura casa por los cuatro lados
    return np.clip(a, 0.0, 1.0)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    a = generar()
    Image.fromarray((np.sqrt(a) * 255 + 0.5).astype(np.uint8), 'L').save(os.path.join(OUT, 'estrellas.png'), optimize=True)
    print('estrellas.png', a.shape, 'puntos fuertes (> 0,3): %d, medianos (> 0,05): %d' % ((a > 0.3).sum() // 8, (a > 0.05).sum() // 6))
