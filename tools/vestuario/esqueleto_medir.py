"""Mide cómo se deforma la malla al doblar codo, hombro y rodilla, antes y después de esqueleto_v2.py.

Como esqueleto_v2 no gira ningún hueso, el mismo giro local vale para los dos .glb y se pueden comparar.
Métrica: cambio de longitud de las aristas en la franja de pesos compartidos de esa articulación (media y
percentil 95, en %). Cuanto menos, menos se estira o se aplasta la manga en la flexión.

Uso: python esqueleto_medir.py antes.glb despues.glb
"""
import math, sys
import numpy as np
import esqueleto_v2 as E


def axis_q(ax, deg):
    ax = np.asarray(ax, float)
    ax = ax / np.linalg.norm(ax)
    s = math.sin(math.radians(deg) / 2)
    return [ax[0] * s, ax[1] * s, ax[2] * s, math.cos(math.radians(deg) / 2)]


def qmul(a, b):
    x1, y1, z1, w1 = a
    x2, y2, z2, w2 = b
    return [w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2]


def pose_world(cu, extra):
    nodes = cu.g.j['nodes']
    W = {}

    def w(n):
        if n in W:
            return W[n]
        nd = dict(nodes[n])
        if nd.get('name') in extra:
            nd['rotation'] = qmul(nd.get('rotation', [0, 0, 0, 1]), extra[nd['name']])
        p = cu.parent.get(n)
        W[n] = (w(p) if p is not None else np.eye(4)) @ E.trs(nd)
        return W[n]
    return np.stack([w(n) for n in cu.joints])


def skin(cu, extra):
    M = pose_world(cu, extra) @ np.linalg.inv(cu.bind)
    Ph = np.c_[cu.P, np.ones(len(cu.P))]
    out = np.zeros_like(cu.P)
    for k in range(4):
        out += cu.W[:, k:k + 1] * np.einsum('nij,nj->ni', M[cu.J[:, k]], Ph)[:, :3]
    return out


def aristas(cu):
    j = cu.g.j
    s, off = set(), 0
    for nd in j['nodes']:
        if 'mesh' in nd and nd.get('skin') == 0:
            for pr in j['meshes'][nd['mesh']]['primitives']:
                n = cu.g.acc(pr['attributes']['POSITION']).shape[0]
                I = cu.g.acc(pr['indices']).reshape(-1, 3).astype(int) + off
                for a, b in ((0, 1), (1, 2), (2, 0)):
                    s.update(zip(np.minimum(I[:, a], I[:, b]), np.maximum(I[:, a], I[:, b])))
                off += n
    return np.array(sorted(s))


# (hueso que gira, padre para la franja, hijo para el eje, grados)
PRUEBAS = [('lowerarm_l', 'upperarm_l', 'hand_l', 100), ('lowerarm_r', 'upperarm_r', 'hand_r', 100),
           ('upperarm_l', 'clavicle_l', 'lowerarm_l', 70), ('upperarm_r', 'clavicle_r', 'lowerarm_r', 70),
           ('calf_l', 'thigh_l', 'foot_l', 90), ('calf_r', 'thigh_r', 'foot_r', 90)]


def medir(path, ref=None):
    cu = E.Cuerpo(path)
    ref = ref or cu
    ed = aristas(cu)
    L0 = np.linalg.norm(cu.P[ed[:, 0]] - cu.P[ed[:, 1]], axis=1)
    out = {}
    for b, pa, ch, deg in PRUEBAS:
        # eje de flexión tomado del cuerpo de referencia (el mismo para antes y después)
        u1 = ref.head(b) - ref.head(pa)
        u2 = ref.head(ch) - ref.head(b)
        axw = np.cross(u1, u2)
        if np.linalg.norm(axw) < 1e-6:
            axw = np.array([1.0, 0, 0])
        axl = np.linalg.solve(ref.bind[ref.jidx(b)][:3, :3], axw)
        P1 = skin(cu, {b: axis_q(axl, deg)})
        L1 = np.linalg.norm(P1[ed[:, 0]] - P1[ed[:, 1]], axis=1)
        z = (cu.peso(b) > 0.05) & (cu.peso(pa) > 0.05)
        ez = z[ed[:, 0]] | z[ed[:, 1]]
        d = np.abs(L1[ez] - L0[ez]) / np.maximum(L0[ez], 1e-4) * 100
        out['%s %d°' % (b, deg)] = (float(np.mean(d)), float(np.percentile(d, 95))) if ez.any() else (float('nan'),) * 2
    return out, cu


def comparar(antes, despues):
    a, ref = medir(antes)
    d, _ = medir(despues, ref)
    lineas = []
    for k in a:
        lineas.append('  %-16s estiramiento medio %.1f -> %.1f %%   p95 %.1f -> %.1f %%' % (k, a[k][0], d[k][0], a[k][1], d[k][1]))
    return '\n'.join(lineas)


if __name__ == '__main__':
    print(comparar(sys.argv[1], sys.argv[2]))
