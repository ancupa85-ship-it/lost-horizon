"""Escenario realista de la base de Tarsis (misión 1), a escala, construido en Blender a partir del plano del juego
(MAPSRC_BASE en src/10-zones.js: 2 m por casilla). Materiales PBR procedurales, farolas de sodio, focos de torreta,
niebla volumétrica y lluvia. Renderiza con Cycles y guarda el .blend para abrirlo en Blender.
Uso: python3 tools/blender/escena_base.py [salida] ; variables: LH_RES=1920x1080 LH_SAMPLES=96 LH_CAMS=patio,aerea,torreta LH_BLEND=1"""
import bpy, bmesh, os, sys, re, math, random
from mathutils import Vector, Matrix

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else os.path.join(R, 'dist', 'escena')
RES = [int(v) for v in os.environ.get('LH_RES', '1280x720').split('x')]
SAMPLES = int(os.environ.get('LH_SAMPLES', '64'))
CAMS = os.environ.get('LH_CAMS', 'patio,aerea,torreta').split(',')
os.makedirs(OUT, exist_ok=True)
random.seed(1983)
GLB = os.environ.get('LH_GLB')   # si se da una ruta, en vez de renderizar se exporta la escena para el visor en tiempo real
LIGHTS = []

src = open(os.path.join(R, 'src', '10-zones.js'), encoding='utf-8').read()
MAP = re.findall(r'"([^"]+)"', re.search(r'const MAPSRC_BASE=\[(.*?)\];', src, re.S).group(1))
ROWS, COLS, T = len(MAP), len(MAP[0]), 2.0
def cell(x, y): return MAP[y][x] if 0 <= x < COLS and 0 <= y < ROWS else '#'
def wpos(x, y, z=0.0): return Vector((x * T + T / 2, -(y * T + T / 2), z))   # casilla → metros (norte = +Y)
def roomy(x, y): return cell(x, y) in '_zLV'
def building(x, y):
    c = cell(x, y)
    return c == 'W' or roomy(x, y) or (c in 'Dbc' and any(roomy(x + a, y + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))) and c != 'c') or (c == 'c' and all(cell(x + a, y + b) in '_zcW' for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))))
def rnd(x, y, k=0): return random.Random(x * 7919 + y * 104729 + k * 31).random()

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

# ---------------------------------------------------------------- materiales
def new_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes.get('Principled BSDF'); return m, nt, b
def N(nt, kind, **kw):
    n = nt.nodes.new(kind)
    for k, v in kw.items():
        if hasattr(n, k): setattr(n, k, v)
        else: n.inputs[k].default_value = v
    return n
