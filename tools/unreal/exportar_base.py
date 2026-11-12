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
json.dump({'T': T, 'map': j['map'], 'lights': j['lights'], 'spawn': spawn, 'marcas': MARCAS},
          open(os.path.join(OUT, 'base.json'), 'w'), indent=1)
shutil.rmtree(tmp, ignore_errors=True)
n = len([o for o in bpy.data.objects if o.type == 'MESH'])
print('UNREAL', glb, os.path.getsize(glb) // 1024, 'KB,', n, 'mallas,', len(PAL), 'materiales del visor')
