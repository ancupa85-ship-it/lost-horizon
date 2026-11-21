"""Tanda A de animación: cómo funciona por dentro el personaje del GASP y montaje del guardia (BP_GuardiaGASP + RTG).

Se lanza en Tarsis, sin ventana y con el editor de PruebaLumen cerrado:
    D:\\ue_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe "D:\\PruebaLumen\\PruebaLumen\\PruebaLumen.uproject" -run=pythonscript -script="<repo>\\tools\\unreal\\gasp_guardia.py" -unattended -nosplash -nullrhi
Escribe D:\\LostHorizon\\gasp_guardia.txt (o LH_GASP_GUARDIA_SALIDA). LH_GASP_GUARDIA_MONTAR=0 hace solo la parte A.

A. Información (solo lee):
  1. Grafo de eventos de SandboxCharacter_CMC (BeginPlay, Tick, OnLanded, MovementModeChanged, eventos propios y de
     entrada) siguiendo las conexiones de ejecución, más sus funciones de movimiento y el grafo de AC_PreCMCTick; y
     dónde se fijan bOrientRotationToMovement, RotationRate, MaxWalkSpeed o la rotación del actor.
  2. Get_PropertiesForAnimation: de dónde sale cada campo del struct que devuelve.
  3. Valores por defecto del CMC y de las velocidades del BP; E_Gait y E_Stance; nombres internos de S_PlayerInputState.
  4. ABP_GenericRetarget: grafo de eventos y nodo Retarget Pose From Mesh (malla fuente, IKRetargeter).
  5. Pose de referencia de foot_l / ball_l en SKM_UEFN_Mannequin y en cada persona.
B. Montaje en /Game/Tarsis/Anim (solo assets nuevos; los existentes no se tocan):
  6. BP_GuardiaGASP = copia ENTERA de SandboxCharacter_CMC reparentada a ATarsisGuard (los componentes que sobran los
     apaga el C++ en BeginPlay); compilada, con sus errores y avisos. LH_GASP_GUARDIA_SOLO=b6 hace solo este paso.
  7. RTG_UEFN_<persona> (IK_UEFN_Mannequin -> IK_<persona>) y un retarget de prueba de M_Neutral_Walk_Loop_F para ver
     que sale de pie (altura de ball_l en el primer fotograma); la prueba se borra.

Los nodos de los grafos se sacan con unreal.ObjectIterator (EdGraph.Nodes está protegida) y sus conexiones con
BlueprintGraphPin.list_connected_pins, que en 5.8 sí está expuesto.
"""
import os
import re
import unreal

SALIDA = os.environ.get('LH_GASP_GUARDIA_SALIDA') or r'D:\LostHorizon\gasp_guardia.txt'
MONTAR = os.environ.get('LH_GASP_GUARDIA_MONTAR', '1') != '0'

PJ = '/Game/Blueprints/SandboxCharacter_CMC'
PRECMC = '/Game/Blueprints/AC_PreCMCTick'
RETARGET = '/Game/Blueprints/RetargetedCharacters/ABP_GenericRetarget'
UEFN_MALLA = '/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin'
UEFN_ESQ = '/Game/Characters/UEFN_Mannequin/Meshes/SK_UEFN_Mannequin'
UEFN_IK = '/Game/Characters/UEFN_Mannequin/Rigs/IK_UEFN_Mannequin'
PRUEBA_ANIM = 'M_Neutral_Walk_Loop_F'
DEST = '/Game/Tarsis/Anim'
PERSONAS = '/Game/Tarsis/Personas'
IK_ANTIGUOS = '/Game/Tarsis/Anims'          # los IK_<persona> que creó animaciones.py
GUARDIA = DEST + '/BP_GuardiaGASP'
PADRE = '/Script/PruebaLumen.TarsisGuard'
QUITAR = ['SpringArm', 'GameplayCamera', 'Camera', 'VisualOverride', 'BP_VisualOverrideManager', 'AC_TraversalLogic',
          'AC_SmartObjectAnimation', 'AC_PreCMCTick', 'AC_FoleyEvents']