def L(nt, a, b): nt.links.new(a, b)
def noise(nt, vec, scale, detail=6.0, rough=0.55, stretch=None):
    n = N(nt, 'ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
    if stretch:
        mp = N(nt, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch; L(nt, vec, mp.inputs['Vector']); vec = mp.outputs['Vector']
    L(nt, vec, n.inputs['Vector']); return n.outputs[0]
def ramp(nt, fac, stops):
    r = N(nt, 'ShaderNodeValToRGB'); e = r.color_ramp.elements
    while len(e) < len(stops): e.new(0.5)
    for i, (p, c) in enumerate(stops):
        e[i].position = p; e[i].color = (*c, 1) if len(c) == 3 else (c[0], c[0], c[0], 1)
    L(nt, fac, r.inputs['Fac']); return r.outputs['Color']
def mixc(nt, fac, a, b, blend='MIX'):
    m = N(nt, 'ShaderNodeMix', data_type='RGBA', blend_type=blend)
    for sock, v in ((m.inputs[0], fac), (m.inputs[6], a), (m.inputs[7], b)):
        if hasattr(v, 'links'): L(nt, v, sock)
        elif isinstance(v, (int, float)): sock.default_value = v
        else: sock.default_value = (*v, 1)
    return m.outputs[2]
def math_(nt, op, a, b=None):
    m = N(nt, 'ShaderNodeMath', operation=op)
    for i, v in enumerate((a, b)):
        if v is None: continue
        if hasattr(v, 'links'): L(nt, v, m.inputs[i])
        else: m.inputs[i].default_value = v
    return m.outputs[0]
def bump(nt, b, height, strength=0.4, dist=0.02):
    bn = N(nt, 'ShaderNodeBump'); bn.inputs['Strength'].default_value = strength; bn.inputs['Distance'].default_value = dist
    L(nt, height, bn.inputs['Height']); L(nt, bn.outputs['Normal'], b.inputs['Normal'])
def wpos_node(nt): return N(nt, 'ShaderNodeNewGeometry').outputs['Position']

MAT = {}
def m_suelo():
    m, nt, b = new_mat('asfalto_mojado'); p = wpos_node(nt)
    charco = ramp(nt, noise(nt, p, 0.16, 3, 0.5), [(0.47, (0,)), (0.56, (1,))])
    fino = noise(nt, p, 9.0, 8, 0.65); medio = noise(nt, p, 0.7, 4, 0.6)
    br = N(nt, 'ShaderNodeTexBrick'); br.inputs['Scale'].default_value = 1; br.inputs['Mortar Size'].default_value = 0.012
    br.inputs['Brick Width'].default_value = 4; br.inputs['Row Height'].default_value = 4; L(nt, p, br.inputs['Vector']); junta = br.outputs['Fac']
    base = mixc(nt, medio, (0.022, 0.022, 0.024), (0.06, 0.058, 0.054))
    base = mixc(nt, junta, base, (0.008, 0.008, 0.008))
    base = mixc(nt, charco, base, (0.006, 0.007, 0.008))
    L(nt, base, b.inputs['Base Color'])
    seco = math_(nt, 'ADD', math_(nt, 'MULTIPLY', fino, 0.3), 0.3)
    r = N(nt, 'ShaderNodeMix', data_type='FLOAT'); L(nt, charco, r.inputs[0]); L(nt, seco, r.inputs[2]); r.inputs[3].default_value = 0.015
    L(nt, r.outputs[0], b.inputs['Roughness'])
    h = math_(nt, 'SUBTRACT', math_(nt, 'MULTIPLY', fino, math_(nt, 'SUBTRACT', 1.0, charco)), math_(nt, 'MULTIPLY', junta, 1.5))
    bump(nt, b, h, 0.5, 0.015); return m
def m_hormigon(name='hormigon', tone=(0.16, 0.16, 0.155), wet=0.5):
    m, nt, b = new_mat(name); p = wpos_node(nt)
    var = noise(nt, p, 1.3, 6, 0.6); chorreo = ramp(nt, noise(nt, p, 1.0, 5, 0.6, stretch=(2.2, 2.2, 0.12)), [(0.42, (0,)), (0.72, (1,))])
    sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, p, sep.inputs[0])
    tablas = math_(nt, 'LESS_THAN', math_(nt, 'FRACT', math_(nt, 'DIVIDE', sep.outputs['Z'], 1.2)), 0.02)
    zocalo = ramp(nt, sep.outputs['Z'], [(0.0, (1,)), (0.6, (0,))])
    c = mixc(nt, var, tuple(v * 0.75 for v in tone), tuple(v * 1.25 for v in tone))
    c = mixc(nt, math_(nt, 'MULTIPLY', chorreo, 0.75), c, (0.025, 0.024, 0.02))
    c = mixc(nt, math_(nt, 'MULTIPLY', zocalo, 0.6), c, (0.02, 0.022, 0.018))
    L(nt, c, b.inputs['Base Color'])
    L(nt, math_(nt, 'SUBTRACT', 0.8, math_(nt, 'MULTIPLY', chorreo, wet)), b.inputs['Roughness'])
    bump(nt, b, math_(nt, 'SUBTRACT', noise(nt, p, 14, 8, 0.7), math_(nt, 'MULTIPLY', tablas, 2.0)), 0.35, 0.02); return m
def m_simple(name, color, rough=0.5, metal=0.0, emit=None, strength=0.0, grime=0.0, bumpk=0.0, scale=8.0):
    m, nt, b = new_mat(name); p = wpos_node(nt)
    if grime:
        g = noise(nt, p, scale * 0.25, 6, 0.65); L(nt, mixc(nt, math_(nt, 'MULTIPLY', g, grime), color, tuple(v * 0.25 for v in color)), b.inputs['Base Color'])
        L(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', g, 0.3), rough - 0.15), b.inputs['Roughness'])
    else:
        b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = strength
    if bumpk: bump(nt, b, noise(nt, p, scale, 8, 0.7), bumpk, 0.01)
    return m
def m_madera():
    m, nt, b = new_mat('madera_real'); tc = N(nt, 'ShaderNodeTexCoord').outputs['Object']
    veta = noise(nt, tc, 3.0, 8, 0.6, stretch=(1.0, 14.0, 14.0)); man = noise(nt, tc, 2.0, 4, 0.6)
    c = mixc(nt, veta, (0.09, 0.05, 0.022), (0.24, 0.14, 0.06)); c = mixc(nt, math_(nt, 'MULTIPLY', man, 0.5), c, (0.03, 0.02, 0.012))
    L(nt, c, b.inputs['Base Color']); L(nt, math_(nt, 'ADD', math_(nt, 'MULTIPLY', veta, 0.3), 0.35), b.inputs['Roughness']); bump(nt, b, veta, 0.5, 0.01); return m

# ---- texturas escaneadas de Poly Haven (assets/texturas, ver tools/blender/texturas.py): proyección en caja, sin UV
TEXDIR = os.path.join(R, 'assets', 'texturas')
def has_tex(i): return os.path.exists(os.path.join(TEXDIR, i + '_diff.jpg')) and not os.environ.get('LH_NOTEX')
def tex(nt, vec, i, kind, size):
    n = N(nt, 'ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(TEXDIR, '%s_%s.jpg' % (i, kind)), check_existing=True)
    if kind != 'diff': n.image.colorspace_settings.name = 'Non-Color'
    n.projection = 'BOX'; n.projection_blend = 0.2
    mp = N(nt, 'ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / size,) * 3; L(nt, vec, mp.inputs['Vector']); L(nt, mp.outputs['Vector'], n.inputs['Vector']); return n.outputs['Color']
def m_tex(name, i, size, tint=(1, 1, 1), rough_mul=1.0, obj=False, bumpk=0.6, metal=0.0, stains=0.0, plinth=0.0, puddles=False):
    m, nt, b = new_mat(name); p = N(nt, 'ShaderNodeTexCoord').outputs['Object'] if obj else wpos_node(nt); wp = wpos_node(nt)
    c = mixc(nt, 1.0, tex(nt, p, i, 'diff', size), tint, 'MULTIPLY'); r = math_(nt, 'MULTIPLY', tex(nt, p, i, 'rough', size), rough_mul); h = tex(nt, p, i, 'disp', size)
    if stains:
        ch = ramp(nt, noise(nt, wp, 1.0, 5, 0.6, stretch=(2.2, 2.2, 0.12)), [(0.42, (0,)), (0.72, (1,))])
        c = mixc(nt, math_(nt, 'MULTIPLY', ch, stains), c, (0.02, 0.02, 0.017)); r = math_(nt, 'SUBTRACT', r, math_(nt, 'MULTIPLY', ch, 0.3))
    if plinth:
        sep = N(nt, 'ShaderNodeSeparateXYZ'); L(nt, wp, sep.inputs[0])
        c = mixc(nt, math_(nt, 'MULTIPLY', ramp(nt, sep.outputs['Z'], [(0.0, (1,)), (0.7, (0,))]), plinth), c, (0.015, 0.017, 0.013))
    if puddles:
        ch = ramp(nt, noise(nt, wp, 0.16, 3, 0.5), [(0.46, (0,)), (0.56, (1,))])
        c = mixc(nt, ch, c, (0.005, 0.006, 0.007)); mx = N(nt, 'ShaderNodeMix', data_type='FLOAT'); L(nt, ch, mx.inputs[0]); L(nt, r, mx.inputs[2]); mx.inputs[3].default_value = 0.012; r = mx.outputs[0]
        h = math_(nt, 'MULTIPLY', h, math_(nt, 'SUBTRACT', 1.0, ch))
    L(nt, c, b.inputs['Base Color']); L(nt, r, b.inputs['Roughness']); b.inputs['Metallic'].default_value = metal
    bump(nt, b, h, bumpk, 0.03); return m

def build_materials():
    MAT['suelo'] = m_suelo(); MAT['muro'] = m_hormigon('hormigon_muro'); MAT['pared'] = m_hormigon('enfoscado', (0.34, 0.32, 0.28), 0.35)
    MAT['hormigon'] = MAT['muro']; MAT['madera'] = m_madera(); MAT['veta'] = m_simple('madera_oscura', (0.05, 0.03, 0.015), 0.55, grime=0.5, bumpk=0.4)
    MAT['hierro'] = m_simple('hierro', (0.12, 0.11, 0.1), 0.45, 0.9, grime=0.6, bumpk=0.2)
    MAT['oliva'] = m_simple('pintura_oliva', (0.055, 0.075, 0.035), 0.38, grime=0.55, bumpk=0.1, scale=20)
    MAT['bajos'] = m_simple('chasis', (0.018, 0.022, 0.014), 0.5, 0.3, grime=0.5)
    MAT['metal'] = m_simple('galvanizado', (0.3, 0.32, 0.33), 0.38, 0.9, grime=0.7, bumpk=0.15)
    MAT['oscuro'] = m_simple('acero_negro', (0.02, 0.022, 0.025), 0.42, 0.7, grime=0.4)
    MAT['lona'] = m_simple('lona', (0.1, 0.1, 0.06), 0.75, grime=0.5, bumpk=0.5, scale=40)
    MAT['goma'] = m_simple('goma', (0.012, 0.012, 0.013), 0.7, bumpk=0.4, scale=30)
    MAT['cristal'] = m_simple('cristal', (0.01, 0.015, 0.018), 0.04)
    MAT['faro'] = m_simple('faro_apagado', (0.5, 0.45, 0.35), 0.1, emit=(1, 0.6, 0.3), strength=0.15)
    MAT['piloto'] = m_simple('piloto', (0.3, 0.02, 0.02), 0.2, emit=(1, 0.05, 0.03), strength=0.08)
    MAT['aviso'] = m_simple('aviso', (0.5, 0.36, 0.03), 0.5, grime=0.5)
    MAT['tejado'] = m_simple('tela_asfaltica', (0.03, 0.03, 0.032), 0.45, grime=0.5, bumpk=0.5, scale=3)
    MAT['ventana_on'] = m_simple('ventana_luz', (0.8, 0.6, 0.35), 0.2, emit=(1.0, 0.62, 0.3), strength=9.0)
    MAT['ventana_off'] = m_simple('ventana_oscura', (0.01, 0.014, 0.018), 0.05)
    MAT['bombilla'] = m_simple('sodio', (1, 0.6, 0.2), 0.3, emit=(1.0, 0.5, 0.14), strength=120.0)
    MAT['baliza'] = m_simple('baliza', (1, 0.05, 0.02), 0.3, emit=(1.0, 0.04, 0.02), strength=60.0)
    MAT['foco'] = m_simple('foco', (1, 1, 1), 0.3, emit=(0.8, 0.9, 1.0), strength=400.0)
    MAT['marisma'] = m_simple('marisma', (0.008, 0.012, 0.012), 0.08, bumpk=0.15, scale=0.6)
    # con texturas descargadas, las superficies grandes pasan a material escaneado
    if has_tex('asphalt_02'): MAT['suelo'] = m_tex('asfalto_mojado_tex', 'asphalt_02', 3.0, (0.3, 0.3, 0.32), 0.45, puddles=True, bumpk=0.8)
    if has_tex('concrete_wall_008'): MAT['muro'] = MAT['hormigon'] = m_tex('hormigon_tex', 'concrete_wall_008', 3.2, (0.5, 0.5, 0.5), 0.8, stains=0.8, plinth=0.6)
    if has_tex('painted_plaster_wall'): MAT['pared'] = m_tex('enfoscado_tex', 'painted_plaster_wall', 2.6, (0.62, 0.6, 0.55), 0.9, stains=0.6, plinth=0.7)
    if has_tex('wood_planks_dirt'): MAT['madera'] = m_tex('madera_tex', 'wood_planks_dirt', 1.6, (0.8, 0.7, 0.6), 0.85, obj=True)
    if has_tex('rusty_metal_02'): MAT['hierro'] = m_tex('hierro_tex', 'rusty_metal_02', 1.4, (0.5, 0.5, 0.5), 0.8, metal=0.6)
    if has_tex('green_metal_rust'): MAT['oliva'] = m_tex('pintura_oliva_tex', 'green_metal_rust', 2.2, (0.32, 0.4, 0.2), 0.7, obj=True, bumpk=0.25)
    if has_tex('corrugated_iron_02'): MAT['tejado'] = m_tex('uralita_tex', 'corrugated_iron_02', 2.0, (0.35, 0.35, 0.36), 0.8, metal=0.5)
    MAT['suelo_int'] = m_tex('suelo_interior_tex', 'concrete_floor_worn_001', 2.0, (0.55, 0.55, 0.55), 0.9) if has_tex('concrete_floor_worn_001') else m_simple('suelo_interior', (0.12, 0.12, 0.115), 0.6, grime=0.4)
    MAT['techo_int'] = m_simple('techo_interior', (0.3, 0.29, 0.26), 0.9, grime=0.3)
    if GLB:   # para el visor: materiales lisos con nombre; las texturas y el mojado los pone el visor
        for k in list(MAT):
            m = bpy.data.materials.new('lh_' + k); m.use_nodes = True; MAT[k] = m
    m, nt, b = new_mat('lluvia'); b.inputs['Base Color'].default_value = (0.8, 0.85, 0.9, 1); b.inputs['Roughness'].default_value = 0.1
    b.inputs['Alpha'].default_value = 0.3; MAT['lluvia'] = m

# ---------------------------------------------------------------- geometría por lotes (una malla por material)
BM = {}
def bm_of(mat):
    if mat not in BM: BM[mat] = bmesh.new()
    return BM[mat]
def box(mat, size, center, rotz=0.0, rot=None):
    bm = bm_of(mat); r = bmesh.ops.create_cube(bm, size=1.0)
    M = Matrix.Translation(center) @ (rot if rot is not None else Matrix.Rotation(rotz, 4, 'Z')) @ Matrix.Diagonal((*size, 1))
    bmesh.ops.transform(bm, matrix=M, verts=r['verts'])
def cyl(mat, radius, depth, center, rot=None, seg=16):
    bm = bm_of(mat); r = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=radius, radius2=radius, depth=depth)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(center) @ (rot if rot is not None else Matrix.Identity(4)), verts=r['verts'])
def box_uv(me):
    """UV por proyección en caja, en metros: el visor repite la textura según su tamaño real."""
    uv = (me.uv_layers[0] if me.uv_layers else me.uv_layers.new(name='UVMap')).data; vs = me.vertices; ls = me.loops
    for poly in me.polygons:
        n = poly.normal; ax = 2 if abs(n.z) >= abs(n.x) and abs(n.z) >= abs(n.y) else (0 if abs(n.x) >= abs(n.y) else 1)
        for li in poly.loop_indices:
            c = vs[ls[li].vertex_index].co; uv[li].uv = (c.x, c.y) if ax == 2 else ((c.y, c.z) if ax == 0 else (c.x, c.z))
def flush(prefix='base'):
    for mat, bm in BM.items():
        me = bpy.data.meshes.new(prefix + '_' + mat); bm.to_mesh(me); bm.free(); me.materials.append(MAT[mat])
        o = bpy.data.objects.new(prefix + '_' + mat, me); col.objects.link(o); box_uv(me)
        if mat not in ('lluvia',) and not GLB:
            md = o.modifiers.new('bisel', 'BEVEL'); md.width = 0.015; md.segments = 2; md.limit_method = 'ANGLE'
    BM.clear()

HW, HB = 4.6, 3.6   # altura del muro perimetral y de los edificios
def build_world():
    # suelo de la base y marisma alrededor
    box('suelo', (COLS * T, ROWS * T, 0.4), (COLS * T / 2, -ROWS * T / 2, -0.2))
    box('marisma', (900, 900, 0.2), (COLS * T / 2, -ROWS * T / 2, -0.45))
    for y in range(ROWS):
        for x in range(COLS):
            c = cell(x, y); p = wpos(x, y)
            if c == '#':
                box('muro', (T, T * 0.45, HW) if (y in (0, ROWS - 1)) else (T * 0.45, T, HW) if x in (0, COLS - 1) else (T * 0.5, T, HW), p + Vector((0, 0, HW / 2)))
                if (x + y) % 3 == 0 and (x in (0, COLS - 1) or y in (0, ROWS - 1)):   # contrafuerte y poste de alambrada
                    box('muro', (0.6, 0.6, HW + 0.1), p + Vector((0, 0, HW / 2)))
                    box('oscuro', (0.06, 0.06, 1.0), p + Vector((0, 0, HW + 0.5)))
            elif c == 'W':
                box('pared', (T, T, HB), p + Vector((0, 0, HB / 2)))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):      # ventanas hacia el patio
                    n = cell(x + dx, y + dy)
                    if n in '.slP' and rnd(x, y, dx * 3 + dy) < 0.42:
                        on = rnd(x, y, 9 + dx + dy * 2) < 0.55; q = p + Vector((dx * (T / 2 + 0.005), -dy * (T / 2 + 0.005), 2.05))
                        s = (0.05, 1.15, 0.85) if dx else (1.15, 0.05, 0.85)
                        box('ventana_on' if on else 'ventana_off', s, q)
                        fr = (0.09, 1.3, 0.07) if dx else (1.3, 0.09, 0.07)
                        box('oscuro', fr, q + Vector((0, 0, 0.46))); box('pared', (0.16, 1.4, 0.08) if dx else (1.4, 0.16, 0.08), q + Vector((0, 0, -0.47)))
                        for k in (-0.38, -0.19, 0, 0.19, 0.38):           # reja
                            box('oscuro', (0.03, 0.03, 0.9), q + (Vector((dx * 0.05, k, 0)) if dx else Vector((k, -dy * 0.05, 0))))
            elif c in 'DLVbB':
                horiz = cell(x - 1, y) in 'W#' and cell(x + 1, y) in 'W#'     # el muro corre en X: la puerta mira a ±Y
                top = HB if building(x, y) or c != 'D' or True else HW
                mat = 'pared'
                if horiz:
                    box(mat, (T, 0.5, top - 2.2), p + Vector((0, 0, 2.2 + (top - 2.2) / 2)))
                    for s in (-1, 1): box(mat, (0.35, 0.5, 2.2), p + Vector((s * 0.825, 0, 1.1)))
                    box('hierro', (1.3, 0.07, 2.2), p + Vector((0, 0, 1.1))); box('oscuro', (0.05, 0.12, 0.2), p + Vector((0.45, 0, 1.05)))
                else:
                    box(mat, (0.5, T, top - 2.2), p + Vector((0, 0, 2.2 + (top - 2.2) / 2)))
                    for s in (-1, 1): box(mat, (0.5, 0.35, 2.2), p + Vector((0, s * 0.825, 1.1)))
                    box('hierro', (0.07, 1.3, 2.2), p + Vector((0, 0, 1.1))); box('oscuro', (0.12, 0.05, 0.2), p + Vector((0, 0.45, 1.05)))
            if building(x, y) or c in 'LVbB' or (c == 'D' and (roomy(x - 1, y) or roomy(x + 1, y) or roomy(x, y - 1) or roomy(x, y + 1))):
                box('tejado', (T + 0.02, T + 0.02, 0.22), p + Vector((0, 0, HB + 0.11)))
                if c != 'W': box('suelo_int', (T, T, 0.03), p + Vector((0, 0, 0.012))); box('techo_int', (T, T, 0.04), p + Vector((0, 0, HB - 0.02)))
                if c == 'W': box('pared', (T + 0.14, T + 0.14, 0.3), p + Vector((0, 0, HB + 0.33)))   # peto
                elif rnd(x, y, 5) < 0.06: box('metal', (1.1, 0.8, 0.7), p + Vector((0, 0, HB + 0.57)), rotz=rnd(x, y, 6))
                elif rnd(x, y, 7) < 0.04: cyl('metal', 0.18, 1.1, p + Vector((0, 0, HB + 0.75)))
    # alambrada sobre el muro: tres hilos por lado
    Wm, Hm = COLS * T, ROWS * T
    for k in range(3):
        z = HW + 0.35 + k * 0.28
        for yy in (-1.0, -(Hm - 1.0)): box('oscuro', (Wm - 2, 0.02, 0.02), (Wm / 2, yy, z))
        for xx in (1.0, Wm - 1.0): box('oscuro', (0.02, Hm - 2, 0.02), (xx, -Hm / 2, z))
    # mástil de antena sobre comunicaciones, con baliza roja
    a = wpos(9, 11, HB + 0.2)
    for sx in (-1, 1):
        for sy in (-1, 1): box('metal', (0.06, 0.06, 14), a + Vector((sx * 0.3, sy * 0.3, 7)))
    for i in range(14):
        z = 0.5 + i; s = 1 if i % 2 else -1
        for sy in (-1, 1): box('metal', (0.72, 0.03, 0.03), a + Vector((0, sy * 0.3, z)), rot=Matrix.Rotation(s * sy * 0.95, 4, 'Y'))
        for sx in (-1, 1): box('metal', (0.03, 0.72, 0.03), a + Vector((sx * 0.3, 0, z)), rot=Matrix.Rotation(s * sx * 0.95, 4, 'X'))
    cyl('baliza', 0.12, 0.25, a + Vector((0, 0, 14.2)), seg=10)
    for k in range(3): box('oscuro', (1.6, 0.04, 0.04), a + Vector((0, 0, 10 + k * 1.2)), rotz=k * 1.0)
    flush()

CAM_XY = [(3.0, -11.4), (18.4, -18.0), (40.2, -13.4), (49.4, -26.0)]   # posiciones de las cámaras a pie de suelo
def rain(n=34000):
    # cada gota es una raya: dos planos cruzados muy finos, inclinados por el viento
    V, F = [], []
    for i in range(n):
        x = random.uniform(-4, COLS * T + 4); y = -random.uniform(-4, ROWS * T + 4); z = random.uniform(0.2, 12); l = random.uniform(0.3, 0.75); w = 0.0013
        if any((x - cx) ** 2 + (y - cy) ** 2 < 20 for cx, cy in CAM_XY): continue
        for ax, ay in ((w, 0), (0, w)):
            k = len(V); V += [(x - ax, y - ay, z), (x + ax, y + ay, z), (x + ax + l * 0.07, y + ay, z + l), (x - ax + l * 0.07, y - ay, z + l)]; F.append((k, k + 1, k + 2, k + 3))
    me = bpy.data.meshes.new('lluvia'); me.from_pydata(V, [], F); me.materials.append(MAT['lluvia'])
    o = bpy.data.objects.new('lluvia', me); col.objects.link(o); o.visible_shadow = False

# ---------------------------------------------------------------- modelos del juego (assets/models/*.glb) con materiales reales
PROTO = {}
def proto(name):
    if name in PROTO: return PROTO[name]
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(R, 'assets', 'models', name + '.glb'))
    o = [x for x in bpy.data.objects if x not in before and x.type == 'MESH'][0]
    for x in [x for x in bpy.data.objects if x not in before and x is not o]: bpy.data.objects.remove(x)
    o.parent = None; o.rotation_mode = 'XYZ'
    for i, s in enumerate(o.material_slots):
        base = s.material.name.split('.')[0]
        s.material = MAT.get(base, MAT['metal'])
    box_uv(o.data)
    if not GLB: md = o.modifiers.new('bisel', 'BEVEL'); md.width = 0.012; md.segments = 2; md.limit_method = 'ANGLE'
    for c in list(o.users_collection): c.objects.unlink(o)
    PROTO[name] = o; return o
