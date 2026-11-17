"""Exporta la base de Tarsis para Unreal Engine 5 (fase 1 del plan de migración).

Parte de la misma escena que el visor realista (tools/blender/escena_base.py con LH_GLB) y la deja lista para importar:
- cada objeto con su transformación aplicada, de modo que en Unreal todas las mallas se colocan en el origen;
- los materiales lh_<clave> con el color, rugosidad, metal y emisión del visor (escenario/visor.js), sin texturas todavía;
- tres marcas diminutas (lh_marca_o/x/z) para que montar_base.py deduzca en Unreal cómo quedaron los ejes;
- base.json con el plano, las luces y la casilla de salida de Cuttlas.

Uso (con el módulo bpy: pip install bpy):  python3 tools/unreal/exportar_base.py
Salida: assets/unreal/base.glb y assets/unreal/base.json
"""
import os, re, sys, json, math, subprocess, tempfile, shutil

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(R, 'assets', 'unreal')
os.makedirs(OUT, exist_ok=True)

# 1) la escena del visor, sin modelos de Poly Haven ni texturas (el aspecto final se hará con materiales de Unreal)
tmp = tempfile.mkdtemp()
glb0 = os.path.join(tmp, 'base.glb')
# LH_EXT: casillas que se aleja el muro perimetral respecto al plano del juego (tanda 20: 10 casillas = 20 m, con portones,
# camino y portillo; ver build_exterior en escena_base.py). El plano y todo lo de dentro quedan en las mismas coordenadas.
EXT = int(os.environ.get('LH_EXT', '10'))
env = dict(os.environ, LH_GLB=glb0, LH_NOPH='1', LH_NOTEX='1', LH_EXT=str(EXT))
subprocess.run([sys.executable, os.path.join(R, 'tools', 'blender', 'escena_base.py')], env=env, check=True,
               stdout=subprocess.DEVNULL)

import bpy
from mathutils import Vector, Matrix

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb0)

# fuera los maniquíes fijos de los personajes (gente_*, gear_*): en Unreal los guardias son actores con esqueleto
for o in [o for o in bpy.data.objects if o.name.split('.')[0].startswith(('gente_', 'gear_'))]:
    print('quitado', o.name)
    bpy.data.objects.remove(o)

# 2) aplicar transformaciones (las mallas compartidas se duplican primero)
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
for o in meshes:
    if o.data.users > 1:
        o.data = o.data.copy()
for o in meshes:
    o.data.transform(o.matrix_world)
    o.parent = None
    o.matrix_world.identity()
for o in [o for o in bpy.data.objects if o.type != 'MESH']:
    bpy.data.objects.remove(o)

# 3) materiales con los valores del visor
js = open(os.path.join(R, 'escenario', 'visor.js'), encoding='utf-8').read()
body = js[js.index('const M={'):]
body = body[:body.index('};') + 2] + js[js.index('M.hormigon=M.muro;'):].split('\n')[0]

def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

PAL = {}
for key, args in re.findall(r'(?:^|[\s,{.])([a-z_]+)\s*[:=]\s*std\(\{(.*?)\}\)', body, re.S):
    d = {}
    for k in ('color', 'emissive'):
        m = re.search(k + r':0x([0-9a-fA-F]{6})', args)
        if m:
            h = m.group(1)
            d[k] = [lin(int(h[i:i + 2], 16)) for i in (0, 2, 4)]
    for k in ('roughness', 'metalness', 'emissiveIntensity'):
        m = re.search(k + r':([0-9.]+)', args)
        if m:
            d[k] = float(m.group(1))
    PAL[key] = d
PAL.setdefault('hormigon', PAL.get('muro', {}))
# materiales del anillo exterior, que el visor no tiene: losa de hormigón del camino y tierra con grava
PAL.setdefault('camino', {'color': [lin(c) for c in (0x6e, 0x6d, 0x69)], 'roughness': 0.7})
PAL.setdefault('tierra', {'color': [lin(c) for c in (0x5a, 0x52, 0x46)], 'roughness': 0.9})
# tanda 22: alquitrán de las juntas y grietas selladas del camino (negro y algo brillante: de noche devuelve el reflejo de las farolas)
PAL.setdefault('alquitran', {'color': [lin(c) for c in (0x17, 0x17, 0x18)], 'roughness': 0.34})

for mat in bpy.data.materials:
    key = mat.name.split('.')[0][3:] if mat.name.startswith('lh_') else None
    d = PAL.get(key)
    if not d or not mat.use_nodes:
        continue
    b = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if not b:
        continue
    if 'color' in d:
        b.inputs['Base Color'].default_value = (*d['color'], 1)
    b.inputs['Roughness'].default_value = d.get('roughness', 0.7)
    b.inputs['Metallic'].default_value = d.get('metalness', 0.0)
    if 'emissive' in d:
        b.inputs['Emission Color'].default_value = (*d['emissive'], 1)
        b.inputs['Emission Strength'].default_value = d.get('emissiveIntensity', 1.0)

