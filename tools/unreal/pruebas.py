"""Pruebas automáticas de Tarsis en PIE: recorre lo principal del juego y escribe un informe PASA/FALLA.

Uso (en el editor, con el nivel Tarsis abierto; por ejecución remota de Python o desde la consola):
    py tools/unreal/pruebas.py
Arranca el PIE si no está en marcha, ejecuta las pruebas una tras otra con un ejecutor por ticks (cada prueba es un
generador que cede segundos de juego o una condición de espera) y deja el informe en
    Saved/Pruebas/informe_<fecha>.txt
El progreso queda en builtins._tarsis_pruebas (estado, prueba actual y resultados) para consultarlo desde fuera.

Las pruebas usan solo funciones y propiedades expuestas del Director y de los guardias (Interact, KeypadDigit, ShootDart,
PressKey, MenuLines, KnockOut...). No necesitan el teclado ni que la ventana tenga el foco.
"""
import builtins, math, os, time
import unreal

V = unreal.Vector
GEN = V(4300, 1700, 0)          # GeneratorLoc
SITIO = V(4300, 1980, 0)        # RepairSpot (GeneratorLoc + 0,280)
FAROL = V(6840, 5216, 380)      # farol de la garita
SALIDA = V(6900, 5300, 0)       # celda G (34, 26)


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
    p.set_actor_location(V(x, y, p.get_actor_location().z), False, True)
    unreal.GameplayStatics.get_player_controller(mundo(), 0).set_control_rotation(unreal.Rotator(0.0, 0.0, yaw))

def mirar(punto):
    p = jugador()
    cam = p.get_component_by_class(unreal.CameraComponent).get_world_location()
    unreal.GameplayStatics.get_player_controller(mundo(), 0).set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cam, punto))

def junto_a(g, d=90.0):
    l = g.get_actor_location()
    p = jugador()
    p.set_actor_location(V(l.x + d, l.y, p.get_actor_location().z), False, True)

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
        n = a.get_actor_label()
        if n.startswith('SpotLight'):
            n = 'farol_garita'
        (on if c.is_visible() else off).append(n)
    return sorted(on), sorted(off)

