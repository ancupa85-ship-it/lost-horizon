"""Genera las personas del escenario realista con MakeHuman (extensión MPFB de Blender, recursos CC0):
cuerpo, cara, pelo y ropa, ya en su postura, exportadas a assets/modelos-ph/persona_<nombre>/ para que
escena_base.py las coloque como cualquier otro modelo.

Requiere la extensión MPFB instalada y los paquetes de recursos descomprimidos en su carpeta de datos
(makehuman_system_assets, pants01, shoes01). Uso: python3 tools/blender/personas.py [nombre ...]
LH_PREVIEW=carpeta guarda además un render de comprobación de cada una."""
import bpy, sys, os, math, json
import numpy as np
from mathutils import Vector, Matrix, Quaternion
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(R, 'assets', 'modelos-ph'); PREVIEW = os.environ.get('LH_PREVIEW')
DATA = os.path.join(bpy.utils.user_resource('EXTENSIONS'), '.user', 'user_default', 'mpfb', 'data') + os.sep

OLIVA = (0.34, 0.4, 0.24); NEGRO = (0.16, 0.16, 0.17)
STAND = {'upperarm_l': (0.1, 0.03, -1), 'lowerarm_l': (0.03, -0.14, -1), 'upperarm_r': (-0.1, 0.03, -1), 'lowerarm_r': (-0.03, -0.14, -1)}
PEOPLE = {
    'cuttlas': dict(curl={'_r': 0.7, '_l': 0.25}, dark_suit=0.42, macro=dict(age=0.58, muscle=0.82, weight=0.48), skin='young_caucasian_male_special_suit', hair='short02', hair_tint=(0.35, 0.3, 0.27),
                    clothes=[('cortu_cargo_pants', NEGRO), ('toigo_ankle_boots_male', NEGRO)],
                    pose={'spine_01': (0, -0.3, 1), 'spine_02': (0, -0.5, 1), 'spine_03': (0, -0.6, 1), 'neck_01': (0, -0.45, 1), 'head': (0, -0.05, 1),
                          'thigh_l': (0.1, -1, 0.08), 'calf_l': (0.0, 0.1, -1), 'thigh_r': (-0.08, -0.3, -1), 'calf_r': (0, 1, -0.13), 'foot_r': (0, 0.25, -1),
                          'upperarm_l': (0.12, -0.55, -1), 'lowerarm_l': (-0.3, -1, 0.05), 'upperarm_r': (-0.12, -0.35, -1), 'lowerarm_r': (0.12, -1, -0.3)}),
    'ibarra': dict(macro=dict(age=0.6, muscle=0.6, weight=0.58), skin='middleage_caucasian_male', hair='short01', hair_tint=(0.4, 0.33, 0.28),
                   clothes=[('male_casualsuit01', OLIVA), ('toigo_ankle_boots_male', NEGRO)], pose=dict(STAND, head=(0.12, -0.1, 1))),
    'moya': dict(macro=dict(age=0.78, muscle=0.7, weight=0.62), skin='old_caucasian_male', hair=None,
                 clothes=[('male_casualsuit01', (0.3, 0.36, 0.22)), ('toigo_ankle_boots_male', NEGRO)],
                 curl={'_l': 0.7, '_r': 0.7},
                 pose={'upperarm_r': (-0.22, 0.1, -1), 'lowerarm_r': (0.55, -0.75, -0.4), 'upperarm_l': (0.2, -0.3, -1), 'lowerarm_l': (-0.5, -0.65, 0.5)}),
    'peris': dict(macro=dict(age=0.42, muscle=0.5, weight=0.42), skin='young_caucasian_male2', hair='short03', hair_tint=(0.75, 0.6, 0.5),
                  clothes=[('male_casualsuit01', (0.37, 0.43, 0.26)), ('toigo_ankle_boots_male', NEGRO)], pose=dict(STAND, head=(-0.2, -0.12, 1), spine_03=(0.02, 0.03, 1))),
}

def tint(obj, colour):
    """Tiñe la textura de color de una prenda (gris por el color), para que valga igual en Cycles y en el visor."""
    for s in obj.material_slots:
        for n in s.material.node_tree.nodes:
            if n.type != 'TEX_IMAGE' or not n.image or any(k in n.image.name.lower() for k in ('normal', '_ao', 'bump', 'spec')): continue
            im = n.image; a = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32); im.pixels.foreach_get(a); a = a.reshape(-1, 4)
            lum = (a[:, 0] * 0.3 + a[:, 1] * 0.5 + a[:, 2] * 0.2)[:, None]; a[:, :3] = np.clip(lum * np.array(colour, dtype=np.float32) * 1.6, 0, 1)
            im.pixels.foreach_set(a.ravel()); im.update(); im.pack()

def pose(arm, dirs, curl=None):
    """Orienta cada hueso hacia una dirección (espacio del esqueleto), de padres a hijos. Devuelve las matrices resultantes."""
    W = {}
    for bn in arm.data.bones:                      # el orden de data.bones va de padres a hijos
        pb = arm.pose.bones[bn.name]; pb.rotation_mode = 'QUATERNION'
        W0 = (W[bn.parent.name] @ bn.parent.matrix_local.inverted() @ bn.matrix_local) if bn.parent else bn.matrix_local.copy()
        q = Vector((0, 1, 0)).rotation_difference(W0.to_3x3().inverted() @ Vector(dirs[bn.name]).normalized()) if bn.name in dirs else None
        if q is None and curl and bn.name[-2:] in curl and bn.name.split('_')[0] in ('index', 'middle', 'ring', 'pinky', 'thumb'):
            q = Quaternion((1, 0, 0), curl[bn.name[-2:]] * (0.5 if bn.name.startswith('thumb') else 1.0))     # dedos cerrados sobre el arma
        if q is not None: pb.rotation_quaternion = q
        W[bn.name] = W0 @ q.to_matrix().to_4x4() if q is not None else W0
    return W