# 3b) farolas solo a la entrada de cada zona (Andres, 2026-11-12: «desentonan un poco»). Casillas del plano:
#     puerta del patio norte a la zona este, hueco de la valla norte, cancela de servicios y control de salida.
#     Las que ya están en una entrada se quedan; otras se mueven allí y las demás se quitan (farola y bombilla).
FAROLAS = [(17, 5), (16, 12), (26, 14), (28, 24)]
_T0 = json.load(open(os.path.splitext(glb0)[0] + '.json'))['T']
cen = lambda c: (c[0] * _T0 + _T0 / 2, -(c[1] * _T0 + _T0 / 2))
fobjs = [o for o in bpy.data.objects if o.type == 'MESH' and o.name.split('.')[0] == 'farola']
def fcell(o):
    xs = [v.co.x for v in o.data.vertices]; ys = [v.co.y for v in o.data.vertices]
    return (sum(xs) / len(xs), sum(ys) / len(ys))
old = {o: fcell(o) for o in fobjs}
want = [cen(c) for c in FAROLAS]
mov = {}   # posición vieja -> nueva (None = quitar)
libres = [w for w in want if not any(math.hypot(w[0] - p[0], w[1] - p[1]) < 0.6 for p in old.values())]
for o, p in sorted(old.items(), key=lambda kv: kv[1]):
    if any(math.hypot(w[0] - p[0], w[1] - p[1]) < 0.6 for w in want):
        mov[p] = p
    elif libres:
        # la más cercana de las entradas que faltan
        w = min(libres, key=lambda w: math.hypot(w[0] - p[0], w[1] - p[1])); libres.remove(w); mov[p] = w
        o.data.transform(Matrix.Translation((w[0] - p[0], w[1] - p[1], 0)))
    else:
        mov[p] = None; bpy.data.objects.remove(o)
bulbs = bpy.data.objects.get('luces_bombilla')
if bulbs:
    import bmesh
    bm = bmesh.new(); bm.from_mesh(bulbs.data); quitar = []
    for v in bm.verts:
        p = min(mov, key=lambda q: math.hypot(v.co.x - q[0], v.co.y - q[1]))
        if math.hypot(v.co.x - p[0], v.co.y - p[1]) > 0.8:
            continue
        if mov[p] is None:
            quitar.append(v)
        else:
            v.co.x += mov[p][0] - p[0]; v.co.y += mov[p][1] - p[1]
    bmesh.ops.delete(bm, geom=quitar, context='VERTS'); bm.to_mesh(bulbs.data); bm.free()
FAROLA_POS = [w for w in mov.values() if w]
print('FAROLAS', len(FAROLA_POS), FAROLA_POS)

# 4) marcas para deducir los ejes en Unreal (cubos de 2 cm en posiciones conocidas, coordenadas de Blender en metros)
MARCAS = {'lh_marca_o': (0, 0, 0), 'lh_marca_x': (10, 0, 0), 'lh_marca_y': (0, 10, 0), 'lh_marca_z': (0, 0, 10)}
for name, p in MARCAS.items():
    me = bpy.data.meshes.new(name)
    s = 0.01
    v = [Vector(p) + Vector((x, y, z)) for x in (-s, s) for y in (-s, s) for z in (-s, s)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(v, [], f)
    bpy.context.scene.collection.objects.link(bpy.data.objects.new(name, me))

# 4b) torres de vigilancia: en el visor se levantan en escenario/visor.js (TOWERS), no en Blender; aquí se copian
#     con las mismas piezas (madera y hierro) para que estén en Unreal. Coordenadas del visor (three.js, y arriba)
#     -> Blender: (x, y, z) -> (x, -z, y).
from mathutils import Matrix
vjs = open(os.path.join(R, 'escenario', 'visor.js'), encoding='utf-8').read()
TWH = float(re.search(r'const TWH=([0-9.]+)', vjs).group(1))
TOWERS = [dict(tx=int(a), ty=int(b), yaw=float(c)) for a, b, c in
          re.findall(r'\{tx:(\d+),ty:(\d+),yaw:(-?[0-9.]+)\}', vjs[vjs.index('TOWERS=['):vjs.index('TOWERS=[') + 300])]
TT = json.load(open(os.path.splitext(glb0)[0] + '.json'))['T']

def mat_lh(key):
    m = bpy.data.materials.get('lh_' + key)
    if m:
        return m
    m = bpy.data.materials.new('lh_' + key)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    d = PAL.get(key, {})
    if 'color' in d:
        b.inputs['Base Color'].default_value = (*d['color'], 1)
    b.inputs['Roughness'].default_value = d.get('roughness', 0.7)
    b.inputs['Metallic'].default_value = d.get('metalness', 0.0)
    return m

def malla(nombre, L, key, mat=None):
    """Una malla de cajas. L: (sx, sy, sz, px, py, pz, rx, ry, rz) en coordenadas del visor (three.js, orden XYZ)."""
    verts, faces = [], []
    for sx, sy, sz, px, py, pz, rx, ry, rz in L:
        M3 = Matrix.Rotation(rx, 3, 'X') @ Matrix.Rotation(ry, 3, 'Y') @ Matrix.Rotation(rz, 3, 'Z')
        n = len(verts)
        for cx in (-0.5, 0.5):
            for cy in (-0.5, 0.5):
                for cz in (-0.5, 0.5):
                    v = M3 @ Vector((cx * sx, cy * sy, cz * sz)) + Vector((px, py, pz))
                    verts.append((v.x, -v.z, v.y))
        faces += [tuple(n + k for k in f) for f in
                  ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))]
    me = bpy.data.meshes.new(nombre)
    me.from_pydata(verts, [], faces)
    me.validate()
    me.materials.append(mat or mat_lh(key))
    bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me))