def luz_en(punto):
    return unreal.TarsisGuard.light_at(mundo(), punto)

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
    s0 = m.get_editor_property('steps_taken'); g0 = d.get_editor_property('guard_steps_played')
    l = m.get_actor_location(); tp(l.x + 500, l.y + 500, 0)
    yield 3.0
    check('los pasos de los guardias salen de la animación', m.get_editor_property('steps_taken') > s0, '%d -> %d' % (s0, m.get_editor_property('steps_taken')))
    check('y suenan cerca de ti', d.get_editor_property('guard_steps_played') > g0, '%d -> %d' % (g0, d.get_editor_property('guard_steps_played')))
    tp(500, 500, 0)
    # un ruido (lo mismo que llama la piedra): se para, gira el cuerpo con suavidad y la cabeza por delante, y lo dice
    d.set_subtitles(True)
    while estado(m) != 'PATROL':
        yield 0.5
    l = m.get_actor_location(); r = m.get_actor_right_vector()
    ruido = V(l.x + r.x * 700, l.y + r.y * 700, l.z)
    m.hear_noise(ruido)
    cabeza, pasos_giro, vmin = 0.0, False, 1e9
    for _ in range(12):
        yield 0.1
        cabeza = max(cabeza, abs(m.get_editor_property('look_yaw')))
        pasos_giro = pasos_giro or m.get_editor_property('turn_stepping')
        if estado(m) == 'SUSPICIOUS': vmin = min(vmin, m.get_velocity().length())
    l = m.get_actor_location()
    quiere = math.degrees(math.atan2(ruido.y - l.y, ruido.x - l.x))
    error = abs((quiere - m.get_actor_rotation().yaw + 540) % 360 - 180)
    check('se para al oír el ruido', vmin < 40, round(vmin))
    check('se gira hacia el ruido', error < 30, '%.0f grados de error' % error)
    check('la cabeza se adelanta al cuerpo', cabeza > 10, '%.0f grados' % cabeza)
    check('gira en el sitio dando pasos', pasos_giro)
    check('dice "¿qué ha sido eso?"', d.get_editor_property('last_voice') == 'moya_ruido', d.get_editor_property('last_voice'))
    check('con subtítulo', 'Que ha sido eso' in str(d.get_editor_property('subtitle')), d.get_editor_property('subtitle'))
    v = guardia('Vega')
    lv = v.get_actor_location()
    v.alarm(V(lv.x + 300, lv.y, lv.z)); yield 0.3   # a su lado, lejos de ti: que no te capture (la 1.ª captura es al calabozo)
    check('al dar la alarma: "¡alto!"', d.get_editor_property('last_voice') == 'vega_alto' and 'Alto' in str(d.get_editor_property('subtitle')), '%s | %s' % (d.get_editor_property('last_voice'), d.get_editor_property('subtitle')))
    faltan = ['%s_%s' % (g, k) for g in ('ibarra', 'moya', 'peris', 'vega', 'ramos', 'centinela') for k in ('quien', 'ruido', 'viento', 'alto', 'nadie', 'suelo')
              if not unreal.load_object(None, '/Game/Tarsis/Sonidos/voz_%s_%s.voz_%s_%s' % (g, k, g, k))]
    check('voces de los seis guardias importadas', not faltan, faltan)
    d.set_subtitles(False)
    # superficies: lo que pisas decide el sonido y lo lejos que se oyen tus pasos
    t1 = guardia('torre1').get_actor_location()
    sup = {'grava': V(4300, 2400, 100), 'madera': V(t1.x, t1.y, t1.z), 'metal': encima_de('contenedor_0'),
           'cemento': encima_de('base_suelo_int'), 'hierba': encima_de('base_marisma')}
    malas = {k: (d.surface_at(p) if p else None) for k, p in sup.items() if not p or d.surface_at(p) != k}
    check('superficies: grava, cemento, metal, madera, hierba', not malas, malas)
    # tus pasos dentro del barracón suenan a cemento
    p = jugador()
    p.set_actor_location(V(1130, 2850, p.get_actor_location().z), False, True)   # barracón oeste, junto a la litera de Ramos
    n0 = d.get_editor_property('player_steps')
    t0 = time.time()
    while time.time() - t0 < 3.0:
        # de un lado a otro del pasillo (0,3 s en cada sentido) sin salir del barracón
        p.add_movement_input(V(1 if int((time.time() - t0) / 0.3) % 2 == 0 else -1, 0, 0), 1.0); yield 0.03
    check('tus pasos suenan según el suelo', d.get_editor_property('player_steps') > n0 and d.get_editor_property('last_step_surface') == 'cemento',
          '%d pasos, %s' % (d.get_editor_property('player_steps') - n0, d.get_editor_property('last_step_surface')))
    tp(500, 500, 0)

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
    p = jugador(); p.set_actor_location(V(l.x - f.x * 500, l.y - f.y * 500, p.get_actor_location().z), False, True)
    mirar(V(l.x, l.y, l.z + 20)); yield 0.2
    d.shoot_dart(); yield 0.3
    check('el dardo duerme a Vega', estado(v) == 'DOWN' and d.get_editor_property('darts') == 4, '%s, %d dardos' % (estado(v), d.get_editor_property('darts')))
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
        pe.alarm(jugador().get_actor_location())
        l = pe.get_actor_location(); f = pe.get_actor_forward_vector()
        p = jugador(); p.set_actor_location(V(l.x + f.x * 120, l.y + f.y * 120, p.get_actor_location().z), False, True)
        yield ('hasta', lambda: director().get_editor_property('captures') >= c0 + n, 20.0)
        yield 0.3
        pos = jugador().get_actor_location()
        if n == 1:
            check('1.ª captura: al calabozo', 'CALABOZO' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:30])
        else:
            check('2.ª captura: vuelve junto a Ibarra', dist2d(pos, sitio) < 150, 'a %d cm del punto' % dist2d(pos, sitio))

