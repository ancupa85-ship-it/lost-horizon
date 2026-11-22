"""Tanda B, primer paso: el fusil de los guardias (Python del editor de Tarsis).

1. M14 del paquete CC0 de Stein Games (descargas/stein_extraido/M14: SKM_M14.fbx y sus texturas de 2048) como malla
   estatica en /Game/Tarsis/Armas/M14, con un material propio (color, normal y rugosidad/metal/oclusion en R/G/B),
   texturas a 1024 como mucho y un socket «Muzzle» en la boca del canon.
2. Las animaciones de fusil de Lyra exportadas en FBX (tools/unreal/lyra_exportar.py: idle a la cadera, idle apuntando y
   culatazo) importadas sobre el esqueleto del maniqui UEFN (los huesos de Manny y del UEFN se llaman igual) en
   /Game/Tarsis/Armas/Anims, y el idle y el apuntado retargeteados a cada persona de guardia con su RTG_UEFN_<persona>
   (MM_Rifle_Idle_Hipfire_<persona>, MM_Rifle_Idle_ADS_<persona>): el guardia los pone de cintura para arriba sobre la
   locomocion del GASP (TarsisArmas.cpp).
3. Los disparos de 7,62 del paquete (exterior: cerca, media distancia y lejos; 4 de cada) en /Game/Tarsis/Sonidos como
   disparo_cerca_1..4, disparo_media_1..4 y disparo_lejos_1..4.
Tanda C (modos «golpes» y «piedra»):
4. Las reacciones a golpes de Lyra (MM_HitReact_*, exportadas con lyra_exportar.py) sobre el esqueleto UEFN, sin
   retarget: las pone el maniqui del GASP del guardia (TarsisFisica.cpp) y la persona las copia.
5. Una piedra de verdad para la Q: malla irregular de ~9 cm (una icosfera con ruido, hecha aqui como .obj) con el
   material de hormigon del nivel, en /Game/Tarsis/Atrezo/SM_Piedra.
Escribe D:\\LostHorizon\\armas_info.txt."""
import glob
import os
import unreal

BASE = r'D:\LostHorizon\descargas'
M14 = os.path.join(BASE, 'stein_extraido', 'M14')
FBX_ANIMS = os.path.join(BASE, 'lyra_fbx')
AUDIO = os.path.join(BASE, 'stein_extraido', 'audio')
DEST = '/Game/Tarsis/Armas'
UEFN_MESH = '/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin'
PERSONAS = ['centinela', 'ibarra', 'moya', 'peris', 'ramos', 'vega', 'roig', 'cuttlas']
L = []
tools = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary


def w(s):
    L.append(str(s))


def importar(fichero, destino, opciones=None, nombre=None):
    t = unreal.AssetImportTask()
    t.filename = fichero
    t.destination_path = destino
    if nombre:
        t.destination_name = nombre
    t.automated = True
    t.replace_existing = True
    t.save = True
    if opciones is not None:
        t.options = opciones
    tools.import_asset_tasks([t])
    return [unreal.load_asset(p) for p in t.get_editor_property('imported_object_paths')]


