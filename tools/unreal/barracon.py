"""Tanda 26: qué cuesta cada cosa en el barracón oeste (29,6 fps en la 0025; el suelo es 30) y qué cuestan las sombras
de las farolas, que son las que hacen que tu sombra delate.

No se supone nada: en UNA partida, plantado en el sitio de medida de siempre (tools/unreal/medir.py, «barracon oeste»),
se cambia una sola cosa cada vez, se esperan 2 s, se miden 6 s de fotogramas y se deja como estaba. La partida sin
tocar se mide al principio y al final: si las dos no coinciden (más de 0,7 fps), la tanda de medidas no vale.

Uso (en el editor, con el nivel Tarsis abierto, sin PIE y con «usar menos CPU en segundo plano» desactivado):
    py tools/unreal/barracon.py
Resultado en builtins._tarsis_barracon y en Saved/Pruebas/barracon_<fecha>.txt (fps medio, peor 1 % y diferencia con
la partida sin tocar). Las farolas se miden también en el camino, que es donde están.
"""
import builtins, os, time
import unreal

V = unreal.Vector
SITIOS = {
    'barracon': (V(1900, 2350, 120), V(300, 2800, 120)),
    'camino': (V(2400, 5950, 120), V(4300, 5700, 100)),
}
ESPERA, MIDE = 2.0, 6.0
B = {'estado': 'arrancando', 'res': [], 'h': None, 'gen': None, 'espera': 0.0, 'dts': None}
builtins._tarsis_barracon = B


def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def luces(prefijo):
    """Componentes de luz local de los actores cuya etiqueta empieza por prefijo."""
    out = []
    for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.Light):
        c = a.get_component_by_class(unreal.LocalLightComponent)
        if c and a.get_actor_label().startswith(prefijo):
            out.append(c)
    return out


def consola(orden):
    unreal.SystemLibrary.execute_console_command(mundo(), orden)


def _sombras(prefijo, valor, solo=None):
    """Pone la sombra de esas luces a valor y devuelve cómo dejarlas como estaban."""
    cs = [c for c in luces(prefijo) if solo is None or solo(c)]
    antes = [c.get_editor_property('cast_shadows') for c in cs]
    for c in cs:
        c.set_cast_shadows(valor)
    return lambda: [c.set_cast_shadows(v) for c, v in zip(cs, antes)]


def _radios(prefijo, valor):
    cs = luces(prefijo)
    antes = [c.get_editor_property('attenuation_radius') for c in cs]
    for c in cs:
        c.set_attenuation_radius(valor)
    return lambda: [c.set_attenuation_radius(v) for c, v in zip(cs, antes)]


def _variable(nombre, valor):
    antes = unreal.SystemLibrary.get_console_variable_float_value(nombre)
    consola('%s %s' % (nombre, valor))
    return lambda: consola('%s %g' % (nombre, antes))


def _camino(c):
    return c.get_owner().get_actor_location().y > 5400.0      # las tres farolas del camino y la de la garita


PLAN = [
    ('sin tocar', 'barracon', lambda: (lambda: None)),
    ('bombillas sin sombra', 'barracon', lambda: _sombras('interior', False)),
    ('bombillas con radio de 6 m', 'barracon', lambda: _radios('interior', 600.0)),
    ('focos de torre sin sombra', 'barracon', lambda: _sombras('foco_torreta', False)),
    ('farolas sin sombra', 'barracon', lambda: _sombras('farola', False)),
    ('sin niebla volumetrica', 'barracon', lambda: _variable('r.VolumetricFog', 0)),
    ('sin reflejos de Lumen', 'barracon', lambda: _variable('r.Lumen.Reflections.Allow', 0)),
    ('sombras virtuales a media resolucion', 'barracon', lambda: _variable('r.Shadow.Virtual.ResolutionLodBiasLocal', 1.0)),
    ('sin tocar (final)', 'barracon', lambda: (lambda: None)),
    ('camino sin tocar', 'camino', lambda: (lambda: None)),
    ('camino: farolas sin sombra', 'camino', lambda: _sombras('farola', False)),
    ('camino: solo las del camino con sombra', 'camino', lambda: _sombras('farola', False, lambda c: not _camino(c))),
    ('camino sin tocar (final)', 'camino', lambda: (lambda: None)),
]


