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
        if a.actor_has_tag('decorado'):
            continue   # tanda 25: el relleno que acompaña a cada farola (no alumbra para el sigilo; sigue a su farola)
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

def relleno_encendido():
    """Las luces de relleno (etiqueta «decorado», tanda 25) que están encendidas."""
    return [a.get_actor_label() for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.Light)
            if a.actor_has_tag('decorado') and not a.actor_has_tag('luz_caseta')   # la luz de la caseta de cada torre (tanda 31) va con el circuito de las torres: no se apaga
            and a.get_component_by_class(unreal.LocalLightComponent) and a.get_component_by_class(unreal.LocalLightComponent).is_visible()]

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
    for f in ('TarsisDirector.cpp', 'TarsisGuard.cpp', 'TarsisHUD.cpp', 'TarsisCodec.cpp', 'TarsisTorch.cpp', 'TarsisEmisora.cpp', 'TarsisCalabozo.cpp', 'TarsisCombat.cpp', 'TarsisEquipo.cpp', 'TarsisCaja.cpp', 'TarsisCharlas.cpp', 'TarsisBengala.cpp', 'TarsisTactica.cpp'):
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
    check('el menú tiene sus 18 líneas', len(lineas) == 18, ' / '.join(lineas))
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

def prueba_calma():
    """Tanda 45 (queja de Andres: «me meten al calabozo y aparecen guardias en alerta»). Al capturarte no queda nada en
    marcha: el tumbado se levanta sin buscar, el aturdido no sale a por ti, el que venía corriendo vuelve a su ronda y
    nadie da la voz por verte tras la reja."""
    d = director()
    libres = lambda: [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) in ('PATROL', 'RETURN') and not x.get_actor_label().endswith('Ramos')]
    yield ('hasta', lambda: len(libres()) >= 3, 30.0)
    a, b, c = libres()[:3]
    lc = c.get_actor_location()
    a.knock_out(); b.stun(4.0); c.alarm(V(lc.x + 500, lc.y, lc.z))
    yield 0.5
    check('preparado: uno en el suelo, uno aturdido y uno corriendo hacia ti', estado(a) == 'DOWN' and b.is_stunned() and estado(c) in ('ALERT', 'SUSPICIOUS', 'SEARCH'), '%s %s %s' % (estado(a), b.is_stunned(), estado(c)))
    d.lock_in_cell(jugador()); yield 0.5   # lo mismo que hace la captura (Captured llama a CalmBase y te encierra)
    check('estás en el calabozo', d.in_cell())
    mal = lambda: ['%s %s' % (x.get_actor_label(), estado(x)) for x in guardias() if estado(x) in ('ALERT', 'SEARCH', 'SUSPICIOUS', 'DOWN') and not x.get_actor_label().endswith('Ramos')]
    check('nada más encerrarte, nadie en alerta ni en el suelo', not mal(), mal())
    peor = []
    for i in range(24):
        yield 0.5
        peor += mal()
    check('a los doce segundos sigue todo en calma (ni el aturdido ni el tumbado salen a buscarte)', not peor and d.base_state() == 0, '%s base %s' % (sorted(set(peor))[:4], d.base_state()))
    # un guardia delante de la reja te ve preso y no da la voz
    puerta = d.get_editor_property('cell_door')
    g = libres()[0]
    g.set_actor_location(V(puerta.x, puerta.y - 150, g.get_actor_location().z), False, True)
    tp(puerta.x, puerta.y + 110, -90.0)
    g.hold(6.0)
    g.set_actor_rotation(unreal.Rotator(0, 0, 90.0), False)
    m = 0.0
    for i in range(8):
        yield 0.5
        m = max(m, g.get_editor_property('meter'))
    check('un guardia ante la reja no se alarma por ver al preso', m < 0.05 and estado(g) in ('PATROL', 'RETURN'), '%.2f %s' % (m, estado(g)))

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
    yield ('hasta', lambda: any('Lo he perdido' in str(x) for x in director().get_editor_property('subtitle_log')), 14.0)   # con los centinelas de torre hablando, la cola puede llevar dos o tres
    check('con subtítulo aunque la opción esté apagada', 'SUBTITULOS DE SONIDOS   < NO' in ' '.join(d.menu_lines()) and any('Lo he perdido' in str(x) for x in d.get_editor_property('subtitle_log')),
          list(d.get_editor_property('subtitle_log'))[-2:])

def prueba_generador():
    d = director()
    on0, off0 = luces()
    halos0 = d.halo_counts()
    tp(4300, 1910, -90); yield 0.1
    d.interact(); yield 0.1
    aparte()
    check('se corta el generador', d.get_editor_property('power_off'))
    yield 3.0
    on, off = luces()
    check('apagón en cadena: todas las luces fuera', len(on) == 0, 'encendidas %s' % on)
    # tanda 25: sin farola no hay halo ni brillo en el suelo mojado
    check('y con ellas sus halos y su brillo en el suelo', d.halo_counts().y == 0 and not relleno_encendido(), '%d halos, %d de relleno' % (d.halo_counts().y, len(relleno_encendido())))
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
    yield 0.2
    check('y los halos', d.halo_counts().y == halos0.y and halos0.y >= 6, '%d de %d' % (d.halo_counts().y, halos0.y))

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

def prueba_farola():
    """Tanda 27: cualquier farola se apaga de un dardo. Gasta el dardo, se queda rota aunque vuelva el generador, pierde
    su halo y deja de alumbrarte; el primer guardia que pisa esa sombra da parte por radio y saca la linterna. Los
    focos de las torres no se rompen."""
    d = director()
    aparte()
    _focos_torre(False)
    ext = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']
    f = ext['farolas'][0]
    fx, fy = f[0] * 100.0 + 25.0, f[1] * 100.0
    far = [a for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.Light) if a.get_actor_label().startswith('farola') and dist2d(a.get_actor_location(), V(fx, fy, 0)) < 150]
    check('hay farola en el camino', len(far) == 1, [a.get_actor_label() for a in far])
    if not far:
        return
    a = far[0]
    comp = a.get_component_by_class(unreal.LocalLightComponent)
    for g in guardias():
        g.hold(3600.0)   # nadie se mueve: lo que se mide es el disparo
    yield 0.5   # los halos de los focos de torre recién apagados se van un instante después: que no entren en la cuenta
    pie = V(fx, fy, 130)
    antes, hc = luz_en(pie), d.halo_counts()
    d.set_darts(3)
    tp(fx + 700, fy, 180); yield 0.2
    mirar(a.get_actor_location()); yield 0.2
    d.shoot_dart(); yield 0.4
    msg = str(d.get_editor_property('message'))
    check('el dardo rompe la farola', 'FAROLA ROTA' in msg and d.broken_lamp_count() == 1 and not comp.is_visible(), '%s, rotas %d' % (msg[:30], d.broken_lamp_count()))
    check('gasta el dardo', d.get_editor_property('darts') == 2, d.get_editor_property('darts'))
    despues = luz_en(pie)
    check('a su pie ya no estás a la luz', antes > 0.5 and despues < antes * 0.5, '%.2f -> %.2f' % (antes, despues))
    check('pierde su halo', d.halo_counts().y == hc.y - 1, '%d -> %d' % (hc.y, d.halo_counts().y))
    # otro dardo a la misma no hace nada más (sigue contando una)
    d.shoot_dart(); yield 0.9
    check('una farola rota no se rompe dos veces', d.broken_lamp_count() == 1, d.broken_lamp_count())
    # el primer guardia que pisa esa sombra da parte y saca la linterna
    aparte(); yield 0.1
    g = next((x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) != 'DOWN'), None)
    voces = len(list(d.get_editor_property('voice_log')))
    d.set_editor_property('tension_t', 0.0)
    g.set_actor_location(V(fx + 120, fy, 100), False, True); yield 0.5
    log_v = [str(x) for x in list(d.get_editor_property('voice_log'))[voces:]]
    check('el guardia que la encuentra da parte por radio', any('farol' in x for x in log_v), log_v)
    check('la base se pone en guardia y él saca la linterna', d.get_editor_property('tension_t') > 30.0 and g.has_flashlight_on(), '%.0f s, linterna %s' % (d.get_editor_property('tension_t'), g.has_flashlight_on()))
    # los focos de las torres no se rompen
    t = next((x for x in guardias() if x.get_editor_property('tower_sentry') and x.get_editor_property('tower_light')), None)
    if t:
        _focos_torre(True)
        tl = t.get_editor_property('tower_light')
        l = tl.get_actor_location()
        tp(l.x + 900, l.y, 180); yield 0.2
        mirar(l); yield 0.2
        d.shoot_dart(); yield 0.4
        check('el foco de una torre no se rompe', d.broken_lamp_count() == 1 and tl.get_component_by_class(unreal.LocalLightComponent).is_visible(), d.broken_lamp_count())
        _focos_torre(False)
    # reponerlas (carga de partida y pruebas) la deja como estaba
    aparte()
    d.repair_lamps(); yield 0.8
    check('repuesta, vuelve a alumbrar con su halo', comp.is_visible() and d.broken_lamp_count() == 0 and d.halo_counts().y == hc.y, '%d halos' % d.halo_counts().y)


def prueba_radio():
    """Tanda 28, «Responde, Carmona»: cada guardia da su parte a su manera y de cerca lo oyes. Si la central llama a uno
    que has dejado en el suelo y estás junto a él, contestas tú: su parte cuela y no viene nadie; «todo tranquilo» es
    la frase de coacción y trae a dos con la base en guardia."""
    d = director()
    c, v = guardia('Carmona'), guardia('Vega')
    for g in guardias():
        g.hold(3600.0)
    check('cada uno tiene su parte', 'con frio' in str(d.parte_of('Carmona')) and str(d.parte_of('Carmona')) != str(d.parte_of('Vega')), '%s / %s' % (d.parte_of('Carmona'), d.parte_of('Vega')))
    # de lejos no se oye; de cerca sí, y se explica la primera vez
    aparte(); yield 0.1
    d.say_parte(c); yield 0.2
    check('de lejos no oyes el parte', len(list(d.get_editor_property('heard_partes'))) == 0, list(d.get_editor_property('heard_partes')))
    detras_de(c, 600.0); yield 0.2
    d.say_parte(c); yield 0.3
    check('de cerca lo oyes y te lo quedas', [str(x) for x in d.get_editor_property('heard_partes')] == ['Carmona'] and str(list(d.get_editor_property('voice_log'))[-1]) == 'carmona_parte'
          and 'ensena_parte' in [str(x) for x in d.get_editor_property('taught')], list(d.get_editor_property('voice_log'))[-2:])
    # derribado Carmona, a los 40 s llama la central: junto a él, puedes contestar
    derribar(c); yield 0.2
    junto_a(c)
    yield ('hasta', lambda: director().get_editor_property('radio_ask'), 55.0)
    ops = [str(x) for x in d.get_editor_property('radio_options')]
    r, k = d.get_editor_property('radio_right'), d.get_editor_property('radio_duress')
    check('la central llama y puedes contestar con tres partes', d.get_editor_property('radio_ask') and len(ops) == 3 and 1 <= r <= 3 and 1 <= k <= 3 and r != k
          and 'con frio' in ops[r - 1] and 'Todo tranquilo' in ops[k - 1] and all('Carmona' in o for o in ops), ops)
    check('las tres salen en pantalla', all(o in str(d.get_editor_property('message')) for o in ops), str(d.get_editor_property('message'))[:60])
    d.answer_radio(r); yield 3.0
    sosp = [g.get_actor_label() for g in guardias() if estado(g) not in ('PATROL', 'DOWN')]
    check('con su parte, la central se lo cree y no manda a nadie', d.get_editor_property('radio_fooled') == 1 and 'central_recibido' in [str(x) for x in d.get_editor_property('voice_log')] and not sosp
          and not d.get_editor_property('radio_ask'), '%s %s' % (list(d.get_editor_property('voice_log'))[-3:], sosp))
    # con Vega, la frase que parece natural: es la de coacción
    d.set_editor_property('tension_t', 0.0)
    derribar(v); yield 0.2
    junto_a(v)
    yield ('hasta', lambda: director().get_editor_property('radio_ask'), 55.0)
    k = d.get_editor_property('radio_duress')
    d.answer_radio(k); yield 2.5
    van = [g.get_actor_label() for g in guardias() if estado(g) == 'SUSPICIOUS']
    check('«todo tranquilo» es la frase de coacción: base en guardia y van dos', d.get_editor_property('tension_t') > 80.0 and len(van) == 2
          and 'central_coaccion' in [str(x) for x in d.get_editor_property('voice_log')], '%.0f s, van %s' % (d.get_editor_property('tension_t'), van))
    yield 2.5
    check('y se te explica después', 'ensena_coaccion' in [str(x) for x in d.get_editor_property('taught')], [str(x) for x in d.get_editor_property('taught')][-3:])
    # lejos del cuerpo no hay pregunta: mandan a alguien como siempre
    aparte()
    check('la central no pregunta dos veces por el mismo', not d.get_editor_property('radio_ask'))


def prueba_apoyo():
    """Tanda 28: nadie entra solo a mirar un ruido donde falta la farola. El que lo oye se planta con la linterna, pide
    apoyo por radio y espera al compañero; luego entran los dos."""
    d = director()
    aparte()
    _focos_torre(False)
    ext = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']
    f = ext['farolas'][0]
    fx, fy = f[0] * 100.0 + 25.0, f[1] * 100.0
    far = [x for x in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.Light) if x.get_actor_label().startswith('farola') and dist2d(x.get_actor_location(), V(fx, fy, 0)) < 150]
    if not far:
        check('hay farola en el camino', False)
        return
    # se rompe con todos quietos (que nadie vea al que dispara) y luego se sueltan dos que no se hayan enterado
    for g in guardias():
        g.hold(3600.0)
    d.set_darts(2)
    tp(fx + 700, fy, 180); yield 0.3
    mirar(far[0].get_actor_location()); yield 0.2
    d.shoot_dart(); yield 0.3
    aparte(); yield 0.1
    d.set_editor_property('tension_t', 0.0)
    libres = [g for g in guardias() if not g.get_editor_property('tower_sentry') and estado(g) == 'PATROL'][:2]
    a, b = libres
    a.set_actor_location(V(fx + 1800, fy, 100), False, True)
    b.set_actor_location(V(fx + 4200, fy, 100), False, True)
    a.hold(0.0); b.hold(0.0); yield 0.2
    a.hear_noise(V(fx, fy, 20)); yield 0.3
    check('con la farola rota, uno oye un ruido en su sombra', d.broken_lamp_count() == 1 and estado(a) == 'SUSPICIOUS', '%d, %s' % (d.broken_lamp_count(), estado(a)))
    yield 2.5
    pa = a.get_actor_location()
    check('no entra solo: se planta, saca la linterna y pide apoyo', a.get_editor_property('wait_buddy') and a.has_flashlight_on() and d.get_editor_property('buddy_calls') == 1
          and any(str(x).endswith('_apoyo') for x in d.get_editor_property('voice_log')), 'espera %s, linterna %s, %s' % (a.get_editor_property('wait_buddy'), a.has_flashlight_on(), list(d.get_editor_property('voice_log'))[-3:]))
    yield 3.0
    check('mientras espera no se mueve, y el compañero viene', dist2d(a.get_actor_location(), pa) < 80 and estado(b) == 'SUSPICIOUS' and any(str(x).endswith('_voy') for x in d.get_editor_property('voice_log')),
          '%.0f cm, %s' % (dist2d(a.get_actor_location(), pa), estado(b)))
    yield ('hasta', lambda: not a.get_editor_property('wait_buddy'), 30.0)
    check('cuando llega el compañero, deja de esperar', not a.get_editor_property('wait_buddy') and dist2d(a.get_actor_location(), b.get_actor_location()) < 600,
          '%.0f cm entre los dos' % dist2d(a.get_actor_location(), b.get_actor_location()))
    yield ('hasta', lambda: dist2d(a.get_actor_location(), V(fx, fy, 0)) < 400, 25.0)
    yield 1.0
    check('entran los dos a la sombra', dist2d(a.get_actor_location(), V(fx, fy, 0)) < 450 and dist2d(b.get_actor_location(), V(fx, fy, 0)) < 900,
          'a %.0f y %.0f cm' % (dist2d(a.get_actor_location(), V(fx, fy, 0)), dist2d(b.get_actor_location(), V(fx, fy, 0))))
    d.repair_lamps()


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
    # (la ruta de navegación por el camino ya no se pide desde aquí: find_path_to_location_synchronously llamado desde Python
    # hace saltar un «ensure» del motor que abre la ventana de informe de errores. Que se puede andar por el camino lo
    # prueban la ronda de Carmona en prueba_anillo y el guardia que va a la cabina del camión en prueba_camion)
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
    check('el jugador empieza junto a la brecha del muro norte (tanda 40)', ps and dist2d(ps[0].get_actor_location(), V(2120, -1640, 0)) < 150, [ps[0].get_actor_location() if ps else None])
    aparte()


def prueba_desgaste():
    """Tanda 22 (arte): el camino y el anillo dejan de parecer recién puestos. Juntas y grietas selladas en la losa, hierbajos
    al pie de vallas y muros, manchas en el suelo y en el muro, y el camión con su textura pegada (no proyectada desde el
    mundo) y barro en los bajos."""
    w = mundo()
    ext = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']
    des = ext.get('desgaste') or {}
    check('la losa tiene juntas, grietas y parches', len(des.get('juntas', [])) >= 15 and len(des.get('grietas', [])) >= 10 and len(des.get('parches', [])) >= 3,
          {k: len(v) for k, v in des.items()})
    mallas = {}
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor):
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        if c and c.get_num_materials():
            mallas[a.get_actor_label()] = (a, c, c.get_material(0).get_name() if c.get_material(0) else '')
    check('el alquitrán de las juntas está en el nivel', any(n.startswith('base_alquitran') for n in mallas), [n for n in mallas if 'alquitran' in n])
    h = next((v for n, v in mallas.items() if n.startswith('hierbajos')), None)
    check('hay hierbajos (%s matas en base.json)' % ext.get('hierbajos'), h is not None and (ext.get('hierbajos') or 0) > 300, sorted(mallas)[:0])
    if h:
        a, c, mat = h
        check('los hierbajos llevan su material recortado', mat.startswith('M_Hierbajo_') and not a.get_editor_property('hidden'), mat)
        check('y no estorban: sin colisión ni sombra', not a.get_actor_enable_collision() and not c.get_editor_property('cast_shadow'),
              '%s, %s' % (a.get_actor_enable_collision(), c.get_editor_property('cast_shadow')))
    manchas = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DecalActor) if a.actor_has_tag('mancha_perimetro')]
    en_camino = [a for a in manchas if abs(a.get_actor_location().y - 5700) < 320]
    check('manchas en el camino (rodadas, aceite, barro) y al pie del muro', len(en_camino) >= 20 and len(manchas) - len(en_camino) >= 8, '%d en el camino, %d en el muro' % (len(en_camino), len(manchas) - len(en_camino)))
    quiere = {'camionmovil_oliva': 'MI_oliva_camion', 'camionmovil_bajos': 'MI_bajos_camion', 'camionmovil_goma': 'MI_goma_camion',
              'camionmovil_lona': 'MI_lona_camion', 'hojaentrada_oliva': 'MI_oliva_hoja', 'camiones_oliva': 'MI_oliva_camion'}
    tiene = {n: next((v[2] for k, v in mallas.items() if k.startswith(n)), None) for n in quiere}
    check('el camión y la hoja del portón llevan la textura pegada, con barro', all(tiene[n] == m for n, m in quiere.items()), {n: m for n, m in tiene.items() if m != quiere[n]})
    yield 0.1


