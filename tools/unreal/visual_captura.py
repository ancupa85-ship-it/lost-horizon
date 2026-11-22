"""Tanda A, novena: la detencion nueva, en PIE de dia en el patio. Cuatro casos: rendido y a golpes, en primera y en
tercera persona. Un guardia se pone delante de Cuttlas y le coge (TestCapture). En cada fotograma de la escena se apunta
el tiempo, los fps, el tipo y la pareja, si ya cae con fisica, si el guardia esta agachado, si sonaron las esposas, lo
borrosa que esta la vista y la altura de la camara; y con fotos (builtins._captura_fotos = True, por defecto) una captura
cada 1/10 s de juego, con el juego a camara lenta (slomo 0.1) mientras se hacen.
Capturas en D:\\LostHorizon\\capturas-gaspA\\captura\\<caso>_NN_t<s>.png y la serie en captura_medidas.txt."""
import builtins, glob, math, os, shutil, time
import unreal

OUT = getattr(builtins, '_captura_out', r'D:\LostHorizon\capturas-gaspA\captura')
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
V = unreal.Vector
FOTOS = getattr(builtins, '_captura_fotos', True)
CASOS = getattr(builtins, '_captura_casos', [('rendido_1p', False, False), ('rendido_3p', False, True), ('golpe_1p', True, False), ('golpe_3p', True, True)])
S = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'L': [], 'caso': None, 'gt0': 0.0, 'ult': -1.0, 'n': 0,
     'pedidas': [], 'antes': set(), 'blur': None, 'dts': [], 'resumen': []}
builtins._visual_captura = S


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def director(w):
    return unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector'))[0]


def guardias(w):
    return unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard'))


def fila(w):
    d = director(w)
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    cm = unreal.GameplayStatics.get_player_camera_manager(w, 0)
    g = S['g']
    gt = unreal.GameplayStatics.get_time_seconds(w) - S['gt0']
    dt = unreal.GameplayStatics.get_world_delta_seconds(w) / max(1e-6, unreal.GameplayStatics.get_global_time_dilation(w))
    S['dts'].append(dt)
    S['L'].append('%s f=%03d t=%.3f fps=%.0f tipo=%d pareja=%s cae=%s agachado=%s esposas=%s borroso=%.2f cam_z=%.0f capturas=%d' % (
        S['caso'], S['n'], gt, 1.0 / max(dt, 1e-4), d.capture_scene_kind(), d.capture_scene_pair(), d.capture_scene_ragdoll(),
        g.get_editor_property('is_crouched'), d.capture_scene_cuffed(), d.capture_blur(), cm.get_camera_location().z,
        d.get_editor_property('captures')))
    if FOTOS and gt - S['ult'] >= 0.1 - 1e-4:
        S['ult'] = gt
        unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1280x720')
        S['pedidas'].append('%s_%03d_t%.2f' % (S['caso'], len(S['pedidas']) + S['base'], gt))
    S['n'] += 1


def recoger():
    nuevas = sorted(set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True)) - S['antes'], key=os.path.getmtime)
    for f, nombre in zip(nuevas, S['pedidas']):
        shutil.move(f, os.path.join(OUT, nombre + '.png'))
    S['base'] += len(S['pedidas'])
    S['antes'] = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
    S['pedidas'] = []


def pasos():
    w = mundo()
    d = director(w)
    if d.get_editor_property('cine'):
        d.interact()
    yield 2.0
    d.set_day(True)
    unreal.SystemLibrary.execute_console_command(w, 'showhud')
    S['blur'] = unreal.SystemLibrary.get_console_variable_int_value('r.MotionBlurQuality')
    unreal.SystemLibrary.execute_console_command(w, 'r.MotionBlurQuality 0')
    os.makedirs(OUT, exist_ok=True)
    S['antes'] = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    gs = [g for g in guardias(w) if not g.get_editor_property('tower_sentry') and g.uses_gasp()]
    for g in guardias(w):
        g.set_editor_property('view_distance', 1.0)
    for i, (caso, golpe, tercera) in enumerate(CASOS):
        g = gs[i % len(gs)]
        S['g'] = g
        for x in guardias(w):
            x.hold(600.0)
        INICIO = V(4300, 3500, 120)
        p.set_actor_location(INICIO, False, True)
        pc.set_control_rotation(unreal.Rotator(0.0, -6.0, 15.0))
        if d.third_now() != tercera:
            d.toggle_third()
        yield 1.0
        # el guardia delante, un poco a la izquierda, mirando a Cuttlas
        f = p.get_actor_forward_vector(); r = p.get_actor_right_vector(); l = p.get_actor_location()
        gl = V(l.x + f.x * 170 - r.x * 40, l.y + f.y * 170 - r.y * 40, g.get_actor_location().z)
        g.set_actor_location(V(gl.x, gl.y, l.z), False, True)
        g.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(gl, l), False)
        yield 1.5
        c0 = d.get_editor_property('captures')
        S['caso'] = caso; S['n'] = 0; S['ult'] = -1.0; S['dts'] = []; S['base'] = 0
        if FOTOS:
            unreal.SystemLibrary.execute_console_command(w, 'slomo 0.1')
        S['gt0'] = unreal.GameplayStatics.get_time_seconds(w)
        d.test_capture(g, golpe)
        while d.get_editor_property('capturing'):
            yield 0.05
            if FOTOS and len(S['pedidas']) > 0 and S['n'] % 40 == 0:
                pass
        S['caso'] = None
        unreal.SystemLibrary.execute_console_command(w, 'slomo 1')
        yield 1.5
        recoger()
        dts = sorted(S['dts'])
        if dts:
            S['resumen'].append('%s: %d fotogramas, %.1f fps de media, peor 1 %% %.1f fps, capturas %d -> %d' % (
                caso, len(dts), len(dts) / sum(dts), 1.0 / dts[max(0, int(len(dts) * 0.99) - 1)], c0, d.get_editor_property('captures')))
    if d.third_now():
        d.toggle_third()


def _fin():
    w = mundo()
    try:
        director(w).set_day(False)
    except Exception:
        pass
    unreal.SystemLibrary.execute_console_command(w, 'slomo 1')
    if S.get('blur') is not None:
        unreal.SystemLibrary.execute_console_command(w, 'r.MotionBlurQuality %d' % S['blur'])
    try:
        recoger()
    except Exception:
        pass
    with open(os.path.join(os.path.dirname(OUT), 'captura_medidas%s.txt' % ('' if FOTOS else '_sin_fotos')), 'w', encoding='utf-8') as f:
        f.write('\n'.join(S['resumen'] + [''] + S['L'] + ['estado: %s' % S['estado']]))


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
        if S['caso']:
            fila(w)
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
