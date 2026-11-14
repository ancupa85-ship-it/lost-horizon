"""Pruebas automáticas de Tarsis en PIE: recorre lo principal del juego y escribe un informe PASA/FALLA.

Uso (en el editor, con el nivel Tarsis abierto; por ejecución remota de Python o desde la consola):
    py tools/unreal/pruebas.py
Arranca el PIE, ejecuta las pruebas con un ejecutor por ticks (cada prueba es un generador que cede segundos de juego o una
condición de espera) y deja el informe en
    Saved/Pruebas/informe_<fecha>.txt
El progreso queda en builtins._tarsis_pruebas (estado, prueba actual y resultados) para consultarlo desde fuera.

Las pruebas van por familias (FAMILIAS): cada familia en un PIE limpio, para que lo que deja una (guardias en alerta,
capturas, puertas abiertas) no tuerza las demás. Las que dependen unas de otras (la llave, la jefatura, el farol y el
final) van en la misma familia. Al acabar cada familia se comprueba que no se ha pedido ningún texto que falte en
assets/unreal/mision1.json.

Las pruebas usan solo funciones y propiedades expuestas del Director y de los guardias (Interact, KeypadDigit, ShootDart,
PressKey, MenuLines, KnockOut...). No necesitan el teclado ni que la ventana tenga el foco.
"""
import builtins, json, math, os, re, time
import unreal

try:
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:   # ejecutado sin archivo (pegado en la consola)
    ROOT = os.path.join(os.path.dirname(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())), '..', '..', 'LostHorizon', 'lost-horizon')

V = unreal.Vector
GEN = V(4300, 1700, 0)          # GeneratorLoc
SITIO = V(4300, 1980, 0)        # RepairSpot (GeneratorLoc + 0,280)
FAROL = V(8660, 5640, 380)      # farol de la garita de salida (lo pone SetupBarrier bajo la luminaria del báculo)
SALIDA = V(9050, 5700, 0)       # ExitLoc: portón de salida del muro nuevo (tanda 20)
PORTILLO = V(310, 7390, 0)      # WicketLoc: portillo de la marisma, en el muro sur


def sin_freno():
    """«Usar menos CPU en segundo plano» del editor, apagado: si no, sin el foco el PIE va a 3 fps y las medidas y las
    pruebas no valen. No está expuesto a Python, se cambia por reflexión en el objeto por defecto (dura la sesión)."""
    o = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
    if o:
        o.set_editor_property('bThrottleCPUWhenNotForeground', False)


# ---------------------------------------------------------------- acceso al juego

def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()

def director():
    w = mundo()
    if not w:
        return None
    ds = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector'))
    return ds[0] if ds else None

def guardias():
    return unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard'))

def guardia(nombre):
    for g in guardias():
        if g.get_actor_label().endswith(nombre):
            return g
    return None

def jugador():
    return unreal.GameplayStatics.get_player_pawn(mundo(), 0)

def estado(g):
    return str(g.get_editor_property('state')).split('.')[-1].split(':')[0]

def dist2d(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)

def tp(x, y, yaw=0.0):
    p = jugador()
    p.set_actor_location(V(x, y, max(p.get_actor_location().z, 100)), False, True)
    unreal.GameplayStatics.get_player_controller(mundo(), 0).set_control_rotation(unreal.Rotator(0.0, 0.0, yaw))

def mirar(punto):
    p = jugador()
    cam = p.get_component_by_class(unreal.CameraComponent).get_world_location()
    unreal.GameplayStatics.get_player_controller(mundo(), 0).set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cam, punto))

def junto_a(g, d=90.0):
    l = g.get_actor_location()
    p = jugador()
    p.set_actor_location(V(l.x + d, l.y, max(p.get_actor_location().z, 100)), False, True)

def derribar(g):
    g.set_editor_property('knock_out_time', 100.0)
    g.knock_out()

def luces():
    """(encendidas, apagadas) por nombre de etiqueta; el farol de la garita (creado en juego) sale como farol_garita."""
    on, off = [], []
    for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.Light):
        c = a.get_component_by_class(unreal.LocalLightComponent)
        if not c:
            continue
        if a.actor_has_tag('camion'):
            continue   # los faros del camión (tanda 21): van y vienen con él y no dependen del generador
        n = a.get_actor_label()
        if n.startswith('SpotLight'):
            n = 'farol_garita'
        (on if c.is_visible() else off).append(n)
    return sorted(on), sorted(off)

def luz_en(punto):
    return unreal.TarsisGuard.light_at(mundo(), punto)

def quietos(*nombres):
    """Deja quietos y sin ver ni oír (Hold) a los guardias del anillo que se nombran: las pruebas que plantan al jugador
    junto al control de salida o en el portillo se escribieron antes de que hubiera centinelas allí (tanda 21)."""
    for n in nombres:
        g = guardia(n)
        if g:
            g.hold(3600.0)

def actores(tag, clase=None):
    return [a for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), clase or unreal.StaticMeshActor) if a.actor_has_tag(tag)]

def reparador_cercano():
    best = None
    for g in guardias():
        if g.get_editor_property('tower_sentry'):
            continue
        dd = dist2d(g.get_actor_location(), SITIO)
        if best is None or dd < best[0]:
            best = (dd, g)
    return best


# ---------------------------------------------------------------- resultados

R = {'estado': 'preparando', 'prueba': '', 'resultados': [], 't0': time.time(), 'h': None, 'gen': None, 'espera': None}
builtins._tarsis_pruebas = R

def check(nombre, ok, detalle=''):
    R['resultados'].append((R['prueba'], nombre, bool(ok), str(detalle)))
    unreal.log('[Pruebas] %s  %s / %s  %s' % ('PASA ' if ok else 'FALLA', R['prueba'], nombre, detalle))


# ---------------------------------------------------------------- pruebas (generadores)
# cada «yield n» espera n segundos (tiempo real del mundo); «yield ('hasta', funcion, maximo)» espera a que funcion() sea cierta

def prueba_intro():
    d = director()
    yield ('hasta', lambda: director().get_editor_property('cine'), 8.0)
    check('la cinemática de entrada arranca', d.get_editor_property('cine'))
    check('el jugador está oculto', jugador().get_editor_property('hidden'))
    t = d.get_editor_property('mission_time')
    yield 1.0
    check('el tiempo de misión no corre', d.get_editor_property('mission_time') == t, d.get_editor_property('mission_time'))
    d.interact()
    yield 0.5
    check('E salta la cinemática', not d.get_editor_property('cine'))
    check('salen las instrucciones', 'TARSIS' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:40])
    check('el objetivo sale de mision1.json', d.objective() == MISION['textos']['obj_llave'], d.objective())
    check('base tranquila al empezar (indicador del HUD)', d.base_state() == 0, d.base_state())

MISION = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'mision1.json'), encoding='utf-8'))

def prueba_datos():
    """La misión en datos: todo texto del C++ está en mision1.json, y el director tiene lo que dice el .json."""
    d = director()
    src = ''
    for f in ('TarsisDirector.cpp', 'TarsisGuard.cpp', 'TarsisHUD.cpp'):
        src += open(os.path.join(ROOT, 'unreal', 'Source', 'Tarsis', f), encoding='utf-8').read()
    claves = set(re.findall(r'(?:Tx|Teach)\(TEXT\("([a-z0-9_]+)"\)', src))
    claves |= {'voz_' + k for k in re.findall(r'Key == TEXT\("([a-z]+)"\)\) T = TEXT', src)}
    t = MISION['textos']
    check('todas las claves del C++ tienen texto en mision1.json', claves and not (claves - set(t)), sorted(claves - set(t)))
    usadas = {x for pt in MISION['puntos'] for k, x in pt.items() if k in ('aviso', 'aviso_cerrado', 'si_falta_texto', 'texto', 'punto_de_control')}
    usadas |= {o['texto'] for o in MISION['objetivos']}
    check('los puntos y objetivos solo usan claves que existen', not (usadas - set(t)), sorted(usadas - set(t)))
    check('textos en ASCII (la fuente del HUD no lleva tildes)', all(ord(c) < 128 for v in t.values() for c in v),
          [k for k, v in t.items() if any(ord(c) > 127 for c in v)][:5])
    check('el director tiene los textos del .json', len(d.get_editor_property('texts')) == len(t), '%d de %d' % (len(d.get_editor_property('texts')), len(t)))
    check('y los %d puntos y %d objetivos' % (len(MISION['puntos']), len(MISION['objetivos'])),
          len(d.get_editor_property('points')) == len(MISION['puntos']) and len(d.get_editor_property('objectives')) == len(MISION['objetivos']))
    yield 0.1

