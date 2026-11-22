"""Inventario de solo lectura de Lyra (tanda B: armas y apuntado; culatazo), sin ventana:
    UnrealEditor-Cmd.exe D:\\lyra\\LyraStarterGame\\Lyra.uproject -run=pythonscript -script=<este archivo> -nullrhi -unattended
No guarda nada en el proyecto. Escribe D:\\LostHorizon\\lyra_inventario.json: las animaciones de Manny con arma (acciones,
apuntado, locomocion de fusil y pistola) con duracion, fotogramas, esqueleto, root motion y avisos de los montajes; las
mallas de armas con sus sockets y esqueleto; y los sockets de la mano de Manny."""
import json
import unreal

AR = unreal.AssetRegistryHelpers.get_asset_registry()
try:
    AR.wait_for_completion()
except Exception:
    pass
AL = unreal.AnimationLibrary
OUT = {'animaciones': [], 'montajes': [], 'aim_offsets': [], 'mallas_armas': [], 'manny': {}, 'errores': []}


def assets(path):
    return sorted(AR.get_assets_by_path(path, recursive=True), key=lambda a: str(a.package_name))


def interesa(nombre):
    n = nombre.lower()
    return any(k in n for k in ('rifle', 'pistol', 'shotgun', 'melee', 'hitreact', 'death', 'grenade', 'equip', 'reload', 'fire', 'ads', 'aim'))


for base in ('/Game/Characters/Heroes/Mannequin/Animations', '/Game/Weapons'):
    for a in assets(base):
        cls = str(a.asset_class_path.asset_name)
        name = str(a.asset_name)
        if cls not in ('AnimSequence', 'AnimMontage', 'AimOffsetBlendSpace', 'AimOffsetBlendSpace1D', 'BlendSpace'):
            continue
        if not interesa(name) and '/Weapons/' not in str(a.package_name):
            continue
        try:
            o = a.get_asset()
            d = {'ruta': str(a.package_name), 'clase': cls}
            if hasattr(o, 'get_play_length'):
                d['segundos'] = round(o.get_play_length(), 3)
            sk = o.get_editor_property('skeleton') if cls != 'AnimMontage' or True else None
            d['esqueleto'] = sk.get_path_name() if sk else None
            if cls == 'AnimSequence':
                try:
                    d['fotogramas'] = AL.get_num_frames(o)
                except Exception:
                    pass
                d['root_motion'] = o.get_editor_property('enable_root_motion')
                d['aditiva'] = str(o.get_editor_property('additive_anim_type'))
                OUT['animaciones'].append(d)
            elif cls == 'AnimMontage':
                d['avisos'] = [(str(e.notify_name), round(AL.get_anim_notify_event_trigger_time(e), 3)) for e in AL.get_animation_notify_events(o)]
                d['slots'] = [str(t.get_editor_property('slot_name')) for t in o.get_editor_property('slot_anim_tracks')]
                OUT['montajes'].append(d)
            else:
                OUT['aim_offsets'].append(d)
        except Exception as ex:
            OUT['errores'].append('%s: %s' % (a.package_name, ex))


def sockets(mesh):
    out = []
    try:
        for i in range(mesh.num_sockets()):
            s = mesh.get_socket_by_index(i)
            out.append({'nombre': str(s.socket_name), 'hueso': str(s.bone_name),
                        'pos': [round(v, 2) for v in (s.relative_location.x, s.relative_location.y, s.relative_location.z)],
                        'rot': [round(v, 2) for v in (s.relative_rotation.pitch, s.relative_rotation.yaw, s.relative_rotation.roll)]})
    except Exception as ex:
        out.append({'error': str(ex)})
    return out


for a in assets('/Game/Weapons'):
    if str(a.asset_class_path.asset_name) in ('SkeletalMesh', 'StaticMesh'):
        try:
            o = a.get_asset()
            d = {'ruta': str(a.package_name), 'clase': str(a.asset_class_path.asset_name)}
            if isinstance(o, unreal.SkeletalMesh):
                d['esqueleto'] = o.skeleton.get_path_name() if o.skeleton else None
                d['sockets'] = sockets(o)
                d['huesos'] = o.skeleton.get_editor_property('bone_tree') and len(o.skeleton.get_editor_property('bone_tree')) if o.skeleton else None
            else:
                d['sockets'] = [{'nombre': str(s.socket_name)} for s in o.get_editor_property('sockets')]
            b = o.get_bounds() if hasattr(o, 'get_bounds') else None
            if b:
                d['medidas_cm'] = [round(v * 2, 1) for v in (b.box_extent.x, b.box_extent.y, b.box_extent.z)]
            OUT['mallas_armas'].append(d)
        except Exception as ex:
            OUT['errores'].append('%s: %s' % (a.package_name, ex))

m = unreal.load_asset('/Game/Characters/Heroes/Mannequin/Meshes/SKM_Manny')
if m:
    OUT['manny'] = {'esqueleto': m.skeleton.get_path_name() if m.skeleton else None, 'sockets': sockets(m)}

with open(r'D:\LostHorizon\lyra_inventario.json', 'w', encoding='utf-8') as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1)
unreal.log('[lyra_inventario] %d animaciones, %d montajes, %d aim offsets, %d mallas' % (
    len(OUT['animaciones']), len(OUT['montajes']), len(OUT['aim_offsets']), len(OUT['mallas_armas'])))