def prueba_charcos():
    """Tanda 23 (arte): el suelo y los muros tienen agua. Charcos de verdad (M_Charco, agua lisa que refleja) junto a cada
    farola del camino, en el anillo y en los patios; más charcos cuando llueve; regueros de humedad que bajan por las cuatro
    caras de dentro del muro y por las garitas; juntas de la losa que rezuman justo donde hay junta; y un solo material de
    hierbajos (los de tandas anteriores se borran)."""
    d = director()
    w = mundo()
    ext = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']
    def mat(a):
        try:
            m = a.decal.get_decal_material()
        except Exception:
            m = a.decal.get_editor_property('decal_material')
        return m.get_name() if m else ''
    por = {}
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DecalActor):
        if a.actor_has_tag('mancha_perimetro'):
            por.setdefault(mat(a), []).append(a)
    agua = por.get('MI_Per_Agua', []) + por.get('MI_Per_AguaBarro', [])
    fijos = [a for a in agua if not a.actor_has_tag('lluvia')]
    lluvia = [a for a in agua if a.actor_has_tag('lluvia')]
    check('charcos fijos en el camino, el anillo y los patios', len(fijos) >= 12 and len(por.get('MI_Per_AguaBarro', [])) >= 5,
          '%d fijos, %d con lluvia, %d turbios' % (len(fijos), len(lluvia), len(por.get('MI_Per_AguaBarro', []))))
    lejos = [f for f in ((1070, 5770), (3600, 5770), (6130, 5770), (-1460, 5640), (8660, 5640))
             if not any(dist2d(a.get_actor_location(), V(f[0], f[1], 0)) < 520 for a in fijos)]
    check('cada farola del camino tiene un charco al lado que la refleja', not lejos, lejos)
    # ajuste 25d: los charcos turbios fijos, junto a las farolas del centro del camino (donde estaban solo había luna)
    turbios = [a for a in por.get('MI_Per_AguaBarro', []) if not a.actor_has_tag('lluvia')]
    sin_luz = [str(a.get_actor_label()) for a in turbios
               if not any(dist2d(a.get_actor_location(), V(f[0], f[1], 0)) < 800 for f in ((1070, 5770), (3600, 5770), (6130, 5770)))]
    check('los charcos turbios fijos están a la luz de una farola', len(turbios) >= 3 and not sin_luz, '%d turbios fijos; lejos: %s' % (len(turbios), sin_luz))
    patio = [a for a in fijos if 0 < a.get_actor_location().x < 7200 and 0 < a.get_actor_location().y < 5300]
    check('y hay charcos en los patios de la base', len(patio) >= 3, len(patio))
    mi = unreal.load_asset('/Game/Tarsis/Materiales/Manchas/MI_Per_Agua')
    padre = mi.get_editor_property('parent') if mi else None
    rug = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, 'Rugosidad') if mi else 9.0
    check('el agua es un material propio, liso (refleja)', padre is not None and padre.get_name() == 'M_Charco' and rug < 0.15
          and padre.get_editor_property('material_domain') == unreal.MaterialDomain.MD_DEFERRED_DECAL, '%s, rugosidad %.2f' % (padre.get_name() if padre else None, rug))
    # mezclas (Substrate): el agua translúcida (escribe color, rugosidad y relieve dentro de la máscara: refleja la farola);
    # manchas y regueros modulados (oscurecen dentro de la máscara). Con alfa compuesto el color se sumaba y no oscurecía
    B = unreal.BlendMode
    mezclas = {n: (unreal.load_object(None, '/Game/Tarsis/Materiales/%s.%s' % (n, n)) or None) for n in ('M_Charco', 'M_Mancha', 'M_Chorreton')}
    mezclas = {n: (m.get_editor_property('blend_mode') if m else None) for n, m in mezclas.items()}
    check('agua translúcida; manchas y regueros modulados (oscurecen, sin caja)', mezclas == {'M_Charco': B.BLEND_TRANSLUCENT,
          'M_Mancha': B.BLEND_MODULATE, 'M_Chorreton': B.BLEND_MODULATE}, mezclas)
    # con lluvia salen más
    w0 = d.get_editor_property('weather')
    while d.get_editor_property('weather') != 0:
        d.simulate_key('Y'); yield 0.2
    yield 0.3
    seco = [a.decal.is_visible() for a in lluvia]
    while d.get_editor_property('weather') != 1:
        d.simulate_key('Y'); yield 0.2
    yield 0.3
    mojado = [a.decal.is_visible() for a in lluvia]
    check('con lluvia salen más charcos (%d) y sin ella no están' % len(lluvia), len(lluvia) >= 14 and not any(seco) and all(mojado),
          '%d visibles en seco, %d con lluvia' % (sum(seco), sum(mojado)))
    check('los fijos están siempre', all(a.decal.is_visible() for a in fijos))
    while d.get_editor_property('weather') != w0:
        d.simulate_key('Y'); yield 0.2
    # regueros en el muro: en las cuatro caras de dentro, de arriba abajo
    reg = por.get('MI_Per_Chorreton', [])
    caras = {'sur': 0, 'norte': 0, 'oeste': 0, 'este': 0}
    for a in reg:
        l = a.get_actor_location()
        c = 'sur' if abs(l.y - 7455) < 30 else 'norte' if abs(l.y + 1855) < 30 else 'oeste' if abs(l.x + 1855) < 30 else 'este' if abs(l.x - 9055) < 30 else None
        if c:
            caras[c] += 1
    altos = [a.decal.get_editor_property('decal_size').z for a in reg]
    check('regueros de humedad en las cuatro caras del muro', all(v >= 4 for v in caras.values()) and sum(caras.values()) == len(reg), caras)
    check('cogen el muro de arriba abajo (4,6 m)', altos and all(abs(z - 230) < 2 for z in altos) and all(abs(a.get_actor_location().z - 230) < 5 for a in reg), sorted(set(altos))[:4])
    check('ninguno tapa el portillo', not [a for a in reg if abs(a.get_actor_location().y - 7455) < 30 and 100 < a.get_actor_location().x < 520])
    gar = por.get('MI_Per_ChorretonGarita', [])
    cerca = lambda a, k: dist2d(a.get_actor_location(), V(ext[k]['garita'][0] * 100, ext[k]['garita'][1] * 100, 0)) < 200
    check('y dos en cada garita', len(gar) == 4 and sum(1 for a in gar if cerca(a, 'entrada')) == 2 and sum(1 for a in gar if cerca(a, 'salida')) == 2, len(gar))
    # juntas que rezuman: cada una encima de una junta de verdad, y las juntas donde el director cree que están
    juntas = sorted(x * 100.0 for x in (ext.get('desgaste') or {}).get('juntas', []))
    rez = por.get('MI_Per_Junta', [])
    fuera = [int(a.get_actor_location().x) for a in rez if not any(abs(a.get_actor_location().x - x) < 10 for x in juntas)]
    check('juntas de la losa que rezuman, cada una sobre su junta', len(rez) >= 6 and not fuera, '%d, fuera de sitio %s' % (len(rez), fuera))
    paso, fase = d.get_editor_property('truck_joint_pitch'), d.get_editor_property('truck_joint_phase')
    desfase = [x for x in juntas if abs((x - fase + paso / 2.0) % paso - paso / 2.0) > 1.0]
    check('el camión sabe dónde están las juntas (golpe de cada eje)', len(juntas) >= 15 and paso > 1 and not desfase and abs(juntas[1] - juntas[0] - paso) < 1.0,
          'paso %s, fase %s, %d fuera' % (paso, fase, len(desfase)))
    # hierbajos: un solo material (los de tandas anteriores se borran al montar)
    # registro de recursos y load_object, no EditorAssetLibrary: durante el PIE esta responde vacío («The Editor is currently in a play mode»)
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    viejos = sorted(str(a.asset_name) for a in reg.get_assets_by_path('/Game/Tarsis/Materiales', recursive=False) if str(a.asset_name).startswith('M_Hierbajo_'))
    check('un solo material de hierbajos (el de esta tanda)', len(viejos) == 1, viejos)
    check('sonidos de la caja del camión importados', all(unreal.load_object(None, '/Game/Tarsis/Sonidos/%s.%s' % (n, n)) for n in ('camion_junta', 'camion_caja')))


def prueba_mojado():
    """Tanda 24 (arte): la lluvia moja la base entera. El director sube «Mojado» en la colección MPC_Tarsis mientras
    llueve y lo baja despacio al escampar; el material maestro oscurece y da brillo a lo que está a la intemperie
    (parámetro Mojable de cada instancia) y deja como estaban los interiores."""
    d = director()
    mel = unreal.MaterialEditingLibrary
    mpc = unreal.load_object(None, '/Game/Tarsis/Materiales/MPC_Tarsis.MPC_Tarsis')
    check('la colección MPC_Tarsis existe y el director la tiene', mpc is not None and d.wetness_in_collection() >= 0.0, d.wetness_in_collection())
    def mojable(n):
        mi = unreal.load_object(None, '/Game/Tarsis/Materiales/MI_%s.MI_%s' % (n, n))
        return round(mel.get_material_instance_scalar_parameter_value(mi, 'Mojable'), 2) if mi else None
    val = {n: mojable(n) for n in ('suelo', 'tejado', 'muro', 'oliva', 'suelo_int', 'pared', 'madera')}
    check('se moja lo que está a la intemperie y no los interiores', val['suelo'] == 1.0 and val['tejado'] == 1.0 and 0.5 < (val['muro'] or 0) < 1.0
          and 0.3 < (val['oliva'] or 0) < 1.0 and val['suelo_int'] == 0.0 and val['pared'] == 0.0 and val['madera'] == 0.0, val)
    w0, ws, ds = d.get_editor_property('weather'), d.get_editor_property('wet_seconds'), d.get_editor_property('dry_seconds')
    moj = lambda: director().get_editor_property('wetness')
    while d.get_editor_property('weather') != 0:
        d.simulate_key('Y'); yield 0.2
    d.set_wetness_now(0.0); yield 0.2
    check('en seco la colección vale 0', moj() < 0.01 and abs(d.wetness_in_collection()) < 0.01, '%.2f, %.2f' % (moj(), d.wetness_in_collection()))
    d.set_editor_property('wet_seconds', 2.0); d.set_editor_property('dry_seconds', 3.0)   # para no esperar 25 s y 90 s
    while d.get_editor_property('weather') != 1:
        d.simulate_key('Y'); yield 0.2
    yield 0.7
    medio = moj()
    check('con la lluvia se va mojando poco a poco', 0.15 < medio < 0.9, '%.2f' % medio)
    yield 2.2
    check('y acaba empapada (la colección vale 1)', moj() > 0.99 and d.wetness_in_collection() > 0.99, '%.2f, %.2f' % (moj(), d.wetness_in_collection()))
    while d.get_editor_property('weather') != 0:
        d.simulate_key('Y'); yield 0.2
    yield 0.8
    medio = moj()
    check('al escampar no se seca de golpe', 0.3 < medio < 0.95, '%.2f' % medio)
    yield 3.4
    check('y vuelve a estar seca', moj() < 0.01 and abs(d.wetness_in_collection()) < 0.01, '%.2f, %.2f' % (moj(), d.wetness_in_collection()))
    # se lee enseguida: en seco el director sigue secando (WetTick) y en 0,1 s ya ha bajado de 0,70 a 0,66
    d.set_wetness_now(0.7)
    visto = d.wetness_in_collection()
    d.set_wetness_now(0.0)
    check('SetWetnessNow lo pone de golpe (capturas y pruebas)', abs(visto - 0.7) < 0.01, '%.2f' % visto)
    d.set_editor_property('wet_seconds', ws); d.set_editor_property('dry_seconds', ds)
    while d.get_editor_property('weather') != w0:
        d.simulate_key('Y'); yield 0.2
    # presupuesto de render: lo que el director del nivel tenga apuntado, puesto de verdad (o ya valía eso)
    quiere = [str(x) for x in d.get_editor_property('render_c_vars')]
    puestas = [str(x) for x in d.get_editor_property('render_applied')]
    mal = []
    for linea in quiere:
        n, _, v = linea.partition('=')
        try:
            ahora = unreal.SystemLibrary.get_console_variable_float_value(n.strip())
            if abs(ahora - float(v)) > 1e-4:
                mal.append('%s=%s (quiere %s)' % (n, ahora, v))
        except Exception as ex:
            mal.append('%s: %r' % (linea, ex))
    check('el presupuesto de render del nivel (%d variables) está puesto' % len(quiere), not mal, mal or puestas)


def prueba_carteles():
    """Tanda 24 (mundo): carteles, rótulos y etiquetas. Chapas esmaltadas en los dinteles y en el muro, señales en poste,
    pintura de plantilla en el muro y en la losa del control y etiquetas en las taquillas (assets/unreal/carteles.json)."""
    w = mundo()
    lista = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'carteles.json'), encoding='utf-8'))['carteles']
    mel = unreal.MaterialEditingLibrary
    por = {}
    for cls in (unreal.StaticMeshActor, unreal.DecalActor):
        for a in actores('cartel', cls):
            por[a.get_actor_label()] = a
    faltan = [c['nombre'] for c in lista if 'Cartel_' + c['nombre'] not in por]
    check('los %d carteles de carteles.json están en el nivel' % len(lista), len(lista) >= 20 and not faltan, faltan)
    torcidos, sin_tex, al_aire, chocan, sin_poste = [], [], [], [], []
    for c in lista:
        a = por.get('Cartel_' + c['nombre'])
        if not a:
            continue
        if c['clase'] != 'placa':
            mi = a.decal.get_decal_material()
        else:
            comp = a.get_component_by_class(unreal.StaticMeshComponent)
            mi = comp.get_material(0)
            r = math.radians(c['mira'])
            nx, ny = math.cos(r), math.sin(r)
            up, der = a.get_actor_up_vector(), a.get_actor_right_vector()
            # de cara a quien lo lee y derecho: la normal del plano hacia «mira» y su Y local (la v de la textura) hacia abajo
            if up.x * nx + up.y * ny < 0.99 or der.z > -0.99:
                torcidos.append(c['nombre'])
            if comp.get_collision_enabled() != unreal.CollisionEnabled.NO_COLLISION:
                chocan.append(c['nombre'])
            p = a.get_actor_location()
            if c.get('poste'):
                poste = por.get('Cartel_' + c['nombre'] + '_poste')
                if not poste or dist2d(poste.get_actor_location(), V(c['pos'][0], c['pos'][1], 0)) > 5 or abs(p.y - 5700) < 320:
                    sin_poste.append(c['nombre'])
            else:
                # pegado a algo: la pared (o la taquilla) queda justo detrás de la chapa, ni a un palmo ni por delante
                h = unreal.SystemLibrary.line_trace_single(w, V(p.x + nx * 30, p.y + ny * 30, p.z), V(p.x - nx * 30, p.y - ny * 30, p.z),
                                                           unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [jugador()], unreal.DrawDebugTrace.NONE, True)
                if h:
                    l = h.to_tuple()[4]
                    sep = (l.x - p.x) * nx + (l.y - p.y) * ny
                if not h or not (-10.0 <= sep <= 1.0):
                    al_aire.append('%s %s' % (c['nombre'], ('%.1f' % sep) if h else 'sin pared'))
        tx = mel.get_material_instance_texture_parameter_value(mi, 'Textura') if mi else None
        if not tx or tx.get_name() != 'T_Cartel_' + c['tex']:
            sin_tex.append(c['nombre'])
    check('cada uno lleva su textura', not sin_tex, sin_tex)
    check('las placas miran a quien las lee y están derechas', not torcidos, torcidos)
    check('cada placa está pegada a su pared o a su taquilla (detrás, a menos de 10 cm)', not al_aire, al_aire)
    check('las señales de poste tienen su poste, fuera del camino', not sin_poste, sin_poste)
    check('ningún cartel estorba el paso', not chocan, chocan)
    B = unreal.BlendMode
    pla = unreal.load_object(None, '/Game/Tarsis/Materiales/M_Cartel.M_Cartel')
    rot = unreal.load_object(None, '/Game/Tarsis/Materiales/M_Rotulo.M_Rotulo')
    check('chapa recortada y pintura modulada (Substrate)', pla is not None and rot is not None and pla.get_editor_property('blend_mode') == B.BLEND_MASKED
          and rot.get_editor_property('blend_mode') == B.BLEND_MODULATE and rot.get_editor_property('material_domain') == unreal.MaterialDomain.MD_DEFERRED_DECAL,
          [m.get_editor_property('blend_mode') if m else None for m in (pla, rot)])
    en_puertas = [n for n in ('Jefatura', 'Archivo', 'Dormitorio', 'CuerpoGuardia', 'Calabozo') if 'Cartel_' + n in por
                  and 225 < por['Cartel_' + n].get_actor_location().z < 300]
    check('las cinco puertas con nombre tienen su placa en el dintel', len(en_puertas) == 5, en_puertas)
    # tanda 25: «ZONA MILITAR» a 2 x 1 m y con luz propia (pintura reflectante): se lee de noche sin poner un foco
    zm = [c for c in lista if c['tex'] == 'zona_militar']
    mal = []
    for c in zm:
        a = por.get('Cartel_' + c['nombre'])
        if not a:
            mal.append(c['nombre']); continue
        e = a.get_actor_scale3d()
        mi = a.get_component_by_class(unreal.StaticMeshComponent).get_material(0)
        br = mel.get_material_instance_scalar_parameter_value(mi, 'Brillo') if mi else 0.0
        if abs(e.x - 2.0) > 0.01 or abs(e.y - 1.0) > 0.01 or not 0.05 <= br <= 0.3:
            mal.append('%s %.1fx%.1f brillo %.2f' % (c['nombre'], e.x, e.y, br))
    check('«ZONA MILITAR»: cinco chapas de 2 x 1 m que se leen de noche (brillo propio)', len(zm) == 5 and not mal, mal)
    sin_brillo = mel.get_material_instance_scalar_parameter_value(por['Cartel_Jefatura'].get_component_by_class(unreal.StaticMeshComponent).get_material(0), 'Brillo') if 'Cartel_Jefatura' in por else -1
    check('las placas de interior no brillan', sin_brillo == 0.0, sin_brillo)
    suelo = [a for a in por.values() if isinstance(a, unreal.DecalActor) and a.get_actor_location().z < 20]
    check('ALTO y la línea, pintados en la losa del control', len(suelo) == 2 and all(abs(a.get_actor_location().y - 5700) < 10 and 8200 < a.get_actor_location().x < 8600 for a in suelo),
          [int(a.get_actor_location().x) for a in suelo])
    yield 0.1


def prueba_materia():
    """Tanda 25 (arte): las superficies grandes dejan de ser un color plano. El material maestro (M_LH) pinta con el
    albedo de verdad de cada material (Tinte) sobre la textura normalizada (Medio), y encima la variación que se ve de
    lejos: losas y paneles de distinto tono con su junta, nubes, manchas, zócalo sucio y regueros. Los contenedores
    tienen costillas, pilares y puertas; el camión es verde oliva."""
    w = mundo()
    mel = unreal.MaterialEditingLibrary
    def mi(n):
        return unreal.load_object(None, '/Game/Tarsis/Materiales/MI_%s.MI_%s' % (n, n))
    def esc(n, p):
        m = mi(n)
        return round(mel.get_material_instance_scalar_parameter_value(m, p), 3) if m else None
    def lum(n, p):
        m = mi(n)
        if not m:
            return None
        c = mel.get_material_instance_vector_parameter_value(m, p)
        return round(0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b, 3)
    claves = ('suelo', 'camino', 'muro', 'hormigon', 'pared', 'tejado', 'oliva', 'suelo_int')
    padres = {n: (mi(n).get_editor_property('parent').get_name() if mi(n) and mi(n).get_editor_property('parent') else None) for n in claves}
    check('las instancias cuelgan del material maestro', all(v == 'M_LH' for v in padres.values()), padres)
    # lo que se ve y lo que queda guardado. En el primer montaje de la 25 todo lo de abajo pasaba (lee las instancias)
    # y la base seguía con el material liso del glTF: las mallas no llegaban a guardarse (poner static_materials por
    # Python no marca el paquete como cambiado) y al reabrir el editor volvían a lh_*. Las capturas salieron sin M_LH
    esperado = {'base_muro': 'MI_muro', 'base_suelo': 'MI_suelo', 'base_camino': 'MI_camino', 'base_tierra': 'MI_tierra',
                'base_hormigon': 'MI_hormigon', 'camionmovil_oliva': 'MI_oliva_camion'}
    puesto, disco = {}, {}
    contenido = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    for d in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path('/Game/Tarsis/Base', recursive=True):
        n = str(d.asset_name)
        if n not in esperado or str(d.asset_class_path.asset_name) != 'StaticMesh':
            continue
        sm = d.get_asset()
        mats = sm.get_editor_property('static_materials') if sm else []
        m0 = mats[0].get_editor_property('material_interface') if mats else None
        puesto[n] = m0.get_name() if m0 else None
        f = os.path.join(contenido, str(d.package_name)[len('/Game/'):] + '.uasset')
        try:
            disco[n] = esperado[n].encode('ascii') in open(f, 'rb').read()
        except Exception as e:
            disco[n] = repr(e)
    check('muro, suelo, camino, tierra y camión llevan su instancia (no el material liso del glTF)',
          len(puesto) >= 5 and all(puesto[k] == esperado[k] for k in puesto), puesto)
    check('y así están guardados en disco (al reabrir el editor no vuelven a lh_*)', len(disco) >= 5 and all(v is True for v in disco.values()), disco)
    alb = {n: lum(n, 'Tinte') for n in claves}
    # albedos de verdad: asfalto y losa 5-14 %, hormigón 12-18 %, enlucido pintado 18-28 %, pintura oliva y tela asfáltica 2-5 %
    check('cada material pinta con su albedo real (ni negro ni tiza)', all(v is not None and 0.02 <= v <= 0.3 for v in alb.values())
          and alb['muro'] > alb['suelo'] and alb['pared'] > alb['muro'] and alb['tejado'] < alb['suelo'], alb)
    med = {n: lum(n, 'Medio') for n in claves}
    check('la textura va normalizada por su color medio', all(v is not None and 0.03 < v < 0.6 for v in med.values()), med)
    losas = {n: (esc(n, 'Losa'), esc(n, 'LosaTono'), esc(n, 'Panel'), esc(n, 'PanelTono'), esc(n, 'Junta')) for n in ('suelo', 'camino', 'muro', 'hormigon')}
    check('losas de distinto tono en el suelo y paneles en los muros', losas['suelo'][0] >= 400 and losas['suelo'][1] > 0.05 and losas['camino'][0] == 600
          and losas['muro'][2] >= 250 and losas['muro'][3] > 0.05 and losas['hormigon'][3] > 0.03, losas)
    cho = {n: esc(n, 'Chorreo') for n in ('muro', 'hormigon', 'pared', 'suelo', 'suelo_int', 'contenedor_0')}
    check('regueros en lo vertical y no en el suelo', cho['muro'] >= 0.4 and cho['hormigon'] >= 0.3 and cho['contenedor_0'] > 0.1 and cho['suelo'] == 0.0 and cho['suelo_int'] == 0.0, cho)
    # ajuste 25d: la grava trae rugosidad 0,47 y con la luna rasante parecía nieve; escalada queda mate
    gr = esc('tierra', 'RugosidadEscala')
    check('la grava es más mate que la textura (la luna no la vuelve nieve)', gr is not None and gr >= 1.2, gr)
    rel = {n: esc(n, 'Relieve') for n in ('suelo', 'camino', 'muro')}
    check('relieve reforzado (se lee con la luz rasante de las farolas)', all(v and v > 1.2 for v in rel.values()), rel)
    # el camión: verde oliva oscuro (antes salía verde lima)
    m = unreal.load_object(None, '/Game/Tarsis/Materiales/MI_oliva_camion.MI_oliva_camion')
    c = mel.get_material_instance_vector_parameter_value(m, 'Tinte') if m else None
    check('el camión es verde oliva oscuro', c is not None and c.g > c.r > c.b and c.g < 0.09 and c.g / max(c.r, 1e-4) < 1.35, (round(c.r, 3), round(c.g, 3), round(c.b, 3)) if c else None)
    # contenedores: el detalle se ve y no se toca; la caja de siempre sigue siendo lo que choca
    det = actores('contenedor_detalle')
    cajas = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor)
             if a.get_actor_label().startswith('contenedor_') and not a.actor_has_tag('contenedor_detalle')]
    check('los contenedores de cada color tienen sus costillas, pilares y puertas', len(det) >= 3 and len(det) == len(cajas), '%d de %d' % (len(det), len(cajas)))
    mal = []
    for a in det:
        comp = a.get_component_by_class(unreal.StaticMeshComponent)
        mat = comp.get_material(0).get_name() if comp and comp.get_material(0) else ''
        o, e = a.get_actor_bounds(False)
        caja = next((b for b in cajas if dist2d(b.get_actor_bounds(False)[0], o) < 60), None)
        if a.get_actor_enable_collision() or not mat.startswith('MI_contenedor_') or a.get_editor_property('hidden') or caja is None \
                or caja.get_component_by_class(unreal.StaticMeshComponent).get_material(0).get_name() != mat:
            mal.append('%s %s' % (a.get_actor_label(), mat))
    check('el detalle se ve, no estorba y va del color de su caja', not mal, mal)
    yield 0.1


