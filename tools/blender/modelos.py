"""Modelos de Lost Horizon hechos con Blender (bpy). Genera assets/models/<hueco>.glb con las medidas de docs/ASSETS.md.
Se puede ejecutar sin abrir Blender (`pip install bpy` y `python3 tools/blender/modelos.py [hueco ...]`) o pegarlo en la
pestaña Scripting de Blender para seguir retocando el modelo a mano antes de exportar.
Convenio: metros, origen en el suelo y en el centro de la huella, Z arriba y frente hacia -Y (en el juego, +Z)."""
import bpy, os, sys, math
from mathutils import Vector

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) if '__file__' in globals() else os.getcwd()
OUT = os.path.join(R, 'assets', 'models')

# El juego usa los colores tal cual (sin gestión de color), así que el Base Color lleva el valor del hex sin convertir.
def mat(name, hexc, emit=None):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    rgb = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = 1; b.inputs['Metallic'].default_value = 0
    if emit:
        e = [int(emit[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        b.inputs['Emission Color'].default_value = (*e, 1); b.inputs['Emission Strength'].default_value = 1
    return m

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def box(name, size, pos, m, rot=(0, 0, 0)):
    """Caja de tamaño (x, y, z) centrada en pos."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = size; o.data.materials.append(m)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); return o

def cyl(name, r, depth, pos, m, rot=(0, 0, 0), verts=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=pos, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(m); return o

def taper(o, top_scale_x, top_scale_y=1.0):
    """Estrecha la cara de arriba de una caja (parabrisas inclinado, lona a dos aguas)."""
    zmax = max(v.co.z for v in o.data.vertices)
    for v in o.data.vertices:
        if abs(v.co.z - zmax) < 1e-5: v.co.x *= top_scale_x; v.co.y *= top_scale_y
    return o

def finish(name):
    """Une todo en una malla (un material por color), aplica transformaciones, pone el origen en el suelo y exporta."""
    obs = [o for o in bpy.data.objects if o.type == 'MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs: o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.join(); o = bpy.context.object; o.name = name; o.data.name = name
    bpy.ops.object.shade_flat()
    bpy.context.scene.cursor.location = (0, 0, 0); bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    o.data.calc_loop_triangles(); tris = len(o.data.loop_triangles)
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    size = [max(c[i] for c in bb) - min(c[i] for c in bb) for i in range(3)]; zmin = min(c[2] for c in bb)
    os.makedirs(OUT, exist_ok=True); path = os.path.join(OUT, name + '.glb')
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=True,
                              export_animations=False, export_cameras=False, export_lights=False)
    print('%s: %d triángulos, %.2f x %.2f x %.2f m (ancho x fondo x alto), suelo en %.3f -> %s' % (name, tris, size[0], size[1], size[2], zmin, path))
    return tris, size

# ---------- caja de madera: 1,8 x 1,3 x 1,8 m, tapa la vista
def caja():
    clear()
    tabla, veta, hierro = mat('madera', '#8c5e2c'), mat('veta', '#4a2e12'), mat('hierro', '#5b6468')
    W, H = 1.8, 1.3; w = 0.14  # ancho del listón
    box('cuerpo', (W - 0.1, W - 0.1, H - 0.08), (0, 0, H / 2), tabla)
    # marco: cuatro postes, y listones arriba y abajo en las cuatro caras
    for sx in (-1, 1):
        for sy in (-1, 1):
            box('poste', (w, w, H), (sx * (W - w) / 2, sy * (W - w) / 2, H / 2), veta)
    for z in (w / 2, H - w / 2):
        for s in (-1, 1):
            box('liston', (W - 2 * w, w * 0.6, w), (0, s * (W - w * 0.6) / 2, z), veta)
            box('liston', (w * 0.6, W - 2 * w, w), (s * (W - w * 0.6) / 2, 0, z), veta)
    # travesaño en diagonal en cada cara
    L = math.hypot(W - 2 * w, H - 2 * w); a = math.atan2(H - 2 * w, W - 2 * w)
    for s in (-1, 1):
        box('diagonal', (L, 0.05, w * 0.8), (0, s * (W - 0.05) / 2, H / 2), veta, rot=(0, -a * s, 0))
        box('diagonal', (0.05, L, w * 0.8), (s * (W - 0.05) / 2, 0, H / 2), veta, rot=(a * s, 0, 0))
    # tapa de tablas con dos travesaños, y cantoneras de hierro
    for i in (-1, 0, 1):
        box('tabla', (0.5, W - 2 * w - 0.02, 0.03), (i * 0.52, 0, H - 0.015), tabla)
    for s in (-1, 1):
        box('travesano', (W - 2 * w, w, 0.035), (0, s * 0.45, H - 0.0175 + 0.0), veta)
        for t in (-1, 1):
            box('cantonera', (0.2, 0.2, 0.04), (s * (W - 0.2) / 2, t * (W - 0.2) / 2, H - 0.02), hierro)
    return finish('caja')

# ---------- camión militar con lona: huella 4 x 4 m (ancho real 3,1; largo 4), alto 2,2. Frente hacia -Y.
def camion():
    clear()
    oliva, bajos, metal = mat('oliva', '#4f5a3c'), mat('bajos', '#2f3824'), mat('metal', '#5b6468')
    lona, goma, cristal = mat('lona', '#6b6a48'), mat('goma', '#15171a'), mat('cristal', '#1c2a30')
    faro, piloto, madera = mat('faro', '#ffb060', emit='#ffb060'), mat('piloto', '#8a2018', emit='#5a120c'), mat('madera', '#8c5e2c')
    Wc = 2.5  # ancho de la caja de carga
    # bastidor y ejes
    for s in (-1, 1): box('larguero', (0.16, 3.8, 0.2), (s * 0.5, 0, 0.62), bajos)
    box('parachoques', (2.5, 0.16, 0.26), (0, -1.92, 0.6), bajos)
    box('parachoques_tras', (2.3, 0.12, 0.18), (0, 1.94, 0.6), bajos)
    for y in (-1.25, 0.7, 1.45):
        cyl('eje', 0.08, 2.4, (0, y, 0.48), bajos, rot=(0, math.pi / 2, 0), verts=6)
        for s in (-1, 1):
            cyl('rueda', 0.48, 0.34, (s * 1.12, y, 0.48), goma, rot=(0, math.pi / 2, 0), verts=12)
            cyl('llanta', 0.2, 0.36, (s * 1.12, y, 0.48), oliva, rot=(0, math.pi / 2, 0), verts=8)
    # morro y cabina
    box('morro', (1.7, 0.75, 0.62), (0, -1.5, 1.03), oliva)
    box('rejilla', (1.2, 0.04, 0.44), (0, -1.89, 1.0), bajos)
    for s in (-1, 1):
        box('aleta', (0.46, 1.1, 0.1), (s * 1.1, -1.3, 1.02), oliva)
        box('aleta_frente', (0.46, 0.1, 0.3), (s * 1.1, -1.82, 0.9), oliva)
        cyl('faro', 0.13, 0.08, (s * 0.72, -1.9, 1.08), faro, rot=(math.pi / 2, 0, 0), verts=8)
        box('retrovisor', (0.05, 0.05, 0.3), (s * 1.3, -1.02, 1.6), bajos)
        box('estribo', (0.3, 0.6, 0.06), (s * 1.18, -0.75, 0.62), bajos)
    box('cabina', (2.2, 0.95, 0.62), (0, -0.67, 1.03), oliva)
    techo = taper(box('cabina_alta', (2.2, 0.95, 0.7), (0, -0.67, 1.69), oliva), 0.94, 0.8)
    box('parabrisas', (1.8, 0.04, 0.42), (0, -1.11, 1.7), cristal, rot=(math.radians(-10), 0, 0))
    for s in (-1, 1): box('ventanilla', (0.04, 0.55, 0.38), (s * 1.08, -0.67, 1.68), cristal)
    # caja de carga con adrales de madera y lona a dos aguas
    box('plataforma', (Wc, 2.15, 0.14), (0, 0.9, 0.86), bajos)
    for s in (-1, 1): box('adral', (0.06, 2.15, 0.5), (s * (Wc - 0.06) / 2, 0.9, 1.18), madera)
    box('adral_frente', (Wc, 0.06, 0.5), (0, -0.15, 1.18), madera)
    box('porton', (Wc, 0.06, 0.5), (0, 1.95, 1.18), madera)
    box('lona_lados', (Wc + 0.04, 2.19, 0.42), (0, 0.9, 1.62), lona)
    taper(box('lona_techo', (Wc + 0.04, 2.19, 0.37), (0, 0.9, 2.015), lona), 0.55)
    for s in (-1, 1):
        box('piloto', (0.16, 0.05, 0.12), (s * 1.0, 1.975, 0.72), piloto)
        box('bidon', (0.18, 0.36, 0.48), (s * 1.34, -0.1, 0.98), oliva)  # bidones en el costado
        box('soporte', (0.3, 0.42, 0.05), (s * 1.3, -0.1, 0.72), bajos)
    cyl('rueda_repuesto', 0.46, 0.26, (0, -0.14, 1.72), goma, rot=(math.pi / 2, 0, 0), verts=12)
    return finish('camion')

# ---------- grupo electrógeno: 1,8 x 1,4 x 1,4 m, tubo de escape hasta 2,9. Panel de mando al frente (-Y).
def generador():
    clear()
    metal, oscuro, bajos = mat('metal', '#5b6468'), mat('oscuro', '#2a2e31'), mat('bajos', '#2f3824')
    oliva, piloto, aviso = mat('oliva', '#4f5a3c'), mat('piloto', '#40ff60', emit='#40ff60'), mat('aviso', '#c9a227')
    for s in (-1, 1): box('patin', (1.8, 0.14, 0.12), (0, s * 0.5, 0.06), bajos)
    box('carcasa', (1.7, 1.3, 1.0), (0, 0, 0.62), oliva)
    taper(box('tapa', (1.7, 1.3, 0.22), (0, 0, 1.23), oliva), 0.96, 0.8)
    box('deposito', (0.5, 1.36, 0.4), (-0.6, 0, 0.5), metal)
    for i in range(5): box('lama', (0.7, 0.03, 0.05), (0.38, -0.66, 0.5 + i * 0.12), oscuro)  # rejilla de ventilación
    for i in range(5): box('lama', (0.7, 0.03, 0.05), (0.38, 0.66, 0.5 + i * 0.12), oscuro)
    box('panel', (0.6, 0.05, 0.45), (-0.45, -0.67, 0.92), oscuro)
    box('piloto', (0.08, 0.03, 0.08), (-0.62, -0.7, 1.04), piloto)
    box('palanca', (0.06, 0.1, 0.2), (-0.3, -0.72, 0.9), aviso)
    box('franja', (1.72, 1.32, 0.06), (0, 0, 0.2), aviso)
    cyl('escape', 0.09, 1.5, (0.6, 0, 2.1), oscuro, verts=8)
    cyl('silenciador', 0.16, 0.5, (0.6, 0, 1.7), metal, verts=8)
    box('sombrerete', (0.26, 0.26, 0.04), (0.6, 0, 2.88), oscuro)
    cyl('tapon', 0.1, 0.06, (-0.3, 0.2, 1.37), metal, verts=8)
    return finish('generador')

# ---------- farola: poste de 3,3 m; la bombilla la pone el juego a 3,25 m en el eje
def farola():
    clear()
    oscuro, metal = mat('oscuro', '#2a2e31'), mat('metal', '#5b6468')
    cyl('base', 0.15, 0.3, (0, 0, 0.15), metal, verts=8)
    cyl('zocalo', 0.1, 0.5, (0, 0, 0.55), oscuro, verts=8)
    cyl('poste', 0.055, 2.5, (0, 0, 1.95), oscuro, verts=6)
    cyl('anilla', 0.08, 0.06, (0, 0, 2.3), metal, verts=6)
    for s in (-1, 1): box('brazo', (0.02, 0.02, 0.2), (s * 0.12, 0, 3.17), oscuro)  # la bombilla queda a la vista entre los brazos
    taper(box('pantalla', (0.3, 0.3, 0.05), (0, 0, 3.275), metal), 0.5, 0.5)
    return finish('farola')

# ---------- torreta del foco: celosía de 1,2 x 1,2 m y 7 m de alto; el foco lo pone el juego arriba, en el eje
def torreta():
    clear()
    metal, oscuro, hormigon, madera = mat('metal', '#5b6468'), mat('oscuro', '#2a2e31'), mat('hormigon', '#7a7f7c'), mat('madera', '#8c5e2c')
    box('zapata', (1.2, 1.2, 0.3), (0, 0, 0.15), hormigon)
    h = 0.52  # media anchura entre patas
    for sx in (-1, 1):
        for sy in (-1, 1): box('pata', (0.1, 0.1, 6.0), (sx * h, sy * h, 3.3), metal)
    tramos = [0.3, 1.8, 3.3, 4.8, 6.3]
    for i, z in enumerate(tramos):
        for s in (-1, 1):
            box('travesano', (2 * h, 0.06, 0.06), (0, s * h, z), metal); box('travesano', (0.06, 2 * h, 0.06), (s * h, 0, z), metal)
        if i < len(tramos) - 1:
            dz = tramos[i + 1] - z; L = math.hypot(2 * h, dz); a = math.atan2(dz, 2 * h) * (1 if i % 2 == 0 else -1)
            for s in (-1, 1):
                box('diagonal', (L, 0.04, 0.05), (0, s * h, z + dz / 2), oscuro, rot=(0, -a * s, 0))
                box('diagonal', (0.04, L, 0.05), (s * h, 0, z + dz / 2), oscuro, rot=(a * s, 0, 0))
    box('plataforma', (1.2, 1.2, 0.08), (0, 0, 6.36), madera)
    for s in (-1, 1):
        box('baranda', (1.2, 0.04, 0.04), (0, s * 0.58, 6.96), metal); box('baranda', (0.04, 1.2, 0.04), (s * 0.58, 0, 6.96), metal)
        for t in (-1, 1): box('montante', (0.04, 0.04, 0.6), (s * 0.58, t * 0.58, 6.68), metal)
    for i in range(12): box('peldano', (0.4, 0.03, 0.03), (0, -0.58, 0.6 + i * 0.5), oscuro)  # escalera de mano en el frente
    return finish('torreta')

MODELOS = {'caja': caja, 'camion': camion, 'generador': generador, 'farola': farola, 'torreta': torreta}
if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a in MODELOS] or list(MODELOS)
    for n in args: MODELOS[n]()
