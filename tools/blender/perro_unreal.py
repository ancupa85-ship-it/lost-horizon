"""El perro del hangar para Unreal: el pastor de perro.py en una sola malla con esqueleto y cuatro animaciones (quieto, andar, sentarse, sentado).
Sale en assets/unreal/perro.glb. LH_PREVIEW=carpeta guarda tres renders (de pie, andando y sentado).
Uso: python3 tools/blender/perro_unreal.py"""
import os, math
AQUI = os.path.dirname(os.path.abspath(__file__)); PV = os.environ.pop('LH_PREVIEW', None); os.environ.pop('LH_ESTILO', None)
src = open(os.path.join(AQUI, 'perro.py'), encoding='utf-8').read(); src = src[:src.index('if PREVIEW:')]
exec(compile(src.replace('__file__', repr(os.path.join(AQUI, 'perro.py'))), 'perro.py', 'exec'))     # deja body, legs y extras en la escena
import bpy
from mathutils import Vector, Matrix
sc = bpy.context.scene; dg = bpy.context.evaluated_depsgraph_get()
# --- huesos: (nombre, padre, cabeza (adelante, alto), cola (adelante, alto), lado)
H = [('raiz', None, (0, 0), (0, 0.12), 0), ('lomo', 'raiz', (0.22, 0.50), (-0.30, 0.50), 0), ('cuello', 'lomo', (0.25, 0.54), (0.38, 0.68), 0), ('cabeza', 'cuello', (0.38, 0.68), (0.62, 0.68), 0),
     ('cola1', 'lomo', (-0.36, 0.50), (-0.46, 0.38), 0), ('cola2', 'cola1', (-0.46, 0.38), (-0.56, 0.26), 0)]
for lado, sx in (('l', 1), ('r', -1)):
    H += [('brazo_' + lado, 'lomo', (0.22, 0.50), (0.22, 0.30), sx * 0.085), ('mano_' + lado, 'brazo_' + lado, (0.22, 0.30), (0.22, 0.04), sx * 0.085),
          ('muslo_' + lado, 'lomo', (-0.27, 0.50), (-0.32, 0.33), sx * 0.085), ('pierna_' + lado, 'muslo_' + lado, (-0.32, 0.33), (-0.37, 0.17), sx * 0.085), ('pie_' + lado, 'pierna_' + lado, (-0.37, 0.17), (-0.32, 0.03), sx * 0.085)]
P = lambda fz, x: Vector((x, -fz[0], fz[1]))
SEG = {n: (P(a, x), P(b, x)) for n, p, a, b, x in H}; PADRE = {n: p for n, p, a, b, x in H}
def dist(v, n):
    a, b = SEG[n]; ab = b - a; t = max(0.0, min(1.0, (v - a).dot(ab) / ab.length_squared)); return (v - (a + ab * t)).length
# --- una sola malla con los pesos puestos a mano
partes = []
for o in [body] + legs + extras:
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); n = bpy.data.objects.new(o.name, me); n.matrix_world = o.matrix_world.copy(); sc.collection.objects.link(n); partes.append((n, o.name))
for o in [body] + legs + extras: bpy.data.objects.remove(o)
pelo = partes[0][0].data.materials[0]
for o, nom in partes:
    if nom == 'cuerpo': cand = ['lomo', 'cuello', 'cabeza', 'cola1', 'cola2']
    elif nom.startswith('pata_d'): cand = ['brazo_' + nom[-1], 'mano_' + nom[-1]]
    elif nom.startswith('pata_t'): cand = ['muslo_' + nom[-1], 'pierna_' + nom[-1], 'pie_' + nom[-1]]
    elif nom in ('collar', 'chapa'): cand = ['cuello']
    else: cand = ['cabeza']
    if nom == 'cuerpo' or nom.startswith('pata'): o.data.materials.clear(); o.data.materials.append(pelo)
    vg = {c: o.vertex_groups.new(name=c) for c in cand}
    for v in o.data.vertices:
        w = o.matrix_world @ v.co; ds = sorted((dist(w, c), c) for c in cand)[:2]
        if nom == 'cuerpo' and -w.y > 0.44 and w.z > 0.6: ds = [(0.0, 'cabeza')]                    # el cráneo, el hocico y las orejas no se doblan
        ws = [(1.0 / (d + 0.004) ** 4, c) for d, c in ds]; tot = sum(x for x, c in ws)
        for x, c in ws: vg[c].add([v.index], x / tot, 'REPLACE')