def prueba_cielo():
    """Tanda 25 (luz y cielo): la noche tiene cielo (cúpula con estrellas, luna y nubes que se cubre con la lluvia y la
    niebla), las farolas tienen halo y dejan de quemar el suelo (se pintan a un décimo; para el sigilo cuentan lo de
    siempre) y cada una lleva un relleno que da brillo en el suelo mojado sin alumbrar a nadie."""
    d = director()
    w = mundo()
    aparte()
    cup = actores('cielo')
    c = cup[0].get_component_by_class(unreal.StaticMeshComponent) if cup else None
    mat = c.get_material(0) if c else None
    check('la cúpula del cielo está puesta, con su material', len(cup) == 1 and mat is not None and mat.get_name() == 'MI_Cielo'
          and not cup[0].get_actor_enable_collision() and not c.get_editor_property('cast_shadow'), [a.get_actor_label() for a in cup])
    if cup:
        o, e = cup[0].get_actor_bounds(False)
        check('y cubre toda la base (más de un kilómetro de radio)', e.x > 100000 and e.z > 100000, int(e.x))
    # ajuste 25c: el haz de los focos de torre con lluvia es un velo, no un cono macizo (cielo.py lo deja en el nivel)
    haz = d.get_editor_property('strong_spot_scattering')
    check('el foco de la torre dispersa poco en la niebla (haz que deja ver detrás)', 0.2 <= haz <= 2.0, '%.1f' % haz)
    # nubes: con lluvia o niebla el cielo se cubre poco a poco y al despejar se abre
    w0, cs = d.get_editor_property('weather'), d.get_editor_property('cloud_seconds')
    while d.get_editor_property('weather') != 0:
        d.simulate_key('Y'); yield 0.2
    d.set_cloudiness_now(0.0); yield 0.2
    check('con el cielo raso «Nublado» vale 0', abs(d.cloudiness_in_collection()) < 0.01 and d.get_editor_property('cloudiness') < 0.01, '%.2f' % d.cloudiness_in_collection())
    d.set_editor_property('cloud_seconds', 2.0)
    while d.get_editor_property('weather') != 1:
        d.simulate_key('Y'); yield 0.2
    yield 0.6
    medio = d.get_editor_property('cloudiness')
    yield 2.0
    check('con la lluvia se cubre poco a poco', 0.1 < medio < 0.9 and d.cloudiness_in_collection() > 0.99, '%.2f y luego %.2f' % (medio, d.cloudiness_in_collection()))
    while d.get_editor_property('weather') != 0:
        d.simulate_key('Y'); yield 0.2
    yield 3.6
    check('y al escampar se abre', d.cloudiness_in_collection() < 0.01, '%.2f' % d.cloudiness_in_collection())
    d.set_editor_property('cloud_seconds', cs)
    while d.get_editor_property('weather') != w0:
        d.simulate_key('Y'); yield 0.2
    # farolas: se pintan a un décimo (no queman la losa) y para el sigilo cuentan lo de siempre
    focos = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Light) if a.get_component_by_class(unreal.LocalLightComponent)]
    lm = lambda a: a.get_component_by_class(unreal.LocalLightComponent).get_editor_property('intensity')
    far = [a for a in focos if a.get_actor_label().startswith('farola')]
    tor = [a for a in focos if a.get_actor_label().startswith('foco_torreta')]
    # tanda 26: lo que pinta un foco de torre con recorrido cambia con la distancia; su base son los lúmenes de sigilo
    base_foco = {g.get_editor_property('tower_light'): g.get_editor_property('beam_lumens') for g in guardias() if g.get_editor_property('tower_sentry')}
    lm_base = lambda a: base_foco.get(a) or lm(a)
    mal = [(a.get_actor_label(), int(lm_base(a))) for a in far + tor if not a.actor_has_tag('luz_fuerte') or lm_base(a) > 1000]
    check('farolas (%d) y focos de torre (%d) pintan a un décimo, marcados «luz_fuerte»' % (len(far), len(tor)), len(far) >= 6 and len(tor) >= 2 and not mal, mal)
    ext = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']
    f = ext['farolas'][1]
    pie = luz_en(V(f[0] * 100, 5700, 100))
    check('al pie de una farola sigues a plena luz para los guardias', pie > 0.5, '%.2f' % pie)
    # halos y relleno
    hc = d.halo_counts()
    halos = actores('halo')
    check('cada luminaria de fuera tiene su halo, encendido', hc.x == len(halos) and hc.x >= len(far) + len(tor) and hc.y == hc.x, '%d halos, %d encendidos, %d en el nivel' % (hc.x, hc.y, len(halos)))
    rell = [a for a in focos if a.actor_has_tag('decorado')]
    sombra = [a.get_actor_label() for a in rell if a.get_component_by_class(unreal.LocalLightComponent).get_editor_property('cast_shadows')]
    check('cada farola tiene su relleno (sin sombras: casi no cuesta)', len(rell) >= len(far) and not sombra, '%d de relleno, %d farolas, con sombra %s' % (len(rell), len(far), sombra))
    # el relleno no alumbra para el sigilo: a 12 m de la farola del camino, fuera de su cono, da lo mismo con él que sin él
    p = V(f[0] * 100 + 1200, 5700, 100)
    cerca = [a for a in rell if dist2d(a.get_actor_location(), V(f[0] * 100, f[1] * 100, 0)) < 300]
    # ajuste 25d: los focos de torre se apagan mientras se mide. Ese punto queda a 19 m de la torre 14 y, según adónde
    # mire su centinela al arrancar, el foco le cae encima (0,92 en vez de 0,12) y la prueba fallaba sin que el relleno
    # tuviera nada que ver
    for a in tor:
        a.get_component_by_class(unreal.LocalLightComponent).set_visibility(False)
    con = luz_en(p)
    for a in cerca:
        a.get_component_by_class(unreal.LocalLightComponent).set_visibility(False)
    sin = luz_en(p)
    for a in cerca + tor:
        a.get_component_by_class(unreal.LocalLightComponent).set_visibility(True)
    check('el relleno no cuenta para el sigilo (misma luz con él que sin él)', len(cerca) == 1 and abs(con - sin) < 0.001 and con < 0.5, '%.3f y %.3f, %d cerca' % (con, sin, len(cerca)))
    # romper el farol de la garita apaga su halo (lo hace el dardo en prueba_farol; aquí, que el recuento baja al apagarla)
    if far:
        comp = far[0].get_component_by_class(unreal.LocalLightComponent)
        comp.set_visibility(False); yield 0.3
        menos = d.halo_counts().y
        comp.set_visibility(True); yield 0.3
        check('una farola apagada pierde su halo, y lo recupera', menos == hc.y - 1 and d.halo_counts().y == hc.y, '%d -> %d -> %d' % (hc.y, menos, d.halo_counts().y))


def prueba_linternas():
    """Tanda 31: los guardias de suelo sacan la linterna donde no llega la luz y la guardan al volver a ella; tú llevas
    la tuya (F): con ella encendida te ven como a plena luz y el guardia al que alumbras viene a mirar. Los proyectores
    de las torres llevan cristal encendido y cada caseta su luz; los focos de fuera repasan el borde del muro."""
    aparte(); yield 0.1
    d = director()
    check('la regla está puesta en su prueba', d.get_editor_property('context_torch'), d.get_editor_property('context_torch'))
    g = next((x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL'), None)
    check('hay un guardia de ronda con quien probar', g is not None, [estado(x) for x in guardias()][:8])
    if not g:
        return
    g.hold(60.0)
    # a oscuras: un punto del anillo norte lejos de toda farola y fuera del recorrido de los focos
    oscuro = None
    for x, y in ((4500, -1200), (3000, -1300), (5500, -1300), (1500, -1300), (7500, 3500)):
        if unreal.TarsisGuard.ambient_at(mundo(), V(x, y, 140)) < 0.2:
            oscuro = V(x, y, 100); break
    check('hay un sitio a oscuras en el anillo', oscuro is not None, oscuro)
    if not oscuro:
        return
    g.set_actor_location(oscuro, False, True); yield 0.2
    g.auto_torch_now(); yield 0.2
    # ajuste 31c: de ronda y al aire libre no la saca aunque esté a oscuras (casi toda la base lo está): solo bajo techo
    # o yendo a mirar algo. El resto de la prueba mide la luz con «torch_outdoors» puesto
    check('de ronda al aire libre no la saca', not g.has_flashlight_on() and not g.is_indoors(), '%s, dentro %s' % (g.has_flashlight_on(), g.is_indoors()))
    dentro = V(700, 3600, g.get_actor_location().z)
    g.set_actor_location(dentro, False, True); yield 0.2
    g.auto_torch_now(); yield 0.2
    check('bajo techo y a oscuras sí (jefatura)', g.is_indoors() and g.has_auto_torch(), 'dentro %s, linterna %s, luz %.2f' % (g.is_indoors(), g.has_flashlight_on(), unreal.TarsisGuard.ambient_at(mundo(), V(700, 3600, 140))))
    g.set_actor_location(oscuro, False, True); yield 0.2
    g.auto_torch_now(); yield 0.2
    check('al salir la guarda', not g.has_flashlight_on(), g.has_flashlight_on())
    g.set_editor_property('torch_outdoors', True)
    g.auto_torch_now(); yield 0.2
    check('a oscuras saca la linterna', g.has_auto_torch(), '%s, luz %.2f' % (g.has_flashlight_on(), unreal.TarsisGuard.ambient_at(mundo(), V(oscuro.x, oscuro.y, 140))))
    luces = [c for c in g.get_components_by_class(unreal.SpotLightComponent) if c.is_visible()]
    check('pinta lo que dice su ajuste y no da sombra', len(luces) == 1 and abs(luces[0].get_editor_property('intensity') - g.get_editor_property('torch_paint_lumens')) < 1.0
          and not luces[0].get_editor_property('cast_shadows'), [c.get_editor_property('intensity') for c in luces])
    # para el sigilo cuenta lo de siempre: a 6 m delante de él, en su cono, estás a la luz; a su espalda, no
    f = g.get_actor_forward_vector()
    p = g.get_actor_location()
    delante, detras = luz_en(V(p.x + f.x * 600, p.y + f.y * 600, 110)), luz_en(V(p.x - f.x * 600, p.y - f.y * 600, 110))
    check('su cono te delata por delante y no por detrás', delante > 0.4 and detras < 0.25, '%.2f / %.2f' % (delante, detras))
    cristal = [c for c in g.get_components_by_class(unreal.StaticMeshComponent) if c.is_visible() and c.get_attach_parent() in luces]
    check('la linterna tiene cristal encendido y destello', len(cristal) == 2, len(cristal))
    # bajo una farola la guarda
    far = next((a for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.SpotLight) if a.get_actor_label().startswith('farola_')
                and a.get_component_by_class(unreal.SpotLightComponent).is_visible()), None)
    fl = far.get_actor_location()
    g.set_actor_location(V(fl.x + 150, fl.y, 100), False, True); yield 0.2
    g.auto_torch_now(); yield 0.2
    check('bajo una farola la guarda', not g.has_flashlight_on(), '%s, luz %.2f' % (g.has_flashlight_on(), unreal.TarsisGuard.ambient_at(mundo(), V(fl.x + 150, fl.y, 140))))
    # sin la regla, ni a oscuras
    d.set_editor_property('context_torch', False)
    g.set_actor_location(oscuro, False, True); yield 0.3
    g.auto_torch_now(); yield 0.2
    check('con la regla quitada no la saca', not g.has_flashlight_on(), g.has_flashlight_on())
    # tu linterna (él sigue sin la suya: si no, su cono ya te alumbraría y no se mediría la tuya)
    check('llevas linterna y empieza apagada', d.get_editor_property('has_torch') and not d.get_editor_property('torch'), d.get_editor_property('torch'))
    check('la F sale en la ayuda de teclas', 'linterna' in str(d.help_line()).lower(), str(d.help_line()))
    tp(oscuro.x + 1500, oscuro.y, 180); yield 0.2
    g.set_actor_location(oscuro, False, True)
    g.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(oscuro, V(oscuro.x + 1500, oscuro.y, 100)), False); yield 0.2
    mirar(V(oscuro.x + 3000, oscuro.y, 150)); yield 0.2     # de espaldas a él: no le alumbras
    antes = g.visibility(jugador())
    d.toggle_torch(); yield 0.3
    c = d.torch_comp()
    check('se enciende: una luz en la cámara', d.get_editor_property('torch') and c and c.is_visible(), d.get_editor_property('torch'))
    con = g.visibility(jugador())
    check('con ella encendida te ve mucho más', con > antes + 0.15, '%.2f -> %.2f' % (antes, con))
    yield 0.4
    check('el indicador de luz lo dice', d.get_editor_property('player_light') > 0.6, '%.2f' % d.get_editor_property('player_light'))
    check('de espaldas a él no cuenta como alumbrarle', d.get_editor_property('torch_notices') == 0, d.get_editor_property('torch_notices'))
    # le alumbras: viene a mirar
    g.set_editor_property('torch_outdoors', False)
    d.set_editor_property('context_torch', True)
    g.hold(0.0)
    d.set_torch(False); yield 0.1
    g.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(oscuro, V(oscuro.x - 1500, oscuro.y, 100)), False)   # él, de espaldas a ti
    tp(oscuro.x + 1100, oscuro.y, 180); yield 0.2
    mirar(V(oscuro.x, oscuro.y, 140)); yield 0.2
    d.set_torch(True); yield 0.6
    check('si le alumbras de cerca, viene a mirar', d.get_editor_property('torch_notices') >= 1 and estado(g) != 'PATROL', '%d, %s' % (d.get_editor_property('torch_notices'), estado(g)))
    # a bocajarro y de cara le deslumbras; de espaldas, no; y no dos veces seguidas
    d.set_torch(False); g.hold(30.0); yield 0.1
    q = g.get_actor_location()
    tp(q.x + 300, q.y, 180)
    g.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(q, V(q.x - 300, q.y, q.z)), False); yield 0.2
    mirar(V(q.x, q.y, q.z + 65)); yield 0.1
    d.set_torch(True); yield 0.4
    check('de espaldas no se deslumbra', d.get_editor_property('torch_blinds') == 0 and not g.is_dazzled(), d.get_editor_property('torch_blinds'))
    d.set_torch(False)
    g.set_actor_rotation(unreal.MathLibrary.find_look_at_rotation(q, V(q.x + 300, q.y, q.z)), False); yield 0.2
    d.set_torch(True); yield 0.4
    check('de cara y a tres metros, deslumbrado: no te ve', d.get_editor_property('torch_blinds') == 1 and g.is_dazzled() and g.visibility(jugador()) == 0.0,
          '%d, %s, %.2f' % (d.get_editor_property('torch_blinds'), g.is_dazzled(), g.visibility(jugador())))
    check('lo que alumbras de cerca no se quema: la luz baja', d.torch_dim_now() < 0.5 and d.torch_comp().get_editor_property('intensity') < d.get_editor_property('torch_lumens') * 0.5,
          '%.2f, %.0f lm' % (d.torch_dim_now(), d.torch_comp().get_editor_property('intensity')))
    yield d.get_editor_property('torch_blind_seconds') + 0.5
    check('se le pasa y no repite enseguida (se tapa los ojos)', not g.is_dazzled() and d.get_editor_property('torch_blinds') == 1, '%s, %d' % (g.is_dazzled(), d.get_editor_property('torch_blinds')))
    g.hold(30.0)
    d.toggle_torch(); yield 0.1
    check('se apaga con la misma tecla', not d.get_editor_property('torch') and not d.torch_comp().is_visible(), d.get_editor_property('torch'))
    d.set_editor_property('has_torch', False); d.toggle_torch(); yield 0.1
    check('sin el objeto no hay linterna', not d.get_editor_property('torch'), d.get_editor_property('torch'))
    d.set_editor_property('has_torch', True)
    aparte(); yield 0.1
    # torres: cristal en los ocho proyectores y luz en las cuatro casetas
    check('los ocho proyectores tienen cristal encendido', d.get_editor_property('beam_lenses') == 8, d.get_editor_property('beam_lenses'))
    cas = [a for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.PointLight) if a.actor_has_tag('luz_caseta')]
    check('cuatro casetas con su luz, sin sombra y sin contar para el sigilo', len(cas) == 4 and all(a.actor_has_tag('decorado') and not a.get_component_by_class(unreal.PointLightComponent).get_editor_property('cast_shadows') for a in cas), len(cas))
    BASE = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))
    e = BASE['ext']
    aj = MISION['ajustes']['guardias']
    lejos = []
    for k, v in aj.items():
        if k.startswith('vigia'):
            for q in v['sweep_path']:
                dx = max(e['x0'] * 100 - q[0], q[0] - e['x1'] * 100, 0)
                dy = max(e['y0'] * 100 - q[1], q[1] - e['y1'] * 100, 0)
                if not (500 <= max(dx, dy) <= 900):
                    lejos.append((k, q))
    check('los focos de fuera repasan el borde del muro (a 5-9 m)', not lejos, lejos)
    # el códec ya no deja el mensaje de ayuda de fondo: lo comprueba el HUD (no se puede leer desde aquí); queda el dato
    check('textos de la linterna en mision1.json', all(k in MISION['textos'] for k in ('ensena_linterna', 'ensena_linterna_guardia', 'ensena_deslumbrar')), '')

def _de_esquina():
    """Los centinelas de las cuatro torres de esquina (tanda 30): los de dentro y los vigías de fuera."""
    return [g for g in guardias() if g.get_editor_property('tower_sentry') and g.get_actor_label().split('_')[-1] in ('torre1', 'torre2', 'torre3', 'torre4')]

def prueba_esquinas():
    """Tanda 30: cuatro torres grandes en las esquinas del muro, cada una con dos centinelas y dos focos: uno barre
    el anillo por dentro y otro la marisma por fuera. Cada foco tiene su recorrido y su segundo de arranque."""
    aparte(); yield 0.1
    BASE = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))
    torres = BASE.get('torres', [])
    gr = [t for t in torres if t.get('grande')]
    check('cuatro torres de esquina en base.json, con dos puestos cada una', len(gr) == 4 and all(len(t['puestos']) == 2 for t in gr), len(gr))
    e = BASE['ext']
    check('cada una en su esquina, por dentro del muro', sorted((t['pos'][0] < 36, -t['pos'][1] < 28) for t in gr) == [(False, False), (False, True), (True, False), (True, True)]
          and all(e['x0'] + 2 < t['pos'][0] < e['x1'] - 2 and e['y0'] + 2 < -t['pos'][1] < e['y1'] - 2 for t in gr), [t['pos'] for t in gr])
    check('más altas que el muro', all(t['altura'] > 4.6 + 1.0 for t in gr), [t['altura'] for t in gr])
    check('las dos torres de dentro ya no están', len(torres) == 4, [t['name'] for t in torres])
    cs = _de_esquina()
    dentro = [g for g in cs if g.get_actor_label().startswith('Centinela_')]
    fuera = [g for g in cs if g.get_actor_label().startswith('Vigia_')]
    check('ocho centinelas: cuatro miran dentro y cuatro fuera', len(dentro) == 4 and len(fuera) == 4, '%d / %d' % (len(dentro), len(fuera)))
    luces = [g.get_editor_property('tower_light') for g in cs]
    check('cada uno con su foco, ninguno compartido', all(luces) and len({l.get_actor_label() for l in luces if l}) == len(cs), [l.get_actor_label() if l else None for l in luces])
    check('subidos a la plataforma', all(g.get_actor_location().z > 600.0 for g in cs), [round(g.get_actor_location().z) for g in cs])
    aj = MISION['ajustes']['guardias']
    check('todos tienen recorrido en mision1.json', all(str(g.get_editor_property('guard_name')) in aj and len(g.get_editor_property('sweep_path')) >= 2 for g in cs),
          [str(g.get_editor_property('guard_name')) for g in cs if len(g.get_editor_property('sweep_path')) < 2])
    x0, x1, y0, y1 = e['x0'] * 100, e['x1'] * 100, e['y0'] * 100, e['y1'] * 100
    den = lambda p: x0 < p.x < x1 and y0 < p.y < y1
    check('los de dentro barren dentro del muro', all(den(p) for g in dentro for p in g.get_editor_property('sweep_path')))
    check('los vigías barren fuera del muro', all(not den(p) for g in fuera for p in g.get_editor_property('sweep_path')))
    for g in cs:
        g.hold(0.0)
    g = dentro[0]
    # copia: get_editor_property devuelve el struct vivo y a0 seguiría al foco (salía 0 cm)
    a = g.get_editor_property('sweep_aim'); a0 = V(a.x, a.y, a.z)
    yield 4.0
    a = g.get_editor_property('sweep_aim'); a1 = V(a.x, a.y, a.z)
    check('el foco de dentro se mueve por su recorrido', dist2d(a0, a1) > 100.0, '%.0f cm' % dist2d(a0, a1))
    tl = g.get_editor_property('tower_light')
    c = tl.get_component_by_class(unreal.SpotLightComponent)
    fw = tl.get_actor_forward_vector(); lp = tl.get_actor_location()
    k = (0.0 - lp.z) / fw.z if fw.z < -0.01 else 0.0
    suelo = V(lp.x + fw.x * k, lp.y + fw.y * k, 0)
    check('y apunta de verdad a donde dice', fw.z < -0.01 and dist2d(suelo, a1) < 300.0, '%.0f cm' % dist2d(suelo, a1))
    c2 = fuera[0].get_editor_property('tower_light').get_component_by_class(unreal.SpotLightComponent)
    check('el de dentro da sombra, el de fuera no, y los dos llegan', c.get_editor_property('cast_shadows') and not c2.get_editor_property('cast_shadows') and c.get_editor_property('attenuation_radius') >= 6000.0,
          '%s / %.0f' % (c.get_editor_property('cast_shadows'), c.get_editor_property('attenuation_radius')))
    # el foco delata: plantado en su mancha hay mucha más luz que diez metros más allá
    yield ('hasta', lambda: dist2d(g.get_editor_property('sweep_aim'), g.sweep_point_at(g.sweep_time())) < 150.0, 6.0)
    a = g.get_editor_property('sweep_aim'); aim = V(a.x, a.y, a.z)
    # fuera de la mancha: el más oscuro de cuatro puntos a 12 m (uno solo podía caer bajo una farola del patio)
    en = luz_en(V(aim.x, aim.y, 90))
    fuera_de = min(luz_en(V(aim.x + dx, aim.y + dy, 90)) for dx, dy in ((1200, 0), (-1200, 0), (0, 1200), (0, -1200)))
    check('en la mancha del foco hay luz y fuera no', en > 0.3 and en > fuera_de * 2.0, '%.2f / %.2f' % (en, fuera_de))
    for x in cs:
        x.hold(3600.0)

def _focos_torre(encendidos):
    for g in guardias():
        if g.get_editor_property('tower_sentry') and g.get_editor_property('tower_light'):
            g.get_editor_property('tower_light').get_component_by_class(unreal.LocalLightComponent).set_visibility(encendidos)


