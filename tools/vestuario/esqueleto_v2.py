"""Recoloca los huesos de brazos y piernas de las personas de MakeHuman sobre su malla (tanda M).

El esqueleto venía igual para los tres cuerpos y no casaba con la malla: codos y muñecas hasta ~8 cm fuera.
Aquí cada articulación se calcula a partir de la propia malla y de sus pesos:
  - eje de cada tramo (brazo, antebrazo, muslo, pierna) = recta principal (PCA) de los vértices que ese hueso
    mueve con peso >= 0,5;
  - codo y rodilla = punto medio entre las dos rectas, donde más se acercan;
  - hombro, muñeca, cadera y tobillo = la franja de vértices que comparte peso entre los dos huesos, llevada
    sobre el eje de su tramo.
Solo cambian la posición de esas articulaciones (la orientación de cada hueso no se toca, ni los pesos, ni la
malla). Los hijos que no se mueven (dedos, pie) siguen a su padre. Se rehacen las matrices de enlace
(inverseBindMatrices) y, en las animaciones del .glb, las traslaciones fijas de los huesos movidos.

No repesa: los pesos de MakeHuman ya siguen la malla (la franja de pesos compartidos está en el codo de la
malla, no en el hueso); lo que estaba mal era el hueso.

Uso (cualquier Python con numpy, por ejemplo el de Blender):
    python esqueleto_v2.py entrada.glb salida.glb [informe.txt]
Sin argumentos: los cuerpos sin equipo (ibarra, moya, peris) a personas/sin_equipo/<n>_v2.glb.
"""
import os, sys, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from glb import Glb

ROOT = os.path.dirname(os.path.dirname(HERE))
SIN = os.path.join(ROOT, 'assets', 'unreal', 'personas', 'sin_equipo')

# (padre, articulación, hijo) por cadena; la articulación es la cabeza del hueso del medio
CADENAS = [('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l'),
           ('clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r'),
           ('pelvis', 'thigh_l', 'calf_l', 'foot_l'),
           ('pelvis', 'thigh_r', 'calf_r', 'foot_r')]
MIN_CM = 1.0   # por debajo no se mueve


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def trs(n):
    m = np.eye(4)
    if 'matrix' in n:
        return np.array(n['matrix'], float).reshape(4, 4).T
    R = quat_mat(n.get('rotation', [0, 0, 0, 1]))
    S = np.diag(n.get('scale', [1, 1, 1]))
    m[:3, :3] = R @ S
    m[:3, 3] = n.get('translation', [0, 0, 0])
    return m


