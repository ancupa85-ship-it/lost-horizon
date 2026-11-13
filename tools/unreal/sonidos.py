"""Importa los sonidos de assets/unreal/sonidos/*.wav en /Game/Tarsis/Sonidos (Python del editor).

Los genera tools/sonido/generar_sonidos.py. viento y lluvia se marcan en bucle. Los usa ATarsisDirector
(pasos según el suelo, piedra, dardo, viento y lluvia) cargándolos por su ruta.
"""
import os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'assets', 'unreal', 'sonidos')
DEST = '/Game/Tarsis/Sonidos'
BUCLES = ('viento', 'lluvia')

def importar():
    tareas = []
    for f in sorted(os.listdir(CARPETA)):
        if not f.endswith('.wav'):
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', os.path.join(CARPETA, f))
        t.set_editor_property('destination_path', DEST)
        t.set_editor_property('automated', True)
        t.set_editor_property('replace_existing', True)
        t.set_editor_property('save', True)
        tareas.append(t)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tareas)
    for n in BUCLES:
        w = unreal.EditorAssetLibrary.load_asset(DEST + '/' + n)
        if w:
            w.set_editor_property('looping', True)
            unreal.EditorAssetLibrary.save_loaded_asset(w)
    unreal.log('[Tarsis] sonidos importados: %d' % len(tareas))

if __name__ == '__main__':
    importar()
