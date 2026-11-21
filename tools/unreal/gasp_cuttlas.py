"""Tanda A, sexta parte: Cuttlas (el jugador) con el Animation Blueprint del Game Animation Sample en tercera persona.

En el editor abierto con el nivel Tarsis (py tools/unreal/gasp_cuttlas.py), o sin ventana con UnrealEditor-Cmd -run=pythonscript.
LH_GASP_CUTTLAS (o builtins._gasp_cuttlas) elige el modo:
  info    (por defecto) solo lee: la clase del peón del jugador (GameMode del nivel o el global, DefaultPawnClass), su
          padre, componentes, valores del CDO (malla, cámara, cápsula, CMC, acciones de entrada) y sus grafos; el
          PlayerController (dónde añade el IMC); y en SandboxCharacter_CMC lo que toca entrada, cámara y salto
          (SetupInput, SetupCamera, CanJumpInternal, eventos de teclas). Escribe D:\\LostHorizon\\gasp_cuttlas_info.txt.
  montar  crea /Game/Tarsis/Anim/BP_CuttlasGASP (ver montar()).
"""
import builtins
import importlib
import os
import re
import sys

import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grafos
importlib.reload(grafos)
from grafos import L, w, corta, nodos_de, titulo, sentencia, volcar_grafo, grafo

MODO = os.environ.get('LH_GASP_CUTTLAS', '') or getattr(builtins, '_gasp_cuttlas', '') or 'info'
SALIDA = os.environ.get('LH_GASP_CUTTLAS_SALIDA') or (r'D:\LostHorizon\gasp_cuttlas_%s.txt' % MODO)

BEL = unreal.BlueprintEditorLibrary
eal = unreal.EditorAssetLibrary
reg = unreal.AssetRegistryHelpers.get_asset_registry()
GASP_PJ = '/Game/Blueprints/SandboxCharacter_CMC'
MAPA = '/Game/Tarsis/Mapas/Tarsis'
CMC_PROPS = ('max_walk_speed', 'max_walk_speed_crouched', 'max_acceleration', 'braking_deceleration_walking',
             'ground_friction', 'braking_friction_factor', 'braking_friction', 'use_separate_braking_friction',
             'rotation_rate', 'orient_rotation_to_movement', 'use_controller_desired_rotation', 'jump_z_velocity',
             'air_control', 'braking_deceleration_falling', 'gravity_scale', 'max_step_height', 'walkable_floor_angle',
             'crouched_half_height', 'can_walk_off_ledges_when_crouching', 'perch_radius_threshold')
MALLA_PROPS = ('skeletal_mesh_asset', 'anim_class', 'animation_mode', 'relative_location', 'relative_rotation',
               'relative_scale3d', 'owner_no_see', 'only_owner_see', 'visible', 'hidden_in_game', 'cast_shadow')


def clase_bp(bp):
    try:
        return BEL.generated_class(bp)
    except Exception:
        return None


def cadena_padres(cls):
    r = []
    c = cls
    while c:
        r.append(c.get_path_name())
        try:
            c = unreal.SystemLibrary.get_super_class(c) if hasattr(unreal.SystemLibrary, 'get_super_class') else None
        except Exception:
            c = None
        if len(r) > 8:
            break
    return r


def props(obj, lista):
    r = []
    for p in lista:
        try:
            v = obj.get_editor_property(p)
            if hasattr(v, 'get_path_name'):
                v = v.get_path_name()
            r.append('%s=%s' % (p, corta(v, 120)))
        except Exception:
            pass
    return ', '.join(r)


def componentes(bp):
    r = []
    try:
        sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        lib = unreal.SubobjectDataBlueprintFunctionLibrary
        for h in sub.k2_gather_subobject_data_for_blueprint(bp):
            o = lib.get_object(lib.get_data(h))
            if o and not o.get_name().startswith('Default__'):
                padre = ''
                try:
                    ap = o.get_attach_parent()
                    padre = ' <- %s' % ap.get_name() if ap else ''
                    if o.get_attach_socket_name() and str(o.get_attach_socket_name()) != 'None':
                        padre += ':%s' % o.get_attach_socket_name()
                except Exception:
                    pass
                r.append('%s (%s)%s' % (o.get_name().replace('_GEN_VARIABLE', ''), o.get_class().get_name(), padre))
    except Exception as e:
        r.append('(no se pudieron listar: %s)' % e)
    return r