def torre(i, t):
    x, z = t['tx'] * TT + TT / 2, t['ty'] * TT + TT / 2
    W, I = [], []
    def B(L, sx, sy, sz, px, py, pz, rz=0.0, rx=0.0):
        L.append((sx, sy, sz, px, py, pz, rz, rx))
    for a in (-0.95, 0.95):
        for b in (-0.95, 0.95):
            B(W, 0.15, TWH, 0.15, x + a, TWH / 2, z + b); B(W, 0.08, 1.05, 0.08, x + a, TWH + 0.55, z + b)
            B(I, 0.06, 2.3, 0.06, x + a, TWH + 1.15, z + b)
    B(W, 2.2, 0.1, 2.2, x, TWH, z)
    for h in (1.6, 3.1):
        B(W, 2.0, 0.08, 0.08, x, h, z - 0.95); B(W, 2.0, 0.08, 0.08, x, h, z + 0.95)
        B(W, 0.08, 0.08, 2.0, x - 0.95, h, z); B(W, 0.08, 0.08, 2.0, x + 0.95, h, z)
    for q in (-0.95, 0.95):
        B(W, 2.6, 0.07, 0.07, x, 2.35, z + q, 0.62); B(W, 2.6, 0.07, 0.07, x, 2.35, z + q, -0.62)
        B(W, 0.07, 0.07, 2.6, x + q, 2.35, z, 0, 0.62); B(W, 0.07, 0.07, 2.6, x + q, 2.35, z, 0, -0.62)
    for h in (0.55, 1.05):   # barandilla, abierta donde llega la escala
        B(W, 2.0, 0.07, 0.06, x, TWH + h, z - 0.95); B(W, 2.0, 0.07, 0.06, x, TWH + h, z + 0.95)
        B(W, 0.06, 0.07, 2.0, x - 0.95, TWH + h, z)
        B(W, 0.06, 0.07, 0.55, x + 0.95, TWH + h, z - 0.7); B(W, 0.06, 0.07, 0.55, x + 0.95, TWH + h, z + 0.7)
    B(I, 2.6, 0.05, 2.6, x, TWH + 2.32, z, 0.05)
    for b in (-0.24, 0.24):
        B(W, 0.05, TWH + 1.1, 0.05, x + 1.13, (TWH + 1.1) / 2, z + b)
    h = 0.3
    while h < TWH + 0.9:
        B(W, 0.035, 0.035, 0.5, x + 1.13, h, z); h += 0.3
    for L, key in ((W, 'madera'), (I, 'hierro')):
        malla('torre%d_%s' % (i + 1, key), [(q[0], q[1], q[2], q[3], q[4], q[5], q[7], 0.0, q[6]) for q in L], key)
    # el foco cuelga bajo el tejadillo y mira hacia donde mira el centinela (como spotTick del visor, sin bajar)
    ph = 0.27
    return {'name': 'torre%d' % (i + 1), 'pos': [x, -z, 0.0], 'yaw': t['yaw'], 'altura': TWH,
            'escala': [x + 1.75, -z, 0.0],
            'foco': {'pos': [x - 0.25, -z, TWH + 2.05],
                     'dir': [math.sin(t['yaw']) * math.cos(ph), -math.cos(t['yaw']) * math.cos(ph), -math.sin(ph)]}}

import math
TORRES = [torre(i, t) for i, t in enumerate(TOWERS)]

# 4b bis) tanda 30: cuatro torres grandes, una en cada esquina del muro perimetral (por dentro), más altas que el muro.
# Plataforma de 4,4 m para dos centinelas, cada uno con su foco: uno mira hacia dentro de la base y otro hacia fuera.
# Los focos van en las dos esquinas de la plataforma que caen sobre la diagonal (la de dentro y la de fuera).
TG = 6.0   # altura de la plataforma (el muro mide 4,6)

