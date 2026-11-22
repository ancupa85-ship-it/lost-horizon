"""Mide el rendimiento de Tarsis en PIE: fps medio y el peor 1 % en tres sitios, y la memoria de vídeo usada.

Uso (en el editor, con el nivel Tarsis abierto y «usar menos CPU en segundo plano» desactivado):
    py tools/unreal/medir.py
Abre el PIE (r.SetRes 1920x1080w para la ventana) con la calidad Media (scalability 1), salta la entrada, deja a los guardias
quietos (que no te cojan mientras se mide) y en cada sitio espera 2 s y mide 8 s de fotogramas. El resultado queda en
builtins._tarsis_medida y en Saved/Pruebas/medida_<fecha>.txt; la tabla para docs/rendimiento.md la escribe quien lo lanza.
La memoria de vídeo es la de toda la tarjeta (nvidia-smi), con el editor abierto.
"""
import builtins, os, subprocess, time
import unreal

V = unreal.Vector
# sitio: (posición del jugador, punto al que mira)
SITIOS = [
    ('entrada', V(500, 500, 120), V(3000, 2400, 150)),
    ('patio central', V(4300, 3500, 120), V(6600, 4100, 150)),
    ('barracon oeste', V(1900, 2350, 120), V(300, 2800, 120)),
    # tanda 20: los portones del muro nuevo, con el camino y el anillo exterior a la vista
    ('porton de entrada', V(-600, 5850, 120), V(-1900, 5700, 150)),
    ('porton de salida', V(7600, 5860, 120), V(9100, 5700, 150)),
    # tanda E1: el relleno (hangar con taller, plaza de armas y enfermería)
    ('hangar', V(5560, 6420, 120), V(4300, 7000, 100)),
    ('plaza de armas', V(6950, 3700, 120), V(8000, 4300, 200)),
    ('enfermeria', V(7520, 3420, 120), V(7700, 2850, 80)),
]
# tanda 21: el camión entrando por el portón con los faros (una luz con sombra que se mueve) hacia la cámara
CAMION = ('camino con el camion', V(1500, 6150, 120), V(-600, 5700, 120))
ESPERA, MIDE = 2.0, 8.0
M = {'estado': 'arrancando', 'res': [], 'h': None, 'gen': None, 'espera': 0.0, 'dts': None}
builtins._tarsis_medida = M


def sin_freno():
    """«Usar menos CPU en segundo plano» del editor, apagado: si no, sin el foco el PIE va a 3 fps y las medidas y las
    pruebas no valen. No está expuesto a Python, se cambia por reflexión en el objeto por defecto (dura la sesión)."""
    o = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
    if o:
        o.set_editor_property('bThrottleCPUWhenNotForeground', False)


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def vram():
    try:
        o = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
                           capture_output=True, text=True, timeout=10).stdout.strip().split(',')
        return int(o[0]), int(o[1])
    except Exception:
        return None, None