def place(name, pos, rotz=0.0, scale=1.0):
    o = proto(name).copy(); col.objects.link(o); o.location = pos; o.rotation_euler = (0, 0, rotz); o.scale = (scale,) * 3; return o

def lamp(kind, name, pos, color, power, **kw):
    d = bpy.data.lights.new(name, kind); d.color = color; d.energy = power
    for k, v in kw.items(): setattr(d, k, v)
    o = bpy.data.objects.new(name, d); col.objects.link(o); o.location = pos; LIGHTS.append(o); return o
def aim(o, target):
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()

# ---------------------------------------------------------------- piezas redondeadas (sombreado suave) para vehículos
SM = {}
def _append(mat, bm):
    me = bpy.data.meshes.new('tmp'); bm.to_mesh(me); bm.free()
    if mat not in SM: SM[mat] = bmesh.new()
    SM[mat].from_mesh(me); bpy.data.meshes.remove(me)
def rbox(mat, size, center, r=0.04, seg=3, rot=None, M0=None):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if r > 0: bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(r, min(size) * 0.45), segments=seg, affect='EDGES', profile=0.5)
    M = Matrix.Translation(center) @ (rot if rot is not None else Matrix.Identity(4))
    bmesh.ops.transform(bm, matrix=(M0 @ M) if M0 is not None else M, verts=bm.verts); _append(mat, bm)
