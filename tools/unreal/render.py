"""Presupuesto de render de Tarsis (tanda 24): qué ajustes del motor devuelven memoria de vídeo en ESTA tarjeta, y cuánto cuestan.

La tanda 23 midió que las texturas no son el problema (228 MB de 3,8 GB): lo que llena la tarjeta de 4 GB son los
búferes del render (sombras virtuales, caché de superficies de Lumen, reservas de Nanite) y el propio editor. Esos
tamaños se gobiernan con variables de consola. Aquí no se supone nada: cada candidato se prueba solo, en una partida
limpia, y se apunta la memoria de la tarjeta (nvidia-smi) y los fps en tres sitios, contra la partida sin tocar.

El director (C++, RenderCVars) pone las variables al empezar la partida y las deja como estaban al acabar: así se mide
por el mismo camino por el que luego se juega, y cambiar el presupuesto no pide compilar. OJO: una variable puesta a
mano en la consola del editor manda sobre el código (prioridad de consola): antes de medir, no tocarlas a mano.

Uso (en el editor, con el nivel Tarsis abierto, sin PIE):
    py tools/unreal/render.py               mide todos los candidatos (unos 6 minutos) y deja la tabla en
                                            Saved/Pruebas/render_<fecha>.txt y en builtins._tarsis_render
    import render; render.aplicar(['sombras', 'lumen_cache'])     escribe esos candidatos en el director del nivel y guarda
    import render; render.aplicar([])                             quita el presupuesto
Una variable que no exista en este motor no rompe nada: el director la apunta en el registro y sigue.
"""
import builtins, os, subprocess, sys, time
import unreal

V = unreal.Vector
# nombre -> variables. Cada una, sola frente a la partida sin tocar. Los valores de serie son los de UE 5.x en calidad
# alta; con la calidad Media del proyecto alguna ya puede venir recortada (entonces la medida no se mueve y se descarta).
CANDIDATOS = {
    # sombras virtuales: el almacén físico de páginas (de serie 4096 páginas de 128 px: una textura de 8192 x 8192)
    'sombras': ['r.Shadow.Virtual.MaxPhysicalPages=2048'],
    # caché de superficies de Lumen: el atlas (de serie 4096 de lado, varias capas)
    'lumen_cache': ['r.LumenScene.SurfaceCache.AtlasSize=2048'],
    # Nanite: reserva de transmisión de geometría (de serie 512 MB; la base entera pesa mucho menos)
    'nanite': ['r.Nanite.Streaming.StreamingPoolSize=128'],
    # texturas: tope de la reserva de transmisión (piden 228 MB con todo cargado)
    'texturas': ['r.Streaming.PoolSize=400'],
    # resolución interna (el reescalado temporal la sube a la de la ventana): menos búferes y más fps, algo menos de nitidez
    'resolucion': ['r.ScreenPercentage=80'],
    # niebla volumétrica: celdas más gordas (solo se nota con lluvia o niebla)
    'niebla': ['r.VolumetricFog.GridPixelSize=16', 'r.VolumetricFog.GridSizeZ=64'],
}
SITIOS = [
    ('patio central', V(4300, 3500, 120), V(6600, 4100, 150)),
    ('barracon oeste', V(1900, 2350, 120), V(300, 2800, 120)),
    ('porton de salida', V(7600, 5860, 120), V(9100, 5700, 150)),
]
CALIENTA, ESPERA, MIDE = 8.0, 2.0, 5.0
M = {'estado': 'parado', 'res': [], 'h': None, 'gen': None, 'espera': 0.0, 'dts': None}
builtins._tarsis_render = M


def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))


def vram():
    try:
        o = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
                           capture_output=True, text=True, timeout=10).stdout.strip().split(',')
        return int(o[0])
    except Exception:
        return None


def _clase():
    return unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector')


def director_editor():
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ds = unreal.GameplayStatics.get_all_actors_of_class(w, _clase())
    return ds[0] if ds else None


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def aplicar(nombres, guardar=True):
    """Escribe en el director del nivel las variables de esos candidatos (o una lista de «variable=valor» tal cual)."""
    d = director_editor()
    if not d:
        log('AVISO: render: no hay director en el nivel')
        return []
    lista = []
    for n in nombres:
        lista += CANDIDATOS.get(n, [n] if '=' in n else [])
    d.set_editor_property('render_c_vars', lista)
    if guardar:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log('render: presupuesto en el director:', lista or 'ninguno')
    return lista