def prueba_zona():
    """El barracón oeste vestido (tanda 18): atrezo, taquillas de verdad, el fluorescente que titila y sus sonidos."""
    d = director()
    z = d.zone_counts()
    check('fluorescente que titila, zumbido eléctrico y gotera', (z.x, z.y, z.z) == (1, 1, 1), (z.x, z.y, z.z))
    piezas = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'atrezo.json'), encoding='utf-8'))['piezas']
    puestas = [a for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.StaticMeshActor) if a.get_actor_label().startswith('Atrezo_')]
    check('atrezo colocado (%d piezas)' % len(piezas), len(puestas) == len(piezas), len(puestas))
    taq = unreal.load_asset('/Game/Tarsis/Atrezo/Taquilla/SM_Taquilla')
    usan = [c for c in d.get_components_by_class(unreal.StaticMeshComponent) if c.static_mesh == taq]
    check('las taquillas usan la malla de chapa', taq is not None and len(usan) == len(d.get_editor_property('hide_spots')), len(usan))
    # la gotera solo con lluvia
    w0 = d.get_editor_property('weather')
    gotera = [a for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.AmbientSound) if a.actor_has_tag('lluvia')]
    while d.get_editor_property('weather') != 1:
        d.simulate_key('Y'); yield 0.2
    yield 0.3
    con = gotera and gotera[0].get_component_by_class(unreal.AudioComponent).is_playing()
    while d.get_editor_property('weather') != 0:
        d.simulate_key('Y'); yield 0.2
    yield 0.3
    sin = gotera and gotera[0].get_component_by_class(unreal.AudioComponent).is_playing()
    check('la gotera suena con lluvia y calla sin ella', con and not sin, (con, sin))
    charcos = [a for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.DecalActor) if a.actor_has_tag('lluvia')]
    vis = lambda: [a.decal.is_visible() for a in charcos]
    check('charco y pisadas mojadas solo con lluvia', d.rain_decal_count() == len(charcos) > 0 and not any(vis()), (d.rain_decal_count(), len(charcos), vis()))
    while d.get_editor_property('weather') != w0:
        d.simulate_key('Y'); yield 0.2

def aparte():
    """Aparca al jugador lejos de todas las rondas (en la marisma, al oeste): entre pruebas, que nadie le vea ni le coja."""
    p = jugador()
    p.set_actor_location(V(-33900, -34700, 100), False, True)

def detras_de(g, d=130.0):
    """Pone al jugador a d cm a la espalda del guardia, mirándole."""
    l = g.get_actor_location(); f = g.get_actor_forward_vector()
    p = jugador(); p.set_actor_location(V(l.x - f.x * d, l.y - f.y * d, max(p.get_actor_location().z, 100)), False, True)
    mirar(V(l.x, l.y, l.z))

def a_la_vista_de(g, d=150.0):
    """Pone al jugador a d cm del guardia, en una dirección que este vea sin paredes ni muebles por medio."""
    l = g.get_actor_location(); f = g.get_actor_forward_vector()
    base = math.atan2(f.y, f.x)
    p = jugador()
    for k in (0, 1, -1, 2, -2, 3, -3, 4):
        a = base + k * math.pi / 4
        q = V(l.x + math.cos(a) * d, l.y + math.sin(a) * d, max(p.get_actor_location().z, 100))
        h = unreal.SystemLibrary.line_trace_single(mundo(), V(l.x, l.y, l.z + 60), V(q.x, q.y, q.z + 20), unreal.TraceTypeQuery.ECC_VISIBILITY, False, [g, p], unreal.DrawDebugTrace.NONE, True)
        if not h:
            p.set_actor_location(q, False, True)
            return True
    return False

def delante_de(g, d=120.0):
    l = g.get_actor_location(); f = g.get_actor_forward_vector()
    p = jugador(); p.set_actor_location(V(l.x + f.x * d, l.y + f.y * d, max(p.get_actor_location().z, 100)), False, True)
    mirar(V(l.x, l.y, l.z))

def agachado():
    return jugador().get_editor_property('is_crouched')

def prueba_empezar():
    d = director()
    inicio = jugador().get_actor_location()
    check('consejo al empezar', str(d.get_editor_property('hint')).startswith('CONSEJO'), d.get_editor_property('hint'))
    # teclas de verdad: PlayerController.InputKey pasa por toda la pila de entrada (no como PressKey)
    d.simulate_key('C'); yield 0.4
    check('tecla C de verdad: te agachas', agachado())
    check('el consejo pasa a la piedra', d.get_editor_property('hint_step') >= 1, d.get_editor_property('hint'))
    d.simulate_key('C'); yield 0.4
    check('C otra vez: de pie', not agachado())
    s0 = d.get_editor_property('last_stone'); s0 = V(s0.x, s0.y, s0.z)   # copia: el struct es una referencia viva
    d.simulate_key('Q'); yield 0.3
    s1 = d.get_editor_property('last_stone')
    check('tecla Q de verdad: lanza una piedra', dist2d(s0, s1) > 1, s1)
    d.simulate_key('B'); yield 0.2
    check('tecla B de verdad: prismáticos', d.get_editor_property('binoculars'))
    d.simulate_key('B'); yield 0.2
    w0 = d.get_editor_property('weather')
    d.simulate_key('Y'); yield 0.2
    check('tecla Y de verdad: cambia el clima', d.get_editor_property('weather') != w0, '%d -> %d' % (w0, d.get_editor_property('weather')))
    while d.get_editor_property('weather') != w0:
        d.simulate_key('Y'); yield 0.2
    d.simulate_key('LeftShift', True, False); yield 0.2
    check('Mayús de verdad: corres', d.get_editor_property('sprint'))
    d.simulate_key('LeftShift', False, True); yield 0.2
    check('al soltar Mayús dejas de correr', not d.get_editor_property('sprint'))
    d.simulate_key('P'); yield 0.2
    check('tecla P de verdad: menú', d.get_editor_property('menu'))
    d.simulate_key('P'); yield 0.2
    check('P otra vez: se cierra', not d.get_editor_property('menu'))
    # el primer guardia de tu ruta: agachado y por la espalda, sin suerte, se le derriba con la E de verdad
    # (antes, que se les pase la piedra de arriba: el que la oyó va a mirar y vuelve)
    yield ('hasta', lambda: all(estado(x) == 'PATROL' for x in guardias() if not x.get_editor_property('tower_sentry')), 30.0)
    # (Ramos no: a él la E le agarra para hablar)
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry') and estado(g) == 'PATROL' and not g.get_actor_label().endswith('Ramos')]
    g = min(ronda, key=lambda x: dist2d(x.get_actor_location(), inicio))
    g.set_editor_property('knock_out_time', 4.0)   # que se levante pronto: lo usan otras pruebas
    d.simulate_key('C'); yield 0.3
    visto = False
    for _ in range(8):
        detras_de(g, 130); yield 0.1
        visto = visto or estado(g) in ('ALERT', 'SUSPICIOUS')
    check('por la espalda y agachado no te nota', not visto, '%s %s' % (g.get_actor_label()[8:], estado(g)))
    detras_de(g, 90)   # el último paso, pegado a él (con el editor a pocos fps se aleja entre tick y tick)
    check('aviso "E DERRIBAR" por la espalda', 'DERRIBAR' in d.interact_prompt(), d.interact_prompt())
    d.simulate_key('E'); yield 0.3
    check('tecla E de verdad: derribas al primer guardia', estado(g) == 'DOWN', '%s %s' % (g.get_actor_label()[8:], estado(g)))
    check('consejos cumplidos', d.get_editor_property('hint') == '', d.get_editor_property('hint'))
    d.simulate_key('C'); yield 0.3
    aparte()
    yield ('hasta', lambda: estado(g) != 'DOWN', 8.0)

def prueba_frente():
    d = director()
    # de frente y sin que esté en alerta: E empuja y lo aturde; entonces se le derriba por cualquier lado
    c0 = d.get_editor_property('captures')
    m = guardia('Moya')
    yield ('hasta', lambda: estado(m) == 'PATROL', 20.0)
    m.set_editor_property('knock_out_time', 4.0)
    delante_de(m, 120)
    check('aviso "E EMPUJAR" de frente', 'EMPUJAR' in d.interact_prompt(), d.interact_prompt())
    d.simulate_key('E'); yield 0.2
    check('el empujón lo aturde', m.is_stunned(), estado(m))
    check('aturdido no te ve', m.visibility(jugador()) == 0)
    check('dice "¡eh!"', d.get_editor_property('last_voice') == 'moya_eh', d.get_editor_property('last_voice'))
    check('ahora se le derriba de frente', 'DERRIBAR' in d.interact_prompt(), d.interact_prompt())
    d.simulate_key('E'); yield 0.3
    check('derribado tras el empujón', estado(m) == 'DOWN', estado(m))
    aparte()
    # en alerta de frente: la E no hace nada, pero se dice por qué
    pe = guardia('Peris')
    lp = pe.get_actor_location()
    pe.alarm(V(lp.x + 300, lp.y, lp.z)); yield 0.1
    delante_de(pe, 220)
    aviso = d.interact_prompt()
    d.interact()
    msg = str(d.get_editor_property('message'))
    aparte()
    check('en alerta: aviso "TE VE"', 'TE VE' in aviso, aviso)
    check('y la E explica por qué no (la primera vez)', 'DE FRENTE TE VE' in msg, msg[:40])
    taught = [str(x) for x in d.get_editor_property('taught')]
    check('lo enseñado se apunta una sola vez', taught.count('ensena_empujon') == 1 and taught.count('ensena_de_frente') == 1, taught)
    check('sin capturas en esta prueba', d.get_editor_property('captures') == c0, d.get_editor_property('captures'))
    yield ('hasta', lambda: estado(m) != 'DOWN', 8.0)