def rcyl(mat, radius, depth, center, axis='Z', r=0.03, seg=28, M0=None, bseg=3):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=radius, radius2=radius, depth=depth)
    if r > 0:
        rim = [e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6 and abs(abs(e.verts[0].co.z) - depth / 2) < 1e-6]
        bmesh.ops.bevel(bm, geom=rim, offset=min(r, depth * 0.45, radius * 0.45), segments=bseg, affect='EDGES', profile=0.5)
    rot = {'Z': Matrix.Identity(4), 'X': Matrix.Rotation(math.pi / 2, 4, 'Y'), 'Y': Matrix.Rotation(math.pi / 2, 4, 'X')}[axis]
    M = Matrix.Translation(center) @ rot
    bmesh.ops.transform(bm, matrix=(M0 @ M) if M0 is not None else M, verts=bm.verts); _append(mat, bm)
def flush_smooth(prefix):
    for mat, bm in SM.items():
        me = bpy.data.meshes.new(prefix + '_' + mat); bm.to_mesh(me); bm.free(); me.materials.append(MAT[mat])
        me.polygons.foreach_set('use_smooth', [True] * len(me.polygons)); me.set_sharp_from_angle(angle=math.radians(38)); box_uv(me)
        o = bpy.data.objects.new(prefix + '_' + mat, me); col.objects.link(o)
    SM.clear()

