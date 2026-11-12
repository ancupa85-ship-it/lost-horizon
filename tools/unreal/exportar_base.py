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
env = dict(os.environ, LH_GLB=glb0, LH_NOPH='1', LH_NOTEX='1')
subprocess.run([sys.executable, os.path.join(R, 'tools', 'blender', 'escena_base.py')], env=env, check=True,
               stdout=subprocess.DEVNULL)

import bpy
from mathutils import Vector, Matrix

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb0)

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
ch = lambda x, y: (MAP[y] if 0 <= y < ROWS else '')[x] if 0 <= y < ROWS and 0 <= x < len(MAP[y]) else '#'
isF = lambda x, y: ch(x, y) in 'fh'
con = lambda x, y: ch(x, y) in 'fh#W'
H, HH, PI = 2.3, 0.85, math.pi
arms, holes, posts = [], [], []
for y in range(ROWS):
    for x in range(len(MAP[y])):
        if not isF(x, y):
            continue
        cx, cz = x * TT + TT / 2, y * TT + TT / 2
        ds = [d for d in ((1, 0), (-1, 0), (0, 1), (0, -1)) if con(x + d[0], y + d[1])]
        if len(ds) == 1:
            ds = [ds[0], (-ds[0][0], -ds[0][1])]
        posts.append((cx, cz, 0))
        for d in ds:
            (holes if ch(x, y) == 'h' else arms).append((cx + d[0] * 0.5, cz + d[1] * 0.5, 0 if d[0] else PI / 2))
            if not con(x + d[0], y + d[1]):
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
for i, k in enumerate(KONT):
    L = k[3]
    def caja(col, y, dx, ry):
        kont[col % 4].append((L * TT - 0.12, 2.6, TT - 0.1, (k[0] + (L / 2 if k[2] else 0.5)) * TT + dx, y,
                              (k[1] + (0.5 if k[2] else L / 2)) * TT, 0, (0 if k[2] else PI / 2) + ry, 0))
    caja(i, 1.3, 0, 0)
    if k[4]:
        caja(i + 2, 3.9, 0.12, 0.03)
for c, L in enumerate(kont):
    if L:
        malla('contenedor_%d' % c, L, None, mat_rgb('lh_contenedor_%d' % c, KC[c], 0.62, 0.35))

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
for tw in TORRES:
    lights.append({'kind': 'SPOT', 'name': 'foco_torreta', 'pos': tw['foco']['pos'], 'dir': tw['foco']['dir'],
                   'color': [0.8, 0.9, 1.0], 'power': 90000})
json.dump({'T': T, 'map': MAP, 'lights': lights, 'spawn': spawn, 'marcas': MARCAS, 'torres': TORRES,
           'mallas': len([o for o in bpy.data.objects if o.type == 'MESH'])},
          open(os.path.join(OUT, 'base.json'), 'w'), indent=1)
shutil.rmtree(tmp, ignore_errors=True)
n = len([o for o in bpy.data.objects if o.type == 'MESH'])
print('UNREAL', glb, os.path.getsize(glb) // 1024, 'KB,', n, 'mallas,', len(PAL), 'materiales del visor')
