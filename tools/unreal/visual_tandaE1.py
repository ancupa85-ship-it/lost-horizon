"""Tanda E1 (copia de la cabecera de visual_tandaD): fotos del relleno, en PIE. Escenas (builtins._tandaD_escenas): rastro (de noche: pisadas mojadas que salen
de un charco y un guardia que las sigue con la linterna), relevo (al pie de una torre: la charla y el relevo subiendo),
caricia (con el fusil a la espalda), levantarse (de la fisica a agachado y de pie) y arrastre (visto desde 10, 20 y 30 m
con una camara fija). Espera en tiempo de JUEGO y con el codec y las charlas apagados.
Capturas en D:\\LostHorizon\\capturas-tandaD\\<escena>_NN.png y lo medido en tandaD_medidas.txt."""
import builtins, glob, math, os, shutil, time
import unreal

OUT = getattr(builtins, '_tandaE1_out', r'D:\LostHorizon\capturas-tandaE1')
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
V = unreal.Vector
ESCENAS = getattr(builtins, '_tandaE1_escenas', ['hangar', 'enfermeria', 'plaza'])
S = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'L': [], 'pedidas': [], 'antes': set()}
builtins._visual_tandaE1 = S


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
    """Hangar de noche (con su luz y con la linterna, sin la bombilla), enfermería, puerta fría y plaza de día y de noche."""
    w = mundo()
    d = director(w)
    if d.get_editor_property('cine'):
        d.interact()
    for k in ('codec_calls', 'radio_chat', 'talk_rule', 'talk_cross', 'truck'):
        try:
            d.set_editor_property(k, False)
        except Exception:
            pass
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
    if 'hangar' in ESCENAS:
        yield from toma('hangar_noche_taller', (5560, 6420, 100), (4300, 7000, 60), 'bombilla del hangar y lámpara del banco')
        yield from toma('hangar_noche_cajas_lh', (4700, 6750, 100), (4300, 6990, 30), 'cajas LH junto a la trampilla')
        yield from toma('hangar_noche_santana', (4650, 6500, 100), (5200, 7000, 40), 'Santana provisional bajo lona, rueda fuera')
        # con la linterna: la bombilla del hangar apagada
        bombilla = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PointLight) if a.get_actor_label() in ('hangar_25', 'Relleno_Lampara_banco')]
        for b in bombilla:
            b.light_component.set_visibility(False)
        d.set_torch(True)
        yield from toma('hangar_linterna_cajas', (4650, 6800, 100), (4300, 6960, 25), 'solo la linterna')
        yield from toma('hangar_linterna_taller', (4500, 6650, 100), (4060, 6950, 140), 'solo la linterna: tablón y herramientas')
        d.set_torch(False)
        for b in bombilla:
            b.light_component.set_visibility(True)
        recoger()
    if 'enfermeria' in ESCENAS:
        yield from toma('enfermeria_fuera', (7560, 4150, 100), (7560, 3550, 150), 'la puerta y el rótulo')
        yield from toma('enfermeria_dentro', (7520, 3420, 100), (7700, 2850, 60), 'camillas, biombo, fluorescentes')
        yield from toma('enfermeria_mesa', (7650, 3250, 100), (7800, 3420, 75), 'mesa con las fichas')
        yield from toma('puerta_fria', (7880, 3160, 100), (8140, 3105, 100), 'cámara frigorífica con candado y escarcha')
        recoger()
    if 'plaza' in ESCENAS:
        yield from toma('plaza_noche', (6950, 3700, 100), (8000, 4300, 250), 'mástil, sacos, camión')
        d.set_day(True)
        yield from juego(1.5)
        yield from toma('plaza_dia', (6950, 3700, 100), (8000, 4300, 250), 'de día')
        yield from toma('plaza_dia_bandera', (7500, 3750, 100), (7950, 4200, 820), 'la bandera ondeando')
        yield from toma('plaza_dia_tejadillo', (8300, 3500, 100), (8750, 3800, 120), 'tejadillo y sacos')
        d.set_day(False)
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
    with open(os.path.join(OUT, 'tandaE1_medidas.txt'), 'w', encoding='utf-8') as f:
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
