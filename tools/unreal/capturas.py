"""Capturas desde cámaras fijas del nivel Tarsis (para comparar antes y después de un cambio de aspecto).

Uso (en el editor): py tools/unreal/capturas.py [prefijo] [serie]      (series: base, tanda26)
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
# tanda 26: la serie nueva (py tools/unreal/capturas.py <prefijo> tanda26). Los sitios salen del plano, sin haberlos
# visto en pantalla: si una cámara cae dentro de un mueble o mira a una pared, se corrige aquí. Los guardias se paran al
# empezar, así que cada foco de torre queda quieto donde le pille (al principio de su vuelta: torre 1 junto a la puerta
# del barracón, torre 2 a media recta del camino).
TANDA26 = [
    # los dos focos de torre y su mancha en el suelo
    ('foco_patio', V(3156, 2950, 330), V(2600, 2600, 0)),
    ('foco_camino', V(3300, 5950, 110), V(5000, 5700, 40)),
    # tu sombra bajo la primera farola del camino (se mira al suelo, hacia donde cae)
    ('sombra_farola', V(1270, 5700, 110), V(1700, 5560, 0)),
    # la luz de dentro, un cuarto por cámara (bombillas interior_1 a interior_6 de base.json)
    ('dentro_1', V(1050, 3850, 110), V(350, 3300, 120)),
    ('dentro_2_archivo', V(1500, 3900, 110), V(2100, 3300, 120)),
    ('dentro_3', V(5617, 1583, 110), V(5985, 1215, 120)),
    ('dentro_4', V(5300, 1850, 110), V(5900, 1500, 120)),
    ('dentro_5', V(6500, 2300, 110), V(6400, 1700, 120)),
    ('dentro_6_roja', V(6500, 2900, 110), V(6100, 2650, 120)),
    # las de siempre, para comparar la exposición nueva con la 25f
    ('interior', V(2080, 2620, 110), V(300, 2760, 90)),
    ('puerta', V(1750, 1250, 110), V(1300, 2050, 160)),
    ('patio', V(3000, 450, 110), V(900, 2000, 60)),
]
SERIES = {'base': CAMARAS, 'tanda26': TANDA26}
if len(sys.argv) > 2 and sys.argv[2] in SERIES:
    CAMARAS = SERIES[sys.argv[2]]
# o una lista propia desde fuera: builtins._tarsis_camaras = [(nombre, posición, mira), ...]
CAMARAS = getattr(builtins, '_tarsis_camaras', None) or CAMARAS
PREFIJO = sys.argv[1] if len(sys.argv) > 1 else time.strftime('%H%M%S')
OUT = os.path.join(unreal.Paths.project_saved_dir(), 'Capturas')
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
C = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'hechas': [], 'blur': None}
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
    # sin desenfoque de movimiento mientras se captura (al colocar la cámara de golpe, lo que brilla deja estela). Solo
    # aquí: la variable se guarda y se repone al acabar (_fin); el juego no cambia
    C['blur'] = unreal.SystemLibrary.get_console_variable_int_value('r.MotionBlurQuality')
    unreal.SystemLibrary.execute_console_command(w, 'r.MotionBlurQuality 0')
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


def _fin():
    if C.get('blur') is not None:
        unreal.SystemLibrary.execute_console_command(None, 'r.MotionBlurQuality %d' % C['blur'])
        C['blur'] = None


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
            _fin()
            unreal.unregister_slate_post_tick_callback(C['h'])
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    except Exception as ex:
        C['estado'] = 'error: %r' % ex
        _fin()
        unreal.unregister_slate_post_tick_callback(C['h'])


o = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
if o:
    o.set_editor_property('bThrottleCPUWhenNotForeground', False)
if mundo():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
C['h'] = unreal.register_slate_post_tick_callback(_tick)
