"""Tanda A, octava (solo investigar): animaciones del GASP utiles para que los guardias te detengan con un golpe o
tirandote al suelo. Se lanza en el editor del proyecto del GASP (D:\\GASP), que se cierra al acabar:
    UnrealEditor.exe D:\\GASP\\GameAnimationSample.uproject -ExecutePythonScript=<este archivo>
(sin ventana, con -run=pythonscript, el commandlet se queda esperando a la DDC de las bases de Pose Search)
Escribe D:\\LostHorizon\\gasp_captura_info.txt: por animacion, duracion, fotogramas, montaje y notifies; las parejas de
Pose Search Interaction (PSIA: atacante _A y victima _V); y lo que trae SandboxCharacter_Mover_Ragdoll."""
import unreal

L = []
try:
    unreal.AssetRegistryHelpers.get_asset_registry().wait_for_completion()
except Exception:
    pass
AR = unreal.AssetRegistryHelpers.get_asset_registry()


def w(s):
    L.append(s)


def assets(path):
    return sorted(AR.get_assets_by_path(path, recursive=True), key=lambda a: str(a.asset_name))


def notifies(seq):
    try:
        evs = unreal.AnimationLibrary.get_animation_notify_events(seq)
        return sorted({str(e.notify.get_class().get_name()) if e.notify else str(e.get_editor_property('notify_name')) for e in evs})
    except Exception as ex:
        return ['? %s' % ex]


def describir(a):
    o = a.get_asset()
    cls = o.get_class().get_name()
    n = str(a.asset_name)
    if isinstance(o, unreal.AnimMontage):
        try:
            seqs = [s.get_editor_property('anim_reference').get_name() for t in o.get_editor_property('slot_anim_tracks')
                    for s in t.get_editor_property('anim_track').get_editor_property('anim_segments')]
        except Exception:
            seqs = []
        slots = [str(t.get_editor_property('slot_name')) for t in o.get_editor_property('slot_anim_tracks')]
        w('  %-48s Montage %.2f s slots=%s anims=%s notifies=%s' % (n, o.get_play_length(), slots, seqs, notifies(o)))
    elif isinstance(o, unreal.AnimSequence):
        try:
            nf = unreal.AnimationLibrary.get_num_frames(o)
        except Exception:
            nf = '?'
        rm = o.get_editor_property('enable_root_motion')
        curvas = []
        try:
            curvas = [str(c) for c in unreal.AnimationLibrary.get_animation_curve_names(o, unreal.RawCurveTrackTypes.RCT_FLOAT)][:8]
        except Exception:
            pass
        w('  %-48s Seq %.2f s %s fot root_motion=%s notifies=%s curvas=%s' % (n, o.get_play_length(), nf, rm, notifies(o), curvas))
    elif cls == 'PoseSearchInteractionAsset':
        try:
            items = o.get_editor_property('items')
            partes = ['%s:%s' % (str(i.get_editor_property('role')), i.get_editor_property('animation').get_name() if i.get_editor_property('animation') else None) for i in items]
        except Exception as ex:
            partes = ['? %s' % ex]
        w('  %-48s PSIA roles=%s' % (n, partes))
    else:
        w('  %-48s %s' % (n, cls))


for carpeta in ('/Game/Characters/UEFN_Mannequin/Animations/Interactions/Takedowns',
                '/Game/Characters/UEFN_Mannequin/Animations/Interactions/Tackle',
                '/Game/Characters/UEFN_Mannequin/Animations/Interactions/Shoves',
                '/Game/Characters/UEFN_Mannequin/Animations/Ragdoll'):
    w('## %s' % carpeta)
    for a in assets(carpeta):
        try:
            describir(a)
        except Exception as ex:
            w('  %s ERROR %s' % (a.asset_name, ex))

# el peon con ragdoll: componentes y funciones (sin abrir los grafos)
w('## SandboxCharacter_Mover_Ragdoll')
bp = unreal.load_asset('/Game/Blueprints/SandboxCharacter_Mover_Ragdoll')
if bp:
    gen = bp.generated_class()
    w('  padre: %s' % unreal.BlueprintEditorLibrary.get_blueprint_for_class(gen) if False else '  clase: %s' % gen.get_name())
    try:
        sup = unreal.SubobjectDataSubsystem.get() if hasattr(unreal.SubobjectDataSubsystem, 'get') else unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        hs = sup.k2_gather_subobject_data_for_blueprint(bp)
        nombres = []
        for h in hs:
            d = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
            ob = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(d)
            if ob:
                nombres.append('%s(%s)' % (ob.get_name(), ob.get_class().get_name()))
        w('  componentes: %s' % nombres)
    except Exception as ex:
        w('  componentes: ? %s' % ex)
    try:
        cdo = unreal.get_default_object(gen)
        w('  padre de la clase: %s' % gen.get_super_class().get_name() if hasattr(gen, 'get_super_class') else '')
    except Exception:
        pass
for n in ('/Game/Blueprints/MovementModes/BP_MovementMode_Ragdoll', '/Game/Blueprints/AnimNotifies/BP_AnimNotify_TriggerRagdoll',
          '/Game/Characters/UEFN_Mannequin/Animations/Ragdoll/CHT_GetUpMontages', '/Game/Blueprints/Data/S_RagdollProperties'):
    o = unreal.load_asset(n)
    w('  %s: %s' % (n.split('/')[-1], o.get_class().get_name() if o else 'NO'))
# fisica: el physics asset del maniqui UEFN (hace falta para el ragdoll)
for a in assets('/Game/Characters/UEFN_Mannequin'):
    if str(a.asset_class_path.asset_name) == 'PhysicsAsset':
        w('  physics asset: %s' % a.package_name)
open(r'D:\LostHorizon\gasp_captura_info.txt', 'w', encoding='utf-8').write('\n'.join(L))

# con -ExecutePythonScript en el editor con ventana (sin ventana, el commandlet se queda esperando a la DDC de Pose Search)
unreal.SystemLibrary.quit_editor()
