"""Tanda B: fotos de lo nuevo, en PIE de dia. (1) un guardia con el M14, de ronda y apuntando; (2) el lobo amigo trae la
piedra; (3) un guardia acaricia al lobo. Va apuntando en tandaB_medidas.txt lo que importa de cada foto (peso de la pose
de fusil, boca del canon, estado del lobo, guardia agachado...).
Capturas en D:\\LostHorizon\\capturas-tandaB\\<escena>_NN.png. builtins._tandaB_escenas elige escenas."""
import builtins, glob, math, os, shutil, time
import unreal

OUT = getattr(builtins, '_tandaB_out', r'D:\LostHorizon\capturas-tandaB')
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
V = unreal.Vector
ESCENAS = getattr(builtins, '_tandaB_escenas', ['fusil', 'lobo_piedra', 'caricia'])
S = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'L': [], 'pedidas': [], 'antes': set()}
builtins._visual_tandaB = S


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def director(w):
    return unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector'))[0]


def guardias(w):
    return unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard'))


def foto(w, nombre, nota=''):
    unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1600x900')
    S['pedidas'].append(nombre)
    S['L'].append('%s  %s' % (nombre, nota))


def recoger():
    nuevas = sorted(set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True)) - S['antes'], key=os.path.getmtime)
    for f, nombre in zip(nuevas, S['pedidas']):
        shutil.move(f, os.path.join(OUT, nombre + '.png'))
    if len(nuevas) != len(S['pedidas']):
        S['L'].append('AVISO: pedidas %d fotos, salieron %d' % (len(S['pedidas']), len(nuevas)))
    S['antes'] = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
    S['pedidas'] = []


def mirar(w, punto, altura=0.0):
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    cam = unreal.GameplayStatics.get_player_camera_manager(w, 0).get_camera_location()
    r = unreal.MathLibrary.find_look_at_rotation(cam, V(punto.x, punto.y, punto.z + altura))
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(r)


def juego(s):
    # espera s segundos de JUEGO (cada HighResShot congela el juego un rato: esperar en tiempo real no avanza la escena)
    w = mundo()
    t0 = unreal.GameplayStatics.get_time_seconds(w)
    while unreal.GameplayStatics.get_time_seconds(mundo()) - t0 < s:
        yield 0.05