class Cuerpo:
    def __init__(self, path):
        self.g = Glb(path)
        j = self.g.j
        self.skin = j['skins'][0]
        self.joints = self.skin['joints']
        self.name = {j['nodes'][n]['name']: n for n in self.joints}
        self.parent = {}
        for i, n in enumerate(j['nodes']):
            for c in n.get('children', []):
                self.parent[c] = i
        self.world = {}
        for n in range(len(j['nodes'])):
            self.world[n] = self._w(n)
        # vértices de todas las mallas con piel, en espacio de enlace (= mundo en reposo)
        ibm = self.g.acc(self.skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        self.bind = np.linalg.inv(ibm)
        P, Jn, Wt = [], [], []
        for nd in j['nodes']:
            if 'mesh' in nd and nd.get('skin') == 0:
                for pr in j['meshes'][nd['mesh']]['primitives']:
                    a = pr['attributes']
                    P.append(self.g.acc(a['POSITION']).astype(float))
                    Jn.append(self.g.acc(a['JOINTS_0']).astype(int))
                    Wt.append(self.g.acc(a['WEIGHTS_0']).astype(float))
        self.P, self.J, self.W = np.vstack(P), np.vstack(Jn), np.vstack(Wt)

    def _w(self, n):
        m = trs(self.g.j['nodes'][n])
        p = self.parent.get(n)
        return (self._w(p) if p is not None else np.eye(4)) @ m

    def jidx(self, bone):
        return self.joints.index(self.name[bone])

    def head(self, bone):
        return self.bind[self.jidx(bone)][:3, 3]

    def peso(self, bone):
        k = self.jidx(bone)
        return (self.W * (self.J == k)).sum(1)

    def nube(self, bone, th=0.5):
        return self.P[self.peso(bone) >= th]

    def franja(self, a, b):
        wa, wb = self.peso(a), self.peso(b)
        s = wa + wb
        m = (s > 0.7) & (wb > 0.3 * s) & (wb < 0.7 * s)
        return self.P[m]


def eje(pts):
    c = pts.mean(0)
    u = np.linalg.svd(pts - c)[2][0]
    return c, u / np.linalg.norm(u)


def sobre(c, u, p):
    return c + u * np.dot(p - c, u)


def cerca(c1, u1, c2, u2):
    w = c1 - c2
    a, b, cc, d, e = u1 @ u1, u1 @ u2, u2 @ u2, u1 @ w, u2 @ w
    den = a * cc - b * b
    if abs(den) < 1e-9:
        return (c1 + c2) / 2
    s = (b * e - cc * d) / den
    t = (a * e - b * d) / den
    return ((c1 + s * u1) + (c2 + t * u2)) / 2


def desvio(cu, a, b):
    """cm entre el centro de la nube del tramo y la recta del hueso a-b."""
    nube = cu.nube(a)
    if len(nube) < 5:
        return float('nan')
    c = nube.mean(0)
    h, t = cu.head(a), cu.head(b)
    u = (t - h) / np.linalg.norm(t - h)
    return float(np.linalg.norm((c - h) - u * np.dot(c - h, u)) * 100)


def objetivos(cu):
    obj = {}
    for pa, a, b, c in CADENAS:
        na, nb = cu.nube(a), cu.nube(b)
        if len(na) < 8 or len(nb) < 8:
            continue
        ca, ua = eje(na)
        cb, ub = eje(nb)
        fa, fb, fc = cu.franja(pa, a), cu.franja(a, b), cu.franja(b, c)
        ang = math.degrees(math.acos(min(1.0, abs(float(ua @ ub)))))
        if ang >= 20:
            obj[b] = cerca(ca, ua, cb, ub)
        elif len(fb) >= 4:
            # tramos casi en línea (pierna estirada): las rectas no se cruzan bien; la franja del codo o
            # la rodilla, llevada a la recta media
            obj[b] = (sobre(ca, ua, fb.mean(0)) + sobre(cb, ub, fb.mean(0))) / 2
        if len(fa) >= 4:
            s = sobre(ca, ua, fa.mean(0))
            if a.startswith('upperarm'):
                # la franja del hombro queda en lo alto del deltoides: la articulación está un radio del brazo
                # más adentro, hacia el codo
                r = float(np.median(np.linalg.norm((na - ca) - np.outer((na - ca) @ ua, ua), axis=1)))
                hacia = obj[b] - s if b in obj else -ua
                s = s + hacia / np.linalg.norm(hacia) * r
            obj[a] = s
        cu.angulos = getattr(cu, 'angulos', {})
        cu.angulos[b] = ang
        if len(fc) >= 4:
            obj[c] = sobre(cb, ub, fc.mean(0))
    return obj


def medir(cu):
    out = {}
    for pa, a, b, c in CADENAS:
        out[a] = desvio(cu, a, b)
        out[b] = desvio(cu, b, c)
    return out


def aplicar(cu, obj):
    """Mueve las articulaciones a obj (mundo) sin girarlas; los hijos no movidos siguen al padre."""
    j = cu.g.j
    nodes = j['nodes']
    nuevo = {n: cu.world[n].copy() for n in cu.world}
    movidos = {}
    orden = []

    def bajar(n):
        orden.append(n)
        for c in nodes[n].get('children', []):
            bajar(c)
    raices = [n for n in range(len(nodes)) if n not in cu.parent]
    for r in raices:
        bajar(r)
    for n in orden:
        p = cu.parent.get(n)
        name = nodes[n].get('name')
        if p is not None:
            nuevo[n] = nuevo[p] @ trs(nodes[n])   # sigue al padre con su traslación local de antes
        if n in cu.joints and name in obj:
            d = np.linalg.norm(obj[name] - cu.world[n][:3, 3]) * 100
            if d >= MIN_CM:
                nuevo[n][:3, 3] = obj[name]
                movidos[name] = d
                if p is not None:
                    Rp = nuevo[p][:3, :3]
                    loc = np.linalg.solve(Rp, obj[name] - nuevo[p][:3, 3])
                    nodes[n]['translation'] = [float(x) for x in loc]
    # matrices de enlace
    ibm = np.stack([np.linalg.inv(nuevo[n]).T for n in cu.joints]).astype('<f4')
    cu.skin['inverseBindMatrices'] = cu.g.add_acc(ibm.reshape(-1, 16), 'MAT4')
    # traslaciones de las animaciones de los huesos movidos: la nueva de reposo
    for an in j.get('animations', []):
        for ch in an['channels']:
            n = ch['target']['node']
            if ch['target']['path'] == 'translation' and nodes[n].get('name') in movidos:
                smp = an['samplers'][ch['sampler']]
                k = cu.g.acc(smp['output']).shape[0]
                arr = np.tile(np.array(nodes[n]['translation'], '<f4'), (k, 1))
                smp['output'] = cu.g.add_acc(arr, 'VEC3', minmax=True)
    return movidos


PRUEBA_CADENA = {'upperarm_l': ('lowerarm_l', 'upperarm_l'), 'upperarm_r': ('lowerarm_r', 'upperarm_r'),
                 'thigh_l': ('calf_l',), 'thigh_r': ('calf_r',)}


def elegir(src, obj):
    """Se queda, cadena a cadena, con el arreglo solo si la malla se deforma mejor al doblar (esqueleto_medir)."""
    import tempfile
    import esqueleto_medir as M
    base, ref = M.medir(src)
    tmp = os.path.join(tempfile.gettempdir(), 'esqueleto_v2_prueba.glb')
    aceptadas = {}
    for pa, a, b, c in CADENAS:
        sub = {k: v for k, v in obj.items() if k in (a, b, c)}
        if not sub:
            continue
        cu = Cuerpo(src)
        aplicar(cu, sub)
        cu.g.save(tmp)
        prueba, _ = M.medir(tmp, ref)
        claves = [k for k in prueba if k.split()[0] in PRUEBA_CADENA[a]]
        m0 = np.mean([base[k][0] for k in claves])
        m1 = np.mean([prueba[k][0] for k in claves])
        aceptadas[a] = (m1 < m0 - 0.5, m0, m1)
    os.remove(tmp)
    return aceptadas


def procesar(src, dst, informe=None):
    cu = Cuerpo(src)
    antes = medir(cu)
    obj = objetivos(cu)
    dist = {b: float(np.linalg.norm(p - cu.head(b)) * 100) for b, p in obj.items()}
    eleccion = elegir(src, obj)
    for pa, a, b, c in CADENAS:
        if a in eleccion and not eleccion[a][0]:
            for k in (a, b, c):
                obj.pop(k, None)
    movidos = aplicar(cu, obj)
    cu.g.save(dst)
    despues = medir(Cuerpo(dst))
    lineas = ['%s -> %s' % (os.path.basename(src), os.path.basename(dst)),
              'cadenas (estiramiento medio al doblar, sin -> con arreglo): ' +
              ', '.join('%s %.1f -> %.1f %%%s' % (a, e[1], e[2], '' if e[0] else ' (no mejora: se deja)') for a, e in eleccion.items()),
              'articulación: distancia del hueso a la malla (cm) | desvío del tramo antes -> después (cm)']
    for pa, a, b, c in CADENAS:
        for x in (a, b, c):
            if x in dist:
                lineas.append('  %-11s %5.1f cm%s | %s' % (x, dist[x], ' (movido)' if x in movidos else '',
                              ('%.1f -> %.1f' % (antes[x], despues[x])) if x in antes else '-'))
    txt = '\n'.join(lineas)
    print(txt)
    if informe:
        with open(informe, 'a', encoding='utf-8') as f:
            f.write(txt + '\n\n')
    return dist, antes, despues


VESTIDOS = {'ibarra': 'ibarra', 'centinela': 'ibarra', 'moya': 'moya', 'vega': 'moya', 'peris': 'peris', 'ramos': 'peris'}


def trasplantar(base_src, vestido_src, dst):
    """Lleva a una silueta ya vestida (vestir.py) el arreglo calculado sobre su cuerpo sin equipo.
    vestir.py deja el esqueleto byte a byte, así que las articulaciones están en el mismo sitio; las prendas
    (capote, capucha) no deben influir en el cálculo, por eso se mide en el cuerpo desnudo."""
    base = Cuerpo(base_src)
    obj = objetivos(base)
    eleccion = elegir(base_src, obj)
    for pa, a, b, c in CADENAS:
        if a in eleccion and not eleccion[a][0]:
            for k in (a, b, c):
                obj.pop(k, None)
    cu = Cuerpo(vestido_src)
    dif = max(float(np.linalg.norm(cu.head(b) - base.head(b))) for b in base.name)
    assert dif < 1e-4, 'el esqueleto de %s no es el de su cuerpo base (%.4f m)' % (vestido_src, dif)
    movidos = aplicar(cu, obj)
    cu.g.save(dst)
    return movidos


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        procesar(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        for n in ('ibarra', 'moya', 'peris'):
            procesar(os.path.join(SIN, n + '.glb'), os.path.join(SIN, n + '_v2.glb'))