for o, nom in partes: o.select_set(True)
bpy.context.view_layer.objects.active = partes[0][0]; bpy.ops.object.join(); perro = partes[0][0]; perro.name = 'perro'; perro.data.name = 'perro'
# el color del pelo, de los vertices a una textura de 64 px (Unreal no lee el color por vertice del glTF sin tocar el material):
# la U de cada vertice es cuanto tiene de manto negro
srgb = lambda c: 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
img = bpy.data.images.new('perro_pelo', 64, 4); px = []
for y in range(4):
    for x in range(64):
        u = x / 63.0; px += [srgb(TAN[i] + (NEG[i] - TAN[i]) * u) for i in range(3)] + [1.0]
img.pixels = px; img.filepath_raw = os.path.join(os.environ.get('TMPDIR', '/tmp'), 'perro_pelo.png'); img.file_format = 'PNG'; img.save(); img.pack()
me = perro.data; uv = me.uv_layers.new(name='UVMap'); ca = me.color_attributes.get('Col')
for lp in me.loops:
    c = ca.data[lp.vertex_index].color if ca else (TAN[0], 0, 0, 1)
    u = (c[0] - TAN[0]) / (NEG[0] - TAN[0]); uv.data[lp.index].uv = (0.02 + 0.96 * max(0.0, min(1.0, u)), 0.5)
