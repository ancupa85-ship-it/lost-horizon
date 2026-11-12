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

# nombre: (ronda en casillas [col, fila], espera en cada punto, s)
GUARDIAS = {
    'Ibarra': ([[13, 4], [13, 9], [9, 9], [9, 4]], 2.5),   # patio norte, con la llave de la jefatura
    'Moya': ([[20, 19], [33, 19], [33, 20], [20, 20]], 3.0),   # patio central
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

def colocar():
    cls = unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard')
    if not cls:
        log('AVISO: la clase TarsisGuard no está compilada; no se colocan guardias')
        return 0
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.get_class() == cls:
            eas.destroy_actor(a)
    n = 0
    for nombre, (ronda, espera) in GUARDIAS.items():
        pts = [casilla(c, r) for c, r in ronda]
        g = eas.spawn_actor_from_class(cls, pts[0], unreal.Rotator(0, 0, 0))
        g.set_actor_label('Guardia_' + nombre)
        g.set_folder_path('Guardias')
        g.set_editor_property('patrol_points', pts)
        g.set_editor_property('wait_at_point', espera)
        cuerpo(g, nombre.lower())
        n += 1
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
