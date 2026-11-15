"""Cielo y luminarias de la noche de Tarsis (tanda 25).

Hasta la 24 el cielo era el degradado liso de la atmósfera y cada farola un disco de luz cortado a cuchillo sobre el
suelo, sin nada alrededor. Aquí, en el editor con el nivel Tarsis abierto (después de montar_base.py):
    py tools/unreal/cielo.py
  1) Cupula: una esfera enorme con el material M_Cielo (sin iluminar, «es cielo»: la recoge también la luz ambiente):
     degradado nocturno, estrellas (assets/unreal/texturas_propias/estrellas.png, tools/texturas/estrellas.py), la luna
     donde está la luz «Luna», con su halo, y nubes que pasan despacio. Con lluvia o niebla el director sube «Nublado»
     (MPC_Tarsis) y el cielo se cubre: sin estrellas ni luna, nubes bajas con el resplandor de la base en el horizonte.
  2) Halos: una esfera aditiva en cada luminaria (M_Halo: más fuerte en el centro, se pierde en el borde). Con el aire
     húmedo (Nublado) crecen. Etiqueta «halo»: el director los apaga con su luz (apagón, farol roto).
  3) Resplandor de relleno: junto a cada farola, una luz puntual floja, sin sombra y de radio largo (etiqueta
     «decorado»: no cuenta para el sigilo, ATarsisGuard::LightAt, y sigue a su farola). Hace dos cosas: la penumbra
     alrededor del charco de luz, y, sobre todo, el reflejo largo de la farola en el suelo mojado (el foco de la farola
     solo alumbra su cono: fuera de él no había nada que reflejar).
  4) M_Baston: el material encendido del bastón de señales de los guardias (ATarsisGuard::HoldBaton).
Todo va a la carpeta «Cielo» y se quita y se vuelve a poner cada vez.
"""
import os, sys, math
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ESTRELLAS_PNG = os.path.join(ROOT, 'assets', 'unreal', 'texturas_propias', 'estrellas.png')
DM = '/Game/Tarsis/Materiales'
CARPETA = 'Cielo'
ESFERA = '/Engine/BasicShapes/Sphere.Sphere'      # 100 cm de diámetro
V = unreal.Vector
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

# la bóveda: radio en cm (bien lejos de todo: la base mide 110 x 96 m con el anillo)
RADIO_CUPULA = 120000.0
# colores del cielo (lineales, en la escala de la exposición fija del nivel)
# Ajuste de la tanda 25 (25b), con sus capturas delante: el cielo salía azul marino de dibujo y sembrado de puntos blancos. Medido
# en las capturas, la curva de la imagen (exposición fija + tono de película) hace con lo oscuro, más o menos,
# pantalla = 7,4 x valor^1,6 por canal: hunde el rojo y el verde y deja el azul, así que un azul «algo saturado» aquí
# sale añil en pantalla. Ahora el cenit lleva la misma luminancia (la luz ambiente, que recoge la bóveda, no cambia de
# fuerza) con un tercio menos de azul; las nubes de noche rasa son velos algo más claros que el cielo (antes, borrones
# más oscuros que él), estirados por el viento; y el cielo cubierto ya no es más claro que el raso (con lluvia toda la
# base se ponía lechosa: el suelo mojado reflejaba un cielo el doble de luminoso).
CIELO = {
    'Cenit': (0.0045, 0.0080, 0.0200), 'Horizonte': (0.0100, 0.0160, 0.0300),
    'NubeLuz': (0.0150, 0.0200, 0.0300), 'NubeSombra': (0.0085, 0.0120, 0.0210),
    'Cubierto1': (0.0055, 0.0070, 0.0100), 'Cubierto2': (0.0100, 0.0125, 0.0170), 'Resplandor': (0.0140, 0.0090, 0.0040),
    'LunaColor': (0.80, 0.88, 1.00), 'EstrellaColor': (0.85, 0.92, 1.00),
}
# EstrellasRep 0,8: la textura (2048 px) cubre casi todo el cielo de una vez. EstiraNubes: cuánto se encoge el dibujo de
# las nubes a lo largo del viento (menos de 1 = bandas largas). NubeDura: lo cortado que es su borde.
ESCALARES = {'Brillo': 1.0, 'Claros': 0.60, 'EscalaNubes': 1.1, 'VelNubes': 0.006, 'EstrellasRep': 0.8, 'EstrellasFuerza': 0.7,
             'DiscoFuerza': 3.2, 'EstiraNubes': 0.35, 'NubeDura': 1.8}