def prueba_escondites():
    d = director()
    spots, yaws = list(d.get_editor_property('hide_spots')), list(d.get_editor_property('hide_yaws'))
    check('hay taquillas en el barracón y la sala de guardia', len(spots) >= 2, len(spots))
    s, yaw = spots[0], math.radians(yaws[0])
    frente = V(s.x + math.cos(yaw) * 75, s.y + math.sin(yaw) * 75, s.z)
    p = jugador(); p.set_actor_location(V(frente.x, frente.y, max(p.get_actor_location().z, 100)), False, True); yield 0.2
    check('aviso "E ESCONDERTE"', 'ESCONDERTE' in d.interact_prompt(), d.interact_prompt())
    d.interact(); yield 0.3
    check('dentro de la taquilla', d.get_editor_property('hiding') and jugador().get_editor_property('hidden'))
    check('aviso "E SALIR"', 'SALIR' in d.interact_prompt(), d.interact_prompt())
    # un guardia delante, mirando la taquilla: no te ve
    ronda = lambda: [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) in ('PATROL', 'RETURN')]
    yield ('hasta', lambda: len(ronda()) > 0, 30.0)
    g = (ronda() or [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) != 'DOWN'])[0]
    g.set_actor_location(V(s.x + math.cos(yaw) * 220, s.y + math.sin(yaw) * 220, g.get_actor_location().z), False, True)
    g.set_actor_rotation(unreal.Rotator(0, 0, yaws[0] + 180), True)
    yield 0.2
    check('desde fuera no te ven', g.visibility(jugador()) == 0, g.get_actor_label()[8:])
    g.set_actor_location(V(500, 500, g.get_actor_location().z), False, True)   # fuera de en medio (si no, la E le empujaría)
    d.interact(); yield 0.3
    check('E sales de la taquilla', not d.get_editor_property('hiding') and not jugador().get_editor_property('hidden') and dist2d(jugador().get_actor_location(), frente) < 120,
          dist2d(jugador().get_actor_location(), frente))
    # si te ve meterte, el que te persigue te saca (en la otra taquilla, la de la sala de guardia: junto a la del
    # barracón puede haber un caído de otra prueba y la E lo arrastraría)
    c0 = d.get_editor_property('captures')
    s, yaw = spots[-1], math.radians(yaws[-1])
    frente = V(s.x + math.cos(yaw) * 75, s.y + math.sin(yaw) * 75, s.z)
    p = jugador(); p.set_actor_location(V(frente.x, frente.y, max(p.get_actor_location().z, 100)), False, True); yield 0.2
    libres = lambda: [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) in ('PATROL', 'RETURN', 'SEARCH') and x != g]
    yield ('hasta', lambda: len(libres()) > 0, 30.0)
    v = libres()[0] if libres() else g   # si todos están ocupados, el mismo de antes
    v.set_actor_location(V(frente.x + math.cos(yaw) * 600, frente.y + math.sin(yaw) * 600, v.get_actor_location().z), False, True)
    v.alarm(frente)
    d.interact()
    check('te ha visto meterte', d.get_editor_property('hiding'))
    yield ('hasta', lambda: director().get_editor_property('capturing'), 15.0)
    check('al abrirla, la escena de captura', d.get_editor_property('capturing') and not d.get_editor_property('hiding'), d.get_editor_property('capturing'))
    yield ('hasta', lambda: director().get_editor_property('captures') > c0, 5.0)
    check('te saca de la taquilla', d.get_editor_property('captures') > c0 and 'TAQUILLA' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:45])
    check('ya fuera de la taquilla', not d.get_editor_property('hiding') and not jugador().get_editor_property('hidden'))
    aparte()

def prueba_cambios():
    d = director()
    if d.get_editor_property('hiding'):   # por si la prueba anterior se cortó con el jugador en la taquilla
        d.interact(); yield 0.2
    # la jefatura abierta (la llave se cogió en el punto de control): un guardia que la ve abierta va a mirar
    tp(900, 3100 - 120, 90); yield 0.2
    if not d.get_editor_property('jef_open'):
        d.interact(); yield 0.2
    check('jefatura abierta', d.get_editor_property('jef_open'))
    aparte()
    n0 = d.get_editor_property('changes_noticed')
    ronda = lambda: [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and not x.is_investigating()]
    yield ('hasta', lambda: len(ronda()) > 0, 40.0)
    g = ronda()[0]
    g.hold(30.0)
    for lado in (-1, 1):
        g.set_actor_location(V(900, 3100 + lado * 450, g.get_actor_location().z), False, True)
        g.set_actor_rotation(unreal.Rotator(0, 0, -90 if lado > 0 else 90), True)
        yield 1.0
        if d.get_editor_property('changes_noticed') > n0:
            break
    g.hold(0.0)
    check('nota la puerta abierta', d.get_editor_property('changes_noticed') > n0, g.get_actor_label()[8:])
    check('dice "esta puerta estaba cerrada"', g.get_actor_label()[8:].lower() + '_puerta' in list(d.get_editor_property('voice_log')), list(d.get_editor_property('voice_log'))[-4:])
    check('va a mirar', g.is_investigating() or estado(g) == 'SEARCH', estado(g))

def prueba_cuerpo():
    d = director()
    # al ver un cuerpo: va hasta él, se agacha 2 s y avisa por radio; luego la alarma
    # (no el de cerca del generador: lo usan las pruebas de la luz)
    despiertos = lambda: [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL']
    yield ('hasta', lambda: len(despiertos()) >= 2, 40.0)
    caido = max(despiertos(), key=lambda x: dist2d(x.get_actor_location(), GEN))
    # los de las torres, quietos: si uno ve antes el cuerpo, da la voz desde arriba y no hay escena que medir
    torres = [x for x in guardias() if x.get_editor_property('tower_sentry')]
    for x in torres:
        x.hold(20.0)
    caido.set_editor_property('knock_out_time', 60.0)
    caido.knock_out(); yield 0.2
    cl = caido.get_actor_location()
    obs = [x for x in despiertos() if x != caido][0]
    obs.set_actor_location(V(cl.x + 300, cl.y, obs.get_actor_location().z), False, True)
    obs.set_actor_rotation(unreal.Rotator(0, 0, 180), True)
    yield ('hasta', lambda: obs.is_checking_body(), 5.0)
    check('ve el cuerpo y va a mirarlo (sin alarma todavía)', obs.is_checking_body() and estado(obs) != 'ALERT', '%s %s' % (obs.get_actor_label()[8:], estado(obs)))
    check('lo dice él: "¿ese de ahí está en el suelo?"', obs.get_actor_label()[8:].lower() + '_cuerpo' in list(d.get_editor_property('voice_log')), list(d.get_editor_property('voice_log'))[-4:])
    check('sin cartel "HA VISTO A..."', 'EN EL SUELO' not in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:40])
    agach = 0.0
    t0 = time.time()
    while time.time() - t0 < 8.0 and estado(obs) != 'ALERT':
        agach = max(agach, obs.get_editor_property('body_check_t'))
        yield 0.1
    check('se agacha sobre el cuerpo', agach > 1.0, '%.1f s' % agach)
    quien = obs.get_actor_label()[8:].lower()
    check('avisa por radio: "suelo"', quien + '_suelo' in list(d.get_editor_property('voice_log')), list(d.get_editor_property('voice_log'))[-4:])
    check('y da la alarma', estado(obs) == 'ALERT', estado(obs))
    check('base en alerta (indicador del HUD)', d.base_state() == 2, d.base_state())
    yield ('hasta', lambda: 'central_todos' in list(director().get_editor_property('voice_log')), 6.0)
    check('la central por radio: "a todas las unidades"', 'central_todos' in list(d.get_editor_property('voice_log'))
          and any('A todas las unidades' in str(x) for x in d.get_editor_property('subtitle_log')), list(d.get_editor_property('subtitle_log'))[-3:])
    for x in torres:
        x.hold(0.0)
    yield ('hasta', lambda: estado(caido) != 'DOWN', 20.0)   # encontrado, se levanta pronto
    check('el caído se levanta al poco', estado(caido) != 'DOWN', estado(caido))

def encima_de(malla):
    """Un punto sobre una malla de la base (las de la base van una por material y juntan muchas piezas)."""
    for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.StaticMeshActor):
        sm = a.static_mesh_component.static_mesh
        if not sm or sm.get_name() != malla:
            continue
        o, e = a.get_actor_bounds(False)
        for i in range(1, 12):
            for j in range(1, 12):
                p = V(o.x - e.x + 2 * e.x * i / 12, o.y - e.y + 2 * e.y * j / 12, o.z + e.z + 50)
                h = unreal.SystemLibrary.line_trace_single(mundo(), p, V(p.x, p.y, p.z - 600), unreal.TraceTypeQuery.ECC_VISIBILITY, True, [], unreal.DrawDebugTrace.NONE, True)
                if h and h.to_tuple()[9] == a:
                    return V(p.x, p.y, h.to_tuple()[4].z + 5)
    return None