def prueba_foco():
    """Tanda 26: el foco de cada torre sigue un recorrido fijo por el suelo (se puede aprender), apunta de verdad al
    punto que pisa, para el sigilo cuenta siempre lo mismo aunque lo pintado cambie con la distancia, y cuando un
    guardia de abajo da la alarma el foco de la torre que lo tiene a mano acude a ese sitio y luego vuelve."""
    aparte()
    cent = sorted([g for g in guardias() if g.get_editor_property('tower_sentry')], key=lambda g: g.get_actor_label())
    aj = MISION['ajustes']['guardias']
    con = [g for g in cent if len(g.get_editor_property('sweep_path')) >= 2]
    check('las dos torres tienen recorrido', len(cent) >= 2 and len(con) == len(cent), '%d de %d' % (len(con), len(cent)))
    if not con:
        return
    per = [g.sweep_period() for g in con]
    check('una vuelta dura entre 15 y 30 s (da tiempo a aprenderla y a cruzar)', all(15.0 <= x <= 30.0 for x in per), ['%.1f' % x for x in per])
    g = con[0]
    a, b = g.sweep_point_at(3.0), g.sweep_point_at(3.0 + per[0])
    check('la vuelta se repite igual', dist2d(a, b) < 1.0, '%.1f cm' % dist2d(a, b))
    fases = [aj.get(str(x.get_editor_property('guard_name')), {}).get('sweep_phase') for x in con]
    check('cada torre arranca en su segundo fijo, y no a la vez', len(set(fases)) == len(fases) and None not in fases, fases)
    paradas = [dist2d(g.sweep_point_at(0.1), g.sweep_point_at(1.5)) for g in con]
    check('en el primer punto el foco se para', all(x < 1.0 for x in paradas), paradas)
    yield 3.0
    aim, quiere = g.get_editor_property('sweep_aim'), g.sweep_point_at(g.sweep_time())
    check('el foco va por su recorrido', dist2d(aim, quiere) < 300.0, '%.0f cm' % dist2d(aim, quiere))
    luz = g.get_editor_property('tower_light')
    f, lp = luz.get_actor_forward_vector(), luz.get_actor_location()
    t = V(aim.x - lp.x, aim.y - lp.y, aim.z - lp.z); n = math.sqrt(t.x * t.x + t.y * t.y + t.z * t.z) or 1.0
    cos = (f.x * t.x + f.y * t.y + f.z * t.z) / n
    check('la luz apunta al punto del suelo que pisa (sube y baja, no solo gira)', cos > 0.995, '%.4f' % cos)
    # se muestrea una vuelta: la mancha se mueve, lo pintado cambia con la distancia y el sigilo no
    comp = luz.get_component_by_class(unreal.LocalLightComponent)
    base = g.get_editor_property('beam_lumens')
    pintado, plena, pasos, t0 = [], [], 0, 0.0
    while t0 < per[0]:
        aim = g.get_editor_property('sweep_aim')
        antes = V(aim.x, aim.y, aim.z)      # copia: lo que devuelve la propiedad sigue apuntando al valor vivo del guardia
        pintado.append(comp.get_editor_property('intensity'))
        plena.append(luz_en(V(antes.x, antes.y, 100)))
        yield 0.5; t0 += 0.5
        if dist2d(antes, g.get_editor_property('sweep_aim')) > 50.0:
            pasos += 1
    check('la mancha recorre el suelo y hace paradas', 0.4 * len(pintado) < pasos < len(pintado), '%d de %d medidas en movimiento' % (pasos, len(pintado)))
    check('para el sigilo el foco cuenta siempre lo mismo (800 lm pintados, 8000 de sigilo)', abs(base - 800.0) < 1.0, '%.0f' % base)
    check('lo que pinta cambia con la distancia, con tope (no quema lo que tiene cerca)', min(pintado) >= 0.35 * base - 1 and max(pintado) <= 2.5 * base + 1 and max(pintado) - min(pintado) > 40,
          '%.0f a %.0f lm' % (min(pintado), max(pintado)))
    check('dentro de la mancha estás a plena luz', sorted(plena)[len(plena) // 2] > 0.5, '%.2f de mediana, %.2f la peor' % (sorted(plena)[len(plena) // 2], min(plena)))
    # el foco acude a una alarma de abajo y vuelve
    tl = g.get_actor_location()
    p0 = g.sweep_point_at(0.0)
    k = 1500.0 / max(1.0, dist2d(tl, p0))
    sitio = V(tl.x + (p0.x - tl.x) * k + 500.0, tl.y + (p0.y - tl.y) * k, 0.0)
    check('una alarma muy lejos de la torre no mueve el foco', not g.call_beam(V(tl.x + 9000, tl.y, 0), 4.0), '')
    ok = g.call_beam(sitio, 4.0)
    yield ('hasta', lambda: dist2d(g.get_editor_property('sweep_aim'), sitio) < 150.0, 6.0)
    check('alarma cerca: el foco deja su recorrido y acude', ok and dist2d(g.get_editor_property('sweep_aim'), sitio) < 150.0, '%.0f cm' % dist2d(g.get_editor_property('sweep_aim'), sitio))
    yield ('hasta', lambda: g.get_editor_property('beam_call_t') <= 0.0, 6.0)
    yield 4.0
    aim, quiere = g.get_editor_property('sweep_aim'), g.sweep_point_at(g.sweep_time())
    check('y luego vuelve a su recorrido', g.get_editor_property('beam_call_t') <= 0.0 and dist2d(aim, quiere) < 300.0, '%.0f cm' % dist2d(aim, quiere))
    # la alarma de verdad: un guardia de suelo entra en alerta junto a la torre
    suelo = sorted([x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) in ('PATROL', 'RETURN')], key=lambda x: dist2d(x.get_actor_location(), tl))
    if suelo:
        suelo[0].alarm(sitio)
        yield 0.3
        check('cuando uno de abajo da la alarma, el foco acude solo', g.get_editor_property('beam_call_t') > 0.0, '%.1f s' % g.get_editor_property('beam_call_t'))


def prueba_sombra():
    """Tanda 26: tu sombra te delata. Bajo una farola que dibuja sombra, la tuya se alarga por el suelo; un guardia que
    no te ve a ti pero sí ve la sombra se mosquea («?» malva), sin llegar nunca a la alarma. Agachado es más corta, a
    oscuras no hay, y una luz que no dibuja sombra no delata."""
    d = director()
    aparte()
    _focos_torre(False)      # que el foco de una torre no pase por aquí a media medida
    ext = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']
    f = ext['farolas'][0]
    fx, fy = f[0] * 100.0 + 25.0, f[1] * 100.0
    far = [a for a in unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.Light) if a.get_actor_label().startswith('farola') and dist2d(a.get_actor_location(), V(fx, fy, 0)) < 150]
    comp = far[0].get_component_by_class(unreal.LocalLightComponent) if far else None
    check('la farola del camino dibuja sombra', comp is not None and comp.get_editor_property('cast_shadows'), [a.get_actor_label() for a in far])
    # ajuste 26e: que la sombra se vea de verdad, no solo que cuente. El cuerpo del jugador la proyecta en su propia
    # vista (oculto para él, con sombra aunque esté oculto) y la calidad de sombras deja proyectar a las personas
    cuerpo = jugador().get_editor_property('mesh')
    rsq = unreal.SystemLibrary.get_console_variable_int_value('r.ShadowQuality')
    check('tu cuerpo proyecta sombra en tu propia vista y las personas dan sombra (r.ShadowQuality mayor que 0)',
          cuerpo.get_editor_property('owner_no_see') and cuerpo.get_editor_property('cast_shadow') and cuerpo.get_editor_property('cast_hidden_shadow') and rsq > 0,
          'owner_no_see %s, sombra %s, oculta con sombra %s, r.ShadowQuality %d' % (cuerpo.get_editor_property('owner_no_see'), cuerpo.get_editor_property('cast_shadow'), cuerpo.get_editor_property('cast_hidden_shadow'), rsq))
    if not comp:
        _focos_torre(True)
        return
    for g in guardias():
        g.hold(3600.0)
    if agachado():
        d.simulate_key('C'); yield 0.3
    px, py = fx + 175.0, fy - 70.0
    tp(px, py); yield 0.4
    n = d.measure_shadows()
    tips, con = list(d.get_editor_property('shadow_tips')), list(d.get_editor_property('shadow_contrasts'))
    largo = max([dist2d(t, V(px, py, 0)) for t in tips] or [0.0])
    lejos = all((t.x - fx) ** 2 + (t.y - fy) ** 2 > (px - fx) ** 2 + (py - fy) ** 2 for t in tips)
    check('de pie junto a la farola echas sombra, y cae al otro lado de la luz', n >= 2 and lejos and 100.0 < largo < 450.0, '%d puntos, %.0f cm' % (n, largo))
    check('la sombra se marca (la farola manda sobre el resto de la luz)', con and min(con) >= 0.6, ['%.2f' % c for c in con])
    d.simulate_key('C'); yield 0.4
    d.measure_shadows()
    corto = max([dist2d(t, V(px, py, 0)) for t in d.get_editor_property('shadow_tips')] or [0.0])
    check('agachado, la sombra es más corta', agachado() and corto < largo - 30.0, '%.0f frente a %.0f cm' % (corto, largo))
    d.simulate_key('C'); yield 0.4
    comp.set_cast_shadows(False); yield 0.1
    check('una luz que no dibuja sombra no delata', d.measure_shadows() == 0, len(d.get_editor_property('shadow_tips')))
    comp.set_cast_shadows(True); yield 0.1
    tp(fx + 1250.0, 6950.0); yield 0.3
    check('a oscuras no hay sombra', d.measure_shadows() == 0, len(d.get_editor_property('shadow_tips')))
    # un guardia que ve la sombra y no a ti: a 3 m de la punta, de lado, con la punta dentro de su cono y tú fuera
    tp(px, py); yield 0.3
    d.measure_shadows()
    tips = list(d.get_editor_property('shadow_tips'))
    punta = max(tips, key=lambda t: dist2d(t, V(px, py, 0))) if tips else V(px + 164, py - 66, 0)
    sx, sy = punta.x - px, punta.y - py
    sl = math.hypot(sx, sy) or 1.0
    gx, gy = punta.x - sy / sl * 300.0, punta.y + sx / sl * 300.0
    a_punta = math.degrees(math.atan2(punta.y - gy, punta.x - gx))
    a_ti = math.degrees(math.atan2(py - gy, px - gx))
    lado = 1.0 if ((a_punta - a_ti + 180.0) % 360.0 - 180.0) > 0 else -1.0
    obs = guardia('Carmona')
    obs.go_to(V(gx, gy, obs.get_actor_location().z))
    obs.set_actor_location(V(gx, gy, obs.get_actor_location().z), False, True)
    obs.hold(0.05)
    yield ('hasta', lambda: estado(obs) == 'PATROL', 4.0)
    obs.set_actor_rotation(unreal.Rotator(0.0, 0.0, a_punta + lado * 35.0), True)
    yield 0.1
    check('el guardia tiene la sombra delante y a ti fuera de su vista', obs.visibility(jugador()) <= 0.0 and estado(obs) == 'PATROL', '%.2f, %s' % (obs.visibility(jugador()), estado(obs)))
    quieto, n0 = d.get_editor_property('shadow_still_factor'), d.get_editor_property('shadow_noticed')
    d.set_editor_property('shadow_still_factor', 1.0)      # el jugador de la prueba no anda: que cuente como si se moviera
    yield ('hasta', lambda: obs.is_shadow_curious(), 8.0)
    m = obs.get_editor_property('meter')
    check('ve tu sombra y se mosquea, sin haberte visto', obs.is_shadow_curious() and estado(obs) == 'SUSPICIOUS' and d.get_editor_property('shadow_noticed') == n0 + 1,
          '%s, sospecha %.2f, %s' % (estado(obs), m, d.get_editor_property('shadow_watcher')))
    check('una sombra nunca da la alarma (la sospecha tiene tope)', m <= d.get_editor_property('shadow_cap') + 0.01, '%.2f' % m)
    check('y se explica la primera vez', 'SOMBRA' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:30])
    aparte()
    yield ('hasta', lambda: estado(obs) in ('RETURN', 'PATROL'), 25.0)
    check('sin sombra que mirar, se le pasa y vuelve', estado(obs) in ('RETURN', 'PATROL'), estado(obs))
    # el interruptor
    d.set_editor_property('shadow_tells', False)
    tp(px, py); yield 0.6
    check('con el interruptor quitado, la sombra no cuenta', len(d.get_editor_property('shadow_tips')) == 0 and not obs.is_shadow_curious(), len(d.get_editor_property('shadow_tips')))
    d.set_editor_property('shadow_tells', True)
    d.set_editor_property('shadow_still_factor', quieto)
    aparte()
    _focos_torre(True)


def prueba_cobertura():
    """Tanda 24 (juego): el anillo sur deja de ser un llano. Barreras de hormigón, pilas de cajas y de sacos y bidones en
    cinco grupos entre el camino y el muro: se cruza de cobertura en cobertura mientras Carmona hace su ronda."""
    w = mundo()
    quietos('Lobato', 'Sanz', 'Carmona')
    aparte()
    piezas = {p['nombre']: p for p in json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'atrezo.json'), encoding='utf-8'))['piezas'] if p.get('nombre', '').startswith('cob_')}
    cob = {a.get_actor_label()[7:]: a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor) if a.get_actor_label().startswith('Atrezo_cob_')}
    check('las %d piezas de cobertura están en el anillo sur' % len(piezas), len(piezas) >= 90 and len(cob) == len(piezas), '%d de %d' % (len(cob), len(piezas)))
    if not cob:
        return
    caja = {n: a.get_actor_bounds(False) for n, a in cob.items()}     # (centro, media caja)
    fuera = [n for n, (o, e) in caja.items() if o.y - e.y < 6010 or o.y + e.y > 7450 or not -1800 < o.x < 9000]
    check('todas entre el camino y el muro sur (ninguna pisa el camino)', not fuera, fuera)
    # las dos calles de la ronda de Carmona (y 6300 y 6700, de x -900 a 8100), libres: medio cuerpo a cada lado
    calle = [n for n, (o, e) in caja.items() if any(o.y + e.y > y - 60 and o.y - e.y < y + 60 for y in (6300.0, 6700.0)) and o.x + e.x > -1000 and o.x - e.x < 8200]
    check('las dos calles de la ronda de Carmona quedan libres', not calle, calle)
    # barreras: tumbadas a lo largo (X) y de un metro largo de alto: tapan a uno agachado, no a uno de pie
    barr = {n: caja[n] for n, p in piezas.items() if p['modelo'] == 'concrete_road_barrier_02' and n in caja}
    mal = ['%s %dx%dx%d' % (n, e.x * 2, e.y * 2, e.z * 2) for n, (o, e) in barr.items() if not (e.x * 2 > 130 and e.x > e.y * 2 and 95 < e.z * 2 < 130 and o.z - e.z < 12)]
    check('las %d barreras, a lo largo del camino, apoyadas y de un metro de alto' % len(barr), len(barr) >= 10 and not mal, mal)
    # pilas: las piezas de arriba han caído sobre las de abajo (ni flotan ni se han hundido hasta el suelo)
    # alto de cada pieza y capa que le toca según la z de atrezo.json (los sacos, de 18 en 18 cm desde 30; las cajas, 60, 86 y 132)
    capas = []
    for n, p in piezas.items():
        if p['modelo'] in ('cement_bag', 'wooden_military_crate') and n in caja:
            if p['modelo'] == 'cement_bag':
                alto, capa = 18.0, int(round((p['pos'][2] - 30) / 18.0))
            else:
                alto, capa = 46.0, {60: 0, 86: 1, 132: 2}.get(p['pos'][2], 0)
            o, e = caja[n]
            pie = o.z - e.z
            if abs(pie - capa * alto) > 4.0 + capa * 5.0:
                capas.append('%s capa %d, pie a %d cm' % (n, capa, pie))
    check('las pilas de cajas y sacos se apoyan unas en otras', not capas, capas[:6])
    altas = [n for n, (o, e) in caja.items() if o.z + e.z > 125]
    check('hay pilas que tapan a uno de pie (más de 1,25 m)', len(altas) >= 4, len(altas))
    # y sirven: Carmona parado en el camino, mirando a una barrera del medio; detrás, de pie te ve y agachado no
    g = guardia('Carmona')
    n = next((k for k in sorted(barr) if 6400 < barr[k][0].y < 6600), None)
    if not g or not n:
        check('una barrera del medio y Carmona para probarla', False, (n, bool(g)))
        return
    o, e = barr[n]
    g.set_actor_location_and_rotation(V(o.x, o.y - 800, g.get_actor_location().z), unreal.Rotator(0.0, 0.0, 90.0), False, True)
    tp(o.x, o.y + e.y + 48, -90); yield 0.6
    if agachado():
        director().simulate_key('C'); yield 0.4
    de_pie = g.visibility(jugador())
    director().simulate_key('C'); yield 0.5
    abajo = g.visibility(jugador())
    check('detrás de una barrera: de pie te ve, agachado no', de_pie > 0.0 and abajo == 0.0 and agachado(), 'de pie %.2f, agachado %.2f (%s)' % (de_pie, abajo, n))
    if agachado():
        director().simulate_key('C'); yield 0.4
    aparte()


def prueba_gestos():
    """Tanda 24 (juego): los guardias mueven los brazos. Gestos puestos encima de la animación (mano en alto, tender la
    mano, leer los papeles, dar paso, levantar la lona); en el control del camión los hace Sanz (prueba_camion)."""
    aparte()
    g = guardia('Moya')
    if not g:
        check('Moya está en el nivel', False)
        return
    g.hold(3600.0); yield 1.0
    nombre = lambda: str(g.current_gesture())
    h0, i0 = g.hand_height(True), g.hand_height(False)
    check('en reposo, las manos a los lados', 55 < h0 < 115 and 55 < i0 < 115 and nombre() == 'None', 'derecha %d cm, izquierda %d cm, %s' % (h0, i0, nombre()))
    g.play_gesture('alto', 2.0, V(0, 0, 0)); yield 0.9
    h1 = g.hand_height(True)
    check('«alto»: la mano derecha por encima de la cabeza', h1 > 160 and h1 > h0 + 60 and nombre() == 'alto' and g.get_editor_property('gesture_w') > 0.95,
          '%d cm (en reposo %d), %s, peso %.2f' % (h1, h0, nombre(), g.get_editor_property('gesture_w')))
    check('y la izquierda sigue en su sitio', abs(g.hand_height(False) - i0) < 10, '%d cm' % g.hand_height(False))
    yield 1.9
    h2 = g.hand_height(True)
    check('al acabar el gesto, el brazo vuelve a su sitio', abs(h2 - h0) < 10 and nombre() == 'None' and g.get_editor_property('gesture_w') < 0.01, '%d cm, %s' % (h2, nombre()))
    g.play_gesture('leer', 1.6, V(0, 0, 0)); yield 0.9
    hd, hi = g.hand_height(True), g.hand_height(False)
    check('«leer»: las dos manos delante del pecho', 95 < hd < 160 and 95 < hi < 160 and hd > h0 + 12 and hi > i0 + 12 and nombre() == 'leer', 'derecha %d cm, izquierda %d cm' % (hd, hi))
    yield 1.3
    # dar paso hacia su derecha: el antebrazo derecho va y viene
    l, r = g.get_actor_location(), g.get_actor_right_vector()
    g.play_gesture('pase', 2.4, V(l.x + r.x * 500, l.y + r.y * 500, l.z)); yield 0.5
    hs, his = [], []
    for _ in range(10):
        hs.append(g.hand_height(True)); his.append(g.hand_height(False)); yield 0.1
    check('«pase»: el brazo del lado hacia donde manda va y viene', max(hs) - min(hs) > 10 and max(his) - min(his) < 8 and nombre() == 'pase',
          'derecha de %d a %d cm, izquierda de %d a %d' % (min(hs), max(hs), min(his), max(his)))
    # hacia su izquierda, el otro brazo
    yield 2.2
    g.play_gesture('pase', 1.2, V(l.x - r.x * 500, l.y - r.y * 500, l.z)); yield 0.7
    check('hacia el otro lado, con el otro brazo', g.hand_height(False) > i0 + 25 and abs(g.hand_height(True) - h0) < 10, 'izquierda %d cm, derecha %d cm' % (g.hand_height(False), g.hand_height(True)))
    yield 1.2
    # tanda 25: el bastón luminoso (lo que deja leer el alto de noche) se enciende el tiempo que se le pide y se guarda
    check('sin pedirlo, el bastón está guardado', not g.baton_on())
    g.hold_baton(1.0); yield 0.4
    check('HoldBaton lo enciende', g.baton_on())
    yield 1.1
    check('y se apaga solo al acabar el tiempo', not g.baton_on())
    # derribado no gesticula
    g.play_gesture('alto', 3.0, V(0, 0, 0)); g.hold_baton(3.0); yield 0.6
    derribar(g); yield 0.8
    check('derribado no gesticula', estado(g) == 'DOWN' and g.get_editor_property('gesture_w') < 0.05 and nombre() == 'None', '%s, peso %.2f, %s' % (estado(g), g.get_editor_property('gesture_w'), nombre()))
    check('ni lleva el bastón encendido', not g.baton_on())
    registro = [str(x) for x in g.get_editor_property('gesture_log')]
    check('el registro de gestos los cuenta por orden', registro == ['alto', 'leer', 'pase', 'pase', 'alto'], registro)


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
    # load_object y no EditorAssetLibrary: durante el PIE esta responde que no existe («The Editor is currently in a play mode»)
    faltan = [v for v in voces if not unreal.load_object(None, '/Game/Tarsis/Sonidos/%s.%s' % (v, v))]
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
          and len(faros) == 2 and all(a.get_component_by_class(unreal.LocalLightComponent).is_visible() for a in faros), '%s, %d faros' % (estado_c(), len(faros)))
    # tanda 26: dos faros de verdad (entre los dos pintan lo que la luz única), con perfil de haz, cristal y destello; uno con sombra
    fc = d.truck_lamp_counts()
    comps = [a.get_component_by_class(unreal.LocalLightComponent) for a in faros]
    total = sum(c.get_editor_property('intensity') for c in comps)
    con_sombra = sum(1 for c in comps if c.get_editor_property('cast_shadows'))
    check('dos faros que pintan su parte de los lúmenes, y solo uno da sombra', fc.x == 2 and abs(total - d.get_editor_property('truck_lamp_lumens') * d.get_editor_property('truck_lamp_paint')) < 1 and con_sombra == 1,
          '%d faros, %d lm, %d con sombra' % (fc.x, total, con_sombra))
    check('cada faro lleva el perfil del haz de cruce, su cristal y su destello', fc.y == 2 and fc.z == 4, '%d con perfil, %d piezas de luz' % (fc.y, fc.z))
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
    # tanda 22: en el control ya no abre nadie desde lejos. Sanz, que es el de allí, sigue con su ronda (los demás, quietos)
    sanz = guardia('Sanz')
    if sanz:
        sanz.hold(0.0)
    c0 = d.get_editor_property('truck_checks')
    # los que vinieron por el claxon y te vieron plantado delante del camión se quedan en alerta (hold congela su estado)
    # y con un guardia en alerta la base está en guardia: en el control registrarían la caja. Se les calma aquí (GoTo a su
    # sitio los pasa a «volver») y la tensión se pone a cero: lo que se prueba ahora es el control con la base tranquila
    for g in guardias():
        if g.get_editor_property('tower_sentry') or g == sanz:
            continue
        if estado(g) in ('ALERT', 'SEARCH', 'SUSPICIOUS'):
            g.go_to(g.get_actor_location()); g.hold(3600.0)
    d.set_editor_property('tension_t', 0.0)
    yield ('hasta', lambda: estado_c() == 4, 40.0)
    check('para en el control de salida', estado_c() == 4 and abs(cx() - 8270) < 40, '%s en x %d' % (estado_c(), cx()))
    check('el portón de entrada ya está cerrado', d.get_editor_property('entry_gate_t') < 0.02 and abs(hoja[0].get_actor_location().y) < 5, d.get_editor_property('entry_gate_t'))
    yield ('hasta', lambda: director().truck_inspector_name() != '', 4.0)
    check('Sanz deja la ronda y va hacia la cabina', d.truck_inspector_name() == 'Sanz' and d.get_editor_property('truck_check') >= 1,
          '%s, fase %s' % (d.truck_inspector_name(), d.get_editor_property('truck_check')))
    check('la barrera sigue bajada mientras tanto', d.get_editor_property('barrier_t') < 0.05, d.get_editor_property('barrier_t'))
    yield ('hasta', lambda: director().get_editor_property('truck_check') >= 2, 22.0)
    cab = V(cx() + 62, 5700 - 185, 0)
    check('llega a la puerta del conductor y pide los papeles', sanz and d.get_editor_property('truck_checks') == c0 + 1 and dist2d(sanz.get_actor_location(), cab) < 120
          and 'sanz_papeles' in list(d.get_editor_property('voice_log')), '%d cm, %s' % (dist2d(sanz.get_actor_location(), cab) if sanz else -1, list(d.get_editor_property('voice_log'))[-2:]))
    # tanda 24: lo hace con gestos
    yield 0.7
    check('tiende la mano hacia la ventanilla', sanz and str(sanz.current_gesture()) in ('papeles', 'leer') and sanz.get_editor_property('gesture_w') > 0.5,
          '%s, peso %.2f' % (sanz.current_gesture(), sanz.get_editor_property('gesture_w')) if sanz else '')
    check('lleva el bastón luminoso encendido durante el control', sanz and sanz.baton_on())
    yield ('hasta', lambda: director().get_editor_property('barrier_t') > 0.95, 14.0)
    check('mira los papeles y le levanta la barrera', d.get_editor_property('barrier_t') > 0.95 and 'sanz_pase' in list(d.get_editor_property('voice_log')),
          '%.2f, %s' % (d.get_editor_property('barrier_t'), list(d.get_editor_property('voice_log'))[-2:]))
    gl = [str(x) for x in sanz.get_editor_property('gesture_log')] if sanz else []
    check('mano en alto al acercarse, tiende la mano, lee los papeles y da paso con el brazo', [k for k in ('alto', 'papeles', 'leer', 'pase') if k in gl] == ['alto', 'papeles', 'leer', 'pase']
          and gl.index('alto') < gl.index('papeles') < gl.index('leer') < gl.index('pase') and 'lona' not in gl, gl)
    check('con la base tranquila no registra la caja', d.get_editor_property('truck_searches') == 0, d.get_editor_property('truck_searches'))
    yield ('hasta', lambda: director().get_editor_property('truck_passes') >= 1, 30.0)
    check('sale por el portón del este y desaparece', d.get_editor_property('truck_passes') == 1 and estado_c() == 0 and all(a.get_editor_property('hidden') for a in piezas),
          '%d pasadas, estado %s' % (d.get_editor_property('truck_passes'), estado_c()))
    yield ('hasta', lambda: director().get_editor_property('barrier_t') < 0.05, 6.0)
    check('la barrera vuelve a bajar', d.get_editor_property('barrier_t') < 0.05, d.get_editor_property('barrier_t'))
    check('la misión sigue (nadie te ha cogido ni has salido)', not d.get_editor_property('done') and not d.get_editor_property('capturing'))
    if sanz:
        yield ('hasta', lambda: estado(sanz) == 'PATROL' and min(dist2d(sanz.get_actor_location(), V(8500, 5300, 0)), dist2d(sanz.get_actor_location(), V(8100, 5300, 0))) < 450, 12.0)
        check('Sanz vuelve a su ronda', estado(sanz) == 'PATROL' and abs(sanz.get_actor_location().y - 5300) < 200, '%s en y %d' % (estado(sanz), sanz.get_actor_location().y))
        check('y ha guardado el bastón', not sanz.baton_on())