def torre_grande(i, cx, cz):
    L = {'madera': [], 'hierro': []}
    def B(key, sx, sy, sz, px, py, pz, rx=0.0, ry=0.0, rz=0.0):
        L[key].append((sx, sy, sz, cx + px, py, cz + pz, rx, ry, rz))
    for a in (-1.9, 1.9):
        for b in (-1.9, 1.9):
            B('madera', 0.24, TG, 0.24, a, TG / 2, b)                       # patas
            B('madera', 0.12, 2.45, 0.12, a, TG + 1.22, b)                  # pies derechos del tejadillo
            B('hierro', 0.5, 0.25, 0.5, a, 0.12, b)                         # zapatas
    B('madera', 4.4, 0.14, 4.4, 0, TG, 0)                                   # plataforma
    for h in (1.8, 3.6, 5.3):                                               # travesaños
        for q in (-1.9, 1.9):
            B('madera', 3.8, 0.1, 0.1, 0, h, q); B('madera', 0.1, 0.1, 3.8, q, h, 0)
    for h0, h1 in ((0.2, 3.6), (3.6, TG)):                                  # cruces de San Andrés en los cuatro lados, dos pisos
        lar = math.hypot(3.8, h1 - h0); ang = math.atan2(h1 - h0, 3.8); hm = (h0 + h1) / 2
        for q in (-1.9, 1.9):
            for sg in (-1, 1):
                B('madera', lar, 0.08, 0.08, 0, hm, q, rz=sg * ang)
                B('madera', 0.08, 0.08, lar, q, hm, 0, rx=sg * ang)
    for q in (-2.1, 2.1):                                                   # peto de tablas y pasamanos; el lado +x se abre para la escala
        B('madera', 4.2, 0.55, 0.04, 0, TG + 0.36, q); B('madera', 4.2, 0.07, 0.07, 0, TG + 1.1, q)
    B('madera', 0.04, 0.55, 4.2, -2.1, TG + 0.36, 0); B('madera', 0.07, 0.07, 4.2, -2.1, TG + 1.1, 0)
    for b in (-1.35, 1.35):
        B('madera', 0.04, 0.55, 1.5, 2.1, TG + 0.36, b); B('madera', 0.07, 0.07, 1.5, 2.1, TG + 1.1, b)
    B('hierro', 5.2, 0.06, 5.2, 0, TG + 2.48, 0, rz=0.04)                   # tejadillo de chapa
    for b in (-0.26, 0.26):                                                 # escala
        B('madera', 0.06, TG + 1.1, 0.06, 2.3, (TG + 1.1) / 2, b)
    h = 0.3
    while h < TG + 0.9:
        B('madera', 0.04, 0.04, 0.55, 2.3, h, 0); h += 0.3
    # hacia dentro: la diagonal que apunta al centro de la base
    ux, uz = (1.0 if cx < 36 else -1.0) / math.sqrt(2), (1.0 if cz < 28 else -1.0) / math.sqrt(2)
    puestos = []
    for rol, sg, baja in (('dentro', 1.0, 0.38), ('fuera', -1.0, 0.30)):
        fx, fz = sg * ux * 2.75, sg * uz * 2.75                             # el proyector, en su esquina
        B('hierro', 0.5, 0.5, 0.42, fx, TG + 1.55, fz, ry=math.pi / 4)
        B('hierro', 0.09, 1.3, 0.09, fx, TG + 0.65, fz)
        lx, lz = cx + sg * ux * 3.25, cz + sg * uz * 3.25                   # la luz, medio metro por delante de la carcasa
        puestos.append({'rol': rol, 'pos': [cx + sg * ux * 1.5, -(cz + sg * uz * 1.5), 0.0],
                        'foco': {'pos': [lx, -lz, TG + 1.5], 'dir': [sg * ux * math.cos(baja), -sg * uz * math.cos(baja), -math.sin(baja)]}})
    for key in ('madera', 'hierro'):
        malla('torre%d_%s' % (i + 1, key), L[key], key)
    return {'name': 'torre%d' % (i + 1), 'pos': [cx, -cz, 0.0], 'yaw': math.atan2(ux, -uz), 'altura': TG, 'grande': True,
            'escala': [cx + 2.9, -cz, 0.0], 'foco': puestos[0]['foco'], 'puestos': puestos}

ESQUINAS = [(-15.0, -15.0), (87.0, -15.0), (87.0, 71.0), (-15.0, 71.0)] if os.environ.get('LH_EXT', '10') != '0' else []   # NO, NE, SE, SO
N_TORRES_VIEJAS = len(TORRES)
TORRES += [torre_grande(N_TORRES_VIEJAS + k, cx, cz) for k, (cx, cz) in enumerate(ESQUINAS)]

# 4c) recintos del visor (v51): vallas de tela metálica (f), huecos para pasar agachado (h) y contenedores (m).
#     El plano se parchea como en visor.js y se levanta la misma geometría.
MAP = list(json.load(open(os.path.splitext(glb0)[0] + '.json'))['map'])
MAP = [r.replace('l', '.') for r in MAP]   # en el plano, solo las farolas que quedan
for fx, fy in FAROLAS:
    MAP[fy] = MAP[fy][:fx] + 'l' + MAP[fy][fx + 1:]
pre = vjs[:vjs.index('KONT.forEach(k=>{ for')]
KONT = json.loads(re.search(r'const KONT=(\[\[.*?\]\]);', vjs).group(1))
def put(x, y, t):
    MAP[y] = MAP[y][:x] + t + MAP[y][x + len(t):]
for a, b, t in re.findall(r"put\((\d+),(\d+),'([fhm]+)'\)", pre):
    put(int(a), int(b), t)
for k in KONT:
    for i in range(k[3]):
        put(k[0] + (i if k[2] else 0), k[1] + (0 if k[2] else i), 'm')

