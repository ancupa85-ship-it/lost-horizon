"""Exporta la base de Tarsis para Unreal Engine 5 (fase 1 del plan de migración).

Parte de la misma escena que el visor realista (tools/blender/escena_base.py con LH_GLB) y la deja lista para importar:
- cada objeto con su transformación aplicada, de modo que en Unreal todas las mallas se colocan en el origen;
- los materiales lh_<clave> con el color, rugosidad, metal y emisión del visor (escenario/visor.js), sin texturas todavía;
- tres marcas diminutas (lh_marca_o/x/z) para que montar_base.py deduzca en Unreal cómo quedaron los ejes;
- base.json con el plano, las luces y la casilla de salida de Cuttlas.

Uso (con el módulo bpy: pip install bpy):  python3 tools/unreal/exportar_base.py
Salida: assets/unreal/base.glb y assets/unreal/base.json
"""
import os, re, sys, json, subprocess, tempfile, shutil

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
from mathutils import Vector

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
        verts, faces = [], []
        for sx, sy, sz, px, py, pz, rz, rx in L:
            M3 = Matrix.Rotation(rx, 3, 'X') @ Matrix.Rotation(rz, 3, 'Z')   # three.js, orden XYZ
            n = len(verts)
            for cx in (-0.5, 0.5):
                for cy in (-0.5, 0.5):
                    for cz in (-0.5, 0.5):
                        v = M3 @ Vector((cx * sx, cy * sy, cz * sz)) + Vector((px, py, pz))
                        verts.append((v.x, -v.z, v.y))
            faces += [tuple(n + k for k in f) for f in
                      ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))]
        me = bpy.data.meshes.new('torre%d_%s' % (i + 1, key))
        me.from_pydata(verts, [], faces)
        me.validate()
        me.materials.append(mat_lh(key))
        bpy.context.scene.collection.objects.link(bpy.data.objects.new(me.name, me))
    # el foco cuelga bajo el tejadillo y mira hacia donde mira el centinela (como spotTick del visor, sin bajar)
    ph = 0.27
    return {'name': 'torre%d' % (i + 1), 'pos': [x, -z, 0.0], 'yaw': t['yaw'], 'altura': TWH,
            'escala': [x + 1.75, -z, 0.0],
            'foco': {'pos': [x - 0.25, -z, TWH + 2.05],
                     'dir': [math.sin(t['yaw']) * math.cos(ph), -math.cos(t['yaw']) * math.cos(ph), -math.sin(ph)]}}

import math
TORRES = [torre(i, t) for i, t in enumerate(TOWERS)]

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
lights = [l for l in j['lights'] if l.get('name') != 'foco_torreta']
for tw in TORRES:
    lights.append({'kind': 'SPOT', 'name': 'foco_torreta', 'pos': tw['foco']['pos'], 'dir': tw['foco']['dir'],
                   'color': [0.8, 0.9, 1.0], 'power': 90000})
json.dump({'T': T, 'map': j['map'], 'lights': lights, 'spawn': spawn, 'marcas': MARCAS, 'torres': TORRES,
           'mallas': len([o for o in bpy.data.objects if o.type == 'MESH'])},
          open(os.path.join(OUT, 'base.json'), 'w'), indent=1)
shutil.rmtree(tmp, ignore_errors=True)
n = len([o for o in bpy.data.objects if o.type == 'MESH'])
print('UNREAL', glb, os.path.getsize(glb) // 1024, 'KB,', n, 'mallas,', len(PAL), 'materiales del visor')