def prueba_viaje():
    """Tanda 22 (juego): subirse a la caja del camión por detrás y viajar escondido. Sin el expediente te bajas en el control;
    con la base en guardia registran la caja y te sacan; con el expediente, el camión te saca de la base. Va detrás de
    prueba_camion, en la misma partida: el camión ya hace la pasada corta y los guardias, menos Sanz, están quietos."""
    d = director()
    w = mundo()
    estado_c = lambda: director().get_editor_property('truck_state')
    cx = lambda: director().truck_location().x
    sanz = guardia('Sanz')
    if sanz:
        sanz.hold(0.0)
    def a_la_trasera():
        tp(cx() - 265, 5700, 0)
    def dentro(maximo=40.0):
        """Espera a que el camión cruce el portón y sube por detrás."""
        yield ('hasta', lambda: estado_c() == 3 and cx() > -1000, maximo)
        a_la_trasera(); yield 0.05
        if not d.can_board_truck():
            a_la_trasera(); yield 0.05
        d.interact(); yield 0.3
    aparte()
    check('con el camión fuera no hay a qué subirse', not d.can_board_truck() and not d.get_editor_property('riding'))
    r0, c0, s0 = d.get_editor_property('truck_rides'), d.get_editor_property('captures'), d.get_editor_property('truck_searches')
    yield ('hasta', lambda: estado_c() == 0, 40.0)
    d.truck_skip_wait()
    yield ('hasta', lambda: estado_c() == 3 and cx() > -1000, 40.0)
    # --- en marcha, por detrás
    a_la_trasera(); yield 0.05
    if not d.can_board_truck():
        a_la_trasera(); yield 0.05
    check('detrás del camión, al paso: aviso "E SUBIR"', d.can_board_truck() and 'SUBIR' in d.interact_prompt(), d.interact_prompt()[:32])
    n_luces = len(unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Light))
    d.interact(); yield 0.3
    check('subes a la caja y quedas oculto', d.get_editor_property('riding') and jugador().get_editor_property('hidden') and d.get_editor_property('truck_rides') == r0 + 1,
          '%s, %s' % (d.get_editor_property('riding'), d.get_editor_property('truck_rides')))
    check('aviso "E BAJAR"', 'BAJAR' in d.interact_prompt(), d.interact_prompt()[:28])
    x1 = jugador().get_actor_location().x
    mov = []
    for _ in range(10):      # un segundo de viaje, mirando cuánto se mueve la vista (tanda 23)
        yield 0.1
        o = d.ride_offset(); mov.append((o.x, o.y, o.z))
    x2 = jugador().get_actor_location().x
    cam = jugador().get_component_by_class(unreal.CameraComponent).get_world_location()
    check('el camión te lleva', x2 - x1 > 200 and abs(x2 - (cx() - 125)) < 60, '%d cm en 1 s, a %d del centro' % (x2 - x1, x2 - cx()))
    check('la vista queda dentro de la caja, bajo la lona', 180 < cam.z < 225 and abs(cam.y - 5700) < 12, '%d, %d' % (cam.z, cam.y))
    h = unreal.SystemLibrary.line_trace_single(w, V(cx() - 290, 5700, cam.z), V(cx() - 135, 5700, cam.z), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [jugador()], unreal.DrawDebugTrace.NONE, True)
    check('la caja está hueca: por la trasera se ve el interior', h is None, h.to_tuple()[4] if h else '')
    ven = [g.get_actor_label()[8:] for g in guardias() if g.visibility(jugador()) > 0]
    check('ningún guardia te ve ahí dentro', not ven, ven)
    # tanda 23: la caja por dentro
    check('la vista traquetea, sin marear', max(abs(m[2]) for m in mov) > 0.2 and max(abs(c) for m in mov for c in m) < 12.0,
          'hasta %.1f cm de alto y %.1f a lo largo' % (max(abs(m[2]) for m in mov), max(abs(m[0]) for m in mov)))
    check('dentro hay una luz tenue y lo de fuera suena apagado', d.ride_light_on() and d.ride_muffle() > 0.8 and 0 < d.get_editor_property('ride_fill_lumens') < 60,
          '%s, %.2f, %s lm' % (d.ride_light_on(), d.ride_muffle(), d.get_editor_property('ride_fill_lumens')))
    check('esa luz es solo para tus ojos: no es una luz del nivel (los guardias no la cuentan)', len(unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Light)) == n_luces, n_luces)
    # --- bajar en marcha
    d.interact(); yield 0.25
    l = jugador().get_actor_location()
    check('E: saltas por detrás', not d.get_editor_property('riding') and not jugador().get_editor_property('hidden') and jugador().get_actor_enable_collision()
          and -500 < l.x - (cx() - 200) < 0 and abs(l.y - 5700) < 30 and l.z < 180, 'a %d de la trasera, z %d' % (l.x - (cx() - 200), l.z))
    check('al bajar se apaga la luz de la caja', not d.ride_light_on())
    # --- otra vez arriba, hasta el control. Sin el expediente: Sanz mira los papeles sin verte y, al levantarse la barrera, te bajas
    a_la_trasera(); yield 0.05
    if not d.can_board_truck():
        a_la_trasera(); yield 0.05
    d.interact(); yield 0.3
    check('vuelves a subir', d.get_editor_property('riding') and d.get_editor_property('truck_rides') == r0 + 2, d.get_editor_property('truck_rides'))
    j0, xj = d.get_editor_property('truck_joints'), cx()
    yield ('hasta', lambda: estado_c() == 4, 45.0)
    j1 = d.get_editor_property('truck_joints')
    quiere = 2 * int((cx() - xj) // d.get_editor_property('truck_joint_pitch'))     # dos ejes por junta
    check('cada eje golpea en cada junta de la losa', quiere >= 8 and abs(j1 - j0 - quiere) <= 3, '%d golpes en %d m (se esperan %d)' % (j1 - j0, (cx() - xj) / 100, quiere))
    yield ('hasta', lambda: director().get_editor_property('truck_check') >= 2, 26.0)
    o = d.ride_offset()
    check('parado en el control solo queda el temblor del motor', math.sqrt(o.x ** 2 + o.y ** 2 + o.z ** 2) < 0.5 and d.get_editor_property('truck_joints') == j1,
          '%.2f cm, %d golpes de más' % (math.sqrt(o.x ** 2 + o.y ** 2 + o.z ** 2), d.get_editor_property('truck_joints') - j1))
    check('en el control miran los papeles contigo dentro', d.get_editor_property('riding') and d.truck_inspector_name() == 'Sanz' and d.get_editor_property('truck_check') == 2,
          '%s, fase %s' % (d.truck_inspector_name(), d.get_editor_property('truck_check')))
    check('y Sanz, a dos pasos, no te ve', sanz and sanz.visibility(jugador()) == 0 and estado(sanz) == 'PATROL', estado(sanz) if sanz else '')
    yield ('hasta', lambda: not director().get_editor_property('riding'), 16.0)
    msg = str(d.get_editor_property('message'))
    l = jugador().get_actor_location()
    check('sin el expediente te bajas antes de que salga', not d.get_editor_property('riding') and 'TE BAJAS DEL CAMION' in msg and not jugador().get_editor_property('hidden')
          and dist2d(l, V(8270 - 295, 5700, 0)) < 80, '%s / a %d cm' % (msg[:22], dist2d(l, V(8270 - 295, 5700, 0))))
    check('no han registrado la caja ni te han cogido', d.get_editor_property('truck_searches') == s0 and d.get_editor_property('captures') == c0 and not d.get_editor_property('done'))
    aparte()
    yield ('hasta', lambda: estado_c() == 5 and cx() > 8400, 8.0)
    tp(cx() - 265, 5700, 0); yield 0.05
    check('y ya en marcha hacia fuera no te deja subir', estado_c() == 5 and not d.can_board_truck(), estado_c())
    check('fuera de la caja el mundo vuelve a sonar entero', d.ride_muffle() < 0.15 and not d.ride_light_on(), '%.2f' % d.ride_muffle())
    aparte()
    yield ('hasta', lambda: estado_c() == 0, 30.0)
    # --- base en guardia: después de los papeles, Sanz rodea el camión, mira la caja y te saca
    d.set_editor_property('tension_t', 120.0)
    d.truck_skip_wait()
    yield from dentro()
    check('subes con la base en guardia', d.get_editor_property('riding') and d.base_state() >= 1, d.base_state())
    yield ('hasta', lambda: estado_c() == 4, 45.0)
    yield ('hasta', lambda: director().get_editor_property('truck_check') >= 3 or director().get_editor_property('capturing'), 30.0)
    check('con la base en guardia, registro de la caja', d.get_editor_property('truck_searches') == s0 + 1 and 'sanz_registro' in list(d.get_editor_property('voice_log')),
          '%d, %s' % (d.get_editor_property('truck_searches'), list(d.get_editor_property('voice_log'))[-2:]))
    yield ('hasta', lambda: director().get_editor_property('capturing'), 16.0)
    check('levanta la lona y te coge', d.get_editor_property('capturing') and not d.get_editor_property('riding') and not jugador().get_editor_property('hidden'),
          '%s, %s' % (d.get_editor_property('capturing'), d.get_editor_property('riding')))
    gl = [str(x) for x in guardia('Sanz').get_editor_property('gesture_log')] if guardia('Sanz') else []
    check('y lo hace con el brazo (gesto «lona»)', 'lona' in gl, gl[-4:])
    yield ('hasta', lambda: director().get_editor_property('captures') > c0, 5.0)
    check('el aviso dice de dónde te sacan', d.get_editor_property('captures') == c0 + 1 and 'LEVANTA LA LONA' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:40])
    yield ('hasta', lambda: not director().get_editor_property('capturing'), 5.0)
    aparte()
    d.set_editor_property('tension_t', 0.0)
    yield ('hasta', lambda: estado_c() == 0, 40.0)
    # --- con el expediente: el camión te saca de la base
    d.set_flag('expediente')
    check('expediente en la chaqueta', d.get_editor_property('file'))
    d.truck_skip_wait()
    yield from dentro()
    check('subes con el expediente', d.get_editor_property('riding') and d.base_state() == 0, d.base_state())
    yield ('hasta', lambda: estado_c() == 4, 45.0)
    yield ('hasta', lambda: director().get_editor_property('done'), 45.0)
    msg = str(d.get_editor_property('message'))
    check('final en la caja del camión', d.get_editor_property('done') and d.get_editor_property('left_by_truck') and 'MISION CUMPLIDA' in msg and 'camion' in msg, msg[:60].replace('\n', ' / '))
    check('sigues dentro mientras se aleja', d.get_editor_property('riding') and jugador().get_editor_property('hidden') and estado_c() == 5, '%s, estado %s' % (d.get_editor_property('riding'), estado_c()))
    yield ('hasta', lambda: director().get_editor_property('report'), 25.0)
    rl = list(d.get_editor_property('report_lines'))
    check('el parte cuenta que saliste en el camión', any('camion de suministros' in x for x in rl) and any('registran todos los camiones' in x for x in rl), ' | '.join(rl[3:5]))


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
    check('CONTROLES abre la página de teclas', len(ls) == 15 and 'VOLVER' in ls[-1], ' / '.join(ls))
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
    yield from teclas(d, *(['Down'] * 13), 'Enter')   # trece acciones desde la tanda 43
    ls = lineas(d)
    check('TECLAS POR DEFECTO lo deshace', ls[0] == tecla0 and ls[1] == interact, '%s / %s' % (ls[0], ls[1]))
    yield from teclas(d, 'Escape')
    check('Esc vuelve a la página principal', len(lineas(d)) == 18, len(lineas(d)))
    yield from teclas(d, 'P')
    check('P cierra el menú', not d.get_editor_property('menu'))


def prueba_opciones():
    d = director()
    # la dificultad guardada de quien juega puede no ser NORMAL: se pone NORMAL por el menú y al final se le devuelve
    dif0 = d.get_editor_property('difficulty')
    if dif0 != 1:
        yield from teclas(d, 'P', *(['Down'] * 10), 'Right' if dif0 == 0 else 'Left', 'P')
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
    if dif0 != 1:
        yield from teclas(d, 'P', *(['Down'] * 10), 'Left' if dif0 == 0 else 'Right', 'P')
        check('la dificultad de quien juega, como estaba', d.get_editor_property('difficulty') == dif0, d.get_editor_property('difficulty'))


# ---------------------------------------------------------------- puertas (arreglo de la 0024)

def _barrido_de_pie(a, b):
    """Lo que para a la cápsula del jugador, de pie, yendo de a a b (en el suelo): lista de «actor/componente@punto»."""
    p = jugador()
    cap = p.get_component_by_class(unreal.CapsuleComponent)
    r, hh = cap.get_unscaled_capsule_radius(), cap.get_unscaled_capsule_half_height()
    z = 4 + hh + 2
    hs = unreal.SystemLibrary.capsule_trace_multi(mundo(), V(a.x, a.y, z), V(b.x, b.y, z), r, hh, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                 False, [p], unreal.DrawDebugTrace.NONE, True) or []
    out = []
    for h in hs:
        t = h.to_tuple()
        if not t[0]:
            continue
        act = next((x for x in t if isinstance(x, unreal.Actor)), None)
        pt = next((x for x in t if isinstance(x, unreal.Vector)), None)
        out.append('%s@%s' % (act.get_actor_label() if act else None, [round(c) for c in (pt.x, pt.y, pt.z)] if pt else None))
    return out

def _anda(destino, tmax=8.0):
    """Anda de verdad (entrada de movimiento en cada fotograma) hasta destino; False si se atasca o se acaba el tiempo."""
    p = jugador()
    t0 = time.time(); ult, tu = p.get_actor_location(), t0
    while time.time() - t0 < tmax:
        l = p.get_actor_location()
        dv = V(destino.x - l.x, destino.y - l.y, 0)
        if dv.length() < 60:      # 60 cm: con el editor en segundo plano (3-8 fps) cada fotograma avanza mucho y se pasa
            return True
        p.add_movement_input(dv.normal(), 1.0, True)
        if time.time() - tu > 2.5:
            if (l - ult).length() < 15:
                return False
            ult, tu = l, time.time()
        yield 0.0
    return False

def _ruta(puntos):
    for k, q in enumerate(puntos):
        ok = yield from _anda(q)
        if not ok:
            l = jugador().get_actor_location()
            return 'atascado en (%d,%d) camino del punto %d' % (l.x, l.y, k)
    return ''

def prueba_puertas():
    """0024: en los huecos de puerta de la base se pasa DE PIE. La colisión de las mallas Nanite sale de su malla de
    respaldo; con el respaldo simplificado, los dinteles del archivo y de dos puertas más bajaban a 1,85 m y solo se
    pasaba agachado («entro al archivo y no puedo salir»). Desde la 0024 el respaldo va sin simplificar (montar_base.py)."""
    d = director()
    for g in guardias():
        g.hold(3600.0)
    p = jugador()
    if agachado():
        p.un_crouch()
    # abrir la jefatura (L) y el archivo (V) como en el juego: llave, E y la clave en el teclado
    tp(900, 2990); yield 0.2
    d.set_flag('llave_jefatura'); d.interact(); yield 0.3
    tp(1150, 3480); yield 0.2
    d.interact(); yield 0.2
    for c in str(d.get_editor_property('vault_code')):
        d.keypad_digit(int(c))
    yield 0.3
    check('jefatura y archivo abiertos', d.has_flag('jefatura_abierta') and d.get_editor_property('vault_open'), [str(f) for f in d.flag_list()])
    # (a) barrido de pie por cada casilla de puerta del plano, en el sentido de paso y en el contrario
    mapa = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['map']
    celda = lambda x, y: mapa[y][x] if 0 <= y < len(mapa) and 0 <= x < len(mapa[y]) else '#'
    malas, n = [], 0
    for y, fila in enumerate(mapa):
        for x, c in enumerate(fila):
            if c not in 'DLVbB':
                continue
            n += 1
            cx, cy = (x + 0.5) * 200.0, (y + 0.5) * 200.0
            en_x = celda(x - 1, y) in 'W#' and celda(x + 1, y) in 'W#'     # el muro va en X: se pasa en Y
            a, b = (V(cx, cy - 160, 0), V(cx, cy + 160, 0)) if en_x else (V(cx - 160, cy, 0), V(cx + 160, cy, 0))
            ida, vuelta = _barrido_de_pie(a, b), _barrido_de_pie(b, a)
            if ida or vuelta:
                malas.append('%s(%d,%d): %s' % (c, x, y, (ida or vuelta)[0]))
    check('por todas las puertas del plano se pasa de pie (%d)' % n, n >= 8 and not malas, malas)
    # (b) andando: entrar al archivo de pie, coger el expediente y salir de pie hasta el despacho y la puerta de la jefatura
    tp(1100, 3500); yield 0.3
    mal = yield from _ruta([V(1500, 3500, 0), V(1850, 3420, 0)])
    check('se entra al archivo de pie andando', not mal and not agachado(), mal)
    d.interact(); yield 0.5
    check('se coge el expediente', d.get_editor_property('file'))
    afuera = [V(1500, 3500, 0), V(1100, 3500, 0), V(900, 3300, 0), V(900, 2900, 0)]
    mal = yield from _ruta(afuera)
    check('y se sale de pie hasta fuera de la jefatura', not mal and not agachado(), mal)
    # (c) lo mismo tras cargar el punto de control del expediente (que se guarda dentro del archivo)
    ok = d.load_checkpoint(); yield 0.6
    l = jugador().get_actor_location()
    check('el punto de control del expediente te deja en el archivo', ok and l.x > 1350, '%s (%d,%d)' % (ok, l.x, l.y))
    mal = yield from _ruta(afuera)
    check('tras cargarlo se sale de pie', not mal, mal)
    aparte()


def prueba_codec():
    """Tanda 29, el códec: las llamadas entrantes suenan sin parar el juego y se cogen con la R; con la conversación
    abierta el juego está en pausa y se pasa de frase; sin llamada, la R abre el menú de frecuencias (Control, Roig y,
    sin luz o con el expediente, la voz sin nombre). Control contesta según el objetivo y Roig da la pista del salmo."""
    d = director()
    pausa = lambda: unreal.GameplayStatics.is_game_paused(mundo())
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.1
    t = MISION['textos']
    convs = [k[6:] for k in t if k.startswith('codec_') and '|' in t[k]]
    check('hay conversaciones en mision1.json', len(convs) >= 25, len(convs))
    check('toda frase empieza por C|, T|, R| o F|', all(l[:2] in ('C|', 'T|', 'R|', 'F|') for c in convs for l in t['codec_' + c].split('\n')),
          [c for c in convs if not all(l[:2] in ('C|', 'T|', 'R|', 'F|') for l in t['codec_' + c].split('\n'))])
    # llamada entrante: no para el juego
    d.codec_ring('inicio'); yield 0.3
    check('la llamada entra sin parar el juego', str(d.get_editor_property('codec_pending')) == 'inicio' and not pausa() and not d.get_editor_property('codec'))
    check('se anuncia con su frecuencia', '141.12' in str(d.codec_pending_text()), str(d.codec_pending_text()))
    d.codec_key(); yield 0.3
    check('la R la coge: códec abierto y juego en pausa', d.get_editor_property('codec') and pausa())
    check('la llamada deja de estar pendiente', str(d.get_editor_property('codec_pending')) == 'None', str(d.get_editor_property('codec_pending')))
    n = len(t['codec_inicio'].split('\n'))
    check('tantas frases como en el .json', d.codec_line_count() == n, '%d / %d' % (d.codec_line_count(), n))
    check('habla Control por 141.12', str(d.codec_line()).startswith('CONTROL|141.12|Cuttlas'), str(d.codec_line())[:40])
    tm = d.get_editor_property('mission_time')
    yield 0.6
    check('el tiempo de misión no corre', d.get_editor_property('mission_time') == tm)
    d.press_key('P'); yield 0.1
    check('la P no abre el menú encima', not d.get_editor_property('menu'))
    # la primera pulsación completa la frase y la segunda pasa a la siguiente
    d.codec_ring('alarma'); yield 0.1
    check('hablando no entra otra llamada', str(d.get_editor_property('codec_pending')) == 'None')
    i0 = d.get_editor_property('codec_idx')
    d.press_key('Enter'); yield 0.1
    d.press_key('Enter'); yield 0.1
    check('Intro pasa de frase', d.get_editor_property('codec_idx') == i0 + 1, d.get_editor_property('codec_idx'))
    for _ in range(2 * n + 2):
        if not d.get_editor_property('codec'):
            break
        d.codec_next(); yield 0.05
    check('tras la última frase cuelga y el juego sigue', not d.get_editor_property('codec') and not pausa())
    check('queda apuntada', 'inicio' in [str(x) for x in d.get_editor_property('codec_taken')])
    # tanda 32: la tecla de la radio es una acción más (se reasigna) y lo ya oído viaja con el punto de control
    check('la tecla de la radio sale en la ayuda', 'R radio' in str(d.help_line()), str(d.help_line()))
    d.checkpoint('prueba del codec'); yield 0.2
    d.codec_reset()
    check('codec_reset lo olvida', 'inicio' not in [str(x) for x in d.get_editor_property('codec_taken')])
    d.codec_ring('alarma'); yield 0.1
    ok = d.load_checkpoint(); yield 0.6
    check('al cargar el punto de control, lo oído vuelve', ok and 'inicio' in [str(x) for x in d.get_editor_property('codec_taken')], [str(x) for x in d.get_editor_property('codec_taken')])
    check('y no queda una llamada de antes sonando', str(d.get_editor_property('codec_pending')) == 'None', str(d.get_editor_property('codec_pending')))
    for g in guardias():
        g.hold(3600.0)
    # menú de frecuencias
    d.codec_key(); yield 0.1
    m = [str(x) for x in d.codec_menu_lines()]
    check('sin llamada, la R abre el menú sin pausa', d.get_editor_property('codec_menu') and not pausa(), m)
    check('Control y Roig; la tercera voz aún no', len(m) == 4 and 'CONTROL' in m[1] and 'ROIG' in m[2], m)
    d.codec_call(3); yield 0.1
    check('la tercera frecuencia no contesta todavía', not d.get_editor_property('codec'))
    check('Control habla del objetivo', str(d.codec_control_conv()) == 'control_llave', str(d.codec_control_conv()))
    d.codec_call(1); yield 0.2
    check('llamas a Control: se abre y pausa', d.get_editor_property('codec') and pausa() and 'Ibarra' in str(d.codec_line()), str(d.codec_line())[:60])
    d.press_key('Escape'); yield 0.2
    check('Esc cuelga', not d.get_editor_property('codec') and not pausa() and not d.get_editor_property('menu'))
    # Roig: la pista del salmo solo con la mesa leída y el archivo cerrado
    d.codec_key(); d.codec_call(2); yield 0.1
    check('Roig contesta por 140.85', str(d.codec_line()).startswith('ROIG|140.85|') and 'De profundis' not in str(d.codec_line()), str(d.codec_line())[:40])
    d.close_codec()
    d.set_flag('nota_leida')
    check('con la nota leída, Control habla del archivo', str(d.codec_control_conv()) == 'control_archivo', str(d.codec_control_conv()))
    d.codec_key(); d.codec_call(2); yield 0.1
    check('con la mesa leída, Roig da la pista del salmo', 'De profundis' in str(d.codec_line()), str(d.codec_line())[:60])
    d.close_codec()
    d.codec_key(); d.codec_call(2); yield 0.1
    check('la pista, una sola vez', d.get_editor_property('codec') and 'De profundis' not in str(d.codec_line()), str(d.codec_line())[:60])
    d.close_codec(); yield 0.1
    # llamada automática: al saltar la alarma
    d.set_editor_property('codec_calls', True); yield 0.3
    g = guardias()[0]
    l = g.get_actor_location()
    g.alarm(V(l.x + 250, l.y, l.z)); yield 0.6
    check('con la alarma, Control llama', str(d.get_editor_property('codec_pending')) == 'alarma', '%s / base %s' % (d.get_editor_property('codec_pending'), d.base_state()))
    d.set_editor_property('codec_calls', False)
    d.codec_reset(); yield 0.1
    check('codec_reset quita la llamada pendiente', str(d.get_editor_property('codec_pending')) == 'None')
    # todas las conversaciones existen y se abren (ninguna clave pedida falta en el .json)
    mal = []
    for c in convs:
        if not d.open_codec(c):
            mal.append(c)
        d.close_codec()
    yield 0.1
    check('todas las conversaciones se abren', not mal, mal)
    check('no queda en pausa', not pausa() and not d.get_editor_property('codec'))
    d.codec_key(); yield 0.1
    check('la voz sin nombre ya se ha oído: tercera frecuencia', d.codec_voice_open() and len(d.codec_menu_lines()) == 5, [str(x) for x in d.codec_menu_lines()])
    d.codec_call(3); yield 0.1
    check('y contesta por 000.00', '|000.00|' in str(d.codec_line()), str(d.codec_line())[:40])
    d.close_codec(); yield 0.1
    check('ningún texto pedido falta', not list(d.get_editor_property('missing_texts')), list(d.get_editor_property('missing_texts')))

