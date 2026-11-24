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
    check('fluorescente que titila, zumbido eléctrico y gotera (tanda E1: más el de la enfermería)', z.x >= 1 and (z.y, z.z) == (1, 1), (z.x, z.y, z.z))
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
    # tanda E2: no al llegar a una esquina de su ronda (ahí se para y echa un vistazo alrededor: te ve, y con razón)
    def _lejos_de_esquina():
        l = g.get_actor_location()
        return min(dist2d(l, p) for p in g.get_editor_property('patrol_points')) > 350
    yield ('hasta', _lejos_de_esquina, 25.0)
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
    yield ('hasta', lambda: director().get_editor_property('captures') > c0, 10.0)   # tanda A, novena: la detención dura unos 5 s
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
    # tanda A: con el ABP del GASP el giro en el sitio es una animación de giro (Motion Matching) y no los pasos sueltos de
    # antes (bTurnStepping queda a falso): se mide que el cuerpo gira y que los pies de la persona se mueven al girar
    gasp = m.uses_gasp()
    cuerpo = ([c for c in m.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name().startswith('CuerpoPersona')] or [None])[0]
    def pies():
        if not cuerpo:
            return None
        l = m.get_actor_location()
        return [cuerpo.get_socket_location(b) - l for b in ('ball_l', 'ball_r')]
    yaw0, pies0, giro, paso = m.get_actor_rotation().yaw, pies(), 0.0, 0.0
    cabeza, pasos_giro, vmin, error = 0.0, False, 1e9, 180.0
    # tanda A, séptima: parado, el ABP del GASP solo gira las piernas si quiere apuntar; el guardia pone WantsToAim un
    # momento cuando las piernas se quedan GaspTurnFrom grados por detrás (TarsisGaspTurn.h)
    apunto, desfase, alineado = False, 0.0, False
    def mira_giro():
        nonlocal apunto, desfase, alineado
        if not gasp:
            return
        apunto = apunto or m.gasp_turn_aiming()
        desfase = max(desfase, abs(m.gasp_turn_delta()))
        if apunto and m.get_velocity().length() < 10 and abs(m.gasp_turn_delta()) < 20:
            alineado = True
    for _ in range(12):
        yield 0.1
        mira_giro()
        error = min(error, error_giro())
        cabeza = max(cabeza, abs(m.get_editor_property('look_yaw')))
        pasos_giro = pasos_giro or m.get_editor_property('turn_stepping')
        giro = max(giro, abs((m.get_actor_rotation().yaw - yaw0 + 540) % 360 - 180))
        p = pies()
        if p and pies0:
            # el pie se mueve respecto al cuerpo más de lo que lo movería el giro rígido de la pose
            paso = max(paso, max((p[i] - pies0[i]).length() for i in range(2)))
        if estado(m) == 'SUSPICIOUS': vmin = min(vmin, m.get_velocity().length())
    check('se para al oír el ruido', vmin < 40, round(vmin))
    check('se gira hacia el ruido', error < 30, '%.0f grados de error' % error)
    check('la cabeza se adelanta al cuerpo', cabeza > 6, '%.0f grados' % cabeza)
    if gasp:
        check('gira en el sitio dando pasos (GASP: gira y mueve los pies)', giro > 30 and paso > 8, 'giro %.0f grados, pie %.0f cm' % (giro, paso))
        for _ in range(15):
            if alineado or m.get_velocity().length() >= 10:
                break
            yield 0.1
            mira_giro()
        check('parado, las piernas siguen al cuerpo (giro en el sitio del GASP)', apunto and (alineado or m.get_velocity().length() >= 10),
              'desfase máximo %.0f grados, WantsToAim %s, alineado parado %s' % (desfase, apunto, alineado))
        yield 2.0
        check('el giro no deja puesto WantsToAim', not m.gasp_turn_aiming(), m.gasp_turn_aiming())
    else:
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
    # lo que se ve: la cámara de la escena (tanda A, novena: una cámara suelta que sigue a tu cabeza) o la tuya
    cm = pc.get_editor_property('player_camera_manager')
    cam = cm.get_camera_location()
    gl = g.get_actor_location()
    quiere = math.degrees(math.atan2(gl.y - cam.y, gl.x - cam.x))
    err = abs((quiere - cm.get_camera_rotation().yaw + 540) % 360 - 180)
    check('la cámara se vuelve hacia él', err < 30, '%.0f grados' % err)
    # tanda A, novena: rendido (te coge de cerca, sin huir): empujón del GASP, caes con física, se agacha sobre ti,
    # esposas y negro. Sin el GASP en el guardia o en Cuttlas, la escena de antes (CaptureSceneKind 0)
    nueva = d.capture_scene_kind() != 0
    vistos = {'tipo': d.capture_scene_kind(), 'pareja': d.capture_scene_pair(), 'cae': False, 'esposas': False, 'agachado': False}
    def mira():
        vistos['cae'] = vistos['cae'] or d.capture_scene_ragdoll()
        vistos['esposas'] = vistos['esposas'] or d.capture_scene_cuffed()
        vistos['agachado'] = vistos['agachado'] or g.get_editor_property('is_crouched')
        return director().get_editor_property('captures') > c0
    yield ('hasta', mira, 10.0)
    if nueva:
        check('detención de rendido: empujón del GASP según de dónde viene', vistos['tipo'] == 1 and vistos['pareja'].startswith('shove_'), '%s %s' % (vistos['tipo'], vistos['pareja']))
        check('caes con física, se agacha sobre ti y suenan las esposas antes del negro', vistos['cae'] and vistos['agachado'] and vistos['esposas'], vistos)
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
    d.set_editor_property('miss_min', 40.0); d.set_editor_property('miss_max', 40.0)   # tanda F: 60-120 s; aquí, 40 como antes
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
    check('en reposo, las manos a los lados', 55 < h0 < 122 and 55 < i0 < 122 and nombre() == 'None', 'derecha %d cm, izquierda %d cm, %s' % (h0, i0, nombre()))
    g.play_gesture('alto', 2.0, V(0, 0, 0)); yield 0.9
    h1 = g.hand_height(True)
    # tanda E2: desde la tanda D las manos van a la estatura de cada persona: con una alta la mano en reposo cuelga a
    # 114 cm y la de «alto» a 169 (encima de su cabeza); +60 sobre el reposo fallaba sin que estuviera mal
    check('«alto»: la mano derecha por encima de la cabeza', h1 > 160 and h1 > h0 + 50 and nombre() == 'alto' and g.get_editor_property('gesture_w') > 0.95,
          '%d cm (en reposo %d), %s, peso %.2f' % (h1, h0, nombre(), g.get_editor_property('gesture_w')))
    check('y la izquierda sigue en su sitio', abs(g.hand_height(False) - i0) < 10, '%d cm' % g.hand_height(False))
    yield 1.9
    h2 = g.hand_height(True)
    check('al acabar el gesto, el brazo vuelve a su sitio', abs(h2 - h0) < 10 and nombre() == 'None' and g.get_editor_property('gesture_w') < 0.01, '%d cm, %s' % (h2, nombre()))
    g.play_gesture('leer', 1.6, V(0, 0, 0)); yield 0.9
    hd, hi = g.hand_height(True), g.hand_height(False)
    check('«leer»: las dos manos delante del pecho', 95 < hd < 160 and 95 < hi < 160 and hd > h0 + 5 and hi > i0 + 5 and nombre() == 'leer', 'derecha %d cm, izquierda %d cm' % (hd, hi))
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
    yield ('hasta', lambda: director().get_editor_property('captures') > c0, 10.0)   # tanda A, novena: la detención dura unos 5 s
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
    check('CONTROLES abre la página de teclas', len(ls) == 16 and 'VOLVER' in ls[-1], ' / '.join(ls))   # 14 acciones (tanda H: MATAR)
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
    yield from teclas(d, *(['Down'] * 14), 'Enter')   # catorce acciones desde la tanda H
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
    # el tamaño del texto guardado de quien juega puede no ser 100 %: se mira antes y se comprueba el cambio desde ahí
    yield from teclas(d, 'P')
    tam = [x for x in lineas(d) if 'TAMANO DEL TEXTO' in x]
    tam0 = int(tam[0].split('<')[1].split('%')[0]) if tam else 100
    yield from teclas(d, 'P')
    tam1 = min(tam0 + 10, 140)
    if dif0 != 1:
        yield from teclas(d, 'P', *(['Down'] * 10), 'Right' if dif0 == 0 else 'Left', 'P')
    yield from teclas(d, 'P', *(['Down'] * 10), 'Right')
    check('DIFICULTAD pasa a DIFICIL', 'DIFICULTAD   < DIFICIL >' in ' '.join(lineas(d)), [x for x in lineas(d) if 'DIFICULTAD' in x])
    check('la dificultad se guarda en el director', d.get_editor_property('difficulty') == 2, d.get_editor_property('difficulty'))
    yield from teclas(d, 'Left', 'Down', 'Right', 'Down', 'Enter', 'Down', 'Enter', 'P')
    ls = ' '.join(lineas(d))
    check('tamaño del texto un 10 %% más (de %d a %d %%)' % (tam0, tam1), 'TAMANO DEL TEXTO   < %d %%' % tam1 in ls, [x for x in lineas(d) if 'TAMANO' in x])
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
    check('opciones restauradas', d.get_editor_property('difficulty') == 1 and 'TAMANO DEL TEXTO   < %d %%' % (tam1 - 10) in ' '.join(lineas(d)),
          [x for x in lineas(d) if 'TAMANO' in x])
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
    d.set_editor_property('miss_min', 40.0); d.set_editor_property('miss_max', 40.0)   # tanda F: 60-120 s; aquí, 40 como antes
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
            jugador().set_actor_location(V(sx + 1300, sy, 150), False, True)
            yield ('hasta', lambda: director().get_editor_property('talk_line') >= 2, 14.0)
            check('a media distancia llegan palabras sueltas', P('talk_lines_half') >= 1, P('talk_lines_half'))
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
    # los refuerzos: había pedido apoyo al dar el alto, pero estaban todos quietos (hold); ahora uno libre.
    # La central contesta BackupDelay (5 s) después del alto; si te disparan antes (el primer tiro puede llegar a los ~4 s
    # del alto) la comprobación llegaba antes que la radio y fallaba a veces: se espera a que pase ese plazo
    yield ('hasta', lambda: 'central_refuerzos' in [str(x) for x in director().get_editor_property('voice_log')], P('backup_delay') + 2.0)
    check('pidió refuerzos por radio', 'central_refuerzos' in vl(), vl()[-4:])
    # con puntería: heridas, y a la tercera caes
    d.set_editor_property('armed_aim', 100.0)
    yield ('hasta', lambda: director().get_editor_property('wounds') > 0 or director().get_editor_property('capturing'), 10.0)
    check('un impacto es una herida', P('hits') >= 1 and (P('wounds') >= 1 or P('capturing')) , '%s impactos, %s heridas' % (P('hits'), P('wounds')))
    golpe = {'tipo': 0, 'borroso': 0.0}
    def mira_golpe():
        if director().capture_scene_kind() != 0:
            golpe['tipo'] = director().capture_scene_kind()
            golpe['pareja'] = str(director().capture_scene_pair())
        golpe['borroso'] = max(golpe['borroso'], director().capture_blur())
        return director().get_editor_property('captures') > c0
    yield ('hasta', mira_golpe, 30.0)
    check('a la tercera herida caes y te llevan', P('captures') == c0 + 1 and P('hits') >= P('max_wounds'), '%s impactos' % P('hits'))
    # tanda A, novena: herido, la escena del golpe (derribo del GASP) con la vista borrosa
    check('herido: detención a golpes, con la vista borrosa', golpe['tipo'] in (0, 2) and (golpe['tipo'] == 0 or golpe['borroso'] > 0.5), golpe)
    # tanda B: con fusil, el golpe es el culatazo de Lyra; y los tiros suenan según la distancia (7,62 cerca/media/lejos)
    check('tanda B: con fusil, el golpe es un culatazo', golpe['tipo'] != 2 or golpe.get('pareja') == 'culatazo', golpe)
    check('tanda B: el último tiro sonó con un 7,62 por distancia', str(P('last_shot_sound')) in ('cerca', 'media', 'lejos'), P('last_shot_sound'))
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
    # tanda 47b: junto a la emisora, con la base tranquila, se oye como si estuvieras al lado
    em = P('emisora_loc'); h0 = P('tap_lines_heard'); f0 = d.facts_known()
    tp(em.x + 150, em.y); yield 0.3
    check('junto a la emisora y sin alarma estás a la escucha', d.at_emisora(), '%s base %s' % (d.at_emisora(), d.base_state()))
    yield ('hasta', lambda: director().get_editor_property('tap_lines_heard') > h0 or director().get_editor_property('talk_idx') < 0, P('talk_line_seconds') * 2 + 6.0)
    check('desde la emisora oyes la frase aunque hablen lejos', P('tap_lines_heard') > h0 and any('EMISORA' in str(x) for x in list(P('subtitle_log'))[-3:]), '%s %s' % (P('tap_lines_heard'), list(P('subtitle_log'))[-2:]))
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
    d.set_darts(0)
    d.set_editor_property('aim_held', True); yield 0.6
    check('sin dardos no se apunta', P('aim_alpha') < 0.01 and abs(cam.get_editor_property('field_of_view') - f0) < 0.5 and not d.can_aim(), '%.2f %.1f' % (P('aim_alpha'), cam.get_editor_property('field_of_view')))
    d.set_darts(3); yield 0.8
    check('con dardos, el botón derecho cierra la vista', P('aim_alpha') > 0.95 and abs(cam.get_editor_property('field_of_view') - P('aim_fov')) < 1.0, '%.2f %.1f' % (P('aim_alpha'), cam.get_editor_property('field_of_view')))
    check('apuntando al aire la mira no marca a nadie', d.dart_aim() is None)
    d.set_editor_property('aim_held', False); yield 0.8
    check('al soltar, la vista vuelve', P('aim_alpha') < 0.01 and abs(cam.get_editor_property('field_of_view') - f0) < 0.5, '%.2f %.1f frente a %.1f' % (P('aim_alpha'), cam.get_editor_property('field_of_view'), f0))
    d.set_editor_property('aim_held', True); yield 0.6
    d.toggle_binoculars(); yield 0.3
    d.toggle_binoculars(); d.set_editor_property('aim_held', False); yield 0.8
    check('prismáticos mientras apuntas: al bajar todo, la vista es la de antes', abs(cam.get_editor_property('field_of_view') - f0) < 0.5, cam.get_editor_property('field_of_view'))
    d.set_darts(d0)