def prueba_guardias():
    d = director()
    suelo = [g for g in guardias() if not g.get_editor_property('tower_sentry')]
    check('ronda a 175 cm/s', all(abs(g.get_editor_property('walk_speed') - 175) < 1 for g in suelo), {g.get_actor_label()[8:]: round(g.get_editor_property('walk_speed')) for g in suelo})
    # nadie va y viene entre dos puntos muy juntos (solo Peris, de la mesa a la puerta) ni se queda andando sin avanzar
    # (ida y vuelta A -> B -> A a menos de 4,5 m sin pararse de verdad en B: parece que se ha quedado en bucle)
    juntos = []
    for g in suelo:
        pts = list(g.get_editor_property('patrol_points'))
        esperas = list(g.get_editor_property('patrol_waits'))
        n = len(pts)
        for i in range(n):
            a, b, c = pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
            if n > 2 and dist2d(a, c) < 50 and 0 < dist2d(a, b) < 450 and not g.get_actor_label().endswith('Peris'):
                espera_b = esperas[(i + 1) % n] if (i + 1) % n < len(esperas) else g.get_editor_property('wait_at_point')
                if espera_b < 4.0:
                    juntos.append('%s (%.1f s en %d)' % (g.get_actor_label()[8:], espera_b, (i + 1) % n))
    check('ninguna ronda en bucle entre puntos juntos', not juntos, juntos)
    pos0 = {g.get_actor_label(): g.get_actor_location() for g in suelo}
    andando = {g.get_actor_label(): 0 for g in suelo}
    for _ in range(16):
        yield 0.5
        for g in suelo:
            if estado(g) == 'PATROL' and g.get_velocity().length() > 40:
                andando[g.get_actor_label()] += 1
    atascados = [k[8:] for k in andando if andando[k] >= 14 and dist2d(guardia(k[8:]).get_actor_location(), pos0[k]) < 300]
    check('nadie anda sin avanzar', not atascados, atascados)
    # pasos a compás de la animación (pie que apoya) y suenan cerca de ti
    m = guardia('Moya')
    yield ('hasta', lambda: m.get_velocity().length() > 60, 10.0)   # que esté andando, no parado en su punto
    s0 = m.get_editor_property('steps_taken'); g0 = d.get_editor_property('guard_steps_played')
    l = m.get_actor_location(); tp(l.x + 500, l.y + 500, 0)
    yield ('hasta', lambda: m.get_editor_property('steps_taken') > s0 and director().get_editor_property('guard_steps_played') > g0, 10.0)
    check('los pasos de los guardias salen de la animación', m.get_editor_property('steps_taken') > s0, '%d -> %d' % (s0, m.get_editor_property('steps_taken')))
    check('y suenan cerca de ti', d.get_editor_property('guard_steps_played') > g0, '%d -> %d' % (g0, d.get_editor_property('guard_steps_played')))
    aparte()
    # un ruido (lo mismo que llama la piedra): se para, gira el cuerpo con suavidad y la cabeza por delante, y lo dice
    d.set_subtitles(True)
    while estado(m) != 'PATROL':
        yield 0.5
    l = m.get_actor_location(); r = m.get_actor_right_vector()
    ruido = V(l.x + r.x * 700, l.y + r.y * 700, l.z)
    m.hear_noise(ruido)
    # el giro se mide mientras se vuelve en el sitio: luego va hacia allí por el camino de la navegación, que rodea
    # muros y cajas, y su rumbo ya no apunta al ruido
    def error_giro():
        l = m.get_actor_location()
        quiere = math.degrees(math.atan2(ruido.y - l.y, ruido.x - l.x))
        return abs((quiere - m.get_actor_rotation().yaw + 540) % 360 - 180)
    cabeza, pasos_giro, vmin, error = 0.0, False, 1e9, 180.0
    for _ in range(12):
        yield 0.1
        error = min(error, error_giro())
        cabeza = max(cabeza, abs(m.get_editor_property('look_yaw')))
        pasos_giro = pasos_giro or m.get_editor_property('turn_stepping')
        if estado(m) == 'SUSPICIOUS': vmin = min(vmin, m.get_velocity().length())
    check('se para al oír el ruido', vmin < 40, round(vmin))
    check('se gira hacia el ruido', error < 30, '%.0f grados de error' % error)
    check('la cabeza se adelanta al cuerpo', cabeza > 6, '%.0f grados' % cabeza)
    check('gira en el sitio dando pasos', pasos_giro)
    check('dice "¿qué ha sido eso?"', d.get_editor_property('last_voice') == 'moya_ruido', d.get_editor_property('last_voice'))
    check('con subtítulo', any('Que ha sido eso' in str(x) for x in d.get_editor_property('subtitle_log')), list(d.get_editor_property('subtitle_log'))[-3:])
    v = [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and x != m][0]
    lv = v.get_actor_location()
    v.alarm(V(lv.x + 300, lv.y, lv.z)); yield 0.3   # a su lado, lejos de ti: que no te capture (la 1.ª captura es al calabozo)
    check('base en alerta (indicador del HUD)', d.base_state() == 2, d.base_state())
    yield ('hasta', lambda: any('Alto' in str(x) for x in director().get_editor_property('subtitle_log')), 6.0)   # puede ir en cola
    check('al dar la alarma: "¡alto!"', any(str(x).endswith('_alto') for x in d.get_editor_property('voice_log')) and any('Alto' in str(x) for x in d.get_editor_property('subtitle_log')),
          '%s | %s' % (list(d.get_editor_property('voice_log'))[-3:], list(d.get_editor_property('subtitle_log'))[-2:]))
    faltan = ['%s_%s' % (g, k) for g in ('ibarra', 'moya', 'peris', 'vega', 'ramos', 'centinela')
              for k in ('quien', 'ruido', 'viento', 'alto', 'nadie', 'suelo', 'puerta', 'luz', 'donde', 'eh',
                        'farol', 'cuerpo', 'despierta', 'tengo', 'perdido', 'yacasi')]
    faltan += ['central_' + k for k in ('todos', 'responde', 'luz', 'comova', 'reserva')]
    faltan = [x for x in faltan if not unreal.load_object(None, '/Game/Tarsis/Sonidos/voz_%s.voz_%s' % (x, x))]
    check('voces de los seis guardias y de la central importadas', not faltan, faltan)
    d.set_subtitles(False)
    # superficies: lo que pisas decide el sonido y lo lejos que se oyen tus pasos
    t1 = guardia('torre1').get_actor_location()
    sup = {'grava': V(4300, 2400, 100), 'madera': V(t1.x, t1.y, t1.z), 'metal': encima_de('contenedor_0'),
           'cemento': encima_de('base_suelo_int'), 'hierba': encima_de('base_marisma')}
    malas = {k: (d.surface_at(p) if p else None) for k, p in sup.items() if not p or d.surface_at(p) != k}
    check('superficies: grava, cemento, metal, madera, hierba', not malas, malas)
    # tus pasos dentro del barracón suenan a cemento
    p = jugador()
    if agachado():   # de pie: agachado los pasos casi no suenan y la zancada es otra
        d.simulate_key('C'); yield 0.3
    # Ramos hace la ronda por este barracón: si ve al jugador lo coge y la escena de captura bloquea el movimiento
    # (por eso esta comprobación fallaba a veces). Quietos todos mientras se anda
    for g in guardias():
        g.hold(6.0)
    if d.get_editor_property('capturing'):
        yield ('hasta', lambda: not director().get_editor_property('capturing'), 5.0)
    p.set_actor_location(V(700, 2600, 110), False, True)   # al oeste del pasillo central del barracón
    # por si una prueba anterior lo dejó cayendo o con el movimiento bloqueado (cinemática, menú)
    p.get_component_by_class(unreal.CharacterMovementComponent).set_movement_mode(unreal.MovementMode.MOVE_WALKING)
    unreal.GameplayStatics.get_player_controller(mundo(), 0).reset_ignore_move_input()
    yield 0.2
    n0 = d.get_editor_property('player_steps')
    t0 = time.time()
    while time.time() - t0 < 2.0 and p.get_actor_location().x < 2000:
        # por el pasillo central del barracón, en un solo sentido. La entrada se da en CADA fotograma: si se da
        # cada 0,03 s y el juego va a más de 60 fps, entre medias frena y el jugador apenas avanza (17 cm/s)
        p.add_movement_input(V(1, 0, 0), 1.0); yield 0.0
    check('tus pasos suenan según el suelo', d.get_editor_property('player_steps') > n0 and d.get_editor_property('last_step_surface') == 'cemento',
          '%d pasos, %s, en x %.0f, agachado %s' % (d.get_editor_property('player_steps') - n0, d.get_editor_property('last_step_surface'), p.get_actor_location().x, agachado()))
    aparte()

def prueba_menu():
    d = director()
    pc = unreal.GameplayStatics.get_player_controller(mundo(), 0)
    def giro():
        pc.set_control_rotation(unreal.Rotator(0, 0, 0))
        pc.add_yaw_input(5.0)
        pc.add_pitch_input(5.0)
    giro(); yield 0.3
    r = pc.get_control_rotation(); base_yaw, base_pitch = r.yaw, (r.pitch + 180) % 360 - 180
    d.press_key('P'); yield 0.2
    check('P abre el menú y pausa', d.get_editor_property('menu') and unreal.GameplayStatics.is_game_paused(mundo()))
    lineas = list(d.menu_lines())
    check('el menú tiene sus 15 líneas', len(lineas) == 15, ' / '.join(lineas))
    sens0 = float(lineas[2].split('<')[1].split('>')[0])
    for k in ('Down', 'Down', 'Right', 'Right', 'Right', 'Right', 'Right'):
        d.press_key(k); yield 0.1
    sens1 = float(list(d.menu_lines())[2].split('<')[1].split('>')[0])
    check('Derecha sube la sensibilidad', abs(sens1 - min(3.0, sens0 + 0.5)) < 0.01, '%.1f -> %.1f' % (sens0, sens1))
    d.press_key('P'); yield 0.2
    check('P cierra el menú y reanuda', not d.get_editor_property('menu') and not unreal.GameplayStatics.is_game_paused(mundo()))
    giro(); yield 0.3
    r = pc.get_control_rotation()
    esperado = base_yaw * sens1 / sens0 if sens0 else 0
    check('la sensibilidad cambia el giro', abs(r.yaw - esperado) < 0.2, 'yaw %.2f (esperado %.2f)' % (r.yaw, esperado))
    # dejarla como estaba
    d.press_key('P'); yield 0.1
    for k in ('Down', 'Down') + ('Left',) * 5:
        d.press_key(k); yield 0.1
    d.press_key('P'); yield 0.2
    check('sensibilidad restaurada', abs(float(list(d.menu_lines())[2].split('<')[1].split('>')[0]) - sens0) < 0.01)