def rprofile(mat, pts, width, center=(0, 0, 0), r=0.03, seg=2, M0=None, along='X'):
    """Extruye un perfil 2D. along='X': puntos (y, z) extruidos a lo ancho; along='Y': puntos (x, z) extruidos a lo largo."""
    bm = bmesh.new(); f = bm.faces.new([bm.verts.new((-width / 2, a, b)) for a, b in pts])
    ext = bmesh.ops.extrude_face_region(bm, geom=[f]); bmesh.ops.translate(bm, vec=(width, 0, 0), verts=[e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)])
    if r > 0: bmesh.ops.bevel(bm, geom=list(bm.edges), offset=r, segments=seg, affect='EDGES', profile=0.5, clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    M = Matrix.Translation(center) @ (Matrix(((0, 1, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))) if along == 'Y' else Matrix.Identity(4))
    bmesh.ops.transform(bm, matrix=(M0 @ M) if M0 is not None else M, verts=bm.verts); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); _append(mat, bm)

def truck(pos, rotz):
    """Camión ligero 4x4 de cabina corta y ruedas grandes (del estilo de los Unimog de la época), con caja de lona.
    Frente hacia -Y; mide 4 x 2,1 m y cabe en el bloque de 4 x 4 m del plano."""
    M0 = Matrix.Translation(pos) @ Matrix.Rotation(rotz, 4, 'Z'); V = Vector; rad = math.radians
    B = lambda mat, size, c, r=0.02, rot=None: rbox(mat, size, V(c), r, 2, rot, M0)
    C = lambda mat, ra, dep, c, axis='Z', r=0.02, seg=24: rcyl(mat, ra, dep, V(c), axis, r, seg, M0)
    Pr = lambda mat, pts, w, c=(0, 0, 0), r=0.03, along='X': rprofile(mat, pts, w, V(c), r, 2, M0, along)
    arc = lambda y0, z0, R, th, a0=18, a1=162, n=10: [(y0 + R * math.cos(rad(a0 + (a1 - a0) * k / n)), z0 + R * math.sin(rad(a0 + (a1 - a0) * k / n))) for k in range(n + 1)] + [(y0 + (R - th) * math.cos(rad(a1 - (a1 - a0) * k / n)), z0 + (R - th) * math.sin(rad(a1 - (a1 - a0) * k / n))) for k in range(n + 1)]
    RW, ZW = 0.5, 0.5; AX = (-1.12, 1.18)
    # ruedas con taco, llanta de disco y tuercas
    for s in (-1, 1):
        for y in AX:
            x = s * 0.86
            C('goma', RW - 0.025, 0.3, (x, y, ZW), 'X', 0.07, 40)
            for k in range(26):
                a = k * 2 * math.pi / 26; side = 1 if k % 2 else -1
                rbox('goma', (0.15, 0.085, 0.05), V((x + side * 0.07, y + math.cos(a) * (RW - 0.012), ZW + math.sin(a) * (RW - 0.012))), 0.008, 1, Matrix.Rotation(a - math.pi / 2, 4, 'X') @ Matrix.Rotation(side * 0.35, 4, 'Z'), M0)
            C('goma', 0.41, 0.33, (x, y, ZW), 'X', 0.05, 40)                                   # flanco
            C('oliva', 0.31, 0.2, (x + s * 0.075, y, ZW), 'X', 0.03, 32); C('bajos', 0.25, 0.2, (x + s * 0.079, y, ZW), 'X', 0.04, 28); C('oliva', 0.2, 0.2, (x + s * 0.086, y, ZW), 'X', 0.03, 24)
            C('oliva', 0.09, 0.14, (x + s * 0.15, y, ZW), 'X', 0.03, 16)
            for k in range(6):
                a = k * math.pi / 3; C('metal', 0.02, 0.03, (x + s * 0.186, y + math.cos(a) * 0.15, ZW + math.sin(a) * 0.15), 'X', 0.004, 6)
            # ballestas y guardabarros
            for k in range(4): B('bajos', (0.07, 1.0 - k * 0.16, 0.022), (s * 0.5, y, ZW + 0.2 + k * 0.024), 0.004)
        Pr('oliva', arc(AX[0], ZW, 0.66, 0.035), 0.44, (s * 0.86, 0, 0), 0.01)
        Pr('bajos', arc(AX[1], ZW, 0.64, 0.03, 30, 150), 0.4, (s * 0.86, 0, 0), 0.008)
        B('goma', (0.4, 0.02, 0.36), (s * 0.86, AX[1] + 0.6, 0.52), 0.004)
        B('bajos', (0.12, 3.75, 0.2), (s * 0.4, 0.02, 0.86), 0.02)                               # largueros
        B('bajos', (0.3, 0.6, 0.05), (s * 1.0, -0.62, 0.72), 0.012); B('bajos', (0.04, 0.04, 0.3), (s * 0.95, -0.4, 0.86), 0.008); B('bajos', (0.04, 0.04, 0.3), (s * 0.95, -0.84, 0.86), 0.008)   # estribo
        # faros con aro, intermitentes, retrovisores, puertas
        C('oscuro', 0.125, 0.07, (s * 0.72, -1.93, 1.22), 'Y', 0.015, 24); C('faro', 0.1, 0.06, (s * 0.72, -1.955, 1.22), 'Y', 0.02, 24); C('metal', 0.112, 0.02, (s * 0.72, -1.962, 1.22), 'Y', 0.006, 24)
        B('piloto', (0.09, 0.035, 0.06), (s * 0.72, -1.95, 1.4), 0.01)
        B('oscuro', (0.025, 0.025, 0.42), (s * 1.06, -1.2, 1.95), 0.006, Matrix.Rotation(s * -0.25, 4, 'Y')); B('oscuro', (0.035, 0.15, 0.24), (s * 1.12, -1.22, 2.12), 0.015)
        B('cristal', (0.02, 0.62, 0.4), (s * 1.004, -0.64, 1.98), 0.006)
        for yy in (-1.02, -0.22): B('bajos', (0.012, 0.014, 0.72), (s * 1.006, yy, 1.36), 0)   # juntas de la puerta
        B('bajos', (0.012, 0.8, 0.014), (s * 1.006, -0.62, 1.0), 0); B('metal', (0.025, 0.11, 0.025), (s * 1.02, -0.32, 1.62), 0.008)
        # adrales de chapa con nervios, pilotos traseros
        B('oliva', (0.035, 1.98, 0.42), (s * 1.03, 1.0, 1.31), 0.008); B('oliva', (0.05, 1.98, 0.04), (s * 1.035, 1.0, 1.52), 0.01)
        for yy in (0.1, 0.55, 1.0, 1.45, 1.9): B('oliva', (0.05, 0.06, 0.4), (s * 1.045, yy, 1.3), 0.01)
        for yy in (0.4, 1.0, 1.6): B('metal', (0.03, 0.05, 0.03), (s * 1.07, yy, 1.42), 0.006); B('oscuro', (0.012, 0.03, 0.34), (s * 1.075, yy, 1.6), 0.003)   # ganchos y correas de la lona
        B('piloto', (0.12, 0.03, 0.08), (s * 0.88, 2.0, 1.0), 0.01); B('faro', (0.06, 0.03, 0.06), (s * 0.72, 2.0, 1.0), 0.008)
        B('bajos', (0.05, 0.16, 0.08), (s * 0.5, -1.99, 0.84), 0.015)                           # ganchos de remolque
    for y in AX:
        C('bajos', 0.065, 1.6, (0, y, ZW), 'X', 0, 12); B('bajos', (0.34, 0.36, 0.34), (0.12, y, ZW), 0.13)
    C('bajos', 0.045, 2.2, (0.12, 0.03, 0.6), 'Y', 0, 8)
    B('bajos', (2.0, 0.1, 0.2), (0, -1.93, 0.82), 0.03); B('bajos', (1.9, 0.08, 0.14), (0, 1.97, 0.84), 0.02); B('metal', (0.4, 0.015, 0.11), (0.0, -1.985, 0.82), 0.003)
    # cabina: perfil con morro corto inclinado y parabrisas tendido
    Pr('oliva', [(-1.9, 0.95), (-1.9, 1.5), (-1.82, 1.6), (-1.38, 1.72), (-1.12, 2.3), (-0.2, 2.3), (-0.12, 2.22), (-0.12, 0.95)], 2.0, r=0.045)
    Pr('lona', [(-1.1, 2.3), (-1.06, 2.36), (-0.24, 2.36), (-0.2, 2.3)], 1.9, r=0.012)
    ws = Matrix.Rotation(math.atan2(0.58, 0.26), 4, 'X')
    for s in (-1, 1): B('cristal', (0.82, 0.5, 0.02), (s * 0.44, -1.262, 2.005), 0.004, ws)
    B('oliva', (0.05, 0.56, 0.03), (0, -1.265, 2.006), 0.006, ws); B('bajos', (1.84, 0.025, 0.03), (0, -1.395, 1.735), 0.006)
    for s in (-1, 1): B('oscuro', (0.4, 0.014, 0.014), (s * 0.4, -1.375, 1.82), 0.003, Matrix.Rotation(s * 0.5, 4, 'Y') @ ws)
    B('oscuro', (1.24, 0.03, 0.42), (0, -1.905, 1.22), 0.01)
    for k in range(5): B('oliva', (1.2, 0.03, 0.035), (0, -1.925, 1.06 + k * 0.08), 0.008)
    B('oliva', (0.05, 0.05, 0.06), (0, -1.8, 1.64), 0.012)
    C('oscuro', 0.006, 1.7, (-0.9, -0.2, 3.1), 'Z', 0, 5); C('oscuro', 0.03, 0.12, (-0.9, -0.2, 2.3), 'Z', 0.008, 8)    # antena
    C('oscuro', 0.045, 1.5, (0.94, -0.06, 1.75), 'Z', 0.01, 12); C('metal', 0.07, 0.42, (0.94, -0.06, 1.35), 'Z', 0.02, 12)   # escape
    C('oliva', 0.21, 0.6, (-0.82, 0.3, 0.8), 'Y', 0.05, 20); C('metal', 0.04, 0.04, (-0.82, 0.3, 1.02), 'Z', 0.008, 10)        # depósito
    B('bajos', (0.36, 0.56, 0.34), (0.84, 0.3, 0.8), 0.025)
    # caja y lona con arcos
    B('bajos', (2.06, 1.98, 0.1), (0, 1.0, 1.06), 0.015); B('oliva', (2.06, 0.035, 0.42), (0, 1.975, 1.31), 0.008); B('oliva', (2.06, 0.035, 0.42), (0, 0.025, 1.31), 0.008)
    lona = [(-1.05, 1.5), (-1.05, 2.12), (-0.96, 2.32), (-0.72, 2.45), (-0.3, 2.5), (0.3, 2.5), (0.72, 2.45), (0.96, 2.32), (1.05, 2.12), (1.05, 1.5)]
    Pr('lona', lona, 1.94, (0, 1.0, 0), 0.03, 'Y')
    for yy in (0.06, 0.68, 1.32, 1.94): Pr('lona', [(x * 1.014, 1.5 + (z - 1.5) * 1.012) for x, z in lona], 0.05, (0, yy, 0), 0.012, 'Y')
    B('oscuro', (1.7, 0.012, 0.9), (0, 1.975, 1.98), 0.004)                                 # trasera abierta en sombra
    for s in (-1, 1): Pr('lona', [(-0.12, 1.5), (-0.12, 2.3), (0.12, 2.42), (0.12, 1.5)], 0.03, (s * 0.92, 1.985, 0), 0.008, 'Y')
    C('lona', 0.07, 1.8, (0, 1.99, 2.42), 'X', 0.02, 12)                                    # lona trasera enrollada
    if has_ph('metal_jerrycan_green'):
        for k in (0, 1): put('metal_jerrycan_green', M0 @ V((1.0 if not k else -1.0, -0.62 + 0.0, 0.745)), rotz + math.pi / 2)

