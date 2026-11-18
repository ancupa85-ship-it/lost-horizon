"""Viste a los guardias con equipo que les tapa la cara: pasamontañas, guantes, casco, capote con capucha,
braga de lana, faldón de guerrera, correaje y gorra. Pilar «rostros que no se ven» de la dirección artística.

Lee assets/unreal/personas/sin_equipo/<nombre>.glb (la persona de MakeHuman tal cual, con esqueleto y animaciones)
y escribe assets/unreal/personas/<nombre>.glb con las prendas añadidas como mallas del mismo esqueleto. No pasa por
Blender: el esqueleto y las animaciones quedan byte a byte como estaban. Las prendas se construyen con numpy a partir
de las medidas de cada cuerpo (cabeza, hombros, cintura), y se pesan copiando los pesos del cuerpo que tienen debajo.

Uso:  python3 tools/vestuario/vestir.py [nombre ...]      (sin nombres: todos los de EQUIPO)
Ejes de trabajo: Z arriba, -Y delante, +X izquierda del personaje (como en Blender); al escribir se pasa a glTF.
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from glb import Glb
import texturas

ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, 'assets', 'unreal', 'personas', 'sin_equipo')
DST = os.path.join(ROOT, 'assets', 'unreal', 'personas')

# Qué lleva cada uno. La silueta distingue a cada guardia de lejos y a oscuras.
EQUIPO = {
    'ibarra': dict(cabeza='capucha', capote=True),                          # el veterano del patio norte: capote con la capucha puesta
    'moya': dict(cabeza='casco', braga=True, faldon=True, correaje=True),   # patio central: casco y correaje completo
    'peris': dict(cabeza='gorra', braga=True, faldon=True, cinturon=True),  # cuartelero: gorra de faena, sin casco
    'vega': dict(base='moya', cabeza='casco', braga=True, capote='sin_capucha'),              # portón: casco y capote
    'ramos': dict(base='peris', cabeza='casco', braga=True, faldon=True, cinturon=True),      # el recluta: casco que le viene grande y poco más
    'centinela': dict(base='ibarra', cabeza='casco', braga=True, capote='sin_capucha'),       # los dos de las torres: casco y capote
}


def zup(P):
    return np.c_[P[:, 0], -P[:, 2], P[:, 1]]


def yup(P):
    return np.c_[P[:, 0], P[:, 2], -P[:, 1]]


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def sstep(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def weld(P, tol=2e-5):
    key = np.round(P / tol).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return first, inv.reshape(-1)


def vnormals(P, T):
    """Normales suaves, soldando por posición (las costuras de UV no hacen arista)."""
    first, inv = weld(P)
    Tw = inv[T]
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    acc = np.zeros((len(first), 3))
    for k in range(3):
        np.add.at(acc, Tw[:, k], fn)
    return unit(acc)[inv]


def smooth(P, T, A, iters, lam=0.5, fixed=None):
    """Suavizado laplaciano de un atributo A (n,k) sobre la malla soldada por posición."""
    first, inv = weld(P)
    Tw = inv[T]
    n = len(first)
    Aw = np.zeros((n, A.shape[1]))
    cnt = np.zeros(n)
    np.add.at(Aw, inv, A)
    np.add.at(cnt, inv, 1)
    Aw /= cnt[:, None]
    e = np.r_[Tw[:, [0, 1]], Tw[:, [1, 2]], Tw[:, [2, 0]]]
    e = np.unique(np.sort(e, axis=1), axis=0)
    e = e[e[:, 0] != e[:, 1]]
    deg = np.zeros(n)
    np.add.at(deg, e[:, 0], 1)
    np.add.at(deg, e[:, 1], 1)
    deg = np.maximum(deg, 1)
    fx = None if fixed is None else np.bincount(inv, weights=fixed.astype(float), minlength=n) > 0
    for _ in range(iters):
        s = np.zeros_like(Aw)
        np.add.at(s, e[:, 0], Aw[e[:, 1]])
        np.add.at(s, e[:, 1], Aw[e[:, 0]])
        new = Aw + lam * (s / deg[:, None] - Aw)
        if fx is not None:
            new[fx] = Aw[fx]
        Aw = new
    return Aw[inv]


def catmull(C, m):
    """Interpola filas de control C (k, ...) con Catmull-Rom, m tramos por intervalo; devuelve (k-1)*m+1 filas."""
    C = np.asarray(C, float)
    out = []
    K = len(C)
    for i in range(K - 1):
        p0, p1, p2, p3 = C[max(i - 1, 0)], C[i], C[i + 1], C[min(i + 2, K - 1)]
        for s in range(m):
            t = s / m
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(C[-1])
    return np.array(out)


def grid_tris(nr, nc, closed=False, skip=None):
    """Triángulos de una rejilla de nr filas x nc columnas (índice = fila*nc + col)."""
    T = []
    for r in range(nr - 1):
        for c in range(nc - 1 if not closed else nc):
            if skip is not None and skip(r, c):
                continue
            a, b = r * nc + c, r * nc + (c + 1) % nc
            d, e = a + nc, b + nc
            T += [(a, d, b), (b, d, e)]
    return np.array(T, int).reshape(-1, 3)


def rbox(size, r=0.012, n=4):
    """Caja de esquinas redondeadas centrada en el origen (bolsillos, cartucheras)."""
    h = np.array(size, float) / 2
    P, T = [], []
    lin = np.linspace(-1, 1, n + 1)
    for ax in range(3):
        for sg in (-1, 1):
            u, v = [a for a in range(3) if a != ax]
            base = len(P)
            for i in lin:
                for j in lin:
                    p = np.zeros(3)
                    p[ax] = sg * h[ax]
                    p[u] = i * h[u]
                    p[v] = j * h[v]
                    core = np.clip(p, -(h - r), h - r)
                    d = p - core
                    nd = np.linalg.norm(d)
                    P.append(core + (d / nd * r if nd > 1e-9 else 0))
            for i in range(n):
                for j in range(n):
                    a = base + i * (n + 1) + j
                    q = [a, a + 1, a + n + 2, a + n + 1]
                    flip = (sg > 0) ^ (ax == 1)
                    T += [(q[0], q[1], q[2]), (q[0], q[2], q[3])] if flip else [(q[0], q[2], q[1]), (q[0], q[3], q[2])]
    return np.array(P), np.array(T, int)


class Persona:
    def __init__(self, nombre, base=None):
        self.nombre = nombre
        self.g = g = Glb(os.path.join(SRC, (base or nombre) + '.glb'))
        j = g.j
        self.quitadas = g.remove_mesh_nodes(lambda s: 'short' in s or 'hair' in s)   # el pelo: va tapado
        skin = j['skins'][0]
        self.bones = [j['nodes'][k]['name'] for k in skin['joints']]
        self.bi = {n: i for i, n in enumerate(self.bones)}
        self.nb = len(self.bones)
        ibm = g.acc(skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1).astype(float)
        self.J = {n: zup(np.linalg.inv(ibm[i])[:3, 3][None])[0] for i, n in enumerate(self.bones)}
        self.parent = [i for i, n in enumerate(j['nodes']) if any('mesh' in j['nodes'][c] for c in n.get('children', []))][0]
        # sólidos del cuerpo: por material (sin el prefijo del nombre)
        self.parts = {}
        for n in j['nodes']:
            if 'mesh' not in n:
                continue
            for p in j['meshes'][n['mesh']]['primitives']:
                mat = j['materials'][p['material']]['name'].split('_', 1)[1]
                P = zup(g.acc(p['attributes']['POSITION']).astype(float))
                Jn = g.acc(p['attributes']['JOINTS_0']).astype(int)
                Wn = g.acc(p['attributes']['WEIGHTS_0']).astype(float)
                W = np.zeros((len(P), self.nb))
                for k in range(4):
                    np.add.at(W, (np.arange(len(P)), Jn[:, k]), Wn[:, k])
                W /= np.maximum(W.sum(1, keepdims=True), 1e-9)
                self.parts[mat] = dict(P=P, W=W, T=g.acc(p['indices']).reshape(-1, 3).astype(int), mat=p['material'])
        piel = [k for k in self.parts if k in ('body', 'lips', 'fingernails', 'ears')]
        ropa = [k for k in self.parts if 'suit' in k or 'boots' in k]
        self.piel = self._join(piel)
        self.solido = self._join(piel + ropa)
        self.mats = {}
        self._medidas()

    def _join(self, keys):
        P, W, T, o = [], [], [], 0
        for k in keys:
            q = self.parts[k]
            P.append(q['P'])
            W.append(q['W'])
            T.append(q['T'] + o)
            o += len(q['P'])
        return dict(P=np.vstack(P), W=np.vstack(W), T=np.vstack(T))

    def wsum(self, W, pref):
        idx = [i for i, n in enumerate(self.bones) if n.startswith(pref)]
        return W[:, idx].sum(1)

    def _medidas(self):
        P, W = self.piel['P'], self.piel['W']
        ojos = [v for k, v in self.parts.items() if 'low-poly' in k or 'eye' == k][0]['P']
        m = self.m = {}
        m['ojo_z'] = (ojos[:, 2].min() + ojos[:, 2].max()) / 2
        m['ojo_x'] = np.abs(ojos[:, 0]).max()
        m['ojo_y'] = ojos[:, 1].min()
        head = P[W[:, self.bi['head']] > 0.5]
        craneo = head[head[:, 2] > m['ojo_z'] + 0.03]
        m['cx'] = (craneo[:, 0].min() + craneo[:, 0].max()) / 2
        m['hw'] = (craneo[:, 0].max() - craneo[:, 0].min()) / 2
        m['cy'] = (craneo[:, 1].min() + craneo[:, 1].max()) / 2
        m['hd'] = (craneo[:, 1].max() - craneo[:, 1].min()) / 2
        m['top'] = head[:, 2].max()
        cara = head[head[:, 1] < m['cy'] - m['hd'] * 0.45]
        m['menton_z'] = cara[:, 2].min()
        m['cara_y'] = cara[:, 1].min()
        # el torso sin brazos, para apoyar correas y faldón
        S = self.solido
        brazo = sum(self.wsum(S['W'], p) for p in ('upperarm', 'lowerarm', 'hand', 'index', 'middle', 'ring', 'pinky', 'thumb'))
        keep = (brazo[S['T']] < 0.5).all(1)
        self.torso = dict(P=S['P'], T=S['T'][keep])
        self._tri = {}
        # OJO: el esqueleto es el mismo para todos los cuerpos y sus articulaciones no caen donde las de la malla
        # (hasta 8 cm en codos y hombros de los altos). Las prendas se miden sobre la malla, no sobre los huesos.
        m['H'] = S['P'][:, 2].max()
        m['cintura'] = 0.575 * m['H']
        u = S['P'][S['W'][:, self.bi['upperarm_l']] > 0.6]
        l = S['P'][S['W'][:, self.bi['lowerarm_l']] > 0.6]
        m['hombro'] = u[u[:, 0] <= np.quantile(u[:, 0], 0.25)].mean(0)
        m['codo'] = np.vstack([u[u[:, 0] >= np.quantile(u[:, 0], 0.8)], l[l[:, 0] <= np.quantile(l[:, 0], 0.2)]]).mean(0)
        pc = self.piel
        hn = pc['W'][:, self.bi['head']] + pc['W'][:, self.bi['neck_01']]
        self.cabeza = dict(P=pc['P'], T=pc['T'][(hn[pc['T']] > 0.3).all(1)])
        self.cuello_pts = pc['P'][np.unique(self.cabeza['T'])]
        self.sin_cabeza = (S['W'][:, self.bi['head']] + S['W'][:, self.bi['neck_01']]) < 0.3

    def ztop(self, x, dx=0.025):
        """Altura de la parte de arriba del cuerpo (hombro, brazo) a una distancia x del eje."""
        S = self.solido['P'][self.sin_cabeza]
        s = S[np.abs(S[:, 0] - (self.m['cx'] + x)) < dx]
        return s[:, 2].max()

    def eje_cuello(self, z, dz=0.022):
        q = self.cuello_pts
        s = q[np.abs(q[:, 2] - z) < dz]
        if len(s) < 6:
            zz = np.clip(z, q[:, 2].min() + dz, q[:, 2].max() - dz)
            s = q[np.abs(q[:, 2] - zz) < dz]
        return np.array([(s[:, 0].min() + s[:, 0].max()) / 2, (s[:, 1].min() + s[:, 1].max()) / 2, z])

    # ---- rayos contra el cuerpo
    def ray(self, o, d, quien='solido', far=True, tmax=1.0):
        if quien not in self._tri:
            q = getattr(self, quien)
            V0 = q['P'][q['T'][:, 0]]
            self._tri[quien] = (V0, q['P'][q['T'][:, 1]] - V0, q['P'][q['T'][:, 2]] - V0)
        V0, E1, E2 = self._tri[quien]
        h = np.cross(d, E2)
        a = (E1 * h).sum(1)
        ok = np.abs(a) > 1e-12
        f = 1.0 / np.where(ok, a, 1.0)
        s = o - V0
        u = f * (s * h).sum(1)
        q = np.cross(s, E1)
        v = f * (q @ d)
        t = f * (E2 * q).sum(1)
        hit = ok & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6) & (t > 1e-6) & (t < tmax)
        if not hit.any():
            return None
        return t[hit].max() if far else t[hit].min()

    def centro(self, z, dz=0.03):
        P = self.torso['P'][np.unique(self.torso['T'])]
        s = P[np.abs(P[:, 2] - z) < dz]
        return np.array([(s[:, 0].min() + s[:, 0].max()) / 2, (s[:, 1].min() + s[:, 1].max()) / 2, z])

    def radio(self, z, phi, quien='torso', c=None):
        """Distancia del eje del cuerpo a su superficie exterior a la altura z y en el rumbo phi (0 = delante)."""
        c = self.centro(z) if c is None else c
        return self.ray(c, np.array([math.sin(phi), -math.cos(phi), 0.0]), quien)

    # ---- pesos
    def pesos(self, Q, k=8, src=None):
        S = self.solido if src is None else src
        out = np.zeros((len(Q), self.nb))
        for a in range(0, len(Q), 256):
            q = Q[a:a + 256]
            d2 = ((q[:, None, :] - S['P'][None]) ** 2).sum(-1)
            idx = np.argpartition(d2, k, axis=1)[:, :k]
            w = 1.0 / (np.take_along_axis(d2, idx, 1) + 1e-5)
            out[a:a + 256] = (w[:, :, None] * S['W'][idx]).sum(1) / w.sum(1)[:, None]
        return out

    def separar(self, P, minimo=0.012, centro=None, iters=3):
        """Empuja hacia fuera los puntos que quedaron a menos de `minimo` del cuerpo (en reposo)."""
        S = self.solido['P']
        P = P.copy()
        for _ in range(iters):
            for a in range(0, len(P), 256):
                q = P[a:a + 256]
                d2 = ((q[:, None, :] - S[None]) ** 2).sum(-1)
                i = d2.argmin(1)
                d = np.sqrt(d2[np.arange(len(q)), i])
                cerca = d < minimo
                if cerca.any():
                    c = np.array([0.0, 0.0, 0.0]) if centro is None else centro
                    out = q[cerca] - np.c_[np.full(cerca.sum(), c[0]), np.full(cerca.sum(), c[1]), q[cerca][:, 2]]
                    out = unit(out)
                    q[cerca] += out * (minimo - d[cerca])[:, None]
                    P[a:a + 256] = q
        return P

    # ---- materiales
    def material(self, clave):
        if clave in self.mats:
            return self.mats[clave]
        g = self.g
        defs = {'capote': (texturas.capote, 0.48, True, 1.0), 'pano': (texturas.pano, 0.86, True, 0.8), 'lana': (texturas.lana, 0.96, False, 1.0),
                'casco': (texturas.casco, 0.55, False, 0.6), 'lona': (texturas.lona, 0.9, True, 1.0), 'cuero': (texturas.cuero, 0.6, False, 0.7)}
        fn, rough, doble, ns = defs[clave]
        col, nor = fn()
        tc = g.add_image(col, 'tx_' + clave, jpeg=84)
        tn = g.add_image(nor, 'tn_' + clave, jpeg=88)
        self.mats[clave] = g.add_material(self.nombre + '_' + clave, tex=tc, normal=tn, rough=rough, double=doble, nscale=ns)
        return self.mats[clave]

    def emit(self, nombre, P, UV, T, W, mat, N=None):
        T = np.asarray(T, int)
        area = np.linalg.norm(np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]]), axis=1)
        T = T[area > 1e-10]
        if N is None:
            N = vnormals(P, T)
        used = np.unique(T)
        mp = np.full(len(P), -1)
        mp[used] = np.arange(len(used))
        P, N, UV, W, T = P[used], N[used], UV[used], W[used], mp[T]
        idx = np.argsort(-W, axis=1)[:, :4]
        w4 = np.take_along_axis(W, idx, 1)
        w4[w4 < 0.01] = 0
        w4 /= w4.sum(1, keepdims=True)
        idx[w4 == 0] = 0
        self.g.add_skinned_mesh(self.nombre + '_' + nombre, yup(P), yup(N), UV, idx, w4, T, self.material(mat), self.parent)
        print('   %-12s %5d vértices %5d triángulos (%s)' % (nombre, len(P), len(T), mat))

    def rigido(self, n, hueso):
        W = np.zeros((n, self.nb))
        W[:, self.bi[hueso]] = 1
        return W

    # ================================================================ prendas
    def funda(self, sel, off, sub=None, suave=2):
        """Segunda piel: copia las caras de la piel que cumplen sel(P, W) y las saca `off` metros hacia fuera."""
        S = self.piel
        vs = sel(S['P'], S['W'])
        T = S['T'][vs[S['T']].all(1)]
        first, inv = weld(S['P'])
        P, W, T = S['P'][first], S['W'][first], inv[T]
        used = np.unique(T)
        mp = np.full(len(P), -1)
        mp[used] = np.arange(len(used))
        P, W, T = P[used], W[used], mp[T]
        if sub is not None:
            for _ in range(sub[1]):
                P, W, T = subdividir(P, W, T, sub[0](P))
        N = vnormals(P, T)
        P0 = P.copy()
        Q = P + N * off
        if suave:
            Q = smooth(Q, T, Q, suave, 0.5)
        d = ((Q - P0) * N).sum(1)
        Q += N * np.maximum(off * 0.8 - d, 0)[:, None]
        return Q, W, T

    def pasamontanas(self):
        m = self.m
        zc, hh, hw = m['ojo_z'] + 0.001, 0.0145, m['ojo_x'] + 0.006   # rendija de los ojos: cápsula tumbada
        yl = m['cy'] - m['hd'] * 0.2

        def sd(P):
            dx = np.maximum(np.abs(P[:, 0] - m['cx']) - (hw - hh), 0)
            return np.where(P[:, 1] < yl, np.hypot(dx, P[:, 2] - zc) - hh, 1.0)
        cuello = self.ztop(m['hw'] * 0.95) - 0.06
        P, W, T = self.funda(lambda P, W: P[:, 2] > cuello, 0.0045, sub=(lambda P: sd(P) < 0.022, 2))
        s = sd(P)
        dentro = s[T].mean(1) < 0
        borde = np.zeros(len(P), bool)
        borde[np.unique(T[dentro])] = True
        T = T[~dentro]
        mover = borde & np.isin(np.arange(len(P)), np.unique(T))
        # los vértices del borde se llevan a la curva de la rendija (contorno limpio en vez de dientes de sierra)
        dx = np.abs(P[:, 0] - m['cx']) - (hw - hh)
        gx = np.where(dx > 0, np.sign(P[:, 0] - m['cx']) * dx, 0.0)
        gz = P[:, 2] - zc
        gn = np.maximum(np.hypot(gx, gz), 1e-9)
        P[mover, 0] -= (s * gx / gn)[mover]
        P[mover, 2] -= (s * gz / gn)[mover]
        ang = np.arctan2(P[:, 0] - m['cx'], -(P[:, 1] - m['cy']))
        UV = np.c_[ang / (2 * np.pi) * 5.0, P[:, 2] * 9.0]
        self.emit('pasamontanas', P, UV, T, W, 'lana')

    def guantes(self):
        dedos = ('hand', 'index', 'middle', 'ring', 'pinky', 'thumb')

        def sel(P, W):
            mano = sum(self.wsum(W, d) for d in dedos) > 0.45
            # puño del guante: sube 6 cm por el antebrazo para que no asome piel entre el guante y la manga
            ante = np.flatnonzero(~mano & (self.wsum(W, 'lowerarm') > 0.3))
            H = P[mano]
            d = np.concatenate([np.sqrt(((P[ante[i:i + 500], None, :] - H[None]) ** 2).sum(2)).min(1) for i in range(0, len(ante), 500)])
            mano[ante[d < 0.06]] = True
            return mano
        P, W, T = self.funda(sel, 0.0035, suave=0)
        UV = np.c_[P[:, 1] * 6.0, P[:, 2] * 6.0]
        self.emit('guantes', P, UV, T, W, 'cuero')

    def _borde_casco(self, phi):
        m = self.m
        c = np.cos(phi)
        wf, wb, ws = np.maximum(c, 0) ** 2, np.maximum(-c, 0) ** 2, np.sin(phi) ** 2
        return wf * (m['ojo_z'] + 0.040) + ws * (m['ojo_z'] + 0.002) + wb * (m['ojo_z'] - 0.022)

    def casco(self):
        """Casco de acero tipo M1: cúpula alta, visera corta, ala trasera; con forro interior y barboquejo."""
        m = self.m
        nc, nr = 40, 11
        phi = np.arange(nc + 1) / nc * 2 * np.pi
        zr = self._borde_casco(phi)
        c = np.cos(phi)
        vuelo = np.maximum(c, 0) ** 2 * 0.10 + np.sin(phi) ** 2 * 0.035 + np.maximum(-c, 0) ** 2 * 0.075

        def capa(rx, ry, ztop, alfas, zoff=0.0):
            rows = []
            R = 1.0 / np.sqrt((np.sin(phi) / rx) ** 2 + (np.cos(phi) / ry) ** 2)
            for a in alfas:
                h = math.sin(a * math.pi / 2) ** 0.72
                v = math.cos(a * math.pi / 2) ** 0.92 if a < 1 else 0.0
                r = R * h * (1 + vuelo * float(sstep(0.78, 1.0, a)))
                rows.append(np.c_[m['cx'] + r * np.sin(phi), m['cy'] - 0.004 - r * np.cos(phi), zr + zoff + (ztop - zr) * v])
            return rows
        rx, ry, zt = m['hw'] + 0.033, m['hd'] + 0.034, m['top'] + 0.032
        fuera = capa(rx, ry, zt, np.linspace(0, 1, nr))
        dentro = capa(rx - 0.008, ry - 0.008, zt - 0.008, np.linspace(1, 0.35, 6), zoff=0.004)
        rows = fuera + dentro
        P = np.vstack(rows)
        nrr = len(rows)
        T = grid_tris(nrr, nc + 1)
        UV = np.c_[np.tile(phi / (2 * np.pi) * 2.0, nrr), np.repeat(np.arange(nrr) / 8.0, nc + 1)]
        self.emit('casco', P, UV, T, self.rigido(len(P), 'head'), 'casco')
        # barboquejo: de sien a sien por debajo del mentón, pegado a la cara
        betas = np.linspace(-1.92, 1.92, 27)
        z0 = m['ojo_z'] - 0.012
        ys, yc = m['cy'] + 0.004, m['cara_y'] + 0.05
        C = []
        for b in betas:
            o = np.array([m['cx'], ys + (yc - ys) * max(math.cos(b), 0) ** 1.5, z0])
            d = np.array([math.sin(b), 0.0, -math.cos(b)])
            t = self.ray(o, d, 'cabeza', tmax=0.3)
            C.append(o + d * ((t if t else m['hw']) + 0.0075))
        C = np.array(C)
        C = smooth_path(C, 2)
        tg = unit(np.gradient(C, axis=0))
        nrm = unit(C - np.c_[np.full(len(C), m['cx']), C[:, 1], np.full(len(C), z0)])
        bi = unit(np.cross(tg, nrm))
        w = 0.009
        P = np.vstack([C - bi * w, C + nrm * 0.002, C + bi * w]).reshape(3, -1, 3).transpose(1, 0, 2).reshape(-1, 3)
        T = grid_tris(len(C), 3)
        UV = np.c_[np.tile([0.0, 0.05, 0.1], len(C)), np.repeat(np.arange(len(C)) * 0.05, 3)]
        self.emit('barboquejo', P, UV, T, self.rigido(len(P), 'head'), 'lona')


def smooth_path(C, iters):
    C = C.copy()
    for _ in range(iters):
        C[1:-1] = 0.5 * C[1:-1] + 0.25 * (C[:-2] + C[2:])
    return C


def subdividir(P, W, T, marca):
    """Parte en cuatro los triángulos con algún vértice marcado; los vecinos se cosen (sin grietas)."""
    sel = marca[T].any(1)
    mid = {}
    P, W = list(P), list(W)

    def m(a, b):
        k = (min(a, b), max(a, b))
        if k not in mid:
            mid[k] = len(P)
            P.append((P[a] + P[b]) / 2)
            W.append((W[a] + W[b]) / 2)
        return mid[k]
    for t in T[sel]:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            m(a, b)
    out = []
    for t in T:
        e = [mid.get((min(t[i], t[(i + 1) % 3]), max(t[i], t[(i + 1) % 3]))) for i in range(3)]
        n = sum(x is not None for x in e)
        a, b, c = t
        if n == 0:
            out.append((a, b, c))
        elif n == 3:
            out += [(a, e[0], e[2]), (e[0], b, e[1]), (e[2], e[1], c), (e[0], e[1], e[2])]
        elif n == 1:
            i = [x is not None for x in e].index(True)
            v = [a, b, c]
            p, q, r = v[i], v[(i + 1) % 3], v[(i + 2) % 3]
            out += [(p, e[i], r), (e[i], q, r)]
        else:
            i = [x is None for x in e].index(True)   # arista sin partir: (v[i], v[i+1])
            v = [a, b, c]
            p, q, r = v[i], v[(i + 1) % 3], v[(i + 2) % 3]
            mq, mr = e[(i + 1) % 3], e[(i + 2) % 3]   # medios de (q,r) y (r,p)
            out += [(p, q, mq), (p, mq, mr), (mr, mq, r)]
    return np.array(P), np.array(W), np.array(out, int)



# ================================================================ más prendas (métodos de Persona)
def _anillo(self, zs, nc, quien='torso', eje=None, rmax=0.5, relleno=0.1):
    """Radios de la superficie del cuerpo en una rejilla de alturas zs (filas) por nc rumbos; huecos rellenos."""
    phi = np.arange(nc) / nc * 2 * np.pi
    R = np.full((len(zs), nc), np.nan)
    C = []
    for i, z in enumerate(zs):
        c = self.centro(z) if eje is None else eje(z)
        C.append(c)
        for k, f in enumerate(phi):
            t = self.ray(c, np.array([math.sin(f), -math.cos(f), 0.0]), quien, tmax=rmax)
            if t:
                R[i, k] = t
    for i in range(len(zs)):   # huecos (entre las piernas, p. ej.): se interpolan alrededor
        r = R[i]
        if np.isnan(r).all():
            r[:] = relleno
        elif np.isnan(r).any():
            ok = ~np.isnan(r)
            x = np.arange(nc)
            r[~ok] = np.interp(x[~ok], np.r_[x[ok] - nc, x[ok], x[ok] + nc], np.r_[r[ok], r[ok], r[ok]])
    return phi, R, np.array(C)


def _circ(R, w=1):
    out = R.copy()
    for _ in range(w):
        out = 0.5 * out + 0.25 * (np.roll(out, 1, axis=-1) + np.roll(out, -1, axis=-1))
    return out


def _lazo(self, C, R, phi, zs):
    """Puntos de una rejilla cerrada (con columna de costura repetida) a partir de centros, radios y alturas por fila."""
    rows = []
    for i in range(len(zs)):
        r = np.r_[R[i], R[i][:1]]
        f = np.r_[phi, phi[:1] + 2 * np.pi]
        z = zs[i] if np.ndim(zs[i]) else np.full(len(f), zs[i])
        rows.append(np.c_[C[i][0] + r * np.sin(f), C[i][1] - r * np.cos(f), z])
    return np.vstack(rows)


def cintura(self):
    return self.m['cintura']


def braga(self):
    """Braga de lana subida hasta el mentón: tapa el cuello y se mete por dentro del cuello de la camisa."""
    m = self.m
    nc, K = 32, 7
    phi = np.arange(nc) / nc * 2 * np.pi
    c = np.cos(phi)
    base = self.ztop(m['hw'] * 0.95) - 0.035   # donde el cuello se une a los hombros
    zlo = base - 0.030 * np.maximum(c, 0) ** 2
    zhi = np.maximum(c, 0) ** 2 * (m['menton_z'] + 0.018) + np.sin(phi) ** 2 * (m['menton_z'] + 0.034) + np.maximum(-c, 0) ** 2 * (m['ojo_z'] - 0.07)
    O, D, R, Z = [], [], np.zeros((K, nc)), np.zeros((K, nc))
    for k in range(K):
        s = k / (K - 1)
        for i, f in enumerate(phi):
            z = zlo[i] + (zhi[i] - zlo[i]) * s
            o = self.eje_cuello(z)
            d = np.array([math.sin(f), -math.cos(f), 0.0])
            t = self.ray(o, d, 'cabeza', tmax=0.16)
            R[k, i] = min(t, 0.085) if t else np.nan
            Z[k, i] = z
            O.append(o)
            D.append(d)
    for k in range(K):
        r = R[k]
        if np.isnan(r).all():
            r[:] = 0.06
        elif np.isnan(r).any():
            ok = ~np.isnan(r)
            x = np.arange(nc)
            r[~ok] = np.interp(x[~ok], np.r_[x[ok] - nc, x[ok], x[ok] + nc], np.r_[r[ok], r[ok], r[ok]])
    R = _circ(R, 2)
    O, D = np.array(O).reshape(K, nc, 3), np.array(D).reshape(K, nc, 3)
    out = []
    for k in range(K):
        s = k / (K - 1)
        bulto = 0.006 + 0.016 * math.sin(math.pi * min(s * 1.1, 1.0)) ** 0.8
        plieg = 0.003 * np.sin(5 * phi + 4.0 * s) + 0.002 * np.sin(9 * phi - 3.0 * s + 1.0)
        r = R[k] + bulto + plieg * math.sin(math.pi * s)
        row = O[k] + D[k] * r[:, None]
        row[:, 2] = Z[k]
        out.append(np.vstack([row, row[:1]]))
    Q = np.vstack(out)
    T = grid_tris(K, nc + 1)
    UV = np.c_[np.tile(np.arange(nc + 1) / nc * 5.0, K), np.repeat(np.arange(K) / (K - 1) * 1.1, nc + 1)]
    W = smooth(Q, T, self.pesos(Q), 3)
    self.emit('braga', Q, UV, T, W, 'lana')


def camiseta(self):
    """Camiseta verde bajo la camisa: tapa la piel del escote."""
    m = self.m
    z1 = self.ztop(m['hw'] * 0.95) + 0.01
    z0 = z1 - 0.26
    P, W, T = self.funda(lambda P, W: (P[:, 2] > z0) & (P[:, 2] < z1) & (np.abs(P[:, 0] - m['cx']) < 0.13) & (P[:, 1] < m['cy'] + 0.03) & (self.wsum(W, 'upperarm') < 0.3), 0.0025, suave=0)
    UV = np.c_[P[:, 0] * 5.0, P[:, 2] * 5.0]
    self.emit('camiseta', P, UV, T, W, 'pano')


def faldon(self):
    """Faldón de la guerrera por fuera del pantalón: la camisa de MakeHuman pasa a leerse como guerrera de campaña."""
    zb = self.cintura()
    nc = 40
    zs = np.linspace(zb + 0.03, zb - 0.185, 7)
    phi, R, C = _anillo(self, zs, nc)
    R = np.maximum.accumulate(R, axis=0) * 0.5 + R * 0.5   # no se ciñe a los entrantes de debajo
    R = _circ(R, 2)
    s = np.linspace(0, 1, len(zs))[:, None]
    R = R + 0.007 + 0.016 * s ** 1.2 + (0.004 * np.sin(7 * phi + 0.6) + 0.003 * np.sin(12 * phi + 2.0))[None, :] * s
    Cm = np.tile(C.mean(0), (len(zs), 1))
    Cm[:, 2] = zs
    Cm = 0.5 * Cm + 0.5 * C
    P = _lazo(self, Cm, R, phi, zs)
    P[-(nc + 1):, 2] += 0.006 * np.sin(5 * np.r_[phi, phi[:1]] + 1.0)
    T = grid_tris(len(zs), nc + 1)
    UV = np.c_[np.tile(np.arange(nc + 1) / nc * 6.0, len(zs)), np.repeat((zb - zs) * 5.0, nc + 1)]
    W = self.pesos(P)
    W0 = np.tile(W[nc + 1:2 * (nc + 1)], (len(zs), 1))
    h = np.repeat(0.45 * sstep(0.25, 1.0, s[:, 0]), nc + 1)[:, None]
    W = smooth(P, T, (1 - h) * W + h * W0, 4)
    self.emit('faldon', P, UV, T, W, 'pano')
    self._faldon = True


def cinturon(self, cartucheras=False):
    """Cinturón de lona con hebilla; con cartucheras y cantimplora si va de correaje."""
    zb = self.cintura()
    nc = 40
    g = 0.012 if getattr(self, '_faldon', False) else 0.0
    zs = np.array([zb - 0.027, zb - 0.027, zb, zb + 0.027, zb + 0.027])
    phi, R, C = _anillo(self, np.array([zb - 0.025, zb, zb + 0.025]), nc)
    r0 = _circ(R.max(0), 2) + g
    c0 = C.mean(0)
    Rr = np.array([r0 + 0.002, r0 + 0.010, r0 + 0.011, r0 + 0.010, r0 + 0.002])
    P = _lazo(self, [np.r_[c0[:2], z] for z in zs], Rr, phi, zs)
    T = grid_tris(len(zs), nc + 1)
    UV = np.c_[np.tile(np.arange(nc + 1) / nc * 9.0, len(zs)), np.repeat([0.0, 0.03, 0.2, 0.37, 0.4], nc + 1)]
    self.emit('cinturon', P, UV, T, smooth(P, T, self.pesos(P), 2), 'lona')
    self._cint = (c0, r0, phi, zb)

    def pieza(nombre, f, size, dz, mat, r=0.012, fuera=0.0):
        rr = np.interp(f % (2 * np.pi), np.r_[phi, 2 * np.pi], np.r_[r0, r0[:1]]) + 0.010 + size[1] / 2 + fuera
        cen = np.array([c0[0] + rr * math.sin(f), c0[1] - rr * math.cos(f), zb + dz])
        B, Tb = rbox(size, r)
        ca, sa = math.cos(f), math.sin(f)
        Rz = np.array([[ca, sa, 0], [-sa, ca, 0], [0, 0, 1]])   # el fondo de la caja (eje y local) mira hacia fuera
        B = B @ Rz.T
        B[:, :2] = np.c_[B[:, 0], B[:, 1]] * 1.0
        Pq = B * np.array([1, -1, 1]) + cen if False else (np.c_[B[:, 0] * ca + B[:, 1] * sa, -(-B[:, 0] * sa + B[:, 1] * ca) * 1.0, B[:, 2]] * 0 + 0)
        return cen, B, Tb
    piezas = [('hebilla', 0.0, (0.05, 0.012, 0.046), 0.0, 'casco', 0.004, -0.004)]
    if cartucheras:
        piezas += [('cartuchera_i', 0.50, (0.088, 0.046, 0.108), -0.012, 'lona', 0.012, 0.0), ('cartuchera_d', -0.50, (0.088, 0.046, 0.108), -0.012, 'lona', 0.012, 0.0),
                   ('cantimplora', math.pi - 0.75, (0.115, 0.07, 0.15), -0.06, 'pano', 0.03, 0.0)]
    for nombre, f, size, dz, mat, r, fuera in piezas:
        rr = float(np.interp(f % (2 * np.pi), np.r_[phi, 2 * np.pi], np.r_[r0, r0[:1]])) + 0.010 + size[1] / 2 + fuera
        cen = np.array([c0[0] + rr * math.sin(f), c0[1] - rr * math.cos(f), zb + dz])
        B, Tb = rbox(size, r)
        # ejes locales: x = tangente, y = hacia fuera, z = arriba
        tx = np.array([math.cos(f), math.sin(f), 0.0])
        ty = np.array([math.sin(f), -math.cos(f), 0.0])
        Pq = cen + B[:, :1] * tx + B[:, 1:2] * ty + B[:, 2:3] * np.array([0, 0, 1.0])
        if np.dot(np.cross(tx, ty), [0, 0, 1]) < 0:
            Tb = Tb[:, ::-1]
        UV = np.c_[B[:, 0] * 6 + B[:, 1] * 3, B[:, 2] * 6]
        W = np.tile(self.pesos(cen[None] - ty * (size[1] / 2 + 0.01))[0], (len(Pq), 1))
        self.emit(nombre, Pq, UV, Tb, W, mat)


def correaje(self):
    """Cinturón con cartucheras y cantimplora, y tirantes en Y por encima de los hombros."""
    cinturon(self, cartucheras=True)
    c0, r0, phi, zb = self._cint
    J = self.J
    zc = (zb + self.ztop(0.09)) / 2
    cy = self.centro(zc)[1]
    w = 0.019
    g = 0.012 if getattr(self, '_faldon', False) else 0.0

    def cinta(nombre, psis, xs, lados=(1,)):
        for sg in lados:
            L = []
            for ps, x in zip(psis, xs):
                fila = []
                for dx in (-w, 0.0, w):
                    o = np.array([c0[0] + sg * x + dx, cy, zc])
                    d = np.array([0.0, -math.cos(ps), math.sin(ps)])
                    t = self.ray(o, d, 'torso', tmax=0.6)
                    fila.append(o + d * ((t if t else 0.15) + 0.007 + (0.0025 if dx == 0 else 0)))
                L.append(fila)
            L = np.array(L)
            for k in range(3):
                L[:, k] = smooth_path(L[:, k], 3)
            L = L[L[:, 1, 2] > zb - 0.012]
            P = L.reshape(-1, 3)
            T = grid_tris(len(L), 3)
            if sg < 0:
                T = T[:, ::-1]
            UV = np.c_[np.tile([0.0, 0.1, 0.2], len(L)), np.repeat(np.arange(len(L)) * 0.12, 3)]
            self.emit(nombre + ('_i' if sg > 0 else '_d') if len(lados) > 1 else nombre, P, UV, T, smooth(P, T, self.pesos(P), 2), 'lona')
    # suben por delante desde el cinturón, cruzan el hombro y bajan por la espalda hasta el cinturón (arnés en H)
    fz = zb + 0.02 - zc
    ps0 = math.atan2(fz, 0.13)
    n = 34
    psis = np.linspace(ps0, math.pi - ps0, n)
    u = np.linspace(0, 1, n)
    xs = 0.086 + 0.016 * sstep(0.0, 0.4, u) - 0.050 * sstep(0.6, 1.0, u)
    cinta('tirante', psis, xs, lados=(1, -1))


def gorra(self):
    """Gorra de faena con visera, calada sobre el pasamontañas."""
    m = self.m
    nc = 36
    phi = np.arange(nc + 1) / nc * 2 * np.pi
    c = np.cos(phi)
    zr = np.maximum(c, 0) ** 2 * (m['ojo_z'] + 0.032) + np.sin(phi) ** 2 * (m['ojo_z'] + 0.024) + np.maximum(-c, 0) ** 2 * (m['ojo_z'] + 0.002)
    rx, ry = m['hw'] + 0.011, m['hd'] + 0.013
    R = 1.0 / np.sqrt((np.sin(phi) / rx) ** 2 + (np.cos(phi) / ry) ** 2)
    H = m['top'] + 0.016 - zr + 0.014 * np.maximum(c, 0)   # algo más alta por delante
    perfil = [(0.985, -0.01), (1.0, 0.0), (1.012, 0.35), (1.0, 0.72), (0.93, 0.93), (0.72, 1.0), (0.38, 1.02), (0.0, 1.03)]
    rows = [np.c_[m['cx'] + R * a * np.sin(phi), m['cy'] - 0.003 - R * a * np.cos(phi), zr + H * b] for a, b in perfil]
    P = np.vstack(rows)
    T = grid_tris(len(rows), nc + 1)[:, ::-1]
    UV = np.c_[np.tile(phi / (2 * np.pi) * 4.0, len(rows)), np.repeat(np.arange(len(rows)) * 0.25, nc + 1)]
    self.emit('gorra', P, UV, T, self.rigido(len(P), 'head'), 'pano')
    # visera
    fs = np.linspace(-1.05, 1.05, 15)
    Rv = 1.0 / np.sqrt((np.sin(fs) / rx) ** 2 + (np.cos(fs) / ry) ** 2)
    zv = m['ojo_z'] + 0.032 + (np.sin(fs) ** 2) * (-0.006)
    L = 0.068 * np.cos(fs * 1.35) ** 0.6
    rows = []
    for s in np.linspace(0, 1, 5):
        r = Rv * 0.995 + L * s
        rows.append(np.c_[m['cx'] + r * np.sin(fs), m['cy'] - 0.003 - r * np.cos(fs), zv - 0.020 * s - 0.006 * s * s + 0.004])
    P = np.vstack(rows)
    T = grid_tris(5, len(fs))[:, ::-1]
    UV = np.c_[np.tile(fs, 5), np.repeat(np.linspace(0, 0.4, 5), len(fs))]
    self.emit('visera', P, UV, T, self.rigido(len(P), 'head'), 'pano')


def capote(self, capucha=True):
    """Capote de agua: de la coronilla (o del cuello, sin capucha) a la rodilla en una sola pieza, abierto por los lados."""
    m, J = self.m, self.J
    top, eye, chin = m['top'], m['ojo_z'], m['menton_z']
    hcy, hd, hw, hx = m['cy'], m['hd'], m['hw'], m['cx']
    S, E, H = m['hombro'], m['codo'], m['H']
    sx, ex = S[0] - hx, E[0] - hx
    xm = (sx + ex) / 2
    xn = max(hw + 0.045, 0.115)
    zn = self.ztop(xn) + 0.028          # donde la capucha se apoya en los hombros, junto al cuello
    zt = self.ztop(sx) - 0.16           # altura del pecho
    ay = self.centro(zt)[1]
    yF0, yB0 = ay - self.radio(zt, 0.0), ay + self.radio(zt, math.pi)
    zh = self.ztop(sx + 0.015) + 0.030
    # filas de control: delante (y, z), detrás (y, z), lado (x, y, z), exponente de la sección
    ctrl = np.array([
        (hcy - 0.004, top + 0.036, hcy + 0.004, top + 0.036, 0.004, hcy, top + 0.036, 2.0),
        (hcy - hd * 0.66, top + 0.028, hcy + hd * 0.64, top + 0.024, hw * 0.74, hcy, top + 0.022, 2.0),
        (hcy - hd - 0.040, top - 0.026, hcy + hd + 0.030, top - 0.030, hw + 0.030, hcy, top - 0.032, 2.1),
        (hcy - hd - 0.042, eye, hcy + hd + 0.038, eye, hw + 0.040, hcy + 0.005, eye, 2.2),
        (hcy - hd - 0.028, chin + 0.012, hcy + hd + 0.026, chin, hw + 0.038, hcy + 0.010, chin, 2.2),
        (yF0 - 0.010, zn - 0.030, hcy + hd + 0.016, zn - 0.010, xn, (hcy + S[1]) / 2, zn, 2.2),
        (yF0 - 0.026, zh - 0.060, yB0 + 0.024, zh - 0.040, sx + 0.010, S[1], zh - 0.008, 2.25),
        (yF0 - 0.040, zh - 0.200, yB0 + 0.036, zh - 0.200, xm + 0.012, (S[1] + E[1]) / 2, self.ztop(xm + 0.012) + 0.022, 2.3),
        (yF0 - 0.050, zh - 0.340, yB0 + 0.044, zh - 0.340, ex + 0.024, E[1], self.ztop(ex + 0.024) + 0.024, 2.3),
        (yF0 - 0.066, 0.50 * H, yB0 + 0.056, 0.50 * H, ex + 0.088, E[1] - 0.010, E[2] - 0.035, 2.4),
        (yF0 - 0.078, 0.365 * H, yB0 + 0.066, 0.355 * H, ex + 0.100, E[1] - 0.015, E[2] - 0.135, 2.4),
    ])
    kn = 5   # fila de control del cuello
    if not capucha:   # sin capucha: cuello subido en lugar de la cabeza
        c5 = ctrl[5]
        cuello = (c5[0] + 0.030, c5[1] + 0.055, c5[2] - 0.035, c5[3] + 0.050, c5[4] - 0.030, c5[5], c5[6] + 0.045, 2.0)
        ctrl = np.vstack([cuello, ctrl[5:]])
        kn = 1
    sub = 4
    F = catmull(ctrl, sub)
    nr = len(F)
    half, K = 28, 5
    nc = 2 * half + 1
    cols = np.arange(-half, half + 1)
    # abertura de la cara: filas cuyo frente cae entre el mentón y la frente
    zlo, zhi = chin + 0.004, eye + 0.062
    zmid, hz = (zlo + zhi) / 2, (zhi - zlo) / 2
    base = K * math.pi / half
    abierto = (F[:, 1] > zlo) & (F[:, 1] < zhi) & (np.arange(nr) < kn * sub + 1) & capucha
    rows = []
    for r in range(nr):
        yF, zF, yB, zB, xS, yS, zS, n = F[r]
        fo = base
        if abierto[r]:
            fo = max(0.66 * math.sqrt(max(1 - ((zF - zmid) / hz) ** 2, 0.0)), 0.16)
        a = np.abs(cols)
        phi = np.where(a <= K, fo * a / K, fo + (math.pi - fo) * (a - K) / (half - K)) * np.sign(cols)
        s, c = np.sin(phi), np.cos(phi)
        e = 2.0 / n
        x = hx + xS * np.sign(s) * np.abs(s) ** e
        y = np.where(c > 0, yS - (yS - yF) * np.abs(c) ** e, yS + (yB - yS) * np.abs(c) ** e)
        z = np.maximum(c, 0) ** 2 * zF + s ** 2 * zS + np.maximum(-c, 0) ** 2 * zB
        rows.append(np.c_[x, y, z])
    P = np.array(rows)   # (nr, nc, 3)
    ra = np.where(abierto)[0]
    r0, r1 = (ra.min(), ra.max()) if capucha else (0, -1)
    # visera de la capucha: el borde de la abertura se adelanta para dejar la cara en sombra
    for r in range(max(r0 - 3, 0), r1 + 1):
        u = (r - r0) / max(r1 - r0, 1)
        ov = 0.022 * (1 - sstep(0.0, 0.9, u)) + 0.006
        gcol = sstep(K + 4, K, np.abs(cols))
        P[r, :, 1] -= ov * gcol
    # pliegues de la caída, de los hombros al bajo
    rs = (kn + 1) * sub
    cen = np.c_[np.full(nr, hx), F[:, 5]]
    ang = cols / half * math.pi
    pl = 0.7 * np.sin(6 * ang + 1.3) + 0.5 * np.sin(10 * ang + 0.4) + 0.35 * np.sin(15 * ang + 2.1) + 0.2 * np.sin(23 * ang + 0.9)
    for r in range(rs, nr):
        t = (r - rs) / (nr - 1 - rs)
        d = unit(P[r, :, :2] - cen[r])
        P[r, :, :2] += d * ((0.005 + 0.034 * t) * pl * (0.35 + 0.65 * np.abs(np.cos(ang)) ** 0.7))[:, None]
        P[r, :, 2] += (0.018 * np.sin(4 * ang + 0.7) + 0.008 * np.sin(9 * ang + 2.0)) * t ** 2
    Pf = P.reshape(-1, 3)
    cuerpo = np.repeat(np.arange(nr) >= kn * sub, nc)
    Pf[cuerpo] = self.separar(Pf[cuerpo], 0.022, centro=np.array([hx, ay, 0]))
    Pf[~cuerpo] = self.separar(Pf[~cuerpo], 0.012, centro=np.array([hx, hcy, 0]))
    P = Pf.reshape(nr, nc, 3)
    P[:, -1] = P[:, 0]   # costura de detrás
    quita = lambda r, c: abierto[r] and abierto[r + 1] and (half - K) <= c < (half + K)
    T = grid_tris(nr, nc, skip=quita)[:, ::-1]
    largo = np.r_[np.zeros((1, nc)), np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=2), axis=0)]
    UV = np.c_[np.tile(np.arange(nc) / (nc - 1) * 6.0, nr), (largo * 3.0).reshape(-1)]
    Pf = P.reshape(-1, 3)
    W = self.pesos(Pf)
    fuera = [i for i, n in enumerate(self.bones) if n.split('_')[0] in ('lowerarm', 'hand', 'index', 'middle', 'ring', 'pinky', 'thumb')]
    for lado in ('_l', '_r'):
        idx = [i for i in fuera if self.bones[i].endswith(lado)]
        W[:, self.bi['upperarm' + lado]] += W[:, idx].sum(1)
        W[:, idx] = 0
    W = W.reshape(nr, nc, -1)
    lat = np.sin(ang) ** 2
    rh = (kn + 3) * sub
    for r in range(rh + 1, nr):
        h = ((0.65 + 0.35 * lat) * float(sstep(rh, nr - 1, r)))[:, None]
        W[r] = (1 - h) * W[r] + h * W[rh]
    W = smooth(Pf, T, W.reshape(nr * nc, -1), 5)
    self.emit('capote', Pf, UV, T, W, 'capote')


for _f in (camiseta, braga, faldon, cinturon, correaje, gorra, capote, cintura):
    setattr(Persona, _f.__name__, _f)


def vestir(nombre):
    eq = EQUIPO[nombre]
    p = Persona(nombre, eq.get('base'))
    print(nombre, eq)
    g = p.g
    if p.quitadas:
        print('   sin', p.quitadas)
    # traje de MakeHuman al verde oliva del uniforme
    for mt in g.j['materials']:
        if 'suit' in mt['name']:
            ti = g.j['textures'][mt['pbrMetallicRoughness']['baseColorTexture']['index']]['source']
            g.set_image(ti, texturas.retinte(g.image(ti)))
            mt['pbrMetallicRoughness']['roughnessFactor'] = 0.86
    # piel curtida y algo más oscura: lo único que asoma es el contorno de los ojos, y con la piel clara de
    # MakeHuman brillaba como un antifaz
    for mt in g.j['materials']:
        if mt['name'].endswith(('_body', '_ears', '_lips')):
            mt.setdefault('pbrMetallicRoughness', {})['baseColorFactor'] = [0.66, 0.62, 0.60, 1.0]
    p.pasamontanas()
    p.guantes()
    p.camiseta()
    if eq.get('cabeza') == 'casco':
        p.casco()
    for extra in ('braga', 'faldon', 'correaje', 'cinturon'):
        if eq.get(extra):
            getattr(p, extra)()
    if eq.get('capote'):
        p.capote(capucha=eq['capote'] != 'sin_capucha')
    if eq.get('cabeza') == 'gorra':
        p.gorra()
    n = g.save(os.path.join(DST, nombre + '.glb'))
    print('   ->', os.path.join(DST, nombre + '.glb'), '%.0f KB' % (n / 1024))


if __name__ == '__main__':
    for n in (sys.argv[1:] or sorted(EQUIPO)):
        vestir(n)