def prueba_tercera():
    """Tanda 47. La G pasa a tercera persona: la cámara se va detrás del hombro (sin atravesar paredes), se ve el cuerpo de
    Cuttlas y se esconden los brazos; otra vez la G y todo vuelve. Con los prismáticos la vista es la de siempre."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    cam = jugador().get_component_by_class(unreal.CameraComponent)
    # lo que dejen las pruebas de antes: de pie y sin asomarse (si no, la camara aun se mueve y la animacion es la de agachado)
    d.simulate_key('Z', False, True); d.simulate_key('V', False, True)
    if jugador().get_editor_property('is_crouched'): jugador().un_crouch()
    aparte(); yield 1.0
    check('Cuttlas tiene cuerpo (modelo importado)', d.hero_ready())
    c0 = cam.get_world_location()
    d.toggle_third(); yield 0.8
    c1 = cam.get_world_location(); off = d.third_cam_offset()
    lejos = math.sqrt((c1.x - c0.x) ** 2 + (c1.y - c0.y) ** 2 + (c1.z - c0.z) ** 2)
    check('la G saca la cámara detrás del hombro', d.third_now() and P('third_alpha') > 0.95 and 150 < lejos < 300, '%.0f cm, alfa %.2f' % (lejos, P('third_alpha')))
    check('se ve el cuerpo y no los brazos', d.hero_shown() and (not d.hero_ready() or d.hero_anim_index() == 0), '%s anim %s' % (d.hero_shown(), d.hero_anim_index()))
    pc = unreal.GameplayStatics.get_player_controller(mundo(), 0)
    for k in range(8):
        pc.set_control_rotation(unreal.Rotator(0.0, 0.0, 45.0 * k)); yield 0.15
    pc.set_control_rotation(unreal.Rotator(0.0, 0.0, 0.0)); yield 0.3
    if d.hero_uses_gasp():
        # tanda A, séptima: parado, girar la cámara 160 grados; las piernas lo siguen girando en el sitio (WantsToAim un
        # momento, TarsisGaspTurn.h) y no se quedan atrás hasta el primer paso
        yield 1.5
        pc.set_control_rotation(unreal.Rotator(0.0, 0.0, 160.0))
        apunto, alineado = False, False
        for _ in range(30):
            yield 0.1
            apunto = apunto or d.hero_gasp_turn_aiming()
            if apunto and abs(d.hero_gasp_turn_delta()) < 20:
                alineado = True
                break
        check('parado, al girar 160 grados las piernas siguen a la cámara', apunto and alineado and jugador().get_velocity().length() < 10,
              'WantsToAim %s, desfase %.0f grados' % (apunto, d.hero_gasp_turn_delta()))
        yield 1.0
        check('el giro no deja puesto WantsToAim', not d.hero_gasp_turn_aiming(), d.hero_gasp_turn_aiming())
        pc.set_control_rotation(unreal.Rotator(0.0, 0.0, 0.0)); yield 1.5
    # tanda A, octava: al agacharse y levantarse en tercera, ni la cámara ni el cuerpo dan un salto de un fotograma (antes la
    # cámara bajaba 55 cm de golpe y el cuerpo salía 54 cm más alto el primer fotograma agachado)
    cm = unreal.GameplayStatics.get_player_camera_manager(mundo(), 0)
    cuerpo = ([c for c in jugador().get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name().startswith('CuerpoCuttlas')] or [None])[0]
    def saltos(accion):
        prev, cam_max, pel_max = None, 0.0, 0.0
        t0 = time.time()
        accion()
        while time.time() - t0 < 0.7:
            yield 0.0
            z = (cm.get_camera_location().z, cuerpo.get_socket_location('pelvis').z if cuerpo else 0.0)
            if prev:
                cam_max = max(cam_max, abs(z[0] - prev[0])); pel_max = max(pel_max, abs(z[1] - prev[1]))
            prev = z
        res.append((cam_max, pel_max))
    res = []
    yield from saltos(lambda: jugador().crouch())
    check('agachado, la animación es la de ir agachado', not d.hero_ready() or d.hero_anim_index() == 2, d.hero_anim_index())
    yield from saltos(lambda: jugador().un_crouch())
    check('agacharse y levantarse en tercera, sin saltos de un fotograma', all(c < 20 and p < 20 for c, p in res),
          'máximo por fotograma: cámara %.1f / %.1f cm, pelvis %.1f / %.1f cm' % (res[0][0], res[1][0], res[0][1], res[1][1]))
    yield 0.4
    d.toggle_binoculars(); yield 0.6
    check('con los prismáticos, la vista de siempre', not d.third_now() and P('third_alpha') < 0.05, P('third_alpha'))
    d.toggle_binoculars(); yield 0.6
    d.toggle_third(); yield 0.8
    c2 = cam.get_world_location()
    vuelve = math.sqrt((c2.x - c0.x) ** 2 + (c2.y - c0.y) ** 2 + (c2.z - c0.z) ** 2)
    check('otra vez la G: la cámara vuelve a su sitio exacto tras girar una vuelta entera', not d.third_now() and not d.hero_shown() and vuelve < 3.0, '%.1f cm' % vuelve)

def prueba_perro():
    """Tanda 46. El perro del hangar ronda entre dos puntas; no ve, huele: a menos de DogSmell gruñe (aviso, sin ladrar),
    si no te apartas ladra y llama a los guardias de cerca, y si te vas se calla. Con el hueso de la olla se le puede dar
    desde DogGiveDist: se sienta, queda amigo y ya no ladra. Al capturarte vuelve a su ronda."""
    d = director()
    P = lambda k: d.get_editor_property(k)
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 1.0
    # tanda B: es un lobo (Animal Variety Pack) con nueve animaciones; sin el pack, el perro de antes con cuatro
    check('el lobo está en el hangar (con sus nueve animaciones; o el perro de antes con cuatro)', d.dog_ready() and d.dog_anim_count() == (9 if P('dog_wolf') else 4), '%s lobo %s, %s animaciones, giro %.0f' % (d.dog_ready(), P('dog_wolf'), d.dog_anim_count(), P('dog_mesh_yaw')))
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

def prueba_fusil():
    """Tanda B. Los guardias llevan un M14 en la mano derecha, con la pose de fusil de Lyra de cintura para arriba, y
    los tiros salen de la boca del cañón (socket Muzzle)."""
    yield ('hasta', lambda: all(estado(x) == 'PATROL' for x in guardias() if not x.get_editor_property('tower_sentry')), 30.0)
    yield 2.0
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry')]
    con = [g for g in ronda if g.has_rifle()]
    check('los guardias de ronda llevan fusil', len(con) == len(ronda) and len(ronda) > 0, '%d de %d' % (len(con), len(ronda)))
    pose = [g for g in con if g.rifle_pose_weight() > 0.9]
    check('y lo sujetan con la pose de fusil', len(pose) == len(con), ['%s %.2f' % (g.get_actor_label(), g.rifle_pose_weight()) for g in con if g.rifle_pose_weight() <= 0.9][:4])
    mal = []
    for g in con:
        m, l, f = g.rifle_muzzle(), g.get_actor_location(), g.get_actor_forward_vector()
        dl = math.hypot(m.x - l.x, m.y - l.y)
        delante = (m.x - l.x) * f.x + (m.y - l.y) * f.y
        if dl > 150 or delante < -10 or not (l.z - 60 < m.z < l.z + 120):
            mal.append('%s %.0f cm, delante %.0f, z %+.0f' % (g.get_actor_label(), dl, delante, m.z - l.z))
    check('la boca del cañón, delante del guardia y a la altura de la cadera o el pecho', not mal, mal[:4])
    # tanda C: andando, el fusil se mece con el paso (no un maniquí rígido)
    yield ('hasta', lambda: any(g.rifle_sway() > 0.5 for g in con), 10.0)
    check('tanda C: andando, el fusil se mece con el paso', any(g.rifle_sway() > 0.5 for g in con), [round(g.rifle_sway(), 2) for g in con][:6])
    # tanda C: a la cadera, la culata bajo la axila (no el fusil al pecho con los brazos estirados)
    cad = [g for g in con if not g.rifle_aiming()]
    lejos = ['%s %.0f' % (g.get_actor_label(), (g.rifle_butt() - g.rifle_shoulder()).length()) for g in cad if (g.rifle_butt() - g.rifle_shoulder()).length() > 30]
    check('tanda C: a la cadera, la culata pegada al cuerpo bajo el hombro', cad and not lejos, lejos[:4])
    # tanda C: apuntando, la culata al hombro y el cañón recto a la altura de la cara
    g = con[0]
    l = g.get_actor_location(); f = g.get_actor_forward_vector()
    g.alarm(V(l.x + f.x * 900, l.y + f.y * 900, l.z))
    yield ('hasta', lambda: g.rifle_aiming() and g.rifle_pose_weight() > 0.95, 6.0)
    yield 1.0
    b, s, m, l = g.rifle_butt(), g.rifle_shoulder(), g.rifle_muzzle(), g.get_actor_location()
    check('tanda C: apuntando, la culata al hombro', g.rifle_aiming() and (b - s).length() < 16, '%s a %.1f cm del hombro' % (g.get_actor_label(), (b - s).length()))
    check('y el cañón recto, a la altura de la cara', abs(m.z - b.z) < 18 and m.z - l.z > 35, 'boca %+.0f sobre la culata, %+.0f sobre el actor' % (m.z - b.z, m.z - l.z))

def prueba_centinela():
    """Tanda C. Los centinelas de las torres llevan el M14 como los de ronda y, si huyes a tiro, te disparan desde la torre:
    el fogonazo sale de la boca de su fusil."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    yield 1.0
    ts = [g for g in guardias() if g.get_editor_property('tower_sentry')]
    check('los centinelas de las torres llevan el M14', len(ts) > 0 and all(g.has_rifle() for g in ts), '%d de %d' % (len([g for g in ts if g.has_rifle()]), len(ts)))
    mal = ['%s %.0f' % (g.get_actor_label(), (g.rifle_muzzle() - g.get_actor_location()).length()) for g in ts if (g.rifle_muzzle() - g.get_actor_location()).length() > 160]
    check('con el fusil en las manos (la boca junto a ellos, arriba en la torre)', not mal, mal[:4])
    vig = [g for g in ts if 'centinela' in g.get_actor_label().lower()] or ts
    g = vig[0]
    d.set_day(True)
    d.set_editor_property('armed_rule', True)
    d.set_editor_property('armed_aim', 0.0)   # que falle: aqui solo se mira que dispare y desde donde
    d.test_tower_fire(True)
    l = g.get_actor_location(); f = g.get_actor_forward_vector()
    tp(l.x + f.x * 1100, l.y + f.y * 1100)
    mirar(V(l.x, l.y, l.z)); yield 0.3
    t0 = g.get_editor_property('tower_shots')
    yield ('hasta', lambda: g.get_editor_property('tower_shots') > t0, 15.0)
    check('si huyes a tiro, el centinela te dispara desde la torre', g.get_editor_property('tower_shots') > t0, '%s: %d tiros, estado %s' % (g.get_actor_label(), g.get_editor_property('tower_shots'), estado(g)))
    check('el tiro sale de la boca de su fusil (sonido 7,62)', str(P('last_shot_sound')) in ('cerca', 'media', 'lejos'), P('last_shot_sound'))
    d.test_tower_fire(False)
    d.set_editor_property('armed_rule', False)
    d.set_editor_property('armed_aim', 1.0)
    d.set_day(False)
    aparte()

