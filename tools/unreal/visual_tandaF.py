"""Tanda F (cabecera de visual_tandaE2): fotos en PIE del pasillo de tablones (el que cede vuelve atrás y espera; los
dos con el fusil bajado al cruzarse), la antena (cable sano y cortado), la llave del gasoil abierta (chorro y charco) y
el huerto. Escenas: builtins._tandaF_escenas. Capturas en D:\LostHorizon\capturas-tandaF y lo medido en tandaF_medidas.txt."""
import builtins, glob, math, os, shutil, time
import unreal

OUT = getattr(builtins, '_tandaF_out', r'D:\LostHorizon\capturas-tandaF')
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
V = unreal.Vector
ESCENAS = getattr(builtins, '_tandaF_escenas', ['pasillo', 'sabotaje', 'huerto'])
S = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'L': [], 'pedidas': [], 'antes': set()}
builtins._visual_tandaF = S


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
    def toma(nombre, pos, mira, nota='', alto=0.0):
        poner(w, pos[0], pos[1], pos[2])
        yield from juego(0.4)
        mirar(w, V(*mira), alto)
        yield from juego(0.5)
        foto(w, nombre, nota)
        yield from juego(0.4)
    if 'pasillo' in ESCENAS:
        a, b = gs[0], gs[1]
        pa, pb = (-1050, 350), (-1050, 1450)
        a.set_actor_location(V(pa[0], pa[1], 100), False, True); b.set_actor_location(V(pb[0], pb[1], 100), False, True)
        a.hold(0.0); b.hold(0.0)
        a.errand(V(pb[0], pb[1], 100), V(pb[0], pb[1] + 1, 100), 40.0); b.errand(V(pa[0], pa[1], 100), V(pa[0], pa[1] + 1, 100), 40.0)
        hechas, ultima, dmin, tuck = 0, -10.0, 1e9, 0.0
        t = 0.0
        while t < 30.0 and hechas < 6:
            yield from juego(0.1)
            t += 0.1
            la, lb = a.get_actor_location(), b.get_actor_location()
            dd = math.hypot(la.x - lb.x, la.y - lb.y)
            dmin = min(dmin, dd)
            tuck = max(tuck, min(a.rifle_tuck(), b.rifle_tuck()))
            if dd < 420 and t - ultima > 1.6:
                ultima = t
                poner(w, -1050, (la.y + lb.y) / 2 + 380, 460)
                yield 0.05
                mirar(w, V(-1050, (la.y + lb.y) / 2, 60), 0.0)
                yield 0.05
                foto(w, 'pasillo_%d' % hechas, 'a %.0f cm; atrás %s/%s; cede %s/%s; fusil bajado %.2f/%.2f' % (dd, a.is_backing_out(), b.is_backing_out(), a.is_yielding(), b.is_yielding(), a.rifle_tuck(), b.rifle_tuck()))
                hechas += 1
        S['L'].append('pasillo: distancia mínima %.0f cm, vueltas atrás %d + %d, fusil bajado máx %.2f' % (dmin, a.get_editor_property('back_outs'), b.get_editor_property('back_outs'), tuck))
        # los fusiles de cerca: dos guardias juntos en el patio
        a.hold(900.0); b.hold(900.0)
        a.set_actor_location(V(5400, 3950, 100), False, True); b.set_actor_location(V(5400, 4080, 100), False, True)
        a.set_actor_rotation(unreal.Rotator(0, 0, 0), False); b.set_actor_rotation(unreal.Rotator(0, 0, 180), False)
        yield from juego(1.5)
        yield from toma('fusiles_juntos', (5650, 4015, 150), (5400, 4015, 110), 'dos juntos: fusil bajado %.2f/%.2f' % (a.rifle_tuck(), b.rifle_tuck()))
        b.set_actor_location(V(5400, 4500, 100), False, True)
        yield from juego(1.5)
        yield from toma('fusil_solo', (5650, 3950, 150), (5400, 3950, 110), 'solo: fusil bajado %.2f' % a.rifle_tuck())
        recoger()
    if 'sabotaje' in ESCENAS:
        an = d.get_editor_property('antenna_loc')
        yield from toma('antena_sana', (an.x + 150, an.y + 260, 100), (an.x, an.y, 100), 'caja de empalme y cable sano')
        poner(w, an.x, an.y + 110, 100)
        yield from juego(0.3)
        mirar(w, V(an.x, an.y, 100))
        d.interact()
        yield from juego(1.8)
        foto(w, 'antena_cortando', str(d.interact_prompt()))
        yield from juego(d.get_editor_property('antenna_cut_seconds'))
        yield from juego(0.5)
        yield from toma('antena_cortada', (an.x + 150, an.y + 260, 100), (an.x, an.y, 80), 'cortado: %s' % d.antenna_cut())
        va = d.get_editor_property('valve_loc')
        poner(w, va.x + 40, va.y, 100)
        yield from juego(0.3)
        mirar(w, V(va.x - 30, va.y, 60))
        d.interact()
        yield from juego(d.get_editor_property('valve_open_seconds') + 0.6)
        yield from toma('gasoil_abierto', (va.x + 330, va.y + 230, 120), (va.x, va.y, 30), 'abierto: %s' % d.valve_open())
        d.set_day(False)
        yield from toma('gasoil_noche', (va.x + 330, va.y + 230, 120), (va.x, va.y, 30), 'de noche')
        d.set_day(True)
        recoger()
    if 'huerto' in ESCENAS:
        yield from toma('huerto', (7400, 1000, 160), (7850, 1500, 0), 'tierra labrada y matas')
        yield from toma('huerto_cerca', (7600, 1300, 120), (7800, 1420, 0), 'de cerca')
        d.set_day(False)
        yield from toma('huerto_noche', (7400, 1000, 160), (7850, 1500, 0), 'de noche')
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
    with open(os.path.join(OUT, 'tandaF_medidas.txt'), 'w', encoding='utf-8') as f:
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