def mat_rgb(nombre, rgb, rough, metal):
    m = bpy.data.materials.get(nombre) or bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (*[lin(c) for c in rgb], 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m

ROWS, COLS = len(MAP), max(len(r) for r in MAP)
JEXT = json.load(open(os.path.splitext(glb0)[0] + '.json')).get('ext')
ANILLO = {}   # casillas de fuera del plano: vallas del anillo y muro nuevo
if JEXT:
    E = JEXT['casillas']; conserva = {tuple(c) for c in JEXT['conserva']}
    for x in range(-E, COLS + E):
        for y in range(-E, ROWS + E):
            if x in (-E, COLS + E - 1) or y in (-E, ROWS + E - 1):
                ANILLO[(x, y)] = '.' if (y in JEXT['filas_porton'] and x in (-E, COLS + E - 1)) else '#'
    for x0, y0, x1, y1 in JEXT.get('tabiques', []):
        for y in range(y0, y1 + 1):
            ANILLO[(x0, y)] = '#'
    # vallas que antes morían en el muro y ahora cruzan el anillo hasta el muro nuevo, cada una con su hueco para pasar agachado:
    # así el anillo no sirve de atajo entre zonas. [fila, primera columna, última columna, columna del hueco]
    VALLAS_ANILLO = [(10, -E + 1, -1, -5), (12, COLS - 1, COLS + E - 2, COLS + 4), (23, COLS - 1, COLS + E - 2, COLS + 3)]
    for fila, c0, c1, hueco in VALLAS_ANILLO:
        for x in range(c0, c1 + 1):
            ANILLO[(x, fila)] = 'h' if x == hueco else 'f'
    JEXT['vallas'] = [list(v) for v in VALLAS_ANILLO]
def ch(x, y):
    if (x, y) in ANILLO:
        return ANILLO[(x, y)]
    if 0 <= y < ROWS and 0 <= x < len(MAP[y]):
        if JEXT and (x in (0, COLS - 1) or y in (0, ROWS - 1)) and MAP[y][x] == '#':
            return '#' if (x, y) in conserva else '.'   # el muro antiguo ya no está, salvo donde hace de pared de un edificio
        return MAP[y][x]
    return '.' if JEXT and -JEXT['casillas'] < x < COLS + JEXT['casillas'] - 1 and -JEXT['casillas'] < y < ROWS + JEXT['casillas'] - 1 else '#'
EX = JEXT['casillas'] if JEXT else 0
isF = lambda x, y: ch(x, y) in 'fh'
solido = lambda x, y: ch(x, y) in 'fh#W'
# para decidir hacia dónde corre cada valla cuenta también el muro antiguo: las de dentro quedan como estaban
con = lambda x, y: solido(x, y) or (0 <= y < ROWS and 0 <= x < len(MAP[y]) and MAP[y][x] == '#')
H, HH, PI = 2.3, 0.85, math.pi
arms, holes, posts = [], [], []
for y in range(-EX, ROWS + EX):
    for x in range(-EX, COLS + EX):
        if not isF(x, y):
            continue
        cx, cz = x * TT + TT / 2, y * TT + TT / 2
        ds = [d for d in ((1, 0), (-1, 0), (0, 1), (0, -1)) if con(x + d[0], y + d[1])]
        if len(ds) == 1:
            ds = [ds[0], (-ds[0][0], -ds[0][1])]
        posts.append((cx, cz, 0))
        for d in ds:
            (holes if ch(x, y) == 'h' else arms).append((cx + d[0] * 0.5, cz + d[1] * 0.5, 0 if d[0] else PI / 2))
            if not solido(x + d[0], y + d[1]):
                posts.append((cx + d[0], cz + d[1], 0.5))
tela, hierro = [], []
for q in arms:   # la tela: placa fina (en Unreal se le pondrá un material de malla con transparencia)
    tela.append((1.0, H, 0.015, q[0], H / 2, q[1], 0, q[2], 0))
for q in holes:
    tela.append((1.0, H - HH, 0.015, q[0], HH + (H - HH) / 2, q[1], 0, q[2], 0))
for q in posts:
    hh = H + 0.3 + q[2]
    hierro.append((0.07, hh, 0.07, q[0], hh / 2, q[1], 0, 0, 0))
for q in arms + holes:
    hierro += [(1.0, r, r, q[0], yy, q[1], 0, q[2], 0) for yy, r in ((H, 0.05), (H + 0.14, 0.018), (H + 0.27, 0.018))]
for q in holes:
    hierro.append((1.0, 0.02, 0.02, q[0], HH, q[1], 0, q[2], 0))
# cancelas abiertas, plegadas contra la valla (hoja de 1,9 m)
for gx, gz, yaw in ((20 * TT, 15 * TT + TT / 2 + 0.1, PI), (22 * TT, 15 * TT + TT / 2 + 0.1, 0), (29 * TT + TT / 2 + 0.1, 25 * TT, PI / 2)):
    c, s_ = math.cos(yaw), math.sin(yaw)
    P = lambda lx, ly: (gx + lx * c, ly, gz - lx * s_)   # rotación en Y de three.js: x' = x cos, z' = -x sin
    p = P(0.98, H / 2 - 0.02); tela.append((1.9, H - 0.15, 0.015, p[0], p[1], p[2], 0, yaw, 0))
    for ly in (H - 0.08, 0.12):
        p = P(0.98, ly); hierro.append((1.9, 0.05, 0.05, p[0], p[1], p[2], 0, yaw, 0))
    p = P(1.93, H / 2 - 0.02); hierro.append((0.05, H - 0.2, 0.05, p[0], p[1], p[2], 0, yaw, 0))
malla('valla_tela', tela, None, mat_rgb('lh_tela', (167, 173, 173), 0.5, 0.6))
malla('valla_hierro', hierro, 'hierro')
# contenedores de 20 pies, cuatro colores como en el visor; los dobles llevan otro encima algo girado
KC = [(0x6a, 0x2c, 0x20), (0x28, 0x46, 0x5a), (0x3a, 0x55, 0x37), (0x77, 0x67, 0x2a)]
kont = [[] for _ in KC]
# tanda 25: la chapa de verdad. Cada contenedor era una caja lisa; ahora lleva encima, en otra malla (contenedordet_N, que
# en Unreal no tiene colisión: se anda, se dispara y se mira contra la caja de siempre), los pilares de las esquinas, los
# largueros de arriba y de abajo, las costillas de la chapa ondulada en los costados, el testero y el techo, y en el otro
# testero las puertas con sus cuatro barras de cierre. Unos 80 prismas por contenedor.
kdet = [[] for _ in KC]
def detalle_contenedor(col, largo, alto, ancho, cx, cy, cz, giro, puertas):
    c_, s_ = math.cos(giro), math.sin(giro)
    D = kdet[col % 4]
    def B(sx, sy, sz, ox, oy, oz):     # prisma en los ejes del contenedor (x a lo largo, y arriba, z a lo ancho)
        D.append((sx, sy, sz, cx + ox * c_ + oz * s_, cy + oy, cz - ox * s_ + oz * c_, 0, giro, 0))
    hx, hy, hz = largo / 2, alto / 2, ancho / 2
    for ex in (-1, 1):
        for ez in (-1, 1):             # pilares: sobresalen 2,5 cm por los dos lados
            B(0.17, alto + 0.03, 0.17, ex * (hx - 0.06), 0, ez * (hz - 0.06))
    for ey in (-1, 1):                 # largueros y travesaños
        for ez in (-1, 1):
            B(largo - 0.3, 0.15, 0.06, 0, ey * (hy - 0.075), ez * (hz + 0.005))
        for ex in (-1, 1):
            B(0.06, 0.15, ancho - 0.3, ex * (hx + 0.005), ey * (hy - 0.075), 0)
    n = int((largo - 0.5) / 0.26)      # costillas de los costados, cada 26 cm
    for i in range(n):
        ox = (i - (n - 1) / 2) * 0.26
        for ez in (-1, 1):
            B(0.11, alto - 0.3, 0.036, ox, 0, ez * (hz + 0.012))
    m_ = int((ancho - 0.4) / 0.26)
    for i in range(m_):                # testero ciego
        B(0.036, alto - 0.3, 0.11, -puertas * (hx + 0.012), 0, (i - (m_ - 1) / 2) * 0.26)
    # puertas: el canto de las dos hojas, las cuatro barras de cierre con su maneta y las bisagras
    px = puertas * (hx + 0.02)
    B(0.03, alto - 0.32, 0.035, px - puertas * 0.005, 0, 0)
    for oz in (-0.66, -0.24, 0.24, 0.66):
        B(0.04, alto - 0.2, 0.04, px + puertas * 0.012, 0, oz)
        B(0.035, 0.05, 0.2, px + puertas * 0.03, -0.25, oz + (0.09 if oz < 0 else -0.09))
        for oy in (-0.8, 0.8):
            B(0.05, 0.09, 0.07, px + puertas * 0.012, oy, oz)
    for ez in (-1, 1):
        for oy in (-0.95, -0.3, 0.35, 0.98):
            B(0.05, 0.12, 0.05, px, oy, ez * (hz - 0.2))
    t = int((largo - 0.4) / 0.52)      # techo: costillas atravesadas, cada 52 cm
    for i in range(t):
        B(0.12, 0.03, ancho - 0.28, (i - (t - 1) / 2) * 0.52, hy + 0.008, 0)
for i, k in enumerate(KONT):
    L = k[3]
    def caja(col, y, dx, ry):
        q = (L * TT - 0.12, 2.6, TT - 0.1, (k[0] + (L / 2 if k[2] else 0.5)) * TT + dx, y,
             (k[1] + (0.5 if k[2] else L / 2)) * TT, 0, (0 if k[2] else PI / 2) + ry, 0)
        kont[col % 4].append(q)
        detalle_contenedor(col, q[0], q[1], q[2], q[3], q[4], q[5], q[7], 1 if (i + col) % 2 else -1)
    caja(i, 1.3, 0, 0)
    if k[4]:
        caja(i + 2, 3.9, 0.12, 0.03)
for c, L in enumerate(kont):
    if L:
        malla('contenedor_%d' % c, L, None, mat_rgb('lh_contenedor_%d' % c, KC[c], 0.62, 0.35))
        malla('contenedordet_%d' % c, kdet[c], None, mat_rgb('lh_contenedor_%d' % c, KC[c], 0.62, 0.35))

# 4d) tanda 22: hierbajos al pie de las vallas y del muro, en los bordes del camino y en alguna junta de la losa. Una sola malla
#     («hierbajos») de planos cruzados con sus propias UV sobre la textura de cuatro matas (tools/texturas/hierbajo.py); cada plano
#     va por las dos caras y con la normal hacia arriba, para que la luz le dé como al suelo que pisa. En Unreal lleva el material
#     recortado M_Hierbajo, sin colisión, sin sombra y sin contar para la navegación (tools/unreal/montar_base.py).
import random
def hierbajos():
    rs = random.Random(2207); V, F, UV = [], [], []
    TAM = (0.78, 0.6, 0.92, 0.56)     # lado del plano de cada mata (m): hierba seca alta, mata verde, cardo, roseta
    def mata(px, py, z=0.0, k=1.0, var=None):
        v = var if var is not None else rs.choices((0, 1, 2, 3), (35, 35, 12, 18))[0]
        s = TAM[v] * k * rs.uniform(0.72, 1.25); w, h = s * rs.uniform(0.9, 1.15), s * rs.uniform(0.9, 1.1)
        a0 = rs.uniform(0, PI); c, r = v % 2, v // 2; pad = 0.004
        u0, u1 = c * 0.5 + pad, (c + 1) * 0.5 - pad
        vb, vt = 1 - (r + 1) * 0.5 + pad, 1 - r * 0.5 - pad
        lx, ly = rs.uniform(-0.07, 0.07) * h, rs.uniform(-0.07, 0.07) * h     # ninguna sale a plomo
        for a in (a0, a0 + PI / 2 + rs.uniform(-0.25, 0.25)):
            dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2
            if rs.random() < 0.5: u0, u1 = u1, u0
            q = [(px - dx, py - dy, z - 0.025), (px + dx, py + dy, z - 0.025), (px + dx + lx, py + dy + ly, z + h - 0.025), (px - dx + lx, py - dy + ly, z + h - 0.025)]
            uv = [(u0, vb), (u1, vb), (u1, vt), (u0, vt)]
            for orden in ((0, 1, 2, 3), (3, 2, 1, 0)):
                n = len(V); V.extend((q[i][0], -q[i][1], q[i][2]) for i in orden); UV.extend(uv[i] for i in orden); F.append((n, n + 1, n + 2, n + 3))
    def linea(xa, ya, xb, yb, nx, ny, dens, z=0.0, k=1.0, saltos=()):
        """Matas al pie de una línea (muro, bordillo). (nx, ny): hacia dónde se separan de ella; saltos: tramos, en metros desde
        el principio, que se dejan limpios. Salen a rodales, no repartidas por igual."""
        L = math.hypot(xb - xa, yb - ya); f = rs.uniform(0, 6.28); s = rs.uniform(0, 0.5)
        while s < L:
            rodal = 0.5 + 0.5 * math.sin(s * 0.41 + f) * math.sin(s * 0.13 + f * 2.7)
            if rs.random() < dens * (0.15 + 1.7 * rodal) and not any(a <= s <= b for a, b in saltos):
                d = rs.uniform(0.04, 0.2); t = s / L; mata(xa + (xb - xa) * t + nx * d, ya + (yb - ya) * t + ny * d, z, k)
            s += rs.uniform(0.3, 0.7)
    def corro(px, py, r0, r1, n, k=1.0, z=0.0):
        for _ in range(n):
            a = rs.uniform(0, 2 * PI); r = rs.uniform(r0, r1); mata(px + math.cos(a) * r, py + math.sin(a) * r, z, k)
    # 1) las vallas: las del anillo, tupidas (nadie las desbroza); las de dentro, alguna mata suelta. Los huecos de pasar agachado, limpios
    for qx, qz, rot in arms:
        fuera = qx < 0 or qx > COLS * TT or qz < 0 or qz > ROWS * TT
        for _ in range(2 if fuera else 1):
            if rs.random() < (0.62 if fuera else 0.3):
                u = rs.uniform(-0.48, 0.48); d = rs.choice((-1, 1)) * rs.uniform(0.04, 0.16)
                mata(qx + (u if rot == 0 else d), qz + (d if rot == 0 else u), 0.0, 1.0 if fuera else 0.8)
    if JEXT:
        X0, X1, Y0, Y1 = JEXT['x0'], JEXT['x1'], JEXT['y0'], JEXT['y1']; cam = JEXT['camino']
        ya, yb = cam['y'] - cam['ancho'] / 2, cam['y'] + cam['ancho'] / 2; zl = cam['alto']
        xi0, xi1, yi0, yi1 = X0 + 1.45, X1 - 1.45, Y0 + 1.45, Y1 - 1.45          # caras de dentro del muro
        # 2) pie del muro por dentro. Sin matas en los portones ni en el carril de las hojas correderas (al sur de cada portón), ni en el portillo
        px = JEXT['portillo'][0]; carril = (ya - 1.0 - yi0, yb + 7.6 - yi0)
        linea(xi0, yi0, xi1, yi0, 0, 1, 0.22)
        linea(xi0, yi1, xi1, yi1, 0, -1, 0.24, saltos=((px - 1.0 - xi0, px + 1.0 - xi0),))
        linea(xi0, yi0, xi0, yi1, 1, 0, 0.22, saltos=(carril,))
        linea(xi1, yi0, xi1, yi1, -1, 0, 0.22, saltos=(carril,))
        # 3) bordes del camino por fuera del bordillo: dentro de la base y los primeros 45 m del terraplén (más crecidos: ahí no pisa nadie)
        for yy, s in ((ya - 0.22, -1), (yb + 0.22, 1)):
            linea(X0 + 2.2, yy, X1 - 2.2, yy, 0, s, 0.2)
            linea(X0 - 45.0, yy, X0 - 0.7, yy, 0, s, 0.42, z=-0.02, k=1.15)
            linea(X1 + 0.7, yy, X1 + 45.0, yy, 0, s, 0.42, z=-0.02, k=1.15)
        for k in range(8):       # y al pie de los hitos del terraplén
            for q in (-5.6, 5.6):
                for xh in (X0 - 3 - k * 6, X1 + 3 + k * 6):
                    if rs.random() < 0.6: corro(xh, cam['y'] + q, 0.14, 0.3, rs.randint(1, 3), 1.1, -0.02)
        # 4) al pie de las farolas, de los báculos de los portones y de las garitas (por los lados que no dan al camino)
        for fx, fy, _ in JEXT.get('farolas', []): corro(fx, yb + 0.5, 0.24, 0.42, rs.randint(2, 4))
        for key in ('entrada', 'salida'):
            g = JEXT[key]; corro(g['baculo'][0], g['baculo'][1] - 0.1, 0.24, 0.4, 2, 0.8)
            gx, gy = g['garita']
            linea(gx - 1.35, gy - 1.38, gx + 1.35, gy - 1.38, 0, -1, 0.5)
            lado = -1 if key == 'entrada' else 1       # el lado contrario a la puerta
            linea(gx + lado * 1.38, gy - 1.3, gx + lado * 1.38, gy + 1.0, lado, 0, 0.45)
        # 5) en la losa: una mata pequeña donde alguna junta llega al bordillo y en la punta de alguna grieta
        for xj in JEXT['desgaste']['juntas']:
            for yy, s in ((ya, 1), (yb, -1)):
                if rs.random() < 0.5: mata(xj + rs.uniform(-0.05, 0.05), yy + s * rs.uniform(0.05, 0.16), zl, rs.uniform(0.38, 0.55), rs.choice((1, 1, 3, 0)))
        for gx0, gy0, gx1, gy1 in JEXT['desgaste']['grietas']:
            if X0 + 2 < gx1 < X1 - 2 and rs.random() < 0.5 and abs(gy1 - cam['y']) > 1.3:
                mata(gx1, gy1, zl, rs.uniform(0.32, 0.46), rs.choice((1, 3)))
    me = bpy.data.meshes.new('hierbajos'); me.from_pydata(V, [], F)
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices): uvl.data[li].uv = UV[vi]
    me.normals_split_custom_set([(0.0, 0.0, 1.0)] * len(me.loops))
    me.materials.append(mat_rgb('lh_hierbajo', (84, 98, 52), 0.85, 0.0))
    bpy.context.scene.collection.objects.link(bpy.data.objects.new('hierbajos', me))
    return len(F) // 4