# Desde 401919f BP_GuardiaGASP es la copia ENTERA (los componentes que no queremos los apaga el C++ en BeginPlay,
# TarsisGasp.cpp): quitarlos dejaba 8 nodos huérfanos y el BP en BS_ERROR. LH_GASP_QUITAR=1 vuelve a quitarlos.
QUITAR_COMPONENTES = os.environ.get('LH_GASP_QUITAR') == '1'
# LH_GASP_GUARDIA_SOLO=b6 rehace solo BP_GuardiaGASP (sin la parte A ni los RTG)
SOLO = os.environ.get('LH_GASP_GUARDIA_SOLO', '')

reg = unreal.AssetRegistryHelpers.get_asset_registry()
eal = unreal.EditorAssetLibrary
BEL = unreal.BlueprintEditorLibrary
L = []


def w(s=''):
    L.append(s)


def corta(s, n=160):
    s = str(s).replace('\n', ' ')
    return s if len(s) <= n else s[:n - 1] + '…'


# ------------------------------------------------------------------ lectura de grafos
_NODOS = {}


def nodos_por_grafo():
    """outer (EdGraph) -> nodos, de una pasada por todos los EdGraphNode cargados (se rehace con nodos_de si falta)."""
    if not _NODOS:
        for n in unreal.ObjectIterator(unreal.EdGraphNode):
            try:
                _NODOS.setdefault(n.get_outer().get_path_name(), []).append(n)
            except Exception:
                pass
    return _NODOS


def nodos_de(g):
    k = g.get_path_name()
    if k not in nodos_por_grafo():
        _NODOS.clear()   # se cargó otro blueprint después de la última pasada
        nodos_por_grafo()
        _NODOS.setdefault(k, [])   # grafo vacío: que no vuelva a rehacer la pasada
    return _NODOS[k]


def titulo(n):
    try:
        t = str(BEL.get_node_title(n)) if isinstance(n, unreal.K2Node) else n.get_name()
    except Exception:
        t = n.get_name()
    return t.replace('\n', ' ').strip()


def pines(n):
    try:
        return list(BEL.list_all_pins(n))
    except Exception:
        return []


def tipo_txt(p):
    try:
        return str(p.get_pin_type().export_text())
    except Exception:
        return ''


def es_exec(p):
    # el texto visible del tipo va traducido (editor en español): se mira la categoría interna
    return bool(re.search(r'PinCategory="?exec"?[,)]', tipo_txt(p)))


def es_salida(p):
    return p.get_pin_direction() == unreal.EdGraphPinDirection.EGPD_OUTPUT


def nombre(p):
    return str(p.get_pin_name())


def conectados(p):
    try:
        return list(p.list_connected_pins())
    except Exception:
        return []


def es_puro(n):
    return not any(es_exec(p) for p in pines(n))


def expr(p, prof=2):
    """Valor de un pin de entrada: de qué nodo viene (con sus entradas si es puro) o su valor por defecto."""
    c = conectados(p)
    if not c:
        v = ''
        try:
            v = str(p.get_pin_value())
        except Exception:
            pass
        return v if v not in ('', 'None') else '∅'
    src = c[0]
    n = src.get_owning_node()
    t = titulo(n)
    sal = [q for q in pines(n) if es_salida(q) and not es_exec(q)]
    extra = ('.' + nombre(src)) if len(sal) > 1 or nombre(src) not in ('ReturnValue', 'Return Value', '') else ''
    if es_puro(n) and prof > 0:
        args = [q for q in pines(n) if not es_salida(q) and not es_exec(q) and nombre(q) != 'self']
        if args:
            return '%s(%s)%s' % (t, ', '.join('%s=%s' % (nombre(q), expr(q, prof - 1)) for q in args), extra)
    return '%s%s' % (t, extra)


def sentencia(n):
    ent = [p for p in pines(n) if not es_salida(p) and not es_exec(p) and nombre(p) not in ('self',)]
    partes = []
    for p in ent:
        v = expr(p, 2)
        if v != '∅':
            partes.append('%s=%s' % (nombre(p), v))
    return titulo(n) + (' (' + '; '.join(partes) + ')' if partes else '')


