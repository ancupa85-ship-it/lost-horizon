"""Importa las personas del juego web (assets/unreal/personas/<nombre>.glb) como mallas con esqueleto y animaciones.

Los .glb salen del visor realista (window.LH_ESC.people en tarsis-escenario.html): personas de MakeHuman con
esqueleto de 53 huesos con nombres al estilo de Unreal (Root, pelvis, spine_01... ball_r) y animaciones
idle, walk, down y aim (Cuttlas: idle, stand, walk y sneak). Se importan en /Game/Tarsis/Personas/<nombre>.

Uso desde otro script del editor:
    import personas
    p = personas.cargar('ibarra')   # {'malla': SkeletalMesh, 'idle': AnimSequence, 'walk': ..., 'aim': ..., 'down': ...}
"""
import os
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
    ruta = DEST + '/' + nombre
    if not forzar and _assets(ruta).get('SkeletalMesh'):
        return ruta
    if not os.path.exists(glb):
        log('AVISO: falta', glb)
        return None
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', glb)
    task.set_editor_property('destination_path', ruta)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    log('persona importada', nombre, len(list(task.get_editor_property('imported_object_paths') or [])), 'assets')
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
    log('persona', nombre, '- animaciones:', sorted(k for k in res if k != 'malla'),
        '- todas:', [str(a.asset_name) for a in clases.get('AnimSequence') or []])
    return res

if __name__ == '__main__':
    for f in sorted(os.listdir(CARPETA)):
        if f.endswith('.glb'):
            cargar(f[:-4], forzar=bool(os.environ.get('LH_REIMPORT')))
