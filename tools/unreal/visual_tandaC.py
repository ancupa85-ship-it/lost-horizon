"""Tanda C: fotos de lo nuevo, en PIE de dia. Escenas (builtins._tandaC_escenas): fusil (de ronda y apuntando, culata al
hombro), centinela (el de la torre con su M14), caricia (la mano sobre el lomo del lobo), piedra (en la boca del lobo),
dardo (un guardia cae con ragdoll) y arrastre (el cuerpo arrastrado de los hombros). Espera en tiempo de JUEGO (cada
HighResShot frena el juego) y con el codec y las charlas apagados (el codec pausa el PIE).
Capturas en D:\\LostHorizon\\capturas-tandaC\\<escena>_NN.png y lo medido en tandaC_medidas.txt."""
import builtins, glob, math, os, shutil, time
import unreal

OUT = getattr(builtins, '_tandaC_out', r'D:\LostHorizon\capturas-tandaC')
SHOTS = os.path.join(unreal.Paths.project_saved_dir(), 'Screenshots')
V = unreal.Vector
ESCENAS = getattr(builtins, '_tandaC_escenas', ['fusil', 'centinela', 'caricia', 'piedra', 'dardo', 'arrastre'])
S = {'estado': 'arrancando', 'h': None, 'gen': None, 'espera': 0.0, 'L': [], 'pedidas': [], 'antes': set()}
builtins._visual_tandaC = S


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()


def director(w):
    return unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector'))[0]


def guardias(w):
    return unreal.GameplayStatics.get_all_actors_of_class(w, unreal.load_class(None, '/Script/PruebaLumen.TarsisGuard'))


def foto(w, nombre, nota=''):
    unreal.SystemLibrary.execute_console_command(w, 'HighResShot 1600x900')
    S['pedidas'].append(nombre)
    S['L'].append('%s  %s' % (nombre, nota))


def recoger():
    nuevas = sorted(set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True)) - S['antes'], key=os.path.getmtime)
    for f, nombre in zip(nuevas, S['pedidas']):
        shutil.move(f, os.path.join(OUT, nombre + '.png'))
    if len(nuevas) != len(S['pedidas']):
        S['L'].append('AVISO: pedidas %d fotos, salieron %d' % (len(S['pedidas']), len(nuevas)))
    S['antes'] = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
    S['pedidas'] = []


def juego(s):
    t0 = unreal.GameplayStatics.get_time_seconds(mundo())
    while unreal.GameplayStatics.get_time_seconds(mundo()) - t0 < s:
        yield 0.05


def mirar(w, punto, altura=0.0):
    cam = unreal.GameplayStatics.get_player_camera_manager(w, 0).get_camera_location()
    unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.MathLibrary.find_look_at_rotation(cam, V(punto.x, punto.y, punto.z + altura)))


def poner(w, x, y, z):
    p = unreal.GameplayStatics.get_player_pawn(w, 0)
    p.set_actor_location(V(x, y, z), False, True)


def de_lado(w, g, lado=280.0, delante=120.0, alto=20.0):
    l = g.get_actor_location(); f = g.get_actor_forward_vector(); r = g.get_actor_right_vector()
    poner(w, l.x + r.x * lado + f.x * delante, l.y + r.y * lado + f.y * delante, l.z + alto)