def flujo(pin, sangria, vistos, cuenta, maximo=80):
    for dst in conectados(pin):
        if cuenta[0] >= maximo:
            if cuenta[0] == maximo:
                w(sangria + '… (corto aquí)')
                cuenta[0] += 1
            return
        n = dst.get_owning_node()
        clave = n.get_path_name()
        if clave in vistos:
            w(sangria + '↺ ' + titulo(n))
            continue
        vistos.add(clave)
        cuenta[0] += 1
        w(sangria + '- ' + corta(sentencia(n), 400))
        salidas = [p for p in pines(n) if es_salida(p) and es_exec(p)]
        for p in salidas:
            if len(salidas) > 1:
                if conectados(p):
                    w(sangria + '  [' + nombre(p) + ']')
                    flujo(p, sangria + '    ', vistos, cuenta, maximo)
            else:
                flujo(p, sangria, vistos, cuenta, maximo)


def entradas(grafo):
    """Nodos de entrada de un grafo: con salida exec y sin entrada exec (eventos, entradas de función, input)."""
    r = []
    for n in nodos_de(grafo):
        ps = pines(n)
        if any(es_exec(p) and es_salida(p) for p in ps) and not any(es_exec(p) and not es_salida(p) for p in ps):
            r.append(n)
    return r


def volcar_grafo(grafo, maximo=80, filtro=None):
    w('  ## grafo %s' % grafo.get_name())
    for e in entradas(grafo):
        t = titulo(e)
        if filtro and not re.search(filtro, t, re.I):
            continue
        datos_e = [nombre(p) for p in pines(e) if es_salida(p) and not es_exec(p)]
        w('  * %s%s' % (t, (' -> ' + ', '.join(datos_e)) if datos_e else ''))
        vistos, cuenta = set(), [0]
        for p in pines(e):
            if es_exec(p) and es_salida(p):
                if nombre(p) not in ('then', 'Then', 'OutputDelegate', '') and len([q for q in pines(e) if es_exec(q) and es_salida(q)]) > 1:
                    if conectados(p):
                        w('    [' + nombre(p) + ']')
                        flujo(p, '      ', vistos, cuenta, maximo)
                else:
                    flujo(p, '    ', vistos, cuenta, maximo)


def enum_valores(f, e):
    """valor -> nombre interno (E_X::NewEnumeratorK) y nombre visible, leídos del .uasset del UserDefinedEnum."""
    t = open(f, 'rb').read().decode('latin-1')
    internos = list(dict.fromkeys(re.findall(re.escape(e) + r'::(NewEnumerator\d+)', t)))
    visibles = {}
    for m in re.finditer(r'DisplayNameMap\((\d+) - Value\)', t):
        ini = t.rfind('/Game/', 0, m.start())
        trozo = t[max(0, ini - 80):ini]
        cand = [c for c in re.findall(r'[A-Za-z][A-Za-z0-9 _\-]+', trozo) if not re.fullmatch(r'[0-9A-F]{16,}', c)]
        if cand:
            visibles[int(m.group(1))] = cand[-1]
    return ['%d = %s::%s "%s"' % (i, e, n, visibles.get(i, '?')) for i, n in enumerate(internos)]


def grafo(bp, nombre_g):
    for g in BEL.list_graphs(bp):
        if g.get_name() == nombre_g:
            return g
    return None