def prueba_dardos():
    d = director()
    r = guardia('Ramos')
    derribar(r); yield 0.2
    junto_a(r); yield 0.2
    d.interact(); yield 0.2
    tp(4660, 420, -90); yield 0.2
    d.interact(); yield 0.3
    check('el botiquín da 5 dardos', d.get_editor_property('darts') == 5, d.get_editor_property('darts'))
    # con la pistola, los brazos suben a la vista (unos 0,3 s) con la pistola en la mano derecha
    yield ('hasta', lambda: director().get_editor_property('arms_visible'), 3.0)
    arms, pistola = d.get_editor_property('arms'), d.get_editor_property('pistol')
    check('brazos en primera persona visibles', d.get_editor_property('arms_visible') and arms and arms.is_visible(), arms)
    check('pistola en la mano (HandGrip_R)', pistola is not None and pistola.is_visible() and pistola.get_attach_parent() == arms
          and str(pistola.get_attach_socket_name()) == 'HandGrip_R', pistola.get_attach_socket_name() if pistola else None)
    v = guardia('Vega')
    l = v.get_actor_location(); f = v.get_actor_forward_vector()
    p = jugador(); p.set_actor_location(V(l.x - f.x * 500, l.y - f.y * 500, max(p.get_actor_location().z, 100)), False, True)
    mirar(V(l.x, l.y, l.z + 20)); yield 0.2
    d.shoot_dart(); yield 0.3
    check('el dardo duerme a Vega', estado(v) == 'DOWN' and d.get_editor_property('darts') == 4, '%s, %d dardos' % (estado(v), d.get_editor_property('darts')))
    check('la primera vez se explica', 'DORMIDO' in str(d.get_editor_property('message')) and 'ensena_dormido' in [str(x) for x in d.get_editor_property('taught')], str(d.get_editor_property('message'))[:30])
    junto_a(v); yield 0.3
    check('aviso de recuperar el dardo', 'RECUPERAR EL DARDO' in d.interact_prompt(), d.interact_prompt())
    d.interact(); yield 0.3
    check('se recupera el dardo', d.get_editor_property('darts') == 5, d.get_editor_property('darts'))
    check('después se puede arrastrar', 'ARRASTRAR' in d.interact_prompt(), d.interact_prompt())

def prueba_punto_control():
    d = director()
    i = guardia('Ibarra')
    derribar(i); yield 0.2
    junto_a(i); yield 0.2
    d.interact(); yield 0.3
    check('se coge la llave', d.get_editor_property('key'))
    check('punto de control guardado', d.get_editor_property('checkpoint_name') == 'LA LLAVE DE IBARRA', d.get_editor_property('checkpoint_name'))
    sitio = jugador().get_actor_location()
    c0 = d.get_editor_property('captures')
    pe = guardia('Peris')
    for n in (1, 2):
        a_la_vista_de(pe, 150)   # en su mesa mira a la pared: «delante» podía quedar tras ella
        pe.alarm(jugador().get_actor_location())
        yield ('hasta', lambda: director().get_editor_property('captures') >= c0 + n, 25.0)
        msg = str(d.get_editor_property('message'))   # en el momento: otro aviso podría taparlo después
        yield 0.3
        pos = jugador().get_actor_location()
        if n == 1:
            check('1.ª captura: al calabozo', 'CALABOZO' in msg or c0 > 0, '%s (capturas antes: %d; Peris %s, ve %.2f, a %d cm, jugador oculto %s, colisión %s)' % (msg[:30], c0, estado(pe), pe.visibility(jugador()), dist2d(pe.get_actor_location(), jugador().get_actor_location()), jugador().get_editor_property('hidden'), jugador().get_actor_enable_collision()))
        else:
            check('2.ª captura: vuelve junto a Ibarra', dist2d(pos, sitio) < 150, 'a %d cm del punto' % dist2d(pos, sitio))

def prueba_captura():
    d = director()
    pc = unreal.GameplayStatics.get_player_controller(mundo(), 0)
    c0 = d.get_editor_property('captures')
    ronda = lambda: [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and not x.get_actor_label().endswith('Ramos')]
    yield ('hasta', lambda: len(ronda()) > 0, 30.0)
    g = ronda()[0]
    a_la_vista_de(g, 150)
    g.alarm(jugador().get_actor_location())
    yield ('hasta', lambda: director().get_editor_property('capturing'), 10.0)
    check('te coge: empieza la escena', d.get_editor_property('capturing'), estado(g))
    check('dice "¡te tengo!"', g.get_actor_label()[8:].lower() + '_tengo' in list(d.get_editor_property('voice_log')), list(d.get_editor_property('voice_log'))[-3:])
    check('sin control durante la escena', pc.is_move_input_ignored() and pc.is_look_input_ignored())
    check('aún no te ha llevado (primero la escena)', d.get_editor_property('captures') == c0)
    yield 0.6
    cam = jugador().get_component_by_class(unreal.CameraComponent).get_world_location()
    gl = g.get_actor_location()
    quiere = math.degrees(math.atan2(gl.y - cam.y, gl.x - cam.x))
    err = abs((quiere - pc.get_control_rotation().yaw + 540) % 360 - 180)
    check('la cámara se vuelve hacia él', err < 30, '%.0f grados' % err)
    yield ('hasta', lambda: director().get_editor_property('captures') > c0, 4.0)
    check('golpe, negro y al calabozo', d.get_editor_property('captures') == c0 + 1 and 'CALABOZO' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:30])
    yield ('hasta', lambda: not director().get_editor_property('capturing'), 4.0)
    check('vuelves a tener el control', not pc.is_move_input_ignored() and not pc.is_look_input_ignored())

def prueba_perdido():
    d = director()
    aparte()
    ronda = lambda: [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) in ('PATROL', 'RETURN') and not x.get_actor_label().endswith('Ramos')]
    yield ('hasta', lambda: len(ronda()) > 0, 30.0)
    g = ronda()[0]
    l = g.get_actor_location()
    g.alarm(V(l.x + 250, l.y, l.z))
    yield ('hasta', lambda: estado(g) == 'SEARCH', 20.0)
    yield 0.3
    quien = g.get_actor_label()[8:].lower()
    check('al perderte: "lo he perdido"', quien + '_perdido' in list(d.get_editor_property('voice_log')), '%s %s' % (estado(g), list(d.get_editor_property('voice_log'))[-3:]))
    # el subtítulo puede esperar en cola a que acabe el anterior
    yield ('hasta', lambda: any('Lo he perdido' in str(x) for x in director().get_editor_property('subtitle_log')), 8.0)
    check('con subtítulo aunque la opción esté apagada', 'SUBTITULOS DE SONIDOS   < NO' in ' '.join(d.menu_lines()) and any('Lo he perdido' in str(x) for x in d.get_editor_property('subtitle_log')),
          list(d.get_editor_property('subtitle_log'))[-2:])

def prueba_generador():
    d = director()
    on0, off0 = luces()
    tp(4300, 1910, -90); yield 0.1
    d.interact(); yield 0.1
    aparte()
    check('se corta el generador', d.get_editor_property('power_off'))
    yield 3.0
    on, off = luces()
    check('apagón en cadena: todas las luces fuera', len(on) == 0, 'encendidas %s' % on)
    # la central habla 1,6 s después del corte; su subtítulo espera en cola a que acaben los de los guardias
    yield ('hasta', lambda: any('Se ha ido la luz' in str(x) for x in director().get_editor_property('subtitle_log')), 10.0)
    check('la central por radio (voz y subtítulo)', 'central_luz' in list(d.get_editor_property('voice_log'))
          and any('Se ha ido la luz' in str(x) for x in d.get_editor_property('subtitle_log')), list(d.get_editor_property('subtitle_log'))[-3:])
    check('base en guardia (indicador del HUD)', d.base_state() >= 1, d.base_state())
    despiertos = [g for g in guardias() if not g.get_editor_property('tower_sentry') and estado(g) != 'DOWN']
    linternas = [g.get_actor_label()[8:] for g in despiertos if any(c.is_visible() for c in g.get_components_by_class(unreal.SpotLightComponent))]
    check('los guardias de suelo despiertos sacan linterna', len(linternas) == len(despiertos), '%s de %s' % (linternas, [g.get_actor_label()[8:] for g in despiertos]))
    yield ('hasta', lambda: not director().get_editor_property('power_off'), 70.0)
    on, off = luces()
    msg = str(d.get_editor_property('message'))
    check('un guardia lo arregla y vuelven todas', 'ha arrancado' in msg and len(on) == len(on0), '%s | %d de %d' % (msg[:40], len(on), len(on0)))

def prueba_reserva():
    d = director()
    tp(4300, 1910, -90); yield 0.1
    d.interact(); yield 0.1
    aparte()
    # en cuanto llega a su sitio (si se espera a la radio de los 15 s, uno que esté cerca ya lo ha arreglado)
    # el que manda el director (no siempre el más cercano al sitio)
    rep_d = lambda: director().get_editor_property('repairer')
    yield ('hasta', lambda: rep_d() is not None and dist2d(rep_d().get_actor_location(), SITIO) < 250, 30.0)
    rep = rep_d() or reparador_cercano()[1]
    dd = dist2d(rep.get_actor_location(), SITIO)
    check('el reparador está en su sitio', dd < 400, '%s a %d cm' % (rep.get_actor_label(), dd))
    derribar(rep)
    # los demás, quietos mientras entra la reserva: si uno encuentra al reparador en el suelo, este se levanta antes
    # de que la radio pregunte y la prueba mediría otra cosa
    otros = [g for g in guardias() if g != rep and not g.get_editor_property('tower_sentry') and estado(g) != 'DOWN']
    for g in otros:
        g.hold(25.0)
    yield ('hasta', lambda: not director().get_editor_property('power_off'), 20.0)
    for g in otros:
        g.hold(0.0)
    yield 0.5
    on, off = luces()
    check('vuelve la luz a medias', 'A MEDIAS' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:30])
    check('la central: "entra la reserva"', 'central_reserva' in list(d.get_editor_property('voice_log')), list(d.get_editor_property('voice_log'))[-4:])
    # por nombre de familia: el número depende del orden de las luces de base.json (la farola de la entrada, tanda 20, las corrió)
    torres = [n for n in on + off if n.startswith('foco_torreta')]
    check('los focos de las torres vuelven', len(torres) >= 2 and all(n in on for n in torres), on)
    # la mitad de las que estaban encendidas (sin las de las torres ni interior_0, que el barracón oeste tiene apagada)
    resto_on = [x for x in on if not x.startswith('foco_torreta') and x != 'interior_0']
    resto_off = [x for x in off if x != 'interior_0']
    k = len(resto_off) / max(1, len(resto_on) + len(resto_off))
    check('queda apagada la mitad del resto', 0.3 <= k <= 0.7, '%.0f %% apagadas: %s' % (k * 100, resto_off))
    check('el reparador sigue en el suelo', estado(rep) == 'DOWN', estado(rep))
    yield 6.0
    llegan = [g.get_actor_label()[8:] for g in guardias() if dist2d(g.get_actor_location(), GEN) < 400 and estado(g) != 'DOWN']
    check('los alertados por radio llegan al generador', len(llegan) >= 1, llegan)