def prueba_fisica():
    """Tanda C. Fisica de los guardias: un golpe se nota (reaccion de Lyra segun de donde viene y la cintura para arriba con
    fisica que se apaga sola); el dardo, tras la reaccion, los tumba con ragdoll y se quedan en reposo; el cuerpo se
    arrastra con fisica de los hombros; al despertar pasan de la fisica a la animacion mezclando; y solo cerca del
    jugador (los de lejos caen con la animacion de siempre)."""
    d = director()
    yield ('hasta', lambda: len([x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL']) >= 3, 30.0)
    ronda = [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and x.uses_gasp()]
    check('hay guardias del GASP de ronda', len(ronda) >= 3, len(ronda))
    if len(ronda) < 3:
        return
    for x in guardias():
        x.hold(3600.0)
        x.set_editor_property('view_distance', 1.0)
    g, h, k = ronda[0], ronda[1], ronda[2]
    suelo = lambda x: x.get_actor_location().z - x.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
    # 1. el golpe: viene de frente (el golpe viaja hacia atras)
    detras_de(g, 260); yield 0.3
    f = g.get_actor_forward_vector()
    g.hit_react(V(-f.x, -f.y, 0.0), True); yield 0.12
    check('un golpe: reaccion de Lyra segun de donde viene', g.hit_reacting() and 'HitReact_Front' in str(g.last_hit_anim()), g.last_hit_anim())
    check('y de cintura para arriba, cuerpos con fisica (que se van apagando)', g.physics_active() and g.hit_physics_weight() > 0.05, '%.2f' % g.hit_physics_weight())
    yield 2.0
    check('se le pasa solo: vuelve a la animacion de siempre', not g.hit_reacting() and not g.physics_active() and estado(g) != 'DOWN', '%s %s %s' % (g.hit_reacting(), g.physics_active(), estado(g)))
    # 2. el dardo: primero la reaccion, luego cae con ragdoll y se queda quieto
    detras_de(h, 500); yield 0.3
    f = h.get_actor_forward_vector()
    h.set_editor_property('knock_out_time', 100.0)
    h.dart_hit(V(f.x, f.y, 0.0)); h.knock_out(); yield 0.1
    check('dardo: primero la reaccion', h.hit_reacting() and not h.is_ragdoll(), '%s %s' % (h.hit_reacting(), h.is_ragdoll()))
    yield 0.6
    check('y cae con ragdoll (no un corte a la pose tumbada)', h.is_ragdoll() and estado(h) == 'DOWN', '%s %s' % (h.is_ragdoll(), estado(h)))
    yield 4.0
    pz = h.pelvis_location().z - suelo(h)
    check('en el suelo, en reposo', pz < 35, 'pelvis a %.0f cm del suelo' % pz)
    check('la capsula le sigue (los demas lo encuentran donde cayo)', dist2d(h.get_actor_location(), h.pelvis_location()) < 15, '%.0f cm' % dist2d(h.get_actor_location(), h.pelvis_location()))
    # 3. arrastrarlo: de los hombros, con fisica
    junto_a(h); yield 0.3
    check('se puede arrastrar', 'ARRASTRAR' in str(d.interact_prompt()), d.interact_prompt())
    d.interact(); yield 0.3
    check('se arrastra con fisica (de los hombros, no rigido)', d.drag_physics(), d.get_editor_property('dragged'))
    p0 = h.pelvis_location()
    pl = jugador(); s = pl.get_actor_location()
    dx, dy = s.x - p0.x, s.y - p0.y
    n = max(1.0, math.hypot(dx, dy)); dx, dy = dx / n, dy / n
    for i in range(16):
        pl.set_actor_location(V(s.x + dx * 22 * (i + 1), s.y + dy * 22 * (i + 1), s.z), True, False)
        unreal.GameplayStatics.get_player_controller(mundo(), 0).set_control_rotation(unreal.Rotator(0.0, 0.0, math.degrees(math.atan2(dy, dx))))
        yield 0.1
    yield 0.8
    p1 = h.pelvis_location()
    check('el cuerpo te sigue', dist2d(p0, p1) > 150, '%.0f cm' % dist2d(p0, p1))
    check('a rastras: la pelvis junto al suelo (las piernas arrastran)', p1.z - suelo(h) < 45, '%.0f cm' % (p1.z - suelo(h)))
    d.interact(); yield 0.3
    check('se suelta con la E', not d.drag_physics() and d.get_editor_property('dragged') is None, d.get_editor_property('dragged'))
    # 4. despertar: de la fisica a la animacion, mezclando
    h.wake_now(); yield 0.1
    check('al despertar, de la pose tumbada a la animada mezclando', not h.is_ragdoll() and h.wake_blending(), '%s %s' % (h.is_ragdoll(), h.wake_blending()))
    check('tanda D: se levanta pasando por agachado (boca arriba o abajo)', h.getting_up() and h.get_editor_property('is_crouched'), 'boca %s, agachado %s' % ('arriba' if h.last_face_up() else 'abajo', h.get_editor_property('is_crouched')))
    yield 1.5
    check('y de pie', estado(h) != 'DOWN' and not h.wake_blending() and h.pelvis_location().z - suelo(h) > 70, '%s, pelvis a %.0f cm' % (estado(h), h.pelvis_location().z - suelo(h)))
    # 5. lejos del jugador, sin fisica (la animacion de siempre)
    aparte(); yield 0.3
    k.set_editor_property('knock_out_time', 100.0)
    k.knock_out(); yield 0.5
    check('lejos del jugador, cae sin fisica (ahorro)', estado(k) == 'DOWN' and not k.is_ragdoll(), '%s %s' % (estado(k), k.is_ragdoll()))
    # tanda D: los cuerpos de los de cerca, ya creados antes de hacer falta (sin tiron al arrancar la fisica)
    calientes = [x for x in guardias() if x.uses_gasp() and x.physics_warmed()]
    check('tanda D: fisica precalentada en los de cerca', len(calientes) >= 2, ['%s %.1f ms' % (x.get_actor_label(), x.get_editor_property('phys_warm_ms')) for x in calientes][:4])
    k.wake_now()
    for x in guardias():
        x.hold(0.0)
        x.set_editor_property('view_distance', 2000.0)

def prueba_lobo_piedra():
    """Tanda B. El lobo amigo va a por la piedra que tiras (Q) si cae a menos de DogFetchRadius, la coge con la boca, te la
    trae y la suelta a tus pies. Los guardias siguen yendo a mirar el ruido de la piedra."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    if not d.dog_ready():
        yield 1.0
    check('el lobo está', d.dog_ready())
    if not d.dog_ready():
        return
    d.set_flag('perro_amigo'); yield 0.5
    check('amigo', P('dog_state') == 3, P('dog_state'))
    hg = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))['ext']['hangar']
    cx, cy = (hg['x0'] + hg['x1']) * 50, (hg['y0'] + hg['y1']) * 50
    l = d.dog_location()
    # a tu lado, tiras hacia el centro del hangar, un poco hacia abajo (cae a unos 5 m)
    px, py = l.x + (cx - l.x) * 0.15, l.y + (cy - l.y) * 0.15 - 250
    tp(px, py)
    yaw = math.degrees(math.atan2(cy - py, cx - px))
    unreal.GameplayStatics.get_player_controller(mundo(), 0).set_control_rotation(unreal.Rotator(0.0, -20.0, yaw))
    yield 0.3
    f0 = P('dog_fetches')
    for x in guardias():
        x.hold(3600.0)   # que nadie venga a por ti por el ruido de la piedra mientras el lobo la trae
    d.throw_stone(); yield 0.3
    caida = d.get_editor_property('last_stone')
    # tanda C: una piedra de verdad (SM_Piedra, unos 9 cm), que se vea en la boca del lobo
    tam = d.last_stone_size()
    # tanda E2: es la caja del actor, alineada con el mundo: girada, una piedra de 10 cm da hasta unos 13
    check('tanda C: la piedra es una piedra de verdad, de unos 9 cm', str(d.last_stone_mesh()) == 'SM_Piedra' and 7.0 <= max(tam.x, tam.y, tam.z) <= 13.5, '%s %.1f x %.1f x %.1f cm' % (d.last_stone_mesh(), tam.x, tam.y, tam.z))
    check('la piedra cae a su alcance', math.hypot(caida.x - l.x, caida.y - l.y) < P('dog_fetch_radius'), '%.0f cm' % math.hypot(caida.x - l.x, caida.y - l.y))
    check('sale corriendo a por ella', P('dog_fetch') == 1 and d.dog_anim_index() == 4, '%s anim %s' % (P('dog_fetch'), d.dog_anim_index()))
    vistos = {'boca': False, 'lejos_boca': 999.0}
    def mira():
        if d.dog_carrying():
            vistos['boca'] = True
            dl = d.dog_location(); s = d.dog_stone_location()
            vistos['lejos_boca'] = min(vistos['lejos_boca'], math.hypot(s.x - dl.x, s.y - dl.y))
        return director().get_editor_property('dog_fetches') > f0
    yield ('hasta', mira, 20.0)
    check('la coge con la boca y te la trae', vistos['boca'] and P('dog_fetches') == f0 + 1, '%s, %s traidas' % (vistos, P('dog_fetches')))
    pl = jugador().get_actor_location()
    dl = d.dog_location()
    check('la suelta a tus pies (y él se queda a tu lado)', math.hypot(dl.x - pl.x, dl.y - pl.y) < 260, '%.0f cm' % math.hypot(dl.x - pl.x, dl.y - pl.y))
    check('y ya no la lleva', not d.dog_carrying() and P('dog_fetch') == 0, P('dog_fetch'))
    for x in guardias():
        x.hold(0.0)
    # lejos de él no va
    lejos = d.dog_location()
    tp(lejos.x, lejos.y - 200)
    unreal.GameplayStatics.get_player_controller(mundo(), 0).set_control_rotation(unreal.Rotator(0.0, 25.0, -90.0))
    d.set_editor_property('dog_fetch_radius', 100.0)
    yield 1.6
    d.throw_stone(); yield 0.5
    check('si cae lejos (más que DogFetchRadius) no va', P('dog_fetch') == 0, P('dog_fetch'))
    d.set_editor_property('dog_fetch_radius', 2500.0)

def prueba_lobo_paso():
    """Tanda C. El lobo pasa de una animacion a otra mezclando (sin saltos) y anda al paso de la animacion (sin patinar):
    la velocidad de reproduccion sale de lo que avanza de verdad entre lo que avanza la animacion."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    aparte(); yield 1.0
    if not d.dog_ready():
        check('el lobo esta', False)
        return
    yield ('hasta', lambda: d.dog_anim_index() == 1 and d.dog_speed2d() > 40, 15.0)
    yield 0.6
    r = d.dog_play_rate()
    check('andando, al paso de la animacion (velocidad de reproduccion cerca de 1)', P('dog_state') != 3 and 0.75 <= r <= 1.35, 'anim %s, %.0f cm/s, rate %.2f' % (d.dog_anim_index(), d.dog_speed2d(), r))
    vio = {'mezcla': False}
    def mira():
        vio['mezcla'] = vio['mezcla'] or d.dog_blending()
        return d.dog_anim_index() != 1
    yield ('hasta', mira, 20.0)
    check('al cambiar de animacion, mezcla (sin saltos)', vio['mezcla'], 'anim %s' % d.dog_anim_index())

def prueba_lobo_caricia():
    """Tanda B. Un guardia tranquilo que ve al lobo amigo cerca cree que es un perro suelto: le habla, va, se agacha y lo
    acaricia unos segundos (mirando al suelo: ve mucho menos) y vuelve a su ronda; no repite hasta DogPetCooldown. El
    lobo se queda quieto mientras. Uno en alerta no lo acaricia."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    d.set_flag('perro_amigo')
    aparte()
    yield 1.0
    check('el lobo amigo está', d.dog_ready() and P('dog_state') == 3, P('dog_state'))
    if not d.dog_ready():
        return
    d.set_editor_property('dog_pet_seconds', 6.0)
    d.dog_forget_pets()
    yield ('hasta', lambda: any(estado(x) == 'PATROL' and not x.get_editor_property('tower_sentry') for x in guardias()), 20.0)
    # uno en alerta, al lado del lobo: no lo acaricia
    l = d.dog_location()
    libres = [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and not x.is_petting()]
    a = libres[0]
    a.alarm(V(l.x + 3000, l.y, l.z))
    yield 0.3
    a.set_actor_location(V(l.x + 200, l.y, a.get_actor_location().z), False, True)
    yield 2.0
    check('uno en alerta no lo acaricia', not a.is_petting() and d.dog_petter() != a, '%s %s' % (estado(a), a.is_petting()))
    # uno tranquilo, a 2,5 m
    g = None
    for x in guardias():
        if x != a and not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and not x.is_on_errand():
            g = x
            break
    check('hay un guardia tranquilo', g is not None)
    if g is None:
        return
    l = d.dog_location()
    g.set_actor_location(V(l.x - 250, l.y, g.get_actor_location().z), False, True)
    yield ('hasta', lambda: d.dog_petter() is not None, 3.0)
    p = d.dog_petter()
    check('un guardia tranquilo que lo ve va a acariciarlo', p is not None and p.is_petting(), p.get_actor_label() if p else None)
    if p is None:
        return
    check('y le dice algo al «chucho»', str(P('last_voice')).endswith('_lobo'), P('last_voice'))
    yield ('hasta', lambda: p.pet_crouched(), 12.0)
    yield 0.3   # el agachado del CharacterMovement llega un fotograma después
    l0 = d.dog_location()
    check('llega, se agacha y lo acaricia', p.pet_crouched() and p.get_editor_property('is_crouched'), '%s %s' % (p.pet_crouched(), p.get_editor_property('is_crouched')))
    check('al lado del lobo', math.hypot(p.get_actor_location().x - l0.x, p.get_actor_location().y - l0.y) < 180, '%.0f cm' % math.hypot(p.get_actor_location().x - l0.x, p.get_actor_location().y - l0.y))
    yield 2.0
    l1 = d.dog_location()
    check('el lobo se queda quieto mientras (tanda C: de pie, dejandose)', math.hypot(l1.x - l0.x, l1.y - l0.y) < 5 and d.dog_anim_index() in (0, 2, 3), '%.0f cm, anim %s' % (math.hypot(l1.x - l0.x, l1.y - l0.y), d.dog_anim_index()))
    mano = (p.left_hand_location() - d.dog_back_location()).length()
    check('tanda C: con la mano sobre el lomo', p.pet_hand_weight() > 0.9 and mano < 30, 'mano a %.0f cm del lomo, peso %.2f' % (mano, p.pet_hand_weight()))
    check('tanda D: con el fusil a la espalda (no vertical en la mano)', p.rifle_on_back(), p.rifle_on_back())
    check('tanda C: y el lobo mueve la cola', d.dog_wagging() > 0.5, '%.2f' % d.dog_wagging())
    yield ('hasta', lambda: not p.is_petting(), 8.0)
    yield 0.3
    check('a los seis segundos se levanta y vuelve a su ronda', not p.is_petting() and not p.get_editor_property('is_crouched') and not p.is_on_errand() and estado(p) in ('PATROL', 'RETURN'), 'acaricia %s agachado %s recado %s %s' % (p.is_petting(), p.get_editor_property('is_crouched'), p.is_on_errand(), estado(p)))
    n = P('dog_pets')
    l = d.dog_location()
    p.set_actor_location(V(l.x - 250, l.y, p.get_actor_location().z), False, True)
    yield 2.0
    check('no repite enseguida (DogPetCooldown)', d.dog_petter() != p, d.dog_petter().get_actor_label() if d.dog_petter() else None)

def prueba_huellas():
    """Tanda D. Huellas: en el barro y los charcos (y la hierba con lluvia) Cuttlas deja huellas que se borran solas;
    agachado, mas tenues; en suelo duro, ninguna, salvo las pisadas mojadas al salir de un charco. Un guardia tranquilo
    que ve una huella fresca con luz sigue el rastro en orden y, en la ultima, busca. Las del lobo no alarman."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.5
    d.set_day(True)
    yield 0.5
    n = d.soft_patch_count()
    check('hay suelo blando (barro y charcos de las tandas 22 y 23)', n > 10, n)
    barro = [d.soft_patch_center(i) for i in range(n) if not d.soft_patch_water(i) and not d.soft_patch_rain(i)]
    agua = [d.soft_patch_center(i) for i in range(n) if d.soft_patch_water(i) and not d.soft_patch_rain(i)]
    agua = [c for c in agua if dist2d(c, d.get_editor_property('valve_loc')) > 500]   # tanda F: el del gasoil, oculto hasta abrir la llave
    check('barro y agua sin lluvia', len(barro) > 0 and len(agua) > 0, '%d barro, %d agua' % (len(barro), len(agua)))
    if not barro or not agua:
        return
    m0 = P('prints_made')
    b = barro[0]
    d.test_footstep(V(b.x, b.y, b.z), 0.0, False)
    check('en el barro queda una huella', P('prints_made') == m0 + 1 and str(P('last_print_kind')) == 'blando' and d.print_fade(0) > 0.9, '%s %s %.2f' % (P('prints_made') - m0, P('last_print_kind'), d.print_fade(0)))
    d.test_footstep(V(b.x + 10, b.y, b.z), 0.0, True)
    check('agachado, mas tenue', 0.2 < d.print_fade(0) < 0.6, '%.2f' % d.print_fade(0))
    # suelo duro (la losa del patio central)
    m1 = P('prints_made')
    d.test_footstep(V(4300, 3500, 2), 0.0, False)
    check('en suelo duro (y seco), ninguna', P('prints_made') == m1 and str(P('last_print_kind')) == 'duro', '%s %s' % (P('prints_made') - m1, P('last_print_kind')))
    # el charco: al salir, pisadas mojadas que se van secando
    a = agua[0]
    d.test_footstep(V(a.x, a.y, a.z), 0.0, False)
    check('en el agua no queda huella, pero sales mojado', str(P('last_print_kind')) == 'agua' and P('wet_steps_left') == P('print_wet_steps'), '%s %s' % (P('last_print_kind'), P('wet_steps_left')))
    d.test_footstep(V(4300, 3500, 2), 0.0, False)
    f1 = d.print_fade(0)
    for k in range(8):
        d.test_footstep(V(4300 + 70 * (k + 1), 3500, 2), 0.0, False)
    f9 = d.print_fade(0)
    check('al salir del charco, pisadas mojadas en lo duro que se van secando', str(P('last_print_kind')) == 'mojada' and f1 > f9 > 0.0, '%.2f > %.2f' % (f1, f9))
    for k in range(20):
        d.test_footstep(V(5000 + 70 * k, 3500, 2), 0.0, False)
    check('a las veinte pisadas ya no deja agua', str(P('last_print_kind')) == 'duro' and P('wet_steps_left') == 0, P('last_print_kind'))
    # se borran
    d.test_age_prints(P('print_life'))
    yield 0.8
    check('se borran a los tres minutos', d.prints_active() == 0 and d.print_fade(0) == 0.0, '%d activas' % d.prints_active())
    check('un anillo fijo de calcomanias (no crece)', 0 < d.print_decal_count() <= P('print_pool'), '%d de %d' % (d.print_decal_count(), P('print_pool')))
    # el rastro: sale de un charco y cruza el patio; un guardia de ronda delante lo ve y lo sigue
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry') and estado(g) == 'PATROL']
    g = ronda[0]
    s0, t0 = P('tracks_started'), P('tracks_finished')
    # un sitio despejado: desde el barro, la primera direccion sin nada en 4,5 m por detras (el guardia) ni 10 m por
    # delante (el rastro). Tanda D: en (4300, 3800) el rastro caia dentro de la caja de colision de un contenedor
    def _libre(p0, p1):
        return unreal.SystemLibrary.line_trace_single(mundo(), p0, p1, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [g, jugador()], unreal.DrawDebugTrace.NONE, True) is None
    rumbo = None
    for c in barro:
        for yaw in range(0, 360, 30):
            f = unreal.MathLibrary.get_forward_vector(unreal.Rotator(0, 0, yaw))
            if _libre(V(c.x - f.x * 420, c.y - f.y * 420, c.z + 60), V(c.x + f.x * 950, c.y + f.y * 950, c.z + 60)):
                rumbo = (c, yaw, f)
                break
        if rumbo:
            break
    check('hay un sitio despejado para el rastro', rumbo is not None, '(%.0f, %.0f) rumbo %d' % (rumbo[0].x, rumbo[0].y, rumbo[1]) if rumbo else None)
    if rumbo is None:
        return
    b0 = b
    b, yaw, f = rumbo
    # sale de un charco (botas mojadas), pisa el barro y sigue por lo duro: las primeras de barro, luego mojadas
    d.test_footstep(V(a.x, a.y, a.z), 0.0, False)
    for k in range(14):
        lado = 12 if k % 2 else -12
        d.test_footstep(V(b.x + f.x * 65 * k - f.y * lado, b.y + f.y * 65 * k + f.x * lado, b.z + 2), yaw, False)
    # de ronda: su recorrido le lleva por encima del rastro (si se le gira a mano, la ronda lo vuelve a girar)
    pts0 = list(g.get_editor_property('patrol_points'))
    gz = b.z + 88.0
    g.set_editor_property('patrol_points', [V(b.x + f.x * 1500, b.y + f.y * 1500, gz), V(b.x + f.x * 1500 + 20, b.y + f.y * 1500, gz)])
    g.set_actor_location(V(b.x - f.x * 380, b.y - f.y * 380, b.z + 95), False, True)
    g.set_actor_rotation(unreal.Rotator(0, 0, yaw), False)
    g.hold(0.0)
    for k in range(12):
        yield 1.0
        if P('tracks_started') > s0:
            break
        unreal.log('[Pruebas] traza huellas %d: %s' % (k, d.print_sight_why(g)))
    check('un guardia ve las huellas y sigue el rastro', P('tracks_started') == s0 + 1 and g.get_editor_property('tracking_prints'), '%s, %s' % (P('tracks_started') - s0, P('last_track_guard')))
    check('lo dice', 'huellas' in str(P('last_voice')), P('last_voice'))
    yield ('hasta', lambda: director().get_editor_property('tracks_finished') > t0, 90.0)
    check('las sigue en orden hasta la ultima y se pone a buscar', P('tracks_finished') == t0 + 1 and P('track_steps') >= 3 and estado(g) in ('SUSPICIOUS', 'SEARCH'), '%d pasos, %s' % (P('track_steps'), estado(g)))
    g.set_editor_property('patrol_points', pts0)
    # las del lobo: el perro, no alarman
    for x in guardias():
        x.hold(3600.0)
    d.test_age_prints(P('print_life'))   # las del rastro, borradas: que solo queden las del lobo
    b = b0
    yield 0.6
    w0, s1 = P('wolf_prints_seen'), P('tracks_started')
    h = ronda[1]
    for k in range(6):
        d.test_wolfstep(V(b.x + 40 * k, b.y, b.z), 0.0)
    h.set_actor_location(V(b.x - 350, b.y, h.get_actor_location().z), False, True)
    h.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
    h.hold(0.0)
    yield ('hasta', lambda: director().get_editor_property('wolf_prints_seen') > w0, 10.0)
    check('las huellas del lobo: el perro, no las sigue', P('wolf_prints_seen') > w0 and P('tracks_started') == s1, '%d vistas, %d rastros' % (P('wolf_prints_seen') - w0, P('tracks_started') - s1))
    for x in guardias():
        x.hold(0.0)
    d.set_day(False)

def _pasillo(w, ancho_max=150.0, largo=700.0):
    """Un pasillo de verdad del nivel: tramo recto de `largo` cm con pared a los dos lados (menos de ancho_max entre
    ellas) y sin nada en medio. Devuelve (inicio, fin, ancho) o None."""
    def h(a, b):
        r = unreal.SystemLibrary.line_trace_single(w, a, b, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [jugador()] + list(guardias()), unreal.DrawDebugTrace.NONE, True)
        return r.to_tuple()[3] if r else None    # distancia
    for eje in ((1, 0), (0, 1)):
        lado = (-eje[1], eje[0])
        for x in range(-1500, 9000, 100):
            for y in range(-1500, 7400, 100):
                p = V(x, y, 60)
                d1, d2 = h(p, V(x + lado[0] * 100, y + lado[1] * 100, 60)), h(p, V(x - lado[0] * 100, y - lado[1] * 100, 60))
                if d1 is None or d2 is None or d1 + d2 > ancho_max or d1 < 35 or d2 < 35:
                    continue
                fin = V(x + eje[0] * largo, y + eje[1] * largo, 60)
                if h(p, fin) is not None:
                    continue
                ok = True
                for k in range(1, int(largo / 100) + 1):
                    q = V(x + eje[0] * k * 100, y + eje[1] * k * 100, 60)
                    a, b = h(q, V(q.x + lado[0] * 100, q.y + lado[1] * 100, 60)), h(q, V(q.x - lado[0] * 100, q.y - lado[1] * 100, 60))
                    if a is None or b is None or a + b > ancho_max or a < 35 or b < 35:
                        ok = False
                        break
                if ok and abs(suelo_z(w, p) - suelo_z(w, fin)) < 30:
                    return p, fin, d1 + d2
    return None

def suelo_z(w, p):
    r = unreal.SystemLibrary.line_trace_single(w, V(p.x, p.y, p.z + 100), V(p.x, p.y, p.z - 300), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    return r.to_tuple()[4].z if r else p.z

def prueba_paso():
    """Tanda E2. Al cruzarse no se atraviesan: la cápsula bloquea a las personas (salvo tumbado), en ancho se esquivan con
    el RVO y en estrecho uno se arrima, espera y da paso con el brazo. El jugador choca con los de pie y no con los
    tumbados; el lobo rodea a la gente; el relevo y el centinela se paran a su distancia."""
    w = mundo()
    d = director()
    P = lambda k: director().get_editor_property(k)
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry') and not g.get_actor_label().endswith('Ramos')]
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.5
    a, b = ronda[0], ronda[1]
    check('las cápsulas de los de pie bloquean a las personas (y tienen RVO)', all(g.blocks_pawns() and g.avoidance_on() for g in ronda), [(g.get_actor_label()[8:], g.blocks_pawns(), g.avoidance_on()) for g in ronda if not (g.blocks_pawns() and g.avoidance_on())])
    def cruce(pa, pb, segundos, nombre):
        """a va de pa a pb y b de pb a pa; distancia mínima entre centros y atascos (más de 3 s sin avanzar)."""
        za, zb = suelo_z(w, pa) + 95, suelo_z(w, pb) + 95
        a.set_actor_location(V(pa.x, pa.y, za), False, True); b.set_actor_location(V(pb.x, pb.y, zb), False, True)
        y0a, y0b = a.get_editor_property('yields'), b.get_editor_property('yields')
        a.hold(0.0); b.hold(0.0)
        a.errand(V(pb.x, pb.y, zb), V(pb.x * 2 - pa.x, pb.y * 2 - pa.y, zb), 40.0)
        b.errand(V(pa.x, pa.y, za), V(pa.x * 2 - pb.x, pa.y * 2 - pb.y, za), 40.0)
        dmin, quieto, atasco = 1e9, {a: [0.0, a.get_actor_location()], b: [0.0, b.get_actor_location()]}, 0.0
        t, desvio, tuck = 0.0, 0.0, 0.0
        bo0 = a.get_editor_property('back_outs') + b.get_editor_property('back_outs')
        while t < segundos:
            yield 0.1
            t += 0.1
            la, lb = a.get_actor_location(), b.get_actor_location()
            dmin = min(dmin, dist2d(la, lb))
            # tanda F: cuánto se sale cada uno de la recta entre los dos extremos (rodear el pasillo por fuera) y el fusil
            ab = V(pb.x - pa.x, pb.y - pa.y, 0); n_ = max(math.hypot(ab.x, ab.y), 1.0)
            for l in (la, lb):
                desvio = max(desvio, abs((l.x - pa.x) * ab.y - (l.y - pa.y) * ab.x) / n_)
            if dist2d(la, lb) < 160:
                tuck = max(tuck, min(a.rifle_tuck(), b.rifle_tuck()))
            for g, l in ((a, la), (b, lb)):
                q = quieto[g]
                if dist2d(l, q[1]) < 8 and not g.is_yielding() and dist2d(l, pb if g is a else pa) > 120:
                    q[0] += 0.1
                    atasco = max(atasco, q[0])
                else:
                    q[0], q[1] = 0.0, l
            if dist2d(la, pb) < 120 and dist2d(lb, pa) < 120:
                break
        llegan = dist2d(a.get_actor_location(), pb) < 150 and dist2d(b.get_actor_location(), pa) < 150
        R[nombre] = (dmin, atasco, llegan, a.get_editor_property('yields') - y0a + b.get_editor_property('yields') - y0b)
        R[nombre + '_f'] = (desvio, tuck, a.get_editor_property('back_outs') + b.get_editor_property('back_outs') - bo0)
        for g in (a, b):
            g.hold(3600.0)
    R = {}
    # 1) en el patio, en ancho: se esquivan sin pararse
    yield from cruce(V(4300, 3950, 0), V(6500, 3950, 0), 25.0, 'patio')
    dmin, atasco, llegan, ced = R['patio']
    check('en el patio se cruzan sin tocarse (centros a más de 60 cm)', dmin > 60, '%.0f cm' % dmin)
    check('y ninguno se atasca más de 3 s, y llegan', atasco <= 3.0 and llegan, '%.1f s, llegan %s' % (atasco, llegan))
    # 2) en un pasillo estrecho: uno cede el paso
    # el pasillo de tablones de la pista de obstáculos (tools/unreal/relleno.py, PASILLO): 1,20 m entre las caras
    px, py0, py1 = -1050, 600, 1200
    pas = None
    h0 = unreal.SystemLibrary.line_trace_single(w, V(px, (py0 + py1) / 2, 60), V(px + 100, (py0 + py1) / 2, 60), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    h1 = unreal.SystemLibrary.line_trace_single(w, V(px, (py0 + py1) / 2, 60), V(px - 100, (py0 + py1) / 2, 60), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
    if h0 and h1:
        pas = (V(px, py0 - 250, 60), V(px, py1 + 250, 60), abs(h0.to_tuple()[5].x - h1.to_tuple()[5].x))   # puntos de impacto
    check('hay un pasillo estrecho de verdad en el nivel (el de la pista de obstáculos)', pas is not None and pas[2] < 130, pas and '%.0f cm de ancho' % pas[2])
    if pas:
        yield from cruce(pas[0], pas[1], 30.0, 'pasillo')
        dmin, atasco, llegan, ced = R['pasillo']
        check('en el pasillo tampoco se atraviesan', dmin > 55, '%.0f cm' % dmin)
        check('uno se arrima y cede el paso (y nadie se atasca más de 3 s)', ced >= 1 and atasco <= 3.0, '%d cesiones, %.1f s parado' % (ced, atasco))
        check('y los dos llegan a su sitio', llegan, R['pasillo'])
        desvio, tuck, bo = R['pasillo_f']
        check('en el pasillo el que cede vuelve atrás y espera (no lo rodea por fuera)', bo >= 1 and desvio < 150, '%d vueltas atrás, se aparta %.0f cm de la recta' % (bo, desvio))
        check('al cruzarse, los dos con el fusil bajado', tuck > 0.8, '%.2f' % tuck)
    # 3) en pareja al mismo sitio (grupo de búsqueda): uno al lado del otro, no dentro
    for g in (a, b):
        g.hold(0.0)
    a.set_actor_location(V(4400, 3900, a.get_actor_location().z), False, True); b.set_actor_location(V(4400, 4100, b.get_actor_location().z), False, True)
    a.errand(V(5600, 4000, 95), V(6000, 4000, 95), 20.0); b.errand(V(5600, 4000, 95), V(6000, 4000, 95), 20.0)
    dmin = 1e9
    for _ in range(80):
        yield 0.1
        dmin = min(dmin, dist2d(a.get_actor_location(), b.get_actor_location()))
    check('en pareja al mismo sitio, uno junto al otro (no dentro)', dmin > 55, '%.0f cm' % dmin)
    for g in (a, b):
        g.hold(3600.0)
    # 4) el jugador choca con los de pie y no con los tumbados
    p = jugador()
    la = a.get_actor_location()
    p.set_actor_location(V(la.x + 300, la.y, la.z), False, True); yield 0.2
    p.set_actor_location(V(la.x, la.y, la.z), True, False); yield 0.1
    d1 = dist2d(p.get_actor_location(), a.get_actor_location())
    check('el jugador choca con un guardia de pie', d1 > 50, '%.0f cm' % d1)
    b.set_actor_location(V(la.x, la.y + 900, la.z), False, True)   # el de la pareja, fuera del paso
    a.set_editor_property('knock_out_time', 6.0)
    a.knock_out(); yield 1.0
    la = a.get_actor_location()
    p.set_actor_location(V(la.x + 300, la.y, la.z + 40), False, True); yield 0.2
    p.set_actor_location(V(la.x - 200, la.y, la.z + 40), True, False); yield 0.1
    check('y pasa por encima de uno tumbado', p.get_actor_location().x < la.x - 100 and not a.blocks_pawns(), '%.0f' % (p.get_actor_location().x - la.x))
    aparte()
    yield 6.0
    check('al levantarse vuelve a bloquear', a.blocks_pawns(), estado(a))
    # 5) el lobo rodea a un guardia plantado en su paso
    d.set_editor_property('dog', True)
    yield 1.0
    check('el lobo está para la prueba', d.get_editor_property('dog'))
    if d.get_editor_property('dog'):
        g = b
        g.set_actor_location(V(4950, 6600, suelo_z(w, V(4950, 6600, 60)) + 95), False, True)
        g.hold(3600.0)
        p0 = P('dog_person_pushes')
        dmin = 1e9
        for _ in range(200):
            yield 0.1
            dmin = min(dmin, dist2d(d.dog_location(), g.get_actor_location()))
        check('el lobo rodea al guardia que se le pone en medio (no lo atraviesa)', dmin > 60 and P('dog_person_pushes') > p0, '%.0f cm, %d empujones' % (dmin, P('dog_person_pushes') - p0))
    # 6) coste: el fotograma con las rondas en marcha, con lo de cruzarse y sin ello (RVO y CrossTick apagados)
    for g in guardias():
        g.hold(0.0)
    aparte()
    def medio(seg):
        t0 = unreal.GameplayStatics.get_real_time_seconds(w); n = 0
        while unreal.GameplayStatics.get_real_time_seconds(w) - t0 < seg:
            yield 0.0
            n += 1
        R['ms'] = (unreal.GameplayStatics.get_real_time_seconds(w) - t0) * 1000.0 / max(n, 1)
    yield 2.0
    yield from medio(6.0); con = R['ms']
    for g in guardias():
        g.set_editor_property('cross_rule', False)
        g.character_movement.set_editor_property('use_rvo_avoidance', False)
    yield 1.0
    yield from medio(6.0); sin = R['ms']
    for g in guardias():
        g.set_editor_property('cross_rule', True)
        if not g.get_editor_property('tower_sentry'):
            g.character_movement.set_editor_property('use_rvo_avoidance', True)
    check('coste de no atravesarse (fotograma medio, %d guardias)' % len(guardias()), con < sin * 1.15 + 1.0, 'con %.2f ms, sin %.2f ms' % (con, sin))


def _juego(seg):
    """Espera seg segundos de tiempo de JUEGO (con el editor cargado el juego va más lento que el reloj)."""
    t0 = unreal.GameplayStatics.get_time_seconds(mundo())
    yield ('hasta', lambda: unreal.GameplayStatics.get_time_seconds(mundo()) - t0 >= seg, seg * 20.0 + 5.0)


def _voces(d, v0):
    """Las voces que han sonado desde que voices_played valía v0 (el registro solo guarda las 30 últimas)."""
    n = d.get_editor_property('voices_played') - v0
    l = [str(x) for x in d.get_editor_property('voice_log')]
    return l[-n:] if n > 0 else []


def _ronda_libre(solo):
    """Todos quietos salvo `solo` (los que no se mueven no los elige nadie para nada)."""
    for g in guardias():
        g.hold(0.0 if g in solo else 3600.0)


def _largo_ronda(g):
    pts = list(g.get_editor_property('patrol_points'))
    return sum(dist2d(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))) if len(pts) > 1 else 0.0


def prueba_ausencias():
    """Tanda F. Cuerpos que se echan de menos: entre 60 y 120 s (cada uno lo suyo) la central llama al caído y sale su
    compañero (el de la ronda que se cruza con la suya) a recorrer su ronda punto por punto. Si el cuerpo no está en
    ella, «ni rastro» y la base en guardia; si está, lo ve y da el aviso de siempre."""
    d = director()
    vl = lambda: [str(x) for x in director().get_editor_property('voice_log')]
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.3
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry') and len(g.get_editor_property('patrol_points')) >= 2
             and not g.get_actor_label().endswith('Ramos')]
    check('hay rondas de varios puntos', len(ronda) >= 3, len(ronda))
    ts = [d.miss_delay_of(g) for g in ronda]
    check('a cada uno lo echan de menos entre 60 y 120 s, no a todos a la vez', all(60.0 <= t <= 120.0 for t in ts) and max(ts) - min(ts) > 5.0, ['%.0f' % t for t in ts])
    # el compañero: con todos libres, el de la ronda que se cruza con la suya
    ronda.sort(key=_largo_ronda)
    v = ronda[0]
    _ronda_libre(guardias()); yield 0.2
    b = d.buddy_of(v)
    cerca = min(dist2d(p, q) for p in v.get_editor_property('patrol_points') for q in (b.get_editor_property('patrol_points') or [b.get_actor_location()])) if b else 1e9
    check('su compañero es uno cuya ronda se cruza con la suya', b is not None and b != v and cerca < 1500, '%s a %.0f cm' % (b and b.get_actor_label(), cerca))
    _ronda_libre([b]); yield 0.2
    # cae y lo escondes lejos de su ronda: el que lo busca no lo encuentra
    d.set_editor_property('miss_min', 8.0); d.set_editor_property('miss_max', 8.0)
    n0 = len(vl())
    derribar(v); yield 0.3
    l = v.get_actor_location()
    v.set_actor_location(V(-33000, -33000, l.z), False, True)
    yield 5.0
    check('antes de su tiempo nadie lo echa de menos', d.miss_searcher_of(v) is None and 'central_responde' not in vl()[n0:])
    yield ('hasta', lambda: director().miss_searcher_of(v) is not None, 8.0)
    check('la central llama al que no contesta y sale su compañero', d.miss_searcher_of(v) == b and 'central_responde' in vl()[n0:], '%s %s' % (d.miss_searcher_of(v), vl()[-3:]))
    pts = list(v.get_editor_property('patrol_points'))
    vistos = set()
    t = 0.0
    while t < 200.0 and not any(x.endswith('_nirastro') for x in vl()[n0:]):
        yield 0.5
        t += 0.5
        lb = b.get_actor_location()
        for i, p in enumerate(pts):
            if dist2d(lb, p) < 260:
                vistos.add(i)
    check('recorre su ronda punto por punto', len(vistos) >= min(len(pts), 3), '%d de %d puntos en %.0f s' % (len(vistos), len(pts), t))
    check('ni rastro: lo dice por radio y la base queda en guardia', any(x.endswith('_nirastro') for x in vl()[n0:]) and d.get_editor_property('tension_t') > 100.0
          and d.get_editor_property('miss_not_found') == 1, '%s %.0f' % (vl()[-3:], d.get_editor_property('tension_t')))
    check('ya no lo busca nadie', d.miss_searcher_of(v) is None)
    # otro cae en su ronda (sin esconderlo): el compañero lo encuentra y da el aviso de siempre
    d.set_editor_property('tension_t', 0.0)
    w = ronda[1] if ronda[1] != b else ronda[2]
    _ronda_libre(guardias()); yield 0.2
    b2 = d.buddy_of(w)
    _ronda_libre([b2]); yield 0.2
    n1 = len(vl())
    derribar(w); yield 0.3
    yield ('hasta', lambda: director().miss_searcher_of(w) is not None, 14.0)
    check('a este lo busca el suyo', d.miss_searcher_of(w) == b2, '%s / %s' % (d.miss_searcher_of(w), b2 and b2.get_actor_label()))
    yield ('hasta', lambda: w.get_editor_property('found'), 200.0)
    check('lo encuentra en su ronda: el aviso de siempre (cuerpo)', w.get_editor_property('found') and any(x.endswith('_cuerpo') for x in vl()[n1:]), vl()[-3:])
    yield 0.5
    check('y deja de buscar', d.miss_searcher_of(w) is None and d.get_editor_property('miss_searches') == 2, '%s %d' % (d.miss_searcher_of(w), d.get_editor_property('miss_searches')))
    check('ningún texto pedido falta', not list(d.get_editor_property('missing_texts')), list(d.get_editor_property('missing_texts')))


def prueba_sabotaje():
    """Tanda F. Sabotaje con la E y tiempo de manipulación. La antena: sin red hasta que la empalmen (el compañero echa de
    menos al caído más tarde y sin central); el que pasa junto a ella ve el cable y sale uno a arreglarla; arreglada, la
    base en guardia. El gasoil: el chorro se oye y atrae, el charco moja las botas y el primero que llega cierra y avisa."""
    w = mundo()
    d = director()
    vl = lambda: [str(x) for x in director().get_editor_property('voice_log')]
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.5
    tags = {}
    for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor):
        for t in a.tags:
            if str(t).startswith('sabotaje_'):
                tags[str(t)] = tags.get(str(t), 0) + 1
    check('las piezas del rastro están en el nivel', all(tags.get(t) for t in ('sabotaje_antena', 'sabotaje_antena_sano', 'sabotaje_gasoil', 'sabotaje_chorro')), tags)
    check('al empezar: cable sano, sin charco ni chorro', d.sabotage_trace_shown('sabotaje_antena_sano') and not d.sabotage_trace_shown('sabotaje_antena')
          and not d.sabotage_trace_shown('sabotaje_gasoil') and not d.sabotage_trace_shown('sabotaje_chorro'))
    # la antena
    a = d.get_editor_property('antenna_loc')
    tp(a.x, a.y + 110, -90.0); yield 0.4
    check('junto a la caja de la antena, el aviso de la E', 'ANTENA' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 1.0
    check('cortar lleva su tiempo', d.sabotage_work() == 1 and not d.antenna_cut() and 0.1 < d.sabotage_progress() < 0.5 and '%' in str(d.interact_prompt()),
          '%d %.2f %s' % (d.sabotage_work(), d.sabotage_progress(), d.interact_prompt()))
    tp(a.x, a.y + 700, -90.0); yield 0.3
    check('si te alejas lo dejas a medias', d.sabotage_work() == 0 and not d.antenna_cut())
    tp(a.x, a.y + 110, -90.0); yield 0.3
    d.interact(); yield d.get_editor_property('antenna_cut_seconds') + 0.6
    check('cortado: sin red y el cable cuelga', d.antenna_cut() and d.radio_dead() and d.sabotage_trace_shown('sabotaje_antena') and not d.sabotage_trace_shown('sabotaje_antena_sano'),
          '%s %s' % (d.antenna_cut(), d.radio_dead()))
    aparte()
    # sin red: el compañero echa de menos al caído más tarde (x1,5) y sin central
    ronda = sorted([g for g in guardias() if not g.get_editor_property('tower_sentry') and len(g.get_editor_property('patrol_points')) >= 2
                    and not g.get_actor_label().endswith('Ramos')], key=_largo_ronda)
    x = ronda[0]
    _ronda_libre(guardias()); yield 0.2
    b = d.buddy_of(x)
    _ronda_libre([b]); yield 0.2
    d.set_editor_property('miss_min', 6.0); d.set_editor_property('miss_max', 6.0)
    n0 = len(vl())
    derribar(x); yield 7.0
    check('sin red tarda más en echarlo de menos', d.miss_searcher_of(x) is None)
    yield ('hasta', lambda: director().miss_searcher_of(x) is not None, 6.0)
    check('y sale su compañero por su cuenta: sin central', d.miss_searcher_of(x) == b and 'central_responde' not in vl()[n0:] and any(s.endswith('_falta') for s in vl()[n0:]), vl()[n0:])
    b.hold(3600.0)
    # el que pasa junto a la antena ve el cable colgando: ya no esperan, sale uno a empalmarlo
    c = [g for g in ronda if g not in (x, b)][0]
    lc = c.get_actor_location()
    c.set_actor_location(V(a.x + 250, a.y + 200, suelo_z(w, V(a.x + 250, a.y + 200, 0)) + 95), False, True); yield 0.5
    check('el que pasa junto a la antena ve el cable', any(s.endswith('_antena_ve') for s in vl()) and d.get_editor_property('radio_dead_t') >= d.get_editor_property('radio_dead_seconds') - 1.0,
          '%s %.0f' % (vl()[-2:], d.get_editor_property('radio_dead_t')))
    c.hold(0.0)
    yield ('hasta', lambda: director().emisora_fixer_now() is not None, 8.0)
    f = d.emisora_fixer_now()
    check('sale uno a empalmarlo', f is not None and f.is_on_errand(), f)
    if f:
        lf = f.get_actor_location()
        f.set_actor_location(V(a.x, a.y + d.get_editor_property('emisora_stand'), lf.z), False, True)
    yield ('hasta', lambda: not director().radio_dead(), d.get_editor_property('radio_fix_seconds') + 25.0)
    yield 1.0
    check('empalmado: vuelve la red, el cable sano y la base en guardia', not d.radio_dead() and d.has_flag('antena_reparada') and d.sabotage_trace_shown('sabotaje_antena_sano')
          and d.get_editor_property('tension_t') > 100.0 and any(s.endswith('_antena') for s in vl()), '%s %.0f' % (vl()[-3:], d.get_editor_property('tension_t')))
    check('la central lo dice', 'central_red' in vl(), vl()[-3:])
    # el gasoil (el caído de antes, lejos: que su hallazgo no ponga la base en alerta en medio de esto)
    lx = x.get_actor_location()
    x.set_actor_location(V(-33000, -33000, lx.z), False, True)
    for g in guardias():
        g.hold(3600.0)
    d.set_editor_property('tension_t', 0.0)
    yield 0.5
    v = d.get_editor_property('valve_loc')
    tp(v.x + 40, v.y, 180.0); yield 0.4
    check('junto a la llave del gasoil, el aviso de la E', 'GASOIL' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield d.get_editor_property('valve_open_seconds') + 0.6
    check('abierta: el chorro y el charco', d.valve_open() and d.sabotage_trace_shown('sabotaje_gasoil') and d.sabotage_trace_shown('sabotaje_chorro'))
    ch = [a2 for a2 in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.DecalActor) if a2.actor_has_tag('sabotaje_gasoil')][0].get_actor_location()
    d.test_footstep(V(ch.x, ch.y, ch.z - 4), 0.0, False)
    check('el charco moja las botas (huellas mojadas al salir)', str(d.get_editor_property('last_print_kind')) == 'agua', d.get_editor_property('last_print_kind'))
    aparte()
    libres = [g for g in guardias() if not g.get_editor_property('tower_sentry') and not g.get_actor_label().endswith('Ramos')]
    _ronda_libre(libres)
    yield ('hasta', lambda: any(estado(g) == 'SUSPICIOUS' for g in libres), 4.0)
    oyen = [g.get_actor_label() for g in libres if estado(g) == 'SUSPICIOUS']
    check('el chorro se oye: van a mirar (dos la primera vez)', 1 <= len(oyen) <= 2, oyen)
    yield ('hasta', lambda: director().get_editor_property('sabotage_found') >= 1, 120.0)
    check('el primero que llega lo ve y avisa: la base en guardia', d.get_editor_property('sabotage_found') == 1 and any(s.endswith('_gasoil') for s in vl())
          and d.get_editor_property('tension_t') > 100.0, '%s %.0f' % (vl()[-2:], d.get_editor_property('tension_t')))
    yield ('hasta', lambda: not director().valve_open(), 12.0)
    yield 0.3
    check('la cierra: sin chorro, pero el charco se queda', not d.valve_open() and d.has_flag('gasoil_cerrado') and d.sabotage_trace_shown('sabotaje_gasoil')
          and not d.sabotage_trace_shown('sabotaje_chorro'), 'abierta %s, cerrado %s, charco %s, chorro %s, hallazgos %d' % (d.valve_open(), d.has_flag('gasoil_cerrado'),
          d.sabotage_trace_shown('sabotaje_gasoil'), d.sabotage_trace_shown('sabotaje_chorro'), d.get_editor_property('sabotage_found')))
    check('ningún texto pedido falta', not list(d.get_editor_property('missing_texts')), list(d.get_editor_property('missing_texts')))


def _esconder(d, g, idx):
    """Derriba a g junto al escondite idx, lo arrastra y lo mete (E, el tiempo que haga falta)."""
    L = d.stash_slot_loc(idx)
    l = g.get_actor_location()
    g.set_actor_location(V(L.x + 40, L.y + 40, l.z), False, True); yield 0.2
    derribar(g); yield 2.5
    junto_a(g, 60.0); yield 0.3
    d.interact(); yield 0.3   # agarrarlo
    p = jugador().get_actor_location()
    jugador().set_actor_location(V(L.x, L.y, p.z), False, True); yield 0.3


def prueba_escondidos():
    """Tanda G. Cuerpos en taquillas y cajones: arrastrándolo, E y unos segundos; dentro nadie lo ve al pasar, tardan más
    en echarlo de menos (x1,6), en una taquilla ocupada no te puedes esconder y solo lo encuentra quien abra el escondite
    (el compañero que lo busca abre los que tiene cerca de cada punto de la ronda)."""
    d = director()
    vl = lambda: [str(x) for x in director().get_editor_property('voice_log')]
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.3
    nh = len(d.get_editor_property('hide_spots'))
    check('escondites: las taquillas y los cajones grandes', d.stash_slot_count() >= nh + 3, '%d (%d taquillas)' % (d.stash_slot_count(), nh))
    ronda = sorted([g for g in guardias() if not g.get_editor_property('tower_sentry') and len(g.get_editor_property('patrol_points')) >= 2
                    and not g.get_actor_label().endswith('Ramos')], key=_largo_ronda)
    v, w = ronda[0], ronda[1]
    # 1) al cajón
    cj = nh
    yield from _esconder(d, v, cj)
    check('arrastrándolo junto al cajón, el aviso de la E', 'CAJON' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 1.0
    check('meterlo lleva su tiempo', 0.1 < d.stash_progress() < 0.8 and not v.get_editor_property('stashed'), '%.2f' % d.stash_progress())
    yield d.get_editor_property('stash_seconds')
    check('dentro: oculto, sin colisión y ya no lo arrastras', v.get_editor_property('stashed') and v.get_editor_property('hidden') and d.stash_slot_body(cj) == v
          and d.get_editor_property('dragged') is None, '%s %s' % (v.get_editor_property('stashed'), d.stash_slot_body(cj)))
    # nadie lo ve al pasar
    c = [g for g in ronda if g not in (v, w)][0]
    L = d.stash_slot_loc(cj)
    lc = c.get_actor_location()
    c.set_actor_location(V(L.x + 250, L.y, lc.z), False, True)
    c.set_actor_rotation(unreal.Rotator(0, 0, 180), False)
    aparte(); yield 2.0
    check('el que pasa al lado no lo ve', not v.get_editor_property('found') and estado(c) == 'PATROL', estado(c))
    c.hold(3600.0)
    # tardan más en echarlo de menos: sin abrir escondites, ni rastro
    d.set_editor_property('miss_min', 6.0); d.set_editor_property('miss_max', 6.0); d.set_editor_property('stash_search_dist', 0.0)
    _ronda_libre(guardias()); yield 0.2
    b = d.buddy_of(v)
    _ronda_libre([b])
    t0 = v.down_time()
    yield ('hasta', lambda: director().miss_searcher_of(v) is not None, 20.0)
    t = v.down_time()
    check('escondido, tardan más en echarlo de menos (x1,6)', d.miss_searcher_of(v) is not None and t >= 6.0 * 1.55, '%.1f s' % t)
    b.hold(3600.0)
    # solo lo encuentra quien abre el escondite
    n = d.open_stashes_near(c, L, 300.0); yield 0.5
    check('al abrir el cajón lo encuentra: el aviso de siempre', n == 1 and v.get_editor_property('found') and not v.get_editor_property('stashed') and not v.get_editor_property('hidden')
          and any(x.endswith('_cuerpo') for x in vl()), '%d %s' % (n, vl()[-2:]))
    # 2) a una taquilla: ocupada, no te escondes; y el que lo busca la abre al pasar por su punto
    yield from _esconder(d, w, 0)
    d.interact(); yield d.get_editor_property('stash_seconds') + 0.6
    check('en la taquilla', w.get_editor_property('stashed') and d.stash_slot_body(0) == w)
    sp = d.get_editor_property('hide_spots')[0]
    yw = d.get_editor_property('hide_yaws')[0]
    f = unreal.MathLibrary.get_forward_vector(unreal.Rotator(0, 0, yw))
    p = jugador().get_actor_location()
    jugador().set_actor_location(V(sp.x + f.x * 75, sp.y + f.y * 75, p.z), False, True); yield 0.3
    check('con un cuerpo dentro, ahí no te puedes esconder', d.hide_spot_near() != 0 and 'ESCONDERTE' not in str(d.interact_prompt()), str(d.interact_prompt()))
    aparte()
    d.set_editor_property('stash_search_dist', 1e7)   # el que lo busca abre lo que tenga a mano en su primer punto
    _ronda_libre(guardias()); yield 0.2
    b2 = d.buddy_of(w)
    _ronda_libre([b2])
    yield ('hasta', lambda: w.get_editor_property('found'), 60.0)
    check('el que lo busca abre la taquilla y lo encuentra', w.get_editor_property('found') and not w.get_editor_property('stashed') and d.get_editor_property('stashes_found') == 2,
          d.get_editor_property('stashes_found'))
    check('ningún texto pedido falta', not list(d.get_editor_property('missing_texts')), list(d.get_editor_property('missing_texts')))


def prueba_pulso():
    """Tanda G. Pulso al apuntar: la mira se mueve sola, más tras correr, herido o con la base en alerta, y se calma; con
    Mayús se contiene la respiración (quieta unos segundos) y luego tiembla más un rato."""
    d = director()
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield from _juego(0.3)
    d.set_darts(max(1, d.get_editor_property('darts')))
    d.set_editor_property('exertion', 0.0); d.set_editor_property('seen_sway', 0.0); d.set_editor_property('wounds', 0)
    d.set_editor_property('aim_held', False); yield from _juego(0.5)
    check('sin apuntar la mira no se mueve', d.aim_wobble().pitch == 0.0 and d.aim_wobble().yaw == 0.0, d.aim_wobble())
    d.set_editor_property('aim_held', True); yield from _juego(1.0)
    pc = unreal.GameplayStatics.get_player_controller(mundo(), 0)
    def recorrido(seg):
        r0 = pc.get_control_rotation(); m = 0.0
        t0 = unreal.GameplayStatics.get_time_seconds(mundo())
        while unreal.GameplayStatics.get_time_seconds(mundo()) - t0 < seg:
            yield 0.02
            r = pc.get_control_rotation()
            m = max(m, abs(r.yaw - r0.yaw) + abs(r.pitch - r0.pitch))
        R['m'] = m
    R = {}
    a0 = d.aim_sway()
    yield from recorrido(3.0); quieto = R['m']
    check('apuntando, en calma: se mueve un poco', 0.05 < quieto < 1.5 and d.get_editor_property('aim_alpha') > 0.9, '%.2f grados, amplitud %.2f' % (quieto, a0))
    d.set_editor_property('exertion', 1.0); yield from _juego(1.2)
    a1 = d.aim_sway()
    yield from recorrido(3.0); cansado = R['m']
    check('tras correr, mucho más', a1 > a0 * 2.5 and cansado > quieto * 1.8, '%.2f -> %.2f (%.2f -> %.2f grados)' % (a0, a1, quieto, cansado))
    yield from _juego(4.0)
    check('y se calma con el tiempo', d.get_editor_property('exertion') < 0.6 and d.aim_sway() < a1, '%.2f' % d.get_editor_property('exertion'))
    d.set_editor_property('exertion', 0.0); yield from _juego(1.5)
    a0 = d.aim_sway()
    d.set_editor_property('exertion', 0.0)
    d.set_editor_property('wounds', 2); yield from _juego(1.2)
    check('herido, más', d.aim_sway() > a0 * 1.8, '%.2f' % d.aim_sway())
    d.set_editor_property('wounds', 0)
    d.set_editor_property('seen_sway', 1.0); yield from _juego(1.2)
    check('con la base en alerta, más', d.aim_sway() > a0 * 1.8, '%.2f' % d.aim_sway())
    d.set_editor_property('seen_sway', 0.0); yield from _juego(1.5)
    # contener la respiración (Mayús apuntando)
    d.simulate_key('LeftShift'); yield from _juego(0.2)
    check('Mayús apuntando contiene la respiración (no echa a correr)', d.breath_phase() == 1 and not d.get_editor_property('sprint'), '%d %s' % (d.breath_phase(), d.get_editor_property('sprint')))
    yield from _juego(0.6)
    yield from recorrido(1.8); conteniendo = R['m']
    check('conteniendo: mucho más quieta', conteniendo < quieto * 0.6 and d.aim_sway() < a0 * 0.2, '%.2f grados (amplitud %.3f)' % (conteniendo, d.aim_sway()))
    yield ('hasta', lambda: director().breath_phase() == 2, 3.0)
    fase = d.breath_phase()
    yield from recorrido(2.0); suelta = R['m']; amp = d.aim_sway()
    check('luego tiembla más un rato', fase == 2 and amp > a0 * 1.8 and suelta > quieto * 1.1, '%.2f grados (amplitud %.2f)' % (suelta, amp))
    yield ('hasta', lambda: director().breath_phase() == 0, 4.0)
    check('y vuelve a lo normal', d.breath_phase() == 0)
    d.set_editor_property('aim_held', False); yield from _juego(0.6)
    check('al dejar de apuntar, la mira vuelve donde estaba', abs(d.aim_wobble().pitch) < 0.01 and abs(d.aim_wobble().yaw) < 0.01, d.aim_wobble())


def _agachado(d, si=True):
    if bool(jugador().get_editor_property('is_crouched')) != si:
        d.simulate_key('C')


def prueba_trampas():
    """Tanda G. Trampas: agachado y con E, latas en el suelo y cable en un paso estrecho; se recogen. Las latas suenan y
    atraen; el cable hace caer aturdido al que tropieza; con luz, un guardia la ve antes, la quita y avisa."""
    w = mundo()
    d = director()
    vl = lambda: [str(x) for x in director().get_editor_property('voice_log')]
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.3
    d.set_editor_property('trap_cans', 2); d.set_editor_property('trap_wires', 1)
    d.set_day(False); yield 0.3
    # de pie no se pone nada
    px, py0, py1 = -1050, 600, 1200
    tp(px, 200, 90.0); yield 0.3
    _agachado(d, False); yield 0.3
    check('de pie, la E no pone trampas', 'LATAS' not in str(d.interact_prompt()) and 'CABLE' not in str(d.interact_prompt()), str(d.interact_prompt()))
    _agachado(d); yield 0.4
    check('agachado en abierto: colgar latas', 'LATAS' in str(d.interact_prompt()), str(d.interact_prompt()))
    # en el pasillo de tablones: el cable
    tp(px, (py0 + py1) / 2 - 80, 90.0); yield 0.3
    _agachado(d); yield 0.4
    check('agachado en un paso estrecho: tender el cable', 'CABLE' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 0.3
    check('cable tendido de pared a pared', d.trap_count() == 1 and d.trap_kind(0) == 1 and d.get_editor_property('trap_wires') == 0, d.trap_count())
    # recoger
    d.interact(); yield 0.3
    check('E junto a ella la recoge', d.trap_count() == 0 and d.get_editor_property('trap_wires') == 1)
    d.interact(); yield 0.3
    cable = d.trap_loc(0)
    _agachado(d, False); aparte(); yield 0.4
    # un guardia cruza el pasillo de noche (a oscuras no lo ve): tropieza
    a = [g for g in guardias() if not g.get_editor_property('tower_sentry') and not g.get_actor_label().endswith('Ramos')][0]
    za = suelo_z(w, V(px, py1 + 250, 0)) + 95
    a.set_actor_location(V(px, py1 + 250, za), False, True)
    a.hold(0.0)
    a.errand(V(px, py0 - 250, za), V(px, py0 - 400, za), 40.0)
    n0 = len(vl())
    yield ('hasta', lambda: director().get_editor_property('traps_sprung') >= 1, 20.0)
    yield 0.3
    check('el que cruza el cable tropieza y cae aturdido', d.get_editor_property('traps_sprung') == 1 and a.is_stunned() and any(x.endswith('_tropiezo') for x in vl()[n0:]),
          '%d %s %s' % (d.get_editor_property('traps_sprung'), a.is_stunned(), vl()[n0:]))
    check('y el cable se rompe', d.trap_count() == 0)
    a.hold(3600.0)
    # las latas, en el patio (de noche, a oscuras): el que pasa las hace sonar y vienen los de cerca
    tp(4300, 3950, 0.0); yield 0.3
    _agachado(d); yield 0.4
    d.interact(); yield 0.3
    check('latas colgadas', d.trap_count() == 1 and d.trap_kind(0) == 0 and d.get_editor_property('trap_cans') == 1, d.trap_count())
    t = d.trap_loc(0)
    _agachado(d, False); aparte(); yield 0.3
    b, c = [g for g in guardias() if not g.get_editor_property('tower_sentry') and not g.get_actor_label().endswith('Ramos') and g != a][:2]
    zb = suelo_z(w, V(t.x - 400, t.y, 0)) + 95
    b.set_actor_location(V(t.x - 400, t.y, zb), False, True); c.set_actor_location(V(t.x - 900, t.y + 600, zb), False, True)
    b.hold(0.0)
    b.errand(V(t.x + 400, t.y, zb), V(t.x + 600, t.y, zb), 40.0)
    c.hold(0.0)
    n1 = len(vl())
    yield ('hasta', lambda: director().get_editor_property('traps_sprung') + director().get_editor_property('traps_found') >= 2, 20.0)
    yield 0.5
    if d.get_editor_property('traps_found') >= 1:
        check('(con luz) el que pasa ve las latas antes y las quita', any(x.endswith('_trampa') for x in vl()[n1:]))
    else:
        check('las latas suenan: el que pasa y el de cerca van a mirar', d.get_editor_property('traps_sprung') == 2 and any(x.endswith('_lata') for x in vl()[n1:])
              and estado(c) == 'SUSPICIOUS', '%s %s' % (vl()[n1:], estado(c)))
    for g in (b, c):
        g.hold(3600.0)
    d.set_day(False)
    check('ningún texto pedido falta', not list(d.get_editor_property('missing_texts')), list(d.get_editor_property('missing_texts')))


def prueba_trampas_luz():
    """Tanda G. Con buena luz, el guardia que pasa ve la trampa antes de pisarla, la quita y avisa (la base en guardia)."""
    w = mundo()
    d = director()
    vl = lambda: [str(x) for x in director().get_editor_property('voice_log')]
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.3
    d.set_editor_property('trap_cans', 2)
    b = [g for g in guardias() if not g.get_editor_property('tower_sentry') and not g.get_actor_label().endswith('Ramos')][1]
    d.set_day(True); yield 0.3
    tp(4300, 3950, 0.0); yield 0.3
    _agachado(d); yield 0.4
    v2 = d.get_editor_property('voices_played')   # (a pleno día puede verla cualquiera que mire hacia allí)
    d.interact(); yield 0.3
    t = d.trap_loc(0)
    _agachado(d, False); aparte(); yield 0.3
    check('latas colgadas a pleno día', d.trap_count() == 1 or d.get_editor_property('traps_found') == 1, d.trap_count())
    zb = suelo_z(w, V(t.x - 450, t.y, 0)) + 95
    b.set_actor_location(V(t.x - 450, t.y, zb), False, True); b.set_actor_rotation(unreal.Rotator(0, 0, 0), False)
    b.hold(0.0)
    b.errand(V(t.x + 400, t.y, zb), V(t.x + 600, t.y, zb), 40.0)
    yield ('hasta', lambda: director().get_editor_property('traps_found') >= 1, 12.0)
    yield from _juego(3.0)
    check('de día, el que pasa la ve antes, la quita y avisa: la base en guardia', d.get_editor_property('traps_found') >= 1 and any(x.endswith('_trampa') for x in _voces(d, v2))
          and d.trap_count() == 0 and d.get_editor_property('tension_t') > 60.0, '%d %s %d %.0f' % (d.get_editor_property('traps_found'), _voces(d, v2), d.trap_count(), d.get_editor_property('tension_t')))
    b.hold(3600.0)
    d.set_day(False)


def prueba_emboscada():
    """Tanda G. El que sale a empalmar la antena va solo y sin radio; si lo tumbas allí, entra en las ausencias: su
    compañero lo echa de menos (tarde y sin central) y lo busca empezando por la antena."""
    w = mundo()
    d = director()
    vl = lambda: [str(x) for x in director().get_editor_property('voice_log')]
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.3
    a = d.get_editor_property('antenna_loc')
    tp(a.x, a.y + 110, -90.0); yield 0.3
    d.interact(); yield d.get_editor_property('antenna_cut_seconds') + 0.6
    check('antena cortada: sin red', d.antenna_cut() and d.radio_dead())
    aparte()
    ronda = sorted([g for g in guardias() if not g.get_editor_property('tower_sentry') and len(g.get_editor_property('patrol_points')) >= 2
                    and not g.get_actor_label().endswith('Ramos')], key=_largo_ronda)
    f = ronda[0]
    _ronda_libre([f])
    d.set_editor_property('radio_dead_t', d.get_editor_property('radio_dead_seconds') - 0.5)
    yield ('hasta', lambda: director().emisora_fixer_now() is not None, 8.0)
    check('sale uno, solo, a empalmarla', d.emisora_fixer_now() == f and f.is_on_errand(), d.emisora_fixer_now())
    otros = [g for g in guardias() if g != f and not g.get_editor_property('tower_sentry') and dist2d(g.get_actor_location(), f.get_actor_location()) < 1500 and estado(g) != 'DOWN']
    lf = f.get_actor_location()
    f.set_actor_location(V(a.x + 60, a.y + d.get_editor_property('emisora_stand'), lf.z), False, True); yield 1.0
    n0 = len(vl())
    d.set_editor_property('miss_min', 6.0); d.set_editor_property('miss_max', 6.0)
    f.set_editor_property('knock_out_time', 400.0)   # que no despierte antes de que llegue el que lo busca (la antena queda lejos)
    v0 = d.get_editor_property('voices_played')
    f.knock_out(); yield 1.0
    check('lo tumbas allí y nadie se entera por radio', 'central_responde' not in vl()[n0:] and d.radio_dead(), vl()[n0:])
    _ronda_libre(guardias()); yield 0.2
    b = d.buddy_of(f)
    _ronda_libre([b])
    yield ('hasta', lambda: director().miss_searcher_of(f) is not None, 15.0)
    check('su compañero lo echa de menos (x1,5, sin central)', d.miss_searcher_of(f) == b and 'central_responde' not in vl()[n0:] and f.down_time() >= 6.0 * 1.45,
          '%s %.1f' % (d.miss_searcher_of(f), f.down_time()))
    visto = lambda: any(x.endswith('_cuerpo') for x in _voces(director(), v0))
    yield ('hasta', lambda: b.at_errand() or visto(), 150.0)
    lb = b.get_actor_location()
    check('y empieza a buscarlo por la antena (va derecho allí)', dist2d(lb, a) < 600, '%.0f cm de la antena' % dist2d(lb, a))
    yield ('hasta', visto, 30.0)
    check('lo encuentra allí (lo ve y da el aviso)', visto(), '%s, el caído %s a %.0f cm' % (estado(b), estado(f), dist2d(b.get_actor_location(), f.get_actor_location())))


def prueba_disparo():
    """Arreglo del cierre al disparar (tras la tanda G): el dardo y el golpe en guardias sin cuerpos de física todavía
    (recién aparecidos, como los relevos, o sin precalentar) no deben cerrar el motor, tampoco meter en una taquilla a uno
    recién golpeado; y disparar apuntando funciona con el pulso: en calma, tras correr, herido y conteniendo la respiración."""
    w = mundo()
    d = director()
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.5
    # 1) a un relevo nada más aparecer
    d.set_editor_property('relief_rule', True)   # (en las pruebas va apagado)
    yield ('hasta', lambda: director().relief_post_count() > 0, 30.0)
    nuevo = None
    if d.relief_post_count() > 0:
        d.force_relief(0); yield 0.05
        nuevo = d.relief_guard(0)
    check('hay un relevo recién aparecido', nuevo is not None, d.relief_post_count())
    if nuevo:
        f = nuevo.get_actor_forward_vector()
        nuevo.dart_hit(V(-f.x, -f.y, 0.0)); yield 0.05
        nuevo.hit_react(V(f.x, f.y, 0.0), True); yield 2.5
        check('dardo y golpe al relevo recién aparecido: el juego sigue', nuevo is not None and estado(nuevo) in ('DOWN', 'PATROL', 'SUSPICIOUS', 'SEARCH', 'RETURN', 'ALERT'), estado(nuevo))
    # 2) golpe a uno lejos (sin precalentar): al apagarse la reacción se quedan sin cuerpos
    lejos = [g for g in guardias() if not g.get_editor_property('tower_sentry') and dist2d(g.get_actor_location(), jugador().get_actor_location()) > 5000][:3]
    for g in lejos:
        f = g.get_actor_forward_vector()
        g.hit_react(V(f.x, f.y, 0.0), True)
    yield 3.0
    check('golpes a guardias lejos (sin cuerpos precalentados): el juego sigue', len(lejos) > 0 and all(not g.hit_reacting() for g in lejos), len(lejos))
    # 3) golpeado, derribado y a la taquilla enseguida
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry') and len(g.get_editor_property('patrol_points')) >= 2
             and not g.get_actor_label().endswith('Ramos')]
    v = ronda[0]
    L = d.stash_slot_loc(0)
    l = v.get_actor_location()
    v.set_actor_location(V(L.x + 40, L.y + 40, l.z), False, True); yield 0.2
    f = v.get_actor_forward_vector()
    v.hit_react(V(f.x, f.y, 0.0), True); yield 0.05
    yield from _esconder(d, v, 0)
    if d.get_editor_property('dragged') is None:   # (el relevo de antes sale del barracón, junto a esta taquilla: la E pudo ser para él)
        junto_a(v, 60.0); yield 0.3
        if 'ARRASTRAR' in str(d.interact_prompt()):
            d.interact(); yield 0.3
        p = jugador().get_actor_location()
        jugador().set_actor_location(V(L.x, L.y, p.z), False, True); yield 0.3
    av = str(d.interact_prompt()); arr = d.get_editor_property('dragged')
    d.interact(); yield d.get_editor_property('stash_seconds') + 1.5
    check('recién golpeado, a la taquilla: el juego sigue', v.get_editor_property('stashed'), '%s | aviso %r | arrastrando %s | %s' % (v.get_editor_property('stashed'), av, arr, estado(v)))
    aparte(); yield 0.3
    # 4) apuntar y disparar con el pulso
    blanco = [g for g in ronda if g != v and estado(g) != 'DOWN'][0]
    bl = blanco.get_actor_location()
    for nombre, ex, her, aire in (('en calma', 0.0, 0, False), ('tras correr', 1.0, 0, False), ('herido', 0.0, 2, False), ('conteniendo la respiración', 1.0, 2, True)):
        blanco.wake_now() if estado(blanco) == 'DOWN' else None
        yield 0.3
        blanco.set_actor_location(V(bl.x, bl.y, bl.z), False, True)
        blanco.hold(3600.0)
        d.set_darts(3)
        d.set_editor_property('exertion', ex); d.set_editor_property('wounds', her)
        tp(bl.x + 600, bl.y, 180.0); yield 0.3
        mirar(V(bl.x, bl.y, bl.z + 40)); yield 0.2
        d.set_editor_property('aim_held', True); yield 0.8
        if aire:
            d.simulate_key('LeftShift'); yield 0.5
        r = d.dart_aim()
        d.shoot_dart(); yield 0.5
        d.set_editor_property('aim_held', False); yield 0.3
        check('dispara apuntando %s: gasta el dardo y el juego sigue' % nombre, d.get_editor_property('darts') == 2 and (not aire or d.breath_phase() != 0),
              '%d dardos, a tiro %s, %s' % (d.get_editor_property('darts'), r.get_actor_label() if r else None, estado(blanco)))
    d.set_editor_property('exertion', 0.0); d.set_editor_property('wounds', 0)

def prueba_relleno():
    """Tanda E1. Relleno visual del hangar (taller, Santana bajo lona, cajas LH), la enfermería con su cámara fría y la
    plaza de armas (mástil, sacos, tejadillo): todo con colisión, sin cortar rondas, el paso del lobo, el camino a la
    trampilla ni a la caja de cartón; el tablón y las fichas se leen y el candado responde."""
    w = mundo()
    d = director()
    P = lambda k: director().get_editor_property(k)
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.5
    piezas = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'atrezo.json'), encoding='utf-8'))['piezas']
    e1 = {'Atrezo_' + p['nombre']: p for p in piezas if p.get('nombre', '').startswith('e1')}
    act = {a.get_actor_label(): a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor)}
    rel = {n: a for n, a in act.items() if n.startswith('Relleno_')}
    falta = [n for n in e1 if n not in act]
    check('el atrezo nuevo está puesto (%d piezas)' % len(e1), len(e1) >= 40 and not falta, falta)
    check('y lo hecho a mano (enfermería, mástil, sacos, tejadillo, puerta fría)', all(('Relleno_' + n) in rel for n in
          ('Enfermeria_muros', 'Mastil', 'Bandera', 'Sacos_0', 'Tejadillo_postes', 'Puerta_fria', 'Candado')), sorted(rel)[:8])
    def bloquea(a):
        c = a.static_mesh_component
        return c.get_collision_enabled() in (unreal.CollisionEnabled.QUERY_AND_PHYSICS, unreal.CollisionEnabled.QUERY_ONLY) and c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN) == unreal.CollisionResponseType.ECR_BLOCK
    sin = [n for n, p in e1.items() if not p.get('pequeno') and n in act and not bloquea(act[n])]
    sin += [n for n in ('Relleno_Enfermeria_muros', 'Relleno_Puerta_fria', 'Relleno_Mastil', 'Relleno_Sacos_0', 'Relleno_Sacos_3', 'Relleno_Tejadillo_postes') if n in rel and not bloquea(rel[n])]
    check('todo lo grande tiene colisión (y lo pequeño no estorba)', not sin, sin)
    nuevos = set(list(e1) + list(rel))
    def barrido(a, b, radio=38.0, z=60.0):
        """Lo que hay entre a y b para alguien de 38 cm de radio (lo nuevo de la tanda, nada más)."""
        hs = unreal.SystemLibrary.sphere_trace_multi(w, V(a[0], a[1], z), V(b[0], b[1], z), radio, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False,
                                                     [jugador()] + list(guardias()), unreal.DrawDebugTrace.NONE, True)
        out = set()
        for h in hs or []:
            ac = h.to_tuple()[9]
            if ac and ac.get_actor_label() in nuevos:
                out.add(ac.get_actor_label())
        return sorted(out)
    # rondas de los guardias de tierra
    corta = []
    for g in guardias():
        if g.get_editor_property('tower_sentry'):
            continue
        pts = [(p.x, p.y) for p in g.get_editor_property('patrol_points')]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            for n in barrido(a, b):
                corta.append('%s: %s' % (g.get_editor_property('guard_name'), n))
    check('ninguna ronda choca con lo nuevo', not corta, corta)
    check('el lobo sigue cruzando el hangar de punta a punta', not barrido((4350, 6600), (5550, 6600), 30), barrido((4350, 6600), (5550, 6600), 30))
    camino = barrido((4900, 6250), (4900, 6500)) + barrido((4900, 6500), (4520, 6800))
    check('del portón a la trampilla, libre', not camino, camino)
    caja = barrido((4900, 6500), (5500, 6520)) + barrido((5500, 6520), (5500, 6960))   # rodeando el Santana por el este
    check('y hasta la caja de cartón', not caja, caja)
    entrar = barrido((7560, 3800), (7560, 3350), 34) + barrido((7560, 3350), (8020, 3105), 34)
    check('a la enfermería se entra por la puerta y se llega a la cámara fría', not entrar, entrar)
    pared = barrido((7900, 3800), (7900, 3300), 34)
    check('y no se atraviesa el muro', 'Relleno_Enfermeria_muros' in pared, pared)
    plaza = barrido((6800, 4100), (8450, 4100)) + barrido((6800, 4250), (7800, 4250))   # entre las filas de sacos
    check('la plaza de armas se cruza (pasillos entre los sacos)', not plaza, plaza)
    # luces: fluorescente frío que titila
    luces = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.PointLight) if a.get_actor_label().startswith('Relleno_')]
    check('dos fluorescentes fríos en la enfermería y uno titila', len([a for a in luces if 'Fluorescente' in a.get_actor_label()]) == 2 and any('parpadeo' in [str(t) for t in a.tags] for a in luces),
          [(a.get_actor_label(), [str(t) for t in a.tags]) for a in luces])
    # se leen: tablón del taller, fichas médicas y la puerta con candado
    for pid, aviso, clave, que in (('tablon_hangar', 'TABLON', 'NO SE TOCAN', 'el tablón de turnos del taller se lee'),
                                    ('fichas_medicas', 'FICHAS', 'LH-04 - VIDAL, J.', 'las fichas: LH-04 Vidal, traslado a nivel -2, y LH-08 en blanco'),
                                    ('camara_fria', 'PUERTA METALICA', 'Cerrada con candado', 'la puerta de la cámara fría: candado y frío')):
        pt = next((p for p in d.get_editor_property('points') if str(p.id) == pid), None)
        if not pt:
            check(que, False, 'falta el punto ' + pid)
            continue
        tp(pt.pos.x - 70 if pid != "tablon_hangar" else pt.pos.x + 40, pt.pos.y + (60 if pid == "fichas_medicas" else 0)); yield 0.3
        ok_aviso = aviso in str(d.interact_prompt())
        d.interact(); yield 0.3
        msg = str(P('message'))
        extra = ('nivel -2' in msg and 'LH-08' in msg) if pid == 'fichas_medicas' else True
        check(que, ok_aviso and clave in msg and extra, '%s | %s' % (d.interact_prompt(), msg[:70]))
    aparte()
    for g in guardias():
        g.hold(0.0)

