"""Animaciones de verdad para las personas: las del maniquí de la plantilla de UE5, retargeteadas a cada esqueleto.

Las del .glb del juego web son ciclos procedurales (solo se mueven los muslos y las pantorrillas; brazos abiertos y
tronco quieto) y los guardias parecían maniquíes flotando. Aquí, sin descargar nada, se pasan MM_Idle,
MF_Unarmed_Walk_Fwd y MF_Unarmed_Jog_Fwd (/Game/Characters/Mannequins, malla SKM_Manny_Simple) a cada esqueleto de /Game/Tarsis/Personas:

  1. IK Rig del maniquí (IK_TarsisManny) y uno por persona (IK_<persona>), con la definición de cadenas automática
     (los esqueletos de MakeHuman usan nombres al estilo de Unreal: pelvis, spine_01, thigh_l...).
  2. IK Retargeter por persona (RTG_<persona>): ops por defecto, cadenas por nombre (FUZZY) y la pose de retarget del
     destino alineada con la del maniquí (auto_align_all_bones), que resuelve la diferencia T-pose / A-pose.
  3. Copia retargeteada de las tres animaciones en /Game/Tarsis/Anims/<persona>_v<N> (<anim>_<persona>), con root
     motion activo y raíz bloqueada en su primer fotograma: el desplazamiento lo pone la cápsula, la animación anda en
     el sitio.
  4. Se mide la velocidad real de andar y trotar (avance del hueso raíz / duración) y se rehace la mezcla
     BS_mover_<persona>: idle en 0, walk y jog en su velocidad. El guardia recibe WalkAnimSpeed y RunAnimSpeed.

Uso (guardias.py lo llama desde cuerpo()):
    import animaciones
    a = animaciones.preparar('moya', persona)   # persona = personas.cargar('moya')
    # {'idle', 'walk', 'run', 'blend', 'walk_speed', 'run_speed'} o None si falta algo (se quedan las del .glb)
Volver a generarlo todo: LH_REANIM=1 o preparar(..., forzar=True). Cambiar VERSION también obliga a rehacerlo.
"""
import os
import unreal

DEST = '/Game/Tarsis/Anims'
VERSION = 1
FUENTE_MALLA = 'SKM_Manny_Simple'
FUENTE = {'idle': 'MM_Idle', 'walk': 'MF_Unarmed_Walk_Fwd', 'run': 'MF_Unarmed_Jog_Fwd'}

ar = unreal.AssetRegistryHelpers.get_asset_registry()
eal = unreal.EditorAssetLibrary
AL = unreal.AnimationLibrary

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))

def _buscar(nombre, clase):
    """Ruta del asset de la plantilla por nombre (en /Game/Characters), para no depender de las subcarpetas."""
    for a in ar.get_assets_by_path('/Game/Characters', recursive=True):
        if str(a.asset_name) == nombre and str(a.asset_class_path.asset_name) == clase:
            return a
    return None

def _cargar(ruta):
    return unreal.load_object(None, ruta + '.' + ruta.split('/')[-1]) if eal.does_asset_exist(ruta) else None

def _guardar(*assets):
    for a in assets:
        if a:
            eal.save_loaded_asset(a, False)

def _ik_rig(carpeta, nombre, malla, forzar):
    ruta = carpeta + '/' + nombre
    rig = None if forzar else _cargar(ruta)
    if rig:
        return rig
    if eal.does_asset_exist(ruta):
        eal.delete_asset(ruta)
    rig = unreal.IKRigDefinitionFactory.create_new_ik_rig_asset(carpeta, nombre)
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(malla)
    if not c.apply_auto_generated_retarget_definition():
        log('AVISO: sin cadenas automáticas en', nombre)
    # raíz del retarget en la pelvis (la definición automática ya suele ponerla, por si acaso)
    try:
        c.set_retarget_root('pelvis')
    except Exception:
        pass
    _guardar(rig)
    return rig

