"""Tanda A, septima: giro en el sitio estando quieto. Un guardia se vuelve hacia un ruido (90 y 160 grados) y Cuttlas,
parado en tercera persona, gira la camara 90 y 160 grados. Serie cada 0,1 s del desfase de las piernas (hueso raiz del que
conduce y pies de la persona), WantsToAim del giro y velocidad; capturas en D:\\LostHorizon\\capturas-gaspA\\
(guardia_giro_* y cuttlas_giro_*) y la serie en giro_medidas.txt."""
import builtins, glob, math, os, shutil, time
import unreal

OUT = r'D:\LostHorizon\capturas-gaspA'
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
V = unreal.Vector
S = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'L': [], 'hechas': [], 'blur': None, 'cap': None}
builtins._visual_giro = S


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def clase(n):
    return unreal.load_class(None, '/Script/PruebaLumen.' + n)


def director(w):
    return unreal.GameplayStatics.get_all_actors_of_class(w, clase('TarsisDirector'))[0]


def comp(a, pref):
    for c in a.get_components_by_class(unreal.SkeletalMeshComponent):
        if c.get_name().startswith(pref):
            return c
    return None


def piernas(b):
    bl, br = b.get_socket_location('ball_l'), b.get_socket_location('ball_r')
    fl, fr = b.get_socket_location('foot_l'), b.get_socket_location('foot_r')
    return math.degrees(math.atan2((bl.y - fl.y) + (br.y - fr.y), (bl.x - fl.x) + (br.x - fr.x)))


def dif(a, b):
    return ((a - b + 540) % 360) - 180


def raiz(c):
    return -c.get_socket_transform('root', unreal.RelativeTransformSpace.RTS_COMPONENT).rotation.rotator().yaw


def apunta(a, d):
    try:
        return a.gasp_turn_aiming()
    except Exception:
        return d.hero_gasp_turn_aiming()


def muestra(a, d, cuerpo, conductor, etiqueta, t):
    y = a.get_actor_rotation().yaw
    # brazos: altura de las manos sobre la pelvis de la persona (apuntar las subiria)
    manos = None
    if cuerpo:
        pz = cuerpo.get_socket_location('pelvis').z
        manos = round(max(cuerpo.get_socket_location('hand_l').z, cuerpo.get_socket_location('hand_r').z) - pz)
    S['L'].append('%s t=%.1f actor=%.0f raiz=%.0f piernas-actor=%.0f aim=%s vel=%.0f manos-pelvis=%s' % (
        etiqueta, t, y, ((raiz(conductor) + 540) % 360) - 180 if conductor else 0, dif(piernas(cuerpo), y) if cuerpo else 0,
        apunta(a, d), a.get_velocity().length(), manos))


def captura(w, nombre):
    antes = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
    unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1920x1080')
    S['cap'] = (antes, nombre, time.time() + 2.0)


def recoger():
    if not S['cap'] or time.time() < S['cap'][2]:
        return
    antes, nombre, _ = S['cap']
    nuevas = sorted(set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True)) - antes, key=os.path.getmtime)
    if nuevas:
        destino = os.path.join(OUT, '%s.png' % nombre)
        shutil.move(nuevas[-1], destino)
        S['hechas'].append(destino)
        S['cap'] = None


def serie(w, a, d, cuerpo, conductor, etiqueta, fotos):
    """3 s de muestras cada 0,1 s; fotos: {decimas: nombre}"""
    for i in range(1, 31):
        yield 0.1
        recoger()
        muestra(a, d, cuerpo, conductor, etiqueta, i * 0.1)
        if i in fotos and not S['cap']:
            captura(w, fotos[i])
    while S['cap']:
        yield 0.3
        recoger()


