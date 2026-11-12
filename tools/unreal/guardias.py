"""Coloca los guardias de la fase 2 (clase C++ ATarsisGuard) en el nivel Tarsis con sus rondas del juego web.

Se ejecuta en el editor con el nivel abierto (montar_base.py lo llama al final si la clase está compilada).
Rondas por casillas del plano (como en tools/blender/escena_base.py y escenario/visor.js); cada casilla mide T m.
"""
import os, sys, json, importlib
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json')))
T = DATA.get('T', 2.0)

# nombre: (ronda en casillas [col, fila], espera en cada punto (s, o una lista por punto), persona del cuerpo)
# rondas de escenario/visor.js (walk de escena_base.py, EXTRA y WPX)
GUARDIAS = {
    'Ibarra': ([[13, 4], [13, 9], [9, 9], [9, 4]], 2.5, 'ibarra'),   # patio norte, con la llave de la jefatura
    'Moya': ([[20, 19], [33, 19], [33, 20], [20, 20]], 3.0, 'moya'),   # patio central
    'Peris': ([[28, 7], [28, 8], [23, 8], [28, 8]], [9.0, 0.5, 16.0, 0.5], 'peris'),   # cuartelero: sale a fumar a la puerta y vuelve a la mesa
    'Vega': ([[6, 24], [20, 24], [20, 21], [20, 24]], 2.5, 'moya'),   # portón
    'Ramos': ([[2, 13], [13, 13], [13, 11], [13, 13]], 2.5, 'peris'),   # barracón
}

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))

def casilla(c, r, z=100.0):
    # Blender (x*T+T/2, -(r*T+T/2)) -> Unreal: X*100, Y*-100
    return unreal.Vector((c * T + T / 2) * 100.0, (r * T + T / 2) * 100.0, z)

def cuerpo(g, nombre):
    # malla con esqueleto y animaciones del juego web (tools/unreal/personas.py); sin ella queda el cilindro
    try:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import personas
        importlib.reload(personas)
        p = personas.cargar(nombre)
    except Exception as e:
        log('AVISO: sin cuerpo para', nombre, repr(e))
        return
    if not p:
        return
    g.set_editor_property('body_mesh', p['malla'])
    for prop, k in (('idle_anim', 'idle'), ('walk_anim', 'walk'), ('aim_anim', 'aim')):
        if p.get(k):
            g.set_editor_property(prop, p[k])
    # set_editor_property ya avisa al actor del cambio (OnConstruction -> SetupBody); rerun_construction_scripts
    # no está expuesto a Python en 5.8
    if hasattr(g, 'rerun_construction_scripts'):
        g.rerun_construction_scripts()

def navegacion():
    # volumen del mapa de navegación sobre toda la base (36 x 28 casillas de T m), para que los guardias
    # rodeen paredes, vallas y contenedores al perseguir o volver a su ronda
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if isinstance(a, unreal.NavMeshBoundsVolume):
            eas.destroy_actor(a)
    filas = len(DATA['map'])
    cols = max(len(f) for f in DATA['map'])
    ancho, largo = cols * T * 100.0, filas * T * 100.0
    v = eas.spawn_actor_from_class(unreal.NavMeshBoundsVolume, unreal.Vector(ancho / 2, largo / 2, 300.0), unreal.Rotator(0, 0, 0))
    v.set_actor_label('MapaNavegacion')
    v.set_folder_path('Guardias')
    # la caja por defecto mide 200 cm de lado
    v.set_actor_scale3d(unreal.Vector((ancho + 400) / 200.0, (largo + 400) / 200.0, 1400 / 200.0))
    try:
        unreal.SystemLibrary.execute_console_command(unreal.EditorLevelLibrary.get_editor_world(), 'RebuildNavigation')
    except Exception as e:
        log('AVISO: no se pudo reconstruir la navegación:', repr(e))
    log('mapa de navegación', round(ancho / 100), 'x', round(largo / 100), 'm')

def centinelas(eas, cls):
    # un centinela en cada torre (TOWERS del visor), en la plataforma, junto a su foco, que gira con él
    import math
    focos = [a for a in eas.get_all_level_actors() if isinstance(a, unreal.SpotLight)]
    n = 0
    for i, t in enumerate(DATA.get('torres', [])):
        bx, by = t['pos'][0], t['pos'][1]
        loc = unreal.Vector((bx - 0.25) * 100.0, -by * 100.0, t.get('altura', 4.2) * 100.0 + 95.0)
        d = t['foco']['dir']
        yaw = math.degrees(math.atan2(-d[1], d[0]))   # Blender -> Unreal: Y cambia de signo
        g = eas.spawn_actor_from_class(cls, loc, unreal.Rotator(roll=0, pitch=0, yaw=yaw))
        g.set_actor_label('Centinela_' + t['name'])
        g.set_folder_path('Guardias')
        g.set_editor_property('tower_sentry', True)
        g.set_editor_property('tower_yaw', yaw)
        g.set_editor_property('view_distance', 2500.0)
        g.set_editor_property('view_half_angle', 32.0)
        fp = t['foco']['pos']
        fl = unreal.Vector(fp[0] * 100.0, -fp[1] * 100.0, fp[2] * 100.0)
        if focos:
            f = min(focos, key=lambda a: (a.get_actor_location() - fl).length())
            if (f.get_actor_location() - fl).length() < 400:
                f.get_editor_property('root_component').set_editor_property('mobility', unreal.ComponentMobility.MOVABLE)
                g.set_editor_property('tower_light', f)
            else:
                log('AVISO: no encuentro el foco de', t['name'])
        cuerpo(g, 'moya')
        n += 1
    return n

def colocar():
    cls = unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard')
    if not cls:
        log('AVISO: la clase TarsisGuard no está compilada; no se colocan guardias')
        return 0
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    navegacion()
    for a in eas.get_all_level_actors():
        if a.get_class() == cls:
            eas.destroy_actor(a)
    n = 0
    for nombre, (ronda, espera, persona) in GUARDIAS.items():
        pts = [casilla(c, r) for c, r in ronda]
        g = eas.spawn_actor_from_class(cls, pts[0], unreal.Rotator(0, 0, 0))
        g.set_actor_label('Guardia_' + nombre)
        g.set_folder_path('Guardias')
        g.set_editor_property('patrol_points', pts)
        if isinstance(espera, list):
            g.set_editor_property('patrol_waits', espera)
        else:
            g.set_editor_property('wait_at_point', espera)
        cuerpo(g, persona)
        n += 1
    n += centinelas(eas, cls)
    # el director del sigilo (indicador de luz, agacharse con C, avisos); uno por nivel
    dcls = unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector')
    if dcls:
        for a in eas.get_all_level_actors():
            if a.get_class() == dcls:
                eas.destroy_actor(a)
        d = eas.spawn_actor_from_class(dcls, unreal.Vector(0, 0, 300), unreal.Rotator(0, 0, 0))
        d.set_actor_label('DirectorSigilo')
        d.set_folder_path('Guardias')
    log('guardias colocados', n, '- director', 'sí' if dcls else 'no compilado')
    return n

if __name__ == '__main__':
    colocar()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