def _partida(nombre):
    """Una partida: espera a que arranque, calienta, mide en los sitios y devuelve la fila."""
    w = mundo()
    d = unreal.GameplayStatics.get_all_actors_of_class(w, _clase())[0]
    if d.get_editor_property('cine'):
        d.interact()
    try:
        d.set_editor_property('truck', False)
    except Exception:
        pass
    unreal.SystemLibrary.execute_console_command(w, 't.MaxFPS 0')
    yield CALIENTA
    gcls = unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard')
    fila = {'nombre': nombre, 'puestas': [str(x) for x in d.get_editor_property('render_applied')], 'fps': [], 'peor': [], 'vram': []}
    for sitio, pos, mira in SITIOS:
        for g in unreal.GameplayStatics.get_all_actors_of_class(w, gcls):
            g.hold(60.0)
        p = unreal.GameplayStatics.get_player_pawn(w, 0)
        p.set_actor_location(pos, False, True)
        unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pos, mira))
        yield ESPERA
        M['dts'] = []
        yield MIDE
        dts = sorted(M['dts']); M['dts'] = None
        if dts:
            fila['fps'].append(round(len(dts) / sum(dts), 1))
            fila['peor'].append(round(1.0 / dts[max(0, int(len(dts) * 0.99) - 1)], 1))
        fila['vram'].append(vram())
    M['res'].append(fila)


def _plan(nombres):
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    antes = [str(x) for x in director_editor().get_editor_property('render_c_vars')]
    for n in nombres:
        aplicar([] if n == 'sin tocar' else (list(CANDIDATOS) if n == 'todo' else [n]), guardar=False)
        les.editor_request_begin_play()
        t0 = time.time()
        while not (mundo() and unreal.GameplayStatics.get_player_pawn(mundo(), 0)):
            if time.time() - t0 > 90:
                raise RuntimeError('el PIE no arranca')
            yield 0.5
        for e in _partida(n):
            yield e
        les.editor_request_end_play()
        while mundo():
            yield 0.5
        yield 2.0
    director_editor().set_editor_property('render_c_vars', antes)      # como estaba: aplicar() es quien decide


def _tick(dt):
    try:
        if M['estado'] != 'midiendo':
            return
        w = mundo()
        if w and M['dts'] is not None:
            M['dts'].append(unreal.GameplayStatics.get_world_delta_seconds(w) / max(1e-6, unreal.GameplayStatics.get_global_time_dilation(w)))
        now = time.time()
        if now < M['espera']:
            return
        try:
            M['espera'] = now + next(M['gen'])
        except StopIteration:
            M['estado'] = 'terminado'
            unreal.unregister_slate_post_tick_callback(M['h'])
            base = M['res'][0] if M['res'] else None
            lineas = []
            for r in M['res']:
                v = [x for x in r['vram'] if x is not None]
                vb = [x for x in base['vram'] if x is not None] if base else []
                dv = (sum(v) / len(v) - sum(vb) / len(vb)) if v and vb else 0.0
                df = (sum(r['fps']) / len(r['fps']) - sum(base['fps']) / len(base['fps'])) if r['fps'] and base and base['fps'] else 0.0
                lineas.append('%-12s VRAM %s MB (%+.0f) | fps %s (%+.1f) | peor 1 %% %s | puestas: %s' % (
                    r['nombre'], r['vram'], dv, r['fps'], df, r['peor'], '; '.join(r['puestas']) or '-'))
            for l in lineas:
                log('render:', l)
            carpeta = os.path.join(unreal.Paths.project_saved_dir(), 'Pruebas')
            os.makedirs(carpeta, exist_ok=True)
            open(os.path.join(carpeta, 'render_%s.txt' % time.strftime('%Y%m%d_%H%M%S')), 'w', encoding='utf-8').write('\n'.join(lineas))
    except Exception as ex:
        M['estado'] = 'error: %r' % ex
        unreal.unregister_slate_post_tick_callback(M['h'])
        try:
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        except Exception:
            pass


def medir(nombres=None):
    """nombres: candidatos a medir (por defecto todos), siempre contra «sin tocar» y con «todo» al final."""
    if mundo():
        log('AVISO: render: hay una partida en marcha; ciérrala antes de medir')
        return
    o = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
    if o:
        o.set_editor_property('bThrottleCPUWhenNotForeground', False)
    M.update({'estado': 'midiendo', 'res': [], 'espera': 0.0, 'dts': None})
    M['gen'] = _plan(['sin tocar'] + list(nombres or CANDIDATOS) + ['todo'])
    M['h'] = unreal.register_slate_post_tick_callback(_tick)


if __name__ == '__main__':
    medir()
