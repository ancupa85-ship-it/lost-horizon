"""Inventario del Game Animation Sample (GASP) de Epic antes de pasar nada a Tarsis (tanda A de animación).

Se lanza en el proyecto del GASP (D:\\GASP), sin abrir ventana:
    D:\\ue_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe "D:\\GASP\\<proyecto>.uproject" -run=pythonscript -script="<repo>\\tools\\unreal\\gasp_inventario.py"
Escribe <repo>\\docs\\gasp_inventario.json (o en LH_GASP_SALIDA) con:
  - esqueletos y mallas con esqueleto (para el retarget a las personas de MakeHuman),
  - animation blueprints con su esqueleto, clase padre e interfaces (cómo leen la velocidad y la dirección),
  - bases de datos y esquemas de Pose Search (Motion Matching): cuántas animaciones lleva cada una,
  - Choosers, IK Rigs, IK Retargeters y Control Rigs,
  - las secuencias agrupadas por carpeta, con duración y si llevan root motion.
Con eso se decide qué migrar (solo lo que usen el ABP de Cuttlas y los estados de los guardias), no los 500+.
"""
import json
import os
import unreal

SALIDA = os.environ.get('LH_GASP_SALIDA') or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'docs', 'gasp_inventario.json')

reg = unreal.AssetRegistryHelpers.get_asset_registry()
todo = reg.get_assets_by_path('/Game', recursive=True)


def clase(a):
    return str(a.asset_class_path.asset_name)


def ruta(a):
    return str(a.package_name)


def prop(obj, nombre):
    try:
        return obj.get_editor_property(nombre)
    except Exception:
        return None


def etiqueta(a, nombre):
    # en 5.8 ParentClass está protegida: se lee de las etiquetas del registro de assets
    try:
        v = str(a.get_tag_value(nombre) or '')
        return v or None
    except Exception:
        return None


def nombre_obj(o):
    try:
        return o.get_path_name() if o else None
    except Exception:
        return str(o)


inv = {'esqueletos': [], 'mallas': [], 'abp': [], 'pose_search': [], 'choosers': [], 'ik': [], 'control_rig': [],
       'personajes': [], 'secuencias': {}, 'cuentas': {}}

for a in todo:
    c = clase(a)
    inv['cuentas'][c] = inv['cuentas'].get(c, 0) + 1
    p = ruta(a)
    if c == 'Skeleton':
        inv['esqueletos'].append(p)
    elif c == 'SkeletalMesh':
        m = a.get_asset()
        inv['mallas'].append({'ruta': p, 'esqueleto': nombre_obj(prop(m, 'skeleton')),
                              'physics_asset': nombre_obj(prop(m, 'physics_asset'))})
    elif c == 'AnimBlueprint':
        b = a.get_asset()
        gen = None
        try:
            gen = unreal.EditorAssetLibrary.load_blueprint_class(p)
        except Exception:
            pass
        inv['abp'].append({'ruta': p, 'esqueleto': nombre_obj(prop(b, 'target_skeleton')),
                           'padre': etiqueta(a, 'ParentClass'), 'clase': nombre_obj(gen),
                           'plantilla': bool(prop(b, 'is_template'))})
    elif c == 'Blueprint' and 'Character' in str(a.asset_name) and '/Blueprints/' in p:
        inv['personajes'].append({'ruta': p, 'padre': etiqueta(a, 'ParentClass'),
                                  'clase_nativa': etiqueta(a, 'NativeParentClass')})
    elif c in ('PoseSearchDatabase', 'PoseSearchSchema', 'PoseSearchNormalizationSet'):
        o = a.get_asset()
        d = {'ruta': p, 'tipo': c}
        if c == 'PoseSearchDatabase':
            d['esquema'] = nombre_obj(prop(o, 'schema'))
            try:
                d['animaciones'] = o.get_num_animation_assets()   # animation_assets no está expuesta en 5.8
            except Exception:
                d['animaciones'] = None
        inv['pose_search'].append(d)
    elif c.startswith('Chooser'):
        inv['choosers'].append({'ruta': p, 'tipo': c})
    elif c in ('IKRigDefinition', 'IKRetargeter'):
        inv['ik'].append({'ruta': p, 'tipo': c})
    elif c in ('ControlRigBlueprint', 'RigVMBlueprint') or 'ControlRig' in c:
        inv['control_rig'].append({'ruta': p, 'tipo': c})
    elif c == 'AnimSequence':
        s = a.get_asset()
        carpeta = str(a.package_path)
        dur = None
        try:
            dur = round(unreal.AnimationLibrary.get_sequence_length(s), 3)
        except Exception:
            pass
        inv['secuencias'].setdefault(carpeta, []).append({
            'nombre': str(a.asset_name), 'dur': dur, 'root_motion': bool(prop(s, 'enable_root_motion')),
            'esqueleto': nombre_obj(prop(s, 'skeleton'))})

inv['total_secuencias'] = sum(len(v) for v in inv['secuencias'].values())
os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
with open(SALIDA, 'w', encoding='utf-8') as f:
    json.dump(inv, f, ensure_ascii=False, indent=1, sort_keys=True)
unreal.log('GASP: inventario en %s (%d secuencias, %d ABP, %d de Pose Search)' % (
    SALIDA, inv['total_secuencias'], len(inv['abp']), len(inv['pose_search'])))
