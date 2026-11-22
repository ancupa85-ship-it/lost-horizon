"""Exporta de Lyra (sin ventana, sin guardar nada en Lyra) las animaciones de fusil de Manny que usa Tarsis, en FBX:
    UnrealEditor-Cmd.exe D:\\lyra\\LyraStarterGame\\LyraStarterGame.uproject -run=pythonscript -script=<este archivo> -nullrhi -unattended
Salen en D:\\LostHorizon\\descargas\\lyra_fbx\\: el idle de fusil a la cadera (los guardias de ronda), el idle apuntando
(alerta) y el culatazo (la detencion a golpes). Tarsis las importa sobre el esqueleto del maniqui UEFN (los nombres de
los huesos de Manny y del UEFN coinciden) con tools/unreal/armas.py."""
import os
import unreal

OUT = r'D:\LostHorizon\descargas\lyra_fbx'
ANIMS = ['/Game/Characters/Heroes/Mannequin/Animations/Locomotion/Rifle/MM_Rifle_Idle_Hipfire',
         '/Game/Characters/Heroes/Mannequin/Animations/Locomotion/Rifle/MM_Rifle_Idle_ADS',
         '/Game/Characters/Heroes/Mannequin/Animations/Actions/MM_Rifle_Melee']
os.makedirs(OUT, exist_ok=True)
for p in ANIMS:
    a = unreal.load_asset(p)
    if not a:
        unreal.log_error('[lyra_exportar] falta %s' % p)
        continue
    t = unreal.AssetExportTask()
    t.object = a
    t.filename = os.path.join(OUT, a.get_name() + '.fbx')
    t.automated = True
    t.prompt = False
    t.replace_identical = True
    t.exporter = unreal.AnimSequenceExporterFBX()
    opts = unreal.FbxExportOption()
    opts.set_editor_property('export_preview_mesh', False)
    t.options = opts
    ok = unreal.Exporter.run_asset_export_task(t)
    unreal.log('[lyra_exportar] %s -> %s %s' % (a.get_name(), t.filename, ok))
