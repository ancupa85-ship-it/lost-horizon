"""Piezas de tela para el atrezo que no existen en Poly Haven: un capote colgado de un gancho de pared.

Uso:  python3 tools/vestuario/atrezo_tela.py      -> assets/unreal/atrezo_propio/capote_colgado.glb
Malla estática (sin esqueleto), en metros, glTF con Y arriba. Origen: el gancho, en la pared; la tela cuelga
hacia abajo (-Y de glTF) y sobresale de la pared hacia +Z de glTF (-Y en Blender, +Y… según importe Unreal: comprobar al colocar). Material a dos caras con la lona del capote.
"""
import os, sys, io, json, struct
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import texturas

ROOT = os.path.dirname(os.path.dirname(HERE))
DST = os.path.join(ROOT, 'assets', 'unreal', 'atrezo_propio')


def normales(P, T):
    n = np.zeros_like(P)
    f = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    for k in range(3):
        np.add.at(n, T[:, k], f)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)


def escribir(path, mallas, mats):
    """mallas: [(nombre, P, N, UV, T, material)], mats: [(nombre, imagen color, imagen relieve, rugosidad, dos caras)]"""
    buf = bytearray()
    j = dict(asset=dict(version='2.0', generator='lost-horizon atrezo_tela'), scene=0, scenes=[dict(nodes=[])], nodes=[], meshes=[],
             accessors=[], bufferViews=[], buffers=[{}], materials=[], textures=[], images=[], samplers=[dict(magFilter=9729, minFilter=9987, wrapS=10497, wrapT=10497)])

    def view(b, target=None):
        while len(buf) % 4:
            buf.append(0)
        v = dict(buffer=0, byteOffset=len(buf), byteLength=len(b))
        if target:
            v['target'] = target
        buf.extend(b)
        j['bufferViews'].append(v)
        return len(j['bufferViews']) - 1

    def acc(a, tipo, comp, target, mm=False):
        d = dict(bufferView=view(a.tobytes(), target), componentType=comp, count=len(a), type=tipo)
        if mm:
            d['min'], d['max'] = a.min(0).tolist(), a.max(0).tolist()
        j['accessors'].append(d)
        return len(j['accessors']) - 1

    def imagen(im, nombre):
        b = io.BytesIO()
        im.convert('RGB').save(b, 'JPEG', quality=88)
        j['images'].append(dict(bufferView=view(b.getvalue()), mimeType='image/jpeg', name=nombre))
        j['textures'].append(dict(sampler=0, source=len(j['images']) - 1))
        return len(j['textures']) - 1

    for nombre, col, rel, rug, doble in mats:
        m = dict(name=nombre, pbrMetallicRoughness=dict(baseColorTexture=dict(index=imagen(col, nombre + '_color')), roughnessFactor=rug, metallicFactor=0.0), doubleSided=doble)
        if rel is not None:
            m['normalTexture'] = dict(index=imagen(rel, nombre + '_relieve'), scale=0.6)
        j['materials'].append(m)
    for nombre, P, N, UV, T, mat in mallas:
        prim = dict(attributes=dict(POSITION=acc(P.astype('<f4'), 'VEC3', 5126, 34962, True), NORMAL=acc(N.astype('<f4'), 'VEC3', 5126, 34962),
                                    TEXCOORD_0=acc(UV.astype('<f4'), 'VEC2', 5126, 34962)),
                    indices=acc(T.astype('<u2').reshape(-1), 'SCALAR', 5123, 34963), material=mat)
        j['meshes'].append(dict(name=nombre, primitives=[prim]))
        j['nodes'].append(dict(name=nombre, mesh=len(j['meshes']) - 1))
        j['scenes'][0]['nodes'].append(len(j['nodes']) - 1)
    while len(buf) % 4:
        buf.append(0)
    j['buffers'][0]['byteLength'] = len(buf)
    js = json.dumps(j, separators=(',', ':')).encode()
    js += b' ' * (-len(js) % 4)
    with open(path, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(buf)))
        f.write(struct.pack('<I4s', len(js), b'JSON') + js)
        f.write(struct.pack('<I4s', len(buf), b'BIN\0') + bytes(buf))
    return os.path.getsize(path)


