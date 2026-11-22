"""Tanda E2 (cabecera de visual_tandaE1): fotos de los cruces, el anillo exterior y la capilla, en PIE. Escenas (builtins._tandaD_escenas): rastro (de noche: pisadas mojadas que salen
de un charco y un guardia que las sigue con la linterna), relevo (al pie de una torre: la charla y el relevo subiendo),
caricia (con el fusil a la espalda), levantarse (de la fisica a agachado y de pie) y arrastre (visto desde 10, 20 y 30 m
con una camara fija). Espera en tiempo de JUEGO y con el codec y las charlas apagados.
Capturas en D:\\LostHorizon\\capturas-tandaD\\<escena>_NN.png y lo medido en tandaD_medidas.txt."""
import builtins, glob, math, os, shutil, time
import unreal

OUT = getattr(builtins, '_tandaE2_out', r'D:\LostHorizon\capturas-tandaE2')
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
V = unreal.Vector
ESCENAS = getattr(builtins, '_tandaE2_escenas', ['cruces', 'anillo', 'capilla'])
S = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'L': [], 'pedidas': [], 'antes': set()}
builtins._visual_tandaE2 = S


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
    """Dos guardias cruzándose (pasillo de la pista y patio), cada zona del anillo de noche y la capilla."""
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
    d.set_day(False)
    def toma(nombre, pos, mira, nota='', alto=0.0):
        poner(w, pos[0], pos[1], pos[2])
        yield from juego(0.4)
        mirar(w, V(*mira), alto)
        yield from juego(0.5)
        foto(w, nombre, nota)
        yield from juego(0.4)
    if 'cruces' in ESCENAS:
        a, b = gs[0], gs[1]
        for sitio, pa, pb, cam, mira in (('pasillo', (-1050, 350), (-1050, 1450), (-1050, 1700, 200), (-1050, 900, 60)),
                                          ('patio', (4500, 3950), (6300, 3950), (5400, 3500, 160), (5400, 3950, 80))):
            d.set_day(True)
            a.set_actor_location(V(pa[0], pa[1], 100), False, True); b.set_actor_location(V(pb[0], pb[1], 100), False, True)
            a.hold(0.0); b.hold(0.0)
            a.errand(V(pb[0], pb[1], 100), V(pb[0], pb[1] + 1, 100), 40.0); b.errand(V(pa[0], pa[1], 100), V(pa[0], pa[1] + 1, 100), 40.0)
            hechas, dmin = 0, 1e9
            for i in range(160):
                yield from juego(0.1)
                dd = math.hypot(a.get_actor_location().x - b.get_actor_location().x, a.get_actor_location().y - b.get_actor_location().y)
                dmin = min(dmin, dd)
                if dd < 260 and hechas < 3 and i % 4 == 0:
                    poner(w, cam[0], cam[1], cam[2])
                    yield 0.05
                    mirar(w, V((a.get_actor_location().x + b.get_actor_location().x) / 2, (a.get_actor_location().y + b.get_actor_location().y) / 2, 60), 0.0)
                    yield 0.05
                    foto(w, 'cruce_%s_%d' % (sitio, hechas), 'a %.0f cm; cede %s/%s' % (dd, a.is_yielding(), b.is_yielding()))
                    hechas += 1
            S['L'].append('cruce %s: distancia mínima %.0f cm, cesiones %d + %d' % (sitio, dmin, a.get_editor_property('yields'), b.get_editor_property('yields')))
            a.hold(900.0); b.hold(900.0)
        d.set_day(False)
        recoger()
    if 'anillo' in ESCENAS:
        yield from toma('anillo_norte_gasoil_antena', (3300, -300, 100), (1500, -1100, 400), 'depósito de gasoil y antena con vientos')
        yield from toma('anillo_norte_nido', (3300, -700, 100), (2800, -1250, 40), 'nido de ametralladora abandonado')
        yield from toma('anillo_oeste_tiro', (-300, 3000, 100), (-1650, 3700, 120), 'campo de tiro')
        yield from toma('anillo_oeste_pista', (-300, 700, 100), (-1050, 1000, 80), 'pista de obstáculos y pasillo de tablones')
        yield from toma('anillo_este_agua_gallinero', (7300, 1700, 100), (8100, 500, 250), 'depósito de agua, gallinero y huerto')
        yield from toma('anillo_este_desguace', (7700, 2100, 100), (8650, 1800, 120), 'desguace')
        recoger()
    if 'capilla' in ESCENAS:
        yield from toma('capilla_fuera', (6400, -500, 100), (6400, -950, 220), 'la puerta y la espadaña')
        yield from toma('capilla_dentro', (6400, -1020, 100), (6400, -1500, 120), 'velas, altar y crucifijo')
        yield from toma('capilla_libro', (6480, -1250, 100), (6570, -1370, 105), 'el libro de difuntos en el atril')
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
    with open(os.path.join(OUT, 'tandaE2_medidas.txt'), 'w', encoding='utf-8') as f:
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
