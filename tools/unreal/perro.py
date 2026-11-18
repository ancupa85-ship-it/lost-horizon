"""Importa el perro del hangar (assets/unreal/perro.glb, de tools/blender/perro_unreal.py) en /Game/Tarsis/Perro/<huella>:
una malla con esqueleto de 16 huesos y las animaciones quieto, andar, sentarse y sentado. El director lo busca solo en
esa carpeta (TarsisPerro.cpp: SpawnDog), así que no hay que tocar el nivel. Python del editor."""
import os, hashlib
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
GLB = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'assets', 'unreal', 'perro.glb')
DEST = '/Game/Tarsis/Perro'
ar = unreal.AssetRegistryHelpers.get_asset_registry()
eal = unreal.EditorAssetLibrary

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))

def clases(ruta):
    out = {}
    for a in ar.get_assets_by_path(ruta, recursive=True):
        out.setdefault(str(a.asset_class_path.asset_name), []).append(str(a.asset_name))
    return out

def importar(forzar=False):
    if not os.path.exists(GLB):
        log('AVISO: falta', GLB); return None
    ruta = DEST + '/v' + hashlib.md5(open(GLB, 'rb').read()).hexdigest()[:6]
    if not forzar and clases(ruta).get('SkeletalMesh'):
        log('perro: ya importado en', ruta, clases(ruta)); return ruta
    if eal.does_directory_exist(DEST):
        eal.delete_directory(DEST)     # una sola versión: el director coge la primera malla que encuentra
    pipe = unreal.InterchangeGenericAssetsPipeline()
    pipe.get_editor_property('mesh_pipeline').set_editor_property('combine_skeletal_meshes_behavior', unreal.InterchangeCombineSkeletalMeshesBehavior.BY_SKELETON)
    params = unreal.ImportAssetParameters()
    params.set_editor_property('is_automated', True)
    params.set_editor_property('replace_existing', True)
    ov = params.get_editor_property('override_pipelines')
    ov.append(unreal.SoftObjectPath(pipe.get_path_name()))
    params.set_editor_property('override_pipelines', ov)
    res = unreal.InterchangeManager.get_interchange_manager_scripted().import_asset(ruta, unreal.InterchangeManager.create_source_data(GLB), params)
    for a in ar.get_assets_by_path(ruta, recursive=True):
        o = a.get_asset()
        if o:
            eal.save_loaded_asset(o, False)
    c = clases(ruta)
    log('perro importado en', ruta, c)
    faltan = [n for n in ('quieto', 'andar', 'sentarse', 'sentado') if not any(x.lower().endswith(n) for x in c.get('AnimSequence', []))]
    if not c.get('SkeletalMesh') or faltan:
        log('AVISO: perro incompleto. Malla:', c.get('SkeletalMesh'), 'faltan animaciones:', faltan)
    return ruta

if __name__ == '__main__':
    importar()