def prueba_relevo():
    """Tanda D. Relevo de las torres: cada puesto, escalonado; el relevo sale del barracon, se dicen el santo y sena al pie
    de la escalera (de cerca se oye y se apunta) y sube; el puesto queda vacio unos 20-40 s. Si el centinela no esta, el
    relevo avisa por radio y, al minuto, la base se pone en tension. El cuadrante del barracon apunta los relevos."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    d.set_editor_property('relief_rule', True)
    aparte(); yield 3.0
    n = d.relief_post_count()
    check('un relevo por cada puesto de torre', n >= 4, n)
    if n < 4:
        return
    nxt = [round(d.relief_next_in(i)) for i in range(n)]
    check('escalonados (cada puesto a su hora)', len(set(nxt)) == n and max(nxt) - min(nxt) > 60, nxt)
    check('santo y sena de la noche', str(P('password_a')) != '' and str(P('password_b')) != '', '%s / %s' % (P('password_a'), P('password_b')))
    for g in guardias():
        if not g.get_editor_property('tower_sentry'):
            g.set_editor_property('view_distance', 1.0)
    d.set_editor_property('relief_wait_min', 6.0); d.set_editor_property('relief_wait_max', 8.0)
    s0 = d.relief_sentry(0)
    d.force_relief(0); yield 0.5
    r = d.relief_guard(0)
    check('sale el relevo del barracon (copia del centinela)', d.relief_phase(0) == 1 and r is not None and r.has_rifle(), '%s %s' % (d.relief_phase(0), r))
    yield ('hasta', lambda: director().relief_phase(0) >= 2, 240.0)
    check('llega y el centinela baja: el puesto queda vacio', d.relief_phase(0) == 2 and d.relief_post_empty(0), '%s %s' % (d.relief_phase(0), d.relief_post_empty(0)))
    # de cerca: la charla y el santo y sena
    if r:
        l = r.get_actor_location()
        tp(l.x + 120, l.y)
    # tanda E2: mientras charlan, cada uno en su sitio (no uno dentro del otro)
    dmin = 1e9
    for _ in range(300):
        if director().relief_phase(0) >= 3:
            break
        sx, rx = d.relief_sentry(0), d.relief_guard(0)
        if sx and rx:
            dmin = min(dmin, dist2d(sx.get_actor_location(), rx.get_actor_location()))
        yield 0.1
    check('tanda E2: el relevo y el centinela charlan a su distancia (90 cm o más)', 90 <= dmin < 400, '%.0f cm' % dmin)
    check('se oye la charla y el santo y sena se apunta en el mapa mental', P('relief_lines_heard') >= 2 and d.fact_known('relevo_santo'), '%d frases' % P('relief_lines_heard'))
    yield ('hasta', lambda: director().relief_phase(0) in (0, 4), 60.0)
    s1 = d.relief_sentry(0)
    check('el relevo sube y queda de centinela', s1 is not None and s1 != s0 and s1.get_editor_property('tower_sentry') and not d.relief_post_empty(0), s1)
    check('la ventana del puesto vacio, de 20 a 40 s', 18.0 <= P('last_relief_window') <= 42.0, '%.1f s' % P('last_relief_window'))
    check('el proximo relevo, a su hora', d.relief_next_in(0) > P('relief_every') - 30.0 or d.relief_phase(0) == 4, '%.0f s' % d.relief_next_in(0))
    aparte()
    # el puesto vacio: el centinela dormido en la torre
    d.set_editor_property('relief_missing_seconds', 10.0)
    c = d.relief_sentry(1)
    c.set_editor_property('knock_out_time', 300.0)
    c.knock_out()
    r0, a0 = P('relief_radio_calls'), P('relief_missing_alerts')
    d.force_relief(1)
    yield ('hasta', lambda: director().relief_phase(1) == 10, 240.0)
    check('el relevo encuentra el puesto vacio', d.relief_phase(1) == 10, d.relief_phase(1))
    yield ('hasta', lambda: director().get_editor_property('relief_radio_calls') > r0, 10.0)
    check('busca y avisa por radio a Control', P('relief_radio_calls') == r0 + 1, P('relief_radio_calls'))
    yield ('hasta', lambda: director().get_editor_property('relief_missing_alerts') > a0, 20.0)
    check('si no aparece: alerta de nivel 1 (la base lo echa de menos)', P('relief_missing_alerts') == a0 + 1 and d.base_state() >= 1, 'base %s' % d.base_state())
    # el cuadrante del barracon
    q = P('roster_loc')
    tp(q.x, q.y); yield 0.3
    check('el cuadrante de relevos se lee en el barracon', 'CUADRANTE' in str(d.interact_prompt()), d.interact_prompt())
    d.interact(); yield 0.3
    check('y apunta los relevos en el mapa mental', d.fact_known('relevo_cuadrante') and ':' in str(P('message')), str(P('message'))[:60])
    d.set_editor_property('relief_rule', False)
    for g in guardias():
        g.set_editor_property('view_distance', 2000.0)

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

def prueba_letal():
    """Tanda H, la vía letal. Por la espalda, la K mata con el cuchillo: cae como al derribarlo y no se levanta (ni al
    acabar el tiempo, ni al encontrarlo, ni al calmarse la base). Quien lo encuentra no dice «en el suelo»: la central
    avisa de que hay un asesino dentro y la base queda en guardia más tiempo. A Ramos no se le mata."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    nombre = lambda g: str(g.get_editor_property('guard_name'))
    yield ('hasta', lambda: len([x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL']) >= 3, 40.0)
    torres = [x for x in guardias() if x.get_editor_property('tower_sentry')]
    for x in torres:
        x.hold(60.0)
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry') and estado(g) == 'PATROL' and nombre(g) != 'Ramos']
    g = max(ronda, key=lambda x: dist2d(x.get_actor_location(), GEN))
    g.hold(3600.0)
    d.simulate_key('C'); yield 0.3
    for _ in range(3):
        detras_de(g, 90); yield 0.1
    check('por la espalda, el aviso ofrece matar con la K', 'MATAR' in str(d.interact_prompt()) and 'DERRIBAR' in str(d.interact_prompt()), d.interact_prompt())
    t0, k0 = P('takedowns'), P('kills')
    d.simulate_key('K'); yield 0.4
    check('la K lo mata: cae y queda muerto', estado(g) == 'DOWN' and g.get_editor_property('dead'), '%s dead=%s' % (estado(g), g.get_editor_property('dead')))
    check('cuenta como muerto, no como derribo', P('kills') == k0 + 1 and P('takedowns') == t0 and nombre(g) in [str(x) for x in P('killed')], '%d / %d' % (P('kills'), P('takedowns')))
    check('lo enseña una vez', 'HA MUERTO' in str(P('message')), str(P('message'))[:40])
    g.wake_now(); yield 0.3
    check('un muerto no se despierta', estado(g) == 'DOWN', estado(g))
    check('el estado de cada uno lo dice', str(dict(d.people_state()).get(nombre(g), '')) == 'muerto', dict(d.people_state()))
    d.simulate_key('C'); yield 0.3
    aparte(); yield 0.2
    # lo encuentra otro: va a mirarlo, se agacha y la central habla de un asesino
    cl = g.get_actor_location()
    obs = [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and x != g and nombre(x) != 'Ramos'][0]
    obs.set_actor_location(V(cl.x + 300, cl.y, obs.get_actor_location().z), False, True)
    obs.set_actor_rotation(unreal.Rotator(0, 0, 180), True)
    yield ('hasta', lambda: 'central_muerto' in list(director().get_editor_property('voice_log')), 14.0)
    check('la central: «esta muerto, hay un asesino dentro»', 'central_muerto' in list(P('voice_log')) and any('muerto' in str(x) for x in P('subtitle_log')), list(P('subtitle_log'))[-3:])
    check('y no «esta en el suelo»', 'central_todos' not in list(P('voice_log'))[-4:], list(P('voice_log'))[-4:])
    check('la base queda en guardia mas tiempo que con un derribo', P('tension_t') > 120.0 and P('dead_found') == 1, '%.0f s, %d' % (P('tension_t'), P('dead_found')))
    check('el muerto sigue en el suelo', estado(g) == 'DOWN', estado(g))
    d.calm_base(); yield 0.5
    check('al calmarse la base, al muerto no lo levanta nadie', estado(g) == 'DOWN' and g.get_editor_property('dead'), estado(g))
    for x in torres:
        x.hold(0.0)
    # a Ramos no
    r = guardia('Ramos')
    if r and estado(r) != 'DOWN':
        r.hold(3600.0)
        for _ in range(3):
            detras_de(r, 90); yield 0.1
        check('a Ramos no se le ofrece matar', 'MATAR' not in str(d.interact_prompt()) and r.can_be_taken_down(jugador()), d.interact_prompt())
        k1 = P('kills')
        d.kill_action(); yield 0.3
        check('y la K no lo mata (sin hablar con él, lo agarra)', P('kills') == k1 and not r.get_editor_property('dead'), P('kills'))
        if P('choice'):
            d.interact(); yield 0.2   # cierra la conversación sin elegir
        aparte(); yield 0.2
    check('ningún texto pedido falta', not list(P('missing_texts')), list(P('missing_texts')))


def prueba_vias():
    """Tanda H, segundas vías y lo que sigue. La llave de repuesto de la jefatura en la mesa de Peris (solo si sabes el
    dato); el santo y seña con uniforme deja acercarse más y el guardia da el alto una vez; Roig llama tras el
    expediente («Ricino se ha secado»); y el parte lo recoge todo y guarda el estado de cada uno."""
    d = director()
    P = lambda k: director().get_editor_property(k)
    nombre = lambda g: str(g.get_editor_property('guard_name'))
    for g in guardias():
        g.hold(3600.0)
    # ---- la llave de repuesto
    pt = [q for q in MISION['puntos'] if q['id'] == 'llave_repuesto'][0]
    tp(pt['pos'][0], pt['pos'][1], 0); yield 0.3
    check('sin el dato, la llave de repuesto no existe', 'REPUESTO' not in str(d.interact_prompt()), d.interact_prompt())
    check('el dato sale en la charla de Peris y Ramos', any(f[2:] == ['peris_repuesto'] for c in MISION['charlas'] for f in c['frases']))
    d.learn_fact('peris_repuesto'); yield 0.2
    check('sabiéndolo, se ofrece cogerla', 'REPUESTO' in str(d.interact_prompt()), d.interact_prompt())
    d.interact(); yield 0.3
    check('cogida: abre la jefatura como la de Ibarra', d.has_flag('llave_jefatura') and d.has_flag('llave_repuesto') and P('key'), '%s %s' % (d.has_flag('llave_jefatura'), d.has_flag('llave_repuesto')))
    check('y no se ofrece otra vez', 'REPUESTO' not in str(d.interact_prompt()), d.interact_prompt())
    # ---- santo y seña con uniforme
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry') and estado(g) != 'DOWN' and nombre(g) != 'Ramos']
    o = ronda[0]
    d.set_editor_property('relief_rule', True)   # la seña de esta noche la pone el relevo de las torres (en las pruebas va apagado)
    yield ('hasta', lambda: director().relief_post_count() > 0, 30.0)
    d.set_flag('uniforme')
    if agachado():
        d.simulate_key('C'); yield 0.3
    jugador().set_actor_hidden_in_game(True)
    a_la_vista_de(o, 500.0); yield 0.3
    check('con uniforme y sin la seña, nadie da el alto', d.uniform_works() and len(P('challenged')) == 0, list(P('challenged')))
    d.learn_fact('relevo_santo'); yield 0.3
    # que te tenga delante: el guardia mira al jugador
    pl = jugador().get_actor_location(); ol = o.get_actor_location()
    o.set_actor_rotation(unreal.Rotator(0, 0, math.degrees(math.atan2(pl.y - ol.y, pl.x - ol.x))), True); yield 0.4
    check('con la seña, el guardia da el alto', nombre(o) in [str(x) for x in P('challenged')] and any('Alto.' in str(x) for x in P('subtitle_log')), list(P('subtitle_log'))[-3:])
    yield 1.6
    check('y Cuttlas contesta la seña', any(str(x).startswith('CUTTLAS') for x in list(P('subtitle_log'))[-3:]), list(P('subtitle_log'))[-3:])
    jugador().set_actor_hidden_in_game(False)
    check('a 5 m, con la seña, no te ve', o.visibility(jugador()) == 0.0, o.visibility(jugador()))
    aparte(); yield 0.2
    # ---- Roig: «Ricino se ha secado»
    d.set_editor_property('roig_ricino_delay', 1.0)
    d.set_editor_property('codec_calls', True)
    d.open_codec('expediente'); d.close_codec(); yield 0.2
    yield ('hasta', lambda: str(director().get_editor_property('codec_pending')) == 'roig_ricino', 6.0)
    check('tras el expediente, llama Roig', str(P('codec_pending')) == 'roig_ricino', str(P('codec_pending')))
    d.codec_key(); yield 0.2
    check('«Ricino se ha secado», por 140.85', str(d.codec_line()).startswith('ROIG|140.85|') and 'Ricino se ha secado' in str(d.codec_line()), str(d.codec_line())[:80])
    d.close_codec(); yield 0.2
    d.set_editor_property('codec_calls', False)
    # ---- el parte
    d.set_flag('expediente')
    tp(SALIDA.x, SALIDA.y, 0)
    yield ('hasta', lambda: director().get_editor_property('done'), 5.0)
    yield ('hasta', lambda: director().get_editor_property('report'), 25.0)
    rl = list(P('report_lines'))
    check('el parte habla de la llave de repuesto de Peris', any('repuesto' in x and 'Peris' in x for x in rl) and not any('Ibarra le falta' in x for x in rl), ' | '.join(rl))
    check('y acaba con CONTINUARA: Ricino se ha secado', any(x.startswith('CONTINUARA') and 'Ricino' in x for x in rl), ' | '.join(rl[-5:]))
    check('el parte se guarda para la misión 2', unreal.GameplayStatics.does_save_game_exist('TarsisParte', 0))
    sv = unreal.GameplayStatics.load_game_from_slot('TarsisParte', 0)
    try:
        gente = dict(sv.get_editor_property('people'))
        check('con el estado de cada uno', len(gente) >= 5 and all(v in ('vivo', 'dormido', 'muerto', 'aliado') for v in gente.values()), gente)
        check('y que entraste con la de repuesto y oíste a Roig', sv.get_editor_property('spare_key') and sv.get_editor_property('roig_ricino'))
    except Exception as e:
        check('el guardado del parte se lee desde Python', False, str(e))
    check('ningún texto pedido falta', not list(P('missing_texts')), list(P('missing_texts')))


# cada familia, en un PIE limpio; dentro de una familia las pruebas comparten partida (la llave, la jefatura, el farol...)

def prueba_mira():
    """Tanda I. La mira en primera persona: el dardo va al centro de la pantalla (donde está la cruz) y, apuntando, la boca
    de la pistola se lleva sola a ese centro (antes quedaba abajo a la derecha y la cruz parecía descentrada)."""
    d = director()
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.3
    d.set_darts(3)
    d.set_editor_property('exertion', 0.0); d.set_editor_property('seen_sway', 0.0); d.set_editor_property('wounds', 0)
    d.set_editor_property('aim_held', False); yield from _juego(0.8)
    o = d.dart_screen_offset()
    check('sin apuntar, el dardo va al centro (donde está el punto)', abs(o.x) < 0.004 and abs(o.y) < 0.004, '%.4f, %.4f' % (o.x, o.y))
    d.set_editor_property('aim_held', True); yield from _juego(2.0)
    o = d.dart_screen_offset()
    m = d.aim_muzzle_offset()
    sh = d.get_editor_property('aim_auto_shift')
    check('apuntando, el dardo sigue al centro de la cruz', abs(o.x) < 0.004 and abs(o.y) < 0.004, '%.4f, %.4f' % (o.x, o.y))
    check('apuntando, la boca de la pistola junto al centro (menos de 2,5 grados)', abs(m.x) < 0.026 and -0.01 < m.y < 0.045, 'tangentes %.3f, %.3f; corrido %.1f, %.1f cm' % (m.x, m.y, sh.y, sh.z))
    d.set_editor_property('aim_held', False); yield from _juego(0.5)


def prueba_objetos():
    """Tanda I. El selector (rueda y 1-6, solo sin elecciones abiertas; el clic usa el elegido) y los objetos nuevos: se
    recogen con la E en su sitio y desaparecen del mueble; tabaco (el guardia se para a fumar), somnífero (olla y
    cantimplora), cizalla (paso en la malla; el guardia que ve el corte con luz da la alarma), walkie (de un caído, con la T;
    una orden falsa) y espejo (vista por la esquina); el plano apunta rondas y relevos en el mapa mental."""
    w = mundo()
    d = director()
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.3
    d.set_darts(3)
    d.select_item(0); yield 0.1
    # 1) el selector
    check('al empezar, en mano los dardos', d.get_editor_property('item_sel') == 0 and d.item_count(0) == 3 and d.item_count(1) == -1, d.get_editor_property('item_sel'))
    d.simulate_key('Three'); yield 0.2
    check('la tecla 3: las latas', d.get_editor_property('item_sel') == 2 and d.item_name(2) == 'LATAS', d.get_editor_property('item_sel'))
    d.simulate_key('MouseScrollDown'); yield 0.2
    check('la rueda: el siguiente que tienes (el cable)', d.get_editor_property('item_sel') == 3, d.get_editor_property('item_sel'))
    d.simulate_key('Six'); yield 0.2
    check('sin tabaco, la 6 no cambia', d.get_editor_property('item_sel') == 3, d.get_editor_property('item_sel'))
    d.press_key('P'); yield 0.2
    d.simulate_key('One'); yield 0.2
    check('con el menú abierto, las cifras no cambian de objeto', d.get_editor_property('item_sel') == 3, d.get_editor_property('item_sel'))
    d.press_key('P'); yield 0.2
    d.simulate_key('One'); yield 0.2
    check('cerrado, la 1 vuelve a los dardos', d.get_editor_property('item_sel') == 0)
    # 2) recogerlos
    def coger(pid, bandera):
        pt = [q for q in MISION['puntos'] if q['id'] == pid][0]
        tp(pt['pos'][0], pt['pos'][1], 0.0)
        yield 0.4
        R['aviso'] = str(d.interact_prompt())
        d.interact()
        yield 0.4
        tag = 'recoger_' + bandera
        R['oculto'] = all(a.is_hidden() if hasattr(a, 'is_hidden') else a.get_editor_property('hidden') for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor) if a.actor_has_tag(tag))
    R = {}
    for pid, bandera in (('tabaco', 'obj_tabaco'), ('somnifero', 'obj_somnifero'), ('espejo', 'obj_espejo'), ('cizalla', 'obj_cizalla'), ('plano', 'dato_plano_rondas')):
        yield from coger(pid, bandera)
        check('%s: se coge con la E y desaparece del mueble' % pid, d.has_flag(bandera) and R['oculto'], '%s | %s' % (R['aviso'], R['oculto']))
    check('tabaco: 3 cajetillas; somnífero: 2 dosis', d.item_count(4) == 3 and d.item_count(5) == 2, '%d %d' % (d.item_count(4), d.item_count(5)))
    tx = d.get_editor_property('texts')
    rondas = str(tx['dt_plano_rondas']) if 'dt_plano_rondas' in tx else ''
    check('el plano: rondas y relevos en el mapa mental', d.fact_known('plano_rondas') and d.fact_known('plano_relevos') and ':' in rondas, rondas[:80])
    aparte(); yield 0.3
    # 3) tabaco: el que pasa se para a fumar
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry') and len(g.get_editor_property('patrol_points')) >= 2 and not g.get_actor_label().endswith('Ramos')]
    g = ronda[0]
    l = g.get_actor_location(); f = g.get_actor_forward_vector()
    p = jugador()
    p.set_actor_location(V(l.x + f.x * 260, l.y + f.y * 260, max(p.get_actor_location().z, 100)), False, True)
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0, 0, math.degrees(math.atan2(-f.y, -f.x)) + 180)); yield 0.2
    d.simulate_key('Five'); yield 0.2
    d.use_item(); yield 0.2
    check('el tabaco, en el suelo', d.cigs_on_floor() == 1 and d.item_count(4) == 2, d.cigs_on_floor())
    aparte(); yield 0.2
    g.hold(0.0)
    yield ('hasta', lambda: director().get_editor_property('cigs_smoked') >= 1, 25.0)
    check('el guardia se para, la coge y fuma (con su ascua)', d.get_editor_property('cigs_smoked') == 1 and d.is_smoking(g), estado(g))
    g.hold(3600.0)
    # 4) somnífero en la olla: el que viene a comer se duerme
    d.set_editor_property('sleep_delay', 3.0)
    pot = d.get_editor_property('sleep_pot_loc')
    tp(pot.x + 120, pot.y, 180.0); yield 0.3
    d.simulate_key('Six'); yield 0.2
    d.use_item(); yield 0.2
    check('somnífero en la olla', d.get_editor_property('pot_drugged') and d.item_count(5) == 1, d.item_count(5))
    aparte(); yield 0.2
    h = [x for x in ronda if x != g][0]
    h.set_actor_location(V(pot.x + 500, pot.y, suelo_z(w, V(pot.x + 500, pot.y, 0)) + 95), False, True)
    h.hold(0.0)
    yield ('hasta', lambda: director().get_editor_property('slept_by_drug') >= 1, 120.0)
    check('el que viene a comer se duerme al rato (dormido, no muerto)', d.get_editor_property('slept_by_drug') >= 1 and estado(h) == 'DOWN', estado(h))
    h.hold(3600.0)
    # cantimplora: por la espalda
    k = [x for x in ronda if x not in (g, h) and estado(x) != 'DOWN'][0]
    detras_de(k, 90.0); yield 0.3
    d.use_item(); yield 0.2
    yield ('hasta', lambda: estado(k) == 'DOWN', 12.0)
    check('en la cantimplora de uno, por la espalda: se duerme', estado(k) == 'DOWN' and d.item_count(5) == 0, estado(k))
    aparte(); yield 0.3
    # 5) cizalla: la valla del anillo oeste (fila 10), un paso en la malla
    hit = None
    for x in range(-1500, -150, 50):
        r = unreal.SystemLibrary.line_trace_single(w, V(x, 1800, 110), V(x, 2400, 110), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        if r and r.to_tuple()[9] and r.to_tuple()[9].get_actor_label().startswith('valla') and abs(x + 450) > 150:
            hit = r.to_tuple()[4]; break
    check('hay malla de valla donde probar', hit is not None)
    if hit:
        p = jugador()
        p.set_actor_location(V(hit.x, hit.y - 80, max(p.get_actor_location().z, 100)), False, True)
        unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0, 0, 90)); yield 0.3
        z0 = p.get_actor_location().z
        p.set_actor_location(V(hit.x, hit.y + 80, z0), True, False); yield 0.1
        check('sin cortar, la malla no se pasa', p.get_actor_location().y < hit.y, '%.0f' % (p.get_actor_location().y - hit.y))
        p.set_actor_location(V(hit.x, hit.y - 80, z0), False, True); yield 0.2
        d.simulate_key('MouseScrollDown'); yield 0.1
        while d.get_editor_property('item_sel') != 6:
            d.simulate_key('MouseScrollDown'); yield 0.1
        d.use_item(); yield 0.3
        check('cortada con la cizalla', d.get_editor_property('fence_cuts_made') == 1, d.get_editor_property('fence_cuts_made'))
        p.set_actor_location(V(hit.x, hit.y - 40, z0), True, False); yield 0.2
        p.set_actor_location(V(hit.x, hit.y + 80, z0), True, False); yield 0.2
        check('por el corte se pasa', p.get_actor_location().y > hit.y + 40, '%.0f' % (p.get_actor_location().y - hit.y))
        aparte(); yield 0.2
        # de día, el que lo ve da la alarma
        d.set_day(True); yield 0.3
        c = ronda[-1]
        c.set_actor_location(V(hit.x + 30, hit.y - 450, suelo_z(w, V(hit.x + 30, hit.y - 450, 0)) + 95), False, True)
        c.set_actor_rotation(unreal.Rotator(0, 0, 90), False); yield 1.0
        check('de día, el que ve el corte da la alarma', d.get_editor_property('fence_cuts_found') == 1 and d.get_editor_property('tension_t') > 100.0, '%d %.0f' % (d.get_editor_property('fence_cuts_found'), d.get_editor_property('tension_t')))
        d.set_day(False)
    # 6) walkie: de un caído, con la T; y una orden falsa
    v = [x for x in ronda if estado(x) != 'DOWN' and x not in (g,)][0]
    derribar(v); yield 1.0
    junto_a(v, 70.0); yield 0.3
    check('junto a un caído, la T le quita el walkie', 'WALKIE' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interrogate(); yield 0.3
    check('walkie cogido (y en mano)', d.has_walkie() and d.get_editor_property('item_sel') == 7)
    aparte(); yield 0.2
    libres = [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and not x.get_actor_label().endswith('Ramos')]
    for x in libres:
        x.hold(0.0)
    if libres:
        q = libres[0].get_actor_location()
        tp(q.x + 600, q.y)
    yield 0.3
    d.use_item(); yield 0.5
    van = [x.get_actor_label() for x in libres if x.is_on_errand()]
    check('orden falsa: van dos a otra zona', d.get_editor_property('fake_order_used') and len(van) == 2, van)
    d.use_item(); yield 0.3
    check('una sola vez', 'colaria' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:40])
    for x in guardias():
        x.hold(3600.0)
    # 7) espejo: mantener el clic
    d.simulate_key('MouseScrollDown'); yield 0.1
    while d.get_editor_property('item_sel') != 8:
        d.simulate_key('MouseScrollDown'); yield 0.1
    d.use_item(); yield 0.4
    check('el espejo: con el clic, una vista por la esquina', d.get_editor_property('mirror_on'))
    d.use_item_release(); yield 0.2
    check('al soltar, se guarda', not d.get_editor_property('mirror_on'))
    check('ningún texto pedido falta', not list(d.get_editor_property('missing_texts')), list(d.get_editor_property('missing_texts')))