# ------------------------------------------------------------------ A. información
def parte_a():
    pj = unreal.load_asset(PJ)
    w('=== A1. Grafo de eventos de SandboxCharacter_CMC (flujo de ejecución por evento)')
    volcar_grafo(BEL.find_event_graph(pj), 60)
    for f in ('UpdateMovement_PreCMC', 'UpdateRotation_PreCMC', 'GetDesiredGait', 'CalculateMaxSpeed',
              'CalculateMaxAcceleration', 'CalculateBrakingDeceleration', 'CalculateGroundFriction',
              'CalculateBrakingFriction', 'CalculateMaxCrouchSpeed', 'CanSprint', 'UpdatedMovementSimulated'):
        g = grafo(pj, f)
        if g:
            volcar_grafo(g, 40)
    pre = unreal.load_asset(PRECMC)
    if pre:
        w('')
        w('  ## AC_PreCMCTick (componente)')
        volcar_grafo(BEL.find_event_graph(pre), 30)
    w('')
    w('  Dónde se fijan rotación y velocidades (cualquier grafo de SandboxCharacter_CMC y AC_PreCMCTick):')
    pat = r'(Orient Rotation|OrientRotation|Rotation Rate|RotationRate|Max Walk Speed|MaxWalkSpeed|Set Actor Rotation|SetActorRotation|Control Rotation|ControlRotation|Max Acceleration|Braking|Ground Friction|Max Speed)'
    for bp in (pj, pre):
        if not bp:
            continue
        for g in BEL.list_graphs(bp):
            for n in nodos_de(g):
                t = titulo(n)
                if re.search(pat, t) and re.match(r'(Set|SET|K2_Set|Set )', t):
                    w('    %s / %s: %s' % (bp.get_name(), g.get_name(), corta(sentencia(n), 300)))

    w('')
    w('=== A2. Get_PropertiesForAnimation (de dónde sale cada campo)')
    g = grafo(pj, 'Get_PropertiesForAnimation')
    if g:
        volcar_grafo(g, 30)
        for n in nodos_de(g):
            if 'FunctionResult' in n.get_class().get_name() or 'Make' in titulo(n):
                w('  %s:' % titulo(n))
                for p in pines(n):
                    if not es_salida(p) and not es_exec(p):
                        w('    %-28s <- %s' % (nombre(p), corta(expr(p, 4), 400)))

    w('')
    w('=== A3. Valores por defecto')
    cdo = unreal.get_default_object(BEL.generated_class(pj))
    cm = cdo.get_editor_property('character_movement')
    for k in ('max_acceleration', 'braking_deceleration_walking', 'ground_friction', 'braking_friction_factor',
              'braking_friction', 'use_separate_braking_friction', 'rotation_rate', 'orient_rotation_to_movement',
              'use_controller_desired_rotation', 'max_walk_speed', 'max_walk_speed_crouched', 'jump_z_velocity',
              'air_control', 'gravity_scale', 'perch_radius_threshold'):
        try:
            w('  CMC.%s = %s' % (k, corta(cm.get_editor_property(k))))
        except Exception as e:
            w('  CMC.%s: %s' % (k, e))
    try:
        w('  CMC.nav_agent_props.can_crouch = %s' % cm.get_editor_property('nav_agent_props').get_editor_property('can_crouch'))
    except Exception as e:
        w('  nav_agent_props: %s' % e)
    for k in ('use_controller_rotation_yaw', 'use_controller_rotation_pitch', 'use_controller_rotation_roll'):
        try:
            w('  Pawn.%s = %s' % (k, cdo.get_editor_property(k)))
        except Exception:
            pass
    for v in ('WalkSpeeds', 'RunSpeeds', 'SprintSpeeds', 'CrouchSpeeds', 'Gait', 'MovementStickMode', 'AnalogWalk/RunThreshold'):
        try:
            x = cdo.get_editor_property(v)
            if isinstance(x, unreal.Vector):
                x = '(adelante %.0f, lado %.0f, atrás %.0f)' % (x.x, x.y, x.z)
            w('  %s = %s' % (v, x))
        except Exception as e:
            w('  %s: %s' % (v, e))
    contenido = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    for e in ('E_Gait', 'E_Stance', 'E_MovementMode', 'E_RotationMode'):
        f = os.path.join(contenido, 'Blueprints', 'Data', e + '.uasset')
        if os.path.exists(f):
            w('  %s: %s' % (e, ', '.join(enum_valores(f, e))))
    for s in ('S_PlayerInputState', 'S_CharacterPropertiesForAnimation'):
        f = os.path.join(contenido, 'Blueprints', 'Data', s + '.uasset')
        if os.path.exists(f):
            t = open(f, 'rb').read().decode('latin-1')
            w('  %s: %s' % (s, ', '.join(dict.fromkeys(re.findall(r'[A-Za-z][A-Za-z0-9_]*_\d+_[0-9A-F]{32}', t)))))

    w('')
    w('=== A4. ABP_GenericRetarget')
    rt = unreal.load_asset(RETARGET)
    for g in BEL.list_graphs(rt):
        nodos = nodos_de(g)
        if g.get_name() == 'EventGraph' or any(es_exec(p) for n in nodos for p in pines(n)):
            volcar_grafo(g, 40)
        for n in nodos:
            cl = n.get_class().get_name()
            if cl.startswith('AnimGraphNode_') and cl not in ('AnimGraphNode_Root', 'AnimGraphNode_SaveCachedPose'):
                w('  nodo %s (%s, grafo %s)' % (titulo(n), cl, g.get_name()))
                for p in pines(n):
                    if not es_salida(p):
                        w('    pin %-26s <- %s' % (nombre(p), corta(expr(p, 3), 300)))
                try:
                    txt = n.get_editor_property('node').export_text()
                    for clave in ('bUseAttachedParent', 'SourceMeshComponent', 'IKRetargeterAsset', 'bSuppressWarnings',
                                  'RetargetFrom', 'bCopyCurves', 'bUseMeshPose', 'CustomRetargetProfile'):
                        m = re.search(clave + r'=([^,)]*(\([^)]*\))?)', txt)
                        if m:
                            w('    %s = %s' % (clave, corta(m.group(1), 200)))
                except Exception as e:
                    w('    (propiedades del nodo: %s)' % e)
                # pines enlazados a variables o funciones (Property Access / bindings del nodo de animación)
                for prop in ('property_bindings', 'PropertyBindings', 'binding'):
                    try:
                        v = n.get_editor_property(prop)
                        w('    %s = %s' % (prop, corta(v, 400)))
                        break
                    except Exception:
                        pass
                try:
                    txt = n.export_text() if hasattr(n, 'export_text') else ''
                except Exception:
                    txt = ''
                for m in re.finditer(r'(PropertyBindings|Binding)[^\n]{0,300}', txt):
                    w('    ' + corta(m.group(0), 300))
    cdo_rt = unreal.get_default_object(BEL.generated_class(rt))
    for v in ('IKRetargeter', 'IKRetargeter_Map'):
        try:
            w('  %s por defecto = %s' % (v, corta(cdo_rt.get_editor_property(v), 600)))
        except Exception as e:
            w('  %s: %s' % (v, e))
    # quién la configura desde fuera
    for ref in ('/Game/Blueprints/RetargetedCharacters/BP_Manny', '/Game/Blueprints/AC_VisualOverrideManager'):
        b = unreal.load_asset(ref) if eal.does_asset_exist(ref) else None
        if b:
            for g in BEL.list_graphs(b):
                for n in nodos_de(g):
                    t = titulo(n)
                    if re.search(r'(IKRetargeter|Retarget|Leader|Anim Instance Class|AnimClass|Set Anim|Attach)', t):
                        w('  %s / %s: %s' % (b.get_name(), g.get_name(), corta(sentencia(n), 300)))

    w('')
    w('=== A5. Pose de referencia (componente, cm)')
    mallas = [('SKM_UEFN_Mannequin', unreal.load_asset(UEFN_ESQ))] + [(n, m.get_editor_property('skeleton')) for n, m in personas()]
    for nom, esq in mallas:
        try:
            pose = unreal.AnimPoseExtensions.get_reference_pose(esq)
            partes = []
            for b in ('pelvis', 'foot_l', 'ball_l'):
                t = unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD)
                p = t.translation
                partes.append('%s (%.1f, %.1f, %.1f)' % (b, p.x, p.y, p.z))
                if b in ('foot_l', 'ball_l'):
                    ejes = []
                    for eje, v in (('X', unreal.Vector(1, 0, 0)), ('Y', unreal.Vector(0, 1, 0)), ('Z', unreal.Vector(0, 0, 1))):
                        d = t.transform_direction(v)
                        mayor = max((abs(d.x), '+X' if d.x > 0 else '-X'), (abs(d.y), '+Y' if d.y > 0 else '-Y'),
                                    (abs(d.z), '+Z' if d.z > 0 else '-Z'))
                        ejes.append('%s->%s' % (eje, mayor[1]))
                    partes[-1] += ' ejes ' + ' '.join(ejes)
            w('  %-20s %s' % (nom, '; '.join(partes)))
        except Exception as e:
            w('  %-20s (%s)' % (nom, e))


