"""Modela el pastor de la perrera para el visor: cuerpo y cuatro patas sueltas (el visor las balancea), con el color en los vértices.
Sale en assets/modelos-ph/perro/perro.glb. Mira hacia -Y (en el visor, +Z, como las personas). LH_PREVIEW=carpeta guarda un render.
Uso: python3 tools/blender/perro.py"""
import bpy, os, math
from mathutils import Vector
R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); OUT = os.path.join(R, 'assets', 'modelos-ph', 'perro'); PREVIEW = os.environ.get('LH_PREVIEW')
bpy.ops.wm.read_factory_settings(use_empty=True); os.makedirs(OUT, exist_ok=True)
K = 1.75   # la superficie de una metabola queda hacia la mitad de su radio: se compensa para dar las medidas en metros reales
def blob(name, balls, origin=(0, 0, 0)):
    """balls: (adelante, lado, alto, radio) respecto al origen de la pieza."""
    mb = bpy.data.metaballs.new(name); mb.resolution = 0.016; mb.threshold = 0.6
    for f, s, z, r in balls:
        e = mb.elements.new(type='BALL'); e.co = (s, -f, z); e.radius = r * K
    o = bpy.data.objects.new(name, mb); bpy.context.scene.collection.objects.link(o); bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); bpy.data.objects.remove(o)
    m = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(m); m.location = (origin[1], -origin[0], origin[2]); return m
def chain(a, b, n):
    return [tuple(a[k] + (b[k] - a[k]) * i / (n - 1) for k in range(4)) for i in range(n)]
body = blob('cuerpo', chain((-0.30, 0, 0.50, 0.125), (0.22, 0, 0.50, 0.15), 7) + [(0.0, 0, 0.455, 0.12), (0.2, 0, 0.43, 0.125)]      # lomo, vientre y pecho
            + chain((0.27, 0, 0.56, 0.115), (0.38, 0, 0.68, 0.085), 5) + [(0.43, 0, 0.715, 0.085)]                                  # cuello y cráneo
            + chain((0.48, 0, 0.70, 0.056), (0.62, 0, 0.675, 0.036), 6)                                                           # hocico
            + chain((-0.38, 0, 0.50, 0.05), (-0.56, 0, 0.26, 0.03), 9)                                                            # cola caída
            + [(0.41, sx * 0.055, 0.795, 0.03) for sx in (-1, 1)] + [(0.405, sx * 0.058, 0.83, 0.021) for sx in (-1, 1)] + [(0.4, sx * 0.06, 0.855, 0.013) for sx in (-1, 1)])        # orejas tiesas
legs = []
for name, f, sx, back in (('pata_dl', 0.22, 1, False), ('pata_dr', 0.22, -1, False), ('pata_tl', -0.27, 1, True), ('pata_tr', -0.27, -1, True)):
    if back: b = chain((0, 0, 0, 0.085), (-0.05, 0, -0.17, 0.05), 6) + chain((-0.05, 0, -0.17, 0.045), (-0.1, 0, -0.33, 0.03), 7) + chain((-0.1, 0, -0.33, 0.03), (-0.07, 0, -0.45, 0.028), 6) + [(-0.05, 0, -0.47, 0.033), (-0.03, 0, -0.475, 0.03)]
    else: b = chain((0, 0, 0.02, 0.07), (0, 0, -0.2, 0.04), 7) + chain((0, 0, -0.2, 0.038), (0.0, 0, -0.45, 0.029), 11) + [(0.015, 0, -0.47, 0.033), (0.035, 0, -0.475, 0.03)]
    legs.append(blob(name, b, origin=(f, sx * 0.085, 0.5)))
# color por vértice: fuego en patas, vientre y cara; manto negro en el lomo, el hocico y las orejas
TAN = (0.17, 0.105, 0.05); NEG = (0.03, 0.028, 0.026)
for o in [body] + legs:
    me = o.data; ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT'); me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    for v in me.vertices:
        w = o.location + v.co; f = -w.y; z = w.z
        k = 0.0
        if o is body:
            k = min(1.0, max(0.0, (z - 0.47 - max(0.0, f - 0.18) * 1.15) / 0.07)) if f < 0.42 else 0.0                    # manto
            if f > 0.52 or z > 0.79: k = 1.0                                                  # hocico y orejas
            if f < -0.36: k = max(k, 0.7)                                                     # cola
        t = k * k * (3 - 2 * k); ca.data[v.index].color = tuple(TAN[i] + (NEG[i] - TAN[i]) * t for i in range(3)) + (1.0,)
    mat = bpy.data.materials.new('pelo'); mat.use_nodes = True; nt = mat.node_tree; bs = nt.nodes['Principled BSDF']; bs.inputs['Roughness'].default_value = 0.85
    vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'; nt.links.new(vc.outputs['Color'], bs.inputs['Base Color']); me.materials.append(mat)
    d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = 0.12
print('PERRO', {o.name: len(o.data.polygons) for o in [body] + legs}, flush=True)
if PREVIEW:
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.render.resolution_x = 900; sc.render.resolution_y = 600
    cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); cam.location = (2.0, -1.2, 0.75); cam.rotation_euler = (math.radians(84), 0, math.radians(59)); cam.data.lens = 50; sc.camera = cam
    l = bpy.data.objects.new('l', bpy.data.lights.new('l', 'AREA')); l.data.energy = 300; l.data.size = 2; l.location = (2, -2, 2.5); l.rotation_euler = (math.radians(50), 0, math.radians(40)); sc.collection.objects.link(l)
    sc.world = bpy.data.worlds.new('w'); sc.world.color = (0.2, 0.2, 0.22); sc.render.filepath = os.path.join(PREVIEW, 'perro.png'); bpy.ops.render.render(write_still=True)
for o in bpy.data.objects: o.select_set(o.type == 'MESH')
f = os.path.join(OUT, 'perro.glb')
bpy.ops.export_scene.gltf(filepath=f, export_format='GLB', use_selection=True, export_yup=True, export_apply=True, export_animations=False, export_vertex_color='ACTIVE', export_all_vertex_colors=True)
print('GLB', os.path.getsize(f) // 1024, 'KB', flush=True)