# ---------------------------------------------------------------- modelos escaneados de Poly Haven (assets/modelos-ph)
PHDIR = os.path.join(R, 'assets', 'modelos-ph'); PH = {}
def has_ph(i): return os.path.exists(os.path.join(PHDIR, i, i + '.gltf')) and not os.environ.get('LH_NOPH')
def ph(i, only=None):
    key = (i, only)
    if key in PH: return PH[key]
    before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=os.path.join(PHDIR, i, i + '.gltf'))
    new = [o for o in bpy.data.objects if o not in before]; bpy.context.view_layer.update()
    keep = [o for o in new if o.type == 'MESH' and (only is None or o.name.split('.')[0] in only or (callable(only) and only(o.name)))]
    mats = [(o, o.matrix_world.copy()) for o in keep]
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o, mw in mats:
        for c in o.bound_box:
            w = mw @ Vector(c)
            for k in range(3): mn[k] = min(mn[k], w[k]); mx[k] = max(mx[k], w[k])
        for s in o.material_slots:                  # mojado por la lluvia: menos rugosidad
            b = s.material.node_tree.nodes.get('Principled BSDF') if s.material and s.material.node_tree else None
            if b and not GLB and not s.material.get('lh_wet'):
                s.material['lh_wet'] = 1; inp = b.inputs['Roughness']
                if inp.is_linked:
                    src_ = inp.links[0].from_socket; nt = s.material.node_tree; mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = 0.6
                    nt.links.new(src_, mm.inputs[0]); nt.links.new(mm.outputs[0], inp)
    if GLB:   # para tiempo real: se reduce la malla escaneada
        total = sum(len(o.data.polygons) for o, _ in mats); budget = {'covered_car': 7000, 'street_lamp_01': 2600, 'wooden_military_crate': 1300, 'wooden_crate_02': 900}.get(i, 1600)
        if total > budget:
            for o, _ in mats:
                md = o.modifiers.new('dec', 'DECIMATE'); md.ratio = budget / total
                me2 = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get())); o.modifiers.clear(); o.data = me2
    off = Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z))
    for o in new:
        o.parent = None
        for c in list(o.users_collection): c.objects.unlink(o)
    PH[key] = ([(o, off @ mw) for o, mw in mats], mx - mn); return PH[key]
def put(i, pos, rotz=0.0, scale=1.0, only=None, rot=None):
    parts, dim = ph(i, only); M = Matrix.Translation(pos) @ (rot if rot is not None else Matrix.Rotation(rotz, 4, 'Z')) @ Matrix.Scale(scale, 4)
    for o, mw in parts:
        c = o.copy(); col.objects.link(c); c.matrix_world = M @ mw
    return dim

def crate_stack(p, x, y):
    """Pila de cajas militares que ocupa la casilla (1,8 x 1,8 m) y tapa la vista (1,4 m)."""
    turn = int(rnd(x, y, 1) * 2) * math.pi / 2; kind = rnd(x, y, 8)
    if kind < 0.7 and has_ph('wooden_military_crate'):
        for layer in range(3):
            a = turn + (math.pi / 2 if layer % 2 else 0)
            for k in (-1, 0, 1):
                if layer == 2 and rnd(x, y, 20 + k) < 0.22: continue
                d = Vector((math.cos(a + math.pi / 2), math.sin(a + math.pi / 2), 0)) * (k * 0.55)
                put('wooden_military_crate', p + d + Vector(((rnd(x, y, 30 + k + layer * 3) - 0.5) * 0.06, (rnd(x, y, 40 + k + layer * 3) - 0.5) * 0.06, layer * 0.462)), a + (rnd(x, y, 50 + k + layer * 3) - 0.5) * 0.07)
    elif has_ph('wooden_crate_02'):
        for layer in range(3):
            a = turn + (math.pi / 2 if layer % 2 else 0)
            for k in (-1, 0, 1):
                d = Vector((math.cos(a), math.sin(a), 0)) * (k * 0.56)
                put('wooden_crate_02', p + d + Vector((0, 0, layer * 0.455)), a + (rnd(x, y, 50 + k + layer * 3) - 0.5) * 0.06, 1.0)
    else:
        place('caja', p, turn)