# ------------------------------------------------------------------ personas
_PERS = []


def personas():
    """(nombre, SkeletalMesh) de cada carpeta /Game/Tarsis/Personas/<nombre>_<huella>, como personas.cargar."""
    if not _PERS:
        carpetas = {}
        for a in reg.get_assets_by_path(PERSONAS, recursive=True):
            # el registro guarda restos de importaciones viejas (moya_39d6f5...): solo los que existen
            if str(a.asset_class_path.asset_name) == 'SkeletalMesh' and eal.does_asset_exist(str(a.package_name)):
                carpetas.setdefault(str(a.package_path), []).append(a)
        for c in sorted(carpetas):
            nom = c.split('/')[-1].rsplit('_', 1)[0]
            _PERS.append((nom, sorted(carpetas[c], key=lambda a: str(a.asset_name))[0].get_asset()))
    return _PERS


# ------------------------------------------------------------------ B. montaje
def leer_log(desde):
    """Líneas de compilación del log de este proceso, a partir de la marca."""
    f = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir()), 'PruebaLumen.log')
    try:
        t = open(f, encoding='utf-8', errors='ignore').read()
    except Exception as e:
        return ['(no pude leer el log: %s)' % e]
    i = t.rfind(desde)
    if i < 0:
        return ['(el log aún no tiene la marca; míralo en %s)' % f]
    r = []
    for l in t[i:].splitlines():
        if re.search(r'LogBlueprint: (Error|Warning)|LogK2Compiler|\[Compiler\]', l):
            r.append(re.sub(r'^\[[^\]]*\]\[[^\]]*\]', '', l).strip())
    return r


