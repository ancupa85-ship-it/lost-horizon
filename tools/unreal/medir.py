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
]
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
    unreal.SystemLibrary.execute_console_command(w, 'scalability 1')
    unreal.SystemLibrary.execute_console_command(w, 't.MaxFPS 0')
    unreal.SystemLibrary.execute_console_command(w, 'r.SetRes 1920x1080w')   # la ventana del PIE a 1080p
    yield 8.0   # calentamiento: sombreadores recién compilados y texturas que aún se cargan (el primer sitio salía 7 fps peor)
    gcls = unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard')
    for nombre, pos, mira in SITIOS:
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