# luminarias: prefijo de la etiqueta del actor de luz -> (diámetro del halo en cm, fuerza, lúmenes del relleno o 0).
# Ajuste 25b: el primer halo era una bola opaca de metro y medio colgada de cada farola (y otra tapándole la cabeza al
# centinela de la torre). Ahora en seco es un destello corto pegado a la lámpara (M_Halo, Caida 12: se apaga a un
# palmo) y solo con el aire húmedo se abre en un velo ancho y flojo (Niebla)
LUMINARIAS = {'farola': (170.0, 0.6, 250.0), 'foco_torreta': (40.0, 1.0, 0.0), 'aplique': (70.0, 0.5, 0.0),
              'Luz_PuertaNorte': (70.0, 0.5, 0.0)}
RELLENO_RADIO = 2400.0


def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def _mod(nombre):
    import importlib
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    m = importlib.import_module(nombre)
    importlib.reload(m)
    return m


def limpiar():
    for a in eas().get_all_level_actors():
        if str(a.get_folder_path()) == CARPETA:
            eas().destroy_actor(a)


def textura_estrellas():
    ruta = DM + '/T_Estrellas'
    if eal.does_asset_exist(ruta):
        t = eal.load_asset(ruta)
        if not os.path.exists(ESTRELLAS_PNG) or eal.get_metadata_tag(t, 'lh_fecha') == str(int(os.path.getmtime(ESTRELLAS_PNG))):
            return t
    if not os.path.exists(ESTRELLAS_PNG):
        log('AVISO: falta', ESTRELLAS_PNG, '(python tools/texturas/estrellas.py): cielo sin estrellas')
        return None
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', ESTRELLAS_PNG)
    t.set_editor_property('destination_path', DM)
    t.set_editor_property('destination_name', 'T_Estrellas')
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', False)
    tools.import_asset_tasks([t])
    tx = eal.load_asset(ruta)
    if tx is None:
        return None
    tx.set_editor_property('srgb', False)
    tx.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
    eal.set_metadata_tag(tx, 'lh_fecha', str(int(os.path.getmtime(ESTRELLAS_PNG))))
    eal.save_loaded_asset(tx, False)
    return tx