def volcar_todo(bp, maximo=40, solo=None):
    for g in BEL.list_graphs(bp):
        if solo and g.get_name() not in solo:
            continue
        volcar_grafo(g, maximo)


def bp_de_clase(cls):
    """Blueprint de una clase generada (o None si es C++): /Game/X/BP_Y.BP_Y_C -> /Game/X/BP_Y."""
    p = cls.get_path_name() if cls else ''
    if not p.startswith('/Game/'):
        return None
    return unreal.load_asset(p.split('.')[0])


def info():
    w('Cuttlas con el GASP: lo que hay ahora (gasp_cuttlas.py, modo info)')
    w('')
    mundo = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ws = mundo.get_world_settings()
    gm_nivel = ws.get_editor_property('default_game_mode')
    w('=== 1. GameMode')
    w('  del nivel (WorldSettings.DefaultGameMode): %s' % (gm_nivel.get_path_name() if gm_nivel else 'ninguno (usa el global)'))
    gm_cls = gm_nivel or unreal.load_class(None, '/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode.BP_FirstPersonGameMode_C')
    w('  en uso: %s' % gm_cls.get_path_name())
    gm = unreal.get_default_object(gm_cls)
    for p in ('default_pawn_class', 'player_controller_class', 'hud_class', 'player_state_class', 'game_state_class'):
        try:
            v = gm.get_editor_property(p)
            w('  %s = %s' % (p, v.get_path_name() if v else None))
        except Exception as e:
            w('  %s: %s' % (p, e))
    pawn_cls = gm.get_editor_property('default_pawn_class')
    pc_cls = gm.get_editor_property('player_controller_class')

    w('')
    w('=== 2. Peón del jugador: %s' % pawn_cls.get_path_name())
    pawn_bp = bp_de_clase(pawn_cls)
    if pawn_bp:
        try:
            w('  padre del BP: %s' % BEL.get_blueprint_parent_class(pawn_bp).get_path_name())
        except Exception:
            pass
        w('  componentes: %s' % '; '.join(componentes(pawn_bp)))
        try:
            w('  variables: %s' % ', '.join(str(v) for v in BEL.list_member_variable_names(pawn_bp) if not str(v).startswith('/Script/')))
        except Exception:
            pass
        w('  grafos: %s' % ', '.join(g.get_name() for g in BEL.list_graphs(pawn_bp)))
        volcar_todo(pawn_bp, 30)
    cdo = unreal.get_default_object(pawn_cls)
    for p in ('jump_action', 'move_action', 'look_action', 'mouse_look_action', 'use_controller_rotation_yaw',
              'use_controller_rotation_pitch', 'auto_possess_player'):
        try:
            v = cdo.get_editor_property(p)
            w('  CDO.%s = %s' % (p, v.get_path_name() if hasattr(v, 'get_path_name') else v))
        except Exception:
            pass
    w('  CDO.Mesh: %s' % props(cdo.get_editor_property('mesh'), MALLA_PROPS))
    for c in cdo.get_components_by_class(unreal.SkeletalMeshComponent):
        if c.get_name() != 'CharacterMesh0':
            ap = c.get_attach_parent()
            w('  CDO.%s <- %s: %s' % (c.get_name(), ap.get_name() if ap else None, props(c, MALLA_PROPS)))
    for c in cdo.get_components_by_class(unreal.CameraComponent):
        ap = c.get_attach_parent()
        w('  CDO.%s <- %s:%s: %s' % (c.get_name(), ap.get_name() if ap else None, c.get_attach_socket_name(),
                                      props(c, ('relative_location', 'relative_rotation', 'use_pawn_control_rotation', 'field_of_view'))))
    cap = cdo.get_editor_property('capsule_component')
    w('  CDO.Capsule: radio %.1f, media altura %.1f' % (cap.get_unscaled_capsule_radius(), cap.get_unscaled_capsule_half_height()))
    w('  CDO.CMC: %s' % props(cdo.get_editor_property('character_movement'), CMC_PROPS))

    w('')
    w('=== 3. PlayerController: %s' % pc_cls.get_path_name())
    pc_bp = bp_de_clase(pc_cls)
    if pc_bp:
        try:
            w('  padre: %s' % BEL.get_blueprint_parent_class(pc_bp).get_path_name())
        except Exception:
            pass
        volcar_todo(pc_bp, 30)
    pcdo = unreal.get_default_object(pc_cls)
    for p in ('default_mapping_contexts', 'mobile_excluded_contexts', 'default_mapping_context'):
        try:
            w('  CDO.%s = %s' % (p, corta(pcdo.get_editor_property(p), 400)))
        except Exception:
            pass

    w('')
    w('=== 4. SandboxCharacter_CMC: entrada, cámara, salto')
    pj = unreal.load_asset(GASP_PJ)
    w('  componentes: %s' % '; '.join(componentes(pj)))
    volcar_todo(pj, 40, ('SetupInput', 'SetupCamera', 'CanJumpInternal', 'CanPerformJumpAction', 'Ragdoll_Start'))
    # eventos de tecla sueltos (no de Enhanced Input) del grafo de eventos: se dispararían con el IMC quitado
    eg = BEL.find_event_graph(pj)
    teclas = [titulo(n) for n in nodos_de(eg) if 'InputKey' in n.get_class().get_name() or 'InputAction' in n.get_class().get_name()]
    w('  nodos de entrada del grafo de eventos: %s' % ', '.join(teclas))
    pcdo2 = unreal.get_default_object(clase_bp(pj))
    w('  CDO.Mesh: %s' % props(pcdo2.get_editor_property('mesh'), MALLA_PROPS))
    w('  CDO.Capsule: radio %.1f, media altura %.1f' % (pcdo2.get_editor_property('capsule_component').get_unscaled_capsule_radius(),
                                                     pcdo2.get_editor_property('capsule_component').get_unscaled_capsule_half_height()))
    w('  CDO.use_controller_rotation_yaw = %s' % pcdo2.get_editor_property('use_controller_rotation_yaw'))

    w('')
    w('=== 5. Acciones de entrada e IMC del proyecto')
    for a in reg.get_assets_by_path('/Game', recursive=True):
        c = str(a.asset_class_path.asset_name)
        if c in ('InputMappingContext',):
            imc = a.get_asset()
            try:
                maps = imc.get_editor_property('default_key_mappings').get_editor_property('mappings')
            except Exception:
                try:
                    maps = imc.get_editor_property('mappings')
                except Exception:
                    maps = []
            pares = []
            for m in maps:
                try:
                    pares.append('%s:%s' % (m.get_editor_property('action').get_name(), m.get_editor_property('key').get_editor_property('key_name')))
                except Exception:
                    pass
            w('  IMC %s (%d): %s' % (a.package_name, len(pares), ', '.join(pares)[:600]))


