"""Tanda A, octava: el corte al agacharse en tercera persona. PIE de dia, Cuttlas en tercera; parado y andando, pulsa la C
(agacharse) y otra vez (levantarse). Durante 1 s de juego tras cada pulsacion, en cada fotograma: altura de la camara, de
la pelvis y del pie mas bajo de CuerpoCuttlas, y lo que la camara esta bajada por agacharse; y una captura cada 1/30 s de
juego. Capturar para el juego un momento, asi que durante las fotos el juego va a camara lenta (slomo 0.1) y el tiempo
que se apunta es el del juego.
Capturas en D:\\LostHorizon\\capturas-gaspA\\agachar\\<caso>_<nn>.png y la serie en agachar_medidas.txt.
Con builtins._agachar_sin_fotos = True solo mide."""
import builtins, glob, os, shutil, time
import unreal

OUT = r'D:\LostHorizon\capturas-gaspA\agachar'
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
V = unreal.Vector
S = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'L': [], 'caso': None, 't0': 0.0, 'n': 0,
     'andar': False, 'gt0': 0.0, 'gt': 0.0, 'ult': -1.0, 'fotos': not getattr(builtins, '_agachar_sin_fotos', False), 'blur': None, 'pedidas': [], 'antes': set()}
builtins._visual_agachar = S


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def director(w):
    return unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector'))[0]


def cuerpo(p):
    for c in p.get_components_by_class(unreal.SkeletalMeshComponent):
        if c.get_name().startswith('CuerpoCuttlas'):
            return c
    return None


def fila(w):
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    cm = unreal.GameplayStatics.get_player_camera_manager(w, 0)
    b = cuerpo(p)
    d = director(w)
    try:
        baja = d.crouch_cam_offset()
    except Exception:
        baja = None
    S['L'].append('%s f=%02d t=%.3f cam=%.1f pelvis=%.1f pie=%.1f capsula_base=%.1f bajada_cam=%s agachado=%s vel=%.0f' % (
        S['caso'], S['n'], S['gt'], cm.get_camera_location().z, b.get_socket_location('pelvis').z if b else 0,
        min(b.get_socket_location('ball_l').z, b.get_socket_location('ball_r').z) if b else 0,
        p.get_actor_location().z - p.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height(),
        None if baja is None else round(baja, 1), p.get_editor_property('is_crouched'), p.get_velocity().length()))
    if S['fotos'] and S['gt'] - S['ult'] >= 1.0 / 30.0 - 1e-4:
        S['ult'] = S['gt']
        unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1280x720')
        S['pedidas'].append('%s_%02d' % (S['caso'], S['n']))
    S['n'] += 1


def recoger():
    # las capturas salen en Saved/Screenshots en el orden en que se pidieron (una por vez, el juego a camara lenta)
    nuevas = sorted(set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True)) - S['antes'], key=os.path.getmtime)
    for f, nombre in zip(nuevas, S['pedidas']):
        shutil.move(f, os.path.join(OUT, nombre + '.png'))
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
    unreal.SystemLibrary.execute_console_command(w, 't.MaxFPS 30')
    for g in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard')):
        g.set_editor_property('view_distance', 1.0)
        g.hold(600.0)
    os.makedirs(OUT, exist_ok=True)
    S['antes'] = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    pc = unreal.GameplayStatics.get_player_controller(w, 0)
    d.toggle_third()
    for andar in (False, True):
        p.set_actor_location(V(4300, 3500, 120), False, True)
        pc.set_control_rotation(unreal.Rotator(0.0, -8.0, 15.0))
        p.get_editor_property('character_movement').set_editor_property('max_walk_speed', 300.0)
        S['andar'] = andar
        yield 2.0
        for et in ('agacharse', 'levantarse'):
            S['caso'] = '%s_%s' % (et, 'andando' if andar else 'parado')
            S['n'] = 0
            S['ult'] = -1.0
            if S['fotos']:
                unreal.SystemLibrary.execute_console_command(w, 'slomo 0.1')
            S['gt0'] = unreal.GameplayStatics.get_time_seconds(w) + 0.1   # la C se pulsa en t = 0
            yield 1.0 if S['fotos'] else 0.1
            d.simulate_key('C', True, True)
            while unreal.GameplayStatics.get_time_seconds(w) - S['gt0'] < 1.0:
                yield 0.05
            S['caso'] = None
            yield 0.5   # la ultima captura pedida
            unreal.SystemLibrary.execute_console_command(w, 'slomo 1')
            yield 1.2
            recoger()
        S['andar'] = False
        yield 0.5
    p.get_editor_property('character_movement').set_editor_property('max_walk_speed', 600.0)
    d.toggle_third()
    yield 1.0
    recoger()


def _fin():
    w = mundo()
    try:
        director(w).set_day(False)
    except Exception:
        pass
    unreal.SystemLibrary.execute_console_command(w, 't.MaxFPS 0')
    unreal.SystemLibrary.execute_console_command(w, 'slomo 1')
    if S.get('blur') is not None:
        unreal.SystemLibrary.execute_console_command(w, 'r.MotionBlurQuality %d' % S['blur'])
    recoger()
    with open(os.path.join(os.path.dirname(OUT), 'agachar_medidas.txt'), 'w', encoding='utf-8') as f:
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
        if S['andar']:
            p = unreal.GameplayStatics.get_player_pawn(w, 0)
            p.add_movement_input(p.get_actor_forward_vector(), 1.0, False)
        if S['caso']:
            S['gt'] = unreal.GameplayStatics.get_time_seconds(w) - S['gt0']
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