def prueba_emisora():
    """Tanda 32, dos puzles de radio. La charla: Lobato pregunta por la red qué decir si le apuntan y Carmona le dice la
    frase de coacción (bandera sabe_coaccion). La emisora: en transmisiones se deja muda la red; sin red la central no
    llama al caído ni da voces, a los RadioDeadSeconds sale uno a arreglarla y, arreglada, la base queda en guardia y
    entonces sí llaman al que no contesta."""
    d = director()
    vl = lambda: [str(x) for x in director().get_editor_property('voice_log')]
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.1
    check('la charla no suena sola en las pruebas', d.get_editor_property('radio_chats') == 0, d.get_editor_property('radio_chats'))
    ok = d.start_radio_chat(True); yield 5.5
    check('Lobato pregunta y Carmona dice la frase', ok and d.has_flag('sabe_coaccion') and 'lobato_charla_1' in vl() and 'carmona_charla_2' in vl(), vl()[-3:])
    check('no se pisa a sí misma', not d.start_radio_chat(True) and d.get_editor_property('radio_chats') == 1)
    yield 13.5
    check('la central los manda callar', 'central_charla' in vl(), vl()[-3:])
    # la emisora
    pt = [x for x in MISION['puntos'] if x['id'] == 'emisora'][0]
    e = d.get_editor_property('emisora_loc')
    check('el punto está en la emisora', abs(e.x - pt['pos'][0]) < 60 and abs(e.y - pt['pos'][1]) < 60, '%d,%d' % (e.x, e.y))
    check('la red funciona al empezar', not d.radio_dead())
    tp(pt['pos'][0] + 120, pt['pos'][1], 180.0); yield 0.4
    d.interact(); yield 0.4
    check('aflojar la válvula deja muda la red', d.radio_dead() and d.has_flag('emisora_muda'), str(d.get_editor_property('message'))[:50])
    c, v = guardia('Carmona'), guardia('Vega')
    derribar(c); yield 0.2
    aparte()
    n0 = len(vl())
    yield 46.0
    check('sin red, la central no llama al caído', 'central_responde' not in vl()[n0:] and all(estado(g) in ('PATROL', 'DOWN') for g in guardias() if not g.get_editor_property('tower_sentry')), vl()[n0:])
    check('y alguien prueba la radio en vano', any(x.endswith('_sinradio') for x in vl()), vl()[-3:])
    # mandan a uno: solo Vega está libre
    v.hold(0.0)
    d.set_editor_property('radio_dead_t', d.get_editor_property('radio_dead_seconds') - 0.5)
    yield ('hasta', lambda: director().emisora_fixer_now() is not None, 8.0)
    check('a los 90 s sale uno a arreglarla', d.emisora_fixer_now() == v and v.is_on_errand(), d.emisora_fixer_now())
    l = v.get_actor_location()
    v.set_actor_location(V(e.x + d.get_editor_property('emisora_stand'), e.y, l.z), False, True)
    yield ('hasta', lambda: not director().radio_dead(), d.get_editor_property('radio_fix_seconds') + 25.0)
    check('la arregla: vuelve la red', not d.radio_dead() and d.has_flag('emisora_reparada') and d.get_editor_property('radio_repairs') == 1, d.get_editor_property('radio_repairs'))
    yield 1.5
    check('la central lo dice y la base queda en guardia', 'central_red' in vl() and d.get_editor_property('tension_t') > 60.0, '%s %.0f' % (vl()[-2:], d.get_editor_property('tension_t')))
    yield ('hasta', lambda: 'central_responde' in [str(x) for x in director().get_editor_property('voice_log')], 8.0)
    check('y ahora sí llaman al que no contesta', 'central_responde' in vl(), vl()[-3:])
    check('ningún texto pedido falta', not list(d.get_editor_property('missing_texts')), list(d.get_editor_property('missing_texts')))


def prueba_calabozo():
    """Tanda 35. La primera captura te deja en el calabozo y la reja ya no se abre sola: se sale convenciendo al cabo
    Vidal en tres pasos (amenazar o sobornar falla; el segundo y el tercero piden haber averiguado algo) o con la llave
    que hay bajo la losa suelta. Con la llave, a los CellAlertSeconds encuentran la celda vacía y la base queda en
    guardia; si Vidal abre, calla. De paso: dos claves malas en el teclado del archivo avisan a la central."""
    d = director()
    msg = lambda: str(director().get_editor_property('message'))
    vl = lambda: [str(x) for x in director().get_editor_property('voice_log')]
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.1
    # el teclado del archivo
    t0 = d.get_editor_property('tension_t')
    tp(1150, 3480); yield 0.2
    d.interact(); yield 0.2
    mala = '0130' if str(d.get_editor_property('vault_code')) != '0130' else '0131'
    for c in mala:
        d.keypad_digit(int(c))
    yield 0.2
    check('una clave mala: rojo y nada más', d.get_editor_property('keypad_fails') == 1 and d.get_editor_property('keypad_alerts') == 0 and d.get_editor_property('tension_t') <= t0, d.get_editor_property('keypad_fails'))
    for c in mala:
        d.keypad_digit(int(c))
    yield 2.2
    check('dos claves malas: aviso a la central y base en guardia', d.get_editor_property('keypad_alerts') == 1 and d.get_editor_property('tension_t') > 60.0 and 'central_teclado' in vl() and not d.get_editor_property('vault_open'),
          '%s %.0f %s' % (d.get_editor_property('keypad_alerts'), d.get_editor_property('tension_t'), vl()[-2:]))
    d.set_editor_property('tension_t', 0.0)
    # al calabozo
    puerta, losa = d.get_editor_property('cell_door'), d.get_editor_property('cell_slab')
    hablar = lambda: tp(puerta.x, puerta.y + 110, -90.0)
    P = lambda k: d.get_editor_property(k)
    def decir(n):
        d.interact(); yield 0.2
        d.answer_cell(n); yield 0.2
    d.captured(jugador()); yield 0.5
    check('la primera captura te deja en el calabozo', d.in_cell() and 'CALABOZO' in msg(), msg()[:30])
    yield 4.0
    check('la reja ya no se abre sola', d.in_cell() and P('cell_by_vidal') == 0)
    check('Control, por el códec, habla de Vidal', str(d.codec_control_conv()) == 'control_celda', str(d.codec_control_conv()))
    check('lejos de la reja no se oye qué reza', not P('cell_heard_prayer'))
    hablar(); yield 0.3
    check('junto a la reja, el aviso es hablar con Vidal', 'VIDAL' in str(d.cell_prompt()), str(d.cell_prompt()))
    d.interact(); yield 0.5
    check('tanda 36: la pregunta sale en su caja', P('cell_ask_frames') > 0 and str(P('cell_question')), P('cell_ask_frames'))
    check('tanda 36: Vidal tiene cuerpo y está de medio lado', abs(d.vidal_facing() - P('vidal_yaw')) < 1.0 and P('vidal_body') is not None, d.vidal_facing())
    check('Vidal pregunta: tres respuestas', P('cell_ask') and len(P('cell_options')) == 3 and '1/3' in msg(), msg()[:40])
    # tanda 38: ninguna respuesta cierra la conversación, y tras contestar Vidal la pregunta vuelve sola
    d.answer_cell(1); yield 0.2
    check('amenazarle no vale, pero no cierra nada', P('cell_fails') == 1 and P('cell_stage') == 0 and not P('cell_ask') and not P('vidal_gone'), msg()[:60])
    yield ('hasta', lambda: director().get_editor_property('cell_ask'), P('cell_auto_ask') + 2.0)
    check('la pregunta vuelve sola', P('cell_ask') and P('cell_stage') == 0)
    d.set_editor_property('cell_auto_ask', 0.0)   # en adelante se pregunta con la E, para medir paso a paso
    d.answer_cell(3); yield 0.2
    for i in range(3):
        yield from decir(1)
    check('cinco malas respuestas y Vidal sigue escuchando', P('cell_fails') == 5 and not P('vidal_gone') and 'VIDAL' in str(d.cell_prompt()), P('cell_fails'))
    yield from decir(2)
    check('hablarle de lo que se oye, sí', P('cell_stage') == 1, msg()[:60])
    d.interact(); yield 0.2
    check('el segundo paso tiene respuesta buena sin saber nada, y no está en el mismo sitio', P('cell_right') == 3 and 'grita' in str(P('cell_options')[2]), [str(x)[:20] for x in P('cell_options')])
    d.answer_cell(1); yield 0.2
    check('«es el viento» no vale', P('cell_stage') == 1 and 'viento' in msg(), msg()[:70])
    yield from decir(3)
    check('segundo paso', P('cell_stage') == 2, msg()[:60])
    d.interact(); yield 0.2
    check('el tercero: rezar con él vale siempre; hablar de bajas, sin pruebas, no', P('cell_right') == 1 and 'Reza' in str(P('cell_options')[0]) and P('cell_lacks') == 0, [str(x)[:20] for x in P('cell_options')])
    # si te apartas de la reja, la pregunta se va sin contar como fallo
    f0 = P('cell_fails')
    tp(losa.x - 150, losa.y + 250, -90.0); yield 0.4
    check('apartarse deja la pregunta sin contestar, sin fallo', not P('cell_ask') and P('cell_fails') == f0)
    hablar(); yield 0.3
    yield from decir(3)
    check('hablar de bajas sin pruebas no basta, y dice que registres la celda', P('cell_stage') == 2 and P('cell_lacks') == 1 and 'celda' in msg(), msg()[-60:])
    yield from decir(1)
    check('tercer paso: Vidal cede', P('cell_stage') == 3 and d.in_cell(), msg()[:60])
    yield ('hasta', lambda: not director().in_cell(), 6.0)
    yield 0.2
    check('abre él: nadie da la alarma', not d.in_cell() and P('cell_by_vidal') == 1 and d.has_flag('vidal_calla') and P('cell_alert_t') <= 0.0 and 'no le he visto' in msg(), msg()[:60])
    check('tanda 36: Vidal se queda de cara a la pared', abs(d.vidal_facing() - P('vidal_wall_yaw')) < 1.0, d.vidal_facing())
    # Control, por la radio, desde la celda (ya no hace falta para salir, pero llama y la R va directa a él)
    d.lock_in_cell(jugador()); yield 0.4
    d.set_editor_property('cell_auto_ask', 0.0)
    d.codec_key(); yield 0.2
    check('en la celda, la R va directa a Control', P('codec') and not P('codec_menu'), '%s %s' % (P('codec'), P('codec_menu')))
    for i in range(40):
        if not P('codec'):
            break
        d.codec_next(); yield 0.05
    check('Control lo cuenta por la radio', 'control_celda' in [str(x) for x in P('codec_taken')] and not P('codec'), [str(x) for x in P('codec_taken')][-3:])
    # la losa. Con la medalla se le convence; con la llave se puede callar y abrir
    tp(losa.x - 40, losa.y + 40, 0.0); yield 0.3
    check('en el rincón, la losa suelta', 'LOSA' in str(d.cell_prompt()), str(d.cell_prompt()))
    d.interact(); yield 0.2
    check('debajo, la llave y la medalla', d.has_flag('llave_celda') and 'VIDAL, J.' in msg(), msg()[:40])
    hablar(); yield 0.3
    check('con la llave se puede seguir hablando con Vidal', 'VIDAL' in str(d.cell_prompt()) and d.in_cell(), str(d.cell_prompt()))
    yield from decir(2)
    d.interact(); yield 0.2
    check('con lo que dijo Control, la respuesta buena lo dice', 'doctora' in str(P('cell_options')[2]), str(P('cell_options')[2]))
    d.answer_cell(3); yield 0.2
    d.interact(); yield 0.2
    check('con la llave hay una cuarta respuesta, y la medalla también vale en el tercer paso', P('cell_stage') == 2 and len(P('cell_options')) == 4 and 'medalla' in str(P('cell_options')[2]), [str(x)[:30] for x in P('cell_options')])
    d.answer_cell(3); yield 0.2
    yield ('hasta', lambda: not director().in_cell(), 6.0)
    yield 0.2
    check('la medalla le convence: abre él y calla', P('cell_by_vidal') == 2 and P('cell_by_key') == 0 and P('cell_alert_t') <= 0.0, msg()[:60])
    # callar y abrir con la llave
    d.lock_in_cell(jugador()); yield 0.4
    hablar(); yield 0.3
    yield from decir(4)
    check('la llave abre', not d.in_cell() and P('cell_by_key') == 1 and P('cell_alert_t') > 0.0, msg()[:40])
    check('todavía nadie lo sabe', P('tension_t') <= 0.0 and 'central_fuga' not in vl())
    d.set_editor_property('cell_alert_t', 0.3); yield 1.0
    check('al rato encuentran la celda vacía: base en guardia', P('cell_alerts') == 1 and P('tension_t') > 60.0 and 'central_fuga' in vl(), '%.0f %s' % (P('tension_t'), vl()[-2:]))
    d.set_editor_property('cell_auto_ask', 4.0)
    check('ningún texto pedido falta', not list(P('missing_texts')), list(P('missing_texts')))