def _ayudas(g):
    """Atajos sobre un Grafo de ambiente.py: los nodos se colocan solos en filas."""
    X = unreal
    pos = [-2600, -1200]
    def xy():
        pos[0] += 170
        if pos[0] > -200:
            pos[0] = -2600; pos[1] += 150
        return pos[0], pos[1]
    class H:
        M, A, S, D, AP = (X.MaterialExpressionMultiply, X.MaterialExpressionAdd, X.MaterialExpressionSubtract,
                          X.MaterialExpressionDivide, X.MaterialExpressionAppendVector)
        @staticmethod
        def E(cls, **p):
            return g.E(cls, *xy(), **p)
        @staticmethod
        def esc(nombre, valor):
            return g.esc(nombre, valor, *xy())
        @staticmethod
        def vec(nombre, c):
            return g.E(X.MaterialExpressionVectorParameter, *xy(), parameter_name=nombre, default_value=X.LinearColor(c[0], c[1], c[2], 1))
        @staticmethod
        def op(cls, a, b):
            return g.op(cls, a, b, *xy())
        @staticmethod
        def f1(cls, ent, sal='', **p):    # «ent», no «a»: ComponentMask lleva la propiedad a=False
            n = g.E(cls, *xy(), **p)
            g.une(ent, n, ('Input', '', 'VectorInput'), sal)
            return n
        @staticmethod
        def sat(a):
            return H.f1(X.MaterialExpressionSaturate, a)
        @staticmethod
        def inv(a):
            return H.f1(X.MaterialExpressionOneMinus, a)
        @staticmethod
        def lerp(a, b, alfa):
            return g.lerp(a, b, alfa, *xy())
        @staticmethod
        def canal(src, k):
            return g.canal(src, k, *xy())
        @staticmethod
        def pot(a, e):
            n = g.E(X.MaterialExpressionPower, *xy(), const_exponent=float(e))
            g.une(a, n, 'Base')
            return n
        @staticmethod
        def punto(a, b):
            n = g.E(X.MaterialExpressionDotProduct, *xy())
            g.une(a, n, 'A'); g.une(b, n, 'B')
            return n
        @staticmethod
        def nublado():
            mats = _mod('materiales')
            mpc = mats.coleccion()
            if mpc is None:
                return g.E(X.MaterialExpressionConstant, *xy(), r=0.0)
            cp = g.E(X.MaterialExpressionCollectionParameter, *xy(), collection=mpc)       # la colección, antes que el nombre
            cp.set_editor_property('parameter_name', 'Nublado')
            return cp
    return H