N_MATAS = hierbajos()
if JEXT: JEXT['hierbajos'] = N_MATAS
print('HIERBAJOS', N_MATAS, 'matas')

glb = os.path.join(OUT, 'base.glb')
kw = dict(filepath=glb, export_format='GLB', export_yup=True, export_cameras=False, export_lights=False,
          export_animations=False)
bpy.ops.export_scene.gltf(**kw)

# 5) base.json: plano, luces y salida
j = json.load(open(os.path.splitext(glb0)[0] + '.json'))
T = j['T']
spawn = None
for y, row in enumerate(j['map']):
    x = row.find('P')
    if x >= 0:
        spawn = [x * T + T / 2, -(y * T + T / 2), 0.0]
# los focos de torreta del visor cuelgan de las torres (en Blender estaban en las torretas antiguas)
lights = [l for l in j['lights'] if l.get('name') not in ('foco_torreta', 'farola')]
f0 = next(l for l in j['lights'] if l.get('name') == 'farola')
for w in FAROLA_POS:
    lights.append(dict(f0, pos=[w[0], w[1], f0['pos'][2]]))
if JEXT:   # báculo del portón de entrada (el farol de la salida lo crea el director junto a la barrera)
    q = JEXT['entrada']['farol']
    lights.append(dict(f0, pos=[q[0], -q[1], q[2] + 0.2]))