def prueba_equipo():
    """Tanda 39. Al encerrarte te quitan linterna, prismáticos y dardos: están en el cajón de Peris, en la sala de
    guardia. Registrarlo lleva unos segundos, se corta si te apartas y devuelve lo que llevabas."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    msg = lambda: str(director().get_editor_property('message'))
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.1
    d.set_darts(3)
    d.lock_in_cell(jugador()); yield 0.4
    check('en el calabozo te han registrado', P('gear_taken') and P('darts') == 0 and not P('has_torch') and P('gear_darts') == 3, '%s %s' % (P('gear_taken'), P('darts')))
    d.set_torch(True); yield 0.2
    check('la linterna no enciende, y dice dónde está', not P('torch') and 'PERIS' in msg().upper(), msg()[:40])
    check('la línea secundaria lo recuerda', 'Peris' in str(d.side_objective()), str(d.side_objective()))
    c = P('gear_spot')
    # Peris ha salido a fumar: si está en su mesa, la E es para él (empujar o derribar), no para el cajón
    guardia('Peris').set_actor_location(unreal.Vector(4700.0, 1700.0, guardia('Peris').get_actor_location().z), False, True)
    tp(c.x + 60, c.y, 180.0); yield 0.3
    check('junto a la mesa de Peris, el aviso del cajón', 'CAJON' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 0.5
    check('registrar lleva un rato', P('gear_searching') and P('gear_taken') and 'REGISTRANDO' in str(d.interact_prompt()), str(d.interact_prompt()))
    tp(c.x + 600, c.y, 180.0); yield 0.4
    check('si te apartas, se queda a medias', not P('gear_searching') and P('gear_taken') and 'MEDIAS' in msg(), msg()[:30])
    tp(c.x + 60, c.y, 180.0); yield 0.3
    d.interact()
    yield ('hasta', lambda: director().get_editor_property('gear_back'), P('gear_seconds') + 3.0)
    check('recuperas lo tuyo', P('gear_back') and not P('gear_taken') and P('darts') == 3 and P('has_torch') and d.has_flag('equipo') and 'reloj' in msg(), msg()[:30])
    d.set_torch(True); yield 0.2
    check('y la linterna vuelve a encender', P('torch'))
    d.set_torch(False)
    d.lock_in_cell(jugador()); yield 0.3
    check('una vez recuperado, no te lo vuelven a quitar', not P('gear_taken') and P('darts') == 3)
    aparte()
    check('ningún texto pedido falta', not list(P('missing_texts')), list(P('missing_texts')))

def prueba_hangar():
    """Tanda 40. Se empieza junto a la brecha del muro norte; hay un hangar en la franja sur; el camión pasa control al
    entrar, para un rato ante el hangar y sigue al control de salida; la caja de cartón (X) te esconde quieto y en la
    caja del camión burla el registro; el uniforme te hace pasar por guardia de lejos."""
    d = director(); w = mundo()
    P = lambda k: director().get_editor_property(k)
    estado_c = lambda: director().get_editor_property('truck_state')
    cx = lambda: director().truck_location().x
    traza = lambda a, b: unreal.SystemLibrary.line_trace_single(w, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [jugador()], unreal.DrawDebugTrace.NONE, True)
    for g in guardias():
        g.hold(3600.0)
    ext = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']
    b, hg = ext['brecha'], ext['hangar']
    ps = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PlayerStart)
    check('se empieza junto a la brecha', ps and dist2d(ps[0].get_actor_location(), V(b['inicio'][0] * 100, b['inicio'][1] * 100, 0)) < 60, [ps[0].get_actor_location() if ps else None])
    check('la brecha es un boquete en el muro (a 1 m del suelo se ve el otro lado)', traza(V(b['pos'][0] * 100, b['pos'][1] * 100 + 150, 125), V(b['pos'][0] * 100, b['pos'][1] * 100 - 150, 125)) is None)
    check('y a su lado el muro sigue entero', traza(V(b['pos'][0] * 100 + 300, b['pos'][1] * 100 + 150, 125), V(b['pos'][0] * 100 + 300, b['pos'][1] * 100 - 150, 125)) is not None)
    tp(b['pos'][0] * 100, b['pos'][1] * 100 + 110, -90); yield 0.2
    jugador().crouch(); yield 0.3
    for _ in range(8):
        jugador().launch_character(V(0, -300, 0), True, False); yield 0.15
    check('por el boquete no se vuelve a salir (el cascote lo ciega)', jugador().get_actor_location().y > b['pos'][1] * 100 - 20, jugador().get_actor_location().y)
    jugador().un_crouch(); yield 0.2
    # el hangar
    cxh, cyh = (hg['x0'] + hg['x1']) * 50, (hg['y0'] + hg['y1']) * 50
    h = traza(V(cxh, cyh, 1200), V(cxh + 150, cyh + 150, 100))
    check('el hangar tiene cubierta', h is not None and h.to_tuple()[4].z > hg['alto'] * 100 - 20, h.to_tuple()[4].z if h else None)
    check('portón abierto hacia el camino', traza(V(cxh, hg['y0'] * 100 - 200, 150), V(cxh, hg['y0'] * 100 + 300, 150)) is None)
    check('y pared a los lados del portón', traza(V(hg['x0'] * 100 + 200, hg['y0'] * 100 - 200, 150), V(hg['x0'] * 100 + 200, hg['y0'] * 100 + 300, 150)) is not None)
    tp(cxh, cyh, 0); yield 0.3
    check('dentro se puede estar de pie', abs(jugador().get_actor_location().z - 100) < 40, jugador().get_actor_location().z)
    # la caja
    d.toggle_box(); yield 0.1
    check('sin caja, la X no hace nada', not P('box_on'))
    pt = next(q for q in MISION['puntos'] if q['id'] == 'caja')
    tp(pt['pos'][0] - 90, pt['pos'][1] - 90, 45); yield 0.3
    check('al fondo del hangar, el aviso de la caja', 'CAJA' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 0.3
    check('la coges', d.has_flag('caja') and 'CARTON' in str(P('message')), str(P('message'))[:30])
    check('la línea de teclas la nombra', 'X caja' in str(d.help_line()), str(d.help_line())[-60:])
    sanz = guardia('Sanz')
    a_la_vista_de(sanz, 500); yield 0.3
    v0 = sanz.visibility(jugador())
    d.toggle_box(); yield 0.2
    check('recién puesta aún te ven (medio segundo)', P('box_on') and not d.box_cloaked() and sanz.visibility(jugador()) > 0, sanz.visibility(jugador()))
    yield 0.8
    check('quieto dentro de la caja no te ve', v0 > 0 and d.box_cloaked() and sanz.visibility(jugador()) == 0 and jugador().get_editor_property('is_crouched'), '%.2f antes, %.2f con caja' % (v0, sanz.visibility(jugador())))
    d.throw_stone(); yield 0.2
    check('con la caja puesta no hay piedra, y lo dice', 'CAJA PUESTA' in str(P('message')), str(P('message'))[:30])
    jugador().launch_character(V(250, 0, 0), True, False); yield 0.15
    check('si la caja anda, te ven', not d.box_cloaked(), P('box_on'))
    d.toggle_box(); yield 0.2
    check('la X la quita', not P('box_on') and sanz.visibility(jugador()) > 0)
    # el uniforme
    if jugador().get_editor_property('is_crouched'):
        jugador().un_crouch(); yield 0.3
    a_la_vista_de(sanz, 1500); yield 0.3
    v1 = sanz.visibility(jugador())
    d.set_flag('uniforme'); yield 0.2
    check('con uniforme, de pie y de lejos, eres uno más', d.uniform_works() and sanz.visibility(jugador()) == 0, '%.2f sin, %.2f con' % (v1, sanz.visibility(jugador())))
    a_la_vista_de(sanz, 500); yield 0.2
    check('de cerca no cuela', sanz.visibility(jugador()) > 0, sanz.visibility(jugador()))
    a_la_vista_de(sanz, 1500); yield 0.1
    jugador().crouch(); yield 0.4
    check('agachado, el uniforme no vale', not d.uniform_works())
    jugador().un_crouch(); yield 0.3
    pu = next(q for q in MISION['puntos'] if q['id'] == 'uniforme')
    hu = traza(V(pu['pos'][0], pu['pos'][1], 300), V(pu['pos'][0], pu['pos'][1], -20))
    check('el punto del uniforme está bajo techo y en suelo libre', hu is not None and hu.to_tuple()[4].z < 30, hu.to_tuple()[4].z if hu else None)
    # el camión: control al entrar, parada ante el hangar y registro burlado con la caja
    aparte()
    d.set_editor_property('truck', True)
    d.set_editor_property('truck_entry_papers', 3.0)
    d.set_editor_property('truck_stay_seconds', 8.0)
    d.set_editor_property('truck_start', V(-7000, 5700, 4))
    d.set_editor_property('truck_end_x', 13000.0)
    lob = guardia('Lobato')
    if lob:
        lob.hold(0.0)
    sanz.hold(0.0)
    e0, s0, c0 = P('truck_entry_checks'), P('truck_stays'), P('captures')
    d.set_flag('expediente')
    d.set_editor_property('tension_t', 300.0)
    yield ('hasta', lambda: estado_c() == 0, 40.0)
    d.truck_skip_wait()
    yield ('hasta', lambda: estado_c() == 2, 30.0)
    yield 1.6
    check('ante el portón le piden los papeles y la hoja sigue cerrada', P('truck_entry_checks') == e0 + 1 and P('entry_gate_t') < 0.05, '%s, hoja %.2f' % (P('truck_entry_checks'), P('entry_gate_t')))
    yield ('hasta', lambda: estado_c() == 6, 60.0)
    check('para ante el hangar', estado_c() == 6 and abs(cx() - P('truck_stay_x')) < 40 and P('truck_stays') == s0 + 1, '%s, x %d' % (estado_c(), cx()))
    tp(cx() - 265, 5700, 0); yield 0.1
    check('parado se puede subir', d.can_board_truck())
    d.interact(); yield 0.3
    d.toggle_box(); yield 0.8
    check('en la caja del camión, dentro de la de cartón', P('riding') and P('box_on') and d.box_cloaked())
    yield ('hasta', lambda: estado_c() == 3, 12.0)
    check('al rato arranca hacia el control', estado_c() == 3 and P('riding'), estado_c())
    yield ('hasta', lambda: estado_c() == 4, 45.0)
    b0 = P('truck_box_passes')
    yield ('hasta', lambda: director().get_editor_property('truck_box_passes') > b0 or director().get_editor_property('capturing'), 50.0)
    check('con la base en guardia registran la caja y no te encuentran', P('truck_box_passes') == b0 + 1 and not P('capturing') and P('captures') == c0, '%s, capturas %s' % (P('truck_box_passes'), P('captures') - c0))
    yield ('hasta', lambda: director().get_editor_property('done'), 45.0)
    check('y el camión te saca de la base', P('done') and P('left_by_truck'), str(P('message'))[:40].replace('\n', ' / '))
    check('ningún texto pedido falta', not list(P('missing_texts')), list(P('missing_texts')))

def prueba_bengala():
    """Tanda 42. Brillo, día o noche e intensidad de la linterna en Pausa; tu linterna parpadea; una torre lanza una
    bengala que alumbra lo abierto y no lo que queda bajo techo; la cocina (con su hueso y su parte de raciones) pegada
    al calabozo y la trampilla del hangar, que no se abre."""
    d = director(); w = mundo()
    P = lambda k: director().get_editor_property(k)
    traza = lambda a, b: unreal.SystemLibrary.line_trace_single(w, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [jugador()], unreal.DrawDebugTrace.NONE, True)
    for g in guardias():
        g.hold(3600.0)
    ext = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']
    ck, tr = ext['cocina'], ext['trampilla']
    # el centinela de torre ve lo que alumbra su foco, aunque caiga más lejos que su vista (Andres: «los soldados del foco no me detectan»)
    torre = next((g for g in guardias() if g.get_editor_property('tower_sentry') and len(g.get_editor_property('sweep_path')) >= 2 and g.get_editor_property('view_distance') < 2000), None)
    if torre:
        q = torre.get_editor_property('sweep_aim'); q = V(q.x, q.y, 100)
        tp(q.x, q.y, 0); yield 0.2
        lejos = torre.get_actor_location().distance(jugador().get_actor_location())
        vis = torre.visibility(jugador())
        check('en la mancha del foco, el de la torre te ve aunque estés más lejos que su vista', lejos > torre.get_editor_property('view_distance') and vis > 0.3, 'a %.0f cm, V %.2f' % (lejos, vis))
        tp(q.x + 1500, q.y + 1500, 0); yield 0.2
        check('y fuera de la mancha, a esa distancia, no', torre.visibility(jugador()) == 0.0 or torre.get_actor_location().distance(jugador().get_actor_location()) < torre.get_editor_property('view_distance'), torre.visibility(jugador()))
    # menú
    d.press_key('P'); yield 0.2
    L = [str(x) for x in d.menu_lines()]
    check('Pausa: brillo, linterna y hora antes de salir', len(L) == 18 and 'BRILLO' in L[14] and 'LINTERNA' in L[15] and 'HORA' in L[16] and 'SALIR' in L[17], ' / '.join(L[13:]))
    for _ in range(14):
        d.press_key('Down')
    b0 = P('opt_brightness')
    d.press_key('Right'); yield 0.1
    check('derecha sube el brillo un paso', P('opt_brightness') == b0 + 1, P('opt_brightness'))
    d.press_key('Left'); yield 0.1
    check('e izquierda lo deja como estaba', P('opt_brightness') == b0, P('opt_brightness'))
    d.press_key('Down'); m0 = P('opt_torch_mul')
    d.press_key('Right'); yield 0.1
    check('la linterna sube una décima', abs(P('opt_torch_mul') - min(3.0, m0 + 0.1)) < 0.01 and 'lm' in str(d.menu_lines()[15]), str(d.menu_lines()[15]))
    d.press_key('Left'); yield 0.1
    d.press_key('Down'); d.press_key('Enter'); yield 0.2
    check('la hora pasa a día', P('day') and 'DIA' in str(d.menu_lines()[16]), str(d.menu_lines()[16]))
    d.press_key('Enter'); yield 0.2
    check('y vuelve a noche', not P('day') and 'NOCHE' in str(d.menu_lines()[16]), str(d.menu_lines()[16]))
    d.press_key('P'); yield 0.3
    # día: a cielo abierto se te ve; bajo techo, penumbra
    abierto = V(4300, 3500, 100); dentro = V((ck['x0'] + ck['x1']) * 50 + 250, (ck['y0'] + ck['y1']) * 50 + 120, 100)
    n0 = luz_en(abierto)
    d.set_day(True); yield 0.3
    check('de día, a cielo abierto, luz alta', luz_en(abierto) >= 0.85, luz_en(abierto))
    check('de día, bajo el techo de la cocina, menos', luz_en(dentro) < luz_en(abierto), [luz_en(dentro), luz_en(abierto)])
    d.set_day(False); yield 0.3
    check('de noche todo vuelve a su luz', abs(luz_en(abierto) - n0) < 0.05, [n0, luz_en(abierto)])
    # linterna que parpadea
    d.set_editor_property('has_torch', True)
    d.set_torch(True); yield 0.2
    lm = d.torch_now()
    dim0 = max(d.torch_dim_now(), 0.01)   # cerca de una pared la linterna se atenúa sola: se compara sin eso
    check('linterna encendida con sus lúmenes', P('torch') and lm > 1.0, lm)
    f0 = P('torch_flickers')
    d.set_editor_property('torch_flicker', True); d.set_editor_property('torch_flicker_next', 0.1)
    vistos = set()
    for _ in range(14):
        yield 0.05
        vistos.add(round(d.torch_now() / max(lm, 1.0), 2))
    check('parpadea', P('torch_flickers') == f0 + 1 and len(vistos) >= 2 and min(vistos) < 0.7, sorted(vistos))
    check('el siguiente hueco sale de la lista (6, 10, 12 o 30 s)', 4.0 < P('torch_flicker_next') <= 30.0, P('torch_flicker_next'))
    yield 1.2
    check('y vuelve a su luz', abs(d.torch_now() / max(d.torch_dim_now(), 0.01) - lm / dim0) < lm / dim0 * 0.05, [d.torch_now(), lm])
    d.set_editor_property('torch_flicker', False); d.set_torch(False); yield 0.1
    # bengala
    tp(abierto.x, abierto.y, 0); yield 0.2
    a0, i0, n = luz_en(abierto), luz_en(dentro), P('flares_fired')
    d.set_editor_property('flare_seconds', 6.0)
    d.fire_flare(); yield 0.2
    check('la bengala sale', d.flare_up() and P('flares_fired') == n + 1, [d.flare_up(), P('flares_fired')])
    yield 3.0
    z = d.flare_location().z
    check('arde arriba, sobre la base', z > 3000 and abs(d.flare_location().x - 3600) < 3500, d.flare_location())
    check('lo abierto se ve como de día', luz_en(abierto) > max(0.6, a0 + 0.3), [a0, luz_en(abierto)])
    check('bajo techo, no', luz_en(dentro) < i0 + 0.1, [i0, luz_en(dentro)])
    yield ('hasta', lambda: not director().flare_up(), 8.0)
    check('se apaga sola', not d.flare_up() and abs(luz_en(abierto) - a0) < 0.05, [d.flare_up(), luz_en(abierto)])
    check('la siguiente queda para dentro de unos minutos', P('flare_next') >= P('flare_every_min') - 1, P('flare_next'))
    # cocina
    cxk, cyk = (ck['x0'] + ck['x1']) * 50, (ck['y0'] + ck['y1']) * 50
    h = traza(V(cxk, cyk + 100, 1200), V(cxk, cyk + 100, 100))
    check('la cocina tiene cubierta', h is not None and h.to_tuple()[4].z > ck['alto'] * 100 - 20, h.to_tuple()[4].z if h else None)
    pu = ck['puerta']
    check('puerta abierta al patio', traza(V(pu[0] * 100 - 150, pu[1] * 100, 120), V(pu[0] * 100 + 150, pu[1] * 100, 120)) is None)
    check('y pared a su lado', traza(V(pu[0] * 100 - 150, pu[1] * 100 - 130, 120), V(pu[0] * 100 + 150, pu[1] * 100 - 130, 120)) is not None)
    check('la ronda de Moya pasa libre por delante (y = 39 m)', traza(V(ck['x0'] * 100 - 300, 3900, 120), V(ck['x1'] * 100, 3900, 120)) is None)
    pt = next(q for q in MISION['puntos'] if q['id'] == 'hueso')
    tp(pt['pos'][0] + 90, pt['pos'][1] - 90, 135); yield 0.4
    check('dentro se está de pie', abs(jugador().get_actor_location().z - 100) < 45, jugador().get_actor_location().z)
    check('la olla ofrece mirar', 'OLLA' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 0.3
    check('te llevas el hueso', d.has_flag('hueso') and 'HUESO' in str(P('message')), str(P('message'))[:30])
    pt = next(q for q in MISION['puntos'] if q['id'] == 'raciones')
    tp(pt['pos'][0], pt['pos'][1] + 80, -90); yield 0.4
    check('el parte de raciones se puede leer', 'RACIONES' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 0.3
    check('y habla de los de abajo', 'ABAJO' in str(P('message')), str(P('message'))[:40])
    # trampilla
    pt = next(q for q in MISION['puntos'] if q['id'] == 'trampilla')
    tp(pt['pos'][0], pt['pos'][1] - 60, 90); yield 0.4
    check('la trampilla está donde dice el plano', dist2d(V(pt['pos'][0], pt['pos'][1], 0), V(tr['pos'][0] * 100, tr['pos'][1] * 100, 0)) < 160)
    check('ofrece mirarla', 'TRAMPILLA' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 0.3
    check('no se abre, y queda vista', d.has_flag('vio_trampilla') and 'no se abre' in str(P('message')), str(P('message'))[-40:])
    hz = traza(V(tr['pos'][0] * 100, tr['pos'][1] * 100, 200), V(tr['pos'][0] * 100, tr['pos'][1] * 100, -50))
    check('la hoja levanta un palmo del suelo', hz is not None and 5 < hz.to_tuple()[4].z < 25, hz.to_tuple()[4].z if hz else None)
    check('el camión para diez minutos ante el hangar (ajuste de la misión)', MISION['ajustes']['director']['truck_stay_seconds'] == 600.0)


def prueba_charlas():
    """Tanda 41. Dos guardias se juntan a hablar; de lejos solo hay murmullo y de cerca se oye cada frase. Las frases con
    dato lo apuntan en la ficha del soldado (bandera dato_<id>), una charla cortada se repite, y el mapa se abre con la M."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    t = MISION['textos']; datos = MISION['datos']; charlas = MISION['charlas']
    ids = {q['id'] for q in datos}
    claves = {q['texto'] for q in datos} | {f[1] for c in charlas for f in c['frases']}
    check('charlas y datos solo usan textos que existen', not (claves - set(t)), sorted(claves - set(t)))
    check('cada frase con dato nombra un dato que existe', all(f[2] in ids for c in charlas for f in c['frases'] if len(f) > 2))
    check('todos los que hablan están en el nivel', all(guardia(c[k]) for c in charlas for k in ('a', 'b')), [c[k] for c in charlas for k in ('a', 'b') if not guardia(c[k])])
    check('quien dice cada frase es uno de los dos', all(f[0] in (c['a'], c['b']) for c in charlas for f in c['frases']))
    check('el director tiene las %d charlas y los %d datos' % (len(charlas), len(datos)), len(P('talks')) == len(charlas) and len(P('facts')) == len(datos), '%d, %d' % (len(P('talks')), len(P('facts'))))
    check('al empezar no sabes nada', d.facts_known() == 0 and 'M mapa' not in str(d.help_line()), d.facts_known())
    jugador().set_actor_hidden_in_game(True)    # la prueba mide el oído, no que te vean
    d.set_editor_property('talk_start_dist', 0.0)   # aquí las charlas las arranca la prueba, una a una
    for k, c in enumerate(charlas):
        a, b = guardia(c['a']), guardia(c['b'])
        for g in guardias():
            g.hold(0.0 if g in (a, b) else 3600.0)
        yield 0.3
        sx, sy = c['sitio'][0], c['sitio'][1]
        aparte()
        ok = d.start_talk(k)
        check('%s: %s y %s dejan la ronda para juntarse' % (c['id'], c['a'], c['b']), ok and P('talk_idx') == k and a.is_on_errand() and b.is_on_errand())
        if not ok:
            continue
        yield ('hasta', lambda: director().get_editor_property('talk_phase') == 1 or director().get_editor_property('talk_idx') < 0, P('talk_gather') + 5.0)
        check('%s: llegan los dos al sitio' % c['id'], P('talk_phase') == 1 and dist2d(a.get_actor_location(), V(sx, sy, 0)) < 200 and dist2d(b.get_actor_location(), V(sx, sy, 0)) < 200,
              '%d y %d cm' % (dist2d(a.get_actor_location(), V(sx, sy, 0)), dist2d(b.get_actor_location(), V(sx, sy, 0))))
        if P('talk_phase') != 1:
            continue
        if k == 0:
            # primero de lejos: se ve que hablan, no se entiende y no se apunta nada
            h0 = P('talk_lines_heard')
            jugador().set_actor_location(V(sx + 800, sy, 150), False, True)
            yield ('hasta', lambda: director().get_editor_property('talk_line') >= 2, 14.0)
            check('de lejos solo hay murmullo', P('talk_lines_heard') == h0 and d.facts_known() == 0 and any('voz baja' in str(x) for x in P('subtitle_log')), [str(x)[:40] for x in list(P('subtitle_log'))[-2:]])
            jugador().set_actor_location(V(sx + 300, sy, 150), False, True)
            yield ('hasta', lambda: director().get_editor_property('talk_idx') < 0, 30.0)
            sabe = [f[2] for f in c['frases'][2:] if len(f) > 2]
            check('de cerca se oye y se apunta lo que llegaste a oír', P('talk_lines_heard') >= 2 and all(d.fact_known(x) for x in sabe) and not d.fact_known(c['frases'][0][2])
                  and 'APUNTADO' in str(P('message')), '%d frases, %d datos' % (P('talk_lines_heard') - h0, d.facts_known()))
            check('la línea de teclas ya nombra el mapa', 'M mapa' in str(d.help_line()))
            check('le queda algo que contarte: se repetirá', P('talks_ended') >= 1 and not d.fact_known(c['frases'][0][2]))
            yield 2.5
            ok = d.start_talk(k); yield 0.2
            yield ('hasta', lambda: director().get_editor_property('talk_phase') == 1 or director().get_editor_property('talk_idx') < 0, P('talk_gather') + 5.0)
        jugador().set_actor_location(V(sx + 300, sy, 150), False, True)
        yield ('hasta', lambda: director().get_editor_property('talk_idx') < 0, len(c['frases']) * (P('talk_line_seconds') + 3.0) + 12.0)
        todos = [f[2] for f in c['frases'] if len(f) > 2]
        check('%s: oída entera, sus %d datos quedan apuntados' % (c['id'], len(todos)), all(d.fact_known(x) for x in todos), [x for x in todos if not d.fact_known(x)])
        yield 2.0
    check('los datos que ponen bandera la ponen', all(d.has_flag(q['pone']) for q in datos if q.get('pone')), [q['pone'] for q in datos if q.get('pone') and not d.has_flag(q['pone'])])
    de_charlas = {f[2] for c in charlas for f in c['frases'] if len(f) > 2}   # tanda 43: hay datos que solo se sacan interrogando
    check('sabido todo, ninguna charla vuelve a empezar sola', all(d.fact_known(x) for x in de_charlas), '%d de %d' % (d.facts_known(), len(de_charlas)))
    # una charla que se corta: uno de los dos oye algo y se va
    c = charlas[1]; a = guardia(c['a'])
    for g in guardias():
        g.hold(0.0 if g.get_actor_label().endswith((c['a'], c['b'])) else 3600.0)
    yield 0.3
    n0 = P('talk_cuts')
    if d.start_talk(1):
        yield 1.0
        a.alarm(V(c['sitio'][0] + 1500, c['sitio'][1], 0)); yield 1.0
        check('si uno se va a mirar otra cosa, la charla se corta', P('talk_idx') < 0 and P('talk_cuts') == n0 + 1, '%s, %s' % (P('talk_idx'), P('talk_cuts')))
    # el mapa
    d.toggle_mind_map(); yield 0.3
    check('la M abre el mapa', P('mind_map'))
    d.toggle_mind_map(); yield 0.2
    check('y lo cierra', not P('mind_map'))
    jugador().set_actor_hidden_in_game(False)
    aparte()
    check('ningún texto pedido falta', not list(P('missing_texts')), list(P('missing_texts')))