def pasos():
    w = mundo()
    d = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector'))[0]
    if d.get_editor_property('cine'):
        d.interact()
    try:
        d.set_editor_property('truck', False)
    except Exception:
        pass
    consola('scalability 1')
    consola('t.MaxFPS 0')
    consola('r.SetRes 1920x1080w')
    yield 8.0
    gcls = unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard')
    sitio = None
    for nombre, donde, poner in PLAN:
        for g in unreal.GameplayStatics.get_all_actors_of_class(w, gcls):
            g.hold(120.0)
        if donde != sitio:
            sitio = donde
            pos, mira = SITIOS[donde]
            p = unreal.GameplayStatics.get_player_pawn(w, 0)
            p.set_actor_location(pos, False, True)
            unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.MathLibrary.find_look_at_rotation(pos, mira))
            yield 3.0
        try:
            quitar = poner()
        except Exception as ex:
            B['res'].append({'nombre': nombre, 'sitio': donde, 'error': repr(ex)})
            continue
        yield ESPERA
        B['dts'] = []
        yield MIDE
        dts = sorted(B['dts']); B['dts'] = None
        quitar()
        fila = {'nombre': nombre, 'sitio': donde}
        if dts:
            fila['fps'] = round(len(dts) / sum(dts), 1)
            fila['peor'] = round(1.0 / dts[max(0, int(len(dts) * 0.99) - 1)], 1)
        B['res'].append(fila)
        yield 0.5


def _informe():
    lineas = ['Barracon oeste y farolas - %s' % time.strftime('%Y-%m-%d %H:%M:%S')]
    base = {}
    for r in B['res']:
        if 'fps' in r and r['sitio'] not in base:
            base[r['sitio']] = r['fps']
    for r in B['res']:
        if 'error' in r:
            lineas.append('%-40s ERROR %s' % (r['nombre'], r['error']))
        elif 'fps' in r:
            lineas.append('%-40s %5.1f fps (%+.1f)  peor 1 %%: %5.1f' % (r['nombre'], r['fps'], r['fps'] - base[r['sitio']], r['peor']))
    for sitio, fin in (('barracon', 'sin tocar (final)'), ('camino', 'camino sin tocar (final)')):
        f = next((r for r in B['res'] if r['nombre'] == fin and 'fps' in r), None)
        if f and sitio in base and abs(f['fps'] - base[sitio]) > 0.7:
            lineas.append('OJO: en %s la partida sin tocar da %.1f al principio y %.1f al final: repetir la medida' % (sitio, base[sitio], f['fps']))
    carpeta = os.path.join(unreal.Paths.project_saved_dir(), 'Pruebas')
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, 'barracon_%s.txt' % time.strftime('%Y%m%d_%H%M%S'))
    open(ruta, 'w', encoding='utf-8').write('\n'.join(lineas))
    B['informe'] = ruta
    for l in lineas:
        log(l)


def _tick(dt):
    try:
        w = mundo()
        if B['estado'] == 'arrancando':
            if w and unreal.GameplayStatics.get_player_pawn(w, 0):
                B['estado'] = 'midiendo'
                B['gen'] = pasos()
            return
        if B['estado'] != 'midiendo':
            return
        if w and B['dts'] is not None:
            B['dts'].append(unreal.GameplayStatics.get_world_delta_seconds(w) / max(1e-6, unreal.GameplayStatics.get_global_time_dilation(w)))
        if time.time() < B['espera']:
            return
        try:
            B['espera'] = time.time() + next(B['gen'])
        except StopIteration:
            B['estado'] = 'terminado'
            unreal.unregister_slate_post_tick_callback(B['h'])
            _informe()
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    except Exception as ex:
        B['estado'] = 'error: %r' % ex
        unreal.unregister_slate_post_tick_callback(B['h'])


if __name__ == '__main__':
    o = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
    if o:
        o.set_editor_property('bThrottleCPUWhenNotForeground', False)
    if mundo():
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    B['h'] = unreal.register_slate_post_tick_callback(_tick)
