"""Capturas desde cámaras fijas del nivel Tarsis (para comparar antes y después de un cambio de aspecto).

Uso (en el editor): py tools/unreal/capturas.py [prefijo]
Abre el PIE, salta la entrada, quita el HUD, para y oculta a los guardias y, desde cada cámara de CAMARAS, espera a que se
asiente la imagen y hace un HighResShot de 1920x1080. Las imágenes quedan en Saved/Capturas/<prefijo>_<cámara>.png.
"""
import builtins, glob, os, shutil, sys, time
import unreal

V = unreal.Vector
# nombre: (posición del jugador, punto al que mira). La cámara va unos 60 cm por encima de la posición.
CAMARAS = [
    ('interior', V(2080, 2620, 110), V(300, 2760, 90)),
    ('puerta', V(1750, 1250, 110), V(1300, 2050, 160)),
    ('patio', V(3000, 450, 110), V(900, 2000, 60)),
]
PREFIJO = sys.argv[1] if len(sys.argv) > 1 else time.strftime('%H%M%S')
OUT = os.path.join(unreal.Paths.project_saved_dir(), 'Capturas')
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
C = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'hechas': []}
builtins._tarsis_capturas = C


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def pasos():
    w = mundo()
    d = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector'))[0]
    if d.get_editor_property('cine'):
        d.interact()
    yield 1.5
    unreal.SystemLibrary.execute_console_command(w, 'showhud')   # sin HUD en las capturas
    gcls = unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard')
    os.makedirs(OUT, exist_ok=True)
    for nombre, pos, mira in CAMARAS:
        for g in unreal.GameplayStatics.get_all_actors_of_class(w, gcls):
            g.hold(30.0)
            g.set_actor_hidden_in_game(True)   # que nadie se cuele en el plano
        p = unreal.GameplayStatics.get_player_pawn(w, 0)
        p.set_actor_location(pos, False, True)
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        cam = p.get_component_by_class(unreal.CameraComponent).get_world_location()
        pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cam, mira))
        yield 3.0   # exposición y sombras asentadas
        antes = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
        unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1920x1080')
        yield 3.0
        nuevas = sorted(set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True)) - antes, key=os.path.getmtime)
        if nuevas:
            destino = os.path.join(OUT, '%s_%s.png' % (PREFIJO, nombre))
            shutil.move(nuevas[-1], destino)
            C['hechas'].append(destino)


def _tick(dt):
    try:
        w = mundo()
        if C['estado'] == 'arrancando':
            if w and unreal.GameplayStatics.get_player_pawn(w, 0):
                C['estado'] = 'capturando'
                C['gen'] = pasos()
            return
        if C['estado'] != 'capturando' or time.time() < C['espera']:
            return
        try:
            C['espera'] = time.time() + next(C['gen'])
        except StopIteration:
            C['estado'] = 'terminado'
            unreal.unregister_slate_post_tick_callback(C['h'])
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    except Exception as ex:
        C['estado'] = 'error: %r' % ex
        unreal.unregister_slate_post_tick_callback(C['h'])


o = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
if o:
    o.set_editor_property('bThrottleCPUWhenNotForeground', False)
if mundo():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
C['h'] = unreal.register_slate_post_tick_callback(_tick)
