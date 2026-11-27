"""Tanda P: las piezas propias del cuerpo a cuerpo, de Unreal a Blender y vuelta.

builtins._cqc_paso = 'exportar': saca a FBX (D:\\LostHorizon\\descargas\\cqc_base) las animaciones de base que rehace
    tools/blender/cqc_anims.py: los punetazos MM_Attack_01/02 y la pareja de empujon F del GASP (A y V).
builtins._cqc_paso = 'importar': importa las piezas de D:\\LostHorizon\\descargas\\cqc_tarsis (MM_Tarsis_*.fbx) en
    /Game/Tarsis/Armas/Anims/CQC sobre el esqueleto del maniqui UEFN, sin root motion, y apunta el director del nivel a
    ellas (MeleeStrikeAnimPath y sus segundos, HeroPunchAnimPaths, HeroCounterAnimPath, GrabGuardAnimPath...). Guarda.
Despues: reabrir el editor antes de probar.
"""
import builtins, os
import unreal

BASE = r'D:\LostHorizon\descargas\cqc_base'
PIEZAS = r'D:\LostHorizon\descargas\cqc_tarsis'
DEST = '/Game/Tarsis/Armas/Anims/CQC'
UEFN_MESH = '/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin'
EXPORTAR = ['/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_01',
            '/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_02',
            '/Game/Characters/UEFN_Mannequin/Animations/Interactions/Shoves/M_relaxed_ragdoll_shove_stand_F_A',
            '/Game/Characters/UEFN_Mannequin/Animations/Interactions/Shoves/M_relaxed_ragdoll_shove_stand_F_V']
# pieza -> (propiedad del director, segundos clave que se ponen)
SEGUNDOS = {'MM_Tarsis_Culatazo': {'melee_windup_at': 0.45, 'melee_contact_at': 0.52},
            'MM_Tarsis_Punetazo': {}, 'MM_Tarsis_Contra': {'hero_counter_contact': 0.22},
            'MM_Tarsis_AgarreGuardia': {'grab_hold_at': 0.40}, 'MM_Tarsis_AgarreCuttlas': {}}
out = []


def exportar():
    os.makedirs(BASE, exist_ok=True)
    for p in EXPORTAR:
        a = unreal.load_asset(p)
        if not a:
            out.append('falta %s' % p)
            continue
        t = unreal.AssetExportTask()
        t.object = a
        t.filename = os.path.join(BASE, a.get_name() + '.fbx')
        t.automated = True
        t.prompt = False
        t.replace_identical = True
        t.exporter = unreal.AnimSequenceExporterFBX()
        o = unreal.FbxExportOption()
        o.set_editor_property('export_preview_mesh', False)
        t.options = o
        out.append('%s -> %s' % (a.get_name(), unreal.Exporter.run_asset_export_task(t)))


def importar():
    sk = unreal.load_asset(UEFN_MESH).skeleton
    hechas = {}
    for f in sorted(os.listdir(PIEZAS)):
        if not f.lower().endswith('.fbx'):
            continue
        nombre = os.path.splitext(f)[0]
        ui = unreal.FbxImportUI()
        ui.set_editor_property('import_mesh', False)
        ui.set_editor_property('import_animations', True)
        ui.set_editor_property('import_materials', False)
        ui.set_editor_property('import_textures', False)
        ui.set_editor_property('skeleton', sk)
        ui.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_ANIMATION)
        ui.anim_sequence_import_data.set_editor_property('import_bone_tracks', True)
        t = unreal.AssetImportTask()
        t.filename = os.path.join(PIEZAS, f)
        t.destination_path = DEST
        t.destination_name = nombre
        t.automated = True
        t.replace_existing = True
        t.save = True
        t.options = ui
        try:
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
        except Exception as e:   # avisos de huesos que el UEFN no tiene (thigh_twist_02): la animacion se importa igual
            out.append('aviso %s: %s' % (nombre, str(e).splitlines()[0][:120]))
        a = unreal.load_asset('%s/%s' % (DEST, nombre))
        if isinstance(a, unreal.AnimSequence):
            a.set_editor_property('enable_root_motion', False)
            unreal.EditorAssetLibrary.save_loaded_asset(a, False)
            hechas[nombre] = '%s/%s.%s' % (DEST, nombre, nombre)
            out.append('%s %.2f s' % (nombre, a.get_play_length()))
        else:
            out.append('NO importada %s' % nombre)
    # el director del nivel, a las piezas
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    d = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector'))[0]
    d.modify()
    if 'MM_Tarsis_Culatazo' in hechas:
        d.set_editor_property('melee_strike_anim_path', hechas['MM_Tarsis_Culatazo'])
    if 'MM_Tarsis_Punetazo' in hechas:
        # el propio y, de segunda, el de Lyra (alternan)
        d.set_editor_property('hero_punch_anim_paths', [hechas['MM_Tarsis_Punetazo'], '/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_02.MM_Attack_02'])
        d.set_editor_property('hero_punch_contact', [0.20, 0.40])
    if 'MM_Tarsis_Contra' in hechas:
        d.set_editor_property('hero_counter_anim_path', hechas['MM_Tarsis_Contra'])
    if 'MM_Tarsis_AgarreGuardia' in hechas and 'MM_Tarsis_AgarreCuttlas' in hechas:
        d.set_editor_property('grab_guard_anim_path', hechas['MM_Tarsis_AgarreGuardia'])
        d.set_editor_property('grab_hero_anim_path', hechas['MM_Tarsis_AgarreCuttlas'])
    for n, kv in SEGUNDOS.items():
        if n in hechas:
            for k, v in kv.items():
                d.set_editor_property(k, v)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    out.append('director apuntado a %d piezas' % len(hechas))


paso = getattr(builtins, '_cqc_paso', 'importar')
exportar() if paso == 'exportar' else importar()
print('\n'.join(out))