def prueba_pulido():
    """Tanda J. Pulido: la cizalla deja un agujero en la malla (material) con su solapa; el ascua del que fuma se aviva
    en cada calada y echa humo; el cable brilla con la linterna; objetos, trampas y cortes vuelven con el punto de
    control; el plano dibuja rondas y relevos; los guardias lejos animan a menos pasos; los cajones grandes caben."""
    w = mundo()
    d = director()
    for g in guardias():
        g.hold(3600.0)
    aparte(); yield 0.3
    # 1) el cable con la linterna (el pasillo de tablones de la prueba de trampas)
    d.set_editor_property('trap_cans', 2); d.set_editor_property('trap_wires', 1)
    d.set_day(False); yield 0.3
    px, py0, py1 = -1050, 600, 1200
    tp(px, (py0 + py1) / 2 - 80, 90.0); yield 0.3
    _agachado(d); yield 0.4
    d.interact(); yield 0.3
    check('cable tendido', d.trap_count() == 1 and d.trap_kind(0) == 1, d.trap_count())
    _agachado(d, False); yield 0.3
    cab = d.trap_loc(0)
    tp(px, py0 - 250, 90.0); yield 0.3
    mirar(V(cab.x, cab.y, cab.z + 12)); yield 0.2
    d.set_torch(False); yield 0.3
    sin = d.get_editor_property('wire_glint')
    d.set_torch(True); yield 0.4
    con = d.get_editor_property('wire_glint')
    check('el cable brilla con la linterna (y sin ella, no)', sin == 0.0 and con > 0.3, '%.2f -> %.2f' % (sin, con))
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0, 0, -90)); yield 0.3
    check('mirando a otro lado, no brilla', d.get_editor_property('wire_glint') < 0.05, '%.2f' % d.get_editor_property('wire_glint'))
    d.set_torch(False)
    # 2) la cizalla: agujero de verdad y la solapa de malla
    d.set_editor_property('trap_wires', 0)
    hit = None
    for x in range(-1500, -150, 50):
        r = unreal.SystemLibrary.line_trace_single(w, V(x, 1800, 110), V(x, 2400, 110), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [], unreal.DrawDebugTrace.NONE, True)
        if r and r.to_tuple()[9] and r.to_tuple()[9].get_actor_label().startswith('valla') and abs(x + 450) > 150:
            hit = r.to_tuple()[4]; break
    check('hay malla donde cortar', hit is not None)
    if hit:
        d.set_flag('obj_cizalla'); yield 0.2
        p = jugador()
        p.set_actor_location(V(hit.x, hit.y - 80, max(p.get_actor_location().z, 100)), False, True)
        unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0, 0, 90)); yield 0.3
        d.select_item(6); yield 0.1
        d.use_item(); yield 0.3
        check('el corte abre un agujero en la malla y deja la solapa de malla', d.fence_holes_open() == 1 and d.fence_flap_is_mesh(0), '%d %s' % (d.fence_holes_open(), d.fence_flap_is_mesh(0)))
        mpc = unreal.load_asset('/Game/Tarsis/Materiales/MPC_Cortes')
        kml = getattr(unreal, 'KismetMaterialLibrary', None) or getattr(unreal, 'MaterialLibrary', None)
        c0 = kml.get_vector_parameter_value(w, mpc, 'Corte0') if (mpc and kml) else None
        check('el material sabe dónde está el agujero', c0 is not None and c0.a > 30 and abs(c0.r - hit.x) < 60, str(c0))
    aparte(); yield 0.2
    # 3) el punto de control guarda objetos, trampas puestas y cortes
    d.set_editor_property('cigs', 2); d.set_editor_property('sleep_doses', 1)
    d.set_editor_property('trap_cans', 1)
    tp(px, 200, 90.0); yield 0.3
    _agachado(d); yield 0.4
    d.interact(); yield 0.3
    _agachado(d, False); yield 0.2
    traps = d.trap_count()
    d.test_checkpoint('PRUEBA'); yield 0.2
    d.set_editor_property('cigs', 0); d.set_editor_property('sleep_doses', 0)
    d.set_editor_property('trap_cans', 0)
    d.test_load_checkpoint(); yield 0.5
    check('al cargar: tabaco, somnifero y latas como en el punto de control', d.get_editor_property('cigs') == 2 and d.get_editor_property('sleep_doses') == 1 and d.get_editor_property('trap_cans') == 0,
          '%d %d %d' % (d.get_editor_property('cigs'), d.get_editor_property('sleep_doses'), d.get_editor_property('trap_cans')))
    check('al cargar: las trampas puestas y el corte siguen', d.trap_count() == traps and d.fence_holes_open() == (1 if hit else 0), '%d/%d %d' % (d.trap_count(), traps, d.fence_holes_open()))
    yield 0.6
    check('las cajetillas no se suman otra vez al cargar', d.get_editor_property('cigs') == 2, d.get_editor_property('cigs'))
    aparte(); yield 0.2
    # 4) el ascua y el humo
    ronda = [g for g in guardias() if not g.get_editor_property('tower_sentry') and len(g.get_editor_property('patrol_points')) >= 2 and not g.get_actor_label().endswith('Ramos')]
    g = ronda[0]
    l = g.get_actor_location(); f = g.get_actor_forward_vector()
    p = jugador()
    p.set_actor_location(V(l.x + f.x * 260, l.y + f.y * 260, max(p.get_actor_location().z, 100)), False, True)
    mirar(l); yield 0.2
    d.select_item(4); yield 0.1
    d.use_item(); yield 0.2
    aparte(); yield 0.2
    g.hold(0.0)
    yield ('hasta', lambda: director().get_editor_property('cigs_smoked') >= 1, 30.0)
    check('se para a fumar', d.is_smoking(g), estado(g))
    g.hold(3600.0)
    glows = []
    p0 = d.get_editor_property('smoke_puffs')
    for _ in range(36):
        yield 0.25
        glows.append(d.ember_glow(g))
    check('el ascua se ve (una brasa, no solo luz)', d.ember_visible(g))
    check('en cada calada se aviva y luego vuelve a casi nada', max(glows) > 0.7 and min(glows) < 0.3, '%.2f..%.2f' % (min(glows), max(glows)))
    check('al soltar la calada, humo', d.get_editor_property('smoke_puffs') > p0, '%d -> %d' % (p0, d.get_editor_property('smoke_puffs')))
    # 5) el plano en el mapa mental
    check('el plano tiene la planta de la base', len(d.get_editor_property('plan_rows')) > 10, len(d.get_editor_property('plan_rows')))
    d.learn_fact('plano_rondas'); yield 0.2
    check('con el plano, el mapa mental lo dibuja', d.plan_known())
    d.set_editor_property('relief_rule', True); yield 0.5   # (en las pruebas va apagado)
    hay = d.relief_post_count() > 0 and d.relief_post_loc(0).length() > 100
    check('las torres del relevo, en su sitio', hay, d.relief_post_count())
    d.set_editor_property('relief_rule', False)
    d.toggle_mind_map(); yield 0.4
    check('el mapa mental se abre con el plano', d.get_editor_property('mind_map'))
    d.toggle_mind_map(); yield 0.3
    # 6) animación por distancia
    yield 0.6
    pl = jugador().get_actor_location()
    lejos = [x for x in guardias() if (x.get_actor_location() - pl).length() > 4000 and estado(x) != 'DOWN']
    cerca = [x for x in guardias() if (x.get_actor_location() - pl).length() < 1200 and estado(x) != 'DOWN']
    check('los guardias muy lejos animan a menos pasos', not lejos or all(d.anim_lod_level(x) == 2 for x in lejos), [d.anim_lod_level(x) for x in lejos][:6])
    # 7) los cajones grandes: caben un cuerpo
    cajones = [a for a in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.StaticMeshActor) if a.get_actor_label() in ('Atrezo_han_cajon_e3', 'Atrezo_han_cajon_f3', 'Atrezo_jef_baul')]
    largos = [round(max(a.get_actor_bounds(False)[1].x, a.get_actor_bounds(False)[1].y) * 2) for a in cajones]
    check('los tres cajones de esconder cuerpos miden más de 1,9 m', len(largos) == 3 and min(largos) >= 190, largos)
    d.set_day(True)
    check('ningún texto pedido falta', not list(d.get_editor_property('missing_texts')), list(d.get_editor_property('missing_texts')))