def material_cielo(estrellas):
    amb = _mod('ambiente')
    X = unreal
    g = amb.Grafo(DM + '/M_Cielo', 'M_Cielo', 'cielo v2' + ('' if estrellas else ' sin estrellas'))
    if g.hecho:
        return g.m
    g.m.set_editor_property('shading_model', X.MaterialShadingModel.MSM_UNLIT)
    g.m.set_editor_property('two_sided', True)
    try:
        g.m.set_editor_property('is_sky', True)       # la recoge la luz ambiente (captura en tiempo real)
    except Exception as e:
        log('AVISO: M_Cielo sin «is_sky» (la luz ambiente no verá la bóveda):', repr(e))
    h = _ayudas(g)
    M, A, S, D, AP = h.M, h.A, h.S, h.D, h.AP
    # hacia dónde mira cada píxel: lo contrario del vector hacia la cámara (no depende de la malla)
    d = h.op(M, h.E(X.MaterialExpressionCameraVectorWS), -1.0)
    dz = h.canal(d, 'b')
    dxy = h.f1(X.MaterialExpressionComponentMask, d, r=True, g=True, b=False, a=False)
    arriba = h.sat(dz)
    t = h.pot(h.inv(arriba), 3.0)                          # 0 en el cenit, 1 en el horizonte
    nub = h.nublado()
    base = h.lerp(h.vec('Cenit', CIELO['Cenit']), h.vec('Horizonte', CIELO['Horizonte']), t)
    # nubes: el cielo proyectado en un plano (se estiran hacia el horizonte), ruido de tres niveles que se mueve despacio
    lejos = h.E(X.MaterialExpressionMax, const_b=0.04)
    g.une(dz, lejos, 'A')
    uv = h.op(M, h.op(D, dxy, h.op(A, lejos, 0.22)), h.esc('EscalaNubes', ESCALARES['EscalaNubes']))
    uv = h.op(M, uv, h.op(AP, h.esc('EstiraNubes', ESCALARES['EstiraNubes']), h.E(X.MaterialExpressionConstant, r=1.0)))   # bandas a lo largo del viento
    p = h.op(AP, uv, h.op(M, h.E(X.MaterialExpressionTime), h.esc('VelNubes', ESCALARES['VelNubes'])))
    n1 = g.ruido(*(-2400, 900), 1.0, 3, 0.0, 1.0, pos=p, rapido=True)
    umbral = h.lerp(h.esc('Claros', ESCALARES['Claros']), -0.2, nub)
    nube = h.sat(h.op(M, h.op(S, n1, umbral), h.lerp(h.esc('NubeDura', ESCALARES['NubeDura']), 1.6, nub)))
    # luna: disco de 1,4 grados de radio, halo corto y halo ancho
    ldir = h.f1(X.MaterialExpressionNormalize, h.vec('LunaDir', (0.5, 0.6, 0.62)))
    md = h.punto(d, ldir)
    mds = h.sat(md)
    disco = h.sat(h.op(M, h.op(S, md, 0.99966), 9000.0))
    halo1, halo2 = h.pot(mds, 500.0), h.pot(mds, 30.0)
    despejado = h.inv(nub)
    luna_vis = h.op(M, h.inv(h.op(M, nube, 0.93)), h.inv(h.op(M, nub, 0.95)))
    lcol = h.vec('LunaColor', CIELO['LunaColor'])
    cielo = h.op(A, base, h.op(M, lcol, h.op(M, h.op(M, disco, h.esc('DiscoFuerza', ESCALARES['DiscoFuerza'])), luna_vis)))
    if estrellas is not None:
        suv = h.op(M, h.op(D, dxy, h.op(A, arriba, 1.0)), h.esc('EstrellasRep', ESCALARES['EstrellasRep']))
        ts = h.E(X.MaterialExpressionTextureSampleParameter2D, parameter_name='Estrellas', texture=estrellas,
                 sampler_type=X.MaterialSamplerType.SAMPLERTYPE_MASKS)
        g.une(suv, ts, ('UVs', 'Coordinates'))
        # la textura guarda la raíz del brillo (tools/texturas/estrellas.py): al cuadrado
        s2 = h.E(M); g.une(ts, s2, 'A', 'R'); g.une(ts, s2, 'B', 'R')
        st = h.op(M, s2, h.esc('EstrellasFuerza', ESCALARES['EstrellasFuerza']))
        bajo = h.sat(h.op(M, dz, 3.0))                                                            # el aire del horizonte se las come
        st = h.op(M, h.op(M, st, h.inv(nube)), h.op(M, despejado, h.op(M, bajo, bajo)))           # ni tras las nubes ni pegadas al horizonte
        cielo = h.op(A, cielo, h.op(M, h.vec('EstrellaColor', CIELO['EstrellaColor']), st))
    # color de las nubes: claras por el borde y cerca de la luna; cubierto, grises bajas con el resplandor de la base
    cn = h.lerp(h.vec('NubeLuz', CIELO['NubeLuz']), h.vec('NubeSombra', CIELO['NubeSombra']), h.sat(h.op(S, h.op(M, nube, 1.4), 0.2)))
    cn = h.op(A, cn, h.op(M, lcol, h.op(M, halo2, 0.05)))
    cub = h.op(A, h.lerp(h.vec('Cubierto1', CIELO['Cubierto1']), h.vec('Cubierto2', CIELO['Cubierto2']), n1),
               h.op(M, h.vec('Resplandor', CIELO['Resplandor']), t))
    cnube = h.lerp(cn, cub, nub)
    out = h.lerp(cielo, cnube, nube)
    halo = h.op(M, h.op(A, h.op(M, halo1, 0.25), h.op(M, halo2, 0.03)), h.inv(h.op(M, nub, 0.8)))
    out = h.op(M, h.op(A, out, h.op(M, lcol, halo)), h.esc('Brillo', ESCALARES['Brillo']))
    g.sale(out, X.MaterialProperty.MP_EMISSIVE_COLOR)
    return g.fin()