def parte_b6():
    w('')
    w('=== B6. %s (copia de SandboxCharacter_CMC reparentada a %s)' % (GUARDIA, PADRE))
    if eal.does_asset_exist(GUARDIA):
        eal.delete_asset(GUARDIA)   # es nuestro: se rehace desde el original
        unreal.SystemLibrary.collect_garbage()
    bp = eal.duplicate_asset(PJ, GUARDIA)
    if not bp:
        w('  NO se pudo duplicar %s en %s (si quedó a medias de una pasada anterior, borra %s y repite)' % (PJ, GUARDIA, GUARDIA))
        return None
    padre = unreal.load_class(None, PADRE)
    BEL.reparent_blueprint(bp, padre)
    try:
        actual = corta(BEL.get_blueprint_parent_class(bp), 120)
    except Exception:
        actual = '?'
    w('  padre ahora: %s' % actual)
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    hs = sub.k2_gather_subobject_data_for_blueprint(bp)
    quitar, quedan = [], []
    for h in hs:
        o = lib.get_object(lib.get_data(h))
        if not o:
            continue
        n = o.get_name().replace('_GEN_VARIABLE', '')
        if QUITAR_COMPONENTES and any(n == q or (q == 'Camera' and n.startswith('Camera')) for q in QUITAR):
            quitar.append((n, h))
        elif not n.startswith('Default__'):
            quedan.append('%s (%s)' % (n, o.get_class().get_name()))
    # de uno en uno y los hijos antes que los padres (las cámaras cuelgan del SpringArm): borrarlos juntos hace que el
    # editor no encuentre el padre al promover a los hijos
    quitar.sort(key=lambda x: (0 if x[0].startswith('Camera') else 1))
    hecho = 0
    for n_q, _ in quitar:
        for h in sub.k2_gather_subobject_data_for_blueprint(bp):
            o = lib.get_object(lib.get_data(h))
            if o and o.get_name().replace('_GEN_VARIABLE', '') == n_q:
                try:
                    hecho += sub.delete_subobject(sub.k2_gather_subobject_data_for_blueprint(bp)[0], h, bp)
                except Exception as e:
                    w('  no pude quitar %s: %s' % (n_q, e))
                break
    if QUITAR_COMPONENTES:
        w('  componentes quitados (%s): %s' % (hecho, ', '.join(n for n, _ in quitar)))
    else:
        w('  copia entera: no se quita ningún componente (los apaga el C++ en BeginPlay)')
    w('  componentes: %s' % ', '.join(quedan))
    marca = 'GASP_GUARDIA_COMPILA %d' % id(bp)
    unreal.log(marca)
    BEL.compile_blueprint(bp)
    try:
        st = bp.get_editor_property('status')
    except Exception:
        st = '?'
    w('  compilado, estado %s' % st)
    eal.save_loaded_asset(bp, False)
    msgs = leer_log(marca)
    w('  errores y avisos de compilación (%d):' % len(msgs))
    vistos = set()
    for m in msgs:
        if m not in vistos:
            vistos.add(m)
            w('    ' + corta(m, 400))
    if not QUITAR_COMPONENTES:
        return bp
    # qué nodos se han quedado sin destino: llamadas a funciones de los componentes quitados con el pin self suelto,
    # y lecturas de esas variables
    w('  nodos que apuntaban a lo quitado (grafo: nodo):')
    clases = r'(AC_FoleyEvents|AC_PreCMCTick|AC_TraversalLogic|AC_SmartObjectAnimation|AC_VisualOverrideManager|GameplayCamera|SpringArm|CameraComponent|ChildActorComponent|ActorComponent)'
    quitados = r'^(Get |Obtener |)(%s)' % '|'.join(re.escape(q) for q in QUITAR)
    n_rotos = 0
    for g in BEL.list_graphs(bp):
        for n in nodos_de(g):
            yo = [p for p in pines(n) if nombre(p) == 'self' and not es_salida(p)]
            roto = False
            if yo and not conectados(yo[0]) and re.search(clases, tipo_txt(yo[0])):
                roto = True
            if re.search(quitados, titulo(n)):
                roto = True
            if roto:
                n_rotos += 1
                w('    %s: %s' % (g.get_name(), corta(sentencia(n), 260)))
    if not n_rotos:
        w('    (ninguno encontrado)')
    return bp