def pasos():
    w = mundo()
    cls = unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector')
    d = unreal.GameplayStatics.get_all_actors_of_class(w, cls)[0]
    if d.get_editor_property('cine'):
        d.interact()
    try:
        d.set_editor_property('truck', False)   # el camión, solo en su sitio de medida (el último)
    except Exception:
        pass
    unreal.SystemLibrary.execute_console_command(w, 'scalability 1')
    unreal.SystemLibrary.execute_console_command(w, 't.MaxFPS 0')
    unreal.SystemLibrary.execute_console_command(w, 'r.SetRes 1920x1080w')   # la ventana del PIE a 1080p
    yield 8.0   # calentamiento: sombreadores recién compilados y texturas que aún se cargan (el primer sitio salía 7 fps peor)
    gcls = unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard')
    for nombre, pos, mira in SITIOS + [CAMION]:
        if nombre == CAMION[0]:
            try:
                d.set_editor_property('truck', True)
                d.set_editor_property('truck_start', V(-6000, 5700, 4))
                d.truck_skip_wait()
            except Exception:
                continue   # módulo sin compilar con el camión
            for _ in range(60):   # hasta que ha entrado por el portón (se mide mientras viene por el camino)
                if d.get_editor_property('truck_state') >= 3:
                    break
                yield 0.5
        for g in unreal.GameplayStatics.get_all_actors_of_class(w, gcls):
            g.hold(60.0)
        p = unreal.GameplayStatics.get_player_pawn(w, 0)
        p.set_actor_location(pos, False, True)
        pc = unreal.GameplayStatics.get_player_controller(w, 0)
        pc.set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pos, mira))
        yield ESPERA
        M['dts'] = []
        yield MIDE
        dts = sorted(M['dts'])
        M['dts'] = None
        if not dts:
            continue
        media = len(dts) / sum(dts)
        peor = dts[max(0, int(len(dts) * 0.99) - 1)]
        usado, total = vram()
        vp = unreal.WidgetLayoutLibrary.get_viewport_size(w)
        M['res'].append((nombre, round(media, 1), round(1.0 / peor, 1), usado, total, '%dx%d' % (vp.x, vp.y), len(dts)))
    # tanda A: una pasada con los guardias andando su ronda (en las demás están quietos): el coste real de animarlos con
    # el GASP (Motion Matching). No ven al jugador (vista a 1 cm) para que nadie corte la ronda; el camión, fuera
    try:
        d.set_editor_property('truck', False)
    except Exception:
        pass
    gs = unreal.GameplayStatics.get_all_actors_of_class(w, gcls)
    for g in gs:
        g.set_editor_property('view_distance', 1.0)
        g.hold(0.0)
    nombre, pos, mira = SITIOS[1]
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    p.set_actor_location(pos, False, True)
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pos, mira))
    yield ESPERA + 2.0
    andan = 0
    M['dts'] = []
    for _ in range(int(MIDE / 0.5)):
        yield 0.5
        andan = max(andan, sum(1 for g in gs if g.get_velocity().length() > 30.0))
    dts = sorted(M['dts'])
    M['dts'] = None
    if dts:
        media = len(dts) / sum(dts)
        peor = dts[max(0, int(len(dts) * 0.99) - 1)]
        usado, total = vram()
        vp = unreal.WidgetLayoutLibrary.get_viewport_size(w)
        M['res'].append(('%s con guardias andando (%d de %d)' % (nombre, andan, len(gs)), round(media, 1), round(1.0 / peor, 1),
                         usado, total, '%dx%d' % (vp.x, vp.y), len(dts)))
    # tanda C: la misma pasada con los tres guardias de ronda mas cercanos dormidos con ragdoll (la fisica solo cuesta cerca
    # del jugador y, en reposo, se duerme): se mide recien caidos (los 8 s primeros) con los demas andando
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    ronda = [g for g in gs if not g.get_editor_property('tower_sentry')]
    ronda.sort(key=lambda g: (g.get_actor_location() - pos).length())
    dormidos = ronda[:3]
    for g in dormidos:
        g.set_editor_property('knock_out_time', 100.0)
        # al lado del jugador (a la vista), para que caigan con fisica
        g.set_actor_location(unreal.Vector(pos.x + 300 + 150 * dormidos.index(g), pos.y + 200, g.get_actor_location().z), False, True)
    yield 0.3
    for g in dormidos:
        f = g.get_actor_forward_vector()
        g.dart_hit(unreal.Vector(f.x, f.y, 0.0))
        g.knock_out()
    M['dts'] = []
    fisica = 0
    for _ in range(int(MIDE / 0.5)):
        yield 0.5
        fisica = max(fisica, sum(1 for g in gs if g.physics_active()))
    dts = sorted(M['dts'])
    M['dts'] = None
    if dts:
        media = len(dts) / sum(dts)
        peor = dts[max(0, int(len(dts) * 0.99) - 1)]
        usado, total = vram()
        vp = unreal.WidgetLayoutLibrary.get_viewport_size(w)
        M['res'].append(('%s con 3 dormidos con ragdoll (%d con fisica)' % (nombre, fisica), round(media, 1), round(1.0 / peor, 1),
                         usado, total, '%dx%d' % (vp.x, vp.y), len(dts)))
    for g in dormidos:
        g.wake_now()


def _tick(dt):
    try:
        w = mundo()
        if M['estado'] == 'arrancando':
            if w and unreal.GameplayStatics.get_player_pawn(w, 0):
                M['estado'] = 'midiendo'
                M['gen'] = pasos()
                M['espera'] = 0.0
            return
        if M['estado'] != 'midiendo':
            return
        now = time.time()
        if M['dts'] is not None:
            M['dts'].append(unreal.GameplayStatics.get_world_delta_seconds(w) / max(1e-6, unreal.GameplayStatics.get_global_time_dilation(w)))
        if now < M['espera']:
            return
        try:
            M['espera'] = now + next(M['gen'])
        except StopIteration:
            M['estado'] = 'terminado'
            unreal.unregister_slate_post_tick_callback(M['h'])
            lineas = ['%s: %.1f fps de media, peor 1 %% %.1f fps, VRAM %s de %s MB, ventana %s, %d fotogramas' % r for r in M['res']]
            carpeta = os.path.join(unreal.Paths.project_saved_dir(), 'Pruebas')
            os.makedirs(carpeta, exist_ok=True)
            open(os.path.join(carpeta, 'medida_%s.txt' % time.strftime('%Y%m%d_%H%M%S')), 'w', encoding='utf-8').write('\n'.join(lineas))
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    except Exception as ex:
        M['estado'] = 'error: %r' % ex
        unreal.unregister_slate_post_tick_callback(M['h'])


sin_freno()
if mundo():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
M['h'] = unreal.register_slate_post_tick_callback(_tick)
