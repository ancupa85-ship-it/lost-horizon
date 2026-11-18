"""Importa los retratos del códec (assets/retratos/*.jpg y *.png) en /Game/Tarsis/Retratos (Python del editor).

El nombre del archivo es la clave del personaje: cuttlas, roig, control, fuente. El códec (ATarsisDirector::Portrait)
carga el que haya por su ruta; a quien no tiene retrato ilustrado, el HUD le dibuja el de puntos de la versión web.
Son texturas de interfaz: sin mipmaps y sin streaming, para que no salgan borrosas ni cuenten en el pool.
"""
import os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'assets', 'retratos')
DEST = '/Game/Tarsis/Retratos'

def importar():
    hechos = []
    for f in sorted(os.listdir(CARPETA)):
        nombre, ext = os.path.splitext(f)
        if ext.lower() not in ('.jpg', '.jpeg', '.png'):
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', os.path.join(CARPETA, f))
        t.set_editor_property('destination_path', DEST)
        t.set_editor_property('destination_name', nombre)
        t.set_editor_property('automated', True)
        t.set_editor_property('replace_existing', True)
        t.set_editor_property('save', False)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        tx = unreal.EditorAssetLibrary.load_asset(DEST + '/' + nombre)
        if not tx:
            unreal.log_warning('[Tarsis] retrato sin importar: ' + f)
            continue
        tx.modify()
        tx.set_editor_property('srgb', True)
        tx.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
        tx.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        tx.set_editor_property('never_stream', True)
        unreal.EditorAssetLibrary.save_loaded_asset(tx, False)
        hechos.append(nombre)
    unreal.log('[Tarsis] retratos importados: %s' % ', '.join(hechos))

if __name__ == '__main__':
    importar()
