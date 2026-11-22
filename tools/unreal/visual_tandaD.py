"""Tanda D: fotos de lo nuevo, en PIE. Escenas (builtins._tandaD_escenas): rastro (de noche: pisadas mojadas que salen
de un charco y un guardia que las sigue con la linterna), relevo (al pie de una torre: la charla y el relevo subiendo),
caricia (con el fusil a la espalda), levantarse (de la fisica a agachado y de pie) y arrastre (visto desde 10, 20 y 30 m
con una camara fija). Espera en tiempo de JUEGO y con el codec y las charlas apagados.
Capturas en D:\\LostHorizon\\capturas-tandaD\\<escena>_NN.png y lo medido en tandaD_medidas.txt."""
import builtins, glob, math, os, shutil, time
import unreal

OUT = getattr(builtins, '_tandaD_out', r'D:\LostHorizon\capturas-tandaD')
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
V = unreal.Vector
ESCENAS = getattr(builtins, '_tandaD_escenas', ['rastro', 'relevo', 'caricia', 'levantarse', 'arrastre'])
S = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'L': [], 'pedidas': [], 'antes': set()}
builtins._visual_tandaD = S


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def director(w):
    return unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector'))[0]


def guardias(w):
    return unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard'))


def estado(g):
    return str(g.get_editor_property('state')).split('.')[-1].split(':')[0]


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


def juego(s):
    t0 = unreal.GameplayStatics.get_time_seconds(mundo())
    while unreal.GameplayStatics.get_time_seconds(mundo()) - t0 < s:
        yield 0.05


def mirar(w, punto, altura=0.0):
    # desde los ojos del jugador (la camara es en primera persona). La del gestor de camara llega un fotograma tarde
    # despues de mover al jugador, y las fotos de la caricia salian mirando al cielo
    cam = unreal.GameplayStatics.get_player_pawn(w, 0).get_actor_location() + V(0, 0, 65)
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cam, V(punto.x, punto.y, punto.z + altura)))


def poner(w, x, y, z):
    unreal.GameplayStatics.get_player_pawn(w, 0).set_actor_location(V(x, y, z), False, True)


def camara(w, pos, mira, quien):
    """Vista fija desde fuera. Desde Python no se puede crear una CameraActor en el mundo de la partida
    (GameplayStatics no tiene begin_deferred_actor_spawn_from_class en 5.8): se usa un guardia quieto y oculto,
    cuya camara pasa a ser la vista (queda unos metros por detras de el)."""
    rot = unreal.MathLibrary.find_look_at_rotation(pos, mira)
    quien.hold(600.0)
    quien.set_actor_location(pos, False, True)
    quien.set_actor_rotation(unreal.Rotator(0, 0, rot.yaw), False)
    quien.set_actor_hidden_in_game(True)
    unreal.GameplayStatics.get_player_controller(w, 0).set_view_target_with_blend(quien, 0.0)
    return quien


def sitio_libre(w, d, ignorar, detras=420, delante=950):
    """Un barro y un rumbo sin nada en medio (en (4300, 3800) habia un contenedor con su caja de colision)."""
    n = d.soft_patch_count()
    barro = [d.soft_patch_center(i) for i in range(n) if not d.soft_patch_water(i) and not d.soft_patch_rain(i)]
    for c in barro:
        for yaw in range(0, 360, 30):
            f = unreal.MathLibrary.get_forward_vector(unreal.Rotator(0, 0, yaw))
            if unreal.SystemLibrary.line_trace_single(w, V(c.x - f.x * detras, c.y - f.y * detras, c.z + 60), V(c.x + f.x * delante, c.y + f.y * delante, c.z + 60),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignorar, unreal.DrawDebugTrace.NONE, True) is None:
                return c, yaw, f
    return None