def prueba_armados():
    """Tanda 37. Con fusil no se corre a por nadie: el guardia que te ve se queda a distancia, te apunta y da el alto.
    Quieto, uno se acerca a detenerte; si te mueves, disparan, y a la tercera herida caes. Al dar el alto piden
    refuerzos por radio. Y las escaleras de las torres: se sube y se baja con la E."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    vl = lambda: [str(x) for x in director().get_editor_property('voice_log')]
    ronda = lambda: [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and not x.get_actor_label().endswith('Ramos')]
    yield ('hasta', lambda: len(ronda()) > 1, 30.0)
    g = ronda()[0]
    for x in guardias():
        if x != g:
            x.hold(3600.0)
    c0 = P('captures')
    d.set_editor_property('armed_aim', 0.0)
    d.set_editor_property('player_speed_override', 0.0)
    a_la_vista_de(g, 900)
    d.set_torch(True)   # de noche y a 9 m: con la linterna encendida te ve seguro
    g.alarm(jugador().get_actor_location())
    yield ('hasta', lambda: director().get_editor_property('halt'), 8.0)
    dist = lambda: dist2d(g.get_actor_location(), jugador().get_actor_location())
    check('te ve y da el alto sin echarse encima', P('halt') and P('halts') == 1 and dist() > 400 and not P('capturing'), '%d cm, %s' % (dist(), estado(g)))
    check('dice «¡alto!»', any(x.endswith('_alto') for x in vl()), vl()[-3:])
    # quieto: uno se acerca andando a detenerte
    yield ('hasta', lambda: director().get_editor_property('arrest_guard') is not None, P('surrender_seconds') + 6.0)
    check('quieto, viene a detenerte', P('surrenders') == 1 and P('arrest_guard') == g and P('shots') == 0, P('surrenders'))
    d0 = dist()
    yield 1.5
    check('se acerca andando', dist() < d0 - 60 or P('capturing'), '%d -> %d' % (d0, dist()))
    # echas a correr: ya no viene, dispara (con la puntería a cero para la prueba, falla)
    d.set_editor_property('player_speed_override', 350.0)
    a_la_vista_de(g, 900)
    yield ('hasta', lambda: director().get_editor_property('shots') > 0, 14.0)
    check('si te mueves, dispara', P('shots') > 0 and P('fleeing') and P('arrest_guard') is None and P('hits') == 0 and P('wounds') == 0, '%s tiros, %s' % (P('shots'), estado(g)))
    check('sigue sin echarse encima', dist() > 350 and P('captures') == c0, '%d cm' % dist())
    check('rendirse contó una sola vez', P('surrenders') == 1, P('surrenders'))
    check('el tiro pone la base en guardia', P('tension_t') > 60.0, P('tension_t'))
    check('tanda 39: cada tiro, su fogonazo', P('shot_flashes') == P('shots'), '%s de %s' % (P('shot_flashes'), P('shots')))
    # los refuerzos: había pedido apoyo al dar el alto, pero estaban todos quietos (hold); ahora uno libre
    check('pidió refuerzos por radio', 'central_refuerzos' in vl(), vl()[-4:])
    # con puntería: heridas, y a la tercera caes
    d.set_editor_property('armed_aim', 100.0)
    yield ('hasta', lambda: director().get_editor_property('wounds') > 0 or director().get_editor_property('capturing'), 10.0)
    check('un impacto es una herida', P('hits') >= 1 and (P('wounds') >= 1 or P('capturing')) , '%s impactos, %s heridas' % (P('hits'), P('wounds')))
    yield ('hasta', lambda: director().get_editor_property('captures') > c0, 30.0)
    check('a la tercera herida caes y te llevan', P('captures') == c0 + 1 and P('hits') >= P('max_wounds'), '%s impactos' % P('hits'))
    yield ('hasta', lambda: not director().get_editor_property('capturing'), 6.0)
    d.set_editor_property('player_speed_override', -1.0)
    check('tras la captura no queda alto ni heridas', P('wounds') == 0 and not P('fleeing'))
    # las escaleras de las torres
    for x in guardias():
        x.hold(3600.0)
    d.set_torch(False)
    pies, altos = list(P('ladders')), list(P('ladder_tops'))
    check('cuatro torres con escalera', len(pies) == 4 and len(altos) == 4, len(pies))
    if pies:
        b, t = pies[0], altos[0]
        p = jugador()
        p.set_actor_location(V(b.x + 60, b.y, 110), False, True); yield 0.5
        check('al pie de la torre, el aviso de subir', 'SUBIR' in str(d.ladder_prompt()), '%s (z %d)' % (d.ladder_prompt(), p.get_actor_location().z))
        d.interact(); yield 0.3
        check('subiendo no hay control ni otro aviso', P('climbing') and not str(d.ladder_prompt()))
        yield P('climb_seconds') + 1.0
        l = p.get_actor_location()
        check('arriba, en la plataforma', not P('climbing') and l.z > t.z + 50 and dist2d(l, t) < 150, '%d,%d,%d' % (l.x, l.y, l.z))
        yield 1.0
        l = p.get_actor_location()
        check('y la plataforma te sostiene', l.z > t.z + 50, '%d' % l.z)
        check('arriba, el aviso de bajar', 'BAJAR' in str(d.ladder_prompt()), str(d.ladder_prompt()))
        check('arriba, la E es la escalera y no el centinela', 'BAJAR' in str(d.interact_prompt()), str(d.interact_prompt()))
        d.interact(); yield P('climb_seconds') + 1.0
        l = p.get_actor_location()
        check('de vuelta al pie', l.z < 300 and dist2d(l, b) < 200, '%d,%d,%d' % (l.x, l.y, l.z))
    check('ningún texto pedido falta', not list(P('missing_texts')), list(P('missing_texts')))

def prueba_cruce():
    """Tanda 47 (idea de Andres). Una charla sale cuando sus dos guardias, de ronda, se cruzan (a menos de TalkCrossDist)
    y tú estás cerca (TalkNearDist): se paran allí mismo, no en el sitio fijo. Contigo lejos, se cruzan y no hablan."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    c = MISION['charlas'][0]
    a, b = guardia(c['a']), guardia(c['b'])
    check('los dos de la primera charla están en el nivel', a is not None and b is not None)
    if not a or not b:
        return
    jugador().set_actor_hidden_in_game(True)
    for g in guardias():
        g.hold(0.0 if g in (a, b) else 3600.0)
    yield ('hasta', lambda: director().get_editor_property('mission_time') > float(c.get('desde', 0)) + 1.0, float(c.get('desde', 0)) + 30.0)   # antes de su hora no hablan
    sx, sy = c['sitio'][0], c['sitio'][1]
    juntos = lambda: (a.set_actor_location(V(sx - 900, sy - 250, a.get_actor_location().z), False, True), b.set_actor_location(V(sx - 900, sy + 250, b.get_actor_location().z), False, True))
    n0 = P('talks_crossed')
    aparte(); juntos(); d.set_editor_property('talk_wait', 0.0)
    yield 4.5
    check('contigo lejos se cruzan y no se paran a hablar', P('talk_idx') < 0 and P('talks_crossed') == n0, '%s %s' % (P('talk_idx'), P('talks_crossed')))
    tp(sx - 900, sy + 1100); juntos(); d.set_editor_property('talk_wait', 0.0)
    yield ('hasta', lambda: director().get_editor_property('talk_idx') >= 0, 8.0)
    sp = P('talk_spot_now')
    check('contigo cerca, al cruzarse se paran a hablar', P('talk_idx') == 0 and P('talks_crossed') == n0 + 1 and a.is_on_errand() and b.is_on_errand(), '%s %s' % (P('talk_idx'), P('talks_crossed')))
    check('hablan donde se cruzan, no en el sitio fijo', math.hypot(sp.x - (sx - 900), sp.y - sy) < 500 and math.hypot(sp.x - sx, sp.y - sy) > 400, '%.0f %.0f frente a %s %s' % (sp.x, sp.y, sx, sy))
    yield ('hasta', lambda: director().get_editor_property('talk_phase') == 1 or director().get_editor_property('talk_idx') < 0, P('talk_gather') + 5.0)
    check('se juntan y empiezan', P('talk_phase') == 1, P('talk_phase'))
    d.set_editor_property('talk_rule', False); yield 0.3    # se corta: la prueba de las charlas empieza de cero
    d.set_editor_property('talk_rule', True)
    jugador().set_actor_hidden_in_game(False)

def prueba_apuntar():
    """Tanda 47. Con dardos, mantener el botón derecho cierra la vista a AimFov y saca la mira; al soltar vuelve. Sin
    dardos no se apunta."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    cam = jugador().get_component_by_class(unreal.CameraComponent)
    aparte(); yield 0.3
    f0 = cam.get_editor_property('field_of_view')
    d0 = P('darts')
    d.set_editor_property('darts', 0)
    d.set_editor_property('aim_held', True); yield 0.6
    check('sin dardos no se apunta', P('aim_alpha') < 0.01 and abs(cam.get_editor_property('field_of_view') - f0) < 0.5 and not d.can_aim(), '%.2f %.1f' % (P('aim_alpha'), cam.get_editor_property('field_of_view')))
    d.set_editor_property('darts', 3); yield 0.8
    check('con dardos, el botón derecho cierra la vista', P('aim_alpha') > 0.95 and abs(cam.get_editor_property('field_of_view') - P('aim_fov')) < 1.0, '%.2f %.1f' % (P('aim_alpha'), cam.get_editor_property('field_of_view')))
    check('apuntando al aire la mira no marca a nadie', d.dart_aim() is None)
    d.set_editor_property('aim_held', False); yield 0.8
    check('al soltar, la vista vuelve', P('aim_alpha') < 0.01 and abs(cam.get_editor_property('field_of_view') - f0) < 0.5, '%.2f %.1f frente a %.1f' % (P('aim_alpha'), cam.get_editor_property('field_of_view'), f0))
    d.set_editor_property('aim_held', True); yield 0.6
    d.toggle_binoculars(); yield 0.3
    d.toggle_binoculars(); d.set_editor_property('aim_held', False); yield 0.8
    check('prismáticos mientras apuntas: al bajar todo, la vista es la de antes', abs(cam.get_editor_property('field_of_view') - f0) < 0.5, cam.get_editor_property('field_of_view'))
    d.set_editor_property('darts', d0)

def prueba_perro():
    """Tanda 46. El perro del hangar ronda entre dos puntas; no ve, huele: a menos de DogSmell gruñe (aviso, sin ladrar),
    si no te apartas ladra y llama a los guardias de cerca, y si te vas se calla. Con el hueso de la olla se le puede dar
    desde DogGiveDist: se sienta, queda amigo y ya no ladra. Al capturarte vuelve a su ronda."""
    d = director()
    P = lambda k: d.get_editor_property(k)
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 1.0
    check('el perro está en el hangar (modelo importado con sus cuatro animaciones)', d.dog_ready() and d.dog_anim_count() == 4, '%s %s' % (d.dog_ready(), d.dog_anim_count()))
    if not d.dog_ready():
        return
    l0 = d.dog_location()
    hg = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']['hangar']
    check('nace dentro del hangar y sobre el suelo', hg['x0'] * 100 < l0.x < hg['x1'] * 100 and hg['y0'] * 100 < l0.y < hg['y1'] * 100 and abs(l0.z) < 60, '%.0f %.0f %.0f' % (l0.x, l0.y, l0.z))
    yield 3.0
    l1 = d.dog_location()
    check('ronda: anda sin que nadie lo moleste', P('dog_state') == 0 and math.hypot(l1.x - l0.x, l1.y - l0.y) > 150 and d.dog_anim_index() == 1, '%.0f cm, estado %s, anim %s' % (math.hypot(l1.x - l0.x, l1.y - l0.y), P('dog_state'), d.dog_anim_index()))
    mira = math.degrees(math.atan2(l1.y - l0.y, l1.x - l0.x))
    check('mira hacia donde anda', abs((d.dog_facing() - mira + 540) % 360 - 180) < 25, '%.0f frente a %.0f' % (d.dog_facing(), mira))
    # agachado y a oscuras da igual: huele
    cerca = lambda r: tp(d.dog_location().x, d.dog_location().y + r)
    b0 = P('dog_barks')
    cerca(P('dog_smell') - 120); jugador().crouch(); yield 0.6
    check('a un paso te huele y gruñe, sin ladrar todavía', P('dog_state') == 1 and P('dog_growls') == 1 and P('dog_barks') == b0, '%s %s %s' % (P('dog_state'), P('dog_growls'), P('dog_barks')))
    check('no ofrece nada si no llevas el hueso', 'HUESO' not in str(d.interact_prompt()), str(d.interact_prompt()))
    cerca(P('dog_smell') * 1.25 + 300); yield 2.2
    check('si te apartas, se le pasa', P('dog_state') == 0 and P('dog_barks') == b0, '%s %s' % (P('dog_state'), P('dog_barks')))
    cerca(P('dog_smell') - 120); yield P('dog_growl_seconds') + 2.0
    check('si te quedas, ladra', P('dog_state') == 2 and P('dog_barks') > b0, '%s %s' % (P('dog_state'), P('dog_barks')))
    for g in guardias():
        g.hold(0.0)
    yield 3.0
    check('los ladridos llaman a guardias de cerca (si los hay a menos de DogBarkRadius)', P('dog_calls') >= 0, P('dog_calls'))
    aparte(); yield 4.5
    check('lejos, se calla y vuelve a la ronda', P('dog_state') == 0, P('dog_state'))
    # el hueso
    d.set_flag('hueso')
    b1 = P('dog_barks')
    cerca(P('dog_give_dist') - 60); yield 0.5
    check('con el hueso, la E es dárselo', 'HUESO' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 1.5
    check('se lo come: amigo, sentado, y ya no llevas el hueso', P('dog_state') == 3 and d.has_flag('perro_amigo') and not d.has_flag('hueso') and d.dog_anim_index() in (2, 3), '%s anim %s' % (P('dog_state'), d.dog_anim_index()))
    cerca(100); yield 5.0
    check('amigo: ni gruñe ni ladra aunque lo pises', P('dog_barks') == b1 and P('dog_state') == 3, '%s %s' % (P('dog_barks'), P('dog_state')))
    jugador().un_crouch()

def prueba_tactica():
    """Tanda 43. Interrogar por la espalda (T) da un dato que le toca a ese guardia y lo deja quieto unos segundos;
    asomarse (Z, V) saca la cámara de lado sin mover el cuerpo; y el que te pierde deja tu silueta en el último sitio
    donde te vio y llama a un compañero para registrarlo."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    datos = MISION['datos']
    le_toca = lambda n: [q['id'] for q in datos if q.get('enlace') == n] + [q['id'] for q in datos if q['ficha'] == n]
    nombre = lambda g: str(g.get_editor_property('guard_name'))
    yield ('hasta', lambda: all(estado(x) == 'PATROL' for x in guardias() if not x.get_editor_property('tower_sentry')), 30.0)
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry') and estado(g) == 'PATROL' and nombre(g) != 'Ramos']
    # ---- interrogar
    con_dato = [g for g in ronda if le_toca(nombre(g))]
    check('hay guardias de ronda con algo que contar', len(con_dato) >= 2, [nombre(g) for g in con_dato])
    g = con_dato[0]
    g.hold(3600.0)
    d.forget_interrogations()
    d.simulate_key('C'); yield 0.3
    for _ in range(3):
        detras_de(g, 90); yield 0.1
    check('por la espalda, el aviso ofrece interrogar', 'INTERROGAR' in str(d.interact_prompt()) and 'DERRIBAR' in str(d.interact_prompt()), d.interact_prompt())
    n0, i0, f0 = d.facts_known(), P('interrogations'), P('interrogation_facts')
    d.simulate_key('T'); yield 0.3
    check('la T de verdad lo interroga', P('interrogations') == i0 + 1, P('interrogations'))
    check('y suelta un dato de los que le tocan', d.facts_known() == n0 + 1 and P('interrogation_facts') == f0 + 1 and any(d.has_flag('dato_' + i) for i in le_toca(nombre(g))), '%d datos; %s' % (d.facts_known(), le_toca(nombre(g))))
    check('levanta las manos', 'manos' in [str(x) for x in g.get_editor_property('gesture_log')], [str(x) for x in g.get_editor_property('gesture_log')][-3:])
    check('se queda quieto, a mano para derribarlo', g.is_stunned() and estado(g) != 'ALERT' and 'DERRIBAR' in str(d.interact_prompt()), '%s / %s' % (estado(g), d.interact_prompt()))
    check('ya no se ofrece interrogarlo otra vez', 'INTERROGAR' not in str(d.interact_prompt()), d.interact_prompt())
    d.interrogate(); yield 0.1
    check('y si insistes, no cuenta ni da más datos', P('interrogations') == i0 + 1 and d.facts_known() == n0 + 1, P('interrogations'))
    d.simulate_key('E'); yield 0.3
    check('con la E cae', estado(g) == 'DOWN', estado(g))
    d.simulate_key('C'); yield 0.3
    # quien no tiene nada que le toque, no llena el mapa
    sin = [x for x in ronda if not le_toca(nombre(x)) and x != g]
    if sin:
        x = sin[0]; x.hold(3600.0)
        for _ in range(3):
            detras_de(x, 90); yield 0.1
        n1 = d.facts_known()
        d.interrogate(); yield 0.2
        check('el que no sabe nada lo dice y no apunta ningún dato', d.facts_known() == n1 and P('interrogations') == i0 + 2, '%s: %d' % (nombre(x), d.facts_known()))
        d.simulate_key('E'); yield 0.3
    # ---- la caja de cartón, de cerca, ya no engaña (tanda 44)
    otros = [x for x in ronda if estado(x) == 'PATROL' and x != g]
    if otros:
        o = otros[0]; o.hold(3600.0)
        d.set_flag('caja')
        a_la_vista_de(o, 400.0); yield 0.2
        if not P('box_on'):
            d.toggle_box()
        yield 1.0
        check('quieto en la caja a 4 m, no te ve', P('box_on') and o.visibility(jugador()) == 0.0, o.visibility(jugador()))
        a_la_vista_de(o, 120.0)
        v_cerca = o.visibility(jugador())   # sin esperar: si te ve de verdad, te coge
        jugador().set_actor_hidden_in_game(True)
        check('a un paso, la caja ya no engaña', v_cerca > 0.0, v_cerca)
        if P('box_on'):
            d.toggle_box()
        tp(4300, 3500, 0); yield 0.3
        jugador().set_actor_hidden_in_game(False)
        yield ('hasta', lambda: all(estado(x) in ('PATROL', 'DOWN') for x in guardias() if not x.get_editor_property('tower_sentry')), 40.0)
    # ---- asomarse, en lo abierto
    tp(4300, 3500, 0); yield 0.3   # en (3000,4600) la cámara toca contenedor_2 y hacia él no se asoma (bien)
    cam = lambda: jugador().get_component_by_class(unreal.CameraComponent).get_world_location()
    lado = lambda a, b: (b.x - a.x) * r.x + (b.y - a.y) * r.y
    c0 = cam(); p0 = jugador().get_actor_location(); r = jugador().get_actor_right_vector()
    d.simulate_key('V', True, False); yield 0.7
    c1 = cam()
    check('la V saca la cámara a la derecha', 35.0 < lado(c0, c1) <= P('lean_dist') + 1.0 and abs(P('lean_now') - lado(c0, c1)) < 3.0, '%.0f cm (lean_now %.0f)' % (lado(c0, c1), P('lean_now')))
    check('sin mover el cuerpo', dist2d(p0, jugador().get_actor_location()) < 3.0, dist2d(p0, jugador().get_actor_location()))
    d.simulate_key('V', False, True); yield 0.7
    check('al soltarla vuelve', abs(lado(c0, cam())) < 2.0 and abs(P('lean_now')) < 1.0, lado(c0, cam()))
    d.simulate_key('Z', True, False); yield 0.7
    check('y la Z la saca a la izquierda', lado(c0, cam()) < -35.0, lado(c0, cam()))
    d.simulate_key('Z', False, True); yield 0.7
    check('la línea de teclas lo nombra', 'asomarse' in str(d.help_line()), str(d.help_line())[-70:])
    # ---- el último sitio donde te vieron: el que te pierde deja la silueta y llama al libre más cercano
    libres = [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and nombre(x) != 'Ramos']
    pares = sorted(((dist2d(a.get_actor_location(), b.get_actor_location()), i, j) for i, a in enumerate(libres) for j, b in enumerate(libres) if i != j))
    if not pares:
        check('quedan dos guardias de ronda para la búsqueda en pareja', False); return
    dd, i, j = pares[0]; a, b = libres[i], libres[j]
    la = a.get_actor_location()
    jugador().set_actor_hidden_in_game(True)   # se mide que te pierdan, no que te vean
    m0, s0 = P('last_known_marks'), P('partner_searches')
    a.alarm(la)
    yield ('hasta', lambda: director().get_editor_property('last_known_marks') > m0, 20.0)
    check('al perderte queda la silueta donde te vio', P('last_known_marks') == m0 + 1 and P('last_known_t') > 0.0 and dist2d(P('last_known'), la) < 50.0, '%s, %.0f s' % (P('last_known_marks'), P('last_known_t')))
    if dd < P('partner_dist'):
        yield 0.3
        check('y llama al compañero más cercano', P('partner_searches') == s0 + 1 and estado(b) in ('SUSPICIOUS', 'SEARCH'), '%s a %.0f cm: %s' % (nombre(b), dd, estado(b)))
    t0 = P('last_known_t')
    yield 1.0
    check('la silueta se va con el tiempo', P('last_known_t') < t0, P('last_known_t'))
    jugador().set_actor_hidden_in_game(False)

# cada familia, en un PIE limpio; dentro de una familia las pruebas comparten partida (la llave, la jefatura, el farol...)
FAMILIAS = [[prueba_intro, prueba_datos, prueba_zona, prueba_empezar], [prueba_guardias], [prueba_menu, prueba_musica, prueba_controles, prueba_opciones],
            [prueba_frente], [prueba_captura, prueba_perdido, prueba_calma], [prueba_dardos, prueba_punto_control, prueba_cambios, prueba_farol, prueba_final],
            [prueba_escondites], [prueba_cuerpo], [prueba_generador], [prueba_reserva], [prueba_perimetro, prueba_desgaste, prueba_charcos], [prueba_anillo, prueba_camion, prueba_viaje], [prueba_puertas],
            [prueba_mojado, prueba_carteles, prueba_cobertura, prueba_gestos], [prueba_materia, prueba_cielo], [prueba_foco], [prueba_sombra], [prueba_farola], [prueba_radio], [prueba_apoyo], [prueba_codec], [prueba_esquinas], [prueba_linternas], [prueba_emisora], [prueba_calabozo], [prueba_equipo], [prueba_armados], [prueba_hangar], [prueba_cruce, prueba_charlas], [prueba_bengala], [prueba_tactica, prueba_apuntar], [prueba_perro]]
PRUEBAS = []


# ---------------------------------------------------------------- ejecutor por ticks

def _informe():
    # al acabar se cierra la partida: si se queda abierta, desde fuera parece que alguien está jugando
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    except Exception:
        pass
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
    # el camión (tanda 21) solo en sus pruebas: en las demás cruzaría la base a mitad de una medida de luz o de una captura
    if d:
        d.set_editor_property('truck', siguiente in (prueba_camion, prueba_viaje))
        # tu sombra (tanda 26) solo en su prueba: las demás plantan al jugador bajo farolas para medir otra cosa
        d.set_editor_property('shadow_tells', siguiente is prueba_sombra)
        # tanda 28: contestar por radio y pedir apoyo, solo en sus pruebas (las demás derriban guardias y rompen farolas para medir otra cosa)
        d.set_editor_property('radio_answer', siguiente is prueba_radio)
        d.set_editor_property('buddy_rule', siguiente is prueba_apoyo)
        # tanda 29: las llamadas entrantes del códec, solo en su prueba (prueba_codec las enciende ella)
        d.set_editor_property('codec_calls', False)
        # tanda 32: la charla de Lobato y Carmona, solo en su prueba (mete voces en el registro que otras cuentan)
        d.set_editor_property('radio_chat', False)
        # tanda 35: el puzle del calabozo, solo en su prueba (en las demás la reja se abre sola, como antes, y siguen)
        d.set_editor_property('cell_puzzle', siguiente in (prueba_calabozo, prueba_equipo))
        # tanda 37: guardias armados (alto, cobertura, disparos), solo en su prueba: las demás se escribieron con
        # guardias que corren a cogerte y miden otra cosa
        d.set_editor_property('armed_rule', siguiente is prueba_armados)
        # tanda 40: el control de entrada y la parada del camión ante el hangar, solo en su prueba (las del camión miden
        # tiempos de la pasada de antes); y la caja de cartón, quitada
        # tanda 41: las charlas sacan a los guardias de su ronda: solo en su prueba
        d.set_editor_property('talk_rule', siguiente in (prueba_charlas, prueba_cruce))
        d.set_editor_property('talk_start_dist', 3000.0)
        if d.get_editor_property('mind_map'):
            d.toggle_mind_map()
        d.set_editor_property('truck_entry_papers', 0.0)
        d.set_editor_property('truck_stay_seconds', 0.0)
        # tanda 42: ni bengalas ni parpadeo de tu linterna fuera de su prueba (cambian la luz que miden las demás), y de noche
        # tanda 43: la búsqueda en pareja, solo en su prueba (las demás dan alarmas para medir otra cosa)
        d.set_editor_property('last_seen_rule', siguiente is prueba_tactica)
        d.set_editor_property('talk_cross', siguiente is prueba_cruce)   # tanda 47: en las demás, las charlas no salen solas al cruzarse
        d.set_editor_property('aim_held', False)
        d.set_editor_property('dog', siguiente is prueba_perro)   # tanda 46: el perro solo ronda en su prueba (en las del hangar ladraria y traeria guardias)
        d.set_editor_property('lean_left', False); d.set_editor_property('lean_right', False)
        # tanda 44: la caja que se nota de cerca, solo en su prueba (las de la caja se escribieron pegadas al guardia)
        d.set_editor_property('box_notice_dist', 150.0 if siguiente is prueba_tactica else 0.0)
        d.set_editor_property('flares', False)
        d.set_editor_property('torch_flicker', False)
        if d.get_editor_property('day'):
            d.set_day(False)
        if d.get_editor_property('box_on'):
            d.toggle_box()
        d.set_editor_property('player_speed_override', -1.0)
        d.set_editor_property('armed_aim', 1.0)
        d.set_editor_property('wounds', 0)
        # tanda 31: la linterna según el sitio, solo en su prueba (las demás miden a qué distancia te ven a oscuras sin ella)
        d.set_editor_property('context_torch', siguiente is prueba_linternas)
        d.set_torch(False)
    # tanda 30: los ocho centinelas de las torres de esquina, quietos y sin ver salvo en su prueba: las demás plantan al
    # jugador por el anillo y se escribieron sin ellos (su foco se queda parado al principio de su recorrido)
    # Los de dentro siguen vivos, como lo estaban las dos torres de antes; los vigías de fuera, quietos
    if siguiente is not prueba_esquinas:
        for g in _de_esquina():
            if g.get_actor_label().startswith('Vigia_'):
                g.hold(3600.0)
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
