"""Textura de tela metálica de simple torsión (la de las vallas de los recintos), repetible, con el hueco en el canal alfa.

Cada alambre baja en zigzag y se engancha con los dos vecinos en los quiebros: rombos de 8 cm, alambre galvanizado de 4,5 mm.
La textura cubre 32 x 32 cm (4 x 4 rombos). En Unreal la usa el material M_TelaMalla (tools/unreal/montar_base.py),
recortado (no translúcido): la valla deja ver a través de los huecos en vez de parecer un cristal.
Uso: python3 tools/texturas/tela_metalica.py   ->  assets/unreal/texturas_propias/tela_metalica.png
"""
import os
import numpy as np
from PIL import Image

N = 512            # píxeles de lado
CM = 32.0          # centímetros que cubre
W = N // 8         # ancho de la franja de cada alambre (medio rombo)
H = N // 8         # alto de medio zigzag
R = 4.5 / 10 / CM * N / 2   # radio del alambre en píxeles
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'assets', 'unreal', 'texturas_propias')

def generar(ss=4):
    n = N * ss
    y, x = np.mgrid[0:n, 0:n].astype(np.float64) / ss
    t = y / H
    tri = 2.0 * np.abs(2.0 * (t / 2.0 - np.floor(t / 2.0 + 0.5))) - 1.0      # onda triangular de -1 a 1, periodo 2H
    baja = np.floor(t) % 2                                                   # tramo que va hacia un lado o hacia el otro
    k = np.floor(x / W + 0.5)                                                # alambre más cercano
    best = np.full((n, n), 1e9); lado = np.zeros((n, n)); sentido = np.zeros((n, n))
    for dk in (-1, 0, 1):
        kk = k + dk
        sg = np.where(kk % 2 == 0, 1.0, -1.0)
        cx = kk * W + sg * (W / 2.0) * tri
        d = (x - cx) / np.sqrt(1.0 + (W / H) ** 2)                            # distancia perpendicular al tramo (45 grados)
        m = np.abs(d) < np.abs(best)
        best = np.where(m, d, best); sentido = np.where(m, sg * (1 - 2 * baja), sentido)
    a = np.clip((R - np.abs(best)) * ss + 0.5, 0.0, 1.0)                      # borde suavizado
    perfil = np.sqrt(np.clip(1.0 - (best / R) ** 2, 0.0, 1.0))                # alambre redondo: más claro en el lomo
    luz = 0.42 + 0.38 * perfil + 0.1 * sentido * (best / R)                   # cada tramo recibe la luz por un costado
    # enganche de los quiebros: un poco más grueso y más oscuro (sombra de un alambre sobre el otro)
    quiebro = np.exp(-((tri * tri - 1.0) / 0.12) ** 2)
    luz *= 1.0 - 0.25 * quiebro
    rng = np.random.default_rng(21)
    mota = rng.random((N // 8, N // 8)); mota = np.kron(mota, np.ones((8 * ss, 8 * ss)))
    oxido = np.clip((mota - 0.82) * 6.0, 0.0, 1.0)                           # motas de óxido en algún tramo
    gris = np.stack([luz * 0.78, luz * 0.8, luz * 0.8], -1)
    marron = np.stack([luz * 0.5, luz * 0.3, luz * 0.18], -1)
    rgb = gris * (1 - oxido[..., None] * 0.7) + marron * oxido[..., None] * 0.7
    img = np.concatenate([rgb, a[..., None]], -1)
    img = img.reshape(N, ss, N, ss, 4).mean((1, 3))
    # el color se extiende a los huecos (alfa 0) para que al reducir la textura no entre negro por los bordes
    img[..., :3] = np.where(img[..., 3:4] > 0.02, img[..., :3], np.array([0.5, 0.52, 0.52]))
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    im = generar()
    p = os.path.join(OUT, 'tela_metalica.png')
    Image.fromarray(im, 'RGBA').save(p, optimize=True)
    print('tela_metalica.png', os.path.getsize(p) // 1024, 'KB, cubre', round(float((im[..., 3] > 102).mean()) * 100, 1), '% de la superficie')