for tw in TORRES[:N_TORRES_VIEJAS]:
    lights.append({'kind': 'SPOT', 'name': 'foco_torreta', 'pos': tw['foco']['pos'], 'dir': tw['foco']['dir'],
                   'color': [0.8, 0.9, 1.0], 'power': 90000})
if JEXT:   # tanda 21: farolas del camino y aplique del portillo. Al final de la lista: las luces de antes conservan su número
    for q in JEXT.get('farolas', []):
        lights.append(dict(f0, pos=[q[0], -q[1], q[2] + 0.2]))
    if JEXT.get('portillo_luz'):
        q = JEXT['portillo_luz']
        lights.append({'kind': 'POINT', 'name': 'aplique', 'pos': [q[0], -q[1], q[2]], 'color': [1.0, 0.7, 0.4], 'power': 260})
# tanda 30: los ocho focos de las torres de esquina, al final (las luces de antes conservan su número)
for tw in TORRES[N_TORRES_VIEJAS:]:
    for pu in tw['puestos']:
        lights.append({'kind': 'SPOT', 'name': 'foco_torreta', 'pos': pu['foco']['pos'], 'dir': pu['foco']['dir'],
                       'color': [0.8, 0.9, 1.0], 'power': 90000})
json.dump({'T': T, 'map': MAP, 'lights': lights, 'spawn': spawn, 'marcas': MARCAS, 'torres': TORRES,
           **({'ext': JEXT} if JEXT else {}), 'mallas': len([o for o in bpy.data.objects if o.type == 'MESH'])},
          open(os.path.join(OUT, 'base.json'), 'w'), indent=1)
shutil.rmtree(tmp, ignore_errors=True)
n = len([o for o in bpy.data.objects if o.type == 'MESH'])
print('UNREAL', glb, os.path.getsize(glb) // 1024, 'KB,', n, 'mallas,', len(PAL), 'materiales del visor')