def material_halo():
    amb = _mod('ambiente')
    X = unreal
    g = amb.Grafo(DM + '/M_Halo', 'M_Halo', 'halo v2')
    if g.hecho:
        return g.m
    g.m.set_editor_property('blend_mode', X.BlendMode.BLEND_ADDITIVE)
    g.m.set_editor_property('shading_model', X.MaterialShadingModel.MSM_UNLIT)
    h = _ayudas(g)
    M, A = h.M, h.A
    # de frente al centro de la esfera, 1; hacia el borde, 0: un resplandor redondo desde cualquier sitio
    nv = h.sat(h.punto(h.E(X.MaterialExpressionVertexNormalWS), h.E(X.MaterialExpressionCameraVectorWS)))
    # en seco, un destello corto pegado a la lámpara (Caida alta: a un tercio del radio ya no queda nada)
    cae = h.E(X.MaterialExpressionPower)
    g.une(nv, cae, 'Base'); g.une(h.esc('Caida', 12.0), cae, ('Exp', 'Exponent'))
    # con lluvia o niebla (Nublado), además, un velo ancho y flojo: la luz en el aire húmedo
    velo = h.op(M, h.op(M, h.pot(nv, 3.0), h.esc('Niebla', 0.22)), h.nublado())
    fuerza = h.op(A, h.op(M, cae, h.esc('Fuerza', 0.6)), velo)
    try:      # que no corte en seco contra el poste o la pared
        df = h.E(X.MaterialExpressionDepthFade, fade_distance_default=35.0)
        fuerza = h.op(M, fuerza, df)
    except Exception as e:
        log('AVISO: M_Halo sin fundido de profundidad:', repr(e))
    g.sale(h.op(M, h.vec('Color', (1.0, 0.55, 0.2)), fuerza), X.MaterialProperty.MP_EMISSIVE_COLOR)
    return g.fin()


def material_baston():
    """M_Baston: el tubo rojo encendido del bastón de señales (sin iluminar; la luz la pone el guardia)."""
    amb = _mod('ambiente')
    g = amb.Grafo(DM + '/M_Baston', 'M_Baston', 'baston v1')
    if g.hecho:
        return g.m
    g.m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    c = g.E(unreal.MaterialExpressionVectorParameter, -400, 0, parameter_name='Color', default_value=unreal.LinearColor(6.0, 0.7, 0.18, 1))
    g.sale(c, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return g.fin()


def _instancia(nombre, base, escalares=(), vectores=()):
    ruta = DM + '/' + nombre
    mi = eal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset(
        nombre, DM, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, base)
    for k, v in escalares:
        mel.set_material_instance_scalar_parameter_value(mi, k, v)
    for k, v in vectores:
        mel.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1))
    eal.save_loaded_asset(mi, False)
    return mi


def _esfera(nombre, pos, diametro, material, tags=()):
    a = eas().spawn_actor_from_object(unreal.load_asset(ESFERA), pos, unreal.Rotator(0, 0, 0))
    a.set_actor_label(nombre)
    a.set_folder_path(CARPETA)
    a.set_actor_scale3d(V(diametro / 100.0, diametro / 100.0, diametro / 100.0))
    if tags:
        a.tags = [unreal.Name(t) for t in tags]
    c = a.static_mesh_component
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_collision_profile_name('NoCollision')
    a.set_actor_enable_collision(False)
    c.set_editor_property('can_ever_affect_navigation', False)
    c.set_editor_property('cast_shadow', False)
    for prop in ('receives_decals', 'affect_distance_field_lighting', 'affect_dynamic_indirect_lighting', 'visible_in_ray_tracing'):
        try:
            c.set_editor_property(prop, False)
        except Exception as e:
            log('AVISO:', nombre, 'sin', prop, repr(e))
    c.set_material(0, material)
    return a


def luna_dir():
    """Hacia dónde está la luna: lo contrario de hacia donde alumbra la luz «Luna»."""
    for a in eas().get_all_level_actors():
        if isinstance(a, unreal.DirectionalLight):
            f = a.get_actor_forward_vector()
            return (-f.x, -f.y, -f.z)
    log('AVISO: cielo: no hay luz direccional; la luna se queda donde estaba')
    return None