def pasos():
    w = mundo()
    d = director(w)
    if d.get_editor_property('cine'):
        d.interact()
    for k in ('codec_calls', 'radio_chat', 'talk_rule', 'talk_cross', 'truck'):
        try:
            d.set_editor_property(k, False)
        except Exception:
            pass
    yield 4.0
    d.set_day(True)
    yield 1.0
    unreal.SystemLibrary.execute_console_command(w, 'showhud')
    os.makedirs(OUT, exist_ok=True)
    S['antes'] = set(glob.glob(os.path.join(SHOTS, '**', '*.png'), recursive=True))
    for g in guardias(w):
        g.set_editor_property('view_distance', 1.0)
    ronda = [g for g in guardias(w) if not g.get_editor_property('tower_sentry') and g.uses_gasp()]
    if 'fusil' in ESCENAS and ronda:
        g = ronda[0]
        g.hold(10.0)
        yield 0.5
        de_lado(w, g, 260, 140)
        yield 0.3
        mirar(w, g.get_actor_location(), 25.0)
        yield from juego(0.4)
        foto(w, 'fusil_cadera', 'culata a %.0f cm del hombro' % (g.rifle_butt() - g.rifle_shoulder()).length())
        yield from juego(0.3)
        l = g.get_actor_location(); f = g.get_actor_forward_vector()
        g.alarm(V(l.x + f.x * 900, l.y + f.y * 900, l.z))
        yield from juego(2.0)
        g.hold(10.0)
        yield from juego(0.8)
        de_lado(w, g, 220, 110)
        yield 0.3
        mirar(w, g.get_actor_location(), 45.0)
        yield from juego(0.4)
        b, s, m = g.rifle_butt(), g.rifle_shoulder(), g.rifle_muzzle()
        foto(w, 'fusil_apuntando', 'apunta %s, culata a %.1f cm del hombro, boca %+.0f cm sobre la culata' % (g.rifle_aiming(), (b - s).length(), m.z - b.z))
        yield from juego(0.3)
        # de frente, un poco ladeado: la cara junto a la culata
        l = g.get_actor_location(); f = g.get_actor_forward_vector(); r = g.get_actor_right_vector()
        poner(w, l.x + f.x * 260 + r.x * 90, l.y + f.y * 260 + r.y * 90, l.z + 30)
        yield 0.3
        mirar(w, g.get_actor_location(), 55.0)
        yield from juego(0.4)
        foto(w, 'fusil_apuntando_frente', '')
        yield from juego(0.3)
        # uno andando (el vaiven)
        if len(ronda) > 1:
            for x in ronda[1:]:
                x.hold(0.0)
            yield from juego(2.0)
            a = max(ronda[1:], key=lambda x: x.get_velocity().length())
            de_lado(w, a, 300, 200)
            yield 0.2
            mirar(w, a.get_actor_location(), 25.0)
            yield from juego(0.2)
            foto(w, 'fusil_andando', 'vaiven %.2f, %.0f cm/s' % (a.rifle_sway(), a.get_velocity().length()))
        recoger()
    if 'centinela' in ESCENAS:
        ts = [g for g in guardias(w) if g.get_editor_property('tower_sentry')]
        cen = [g for g in ts if 'centinela' in g.get_actor_label().lower()] or ts
        if cen:
            g = cen[0]
            l = g.get_actor_location(); f = g.get_actor_forward_vector(); r = g.get_actor_right_vector()
            # en la misma plataforma, a un lado: se ve el fusil en sus manos
            poner(w, l.x + r.x * 230 + f.x * 140, l.y + r.y * 230 + f.y * 140, l.z + 25)
            yield 0.5
            mirar(w, g.get_actor_location(), 25.0)
            yield from juego(0.5)
            foto(w, 'centinela_torre', '%s fusil %s, boca a %.0f cm' % (g.get_actor_label(), g.has_rifle(), (g.rifle_muzzle() - g.get_actor_location()).length()))
            yield from juego(0.3)
            # desde abajo, a distancia
            poner(w, l.x + f.x * 900, l.y + f.y * 900, 120)
            yield 0.4
            mirar(w, g.get_actor_location(), 10.0)
            yield from juego(0.4)
            foto(w, 'centinela_desde_abajo', '')
        recoger()
    lobo = 'caricia' in ESCENAS or 'piedra' in ESCENAS
    if lobo:
        for x in guardias(w):
            x.hold(600.0)
        d.set_editor_property('dog', True)
        d.set_flag('perro_amigo')
        poner(w, 4950, 6000, 120)
        yield from juego(2.0)
    if 'piedra' in ESCENAS and d.dog_ready():
        l = d.dog_location()
        poner(w, l.x - 150, l.y - 400, l.z + 120)
        yield 0.3
        mirar(w, l, 30.0)
        yield from juego(0.4)
        r = unreal.GameplayStatics.get_player_controller(w, 0).get_control_rotation()
        unreal.GameplayStatics.get_player_controller(w, 0).set_control_rotation(unreal.Rotator(0.0, -18.0, r.yaw + 40.0))
        yield 0.2
        d.throw_stone()
        yield 0.1
        tam = d.last_stone_size()
        S['L'].append('piedra: %s %.1f x %.1f x %.1f cm' % (d.last_stone_mesh(), tam.x, tam.y, tam.z))
        hechas = 0
        for i in range(60):
            yield from juego(0.1)
            if d.dog_carrying() and hechas < 4:
                # de cerca, de lado: la piedra en la boca
                dl = d.dog_location(); fw = unreal.MathLibrary.get_forward_vector(unreal.Rotator(0, 0, d.dog_facing()))
                rt = unreal.MathLibrary.get_right_vector(unreal.Rotator(0, 0, d.dog_facing()))
                cam = V(dl.x + rt.x * 140 + fw.x * 90, dl.y + rt.y * 140 + fw.y * 90, dl.z + 70)
                poner(w, cam.x, cam.y, cam.z)
                yield 0.1
                mirar(w, d.dog_stone_location(), 0.0)
                yield 0.1
                mirar(w, d.dog_stone_location(), 0.0)
                yield 0.05
                foto(w, 'piedra_boca_%d' % hechas, 'busca %d lleva %s' % (d.get_editor_property('dog_fetch'), d.dog_carrying()))
                hechas += 1
                yield from juego(0.35)
            if d.get_editor_property('dog_fetch') == 0 and i > 5:
                break
        recoger()
    if 'caricia' in ESCENAS and d.dog_ready():
        d.dog_forget_pets()
        l = d.dog_location()
        gs = [g for g in guardias(w) if not g.get_editor_property('tower_sentry') and str(g.get_editor_property('state')).endswith('PATROL: 0>')]
        if gs:
            g = gs[-1]
            for x in guardias(w):
                x.hold(0.0 if x == g else 600.0)
            yield 0.3
            if hasattr(builtins, '_pet_off'):
                g.set_editor_property('pet_stand_off', builtins._pet_off)
            g.set_actor_location(V(l.x - 260, l.y + 60, g.get_actor_location().z), False, True)
            n = 0
            for i in range(40):
                yield from juego(0.4)
                pt = d.dog_petter()
                if pt and pt.pet_crouched() and pt.pet_hand_weight() > 0.9 and n < 4:
                    dl = d.dog_location()
                    gl = pt.get_actor_location()
                    sx, sy = dl.x - gl.x, dl.y - gl.y
                    nn = max(1.0, math.hypot(sx, sy))
                    # de lado a los dos: perpendicular a la linea guardia-lobo
                    poner(w, (dl.x + gl.x) / 2 - sy / nn * 230, (dl.y + gl.y) / 2 + sx / nn * 230, dl.z + 110)
                    yield 0.1
                    mirar(w, d.dog_back_location(), 0.0)
                    yield 0.1
                    mirar(w, d.dog_back_location(), 0.0)
                    yield 0.05
                    mano = (pt.left_hand_location() - d.dog_back_location()).length()
                    gl = pt.get_actor_location(); dl = d.dog_location()
                    foto(w, 'caricia_mano_%d' % n, 'mano a %.0f cm del lomo, guardia a %.0f cm del lobo, lobo anim %d' % (mano, math.hypot(gl.x - dl.x, gl.y - dl.y), d.dog_anim_index()))
                    n += 1
                if n >= 4 or (pt is None and i > 10):
                    break
        recoger()
    if 'dardo' in ESCENAS or 'arrastre' in ESCENAS:
        for x in guardias(w):
            x.hold(600.0)
        g = None
        for x in ronda:
            if str(x.get_editor_property('state')).endswith('PATROL: 0>'):
                g = x
        if g:
            l = g.get_actor_location(); f = g.get_actor_forward_vector(); r = g.get_actor_right_vector()
            poner(w, l.x + r.x * 380 + f.x * 120, l.y + r.y * 380 + f.y * 120, l.z + 20)
            yield 0.3
            mirar(w, g.get_actor_location(), 0.0)
            yield from juego(0.4)
            g.set_editor_property('knock_out_time', 100.0)
            if 'dardo' in ESCENAS:
                unreal.SystemLibrary.execute_console_command(w, 'slomo 0.25')
                g.dart_hit(V(-r.x, -r.y, 0.0)); g.knock_out()
                for i in range(12):
                    yield from juego(0.06)
                    mirar(w, g.pelvis_location(), 20.0)
                    foto(w, 'dardo_%02d' % i, 'reaccion %s ragdoll %s pelvis %.0f' % (g.hit_reacting(), g.is_ragdoll(), g.pelvis_location().z))
                unreal.SystemLibrary.execute_console_command(w, 'slomo 1')
                yield from juego(2.5)
                foto(w, 'dardo_reposo', 'ragdoll %s' % g.is_ragdoll())
                recoger()
            else:
                g.knock_out()
                yield from juego(3.0)
            if 'arrastre' in ESCENAS:
                p = unreal.GameplayStatics.get_player_pawn(w, 0)
                pl = g.pelvis_location()
                p.set_actor_location(V(pl.x + 90, pl.y, pl.z + 100), False, True)
                yield 0.3
                d.interact()
                yield from juego(0.3)
                S['L'].append('arrastre con fisica: %s' % d.drag_physics())
                s0 = p.get_actor_location()
                dx, dy = s0.x - pl.x, s0.y - pl.y
                nn = max(1.0, math.hypot(dx, dy)); dx, dy = dx / nn, dy / nn
                pc = unreal.GameplayStatics.get_player_controller(w, 0)
                for i in range(18):
                    p.set_actor_location(V(s0.x + dx * 20 * (i + 1), s0.y + dy * 20 * (i + 1), s0.z), True, False)
                    pc.set_control_rotation(unreal.Rotator(0.0, 0.0, math.degrees(math.atan2(dy, dx))))
                    yield from juego(0.1)
                # foto desde un lado: el que arrastra y el cuerpo
                c = p.get_actor_location()
                poner_cam = V(c.x - dy * 380 - dx * 120, c.y + dx * 380 - dy * 120, c.z + 60)
                d.interact()   # suelta, para poder mover la camara (el jugador) sin arrastrarlo
                yield from juego(0.1)
                # otra vez: agarrar y arrastrar mirando hacia atras para verlo
                p.set_actor_location(V(g.pelvis_location().x + dx * 90, g.pelvis_location().y + dy * 90, c.z), False, True)
                yield 0.2
                d.interact()
                yield from juego(0.3)
                s1 = p.get_actor_location()
                for i in range(10):
                    p.set_actor_location(V(s1.x + dx * 20 * (i + 1), s1.y + dy * 20 * (i + 1), s1.z), True, False)
                    pc.set_control_rotation(unreal.Rotator(0.0, -30.0, math.degrees(math.atan2(-dy, -dx))))
                    yield from juego(0.1)
                    if i in (4, 9):
                        foto(w, 'arrastre_%d' % i, 'fisica %s, pelvis a %.0f cm del suelo' % (d.drag_physics(), g.pelvis_location().z - (p.get_actor_location().z - 90)))
                d.interact()
                recoger()


def _fin():
    w = mundo()
    try:
        director(w).set_day(False)
    except Exception:
        pass
    unreal.SystemLibrary.execute_console_command(w, 'slomo 1')
    try:
        recoger()
    except Exception:
        pass
    with open(os.path.join(OUT, 'tandaC_medidas.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(S['L'] + ['estado: %s' % S['estado']]))


def _tick(dt):
    try:
        w = mundo()
        if S['estado'] == 'arrancando':
            if w and unreal.GameplayStatics.get_player_pawn(w, 0):
                S['estado'] = 'midiendo'
                S['gen'] = pasos()
            return
        if S['estado'] != 'midiendo':
            return
        if time.time() < S['espera']:
            return
        try:
            S['espera'] = time.time() + next(S['gen'])
        except StopIteration:
            S['estado'] = 'terminado'
            _fin()
            unreal.unregister_slate_post_tick_callback(S['h'])
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    except Exception:
        import traceback
        S['estado'] = 'error: %s' % traceback.format_exc()
        _fin()
        unreal.unregister_slate_post_tick_callback(S['h'])
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()


o = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
if o:
    o.set_editor_property('bThrottleCPUWhenNotForeground', False)
if mundo():
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
S['h'] = unreal.register_slate_post_tick_callback(_tick)