def prueba_revolverse():
    """Tanda K. Revolverse: cuando van a detenerte, un instante para la E; a tiempo le quitas el fusil (al suelo, con
    física) y queda aturdido (la E lo derriba); si no, la detención de siempre. Al que te apunta en el alto, de cerca, la E
    le golpea el fusil; desarmado va a por él (o lo recoge otro que pase). El fusil recogido entra en el selector: matar
    y hacer ruido. La ventana se acorta en DIFÍCIL, herido o con dos encima, y todo vuelve con el punto de control."""
    w = mundo()
    d = director()
    P = lambda k: director().get_editor_property(k)
    ronda = lambda: [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) == 'PATROL' and not x.get_actor_label().endswith('Ramos') and not x.get_editor_property('disarmed')]
    yield ('hasta', lambda: len(ronda()) > 3, 30.0)
    rs = ronda()
    for x in guardias():
        x.hold(3600.0)
    d.set_editor_property('wounds', 0)
    # 1) la ventana y la E a tiempo
    g = rs[0]
    junto_a(g, 110.0); yield 0.3
    w1 = d.counter_window_now(g)
    d.counter_or_capture(g); yield 0.05
    check('van a detenerte: se abre la ventana (unos 0,6 s) con su aviso', P('counter_open') and 0.4 < P('counter_len') < 0.9 and 'REVOLVERSE' in str(d.interact_prompt()), '%.2f %s' % (P('counter_len'), d.interact_prompt()))
    d.interact(); yield 0.3
    g.hold(3600.0)
    check('a tiempo: le quitas el fusil y queda aturdido', P('counters') == 1 and g.get_editor_property('disarmed') and g.is_stunned() and not P('capturing'), '%s %s %s' % (P('counters'), g.get_editor_property('disarmed'), estado(g)))
    check('el fusil sale despedido al suelo', d.floor_rifle_count() == 1, d.floor_rifle_count())
    check('y pide refuerzos', any(str(x).endswith('_desarmado') for x in P('voice_log')), [str(x) for x in P('voice_log')][-3:])
    check('tanda L: se ve el golpe de Cuttlas (brazos hacia delante)', P('strikes') >= 1, P('strikes'))
    # tanda L: la E por mirada, junto al fusil del suelo y con él aturdido a mano
    rl0 = d.floor_rifle_loc(0)
    if g.is_stunned():
        mirar(V(rl0.x, rl0.y, rl0.z)); yield 0.05
        a_fusil = str(d.interact_prompt())
        gl0 = g.get_actor_location()
        mirar(V(gl0.x, gl0.y, gl0.z + 20)); yield 0.05
        a_guardia = str(d.interact_prompt())
        if dist2d(rl0, jugador().get_actor_location()) < 140:
            check('tanda L: mirando el fusil, E lo recoge; mirando al guardia, E lo derriba', 'RECOGER' in a_fusil and 'DERRIBAR' in a_guardia, '%s | %s' % (a_fusil, a_guardia))
    check('aturdido, la E lo derriba', 'DERRIBAR' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 0.4
    check('derribado', estado(g) == 'DOWN', estado(g))
    # 2) recoger el fusil
    yield 1.5
    rl = d.floor_rifle_loc(0)
    p = jugador()
    p.set_actor_location(V(rl.x + 60, rl.y, max(rl.z + 95, 100)), False, True); yield 0.3
    check('junto al fusil: E   RECOGER EL FUSIL', 'RECOGER EL FUSIL' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 0.2
    yield 0.3
    check('tanda L: el fusil en tus manos (primera persona)', d.fp_rifle_shown(), d.fp_rifle_shown())
    check('recogido: en el selector, con cartuchos', d.floor_rifle_count() == 0 and P('player_rifle_ammo') > 0 and P('item_sel') == 9 and d.item_name(9) == 'FUSIL', '%d %d' % (P('player_rifle_ammo'), P('item_sel')))
    # 6) al que te apunta en el alto, de cerca, le golpeas el fusil; luego va a por él
    h = rs[2]
    d.set_editor_property('armed_aim', 0.0)
    d.set_editor_property('player_speed_override', 0.0)
    d.set_editor_property('armed_rule', True)   # (en las pruebas va apagado)
    d.set_day(True); yield 0.3   # de día y a la vista: te ve seguro
    a_la_vista_de(h, 700)
    h.hold(0.0)
    h.set_editor_property('view_distance', 3000.0)
    for _ in range(3):
        h.alarm(jugador().get_actor_location())
        yield ('hasta', lambda: director().get_editor_property('halt'), 6.0)
        if P('halt'):
            break
        a_la_vista_de(h, 600); yield 0.2
    check('te apunta (el alto)', P('halt'), '%s vis=%.2f d=%.0f oculto=%s celda=%s' % (estado(h), h.visibility(jugador()), dist2d(h.get_actor_location(), jugador().get_actor_location()), jugador().get_editor_property('hidden'), estado(h)))
    lejos = 'GOLPEAR' not in str(d.interact_prompt())
    hl = h.get_actor_location(); pl = jugador().get_actor_location()
    dd = (pl - hl); dd.z = 0
    n = dd.length() or 1.0
    jugador().set_actor_location(V(hl.x + dd.x / n * 150, hl.y + dd.y / n * 150, pl.z), False, True); yield 0.15
    check('lejos no vale; a menos de 2,2 m: E   GOLPEAR EL FUSIL', lejos and 'GOLPEAR' in str(d.interact_prompt()), str(d.interact_prompt()))
    d.interact(); yield 0.2
    check('le golpeas el fusil: al suelo', h.get_editor_property('disarmed') and d.floor_rifle_count() == 1, '%s %d' % (h.get_editor_property('disarmed'), d.floor_rifle_count()))
    s0 = P('shots')
    aparte(); yield 0.3
    r0 = P('rifles_recovered')
    yield ('hasta', lambda: director().get_editor_property('rifles_recovered') > r0, 25.0)
    check('desarmado, no dispara y va a por su fusil (y lo recoge)', P('shots') == s0 and not h.get_editor_property('disarmed') and d.floor_rifle_count() == 0, '%s %d %s' % (h.get_editor_property('disarmed'), d.floor_rifle_count(), estado(h)))
    d.set_day(False)
    d.set_editor_property('armed_rule', False)
    d.set_editor_property('player_speed_override', -1.0)
    h.hold(3600.0)
    # 3) disparar: letal y se oye
    t = rs[1]
    lt = t.get_actor_location()
    a_la_vista_de(t, 500); yield 0.2
    mirar(V(lt.x, lt.y, lt.z + 30)); yield 0.2
    k0, a0 = P('kills'), P('player_rifle_ammo')
    d.use_item(); yield 0.3
    check('disparar con el fusil mata', P('kills') == k0 + 1 and t.get_editor_property('dead') and P('player_rifle_ammo') == a0 - 1, '%d %s' % (P('kills'), estado(t)))
    check('y se oye: la base en guardia', P('tension_t') > 100.0, P('tension_t'))
    # 4) el punto de control
    d.test_checkpoint('PRUEBA K'); yield 0.2
    am = P('player_rifle_ammo')
    d.set_editor_property('player_rifle_ammo', 0)
    d.test_load_checkpoint(); yield 0.4
    check('al cargar, el fusil y sus cartuchos', P('player_rifle_ammo') == am, '%d/%d' % (P('player_rifle_ammo'), am))
    # 5) la ventana se acorta: DIFÍCIL, herido
    # (la dificultad la elige quien juega en Opciones: aquí se mira que la ventana sigue a la suya)
    dif = P('difficulty')
    mul = P('counter_easy_mul') if dif <= 0 else (P('counter_hard_mul') if dif >= 2 else 1.0)
    wn = d.counter_window_now(rs[2])
    d.set_editor_property('wounds', 1)
    wh = d.counter_window_now(rs[2])
    d.set_editor_property('wounds', 0)
    check('ventana: FÁCIL la alarga, DIFÍCIL la acorta; herido, más corta', abs(wn - P('counter_window') * mul) < 0.02 and P('counter_easy_mul') > 1.0 > P('counter_hard_mul') and wh < wn,
          'dificultad %d: %.2f (esperada %.2f), herido %.2f' % (dif, wn, P('counter_window') * mul, wh))
    # 7) un fusil sin dueño que lo busque: lo recoge el primero que pase
    o, q = rs[3], [x for x in ronda() if x not in rs[:4]]
    junto_a(o, 110.0); yield 0.2
    d.test_disarm(o); yield 0.3
    derribar(o); yield 1.5
    aparte(); yield 0.2
    if q:
        r = q[0]
        rl = d.floor_rifle_loc(0)
        r.set_actor_location(V(rl.x + 300, rl.y, r.get_actor_location().z), False, True)
        r.hold(0.0); yield 0.2
        r0 = P('rifles_recovered')
        yield ('hasta', lambda: director().get_editor_property('rifles_recovered') > r0, 30.0)
        check('otro que pasa lo ve y lo recoge', d.floor_rifle_count() == 0, '%d %s' % (d.floor_rifle_count(), estado(r)))
        r.hold(3600.0)
    # 8) fallar: la detención de siempre (al final: acaba en captura)
    f = [x for x in guardias() if not x.get_editor_property('tower_sentry') and estado(x) != 'DOWN' and not x.get_editor_property('disarmed') and not x.get_actor_label().endswith('Ramos')][0]
    junto_a(f, 110.0); yield 0.2
    c0, f0 = P('captures'), P('counter_fails')
    d.counter_or_capture(f)
    yield ('hasta', lambda: director().get_editor_property('capturing') or director().get_editor_property('captures') > c0, 4.0)
    check('si no te revuelves a tiempo, te detienen', P('counter_fails') == f0 + 1 and (P('capturing') or P('captures') > c0), '%d %s' % (P('counter_fails'), P('capturing')))
    yield ('hasta', lambda: not director().get_editor_property('capturing'), 25.0)
    check('ningún texto pedido falta', not list(P('missing_texts')), list(P('missing_texts')))

FAMILIAS = [[prueba_intro, prueba_datos, prueba_zona, prueba_empezar], [prueba_guardias], [prueba_menu, prueba_musica, prueba_controles, prueba_opciones],
            [prueba_frente], [prueba_captura, prueba_perdido, prueba_calma], [prueba_dardos, prueba_punto_control, prueba_cambios, prueba_farol, prueba_final],
            [prueba_escondites], [prueba_cuerpo], [prueba_generador], [prueba_reserva], [prueba_perimetro, prueba_desgaste, prueba_charcos], [prueba_anillo, prueba_camion, prueba_viaje], [prueba_puertas],
            [prueba_mojado, prueba_carteles, prueba_cobertura, prueba_gestos], [prueba_materia, prueba_cielo], [prueba_foco], [prueba_sombra], [prueba_farola], [prueba_radio], [prueba_apoyo], [prueba_codec], [prueba_esquinas], [prueba_linternas], [prueba_emisora], [prueba_calabozo], [prueba_equipo], [prueba_armados], [prueba_hangar], [prueba_cruce], [prueba_charlas], [prueba_bengala], [prueba_tactica, prueba_apuntar, prueba_tercera], [prueba_perro, prueba_lobo_piedra, prueba_lobo_caricia], [prueba_lobo_paso], [prueba_fusil, prueba_centinela], [prueba_fisica], [prueba_huellas], [prueba_relevo], [prueba_relleno], [prueba_paso], [prueba_ausencias], [prueba_sabotaje], [prueba_escondidos], [prueba_pulso], [prueba_trampas], [prueba_trampas_luz], [prueba_emboscada], [prueba_disparo], [prueba_letal], [prueba_vias], [prueba_mira], [prueba_objetos], [prueba_pulido], [prueba_revolverse]]
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
        d.set_editor_property('third', False)
        d.set_editor_property('dog', siguiente in (prueba_perro, prueba_lobo_piedra, prueba_lobo_caricia, prueba_lobo_paso))
        # tanda D: las huellas y el relevo, solo en sus pruebas (sacan a los guardias de su sitio y cambian las torres)
        d.set_editor_property('print_rule', siguiente is prueba_huellas)
        d.set_editor_property('relief_rule', siguiente is prueba_relevo)   # tanda 46: el perro solo ronda en su prueba (en las del hangar ladraria y traeria guardias)
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