def prueba_farol():
    d = director()
    quietos('Sanz', 'Carmona')   # el centinela del control está a 4 m: esta prueba mide el farol, no su vista
    antes = luz_en(V(8620, 5600, 130))
    tp(8150, 5700, 0); yield 0.1
    mirar(FAROL); yield 0.2
    d.shoot_dart(); yield 0.2
    aparte(); yield 0.3
    despues = luz_en(V(8620, 5600, 130))
    check('el dardo rompe el farol', 'FAROL ROTO' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:30])
    check('el control queda a oscuras', despues < antes, '%.2f -> %.2f' % (antes, despues))

def prueba_final():
    d = director()
    # sin el expediente, el portón de salida no te deja irte: aviso y la misión sigue
    tp(SALIDA.x, SALIDA.y, 0); yield 0.4
    check('sin el expediente la salida avisa y no acaba', not d.get_editor_property('done') and 'NO PUEDES IRTE' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:40])
    tp(1300, 3500, 90); yield 0.2
    d.interact(); yield 0.2
    for c in str(d.get_editor_property('vault_code')):
        d.keypad_digit(int(c))
    yield 0.3
    tp(1900, 3500, 90); yield 0.2
    d.interact(); yield 0.3
    check('se coge el expediente', d.get_editor_property('file'))
    tp(SALIDA.x, SALIDA.y, 0)
    yield ('hasta', lambda: director().get_editor_property('done'), 5.0)
    check('final por la salida', d.get_editor_property('done') and 'MISION CUMPLIDA' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:30])
    check('cinemática LS_Salida', d.get_editor_property('cine'))
    check('puntuación de sigilo en el final', 'SIGILO:' in str(d.get_editor_property('message')) and d.get_editor_property('rank') != '', '%s %s' % (d.get_editor_property('score'), d.get_editor_property('rank')))
    yield ('hasta', lambda: director().get_editor_property('report'), 25.0)
    rl = list(d.get_editor_property('report_lines'))
    check('sale el parte del día siguiente', d.get_editor_property('report') and len(rl) > 5 and rl[0] == 'PARTE DEL DIA SIGUIENTE', ' | '.join(rl[:4]))
    check('el parte recoge el farol roto y la llave', any('farol' in x for x in rl) and any('Ibarra' in x for x in rl), ' | '.join(rl))
    # el HUD cuenta fotogramas dibujados: con el editor en segundo plano (3-8 fps) medio segundo no llega a 5
    yield ('hasta', lambda: director().get_editor_property('report_frames') > 5, 5.0)
    check('el parte se dibuja en pantalla', d.get_editor_property('report_frames') > 5, d.get_editor_property('report_frames'))
    check('el parte se guarda para la misión 2', unreal.GameplayStatics.does_save_game_exist('TarsisParte', 0))
    if 'musica_t0' in R:
        capas = capas_musica()
        check('la música sigue en bucle pasados 32 s', len(capas) == 3 and all(c.is_playing() for c in capas.values()) and time.time() - R['musica_t0'] > 32, '%d s, %s' % (time.time() - R['musica_t0'], {k: c.is_playing() for k, c in capas.items()}))


def prueba_perimetro():
    """Tanda 20: muro 20 m más afuera, camino de portón a portón, portillo en el muro sur y la salida en el portón este."""
    d = director()
    w = mundo()
    quietos('Lobato', 'Sanz', 'Carmona')
    def traza(a, b):
        h = unreal.SystemLibrary.line_trace_single(w, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [jugador()], unreal.DrawDebugTrace.NONE, True)
        return h.to_tuple()[4].x if h else None
    # desde la franja nueva (dentro del muro nuevo), hacia fuera: el muro está 20 m más allá del antiguo
    xo = traza(V(-1000, 2800, 150), V(-4000, 2800, 150))
    xe = traza(V(8500, 1500, 150), V(12000, 1500, 150))
    check('el muro nuevo está al oeste (x -1855) y al este (x 9055)', xo is not None and xe is not None and abs(xo + 1855) < 120 and abs(xe - 9055) < 120, (xo, xe))
    # los guardias pueden ir por el camino de un portón al otro
    ruta = unreal.NavigationSystemV1.find_path_to_location_synchronously(w, V(-1000, 5700, 100), V(8500, 5700, 100))
    pts = list(ruta.get_editor_property('path_points')) if ruta else []
    check('hay ruta de navegación por el camino', len(pts) > 1 and dist2d(pts[-1], V(8500, 5700, 0)) < 150 and not ruta.is_partial(), '%d puntos%s' % (len(pts), ', parcial' if ruta and ruta.is_partial() else ''))
    # el tope invisible tras el portón de salida
    topes = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor) if a.actor_has_tag('Tope_Salida')]
    check('tope invisible fuera del portón de salida', len(topes) == 1 and topes[0].get_editor_property('hidden') and dist2d(topes[0].get_actor_location(), V(9280, 5700, 0)) < 50, len(topes))
    topes = actores('Tope_Entrada')
    check('y otro fuera del portón de entrada (se abre para el camión)', len(topes) == 1 and topes[0].get_editor_property('hidden') and dist2d(topes[0].get_actor_location(), V(-2010, 5700, 0)) < 50, len(topes))
    # el portillo avisa en su sitio nuevo (sin Ramos, cerrado)
    tp(PORTILLO.x, PORTILLO.y - 120, 90); yield 0.2
    check('el aviso del portillo sale en el muro sur', 'PORTILLO' in d.interact_prompt(), d.interact_prompt()[:30])
    d.interact(); yield 0.2
    check('el portillo sin Ramos está cerrado', 'PORTILLO DE LA MARISMA' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:40])
    # la partida sigue empezando donde siempre
    ps = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PlayerStart)
    check('el jugador sigue empezando en (500, 500)', ps and dist2d(ps[0].get_actor_location(), V(500, 500, 0)) < 150, [ps[0].get_actor_location() if ps else None])
    aparte()


def prueba_anillo():
    """Tanda 21: el anillo deja de estar vacío y a oscuras: farolas en el camino, aplique en el portillo, la tela de las
    vallas como malla de verdad y tres guardias (uno en cada garita y la ronda del sur)."""
    d = director()
    w = mundo()
    aparte()
    ext = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']
    focos = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Light) if a.get_component_by_class(unreal.LocalLightComponent)]
    def hay_luz(q):
        return any(dist2d(a.get_actor_location(), V(q[0] * 100, q[1] * 100, 0)) < 150 and a.get_component_by_class(unreal.LocalLightComponent).is_visible() for a in focos)
    check('tres farolas encendidas a lo largo del camino', len(ext['farolas']) == 3 and all(hay_luz(q) for q in ext['farolas']), [hay_luz(q) for q in ext['farolas']])
    check('aplique encendido sobre el portillo', hay_luz(ext['portillo_luz']), ext['portillo_luz'])
    # el camino bajo una farola está claro; el anillo, a media distancia entre el camino y el muro, sigue oscuro
    f = ext['farolas'][1]
    clara, oscura = luz_en(V(f[0] * 100, 5700, 100)), luz_en(V(f[0] * 100 + 1250, 6950, 100))
    check('charco de luz en el camino y sombra entre farolas', clara > 0.5 and oscura < 0.3, '%.2f y %.2f' % (clara, oscura))
    portillo = luz_en(V(PORTILLO.x, PORTILLO.y - 150, 100))
    check('el portillo ya no está a oscuras (pero tampoco a plena luz)', 0.13 < portillo < 0.6, '%.2f' % portillo)
    telas = set()
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor):
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        m = c.get_material(0) if c and c.get_num_materials() else None
        if m and m.get_name().startswith('M_Tela'):
            telas.add(m.get_name())
    check('la tela de las vallas es la malla recortada', telas and all(n.startswith('M_TelaMalla_') for n in telas), sorted(telas))
    # los tres guardias nuevos, en su sitio, fuera del camino y con su voz
    sitios = {'Lobato': V(-1300, 5300, 0), 'Sanz': V(8500, 5300, 0), 'Carmona': V(-900, 6700, 0)}
    gs = {n: guardia(n) for n in sitios}
    check('Lobato, Sanz y Carmona están en el nivel', all(gs.values()), [n for n, g in gs.items() if not g])
    if not all(gs.values()):
        return
    lejos = {n: int(dist2d(g.get_actor_location(), sitios[n])) for n, g in gs.items()}
    check('cada uno empieza en su puesto', all(v < 400 for v in lejos.values()), lejos)
    check('tienen cuerpo (no el cilindro)', all(g.get_editor_property('body_mesh') for g in gs.values()))
    voces = ['voz_%s_%s' % (n.lower(), k) for n in gs for k in ('quien', 'alto', 'perdido')]
    faltan = [v for v in voces if not unreal.EditorAssetLibrary.does_asset_exist('/Game/Tarsis/Sonidos/' + v)]
    check('cada uno tiene su voz', not faltan, faltan)
    c0 = gs['Carmona'].get_actor_location()
    pisan = set()
    t1 = time.time() + 14.0
    while time.time() < t1:
        for n, g in gs.items():
            l = g.get_actor_location()
            if abs(l.y - 5700) < 330 and -1800 < l.x < 9000:
                pisan.add(n)
        yield 0.5
    check('la ronda del anillo anda', dist2d(gs['Carmona'].get_actor_location(), c0) > 300, int(dist2d(gs['Carmona'].get_actor_location(), c0)))
    check('ninguno pisa el camino (por ahí pasa el camión)', not pisan, sorted(pisan))
    check('nadie se ha mosqueado con el jugador aparcado', all(estado(g) == 'PATROL' for g in gs.values()), {n: estado(g) for n, g in gs.items()})