nt = pelo.node_tree; tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; nt.links.new(tex.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
# --- esqueleto
ad = bpy.data.armatures.new('perro_esq'); arm = bpy.data.objects.new('perro_esq', ad); sc.collection.objects.link(arm); bpy.context.view_layer.objects.active = arm
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
for n, p, a, b, x in H:
    e = ad.edit_bones.new(n); e.head, e.tail = SEG[n]; e.roll = 0
    if p: e.parent = ad.edit_bones[p]
bpy.ops.object.mode_set(mode='OBJECT'); perro.parent = arm; md = perro.modifiers.new('esq', 'ARMATURE'); md.object = arm
REST = {b.name: b.matrix_local.to_3x3() for b in ad.bones}
for pb in arm.pose.bones: pb.rotation_mode = 'QUATERNION'
def pose(giros, lados=None):
    """giros: grados que gira cada hueso en el plano de perfil respecto al mundo (positivo: la punta sube por delante). Los hijos heredan lo del padre salvo que se diga otra cosa."""
    mundo = {}
    for n, p, a, b, x in H: mundo[n] = giros.get(n, mundo.get(p, 0.0))
    for n, p, a, b, x in H:
        loc = mundo[n] - (mundo[p] if p else 0.0); R = REST[n]; M = Matrix.Rotation(-math.radians(loc), 3, 'X')
        if lados and n in lados: M = Matrix.Rotation(math.radians(lados[n]), 3, 'Z') @ M
        arm.pose.bones[n].rotation_quaternion = (R.inverted() @ M @ R).to_quaternion()
def clave(f):
    for pb in arm.pose.bones: pb.keyframe_insert('rotation_quaternion', frame=f)
SENT = {'lomo': 35.2, 'cuello': 12, 'cabeza': 4, 'cola1': -42, 'cola2': -50, 'brazo_l': 3, 'brazo_r': 3, 'mano_l': 3, 'mano_r': 3,
        'muslo_l': 91, 'muslo_r': 91, 'pierna_l': -26, 'pierna_r': -26, 'pie_l': 62, 'pie_r': 62}
def quieto(t, base=None, k=1.0):
    g = dict(base or {}); s = math.sin(2 * math.pi * t)
    g['lomo'] = g.get('lomo', 0) + 0.6 * s * k; g['cabeza'] = g.get('cabeza', 0) + 2.0 * math.sin(2 * math.pi * t + 1.0)
    for l in 'lr':
        for h in ('brazo_', 'mano_'): g[h + l] = g.get(h + l, 0.0)                                     # las manos no se mueven al respirar
    return g, {'cola1': 7 * math.sin(4 * math.pi * t), 'cola2': 10 * math.sin(4 * math.pi * t - 0.8)}
def andar(t):
    g = {'lomo': 1.2 * math.sin(4 * math.pi * t), 'cuello': 2.5 * math.sin(4 * math.pi * t + 0.6), 'cola1': 8, 'cola2': 14}
    for l, f0 in (('l', 0.0), ('r', 0.5)):
        a = 2 * math.pi * (t + f0); b = 2 * math.pi * (t + f0 + 0.5)                                  # las patas van en diagonal: mano izquierda con pie derecho
        g['brazo_' + l] = 24 * math.sin(a); g['mano_' + l] = g['brazo_' + l] - 42 * max(0.0, math.cos(a))
        g['muslo_' + l] = 20 * math.sin(b); g['pierna_' + l] = g['muslo_' + l] - 26 * max(0.0, math.cos(b)); g['pie_' + l] = g['muslo_' + l] + 24 * max(0.0, math.cos(b))
    return g, {'cola1': 6 * math.sin(2 * math.pi * t), 'cola2': 9 * math.sin(2 * math.pi * t - 0.7)}
def mezcla(u):
    u = u * u * (3 - 2 * u); return {k: v * u for k, v in SENT.items()}, None
ANIM = {'quieto': (48, lambda t: quieto(t)), 'andar': (24, andar), 'sentarse': (14, mezcla), 'sentado': (48, lambda t: quieto(t, SENT, 0.5))}
arm.animation_data_create(); an = arm.animation_data; sc.render.fps = 24
for nom, (N, fn) in ANIM.items():
    act = bpy.data.actions.new(nom); an.action = act
    for f in range(N + 1):
        g, lat = fn(f / N); pose(g, lat); clave(f)
    an.action = None; tr = an.nla_tracks.new(); tr.name = nom; tr.strips.new(nom, 0, act); tr.mute = True
def poner(nom, t):
    g, lat = ANIM[nom][1](t); pose(g, lat); bpy.context.view_layer.update()
if PV:
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.render.resolution_x = 800; sc.render.resolution_y = 600
    cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); cam.location = (2.0, -1.2, 0.75); cam.rotation_euler = (math.radians(84), 0, math.radians(59)); cam.data.lens = 50; sc.camera = cam
    l = bpy.data.objects.new('l', bpy.data.lights.new('l', 'AREA')); l.data.energy = 190; l.data.size = 2; l.location = (2, -2, 2.5); l.rotation_euler = (math.radians(50), 0, math.radians(40)); sc.collection.objects.link(l)
    pl = bpy.data.meshes.new('suelo'); pl.from_pydata([(-4, -4, 0.02), (4, -4, 0.02), (4, 4, 0.02), (-4, 4, 0.02)], [], [(0, 1, 2, 3)]); po = bpy.data.objects.new('suelo', pl); sc.collection.objects.link(po)
    sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.2, 0.2, 0.22)
    for fich, nom, t in (('pie', 'quieto', 0.0), ('andar', 'andar', 0.08), ('sentado', 'sentado', 0.0), ('perfil', 'sentado', 0.0)):
        poner(nom, t)
        if fich == 'perfil': cam.location = (2.6, -0.05, 0.5); cam.rotation_euler = (math.radians(88), 0, math.radians(90))
        sc.render.filepath = os.path.join(PV, fich + '.png'); bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(po); bpy.data.objects.remove(cam); bpy.data.objects.remove(l)
pose({}); bpy.context.view_layer.update()
for o in bpy.data.objects: o.select_set(o in (arm, perro))
f = os.path.join(R, 'assets', 'unreal', 'perro.glb')
bpy.ops.export_scene.gltf(filepath=f, export_format='GLB', use_selection=True, export_yup=True, export_animations=True, export_animation_mode='NLA_TRACKS', export_vertex_color='NONE', export_skins=True)
print('PERRO_UNREAL', len(perro.data.polygons), 'caras', os.path.getsize(f) // 1024, 'KB', flush=True)