def _retargeter(carpeta, nombre, rig_src, rig_dst, malla_src, malla_dst, forzar):
    ruta = carpeta + '/' + nombre
    rtg = None if forzar else _cargar(ruta)
    if rtg:
        return rtg
    if eal.does_asset_exist(ruta):
        eal.delete_asset(ruta)
    rtg = unreal.AssetToolsHelpers.get_asset_tools().create_asset(nombre, carpeta, unreal.IKRetargeter, unreal.IKRetargetFactory())
    rc = unreal.IKRetargeterController.get_controller(rtg)
    S, T = unreal.RetargetSourceOrTarget.SOURCE, unreal.RetargetSourceOrTarget.TARGET
    rc.set_ik_rig(S, rig_src)
    rc.set_ik_rig(T, rig_dst)
    rc.add_default_ops()
    rc.assign_ik_rig_to_all_ops(S, rig_src)
    rc.assign_ik_rig_to_all_ops(T, rig_dst)
    rc.set_preview_mesh(S, malla_src)
    rc.set_preview_mesh(T, malla_dst)
    rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    # T-pose del .glb frente a la A-pose del maniquí: se gira la pose de retarget del destino hasta la del origen
    rc.auto_align_all_bones(T, unreal.RetargetAutoAlignMethod.CHAIN_TO_CHAIN)
    _guardar(rtg)
    return rtg

def _hueso_raiz(anim):
    for n in ('Root', 'root'):
        try:
            if AL.get_bone_pose_for_time(anim, n, 0.0, False) is not None and n in [str(b) for b in AL.get_animation_track_names(anim)]:
                return n
        except Exception:
            pass
    return 'Root'

def velocidad(anim):
    """cm/s que avanza la animación (hueso raíz; si no se mueve, la pelvis), en el plano del suelo."""
    d = AL.get_sequence_length(anim)
    if d <= 0:
        return 0.0
    for hueso in (_hueso_raiz(anim), 'pelvis'):
        try:
            a = AL.get_bone_pose_for_time(anim, hueso, 0.0, False).translation
            b = AL.get_bone_pose_for_time(anim, hueso, d, False).translation
        except Exception:
            continue
        v = ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5 / d
        if v > 5.0:
            return v
    return 0.0

def _mezcla(carpeta, nombre, malla, muestras, maximo):
    # si ya existe se rehace en el sitio: los guardias del nivel la referencian y borrarla dejaría create_asset sin hueco
    bs = _cargar(carpeta + '/' + nombre)
    if not bs:
        f = unreal.BlendSpaceFactory1D()
        f.set_editor_property('target_skeleton', malla.get_editor_property('skeleton'))
        bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(nombre, carpeta, unreal.BlendSpace1D, f)
    params = bs.get_editor_property('blend_parameters')
    p0 = params[0]
    p0.set_editor_property('display_name', 'Speed')
    p0.set_editor_property('min', 0.0)
    p0.set_editor_property('max', maximo)
    p0.set_editor_property('grid_num', 4)
    params[0] = p0
    bs.set_editor_property('blend_parameters', params)
    lista = []
    for anim, v in muestras:
        m = unreal.BlendSample()
        m.set_editor_property('animation', anim)
        m.set_editor_property('sample_value', unreal.Vector(v, 0.0, 0.0))
        lista.append(m)
    bs.set_editor_property('sample_data', lista)
    reconstruir(bs)
    _guardar(bs)
    return bs

def reconstruir(bs):
    """Segmentos de ejecución de la mezcla. set_editor_property('sample_data') NO los calcula (el motor solo llama a
    ResampleData desde el editor de mezclas): sin ellos la mezcla no avanza en el juego y el guardia se desliza con
    una pose fija, que era el «flotan como maniquíes». Lo hace ATarsisGuard::RebuildBlendSpace (C++, solo editor)."""
    f = getattr(unreal.TarsisGuard, 'rebuild_blend_space', None) if hasattr(unreal, 'TarsisGuard') else None
    if not f:
        log('AVISO: falta ATarsisGuard::RebuildBlendSpace (recompila el C++); la mezcla', bs.get_name(), 'no se moverá')
        return False
    return f(bs)