def guardar():
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    unreal.log('gasp_cuttlas: escrito %s (%d líneas)' % (SALIDA, len(L)))


FP_PJ = '/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter'
FP_GM = '/Game/FirstPerson/Blueprints/BP_FirstPersonGameMode'
DEST = '/Game/Tarsis/Anim'
CUTTLAS = DEST + '/BP_CuttlasGASP'
GM_TARSIS = DEST + '/BP_TarsisGameModeGASP'
# lo que la copia del GASP cambia del peón de antes y se le devuelve (la primera persona cuelga de GetMesh)
CMC_COPIA = CMC_PROPS + ('nav_agent_props', 'max_swim_speed', 'max_fly_speed', 'max_custom_movement_speed',
                         'max_step_height', 'jump_off_jump_z_factor', 'falling_lateral_friction', 'crouched_speed_multiplier',
                         'braking_sub_step_time', 'use_flat_base_for_floor_checks', 'apply_gravity_while_jumping',
                         'can_walk_off_ledges', 'maintain_horizontal_ground_velocity', 'orient_rotation_to_movement',
                         'use_controller_desired_rotation', 'requested_move_use_acceleration', 'network_smoothing_mode')
MALLA_COPIA = ('skeletal_mesh_asset', 'anim_class', 'animation_mode', 'relative_location', 'relative_rotation',
               'relative_scale3d', 'owner_no_see', 'only_owner_see', 'cast_shadow', 'visible', 'hidden_in_game',
               'visibility_based_anim_tick_option', 'first_person_primitive_type', 'collision_profile_name')