def pick_lamps(min_d=17.0):
    """De las farolas del plano se queda con las que distan al menos min_d metros entre sí, empezando por las más céntricas."""
    cells = [(x, y) for y in range(ROWS) for x in range(COLS) if cell(x, y) == 'l' and not building(x, y)]
    cells.sort(key=lambda c: abs(c[0] - COLS / 2) + abs(c[1] - ROWS / 2)); keep = []
    for c in cells:
        if all(math.hypot((c[0] - k[0]) * T, (c[1] - k[1]) * T) >= min_d for k in keep): keep.append(c)
    print('FAROLAS', len(keep), 'de', len(cells), keep, flush=True); return set(keep)
def build_props():
    seen = set(); ntruck = 0; LAMPS = pick_lamps()
    for y in range(ROWS):
        for x in range(COLS):
            c = cell(x, y); p = wpos(x, y)
            if c == 'c': crate_stack(p, x, y)
            elif c == 'T' and (x, y) not in seen:
                seen.update({(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)}); ntruck += 1; q = p + Vector((T / 2, -T / 2, 0))
                if ntruck == 3 and has_ph('covered_car'): put('covered_car', q + Vector((-0.6, 0, 0)), 0.08); put('concrete_road_barrier', q + Vector((1.2, 0.3, 0)), math.pi / 2 + 0.05)
                else: truck(q, (math.pi if rnd(x, y, 1) < 0.5 else 0) + (rnd(x, y, 2) - 0.5) * 0.1)
            elif c == 'g':
                place('generador', p, 0)
                if has_ph('metal_jerrycan_green'): put('metal_jerrycan_green', p + Vector((1.3, -0.5, 0)), 0.4); put('metal_jerrycan_green', p + Vector((1.35, -0.1, 0)), 1.9)
            elif c == 'l' and (x, y) in LAMPS:
                if has_ph('street_lamp_01'):
                    a = (x * 3 + y) % 4 * math.pi / 2; put('street_lamp_01', p, a)
                    h = Matrix.Rotation(a, 4, 'Z') @ LAMP_HEAD; cyl('bombilla', 0.05, 0.04, p + h + Vector((0, 0, -0.03)), seg=10)
                    lamp('POINT', 'farola', p + h + Vector((0, 0, -0.16)), (1.0, 0.55, 0.2), 2200, shadow_soft_size=0.07)
                else:
                    place('farola', p); cyl('bombilla', 0.07, 0.12, p + Vector((0, 0, 3.17)), seg=10); lamp('POINT', 'farola', p + Vector((0, 0, 3.05)), (1.0, 0.55, 0.2), 1500, shadow_soft_size=0.08)
            elif c == 's' and rnd(x, y, 11) < 0.4 and has_ph('Barrel_01'):
                n = 2 + int(rnd(x, y, 12) * 3)
                for i in range(n):
                    put(('Barrel_01', 'Barrel_02', 'barrel_03')[int(rnd(x, y, 60 + i) * 3)], p + Vector((-0.6 + (i % 3) * 0.6, 0.55 - (i // 3) * 0.6 - 0.1 * (i % 2), 0)), rnd(x, y, 70 + i) * 6)
                if rnd(x, y, 13) < 0.5 and has_ph('old_tyre'): put('old_tyre', p + Vector((0.5, -0.6, 0.08)), rnd(x, y, 14) * 3, rot=Matrix.Rotation(math.pi / 2, 4, 'X'))
            # trastos pequeños junto a las cajas: no ocupan casilla
            if c == 'c' and cell(x + 1, y) == '.' and rnd(x, y, 15) < 0.45:
                q = p + Vector((1.25, (rnd(x, y, 16) - 0.5) * 1.0, 0)); k = rnd(x, y, 17)
                if k < 0.35 and has_ph('ammo_box'): put('ammo_box', q, k * 9); put('ammo_box', q + Vector((0.05, 0.3, 0)), k * 5)
                elif k < 0.6 and has_ph('metal_jerrycan_green'): put('metal_jerrycan_green', q, k * 9)
                elif k < 0.8 and has_ph('trashbag'): put('trashbag', q, k * 9)
                elif has_ph('wooden_crate_01'): put('wooden_crate_01', q, k * 9)
            # paredes: luminaria sobre las puertas, cajas eléctricas, aire acondicionado y bajantes
            if c in 'DLV':
                horiz = cell(x - 1, y) in 'W#' and cell(x + 1, y) in 'W#'
                for sgn in (-1, 1):
                    nx, ny = (x, y + sgn) if horiz else (x + sgn, y)
                    if cell(nx, ny) in '.sl' and has_ph('industrial_wall_lamp') and rnd(x, y, 90 + sgn) < 0.5:
                        n = Vector((0, -sgn, 0)) if horiz else Vector((sgn, 0, 0)); q = p + n * 0.33 + Vector((0, 0, 2.55))
                        put('industrial_wall_lamp', q, math.atan2(n.y, n.x) + math.pi / 2)
                        lamp('POINT', 'aplique', q + n * 0.12 + Vector((0, 0, -0.12)), (1.0, 0.72, 0.42), 55, shadow_soft_size=0.05)
            if c == 'W':
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if cell(x + dx, y + dy) not in '.sl': continue
                    n = Vector((dx, -dy, 0)); ang = math.atan2(n.y, n.x) + math.pi / 2; k = rnd(x, y, 80 + dx * 2 + dy)
                    side = Vector((-n.y, n.x, 0))
                    if k < 0.1 and has_ph('exterior_aircon_unit'): put('exterior_aircon_unit', p + n * 1.2 + Vector((0, 0, 2.6)), ang, only=('exterior_aircon_unit',))
                    elif k < 0.18 and has_ph('utility_box_01'): put('utility_box_01', p + n * 1.22 + side * 0.5, ang)
                    elif k < 0.3:                                                             # bajante con abrazaderas
                        q = p + n * 1.07 + side * 0.8; cyl('metal', 0.05, HB + 0.1, q + Vector((0, 0, HB / 2)), seg=10)
                        for z in (0.5, 1.8, 3.1): box('oscuro', (0.14, 0.14, 0.03), q + Vector((0, 0, z)))
                    box('metal', (T if dy else 0.12, 0.12 if dy else T, 0.1), p + n * 1.07 + Vector((0, 0, HB + 0.02)))   # canalón
    # mobiliario de los interiores, en las casillas donde el juego tiene sus muebles
    F = lambda i, x, y, dx=0.0, dy=0.0, r=0.0, z=0.0: has_ph(i) and put(i, wpos(x, y) + Vector((dx, dy, z)), r)
    F('drawer_cabinet', 1, 12, -0.55, 0, math.pi / 2)
    F('metal_office_desk', 3, 17); F('SchoolChair_01', 3, 17, 0, 0.85, math.pi); F('metal_tool_chest', 3, 17, 1.5, -0.3, 0.3)
    for x, y in ((8, 17), (9, 18), (7, 18)): F('worn_metal_rack', x, y, 0, -0.5)
    F('metal_office_desk', 9, 11, 0, 0.4); F('vintage_radio_transceiver', 9, 11, -0.3, 0.45, 0.2, 0.79); F('SchoolChair_01', 9, 11, 0.2, -0.45, 0.2)
    F('painted_wooden_bench', 30, 14, 0, 0.6); F('metal_tool_chest', 7, 8, 0, 0, 0.5); F('ammo_box', 29, 21, 0, 0, 0.8)
    flush('luces'); flush_smooth('camiones')
    # luces interiores del plano (despacho, archivo, calabozo...): se ven por las puertas y calientan las ventanas
    for m in re.finditer(r'\[([\d.]+),([\d.]+),0x([0-9a-f]{6}),([\d.]+)\]', re.search(r"ZONES\.base=.*?lights:\[(.*?)\]\],", src, re.S).group(1) + ']'):
        x, y, hx, k = float(m.group(1)), float(m.group(2)), m.group(3), float(m.group(4))
        q = Vector((x * T, -y * T, 0)); cyl('oscuro', 0.012, HB - 2.78, q + Vector((0, 0, (HB + 2.78) / 2)), seg=6); cyl('bombilla', 0.045, 0.1, q + Vector((0, 0, 2.73)), seg=10)
        lamp('POINT', 'interior', Vector((x * T, -y * T, 2.55)), tuple(int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)), 120 * k, shadow_soft_size=0.15)
    # torretas con foco: [x, y, hacia x, hacia y, ...]
    for sx, sy, tx, ty in ((18, 0, 7, 25), (35, 27, 13, 7)):   # apuntan lejos, casi horizontales, cruzando el patio
        p = wpos(sx, sy); place('torreta', p)
        head = p + Vector((0, 0, 7.25)); t = wpos(tx, ty, 1.2)
        s = lamp('SPOT', 'foco_torreta', head, (0.8, 0.9, 1.0), 90000, spot_size=math.radians(13), spot_blend=0.25, shadow_soft_size=0.12); aim(s, t)
        d = (t - head).normalized()
        cyl('oscuro', 0.26, 0.5, head - d * 0.15, rot=d.to_track_quat('Z', 'Y').to_matrix().to_4x4(), seg=16)
        cyl('foco', 0.22, 0.02, head + d * 0.11, rot=d.to_track_quat('Z', 'Y').to_matrix().to_4x4(), seg=16)
    flush('focos')
    for o in bpy.data.objects:
        if o.name.startswith('focos_foco'): o.visible_shadow = False
    s = lamp('SUN', 'luna', (0, 0, 30), (0.55, 0.7, 1.0), 0.035, angle=math.radians(2)); s.rotation_euler = (math.radians(52), 0, math.radians(140))

# posición de la cabeza de la farola escaneada respecto a su base
LAMP_HEAD = Vector((0, 0, 3.6))
if has_ph('street_lamp_01'):
    parts, dim = ph('street_lamp_01'); o, mw = parts[0]
    top = [mw @ v.co for v in o.data.vertices]; zmax = max(v.z for v in top); hi = [v for v in top if v.z > zmax - 0.45]
    far = max(hi, key=lambda v: v.x * v.x + v.y * v.y); zs = [v.z for v in hi if (v - far).length < 0.3]
    LAMP_HEAD = Vector((far.x * 0.8, far.y * 0.8, min(zs))); print('FAROLA', tuple(round(v, 2) for v in LAMP_HEAD), tuple(round(v, 2) for v in dim), flush=True)

def atmosphere():
    w = bpy.data.worlds.new('noche'); w.use_nodes = True; scene.world = w
    bg = w.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (0.006, 0.012, 0.03, 1); bg.inputs['Strength'].default_value = 0.35
    # niebla: un volumen que cubre la base
    bpy.ops.mesh.primitive_cube_add(size=1, location=(COLS * T / 2, -ROWS * T / 2, 11)); f = bpy.context.object; f.name = 'niebla'; f.scale = (COLS * T + 60, ROWS * T + 60, 24)
    m = bpy.data.materials.new('niebla'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); v = nt.nodes.new('ShaderNodeVolumeScatter'); v.inputs['Density'].default_value = float(os.environ.get('LH_FOG', '0.011')); v.inputs['Anisotropy'].default_value = 0.55
    nt.links.new(v.outputs[0], out.inputs['Volume']); f.data.materials.append(m)

def camera(name, pos, target, lens):
    d = bpy.data.cameras.new(name); d.lens = lens; d.clip_end = 600; o = bpy.data.objects.new('cam_' + name, d); col.objects.link(o); o.location = pos; aim(o, target); return o

import time; T0 = time.time()
build_materials(); build_world(); build_props()
if GLB:
    import json
    for img in bpy.data.images:
        if img.size[0] > 512: img.scale(512, 512)
    L_ = []
    for o in LIGHTS:
        d = o.rotation_euler.to_quaternion() @ Vector((0, 0, -1)); L_.append({'kind': o.data.type, 'name': o.name.split('.')[0], 'pos': [round(v, 3) for v in o.location], 'color': [round(v, 3) for v in o.data.color], 'power': o.data.energy, 'dir': [round(v, 3) for v in d]})
    json.dump({'map': MAP, 'T': T, 'HB': HB, 'HW': HW, 'lights': L_, 'lampHead': list(LAMP_HEAD)}, open(os.path.splitext(GLB)[0] + '.json', 'w'))
    for o in bpy.data.objects: o.select_set(o.type == 'MESH' and o.name in col.objects)
    kw = dict(filepath=GLB, export_format='GLB', use_selection=True, export_yup=True, export_cameras=False, export_lights=False, export_animations=False, export_image_format='JPEG')
    try: bpy.ops.export_scene.gltf(**kw, export_image_quality=72)
    except TypeError: bpy.ops.export_scene.gltf(**kw, export_jpeg_quality=72)
    tr = sum(len(o.data.polygons) for o in col.objects if o.type == 'MESH'); print('GLB', os.path.getsize(GLB) // 1024, 'KB', len([o for o in col.objects if o.type == 'MESH']), 'objetos', tr, 'caras', flush=True); sys.exit(0)
if not os.environ.get('LH_NORAIN'): rain()
atmosphere()
if os.environ.get('LH_NOFOG'): bpy.data.objects.remove(bpy.data.objects['niebla'])
if os.environ.get('LH_NOBEVEL'):
    for o in bpy.data.objects:
        for md in list(o.modifiers): o.modifiers.remove(md)
print('ESCENA', round(time.time() - T0, 1), 's', flush=True)
CAMERAS = {
    'patio': camera('patio', wpos(1.0, 5.2, 1.6), wpos(9.5, 6.0, 1.9), 22),
    'aerea': camera('aerea', Vector((-16, -ROWS * T - 14, 24)), wpos(17, 13, 0), 26),
    'torreta': camera('torreta', wpos(24.2, 12.5, 1.4), wpos(19.3, 2.0, 4.4), 20),
    'camion': camera('camion', wpos(8.7, 8.5, 1.25), wpos(5.6, 7.4, 1.45), 26),
    'oficinas': camera('oficinas', wpos(19.6, 6.2, 1.5), wpos(26.5, 7.6, 1.9), 24),
}

scene.render.engine = 'CYCLES'; cy = scene.cycles; cy.device = 'CPU'; cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.02
cy.use_denoising = True; cy.max_bounces = 5; cy.volume_bounces = 0; cy.volume_step_rate = 4; cy.sample_clamp_indirect = 6; cy.caustics_reflective = False; cy.caustics_refractive = False
scene.render.resolution_x, scene.render.resolution_y = RES; scene.render.threads_mode = 'AUTO'
try: scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'
except Exception as e: print('vista:', e)
scene.view_settings.exposure = float(os.environ.get('LH_EXPOSURE', '1.6'))
scene.render.image_settings.file_format = 'PNG'
if os.environ.get('LH_BLEND'):
    scene.camera = CAMERAS['patio']; bpy.ops.file.pack_all(); bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'base-tarsis.blend'), compress=True)
for name in CAMS:
    if name not in CAMERAS: continue
    scene.camera = CAMERAS[name]; scene.render.filepath = os.path.join(OUT, name + '.png'); t1 = time.time(); bpy.ops.render.render(write_still=True); print('RENDER', name, round(time.time() - t1, 1), 's', flush=True)
