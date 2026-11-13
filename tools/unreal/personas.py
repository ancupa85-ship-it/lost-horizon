"""Importa las personas del juego web (assets/unreal/personas/<nombre>.glb) como mallas con esqueleto y animaciones.

Los .glb salen del visor realista (window.LH_ESC.people en tarsis-escenario.html): personas de MakeHuman con
esqueleto de 53 huesos con nombres al estilo de Unreal (Root, pelvis, spine_01... ball_r) y animaciones
idle, walk, down y aim (Cuttlas: idle, stand, walk y sneak). Se importan en /Game/Tarsis/Personas/<nombre>_<huella>.
La traslación del nodo del armazón (~0,83 m) está pasada al hueso Root, en reposo y en las animaciones: Interchange
la metía en la pose de referencia pero no en las animaciones, y los guardias salían hundidos hasta la cintura.

Uso desde otro script del editor:
    import personas
    p = personas.cargar('ibarra')   # {'malla': SkeletalMesh, 'idle': AnimSequence, 'walk': ..., 'aim': ..., 'down': ...}
"""
import os, hashlib
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CARPETA = os.path.join(ROOT, 'assets', 'unreal', 'personas')
DEST = '/Game/Tarsis/Personas'
ANIMS = ('idle', 'walk', 'aim', 'down', 'stand', 'sneak')

ar = unreal.AssetRegistryHelpers.get_asset_registry()

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))

def _assets(ruta):
    out = {}
    for a in ar.get_assets_by_path(ruta, recursive=True):
        out.setdefault(str(a.asset_class_path.asset_name), []).append(a)
    return out

def importar(nombre, forzar=False):
    glb = os.path.join(CARPETA, nombre + '.glb')
    if not os.path.exists(glb):
        log('AVISO: falta', glb)
        return None
    # cada versión del .glb va a su carpeta (<nombre>_<huella>): si cambia el archivo se importa de nuevo
    ruta = DEST + '/' + nombre + '_' + hashlib.md5(open(glb, 'rb').read()).hexdigest()[:6]
    if not forzar and _assets(ruta).get('SkeletalMesh'):
        return ruta
    eal = unreal.EditorAssetLibrary
    for d in [DEST + '/' + nombre, ruta]:
        if eal.does_directory_exist(d):
            eal.delete_directory(d)   # sin restos de una importación anterior (p. ej. con las mallas separadas)
    # Cada persona trae varias mallas con el mismo esqueleto (cuerpo, ojos, cejas, ropa, pelo, botas). Con
    # AssetImportTask, Interchange las importa como 7 SkeletalMesh sueltas; se fuerza una sola por esqueleto.
    pipe = unreal.InterchangeGenericAssetsPipeline()
    pipe.get_editor_property('mesh_pipeline').set_editor_property(
        'combine_skeletal_meshes_behavior', unreal.InterchangeCombineSkeletalMeshesBehavior.BY_SKELETON)
    params = unreal.ImportAssetParameters()
    params.set_editor_property('is_automated', True)
    params.set_editor_property('replace_existing', True)
    ov = params.get_editor_property('override_pipelines')
    ov.append(unreal.SoftObjectPath(pipe.get_path_name()))
    params.set_editor_property('override_pipelines', ov)
    mgr = unreal.InterchangeManager.get_interchange_manager_scripted()
    res = mgr.import_asset(ruta, unreal.InterchangeManager.create_source_data(glb), params)
    for p in res or []:
        a = eal.load_asset(str(p).split("'")[1] if "'" in str(p) else str(p))
        if a:
            eal.save_loaded_asset(a)
    log('persona importada', nombre, len(res or []), 'assets')
    return ruta

def cargar(nombre, forzar=False):
    ruta = importar(nombre, forzar)
    if not ruta:
        return None
    clases = _assets(ruta)
    sk = clases.get('SkeletalMesh') or []
    if not sk:
        log('AVISO: no se importó ninguna malla con esqueleto de', nombre, '- clases:', sorted(clases))
        return None
    if len(sk) > 1:
        log('AVISO:', nombre, 'trae', len(sk), 'mallas con esqueleto:', [str(a.asset_name) for a in sk], '- uso la primera')
    res = {'malla': sk[0].get_asset()}
    for a in clases.get('AnimSequence') or []:
        n = str(a.asset_name).lower()
        for k in ANIMS:
            # Interchange suele llamarlas <archivo>_<animación> o solo <animación>
            if n == k or n.endswith('_' + k) or n.endswith(k):
                res.setdefault(k, a.get_asset())
    if res.get('idle') and res.get('walk'):
        try:
            res['blend'] = mezcla(ruta, res['malla'], res['idle'], res['walk'])
        except Exception as e:
            log('AVISO: sin mezcla idle/walk para', nombre, repr(e))
    log('persona', nombre, '- animaciones:', sorted(k for k in res if k != 'malla'),
        '- todas:', [str(a.asset_name) for a in clases.get('AnimSequence') or []])
    return res

def mezcla(ruta, malla, idle, walk, andar=150.0):
    """BlendSpace1D «BS_mover» de quieto (0) a andar (andar cm/s, el WalkAnimSpeed del guardia), una por esqueleto."""
    nombre = ruta + '/BS_mover'
    eal = unreal.EditorAssetLibrary
    if eal.does_asset_exist(nombre):
        return eal.load_asset(nombre)
    f = unreal.BlendSpaceFactory1D()
    f.set_editor_property('target_skeleton', malla.get_editor_property('skeleton'))
    bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset('BS_mover', ruta, unreal.BlendSpace1D, f)
    params = bs.get_editor_property('blend_parameters')
    p0 = params[0]
    p0.set_editor_property('display_name', 'Speed')
    p0.set_editor_property('min', 0.0)
    p0.set_editor_property('max', andar * 3.0)
    p0.set_editor_property('grid_num', 3)
    params[0] = p0
    bs.set_editor_property('blend_parameters', params)
    muestras = []
    for anim, v in ((idle, 0.0), (walk, andar)):
        m = unreal.BlendSample()
        m.set_editor_property('animation', anim)
        m.set_editor_property('sample_value', unreal.Vector(v, 0.0, 0.0))
        muestras.append(m)
    bs.set_editor_property('sample_data', muestras)
    eal.save_loaded_asset(bs)
    log('mezcla creada', nombre)
    return bs

if __name__ == '__main__':
    for f in sorted(os.listdir(CARPETA)):
        if f.endswith('.glb'):
            cargar(f[:-4], forzar=bool(os.environ.get('LH_REIMPORT')))