def prueba_camion():
    """Tanda 21: el camión de suministros entra por el portón oeste (la hoja se corre), cruza por el camino, para en el
    control (la barrera sube) y sale por el este. Sus faros alumbran, el conductor ve y frena si te pones delante."""
    d = director()
    w = mundo()
    piezas, hoja = actores('camion'), actores('hoja_entrada')
    check('el camión y la hoja del portón están en el nivel', len(piezas) >= 5 and len(hoja) >= 1, '%d piezas, %d de la hoja' % (len(piezas), len(hoja)))
    if not piezas or not hoja:
        return
    estado_c = lambda: director().get_editor_property('truck_state')
    cx = lambda: director().truck_location().x
    check('espera fuera, escondido', estado_c() == 0 and all(a.get_editor_property('hidden') for a in piezas), estado_c())
    check('la hoja del portón de entrada, cerrada', d.get_editor_property('entry_gate_t') < 0.01 and abs(hoja[0].get_actor_location().y) < 5, hoja[0].get_actor_location().y)
    # pasada corta: sale de más cerca y desaparece antes (lo de en medio es lo que se prueba)
    d.set_editor_property('truck_start', V(-7000, 5700, 4))
    d.set_editor_property('truck_end_x', 13000.0)
    oscuro = luz_en(V(2300, 5700, 100))
    aparte()
    d.truck_skip_wait()
    yield ('hasta', lambda: estado_c() == 1, 3.0)
    faros = actores('camion', unreal.Light)
    check('aparece con los faros encendidos', estado_c() == 1 and not any(a.get_editor_property('hidden') for a in piezas)
          and len(faros) == 1 and faros[0].get_component_by_class(unreal.LocalLightComponent).is_visible(), '%s, %d faros' % (estado_c(), len(faros)))
    yield ('hasta', lambda: 'CAMION' in str(director().get_editor_property('message')), 4.0)
    check('se avisa la primera vez', 'VIENE UN CAMION' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:30])
    yield ('hasta', lambda: estado_c() == 2, 25.0)
    check('para ante el portón cerrado', estado_c() == 2 and abs(cx() + 2420) < 40, '%s en x %d' % (estado_c(), cx()))
    yield ('hasta', lambda: director().get_editor_property('entry_gate_t') > 0.98, 9.0)
    check('la hoja se corre hacia el sur', abs(hoja[0].get_actor_location().y - 640) < 30, hoja[0].get_actor_location().y)
    yield ('hasta', lambda: estado_c() == 3 and cx() > 1300, 25.0)
    claro = luz_en(V(2300, 5700, 100))
    check('los faros alumbran el camino por delante', claro > oscuro + 0.1, '%.2f -> %.2f' % (oscuro, claro))
    check('y la hoja se cierra detrás', d.get_editor_property('entry_gate_t') < 0.9, d.get_editor_property('entry_gate_t'))
    # de pie en el haz, a 15 m: el conductor te ve y toca el claxon; los guardias de cerca van a mirar
    h0 = d.get_editor_property('truck_horns')
    tp(cx() + 1700, 5700, 180)
    yield ('hasta', lambda: director().get_editor_property('truck_horns') > h0, 4.0)
    check('el conductor te ve en el haz y toca el claxon', d.get_editor_property('truck_horns') == h0 + 1 and 'CAMION' in str(d.get_editor_property('message')),
          '%d, %s' % (d.get_editor_property('truck_horns'), str(d.get_editor_property('message'))[:24]))
    yield 0.4
    mosca = [g.get_actor_label()[8:] for g in guardias() if estado(g) in ('SUSPICIOUS', 'ALERT')]
    check('los guardias de cerca van a mirar', len(mosca) >= 1, mosca)
    # plantado delante: frena en seco y no te pasa por encima
    tp(cx() + 420, 5700, 180); yield 1.2
    x1 = cx(); yield 0.6
    x2 = cx()
    hueco = jugador().get_actor_location().x - x2
    check('frena si te pones delante', abs(x2 - x1) < 3 and hueco > 200, 'se mueve %.1f cm, a %d cm de ti' % (x2 - x1, hueco))
    aparte()
    for g in guardias():   # que no se quede nadie en el camino mirando el ruido: el camión esperaría a que se aparte
        if not g.get_editor_property('tower_sentry'):
            g.hold(3600.0)
            l = g.get_actor_location()
            if abs(l.y - 5700) < 400:
                g.set_actor_location(V(l.x, 6400, l.z), False, True)
    yield 1.5
    check('y sigue cuando te apartas', cx() > x2 + 50, '%d -> %d' % (x2, cx()))
    yield ('hasta', lambda: estado_c() == 4, 40.0)
    check('para en el control de salida', estado_c() == 4 and abs(cx() - 8270) < 40, '%s en x %d' % (estado_c(), cx()))
    check('el portón de entrada ya está cerrado', d.get_editor_property('entry_gate_t') < 0.02 and abs(hoja[0].get_actor_location().y) < 5, d.get_editor_property('entry_gate_t'))
    yield ('hasta', lambda: director().get_editor_property('barrier_t') > 0.95, 12.0)
    check('le levantan la barrera', d.get_editor_property('barrier_t') > 0.95, d.get_editor_property('barrier_t'))
    yield ('hasta', lambda: director().get_editor_property('truck_passes') >= 1, 30.0)
    check('sale por el portón del este y desaparece', d.get_editor_property('truck_passes') == 1 and estado_c() == 0 and all(a.get_editor_property('hidden') for a in piezas),
          '%d pasadas, estado %s' % (d.get_editor_property('truck_passes'), estado_c()))
    yield ('hasta', lambda: director().get_editor_property('barrier_t') < 0.05, 6.0)
    check('la barrera vuelve a bajar', d.get_editor_property('barrier_t') < 0.05, d.get_editor_property('barrier_t'))
    check('la misión sigue (nadie te ha cogido ni has salido)', not d.get_editor_property('done') and not d.get_editor_property('capturing'))


def capas_musica():
    """Componentes de audio de la música (musica_base, _tension y _alerta), estén donde estén."""
    # CreateSound2D no los cuelga de ningún actor: se buscan entre todos los objetos del mundo del PIE
    out = {}
    w = mundo()
    for c in unreal.ObjectIterator(unreal.AudioComponent):
        try:
            cw = c.get_world()   # CreateSound2D sin dueño: sin mundo y con outer /Engine/Transient
            if cw is not None and cw != w:
                continue
            s = c.get_editor_property('sound')
        except Exception:
            continue
        if s and s.get_name().startswith('musica_'):
            out[s.get_name()] = c
    return out

def lineas(d):
    return list(d.menu_lines())

def teclas(d, *ks):
    for k in ks:
        d.press_key(k)
        yield 0.05   # una por tick, como el teclado de verdad

def prueba_musica():
    d = director()
    capas = capas_musica()
    check('suenan las tres capas', len(capas) == 3 and all(c.is_playing() for c in capas.values()), {k: c.is_playing() for k, c in capas.items()})
    R['musica_t0'] = time.time()
    t0 = d.get_editor_property('music_tension')
    g = guardia('Moya')
    l = g.get_actor_location(); f = g.get_actor_forward_vector()
    p = jugador(); p.set_actor_location(V(l.x + f.x * 700, l.y + f.y * 700, max(p.get_actor_location().z, 100)), False, True)
    yield ('hasta', lambda: director().get_editor_property('music_tension') > 0.3, 6.0)
    check('la tensión sube al acercarte a un guardia', d.get_editor_property('music_tension') > 0.3, '%.2f -> %.2f' % (t0, d.get_editor_property('music_tension')))
    tp(500, 500, 0)
    g.alarm(V(500, 500, 0))
    yield ('hasta', lambda: director().get_editor_property('music_alert') > 0.5, 4.0)
    check('la alerta entra con un guardia en alerta', d.get_editor_property('music_alert') > 0.5, '%.2f' % d.get_editor_property('music_alert'))
    base = capas.get('musica_base')
    v0 = base.get_editor_property('volume_multiplier') if base else -1
    # con el menú abierto el juego está en pausa y MusicTick no corre: el volumen se aplica al reanudar
    yield from teclas(d, 'P', *(['Down'] * 7), *(['Left'] * 10), 'P')
    yield 0.5
    v1 = base.get_editor_property('volume_multiplier') if base else -1
    check('MUSICA al 0 % baja la capa base (al reanudar)', v1 <= 0.002, '%.3f -> %.3f' % (v0, v1))
    yield from teclas(d, 'P', *(['Down'] * 7), *(['Right'] * 7), 'P')   # vuelve al 70 %
    yield 0.2
    check('MUSICA restaurada al 70 %', 'MUSICA   < 70 %' in ' '.join(lineas(d)), [x for x in lineas(d) if 'MUSICA' in x])