def cupula():
    base = material_cielo(textura_estrellas())
    vec = [(k, v) for k, v in CIELO.items()]
    ld = luna_dir()
    if ld:
        vec.append(('LunaDir', ld))
    mi = _instancia('MI_Cielo', base, ESCALARES.items(), vec)
    a = _esfera('Cupula', V(3600, 2800, 0), RADIO_CUPULA * 2.0, mi, tags=('cielo',))
    log('cúpula del cielo puesta; luna hacia', ld)
    return a


def _farol_control():
    """El farol del control de salida lo crea el director al empezar la partida: aquí se calcula dónde (como en
    ATarsisDirector::SetupBarrier) para ponerle su halo y su relleno."""
    for a in eas().get_all_level_actors():
        if a.get_class().get_name() == 'TarsisDirector':
            try:
                loc = a.get_editor_property('exit_barrier_loc')
                yaw = math.radians(a.get_editor_property('exit_barrier_yaw'))
                largo = a.get_editor_property('exit_barrier_length')
            except Exception as e:
                log('AVISO: cielo: no se leen los datos de la barrera:', repr(e))
                return None
            lx, ly = largo * 0.4, -60.0
            return V(loc.x + lx * math.cos(yaw) - ly * math.sin(yaw), loc.y + lx * math.sin(yaw) + ly * math.cos(yaw), loc.z + 380.0)
    return None


def luminarias():
    """Halos y resplandores de relleno. Devuelve (halos, rellenos)."""
    base = material_halo()
    lista = []      # (prefijo, nombre, posición, color lineal)
    for a in eas().get_all_level_actors():
        if not isinstance(a, unreal.Light) or str(a.get_folder_path()) == CARPETA:
            continue
        c = a.get_component_by_class(unreal.LocalLightComponent)
        if not c or not c.is_visible():
            continue
        n = a.get_actor_label()
        pre = next((p for p in LUMINARIAS if n.startswith(p)), None)
        if pre:
            col = c.get_editor_property('light_color')
            k = unreal.LinearColor(col.r / 255.0, col.g / 255.0, col.b / 255.0, 1.0)
            lista.append((pre, n, a.get_actor_location(), (k.r ** 2.2, k.g ** 2.2, k.b ** 2.2)))
    fc = _farol_control()
    if fc is not None:
        lista.append(('farola', 'farol_control', fc, (1.0, 0.57, 0.22)))
    mis = {}
    nh = nr = 0
    for pre, n, pos, col in lista:
        diam, fuerza, lm = LUMINARIAS[pre]
        clave = (pre, tuple(round(x, 2) for x in col))
        if clave not in mis:
            mis[clave] = _instancia('MI_Halo_%s_%d' % (pre.replace('Luz_', ''), len(mis)), base, (('Fuerza', fuerza),), (('Color', col),))
        _esfera('Halo_' + n, V(pos.x, pos.y, pos.z - 8.0), diam, mis[clave], tags=('halo',))
        nh += 1
        if lm > 0:
            r = eas().spawn_actor_from_class(unreal.PointLight, V(pos.x, pos.y, pos.z - 12.0), unreal.Rotator(0, 0, 0))
            r.set_actor_label('Brillo_' + n)
            r.set_folder_path(CARPETA)
            r.tags = [unreal.Name('decorado')]
            r.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
            pc = r.get_component_by_class(unreal.PointLightComponent)
            pc.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
            pc.set_editor_property('intensity', lm)
            pc.set_editor_property('attenuation_radius', RELLENO_RADIO)
            pc.set_editor_property('source_radius', 12.0)
            pc.set_editor_property('cast_shadows', False)
            pc.set_editor_property('volumetric_scattering_intensity', 0.0)
            pc.set_light_color(unreal.LinearColor(col[0], col[1], col[2], 1))
            nr += 1
    log('luminarias:', nh, 'halos y', nr, 'resplandores de relleno')
    return nh, nr


def todo():
    limpiar()
    for paso in (cupula, luminarias, material_baston):
        try:
            paso()
        except Exception as e:
            log('AVISO: cielo:', paso.__name__, 'no hecho:', repr(e))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


if __name__ == '__main__':
    todo()