def pasos():
    w = mundo()
    d = director(w)
    if d.get_editor_property('cine'):
        d.interact()
    yield 2.0
    d.set_day(True)
    yield 1.0
    unreal.SystemLibrary.execute_console_command(w, 'showhud')
    S['blur'] = unreal.SystemLibrary.get_console_variable_int_value('r.MotionBlurQuality')
    unreal.SystemLibrary.execute_console_command(w, 'r.MotionBlurQuality 0')
    os.makedirs(OUT, exist_ok=True)
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    gs = unreal.GameplayStatics.get_all_actors_of_class(w, clase('TarsisGuard'))
    for g in gs:
        g.set_editor_property('view_distance', 1.0)
    m = [g for g in gs if not g.get_editor_property('tower_sentry')][0]
    for ang in (90.0, 160.0):
        for g in gs:
            g.hold(0.0 if g == m else 600.0)
        yield 1.0
        m.hold(4.0)
        yield 1.5
        # el jugador a 4,5 m delante del guardia, mirandolo
        l = m.get_actor_location(); f = m.get_actor_forward_vector(); r = m.get_actor_right_vector()
        pos = V(l.x + f.x * 380 - r.x * 220, l.y + f.y * 380 - r.y * 220, l.z + 40)
        p.set_actor_location(pos, False, True)
        pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pos, V(l.x, l.y, l.z - 20)))
        yield 1.1
        m.hold(0.0)   # parado (StopMovement) y libre para oir
        l = m.get_actor_location(); y = m.get_actor_rotation().yaw + ang
        m.hear_noise(V(l.x + math.cos(math.radians(y)) * 700, l.y + math.sin(math.radians(y)) * 700, l.z))
        yield from serie(w, m, d, comp(m, 'CuerpoPersona'), comp(m, 'CharacterMesh0'), 'guardia_%d' % ang,
                         {4: 'guardia_giro_%d_girando' % ang, 25: 'guardia_giro_%d_2s5' % ang})
    for g in gs:
        g.hold(600.0)
    # Cuttlas parado en tercera persona, en la recta del patio
    INICIO = V(4300, 3500, 120)
    p.set_actor_location(INICIO, False, True)
    pc.set_control_rotation(unreal.Rotator(0.0, -8.0, 15.0))
    d.toggle_third()
    yield 1.0
    # un paso corto para que las piernas salgan alineadas con el cuerpo
    cmc = p.get_editor_property('character_movement')
    for _ in range(8):
        p.add_movement_input(p.get_actor_forward_vector(), 1.0, False)
        yield 0.05
    yield 2.0
    for ang in (90.0, 160.0):
        muestra(p, d, comp(p, 'CuerpoCuttlas'), comp(p, 'ConductorGASP'), 'cuttlas_%d_antes' % ang, 0.0)
        r = pc.get_control_rotation()
        pc.set_control_rotation(unreal.Rotator(r.roll, r.pitch, r.yaw + ang))
        yield from serie(w, p, d, comp(p, 'CuerpoCuttlas'), comp(p, 'ConductorGASP'), 'cuttlas_%d' % ang,
                         {4: 'cuttlas_giro_%d_girando' % ang, 25: 'cuttlas_giro_%d_2s5' % ang})
        yield 1.0
    d.toggle_third()


def _fin():
    try:
        director(mundo()).set_day(False)
    except Exception:
        pass
    if S.get('blur') is not None:
        unreal.SystemLibrary.execute_console_command(None, 'r.MotionBlurQuality %d' % S['blur'])
    with open(os.path.join(OUT, 'giro_medidas.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(S['L'] + ['capturas: %s' % S['hechas'], 'estado: %s' % S['estado']]))


def _tick(dt):
    try:
        w = mundo()
        if S['estado'] == 'arrancando':
            if w and unreal.GameplayStatics.get_player_pawn(w, 0):
                S['estado'] = 'midiendo'
                S['gen'] = pasos()
            return
        if S['estado'] != 'midiendo' or time.time() < S['espera']:
            return
        try:
            S['espera'] = time.time() + next(S['gen'])
        except StopIteration:
            S['estado'] = 'terminado'
            _fin()
            unreal.unregister_slate_post_tick_callback(S['h'])
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    except Exception:
        import traceback
        S['estado'] = 'error: %s' % traceback.format_exc()
        _fin()
        unreal.unregister_slate_post_tick_callback(S['h'])
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()


o = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
if o:
    o.set_editor_property('bThrottleCPUWhenNotForeground', False)
if mundo():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
S['h'] = unreal.register_slate_post_tick_callback(_tick)