def build(name):
    P = PEOPLE[name]
    bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.preferences.addon_enable(module='bl_ext.user_default.mpfb')
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    m = TargetService.get_default_macro_info_dict(); m.update(gender=1.0, race={'asian': 0, 'caucasian': 1, 'african': 0}); m.update(P['macro'])
    b = HumanService.create_human(scale=0.1, macro_detail_dict=m, detailed_helpers=False, extra_vertex_groups=True, feet_on_ground=False)   # con los pies en el suelo el esqueleto queda desplazado
    arm = HumanService.add_builtin_rig(b, 'game_engine', import_weights=True)
    HumanService.set_character_skin(DATA + 'skins/%s/%s.mhmat' % (P['skin'], P['skin']), b, skin_type='MAKESKIN')
    if P.get('dark_suit'):                         # el traje va pintado en la piel: se oscurece solo lo gris, no la cara ni las manos
        for s_ in b.material_slots:
            for n in s_.material.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image:
                    im = n.image; a = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32); im.pixels.foreach_get(a); a = a.reshape(-1, 4)
                    grey = (a[:, :3].max(axis=1) - a[:, :3].min(axis=1)) < 0.07; a[grey, :3] *= P['dark_suit']; im.pixels.foreach_set(a.ravel()); im.update(); im.pack()
    add = lambda kind, rel: HumanService.add_mhclo_asset(DATA + rel, b, asset_type=kind, subdiv_levels=0, material_type='MAKESKIN')
    add('Eyes', 'eyes/low-poly/low-poly.mhclo'); add('Eyebrows', 'eyebrows/eyebrow001/eyebrow001.mhclo'); add('Eyelashes', 'eyelashes/eyelashes01/eyelashes01.mhclo')
    if P['hair']: add('Hair', 'hair/%s/%s.mhclo' % (P['hair'], P['hair']))
    for c, col in P['clothes']:
        before = set(bpy.data.objects); add('Clothes', 'clothes/%s/%s.mhclo' % (c, c))
        for o in set(bpy.data.objects) - before: tint(o, col)
    if P.get('hair_tint'):
        for o in bpy.data.objects:
            if o.type == 'MESH' and P['hair'] in o.name: tint(o, P['hair_tint'])
    W = pose(arm, P['pose'], P.get('curl')); bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    aw = arm.matrix_world.copy(); J = {k: aw @ W[k].to_translation() for k in ('head', 'neck_01', 'hand_l', 'hand_r', 'upperarm_l', 'upperarm_r', 'pelvis')}
    for k in ('hand_l', 'hand_r', 'head'): J[k + '_tip'] = aw @ (W[k] @ Vector((0, arm.data.bones[k].length, 0)))
    meshes = []
    for o in [o for o in bpy.data.objects if o.type == 'MESH']:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); mw = o.matrix_world.copy(); n = bpy.data.objects.new(name + '_' + o.name.split('.')[-1], me)
        me.transform(mw); bpy.context.scene.collection.objects.link(n); meshes.append(n)
        for mat in me.materials: mat.name = name + '_' + mat.name.split('.')[-1]
    for o in [o for o in bpy.data.objects if o not in meshes]: bpy.data.objects.remove(o)
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in meshes:
        for v in o.data.vertices:
            for k in range(3): mn[k] = min(mn[k], v.co[k]); mx[k] = max(mx[k], v.co[k])
    off = Vector((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z))
    for o in meshes:
        o.data.transform(Matrix.Translation(off)); o.data.polygons.foreach_set('use_smooth', [True] * len(o.data.polygons))
    meta = {k: list(v + off) for k, v in J.items()}; meta['height'] = mx.z - mn.z; meta['faces'] = sum(len(o.data.polygons) for o in meshes)
    for im in bpy.data.images:
        if im.size[0] > 1024: im.scale(1024, 1024 * im.size[1] // im.size[0]); im.pack()
    d = os.path.join(OUT, 'persona_' + name); os.makedirs(d, exist_ok=True)
    for o in meshes: o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(d, 'persona_' + name + '.gltf'), export_format='GLTF_SEPARATE', export_texture_dir='textures', use_selection=True, export_yup=True,
                              export_animations=False, export_image_format='AUTO')
    json.dump(meta, open(os.path.join(d, 'meta.json'), 'w')); print('PERSONA', name, meta, flush=True)
    if PREVIEW:
        sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.render.resolution_x = 900; sc.render.resolution_y = 700
        for k, (loc, rz) in enumerate((((1.5, -3.0, 1.0), 26), ((-2.6, -2.0, 1.0), -52))):
            cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); cam.location = loc; cam.rotation_euler = (math.radians(88), 0, math.radians(rz)); cam.data.lens = 42
            cam.data.shift_x = 0.0; sc.camera = cam
            if not k:
                l = bpy.data.objects.new('l', bpy.data.lights.new('l', 'AREA')); l.data.energy = 500; l.data.size = 2; l.location = (2, -3, 3); l.rotation_euler = (math.radians(50), 0, math.radians(35)); sc.collection.objects.link(l)
                sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.12, 0.12, 0.14)
            sc.render.filepath = os.path.join(PREVIEW, 'persona_%s_%d.png' % (name, k)); bpy.ops.render.render(write_still=True)

for n in ([a for a in sys.argv[1:] if a in PEOPLE] or list(PEOPLE)): build(n)