def pasos():
    w = mundo()
    d = director(w)
    if d.get_editor_property('cine'):
        d.interact()
    # que nada pare el juego ni saque a los guardias de su sitio mientras se hacen las fotos (el codec pausa el PIE)
    for k in ('codec_calls', 'radio_chat', 'talk_rule', 'talk_cross', 'truck'):
        try:
            d.set_editor_property(k, False)
        except Exception:
            pass
    yield 4.0
    d.set_day(True)
    yield 1.0
    unreal.SystemLibrary.execute_console_command(w, 'showhud')
    os.makedirs(OUT, exist_ok=True)
    S['antes'] = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    for g in guardias(w):
        g.set_editor_property('view_distance', 1.0)   # que no te vean mientras se hacen las fotos
    if 'fusil' in ESCENAS:
        ronda = [g for g in guardias(w) if not g.get_editor_property('tower_sentry')]
        gs = [g for g in ronda if g.has_rifle()]
        S['L'].append('guardias con fusil: %d de %d de ronda (%d en total); sin fusil: %s' % (len(gs), len(ronda), len(guardias(w)), [g.get_actor_label() + ('/gasp' if g.uses_gasp() else '/sin gasp') for g in ronda if not g.has_rifle()]))
        for i, g in enumerate(gs[:3]):
            g.hold(8.0)   # quieto para la foto (la pose de fusil sigue: la pone LookTick)
            yield 0.5
            l = g.get_actor_location(); f = g.get_actor_forward_vector(); r = g.get_actor_right_vector()
            # de lado y un poco por delante, a 3,5 m
            p.set_actor_location(V(l.x + r.x * 300 + f.x * 180, l.y + r.y * 300 + f.y * 180, l.z + 20), False, True)
            yield 0.4
            mirar(w, g.get_actor_location(), 20.0)
            yield 0.3
            m = g.rifle_muzzle(); l = g.get_actor_location()
            foto(w, 'fusil_ronda_%d' % i, '%s pose %.2f apunta %s boca (%+.0f, %+.0f, %+.0f)' % (g.get_actor_label(), g.rifle_pose_weight(), g.rifle_aiming(), m.x - l.x, m.y - l.y, m.z - l.z))
            yield 0.6
        # uno en alerta: apunta (pose ADS de Lyra)
        if gs:
            g = gs[0]
            l = g.get_actor_location()
            g.alarm(V(l.x + 600, l.y, l.z))
            yield 2.0
            g.hold(8.0)
            yield 0.3
            l = g.get_actor_location(); f = g.get_actor_forward_vector(); r = g.get_actor_right_vector()
            p.set_actor_location(V(l.x + r.x * 280 + f.x * 120, l.y + r.y * 280 + f.y * 120, l.z + 20), False, True)
            yield 0.3
            mirar(w, g.get_actor_location(), 20.0)
            yield 0.3
            foto(w, 'fusil_alerta', '%s pose %.2f apunta %s estado %s' % (g.get_actor_label(), g.rifle_pose_weight(), g.rifle_aiming(), g.get_editor_property('state')))
            yield 1.0
        recoger()
    if 'lobo_piedra' in ESCENAS or 'caricia' in ESCENAS:
        for g in guardias(w):
            g.hold(600.0)
        d.set_editor_property('dog', True)
        d.set_flag('perro_amigo')
        p.set_actor_location(V(4950, 6000, 120), False, True)
        yield 2.0
        S['L'].append('lobo: listo %s, es lobo %s, animaciones %d, giro malla %.0f' % (d.dog_ready(), d.get_editor_property('dog_wolf'), d.dog_anim_count(), d.get_editor_property('dog_mesh_yaw')))
    if 'lobo_piedra' in ESCENAS and d.dog_ready():
        l = d.dog_location()
        # a 4 m del lobo, de lado; tiras hacia delante y abajo
        p.set_actor_location(V(l.x - 150, l.y - 400, l.z + 120), False, True)
        yield 0.5
        mirar(w, l, 30.0)
        yield 0.5
        foto(w, 'lobo_00_tumbado', 'estado %d anim %d' % (d.get_editor_property('dog_state'), d.dog_anim_index()))
        yield 0.5
        r = pc.get_control_rotation()
        pc.set_control_rotation(unreal.Rotator(0.0, -18.0, r.yaw + 40.0))
        yield 0.2
        d.throw_stone()
        yield 0.1
        for i in range(1, 30):
            mirar(w, d.dog_location(), 30.0)
            yield 0.05
            foto(w, 'lobo_%02d' % i, 'busca %d anim %d lleva %s' % (d.get_editor_property('dog_fetch'), d.dog_anim_index(), d.dog_carrying()))
            yield from juego(0.3)
            if d.get_editor_property('dog_fetch') == 0 and i > 3:
                break
        S['L'].append('lobo: piedras traidas %d' % d.get_editor_property('dog_fetches'))
        recoger()
    if 'caricia' in ESCENAS and d.dog_ready():
        d.dog_forget_pets()
        l = d.dog_location()
        gs = [g for g in guardias(w) if not g.get_editor_property('tower_sentry') and str(g.get_editor_property('state')).endswith('PATROL: 0>') and g.get_editor_property('meter') < 0.05]
        S['L'].append('caricia: tranquilos %s' % [x.get_actor_label() for x in gs])
        g = gs[-1]
        for x in guardias(w):
            x.hold(0.0 if x == g else 600.0)
        yield 0.3
        g.set_actor_location(V(l.x - 260, l.y + 60, g.get_actor_location().z), False, True)
        p.set_actor_location(V(l.x + 150, l.y - 450, l.z + 120), False, True)
        for i in range(0, 30):
            yield from juego(0.5)
            mirar(w, d.dog_location(), 40.0)
            yield 0.05
            pt = d.dog_petter()
            foto(w, 'caricia_%02d' % i, 'acaricia %s agachado %s lobo anim %d voz %s' % (pt.get_actor_label() if pt else '-', pt.pet_crouched() if pt else False, d.dog_anim_index(), d.get_editor_property('last_voice')))
            if pt is None and i > 6:
                break
        recoger()


def _fin():
    w = mundo()
    try:
        director(w).set_day(False)
    except Exception:
        pass
    try:
        recoger()
    except Exception:
        pass
    with open(os.path.join(OUT, 'tandaB_medidas.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(S['L'] + ['estado: %s' % S['estado']]))


def _tick(dt):
    try:
        w = mundo()
        if S['estado'] == 'arrancando':
            if w and unreal.GameplayStatics.get_player_pawn(w, 0):
                S['estado'] = 'midiendo'
                S['gen'] = pasos()
            return
        if S['estado'] != 'midiendo':
            return
        if time.time() < S['espera']:
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
