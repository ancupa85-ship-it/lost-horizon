"""Tanda G (cabecera de visual_tandaF): fotos en PIE de un cuerpo metido en un cajon, las latas y el cable, y lo que se mueve la mira al apuntar (en las medidas). Escenas: builtins._tandaG_escenas."""
import builtins, glob, math, os, shutil, time
import unreal

OUT = getattr(builtins, '_tandaG_out', r'D:\LostHorizon\capturas-tandaG')
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
V = unreal.Vector
ESCENAS = getattr(builtins, '_tandaG_escenas', ['escondido', 'trampas', 'pulso'])
S = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'L': [], 'pedidas': [], 'antes': set()}
builtins._visual_tandaG = S


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
    gs = [g for g in guardias(w) if not g.get_editor_property('tower_sentry') and not g.get_actor_label().endswith('Ramos')]
    for g in guardias(w):
        g.hold(900.0)
    yield 4.0
    unreal.SystemLibrary.execute_console_command(w, 'showhud')
    os.makedirs(OUT, exist_ok=True)
    S['antes'] = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
    d.set_day(True)
    pj = lambda: unreal.GameplayStatics.get_player_pawn(w, 0)
    def agachado(si=True):
        if bool(pj().get_editor_property('is_crouched')) != si:
            d.simulate_key('C')
    def toma(nombre, pos, mira, nota='', alto=0.0):
        poner(w, pos[0], pos[1], pos[2])
        yield from juego(0.4)
        mirar(w, V(*mira), alto)
        yield from juego(0.5)
        foto(w, nombre, nota)
        yield from juego(0.4)
    if 'escondido' in ESCENAS:
        g = gs[2]
        nh = len(d.get_editor_property('hide_spots'))
        L = d.stash_slot_loc(nh)
        g.set_actor_location(V(L.x + 40, L.y + 60, 100), False, True)
        yield from juego(0.3)
        g.set_editor_property('knock_out_time', 300.0)
        g.knock_out()
        yield from juego(2.5)
        l = g.get_actor_location()
        poner(w, l.x + 60, l.y, 100)
        yield from juego(0.3)
        d.interact()
        yield from juego(0.3)
        poner(w, L.x, L.y + 30, 100)
        yield from juego(0.4)
        mirar(w, V(L.x, L.y, 40))
        yield from juego(0.4)
        foto(w, 'escondido_aviso', str(d.interact_prompt()))
        d.interact()
        yield from juego(1.2)
        foto(w, 'escondido_metiendo', str(d.interact_prompt()))
        yield from juego(d.get_editor_property('stash_seconds'))
        yield from toma('escondido_dentro', (L.x + 260, L.y + 200, 160), (L.x, L.y, 40), 'dentro: %s' % g.get_editor_property('stashed'))
        recoger()
    if 'trampas' in ESCENAS:
        d.set_editor_property('trap_cans', 2); d.set_editor_property('trap_wires', 1)
        poner(w, 4300, 3950, 100)
        yield from juego(0.3)
        mirar(w, V(4500, 3950, 0))
        agachado()
        yield from juego(0.5)
        foto(w, 'latas_aviso', str(d.interact_prompt()))
        d.interact()
        yield from juego(0.4)
        agachado(False)
        yield from toma('latas', (4180, 3870, 140), (4370, 3950, 10), 'latas en su alambre')
        poner(w, -1050, 820, 100)
        yield from juego(0.3)
        mirar(w, V(-1050, 1000, 20))
        agachado()
        yield from juego(0.5)
        foto(w, 'cable_aviso', str(d.interact_prompt()))
        d.interact()
        yield from juego(0.4)
        agachado(False)
        yield from toma('cable', (-1050, 700, 150), (-1050, 890, 10), 'cable de pared a pared')
        d.set_day(False)
        yield from toma('cable_noche', (-1050, 700, 150), (-1050, 890, 10), 'de noche')
        d.set_day(True)
        recoger()
    if 'pulso' in ESCENAS:
        # la mira apuntando: la deriva en 2 s, en calma y tras correr (en las medidas)
        d.set_darts(max(1, d.get_editor_property('darts')))
        poner(w, 4300, 3950, 100)
        yield from juego(0.3)
        mirar(w, V(5300, 3950, 120))
        d.set_editor_property('aim_held', True)
        yield from juego(1.0)
        foto(w, 'apuntando', 'amplitud %.2f' % d.aim_sway())
        for nombre, ex in (('calma', 0.0), ('tras_correr', 1.0)):
            d.set_editor_property('exertion', ex)
            yield from juego(1.5)
            pc = unreal.GameplayStatics.get_player_controller(w, 0)
            r0 = pc.get_control_rotation(); m = 0.0
            for i in range(40):
                yield from juego(0.05)
                r = pc.get_control_rotation()
                m = max(m, abs(r.yaw - r0.yaw) + abs(r.pitch - r0.pitch))
            S['L'].append('pulso %s: la mira se mueve %.2f grados en 2 s (amplitud %.2f)' % (nombre, m, d.aim_sway()))
        d.set_editor_property('exertion', 0.0)
        d.set_editor_property('aim_held', False)
        recoger()


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
    with open(os.path.join(OUT, 'tandaG_medidas.txt'), 'w', encoding='utf-8') as f:
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