def capote_colgado(seed=7, largo=1.18):
    """Capote colgado de la capucha en un gancho: arriba recogido, abajo abierto en pliegues gruesos.
    Trabajo con Z arriba, +Y fuera de la pared, X a lo ancho; al final se pasa a glTF."""
    rng = np.random.default_rng(seed)
    nr, nc = 34, 96
    t = np.linspace(0, 1, nr)[:, None]              # 0 gancho, 1 bajo
    u = np.linspace(-1, 1, nc)[None, :]             # de un borde a otro, por delante
    sm = lambda x: np.clip(x, 0, 1) ** 2 * (3 - 2 * np.clip(x, 0, 1))
    # la capucha es una bolsa floja arriba; debajo la tela cae recogida y casi recta, abriéndose poco
    capu = np.exp(-((t - 0.07) / 0.05) ** 2)
    caida = sm((t - 0.10) / 0.22)
    ancho = 0.034 + 0.026 * capu + 0.150 * caida + 0.055 * t ** 1.5
    fondo = 0.024 + 0.022 * capu + 0.050 * caida + 0.030 * t
    # pliegues de caída: crestas redondas y valles estrechos, nacen del cuello, con anchos desiguales
    f1, f2, f3 = rng.uniform(0, 2 * np.pi, 3)
    uu = u + 0.10 * np.sin(u * 2.3 + f3) + 0.035 * (t - 0.5) * np.sin(u * 5.0 + f1)
    cresta = np.abs(np.sin(uu * 8.2 + f1)) ** 0.6 * 0.75 + np.abs(np.sin(uu * 4.1 + f2)) ** 0.8 * 0.45
    amp = sm((t - 0.10) / 0.30)
    arruga = (np.sin(t * 38 + u * 6 + f2) * np.sin(u * 17 + f1)) * 0.25 * capu     # la capucha, arrugada
    ang = u * (np.pi * 0.5) * 1.10                   # algo más que media vuelta: los bordes vuelven hacia la pared
    X = np.sin(ang) * ancho * (1.0 - 0.10 * amp * cresta) + 0.012 * t * np.sin(f3)   # cuelga un poco torcido
    Y = np.maximum(np.cos(ang), -0.10) * fondo * (0.55 + 0.95 * amp * cresta + arruga + (1 - amp) * 0.45) + 0.010
    Y = np.maximum(Y, 0.004)                         # nunca dentro de la pared
    # el bajo no es recto: un pico más largo a un lado y ondas
    Z = -t * largo * (1.0 + 0.07 * (1 - (u - 0.25) ** 2) * t + 0.020 * np.sin(u * 9 + f2) * t)
    P = np.stack([X + 0.0 * t, Y + 0.0 * t, Z + 0.0 * u], -1).reshape(-1, 3)
    UV = np.stack([(u * 0.5 + 0.5) * 1.6 + 0 * t, t * 2.4 + 0 * u], -1).reshape(-1, 2)
    i = np.arange(nr * nc).reshape(nr, nc)
    a, b, c, d = i[:-1, :-1].ravel(), i[:-1, 1:].ravel(), i[1:, 1:].ravel(), i[1:, :-1].ravel()
    T = np.r_[np.c_[a, d, b], np.c_[b, d, c]]
    return P, UV, T


def gancho():
    """Alcayata de hierro: barra que sale de la pared y sube."""
    n = 8
    ca = np.arange(n) / n * 2 * np.pi
    eje = np.array([[0, 0.0, 0.0], [0, 0.045, 0.0], [0, 0.062, 0.012], [0, 0.066, 0.040]])
    anillos = []
    for k, c in enumerate(eje):
        d = eje[min(k + 1, len(eje) - 1)] - eje[max(k - 1, 0)]
        d /= np.linalg.norm(d)
        s = np.array([1.0, 0, 0])
        w = np.cross(d, s)
        anillos.append(c + 0.006 * (np.cos(ca)[:, None] * s + np.sin(ca)[:, None] * w))
    P = np.concatenate(anillos)
    T = []
    for k in range(len(eje) - 1):
        for q in range(n):
            a, b = k * n + q, k * n + (q + 1) % n
            T += [[a, a + n, b], [b, a + n, b + n]]
    UV = np.c_[P[:, 0] * 20, P[:, 1] * 20]
    return P, UV, np.array(T)


def yup(P):
    return np.c_[P[:, 0], P[:, 2], -P[:, 1]]


def main():
    os.makedirs(DST, exist_ok=True)
    col, rel = texturas.capote()
    cc, cr = texturas.casco()
    P, UV, T = capote_colgado()
    Pg, UVg, Tg = gancho()
    P[:, 2] += 0.030   # la capucha abraza el gancho
    # como en vestir.py, delante es -Y: la tela sobresale de la pared hacia -Y (se refleja y se invierte el sentido de las caras)
    P[:, 1] *= -1; Pg[:, 1] *= -1
    T, Tg = T[:, ::-1], Tg[:, ::-1]
    mallas = [('capote_colgado', yup(P), yup(normales(P, T)), UV, T, 0), ('gancho', yup(Pg), yup(normales(Pg, Tg)), UVg, Tg, 1)]
    n = escribir(os.path.join(DST, 'capote_colgado.glb'), mallas, [('capote', col, rel, 0.78, True), ('hierro', cc, None, 0.6, False)])
    print('capote_colgado.glb', '%.0f KB' % (n / 1024), len(P), 'vértices', len(T), 'triángulos')


if __name__ == '__main__':
    main()
