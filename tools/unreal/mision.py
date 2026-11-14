"""Vuelca la misión 1 (assets/unreal/mision1.json) en el director del nivel Tarsis y guarda el nivel.

Se ejecuta en el editor con el nivel abierto (guardias.py lo llama al colocar el director). Los datos quedan guardados
en el actor DirectorSigilo, así que la partida empaquetada no necesita el .json.

mision1.json:
  «ajustes»   propiedades por nombre del director («director») y de los guardias («guardias»: «*» o el nombre del guardia)
  «textos»    clave -> texto de todo lo que sale en pantalla (ATarsisDirector::Tx; {0}, {1}... son los datos)
  «objetivos» lista ordenada {si: bandera, texto: clave}: el HUD muestra el primero cuya bandera esté puesta
  «puntos»    puntos de interacción sencillos (puerta de la jefatura, mesa de Alarcón, litera de Ramos, botiquín,
              expediente): posición (celda [col, fila] del plano o pos [x, y, z]), radio, avisos, bandera que piden,
              qué hacen si falta, banderas que ponen, sonido, texto, punto de control, si los guardias lo notan
              y el bloque de la misión que quitan.
Lo que tiene más lógica (teclado, generador, Ramos, arrastrar, taquillas, portillo) sigue en el C++.
"""
import os, json
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RUTA = os.path.join(ROOT, 'assets', 'unreal', 'mision1.json')
T = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'))).get('T', 2.0)

# campo del .json -> propiedad de FTarsisPoint (nombre de Python)
CAMPOS = {
    'id': 'id', 'radio': 'radius', 'aviso': 'prompt', 'aviso_cerrado': 'prompt_locked', 'necesita': 'need',
    'si_falta_texto': 'need_text', 'si_falta_sonido': 'need_sound', 'si_falta_pone': 'need_sets', 'pone': 'sets',
    'pone_tambien': 'also_sets', 'repetible': 'repeat', 'sonido': 'sound', 'texto': 'text', 'segundos': 'text_seconds',
    'punto_de_control': 'checkpoint', 'lo_notan': 'change', 'quita': 'remove_block', 'dardos': 'darts',
}

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))

def celda(c, r, z=0.0):
    return unreal.Vector((c * T + T / 2) * 100.0, (r * T + T / 2) * 100.0, z)

def poner(obj, nombre, valor):
    obj.set_editor_property(nombre, valor)

def leer():
    return json.load(open(RUTA, encoding='utf-8'))

def punto(p):
    s = unreal.TarsisPoint()
    for k, v in p.items():
        if k in ('celda', 'pos', 'nota'):
            continue
        if k not in CAMPOS:
            raise ValueError('mision1.json: campo desconocido en un punto: %s' % k)
        poner(s, CAMPOS[k], v)
    if 'celda' in p:
        poner(s, 'pos', celda(*p['celda']))
    else:
        poner(s, 'pos', unreal.Vector(*p['pos']))
    return s

def objetivo(o):
    s = unreal.TarsisObjective()
    # «If» es palabra reservada en Python: se pone por el nombre de la propiedad en C++
    try:
        s.set_editor_property('if_', o.get('si', ''))
    except Exception:
        s.set_editor_property('If', o.get('si', ''))
    s.set_editor_property('text', o['texto'])
    return s

def ajustar(actor, props):
    for k, v in props.items():
        poner(actor, k, v)

def aplicar(director=None):
    """Pone los datos en el director (el que se pasa o el del nivel). Devuelve el director o None."""
    datos = leer()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actores = eas.get_all_level_actors()
    if director is None:
        dcls = unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector')
        director = next((a for a in actores if dcls and a.get_class() == dcls), None)
    if director is None:
        log('AVISO: no hay director en el nivel; coloca los guardias primero (guardias.py)')
        return None
    poner(director, 'texts', {k: v for k, v in datos['textos'].items()})
    poner(director, 'objectives', [objetivo(o) for o in datos['objetivos']])
    poner(director, 'points', [punto(p) for p in datos['puntos']])
    aj = datos.get('ajustes', {})
    ajustar(director, aj.get('director', {}))
    gcls = unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard')
    gs = aj.get('guardias', {})
    for a in actores:
        if not gcls or a.get_class() != gcls:
            continue
        ajustar(a, gs.get('*', {}))
        ajustar(a, gs.get(str(a.get_editor_property('guard_name')), {}))
    log('misión 1 en el director: %d textos, %d objetivos, %d puntos' % (len(datos['textos']), len(datos['objetivos']), len(datos['puntos'])))
    return director

if __name__ == '__main__':
    if aplicar():
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
        log('nivel guardado')