def material_m14(tex):
    """material propio: BaseColor, Normal, y R rugosidad / G metal / B oclusion"""
    ruta = DEST + '/M14/M_M14'
    if EAL.does_asset_exist(ruta):
        EAL.delete_asset(ruta)
    m = tools.create_asset('M_M14', DEST + '/M14', unreal.Material, unreal.MaterialFactoryNew())
    MEL = unreal.MaterialEditingLibrary
    def muestra(t, x, y, normal=False):
        n = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, x, y)
        n.set_editor_property('texture', t)
        if normal:
            n.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        return n
    c = muestra(tex['C'], -400, -200)
    nrm = muestra(tex['N'], -400, 50, True)
    rm = muestra(tex['RMAO'], -400, 300)
    MEL.connect_material_property(c, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(nrm, 'RGB', unreal.MaterialProperty.MP_NORMAL)
    MEL.connect_material_property(rm, 'R', unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(rm, 'G', unreal.MaterialProperty.MP_METALLIC)
    MEL.connect_material_property(rm, 'B', unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, False)
    return m


def fusil():
    tex = {}
    for k in ('C', 'N', 'RMAO'):
        o = importar(os.path.join(M14, 'T_M14_%s.png' % k), DEST + '/M14')
        t = [x for x in o if isinstance(x, unreal.Texture2D)][0]
        t.set_editor_property('max_texture_size', 1024)
        if k == 'N':
            t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
            t.set_editor_property('srgb', False)
        if k == 'RMAO':
            t.set_editor_property('srgb', False)
            t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        EAL.save_loaded_asset(t, False)
        tex[k] = t
    mat = material_m14(tex)
    # la malla: estatica (el fusil no se anima; va pegado a la mano del guardia)
    ui = unreal.FbxImportUI()
    ui.set_editor_property('import_mesh', True)
    ui.set_editor_property('import_as_skeletal', False)
    ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.set_editor_property('import_materials', False)
    ui.set_editor_property('import_textures', False)
    ui.set_editor_property('import_animations', False)
    ui.static_mesh_import_data.set_editor_property('combine_meshes', True)
    o = importar(os.path.join(M14, 'SKM_M14.fbx'), DEST + '/M14', ui, 'SM_M14')
    sm = [x for x in o if isinstance(x, unreal.StaticMesh)]
    w('M14 importado: %s' % [x.get_path_name() for x in o])
    if not sm:
        return None
    sm = sm[0]
    for i in range(sm.get_num_sections(0)):
        sm.set_material(i, mat)
    b = sm.get_bounds()
    ext, ori = b.box_extent, b.origin
    w('M14 caja: origen %s medio-tamano %s' % (ori, ext))
    # el canon va por el eje mas largo; la boca, en el extremo que señala unreal.M14_BOCA (+1 o -1; por defecto +1)
    ejes = [('x', ext.x), ('y', ext.y), ('z', ext.z)]
    eje = max(ejes, key=lambda e: e[1])[0]
    signo = float(getattr(unreal, '_m14_boca', 1.0))
    loc = unreal.Vector(ori.x, ori.y, ori.z)
    setattr(loc, eje, getattr(ori, eje) + signo * getattr(ext, eje))
    sock = unreal.StaticMeshSocket(sm)
    sock.set_editor_property('socket_name', 'Muzzle')
    sock.set_editor_property('relative_location', loc)
    try:
        sm.add_socket(sock)
    except Exception as ex:
        w('add_socket: %s' % ex)
    w('Muzzle en %s (eje %s, signo %+.0f); socket: %s' % (loc, eje, signo, sm.find_socket('Muzzle')))
    EAL.save_loaded_asset(sm, False)
    return sm


def animaciones():
    uefn = unreal.load_asset(UEFN_MESH)
    sk = uefn.skeleton
    hechas = {}
    for f in sorted(glob.glob(os.path.join(FBX_ANIMS, '*.fbx'))):
        nombre = os.path.splitext(os.path.basename(f))[0]
        ui = unreal.FbxImportUI()
        ui.set_editor_property('import_mesh', False)
        ui.set_editor_property('import_animations', True)
        ui.set_editor_property('import_materials', False)
        ui.set_editor_property('import_textures', False)
        ui.set_editor_property('skeleton', sk)
        ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
        ui.anim_sequence_import_data.set_editor_property('import_bone_tracks', True)
        o = importar(f, DEST + '/Anims', ui, nombre)
        a = [x for x in o if isinstance(x, unreal.AnimSequence)]
        w('%s -> %s' % (nombre, [x.get_path_name() for x in o]))
        if a:
            a[0].set_editor_property('enable_root_motion', False)
            EAL.save_loaded_asset(a[0], False)
            hechas[nombre] = a[0]
    # el idle y el apuntado, a cada persona con su retargeter (el culatazo lo hace el maniqui del GASP del guardia)
    for p in PERSONAS:
        rtg = unreal.load_asset('/Game/Tarsis/Anim/RTG_UEFN_%s' % p)
        if not rtg:
            w('sin RTG_UEFN_%s' % p)
            continue
        malla = None
        try:
            ctrl = unreal.IKRetargeterController.get_controller(rtg)
            malla = ctrl.get_preview_mesh(unreal.RetargetSourceOrTarget.TARGET)
        except Exception as ex:
            w('%s: malla de vista previa: %s' % (p, ex))
        if not malla:
            # la malla de la persona: /Game/Tarsis/Personas/<persona>_<huella>/<persona>
            for a in EAL.list_assets('/Game/Tarsis/Personas', recursive=True):
                n = a.split('/')[-1].split('.')[0]
                if n.lower() == p and isinstance(unreal.load_asset(a), unreal.SkeletalMesh):
                    malla = unreal.load_asset(a)
                    break
        if not malla:
            w('%s: sin malla de la persona' % p)
            continue
        fuentes = [hechas[n] for n in ('MM_Rifle_Idle_Hipfire', 'MM_Rifle_Idle_ADS') if n in hechas]
        for a in fuentes:
            dest = DEST + '/Anims/%s_%s' % (a.get_name(), p)
            if EAL.does_asset_exist(dest):
                EAL.delete_asset(dest)
        try:
            r = unreal.IKRetargetBatchOperation.duplicate_and_retarget([EAL.find_asset_data(x.get_path_name()) for x in fuentes], uefn, malla, rtg, '', '', '', '_' + p, DEST + '/Anims', False, False, True)
            for x in r:
                EAL.save_asset(str(x.package_name), False)
            w('%s: retarget %s' % (p, [str(x) for x in r]))
        except Exception as ex:
            w('%s: retarget fallo: %s' % (p, ex))


def golpes():
    uefn = unreal.load_asset(UEFN_MESH)
    sk = uefn.skeleton
    for f in sorted(glob.glob(os.path.join(FBX_ANIMS, 'MM_HitReact_*.fbx'))):
        nombre = os.path.splitext(os.path.basename(f))[0]
        ui = unreal.FbxImportUI()
        ui.set_editor_property('import_mesh', False)
        ui.set_editor_property('import_animations', True)
        ui.set_editor_property('import_materials', False)
        ui.set_editor_property('import_textures', False)
        ui.set_editor_property('skeleton', sk)
        ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
        ui.anim_sequence_import_data.set_editor_property('import_bone_tracks', True)
        o = importar(f, DEST + '/Anims', ui, nombre)
        a = [x for x in o if isinstance(x, unreal.AnimSequence)]
        if a:
            a[0].set_editor_property('enable_root_motion', False)
            EAL.save_loaded_asset(a[0], False)
            w('%s -> %s (%.2f s)' % (nombre, a[0].get_path_name(), a[0].get_play_length()))
        else:
            w('%s: no se importo (%s)' % (nombre, o))


def piedra():
    # icosfera subdividida dos veces, deformada con ruido suave y aplastada: un canto rodado de unos 9 x 7 x 6 cm
    import math, random
    random.seed(7)
    t = (1.0 + 5 ** 0.5) / 2.0
    vs = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
          (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    fs = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
          (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    vs = [tuple(c / math.sqrt(sum(x * x for x in v)) for c in v) for v in vs]
    for _ in range(2):
        cache = {}
        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = [(vs[a][i] + vs[b][i]) / 2 for i in range(3)]
                n = math.sqrt(sum(x * x for x in m))
                vs.append(tuple(x / n for x in m))
                cache[k] = len(vs) - 1
            return cache[k]
        nf = []
        for a, b, c in fs:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        fs = nf
    bultos = [(tuple(random.uniform(-1, 1) for _ in range(3)), random.uniform(-0.18, 0.18)) for _ in range(9)]
    pv = []
    for v in vs:
        r = 1.0
        for d, h in bultos:
            n = math.sqrt(sum(x * x for x in d))
            dot = sum(v[i] * d[i] / n for i in range(3))
            r += h * max(0.0, dot) ** 3
        pv.append((v[0] * r * 4.6, v[1] * r * 3.6, v[2] * r * 2.9))
    ruta = os.path.join(BASE, 'piedra.obj')
    with open(ruta, 'w') as f:
        for p in pv:
            f.write('v %.4f %.4f %.4f\n' % p)
        for p, v in zip(pv, vs):
            u = 0.5 + math.atan2(v[1], v[0]) / (2 * math.pi)
            f.write('vt %.4f %.4f\n' % (u, 0.5 + math.asin(max(-1, min(1, v[2]))) / math.pi))
        for a, b, c in fs:
            f.write('f %d/%d %d/%d %d/%d\n' % (a + 1, a + 1, b + 1, b + 1, c + 1, c + 1))
    ui = unreal.FbxImportUI()
    ui.set_editor_property('import_mesh', True)
    ui.set_editor_property('import_animations', False)
    ui.set_editor_property('import_materials', False)
    ui.set_editor_property('import_textures', False)
    ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_STATIC_MESH)
    ui.static_mesh_import_data.set_editor_property('combine_meshes', True)
    ui.static_mesh_import_data.set_editor_property('auto_generate_collision', False)
    o = importar(ruta, '/Game/Tarsis/Atrezo', ui, 'SM_Piedra')
    sm = [x for x in o if isinstance(x, unreal.StaticMesh)]
    if not sm:
        w('piedra: no se importo (%s)' % o)
        return
    sm = sm[0]
    mat = unreal.load_asset('/Game/Tarsis/Materiales/MI_hormigon')
    if mat:
        sm.set_material(0, mat)
    EAL.save_loaded_asset(sm, False)
    b = sm.get_bounds()
    w('piedra: %s, %d vertices, medio tamano %s, material %s' % (sm.get_path_name(), len(pv), b.box_extent, mat.get_name() if mat else None))


def sonidos():
    for tipo, clave in (('Close', 'cerca'), ('Med', 'media'), ('Far', 'lejos')):
        for i in range(1, 5):
            f = os.path.join(AUDIO, '762_Ext_%s-%03d.ogg' % (tipo, i))
            o = importar(f, '/Game/Tarsis/Sonidos', None, 'disparo_%s_%d' % (clave, i))
            w('%s -> %s' % (os.path.basename(f), [x.get_path_name() for x in o]))


MODO = getattr(unreal, '_armas_modo', 'todo')
if MODO in ('todo', 'fusil'):
    fusil()
if MODO in ('todo', 'anims'):
    animaciones()
if MODO in ('todo', 'sonidos'):
    sonidos()
if MODO in ('todo', 'golpes'):
    golpes()
if MODO in ('todo', 'piedra'):
    piedra()
open(r'D:\LostHorizon\armas_info.txt', 'w', encoding='utf-8').write('\n'.join(L))