def pasos():
    w = mundo()
    d = director(w)
    if d.get_editor_property('cine'):
        d.interact()
    for k in ('codec_calls', 'radio_chat', 'talk_rule', 'talk_cross', 'truck'):
        try:
            d.set_editor_property(k, False)
        except Exception:
            pass
    yield 4.0
    unreal.SystemLibrary.execute_console_command(w, 'showhud')
    os.makedirs(OUT, exist_ok=True)
    S['antes'] = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    ronda = [g for g in guardias(w) if not g.get_editor_property('tower_sentry') and g.uses_gasp()]
    if 'rastro' in ESCENAS:
        # de noche: un rastro mojado cruzando el patio y un guardia que lo ve con la linterna
        d.set_editor_property('print_rule', True)
        for g in guardias(w):
            g.hold(600.0)
        n = d.soft_patch_count()
        agua = [d.soft_patch_center(i) for i in range(n) if d.soft_patch_water(i) and not d.soft_patch_rain(i)]
        barro = [d.soft_patch_center(i) for i in range(n) if not d.soft_patch_water(i) and not d.soft_patch_rain(i)]
        g = ronda[0]
        def libre(p0, p1):
            return unreal.SystemLibrary.line_trace_single(w, p0, p1, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [g, p], unreal.DrawDebugTrace.NONE, True) is None
        # como en la prueba: desde un barro, una direccion despejada (en (4300, 3800) habia un contenedor)
        rumbo = None
        for c in barro:
            for yaw in range(0, 360, 30):
                f = unreal.MathLibrary.get_forward_vector(unreal.Rotator(0, 0, yaw))
                if libre(V(c.x - f.x * 420, c.y - f.y * 420, c.z + 60), V(c.x + f.x * 950, c.y + f.y * 950, c.z + 60)):
                    rumbo = (c, yaw, f)
                    break
            if rumbo:
                break
        if agua and rumbo:
            a = agua[0]
            c, yaw, f = rumbo
            q = V(-f.y, f.x, 0)   # a la derecha del rastro
            def en(t, lat=0.0, z=0.0):
                return V(c.x + f.x * t + q.x * lat, c.y + f.y * t + q.y * lat, c.z + z)
            d.test_footstep(V(a.x, a.y, a.z), 0.0, False)
            for k in range(16):
                d.test_footstep(en(62 * k, 11 if k % 2 else -11, 2), float(yaw), False)
            # primero, las huellas solas (de dia y de cerca)
            d.set_day(True)
            yield from juego(1.0)
            ca = en(300, -260, 160)
            poner(w, ca.x, ca.y, ca.z)
            yield 0.3
            mirar(w, en(450), 0.0)
            yield from juego(0.6)
            foto(w, 'rastro_huellas_de_dia', 'activas %d, ultima %.2f' % (d.prints_active(), d.print_fade(0)))
            # de cerca, mirando al suelo: la forma de la suela, de barro (las primeras) y mojada (las de despues)
            for nombre, t in (('rastro_cerca_barro', 65.0), ('rastro_cerca_mojada', 65.0 * 8)):
                ca = en(t - 60, -110, 140)
                poner(w, ca.x, ca.y, ca.z)
                yield 0.3
                mirar(w, en(t + 30), 0.0)
                yield from juego(0.5)
                foto(w, nombre, 'rumbo %d' % yaw)
            yield from juego(0.4)
            d.set_day(False)
            yield from juego(1.0)
            fin = en(1500, 0, 88)
            g.set_editor_property('patrol_points', [fin, V(fin.x + 20, fin.y, fin.z)])
            gi = en(-380, 0, 95)
            g.set_actor_location(gi, False, True)
            g.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
            g.hold(0.0)
            ca = en(500, -700, 160)
            poner(w, ca.x, ca.y, ca.z)
            for i in range(40):
                yield from juego(0.5)
                if g.get_editor_property('tracking_prints') and i % 3 == 0:
                    mirar(w, g.get_actor_location(), 0.0)
                    yield 0.05
                    foto(w, 'rastro_linterna_%02d' % i, '%s sigue el rastro, pasos %d' % (g.get_actor_label(), d.get_editor_property('track_steps')))
                if d.get_editor_property('tracks_finished') > 0:
                    break
            S['L'].append('rastro: empezados %d, acabados %d, pasos %d, estado %s' % (d.get_editor_property('tracks_started'), d.get_editor_property('tracks_finished'), d.get_editor_property('track_steps'), estado(g)))
        recoger()
        d.set_editor_property('print_rule', False)
    if 'relevo' in ESCENAS:
        d.set_editor_property('relief_rule', True)
        d.set_day(True)
        for g in guardias(w):
            if not g.get_editor_property('tower_sentry'):
                g.set_editor_property('view_distance', 1.0)
        yield from juego(2.0)
        d.set_editor_property('relief_wait_min', 8.0)
        d.set_editor_property('relief_wait_max', 10.0)
        d.force_relief(0)
        for i in range(400):
            yield from juego(0.5)
            if d.relief_phase(0) >= 2:
                break
        r = d.relief_guard(0)
        if r:
            l = r.get_actor_location()
            poner(w, l.x + 260, l.y - 260, l.z + 40)
            yield 0.3
            mirar(w, l, 20.0)
            yield from juego(0.4)
            foto(w, 'relevo_charla_pie_torre', 'fase %d, puesto vacio %s' % (d.relief_phase(0), d.relief_post_empty(0)))
            for i in range(60):
                yield from juego(0.5)
                if d.relief_phase(0) in (0, 4):
                    break
            s = d.relief_sentry(0)
            if s:
                sl = s.get_actor_location()
                poner(w, sl.x + 900, sl.y - 900, 160)
                yield 0.3
                mirar(w, sl, 0.0)
                yield from juego(0.4)
                foto(w, 'relevo_ya_arriba', 'ventana %.1f s, santo y sena %s / %s' % (d.get_editor_property('last_relief_window'), d.get_editor_property('password_a'), d.get_editor_property('password_b')))
        recoger()
        d.set_editor_property('relief_rule', False)
    if 'caricia' in ESCENAS:
        for x in guardias(w):
            x.hold(600.0)
        d.set_editor_property('dog', True)
        d.set_flag('perro_amigo')
        d.set_day(True)
        poner(w, 4950, 6000, 120)
        yield from juego(2.0)
        d.dog_forget_pets()
        l = d.dog_location()
        gs = [g for g in guardias(w) if not g.get_editor_property('tower_sentry') and estado(g) == 'PATROL']
        if gs:
            g = gs[-1]
            g.hold(0.0)
            g.set_actor_location(V(l.x - 260, l.y + 60, g.get_actor_location().z), False, True)
            hechas = 0
            for i in range(40):
                yield from juego(0.4)
                pt = d.dog_petter()
                if pt and pt.pet_crouched() and pt.pet_hand_weight() > 0.9 and hechas < 2:
                    dl = d.dog_location(); gl = pt.get_actor_location()
                    sx, sy = dl.x - gl.x, dl.y - gl.y
                    nn = max(1.0, math.hypot(sx, sy))
                    poner(w, (dl.x + gl.x) / 2 - sy / nn * 230, (dl.y + gl.y) / 2 + sx / nn * 230, dl.z + 110)
                    yield from juego(0.15)
                    mirar(w, gl, 30.0)
                    yield 0.1
                    foto(w, 'caricia_fusil_espalda_%d' % hechas, 'fusil a la espalda %s' % pt.rifle_on_back())
                    hechas += 1
                if hechas >= 2:
                    break
        recoger()
        d.set_editor_property('dog', False)
    if 'levantarse' in ESCENAS:
        for x in guardias(w):
            x.hold(600.0)
        d.set_day(True)
        g = [x for x in ronda if estado(x) == 'PATROL'][0]
        l = g.get_actor_location(); f = g.get_actor_forward_vector(); r = g.get_actor_right_vector()
        # un lado con la vista despejada hasta el guardia (a la derecha habia un muro)
        pc0 = l + V(0, 0, 40)
        sitio = None
        for v in (r, r * -1.0, f, f * -1.0):
            cand = V(l.x + v.x * 360, l.y + v.y * 360, l.z + 40)
            if unreal.SystemLibrary.line_trace_single(w, pc0, cand, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [g, p], unreal.DrawDebugTrace.NONE, True) is None:
                sitio = cand
                break
        sitio = sitio or V(l.x + r.x * 360, l.y + r.y * 360, l.z + 40)
        poner(w, sitio.x, sitio.y, sitio.z)
        yield from juego(0.3)
        mirar(w, l, -30.0)
        g.set_editor_property('knock_out_time', 100.0)
        g.dart_hit(V(-r.x, -r.y, 0)); g.knock_out()
        yield from juego(4.0)
        mirar(w, g.pelvis_location(), 0.0)
        g.wake_now()
        unreal.SystemLibrary.execute_console_command(w, 'slomo 0.3')
        for i in range(10):
            yield from juego(0.06)
            mirar(w, g.get_actor_location(), -20.0)
            foto(w, 'levantarse_%02d' % i, 'boca %s, agachado %s, mezclando %s' % ('arriba' if g.last_face_up() else 'abajo', g.get_editor_property('is_crouched'), g.wake_blending()))
        unreal.SystemLibrary.execute_console_command(w, 'slomo 1')
        recoger()
    if 'arrastre' in ESCENAS:
        for x in guardias(w):
            x.hold(600.0)
        d.set_day(True)
        g = [x for x in ronda if estado(x) == 'PATROL'][-1]
        camg = [x for x in ronda if x != g][0]
        g.set_editor_property('knock_out_time', 200.0)
        sl = sitio_libre(w, d, [g, p], 200, 1400)
        c, yaw, f = sl if sl else (V(4300, 3500, 0), 0, V(1, 0, 0))
        S['L'].append('arrastre en (%.0f, %.0f) rumbo %d' % (c.x, c.y, yaw))
        poner(w, c.x - f.x * 100, c.y - f.y * 100, c.z + 120)
        g.set_actor_location(V(c.x, c.y, c.z + 95), False, True)
        yield 0.3
        g.knock_out()
        yield from juego(3.0)
        pl = g.pelvis_location()
        poner(w, pl.x + 90, pl.y, 120)
        yield 0.3
        d.interact()
        yield from juego(0.3)
        S['L'].append('arrastre con fisica: %s' % d.drag_physics())
        s0 = p.get_actor_location()
        q = V(-f.y, f.x, 0)
        for dist in (1000, 2000, 3000):
            mid = V(s0.x + f.x * 300, s0.y + f.y * 300, s0.z)
            cam = camara(w, V(mid.x - q.x * dist, mid.y - q.y * dist, s0.z + 150 + dist * 0.06), mid, camg)
            for i in range(14):
                p.set_actor_location(V(s0.x + f.x * 25 * (i + 1), s0.y + f.y * 25 * (i + 1), s0.z), True, False)
                pc.set_control_rotation(unreal.Rotator(0, 0, yaw))
                yield from juego(0.1)
            foto(w, 'arrastre_%dm' % (dist // 100), 'fisica %s, pelvis a %.0f cm del suelo' % (d.drag_physics(), g.pelvis_location().z - (p.get_actor_location().z - 90)))
            yield from juego(0.3)
            s0 = p.get_actor_location()
        pc.set_view_target_with_blend(p, 0.0)
        camg.set_actor_hidden_in_game(False)
        d.interact()
        recoger()
    d.set_day(False)


def _fin():
    w = mundo()
    try:
        director(w).set_day(False)
    except Exception:
        pass
    unreal.SystemLibrary.execute_console_command(w, 'slomo 1')
    try:
        recoger()
    except Exception:
        pass
    with open(os.path.join(OUT, 'tandaD_medidas.txt'), 'w', encoding='utf-8') as f:
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