PAWN_COPIA = ('use_controller_rotation_yaw', 'use_controller_rotation_pitch', 'use_controller_rotation_roll',
              'base_eye_height', 'crouched_eye_height', 'jump_max_hold_time', 'jump_max_count')


def plantilla(bp, nombre_comp):
    """Plantilla editable de un componente del blueprint (también los heredados: su copia en el BP hijo)."""
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for h in sub.k2_gather_subobject_data_for_blueprint(bp):
        o = lib.get_object(lib.get_data(h))
        if o and o.get_name().replace('_GEN_VARIABLE', '') == nombre_comp:
            return o
    return None


def copiar(dst, src, lista, etiqueta):
    hechas, fallos = [], []
    for p in lista:
        try:
            v = src.get_editor_property(p)
        except Exception:
            continue
        try:
            if dst.get_editor_property(p) != v:
                dst.set_editor_property(p, v)
                hechas.append(p)
        except Exception as e:
            fallos.append('%s (%s)' % (p, str(e)[:60]))
    w('  %s: copiadas %s%s' % (etiqueta, ', '.join(hechas) or 'ninguna (ya iguales)', ('; fallan ' + ', '.join(fallos)) if fallos else ''))


def montar():
    """BP_CuttlasGASP = copia entera de SandboxCharacter_CMC reparentada a BP_FirstPersonCharacter, con los valores del peón
    de antes; BP_TarsisGameModeGASP = copia de BP_FirstPersonGameMode con ese peón, y el nivel Tarsis apuntando a él
    (vuelta atrás: WorldSettings.DefaultGameMode a ninguno). El GameMode global no se toca."""
    w('Cuttlas con el GASP: montaje (gasp_cuttlas.py, modo montar)')
    fp_cls = unreal.load_class(None, FP_PJ + '.BP_FirstPersonCharacter_C')
    fp_cdo = unreal.get_default_object(fp_cls)
    if eal.does_asset_exist(CUTTLAS):
        eal.delete_asset(CUTTLAS)
        unreal.SystemLibrary.collect_garbage()
    bp = eal.duplicate_asset(GASP_PJ, CUTTLAS)
    if not bp:
        w('  NO se pudo duplicar %s en %s (bórralo a mano y repite)' % (GASP_PJ, CUTTLAS))
        return
    BEL.reparent_blueprint(bp, fp_cls)
    BEL.compile_blueprint(bp)
    w('  %s: padre %s' % (CUTTLAS, BEL.get_blueprint_parent_class(bp).get_path_name()))
    # componentes heredados: su plantilla en el hijo (la copia del GASP trae su malla UEFN con su ABP, su cápsula y su CMC)
    copiar(plantilla(bp, 'CharacterMesh0'), fp_cdo.get_editor_property('mesh'), MALLA_COPIA, 'Mesh')
    cap_dst, cap_src = plantilla(bp, 'CollisionCylinder'), fp_cdo.get_editor_property('capsule_component')
    try:
        cap_dst.set_editor_property('capsule_radius', cap_src.get_unscaled_capsule_radius())
        cap_dst.set_editor_property('capsule_half_height', cap_src.get_unscaled_capsule_half_height())
        w('  Capsule: radio %.1f, media altura %.1f' % (cap_src.get_unscaled_capsule_radius(), cap_src.get_unscaled_capsule_half_height()))
    except Exception as e:
        w('  Capsule: %s' % e)
    copiar(plantilla(bp, 'CharMoveComp'), fp_cdo.get_editor_property('character_movement'), CMC_COPIA, 'CMC')
    cdo = unreal.get_default_object(BEL.generated_class(bp))
    copiar(cdo, fp_cdo, PAWN_COPIA, 'Pawn')
    marca = 'GASP_CUTTLAS_COMPILA %d' % id(bp)
    unreal.log(marca)
    BEL.compile_blueprint(bp)
    w('  compilado, estado %s' % bp.get_editor_property('status'))
    eal.save_loaded_asset(bp, False)
    # comprobación: el CDO compilado tiene lo del peón de antes
    cdo = unreal.get_default_object(BEL.generated_class(bp))
    dif = []
    for p in ('skeletal_mesh_asset', 'anim_class', 'relative_location', 'relative_rotation'):
        if cdo.get_editor_property('mesh').get_editor_property(p) != fp_cdo.get_editor_property('mesh').get_editor_property(p):
            dif.append('Mesh.' + p)
    for p in CMC_PROPS:
        try:
            if cdo.get_editor_property('character_movement').get_editor_property(p) != fp_cdo.get_editor_property('character_movement').get_editor_property(p):
                dif.append('CMC.' + p)
        except Exception:
            pass
    for p in PAWN_COPIA + ('jump_action', 'move_action', 'look_action', 'mouse_look_action'):
        try:
            if cdo.get_editor_property(p) != fp_cdo.get_editor_property(p):
                dif.append(p)
        except Exception:
            pass
    c1, c2 = cdo.get_editor_property('capsule_component'), fp_cdo.get_editor_property('capsule_component')
    if abs(c1.get_unscaled_capsule_half_height() - c2.get_unscaled_capsule_half_height()) > 0.01 or abs(c1.get_unscaled_capsule_radius() - c2.get_unscaled_capsule_radius()) > 0.01:
        dif.append('Capsule')
    w('  diferencias con BP_FirstPersonCharacter tras compilar: %s' % (', '.join(dif) or 'ninguna'))
    w('  componentes: %s' % '; '.join(componentes(bp)))
    # GameMode propio de Tarsis
    if not eal.does_asset_exist(GM_TARSIS):
        eal.duplicate_asset(FP_GM, GM_TARSIS)
    gm_bp = unreal.load_asset(GM_TARSIS)
    gm_cdo = unreal.get_default_object(BEL.generated_class(gm_bp))
    gm_cdo.set_editor_property('default_pawn_class', BEL.generated_class(bp))
    BEL.compile_blueprint(gm_bp)
    eal.save_loaded_asset(gm_bp, False)
    w('  %s: default_pawn_class = %s' % (GM_TARSIS, unreal.get_default_object(BEL.generated_class(gm_bp)).get_editor_property('default_pawn_class').get_path_name()))
    mundo = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ws = mundo.get_world_settings()
    ws.modify()
    ws.set_editor_property('default_game_mode', BEL.generated_class(gm_bp))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    w('  nivel Tarsis: WorldSettings.DefaultGameMode = %s (guardado). Para volver: ponerlo a ninguno.' % GM_TARSIS)
    msgs = []
    try:
        f = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir()), 'PruebaLumen.log')
        t = open(f, encoding='utf-8', errors='ignore').read()
        i = t.rfind(marca)
        if i >= 0:
            msgs = [re.sub(r'^\[[^\]]*\]\[[^\]]*\]', '', l).strip() for l in t[i:].splitlines() if re.search(r'LogBlueprint: (Error|Warning)|\[Compiler\]', l)]
    except Exception:
        pass
    w('  errores y avisos de compilación (%d): %s' % (len(msgs), ' | '.join(dict.fromkeys(msgs))[:1500]))


try:
    {'info': info, 'montar': montar}[MODO]()
except Exception:
    import traceback
    w('ERROR: %s' % traceback.format_exc())
guardar()