def preparar(nombre, persona, forzar=False):
    forzar = forzar or bool(os.environ.get('LH_REANIM'))
    if not persona or not persona.get('malla'):
        return None
    malla = persona['malla']
    sm = _buscar(FUENTE_MALLA, 'SkeletalMesh')
    fuentes = {k: _buscar(v, 'AnimSequence') for k, v in FUENTE.items()}
    if not sm or not all(fuentes.values()):
        log('AVISO: faltan las animaciones del maniquí de la plantilla; se quedan las del .glb')
        return None
    malla_src = sm.get_asset()
    carpeta = '%s/%s_v%d' % (DEST, nombre, VERSION)
    nombres = {k: '%s_%s' % (v, nombre) for k, v in FUENTE.items()}
    hechas = {k: _cargar(carpeta + '/' + n) for k, n in nombres.items()}
    if forzar or not all(hechas.values()):
        rig_src = _ik_rig(DEST, 'IK_TarsisManny', malla_src, forzar)
        rig_dst = _ik_rig(carpeta, 'IK_' + nombre, malla, forzar)
        rtg = _retargeter(carpeta, 'RTG_' + nombre, rig_src, rig_dst, malla_src, malla, forzar)
        # sin borrar las anteriores (las usa la mezcla, que usan los guardias del nivel): se sobrescriben
        res = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            list(fuentes.values()), malla_src, malla, rtg, '', '', '', '_' + nombre, carpeta, False, False, True)
        log('retarget', nombre, '->', [str(a.asset_name) for a in res or []])
        hechas = {k: _cargar(carpeta + '/' + n) for k, n in nombres.items()}
        if not all(hechas.values()):
            log('AVISO: el retarget de', nombre, 'no dejó', [nombres[k] for k, v in hechas.items() if not v])
            return None
    for k, a in hechas.items():
        # En el sitio: la raíz se queda como en el primer fotograma de la propia animación (en el suelo, al origen).
        # No en la pose de referencia: en estos esqueletos el Root de reposo lleva la altura de la cadera (~83 cm) y
        # el retarget ya pone la pelvis a su altura respecto al suelo, así que los guardias flotaban esos 83 cm.
        lock = unreal.RootMotionRootLock.ANIM_FIRST_FRAME
        if (a.get_editor_property('enable_root_motion') != (k != 'idle') or not a.get_editor_property('force_root_lock')
                or a.get_editor_property('root_motion_root_lock') != lock):
            a.set_editor_property('enable_root_motion', k != 'idle')
            a.set_editor_property('root_motion_root_lock', lock)
            a.set_editor_property('force_root_lock', True)
            _guardar(a)
    # la velocidad se mide en la animación retargeteada: ya va escalada a la altura de la persona
    vw = velocidad(hechas['walk'])
    vr = velocidad(hechas['run'])
    if vw < 30.0:
        vw = 300.0 * (vr / 600.0 if vr > 30.0 else 1.0)
        log('AVISO: no se pudo medir la velocidad de andar de', nombre, '- uso', round(vw))
    if vr <= vw * 1.2:
        vr = vw * 2.0
    bs = _mezcla(carpeta, 'BS_mover_' + nombre, malla, ((hechas['idle'], 0.0), (hechas['walk'], vw), (hechas['run'], vr)), vr)
    log('animaciones', nombre, '- andar', round(vw), 'cm/s, trotar', round(vr), 'cm/s')
    return {'idle': hechas['idle'], 'walk': hechas['walk'], 'run': hechas['run'], 'blend': bs,
            'walk_speed': vw, 'run_speed': vr}

if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import personas
    for n in ('ibarra', 'moya', 'peris'):
        preparar(n, personas.cargar(n))