def prueba_generador():
    d = director()
    on0, off0 = luces()
    tp(4300, 1910, -90); yield 0.1
    d.interact(); yield 0.1
    tp(500, 500, 0)
    check('se corta el generador', d.get_editor_property('power_off'))
    yield 3.0
    on, off = luces()
    check('apagón en cadena: todas las luces fuera', len(on) == 0, 'encendidas %s' % on)
    check('aviso por radio en su caja', 'Se ha ido la luz' in str(d.get_editor_property('radio')), str(d.get_editor_property('radio'))[:50])
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
    tp(500, 500, 0)
    # en cuanto llega a su sitio (si se espera a la radio de los 15 s, uno que esté cerca ya lo ha arreglado)
    yield ('hasta', lambda: reparador_cercano()[0] < 250, 30.0)
    dd, rep = reparador_cercano()
    check('el reparador está en su sitio', dd < 400, '%s a %d cm' % (rep.get_actor_label(), dd))
    derribar(rep)
    yield ('hasta', lambda: not director().get_editor_property('power_off'), 20.0)
    yield 0.5
    on, off = luces()
    check('vuelve la luz a medias', 'A MEDIAS' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:30])
    check('los focos de las torres vuelven', 'foco_torreta_12' in on and 'foco_torreta_13' in on, on)
    check('queda apagada la mitad del resto', 4 <= len(off) <= 7, 'apagadas %s' % off)
    check('el reparador sigue en el suelo', estado(rep) == 'DOWN', estado(rep))
    yield 6.0
    llegan = [g.get_actor_label()[8:] for g in guardias() if dist2d(g.get_actor_location(), GEN) < 400 and estado(g) != 'DOWN']
    check('los alertados por radio llegan al generador', len(llegan) >= 1, llegan)

def prueba_farol():
    d = director()
    antes = luz_en(V(6800, 5250, 130))
    tp(6350, 5250, 0); yield 0.1
    mirar(FAROL); yield 0.2
    d.shoot_dart(); yield 0.2
    tp(500, 500, 0); yield 0.3
    despues = luz_en(V(6800, 5250, 130))
    check('el dardo rompe el farol', 'FAROL ROTO' in str(d.get_editor_property('message')), str(d.get_editor_property('message'))[:30])
    check('el control queda a oscuras', despues < antes, '%.2f -> %.2f' % (antes, despues))

def prueba_final():
    d = director()
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
    p = jugador(); p.set_actor_location(V(l.x + f.x * 700, l.y + f.y * 700, p.get_actor_location().z), False, True)
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
    yield ('hasta', lambda: str(director().get_editor_property('subtitle')).startswith('['), 8.0)
    check('subtítulo de los pasos de un guardia', 'MOYA' in str(d.get_editor_property('subtitle')) or str(d.get_editor_property('subtitle')).startswith('['), d.get_editor_property('subtitle'))
    tp(500, 500, 0)
    # dejarlo todo como estaba
    yield from teclas(d, 'P', *(['Down'] * 11), 'Left', 'Down', 'Enter', 'Down', 'Enter', 'P')
    check('opciones restauradas', d.get_editor_property('difficulty') == 1 and 'TAMANO DEL TEXTO   < 100 %' in ' '.join(lineas(d)))


PRUEBAS = [prueba_intro, prueba_guardias, prueba_menu, prueba_musica, prueba_controles, prueba_opciones, prueba_dardos, prueba_punto_control,
           prueba_generador, prueba_reserva, prueba_farol, prueba_final]


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
    R['prueba'] = siguiente.__name__.replace('prueba_', '')
    yield from siguiente()

def _siguiente():
    while PRUEBAS:
        fn = PRUEBAS.pop(0)
        R['prueba'] = fn.__name__.replace('prueba_', '')
        R['gen'] = _limpieza(fn)
        R['espera'] = None
        return True
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
                _siguiente()
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
            if not _siguiente():
                R['estado'] = 'terminado'
                unreal.unregister_slate_post_tick_callback(R['h'])
                _informe()
    except Exception as ex:
        check('excepción', False, repr(ex))
        if not _siguiente():
            R['estado'] = 'terminado'
            unreal.unregister_slate_post_tick_callback(R['h'])
            _informe()

if mundo():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    R['estado'] = 'reiniciando'
else:
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
R['h'] = unreal.register_slate_post_tick_callback(_tick)
unreal.log('[Pruebas] en marcha: %d pruebas' % len(PRUEBAS))