def ik_rig(nom, malla):
    for ruta in ('%s/%s_v1/IK_%s' % (IK_ANTIGUOS, nom, nom), '%s/IK_%s' % (DEST, nom)):
        if eal.does_asset_exist(ruta):
            return unreal.load_asset(ruta), ruta, False
    # como animaciones._ik_rig, pero en /Game/Tarsis/Anim
    rig = unreal.IKRigDefinitionFactory.create_new_ik_rig_asset(DEST, 'IK_' + nom)
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(malla)
    c.apply_auto_generated_retarget_definition()
    try:
        c.set_retarget_root('pelvis')
    except Exception:
        pass
    eal.save_loaded_asset(rig, False)
    return rig, DEST + '/IK_' + nom, True


def cadenas(rig):
    try:
        return [str(x.get_editor_property('chain_name')) for x in unreal.IKRigController.get_controller(rig).get_retarget_chains()]
    except Exception:
        return []


def parte_b7():
    w('')
    w('=== B7. IK Retargeters UEFN -> persona y prueba de retarget (%s)' % PRUEBA_ANIM)
    src_rig = unreal.load_asset(UEFN_IK)
    src_malla = unreal.load_asset(UEFN_MALLA)
    anim = None
    for a in reg.get_assets_by_path('/Game/Characters/UEFN_Mannequin/Animations', recursive=True):
        if str(a.asset_name) == PRUEBA_ANIM and str(a.asset_class_path.asset_name) == 'AnimSequence':
            anim = a   # duplicate_and_retarget quiere AssetData, no el objeto
    w('  fuente: %s (cadenas: %s)' % (UEFN_IK, ', '.join(cadenas(src_rig))))
    prueba = DEST + '/_prueba'
    S, T = unreal.RetargetSourceOrTarget.SOURCE, unreal.RetargetSourceOrTarget.TARGET
    for nom, malla in personas():
        rig, ruta_rig, nuevo = ik_rig(nom, malla)
        nombre_rtg = 'RTG_UEFN_' + nom
        # si ya existe (pasada anterior) se reconfigura en el sitio: borrar y crear con el mismo nombre en la misma
        # sesión falla porque el paquete borrado sigue en memoria
        rtg = unreal.load_asset(DEST + '/' + nombre_rtg) if eal.does_asset_exist(DEST + '/' + nombre_rtg) else None
        if not rtg:
            rtg = unreal.AssetToolsHelpers.get_asset_tools().create_asset(nombre_rtg, DEST, unreal.IKRetargeter, unreal.IKRetargetFactory())
        if not rtg:
            w('  %s: NO se pudo crear' % nombre_rtg)
            continue
        rc = unreal.IKRetargeterController.get_controller(rtg)
        rc.set_ik_rig(S, src_rig)
        rc.set_ik_rig(T, rig)
        rc.remove_all_ops()
        rc.add_default_ops()
        rc.assign_ik_rig_to_all_ops(S, src_rig)
        rc.assign_ik_rig_to_all_ops(T, rig)
        rc.set_preview_mesh(S, src_malla)
        rc.set_preview_mesh(T, malla)
        rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
        rc.auto_align_all_bones(T, unreal.RetargetAutoAlignMethod.CHAIN_TO_CHAIN)
        eal.save_loaded_asset(rtg, False)
        mapa = []
        for ch in cadenas(rig):
            try:
                mapa.append('%s<-%s' % (ch, rc.get_source_chain(ch)))
            except Exception:
                try:
                    mapa.append('%s<-%s' % (ch, rc.get_source_chain(unreal.Name(ch), '')))
                except Exception:
                    mapa.append(ch + '<-?')
        w('  %s: rig %s%s; cadenas %s' % (nombre_rtg, ruta_rig, ' (NUEVO)' if nuevo else '', ', '.join(mapa)))
        if not anim:
            w('    (no encuentro %s para la prueba)' % PRUEBA_ANIM)
            continue
        try:
            res = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
                [anim], src_malla, malla, rtg, '', '', '', '_' + nom, prueba, False, False, True)
            hecho = None
            for a in reg.get_assets_by_path(prueba, recursive=True):
                if str(a.asset_name) == PRUEBA_ANIM + '_' + nom:
                    hecho = a.get_asset()
            if not hecho:
                w('    prueba: el retarget no dejó %s_%s (%s)' % (PRUEBA_ANIM, nom, res))
                continue
            pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(hecho, 0.0, unreal.AnimPoseEvaluationOptions())
            ref = unreal.AnimPoseExtensions.get_reference_pose(malla.get_editor_property('skeleton'))
            alt = {}
            for b in ('pelvis', 'ball_l', 'ball_r', 'foot_l'):
                alt[b] = unreal.AnimPoseExtensions.get_bone_pose(pose, b, unreal.AnimPoseSpaces.WORLD).translation.z
            ref_ball = unreal.AnimPoseExtensions.get_bone_pose(ref, 'ball_l', unreal.AnimPoseSpaces.WORLD).translation.z
            ref_pel = unreal.AnimPoseExtensions.get_bone_pose(ref, 'pelvis', unreal.AnimPoseSpaces.WORLD).translation.z
            bajo = min(alt['ball_l'], alt['ball_r'])
            veredicto = 'DE PIE' if -6.0 <= bajo <= 15.0 else ('FLOTA' if bajo > 15.0 else 'HUNDIDO')
            w('    prueba fotograma 0: pelvis %.1f (ref %.1f), foot_l %.1f, ball_l %.1f, ball_r %.1f (ref ball_l %.1f) -> %s'
              % (alt['pelvis'], ref_pel, alt['foot_l'], alt['ball_l'], alt['ball_r'], ref_ball, veredicto))
        except Exception as e:
            w('    prueba: error %s' % e)
    if eal.does_directory_exist(prueba):
        eal.delete_directory(prueba)
        w('  prueba borrada (%s)' % prueba)


# ------------------------------------------------------------------
w('GASP -> guardia de Tarsis (gasp_guardia.py)')
w('Proyecto: %s' % unreal.Paths.get_project_file_path())
w('')
if SOLO != 'b6':
    try:
        parte_a()
    except Exception as e:
        import traceback
        w('ERROR en la parte A: %s' % traceback.format_exc())
if MONTAR:
    for paso in ((parte_b6,) if SOLO == 'b6' else (parte_b6, parte_b7)):
        try:
            paso()
        except Exception:
            import traceback
            w('ERROR en %s: %s' % (paso.__name__, traceback.format_exc()))
os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
with open(SALIDA, 'w', encoding='utf-8') as f:
    f.write('\n'.join(L) + '\n')
unreal.log('gasp_guardia: escrito %s (%d líneas)' % (SALIDA, len(L)))