def prueba_controles():
    d = director()
    yield from teclas(d, 'P', *(['Down'] * 9), 'Enter')
    ls = lineas(d)
    check('CONTROLES abre la página de teclas', len(ls) == 8 and 'VOLVER' in ls[-1], ' / '.join(ls))
    tecla0 = ls[0]
    yield from teclas(d, 'Enter')
    check('Intro no se asigna a sí misma (espera tecla)', 'PULSA UNA TECLA' in lineas(d)[0], lineas(d)[0])
    yield from teclas(d, 'X')
    check('AGACHARSE pasa a X', '[ X ]' in lineas(d)[0], lineas(d)[0])
    check('se captura una sola vez (ya no espera)', 'PULSA' not in ' '.join(lineas(d)))
    interact = lineas(d)[1]
    yield from teclas(d, 'Enter', 'E')
    ls = lineas(d)
    check('si la tecla choca, se intercambian', '[ E ]' in ls[0] and '[ X ]' in ls[1], '%s / %s' % (ls[0], ls[1]))
    yield from teclas(d, *(['Down'] * 6), 'Enter')
    ls = lineas(d)
    check('TECLAS POR DEFECTO lo deshace', ls[0] == tecla0 and ls[1] == interact, '%s / %s' % (ls[0], ls[1]))
    yield from teclas(d, 'Escape')
    check('Esc vuelve a la página principal', len(lineas(d)) == 15, len(lineas(d)))
    yield from teclas(d, 'P')
    check('P cierra el menú', not d.get_editor_property('menu'))


def prueba_opciones():
    d = director()
    yield from teclas(d, 'P', *(['Down'] * 10), 'Right')
    check('DIFICULTAD pasa a DIFICIL', 'DIFICULTAD   < DIFICIL >' in ' '.join(lineas(d)), [x for x in lineas(d) if 'DIFICULTAD' in x])
    check('la dificultad se guarda en el director', d.get_editor_property('difficulty') == 2, d.get_editor_property('difficulty'))
    yield from teclas(d, 'Left', 'Down', 'Right', 'Down', 'Enter', 'Down', 'Enter', 'P')
    ls = ' '.join(lineas(d))
    check('tamaño del texto al 110 %', 'TAMANO DEL TEXTO   < 110 %' in ls, [x for x in lineas(d) if 'TAMANO' in x])
    check('daltonismo y subtítulos activados', 'DALTONISMO   < SI' in ls and 'SUBTITULOS DE SONIDOS   < SI' in ls)
    g = guardia('Moya')
    l = g.get_actor_location()
    tp(l.x + 600, l.y, 180)
    # pasos («[PASOS - MOYA...]») o, si alguno habla en ese momento, su frase: las dos son subtítulos de sonido
    sub = lambda: str(director().get_editor_property('subtitle'))
    yield ('hasta', lambda: sub().startswith('[') or '"' in sub(), 8.0)
    check('subtítulo de los pasos de un guardia', 'MOYA' in sub() or sub().startswith('[') or '"' in sub(), sub())
    aparte()
    # dejarlo todo como estaba
    yield from teclas(d, 'P', *(['Down'] * 11), 'Left', 'Down', 'Enter', 'Down', 'Enter', 'P')
    check('opciones restauradas', d.get_editor_property('difficulty') == 1 and 'TAMANO DEL TEXTO   < 100 %' in ' '.join(lineas(d)))


# cada familia, en un PIE limpio; dentro de una familia las pruebas comparten partida (la llave, la jefatura, el farol...)
FAMILIAS = [[prueba_intro, prueba_datos, prueba_zona, prueba_empezar], [prueba_guardias], [prueba_menu, prueba_musica, prueba_controles, prueba_opciones],
            [prueba_frente], [prueba_captura, prueba_perdido], [prueba_dardos, prueba_punto_control, prueba_cambios, prueba_farol, prueba_final],
            [prueba_escondites], [prueba_cuerpo], [prueba_generador], [prueba_reserva], [prueba_perimetro], [prueba_anillo, prueba_camion]]
PRUEBAS = []


# ---------------------------------------------------------------- ejecutor por ticks

def _informe():
    res = R['resultados']
    ok = sum(1 for r in res if r[2])
    lineas = ['Pruebas de Tarsis - %s' % time.strftime('%Y-%m-%d %H:%M:%S'), '%d de %d pasan  (%.0f s)' % (ok, len(res), time.time() - R['t0']), '']
    for prueba, nombre, bien, detalle in res:
        lineas.append('%s  %-22s %s  %s' % ('PASA ' if bien else 'FALLA', prueba, nombre, detalle))
    carpeta = os.path.join(unreal.Paths.project_saved_dir(), 'Pruebas')
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, 'informe_%s.txt' % time.strftime('%Y%m%d_%H%M%S'))
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lineas))
    R['informe'] = ruta
    unreal.log('[Pruebas] %d de %d pasan. Informe: %s' % (ok, len(res), ruta))

def _limpieza(siguiente):
    # si una prueba deja el menú abierto (o esperando tecla), se cierra antes de la siguiente: una prueba que falla
    # no debe dejar el juego en pausa para todas las demás
    d = director()
    for _ in range(3):
        if not d or not d.get_editor_property('menu'):
            break
        d.press_key('Escape'); yield 0.1
        if d.get_editor_property('menu'):
            d.press_key('P'); yield 0.1
    if d and d.get_editor_property('menu'):
        check('limpieza: el menú no se cierra', False, ' / '.join(d.menu_lines()))
    # si la prueba anterior acabó con una captura, su escena (unos 2 s sin control y con la E ignorada) termina antes
    if d and d.get_editor_property('capturing'):
        yield ('hasta', lambda: not director().get_editor_property('capturing'), 5.0)
    # el camión (tanda 21) solo en su prueba: en las demás cruzaría la base a mitad de una medida de luz o de una captura
    if d:
        d.set_editor_property('truck', siguiente is prueba_camion)
    R['prueba'] = siguiente.__name__.replace('prueba_', '')
    yield from siguiente()

def _arranque():
    # PIE nuevo (salvo la primera familia, que prueba la intro): se salta la cinemática de entrada
    d = director()
    if d and d.get_editor_property('cine'):
        d.interact()
    yield 0.5

def _textos():
    d = director()
    falta = list(d.get_editor_property('missing_texts')) if d else []
    check('textos: nada se ha pedido que no esté en mision1.json', not falta, falta)
    yield 0.1

def _siguiente():
    if PRUEBAS:
        fn = PRUEBAS.pop(0)
        R['prueba'] = fn.__name__.replace('prueba_', '')
        R['gen'] = fn() if fn in (_arranque, _textos) else _limpieza(fn)
        R['espera'] = None
        return True
    if FAMILIAS:
        # familia nueva: se cierra el PIE y se abre otro limpio
        PRUEBAS.extend(FAMILIAS.pop(0) + [_textos])
        if R.get('familia', 0) > 0:
            PRUEBAS.insert(0, _arranque)
        R['familia'] = R.get('familia', 0) + 1
        if mundo():
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
            R['estado'] = 'reiniciando'
            return True
        return _siguiente()
    return False

def _tick(dt):
    try:
        w = mundo()
        if R['estado'] == 'reiniciando':
            if not w:   # el PIE anterior ya se ha cerrado: se lanza uno limpio (la intro tiene que verse desde el principio)
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
                R['estado'] = 'preparando'
            return
        if R['estado'] == 'preparando':
            if w and director() and jugador():
                R['estado'] = 'corriendo'
                if not _siguiente():
                    R['estado'] = 'terminado'
                    unreal.unregister_slate_post_tick_callback(R['h'])
                    _informe()
            return
        if R['estado'] != 'corriendo':
            return
        # tiempo real: con el menú abierto el juego está en pausa y el tiempo de juego no avanza
        t = unreal.GameplayStatics.get_real_time_seconds(w)
        e = R['espera']
        if e is not None:
            if e[0] == 't' and t < e[1]:
                return
            if e[0] == 'c' and not e[1]() and t < e[2]:
                return
        try:
            y = next(R['gen'])
            R['espera'] = ('t', t + y) if not isinstance(y, tuple) else ('c', y[1], t + y[2])
        except StopIteration:
            if not _siguiente() and R['estado'] == 'corriendo':
                R['estado'] = 'terminado'
                unreal.unregister_slate_post_tick_callback(R['h'])
                _informe()
    except Exception as ex:
        check('excepción', False, repr(ex))
        if not _siguiente():
            R['estado'] = 'terminado'
            unreal.unregister_slate_post_tick_callback(R['h'])
            _informe()

# solo algunas familias: builtins._tarsis_solo = ['captura', 'cuerpo'] (nombre de una prueba de la familia)
_solo = getattr(builtins, '_tarsis_solo', None)
if _solo:
    FAMILIAS[:] = [f for f in FAMILIAS if any(fn.__name__.replace('prueba_', '') in _solo for fn in f)]
_n = sum(len(f) for f in FAMILIAS)
PRUEBAS.extend(FAMILIAS.pop(0) + [_textos])
R['familia'] = 1
if PRUEBAS[0] is not prueba_intro:
    PRUEBAS.insert(0, _arranque)
sin_freno()
if mundo():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    R['estado'] = 'reiniciando'
else:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
R['h'] = unreal.register_slate_post_tick_callback(_tick)
unreal.log('[Pruebas] en marcha: %d pruebas en %d familias' % (_n, len(FAMILIAS) + 1))
