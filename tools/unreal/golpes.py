"""Tanda P: importa los sonidos del cuerpo a cuerpo en capas y la voz de aviso a /Game/Tarsis/Sonidos.

Los genera tools/sonido/generar_golpes.py (golpe_grave/medio/chasquido/pared_N, esfuerzo_* y dolor_*) y
tools/sonido/generar_voces.py con TARSIS_FRASES=toma (voz_<guardia>_toma). Los usa ATarsisDirector::PlayImpact y el aviso
del culatazo en el duelo. Uso, en el editor: py golpes.py  (luego reabrir el editor antes de probar).
"""
import glob, os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
SON = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'assets', 'unreal', 'sonidos')
PATRONES = ['golpe_grave_*.wav', 'golpe_medio_*.wav', 'golpe_chasquido_*.wav', 'golpe_pared_*.wav',
            'esfuerzo_cuttlas_*.wav', 'esfuerzo_guardia_*.wav', 'dolor_cuttlas_*.wav', 'dolor_guardia_*.wav', 'voz_*_toma.wav']

tareas = []
for pat in PATRONES:
    for f in sorted(glob.glob(os.path.join(SON, pat))):
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', f)
        t.set_editor_property('destination_path', '/Game/Tarsis/Sonidos')
        t.set_editor_property('automated', True)
        t.set_editor_property('replace_existing', True)
        t.set_editor_property('save', True)
        tareas.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tareas)
unreal.log('[Tarsis] golpes: %d sonidos importados' % len(tareas))
print('importados', len(tareas))
