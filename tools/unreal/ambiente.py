"""Ambiente de una zona del nivel Tarsis (tanda 18: el barracón oeste y su patio): luz, sonido, posprocesado,
manchas y las taquillas de verdad.

Noche de sodio y luna: sombras frías, luces cálidas, negros profundos con siluetas legibles. Dentro del barracón un
fluorescente frío que a veces titila (etiqueta «parpadeo», lo mueve ATarsisDirector::ZonesTick); sobre la puerta una
lámpara cálida; el resto, oscuridad. Pocas luces con sombra (focos: una vista de sombra, no seis) y radio corto, móviles: el apagón del generador y el farol
roto las apagan en juego, así que no se hornean (y las medidas de fps dicen que no hace falta).
Sonido: zumbido del fluorescente («electrico»: calla sin luz), la radio de la mesa bajito (fuente 3D que también
orienta) y una gotera («lluvia»: solo suena si llueve).

Uso (en el editor, con el nivel Tarsis abierto, después de atrezo.py): py tools/unreal/ambiente.py
Todo lo que pone va a la carpeta «Ambiente» del nivel y se quita y se vuelve a poner cada vez.
"""
import os
import unreal

V = unreal.Vector
CARPETA = 'Ambiente'
DM = '/Game/Tarsis/Materiales'
DS = '/Game/Tarsis/Sonidos'
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

# el barracón oeste por dentro: x 145-2200, y 2200-3000, suelo a 3 cm, techo a 356
FLUORESCENTE = V(1150, 2570, 349)
PUERTA_NORTE = V(1500, 1972, 250)   # bajo la lámpara de pared, fuera



def uno(a, b):
    """Conecta a la única entrada de b (OneMinus, Saturate, Abs, ComponentMask): según el nodo se llama «Input» o «»."""
    if not mel.connect_material_expressions(a, '', b, 'Input'):
        mel.connect_material_expressions(a, '', b, '')

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def limpiar():
    for a in eas().get_all_level_actors():
        if str(a.get_folder_path()) == CARPETA:
            eas().destroy_actor(a)


def poner(cls, nombre, pos, rot=unreal.Rotator(0, 0, 0), tags=()):
    a = eas().spawn_actor_from_class(cls, pos, rot)
    a.set_actor_label(nombre)
    a.set_folder_path(CARPETA)
    if tags:
        a.tags = [unreal.Name(t) for t in tags]
    return a


def color(r, g, b):
    return unreal.LinearColor(r, g, b, 1.0).to_color(True)


# ---------------------------------------------------------------- luz

def luces():
    # la luz del barracón de la base (interior_0, neutra y quieta) pasa a ser el fluorescente: fría, algo verdosa,
    # alargada como el tubo, con sombras y radio corto. Se mueve al tubo y se etiqueta para que titile
    for a in eas().get_all_level_actors():
        if isinstance(a, unreal.PointLight) and str(a.get_folder_path()) != CARPETA:
            l = a.get_actor_location()
            if 145 < l.x < 2200 and 2200 < l.y < 3000:
                a.set_actor_hidden_in_game(True)
                a.point_light_component.set_editor_property('visible', False)
                log('luz de la base apagada en el barracón:', a.get_actor_label())
    # foco hacia abajo y no luz puntual: la sombra se calcula una vez por fotograma y no seis (cubo); en una GTX 1050 Ti
    # las dos luces puntuales con sombra costaban unos 3,5 fps dentro del barracón (tools/unreal/medir.py)
    f = poner(unreal.SpotLight, 'Luz_Fluorescente', FLUORESCENTE, unreal.Rotator(0, -90, 0), tags=('parpadeo',))
    c = f.spot_light_component
    c.set_editor_property('outer_cone_angle', 80.0)
    c.set_editor_property('inner_cone_angle', 45.0)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
    c.set_editor_property('intensity', 1200.0)
    c.set_editor_property('light_color', color(0.72, 0.9, 1.0))
    c.set_editor_property('attenuation_radius', 1300.0)
    c.set_editor_property('source_length', 90.0)
    c.set_editor_property('source_radius', 2.0)
    # sin sombra (0019): con cerchas, literas y baúles debajo, su sombra costaba 1,3-1,6 fps en el barracón
    # (A/B en una sesión, tools/unreal/medir.py) y lo dejaba por debajo de 30. La sombra dura la pone el flexo.
    c.set_editor_property('cast_shadows', False)
    c.set_editor_property('volumetric_scattering_intensity', 0.4)
    # sobre la puerta norte, fuera: lámpara enjaulada de luz cálida (sodio), que recorta al que entra
    p = poner(unreal.SpotLight, 'Luz_PuertaNorte', PUERTA_NORTE, unreal.Rotator(0, -70, -90))   # hacia abajo y algo hacia fuera (-Y)
    c = p.spot_light_component
    c.set_editor_property('outer_cone_angle', 75.0)
    c.set_editor_property('inner_cone_angle', 35.0)
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
    c.set_editor_property('intensity', 420.0)
    c.set_editor_property('light_color', color(1.0, 0.6, 0.26))
    c.set_editor_property('attenuation_radius', 800.0)
    c.set_editor_property('source_radius', 6.0)
    c.set_editor_property('cast_shadows', True)
    c.set_editor_property('volumetric_scattering_intensity', 1.2)
    # dentro, contra el azul del fluorescente, dos fuentes cálidas pequeñas: el flexo de la mesa del cuartelero (foco
    # corto hacia la mesa, con sombra: recorta la radio y el termo) y el resplandor de la estufa (sin sombra)
    fx = poner(unreal.SpotLight, 'Luz_Flexo', V(420, 2495, 150), unreal.Rotator(0, -80, 200), tags=('electrico_luz',))   # la mesa, al fondo oeste
    c = fx.spot_light_component
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
    c.set_editor_property('intensity', 160.0)
    c.set_editor_property('light_color', color(1.0, 0.72, 0.42))
    c.set_editor_property('attenuation_radius', 380.0)
    c.set_editor_property('outer_cone_angle', 55.0)
    c.set_editor_property('inner_cone_angle', 25.0)
    c.set_editor_property('source_radius', 3.0)
    c.set_editor_property('cast_shadows', True)
    es = poner(unreal.PointLight, 'Luz_Estufa', V(560, 2295, 45))
    c = es.point_light_component
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
    c.set_editor_property('intensity', 70.0)
    c.set_editor_property('light_color', color(1.0, 0.42, 0.12))
    c.set_editor_property('attenuation_radius', 300.0)
    c.set_editor_property('source_radius', 15.0)
    c.set_editor_property('cast_shadows', False)


# ---------------------------------------------------------------- sonido

def sonido(nombre, pos, onda, volumen, alcance, tags=()):
    s = unreal.load_asset('%s/%s' % (DS, onda))
    if not s:
        log('AVISO: falta el sonido', onda, '(tools/unreal/sonidos.py)')
        return None
    s.set_editor_property('looping', True)
    eal.save_loaded_asset(s, False)
    a = poner(unreal.AmbientSound, nombre, pos, tags=tags)
    c = a.get_component_by_class(unreal.AudioComponent)
    c.set_editor_property('sound', s)
    c.set_editor_property('volume_multiplier', volumen)
    c.set_editor_property('override_attenuation', True)
    at = c.get_editor_property('attenuation_overrides')
    at.set_editor_property('falloff_distance', alcance)
    at.set_editor_property('attenuation_shape_extents', V(80, 0, 0))
    c.set_editor_property('attenuation_overrides', at)
    return a


def sonidos():
    sonido('Son_Fluorescente', FLUORESCENTE, 'fluorescente', 0.35, 700.0, ('electrico',))
    sonido('Son_Radio', V(925, 2455, 100), 'radio_barracon', 0.45, 1900.0)
    sonido('Son_Gotera', V(1960, 2930, 30), 'gotera', 0.6, 900.0, ('lluvia',))


# ---------------------------------------------------------------- posprocesado de la zona

def posproceso():
    v = poner(unreal.PostProcessVolume, 'PP_BarraconOeste', V(1150, 2150, 150))
    v.set_actor_scale3d(V(12.5, 10.0, 3.0))   # la brocha de 200 uu: 2500 x 2000 x 600 (barracón y su patio)
    v.set_editor_property('unbound', False)
    v.set_editor_property('priority', 1.0)
    v.set_editor_property('blend_radius', 500.0)
    s = v.settings
    # etalonaje: sombras frías azul verdosas, luces cálidas; algo más de contraste y negros profundos
    for k, val in (('color_gain_shadows', unreal.Vector4(0.86, 0.98, 1.06, 1.0)), ('color_gain_highlights', unreal.Vector4(1.06, 1.0, 0.9, 1.0)),
                   ('color_contrast', unreal.Vector4(1.08, 1.08, 1.08, 1.0)), ('color_offset_shadows', unreal.Vector4(-0.004, -0.002, 0.0, 0.0))):
        s.set_editor_property('override_' + k, True)
        s.set_editor_property(k, val)
    for k, val in (('film_grain_intensity', 0.18), ('vignette_intensity', 0.55), ('bloom_intensity', 0.35)):
        s.set_editor_property('override_' + k, True)
        s.set_editor_property(k, val)
    v.settings = s


# ---------------------------------------------------------------- las taquillas (escondites): chapa de verdad

TAQUILLA = '/Game/Tarsis/Atrezo/Taquilla/SM_Taquilla'


def _caja(dm, cx, cy, cz, dx, dy, dz):
    t = unreal.Transform(V(cx, cy, cz), unreal.Rotator(0, 0, 0), V(1, 1, 1))
    unreal.GeometryScript_Primitives.append_box(dm, unreal.GeometryScriptPrimitiveOptions(), t, dx, dy, dz, 0, 0, 0,
                                                unreal.GeometryScriptPrimitiveOriginMode.CENTER)


def taquilla():
    """Taquilla metálica de 60 x 50 x 190 cm (la puerta mira a +Y, el origen en el suelo, como espera
    ATarsisDirector::SetupHiding): cantos biselados, la junta de la puerta, rendijas de ventilación abiertas arriba y
    abajo y el tirador. Material: chapa pintada y gastada (MI_taquilla, del maestro M_LH, con su suciedad)."""
    GS = unreal
    dm = unreal.DynamicMesh()
    _caja(dm, 0, 0, 95, 60, 50, 190)
    bev = unreal.GeometryScriptMeshBevelOptions()
    bev.set_editor_property('bevel_distance', 0.9)
    GS.GeometryScript_MeshModeling.apply_mesh_polygroup_bevel(dm, bev)
    # lo que se le quita: la junta alrededor de la puerta (4 mm) y las rendijas (abiertas 2 cm hacia dentro)
    corte = unreal.DynamicMesh()
    y = 25.0
    for cx, cz, dx, dz in ((0, 4.0, 56, 0.5), (0, 186.0, 56, 0.5), (-28.0, 95, 0.5, 182), (28.0, 95, 0.5, 182)):
        _caja(corte, cx, y, cz, dx, 1.2, dz)
    for k in range(6):
        _caja(corte, 0, y, 150 + k * 5.0, 34, 4.0, 1.4)
    for k in range(3):
        _caja(corte, 0, y, 18 + k * 5.0, 34, 4.0, 1.4)
    op = unreal.GeometryScriptMeshBooleanOptions()
    ident = unreal.Transform()
    GS.GeometryScript_MeshBooleans.apply_mesh_boolean(dm, ident, corte, ident, unreal.GeometryScriptBooleanOperation.SUBTRACT, op)
    # tirador vertical y una placa para el número
    _caja(dm, 22, 26.2, 100, 2.0, 2.4, 12.0)
    _caja(dm, 0, 25.3, 135, 10.0, 0.6, 5.0)
    GS.GeometryScript_Normals.compute_split_normals(dm, unreal.GeometryScriptSplitNormalsOptions(), unreal.GeometryScriptCalculateNormalsOptions())
    if eal.does_asset_exist(TAQUILLA):
        eal.delete_asset(TAQUILLA)
    o = unreal.GeometryScriptCreateNewStaticMeshAssetOptions()
    r = GS.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm, TAQUILLA, o)
    sm = r[0] if isinstance(r, tuple) else r
    if not sm:
        log('AVISO: no se ha creado la taquilla')
        return None
    # material: la chapa verde oxidada del maestro, más gris y fina, bastante sucia
    mi_ruta = DM + '/MI_taquilla'
    if not eal.does_asset_exist(mi_ruta):
        eal.duplicate_asset(DM + '/MI_oliva', mi_ruta)
    mi = unreal.load_asset(mi_ruta)
    mel.set_material_instance_vector_parameter_value(mi, 'Tinte', unreal.LinearColor(0.55, 0.62, 0.52, 1))
    mel.set_material_instance_scalar_parameter_value(mi, 'Tamano', 90.0)
    mel.set_material_instance_scalar_parameter_value(mi, 'Suciedad', 0.85)
    mel.set_material_instance_scalar_parameter_value(mi, 'Metal', 0.35)
    eal.save_loaded_asset(mi, False)
    sm.set_material(0, mi)
    sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    sms.remove_collisions(sm)
    sms.add_simple_collisions(sm, unreal.ScriptCollisionShapeType.BOX)
    eal.save_loaded_asset(sm, False)
    log('taquilla creada:', TAQUILLA)
    return sm


# ---------------------------------------------------------------- manchas: humedad, salitre y mugre (calcomanías)

def material_mancha():
    """M_Mancha: calcomanía de mancha irregular (máscara redonda difusa x ruido del mundo). Parámetros: Color y Fuerza.
    Mezcla «modulada»: con Substrate (r.Substrate=True) es la transmitancia de color sola, y en la calcomanía se porta
    como una mezcla normal: lo de debajo pasa a Color en la proporción de la opacidad. Fuera de la máscara no toca nada
    (no se ve la caja) y dentro oscurece de verdad."""
    # v4 (tanda 23; la v3 fue una prueba). La v2 era alfa compuesto con el color premultiplicado: con Substrate ese color se SUMA a lo de debajo
    # (no oscurece) y las manchas oscuras casi no se veían. Probado también Lerp(1, tinte, máscara) como multiplicador:
    # no multiplica, y en paredes oscuras aclaraba. Las instancias siguen colgando de él con su Color
    g = Grafo(DM + '/M_Mancha', 'M_Mancha', 'mancha v4 modulado')
    if g.hecho:
        return g.m
    g.m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MODULATE)       # antes que el dominio
    g.m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    col = g.E(unreal.MaterialExpressionVectorParameter, -600, -200, parameter_name='Color', default_value=unreal.LinearColor(0.045, 0.038, 0.028, 1))
    uv = g.E(unreal.MaterialExpressionTextureCoordinate, -900, 200)
    c05 = g.E(unreal.MaterialExpressionConstant2Vector, -900, 320, r=0.5, g=0.5)
    sm = g.E(unreal.MaterialExpressionSphereMask, -700, 200, attenuation_radius=0.5, hardness_percent=15.0)
    g.une(uv, sm, 'A'); g.une(c05, sm, 'B')
    ruido = g.ruido(-700, 400, 0.03, 3, -0.4, 1.0)
    mu = g.op(unreal.MaterialExpressionMultiply, sm, ruido, -500, 300)
    opa = g.sat(g.op(unreal.MaterialExpressionMultiply, mu, g.esc('Fuerza', 0.85, -500, 450), -350, 350), -220, 350)
    g.sale(opa, unreal.MaterialProperty.MP_OPACITY)
    g.sale(col, unreal.MaterialProperty.MP_BASE_COLOR)
    return g.fin()


# ---------------------------------------------------------------- tanda 23: charcos y chorretones (calcomanías)

class Grafo:
    """Los nodos de un material, con las conexiones contadas: los nombres de las entradas cambian entre versiones del
    motor (en 5.8 la del ruido es «World Position»), y una conexión que no entra deja el material a medias sin decir
    nada. Aquí cada una que falla se apunta y fin() avisa con el nombre del material y de los nodos."""
    def __init__(self, ruta, nombre, version):
        self.nombre, self.version, self.fallos, self.hecho = nombre, version, [], False
        if eal.does_asset_exist(ruta):
            self.m = unreal.load_asset(ruta)
            if any(e.get_editor_property('desc') == version for e in mel.get_material_expressions(self.m)):
                self.hecho = True        # ya está en esta versión: no se toca
                return
            mel.delete_all_material_expressions(self.m)
            for e in list(mel.get_material_expressions(self.m)):
                mel.delete_material_expression(self.m, e)
        else:
            self.m = tools.create_asset(nombre, ruta.rsplit('/', 1)[0], unreal.Material, unreal.MaterialFactoryNew())

    def E(self, cls, x, y, **props):
        e = mel.create_material_expression(self.m, cls, x, y)
        for k, v in props.items():
            e.set_editor_property(k, v)
        return e

    def esc(self, nombre, valor, x, y):
        return self.E(unreal.MaterialExpressionScalarParameter, x, y, parameter_name=nombre, default_value=valor)

    def une(self, a, b, ent, sal=''):
        for n in (ent if isinstance(ent, (tuple, list)) else (ent,)):
            if mel.connect_material_expressions(a, sal, b, n):
                return True
        self.fallos.append('%s > %s.%s' % (a.get_name(), b.get_name(), ent if isinstance(ent, str) else ent[0]))
        return False

    def uno(self, a, b):                 # la entrada única se llama «Input» o «» según el nodo
        return self.une(a, b, ('Input', ''))

    def op(self, cls, a, b, x, y, **props):
        """Nodo de dos entradas (A, B). b puede ser otro nodo o un número (va a const_b)."""
        if isinstance(b, (int, float)):
            n = self.E(cls, x, y, const_b=float(b), **props)
        else:
            n = self.E(cls, x, y, **props)
            self.une(b, n, 'B')
        self.une(a, n, 'A')
        return n

    def sat(self, a, x, y):
        n = self.E(unreal.MaterialExpressionSaturate, x, y)
        self.uno(a, n)
        return n

    def lerp(self, a, b, alfa, x, y):
        """a y b: nodo o número; alfa: nodo."""
        n = self.E(unreal.MaterialExpressionLinearInterpolate, x, y)
        for v, ent, const in ((a, 'A', 'const_a'), (b, 'B', 'const_b')):
            if isinstance(v, (int, float)):
                n.set_editor_property(const, float(v))
            else:
                self.une(v, n, ent)
        self.une(alfa, n, 'Alpha')
        return n

    def canal(self, src, k, x, y):
        n = self.E(unreal.MaterialExpressionComponentMask, x, y, **{q: q == k for q in 'rgba'})
        self.uno(src, n)
        return n

    def ruido(self, x, y, escala, niveles, lo, hi, pos=None, rapido=False):
        """Ruido de gradiente por textura. rapido: el de textura 3D (una lectura por nivel en vez de ocho; se repite cada
        16 unidades de ruido, así que solo para dibujos lentos, donde la repetición queda a decenas de metros)."""
        fn = unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX
        if rapido:
            fn = getattr(unreal.NoiseFunction, 'NOISEFUNCTION_GRADIENT_TEX3D', fn)
        n = self.E(unreal.MaterialExpressionNoise, x, y, scale=escala, levels=niveles, noise_function=fn, quality=1,
                   output_min=lo, output_max=hi)
        if pos is not None:
            self.une(pos, n, ('World Position', 'Position'))
        return n

    def sale(self, a, prop, sal=''):
        if not mel.connect_material_property(a, sal, prop):
            self.fallos.append('%s > %s' % (a.get_name(), prop))

    def fin(self):
        self.E(unreal.MaterialExpressionConstant, -1800, -600, r=0.0, desc=self.version)      # la marca de versión
        mel.recompile_material(self.m)
        eal.save_loaded_asset(self.m, False)
        if self.fallos:
            log('AVISO: %s: %d conexiones sin hacer: %s' % (self.nombre, len(self.fallos), '; '.join(self.fallos)))
        else:
            log(self.nombre, 'hecho (%s)' % self.version)
        return self.m


CHARCO_NORMAL = True     # tanda 23: con la mezcla puesta antes que el dominio, BLEND_TRANSLUCENT sí compila (el fallo era el orden)


def material_charco():
    """M_Charco: agua quieta sobre el suelo, con su cerco de suelo mojado alrededor. Del centro hacia fuera: el agua
    (oscura, casi sin rugosidad y con el relieve plano: de noche lo que se ve es el reflejo de la farola y del cielo), que
    se va haciendo fina hacia la orilla y deja ver el suelo, y un cerco húmedo (suelo algo más oscuro y satinado, con su
    grano) que se pierde poco a poco. El contorno sale de una máscara redonda por el ruido del mundo: ninguno es igual.
    Parámetros: Color, Fuerza, Rugosidad (la del agua), Fondo (cuánto tapa el agua en el centro), Cerco (cuánto oscurece
    el suelo mojado) y RugosidadCerco.
    Mezcla «translúcida»: es la única de las calcomanías que deja escribir el relieve y que, con Substrate, toca solo lo
    que hay dentro de la máscara (con alfa compuesto escribía la rugosidad en toda la caja); el color va sin multiplicar,
    lo mezcla el motor con la opacidad. Sin CHARCO_NORMAL (motor que no la compile), alfa compuesto como en la tanda 22:
    solo oscurece."""
    # v6 (tanda 25): la v5 seguía leyéndose como una mancha de tinta: la forma era la máscara redonda POR un ruido
    # fino (bordes deshilachados) y el agua tapaba casi todo el suelo (negro salvo en el ángulo del reflejo). Ahora la
    # forma es la distancia al centro MÁS un ruido lento (lóbulos de un metro, como el agua que busca lo hondo de la
    # losa), con un segundo ruido más fino y flojo que solo muerde la orilla; el cerco es más ancho y el agua deja ver
    # más fondo (Fondo 0,75 en las instancias). v5: orilla blanda y cerco. v4: orilla cortada a cuchillo y sin cerco
    g = Grafo(DM + '/M_Charco', 'M_Charco', 'charco v6' + (' plano' if CHARCO_NORMAL else ''))
    if g.hecho:
        return g.m
    M, A, S = unreal.MaterialExpressionMultiply, unreal.MaterialExpressionAdd, unreal.MaterialExpressionSubtract
    # mezcla antes que el dominio (si no, la primera compilación da error)
    g.m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT if CHARCO_NORMAL else unreal.BlendMode.BLEND_ALPHA_COMPOSITE)
    g.m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    col = g.E(unreal.MaterialExpressionVectorParameter, -700, -300, parameter_name='Color', default_value=unreal.LinearColor(0.012, 0.012, 0.011, 1))
    uv = g.E(unreal.MaterialExpressionTextureCoordinate, -1900, 200)
    c05 = g.E(unreal.MaterialExpressionConstant2Vector, -1900, 320, r=0.5, g=0.5)
    # 1 en el centro de la calcomanía y 0 en el borde de la caja (dureza 0: baja en línea recta)
    sm = g.E(unreal.MaterialExpressionSphereMask, -1700, 200, attenuation_radius=0.5, hardness_percent=0.0)
    g.une(uv, sm, 'A'); g.une(c05, sm, 'B')
    lento = g.ruido(-1700, 400, 0.0065, 2, -0.5, 0.5, rapido=True)        # lóbulos de un metro y medio
    fino = g.ruido(-1700, 560, 0.035, 1, -0.5, 0.5, rapido=True)          # mordiscos de un palmo en la orilla
    onda = g.op(A, g.op(M, lento, g.esc('Lobulos', 0.85, -1500, 480), -1350, 400), g.op(M, fino, 0.14, -1500, 600), -1200, 460)
    # pegado al borde de la caja el ruido no puede sacar agua (se vería el corte recto de la caja)
    borde = g.sat(g.op(M, sm, 5.0, -1500, 100), -1350, 100)
    forma = g.op(M, g.op(A, sm, onda, -1050, 300), borde, -900, 300)
    # el agua: entra en forma > 0,44 y está entera en 0,58
    agua0 = g.sat(g.op(M, g.op(S, forma, 0.44, -750, 250), 7.0, -620, 250), -500, 250)
    agua = g.op(M, g.op(M, agua0, agua0, -380, 250), g.esc('Fondo', 0.75, -500, 120), -260, 250)      # al cuadrado: orilla fina
    # el cerco de suelo mojado: empieza bastante antes (forma > 0,20) y sube despacio
    cerco0 = g.sat(g.op(M, g.op(S, forma, 0.20, -750, 520), 3.4, -620, 520), -500, 520)
    cerco = g.op(M, cerco0, g.esc('Cerco', 0.5, -500, 660), -380, 560)
    opa0 = g.E(unreal.MaterialExpressionMax, -280, 380)
    g.une(agua, opa0, 'A'); g.une(cerco, opa0, 'B')
    opa = g.sat(g.op(M, opa0, g.esc('Fuerza', 1.0, -280, 560), -140, 420), -20, 420)
    g.sale(opa, unreal.MaterialProperty.MP_OPACITY)
    if CHARCO_NORMAL:
        g.sale(col, unreal.MaterialProperty.MP_BASE_COLOR)
        # rugosidad: la del cerco (satinado) fuera del agua y la del agua dentro
        rug = g.lerp(g.esc('RugosidadCerco', 0.32, -560, 800), g.esc('Rugosidad', 0.05, -560, 900), agua0, -380, 840)
        g.sale(rug, unreal.MaterialProperty.MP_ROUGHNESS)
        # relieve plano: como la opacidad del cerco es baja, ahí queda casi entero el grano del suelo
        g.sale(g.E(unreal.MaterialExpressionConstant3Vector, -380, 1000, constant=unreal.LinearColor(0, 0, 1, 0)), unreal.MaterialProperty.MP_NORMAL)
    else:
        # con alfa compuesto la calcomanía escribe la rugosidad en TODA su caja: aquí el agua solo oscurece
        g.sale(g.op(M, col, opa, -100, -200, desc='premultiplicado'), unreal.MaterialProperty.MP_BASE_COLOR)
    return g.fin()


def material_chorreton():
    """M_Chorreton: los regueros oscuros que deja el agua al escurrir por un muro. No usa las UV de la calcomanía sino la
    posición en el mundo (vale para un muro que mire a cualquier lado): hilos verticales finos (ruido muy estirado en
    vertical), que salen a grupos y cada uno baja una distancia distinta desde lo alto del muro (Techo, en cm del mundo),
    y una franja de humedad irregular pegada a la coronación, de donde nacen.
    Parámetros: Color, Fuerza, Techo, Largo, Contraste, Grupos (umbral: más bajo, más tramos de muro con regueros) y
    Franja (fuerza de la humedad de arriba). La caja de la calcomanía solo limita dónde puede haberlos."""
    # v4 (tanda 24): en las capturas de la 23 casi no se leían. Hilos más finos (11 cm en vez de 17) y con más contraste,
    # más tramos con regueros, color más oscuro y la franja de arriba. v3: modulado (ver M_Mancha)
    # v5 (tanda 25): a diez metros seguían sin leerse: los hilos de 11 cm se pierden al 50 % de resolución. Ahora van
    # dos anchos a la vez (regueros de un palmo largo, 35 cm, que son los que se ven de lejos, y los hilos finos dentro)
    # y la franja de arriba es más alta
    g = Grafo(DM + '/M_Chorreton', 'M_Chorreton', 'chorreton v5 ancho')
    if g.hecho:
        return g.m
    # la mezcla, antes que el dominio
    g.m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MODULATE)
    g.m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    M, A, S, D, AP = (unreal.MaterialExpressionMultiply, unreal.MaterialExpressionAdd, unreal.MaterialExpressionSubtract,
                      unreal.MaterialExpressionDivide, unreal.MaterialExpressionAppendVector)
    col = g.E(unreal.MaterialExpressionVectorParameter, -500, -400, parameter_name='Color', default_value=unreal.LinearColor(0.018, 0.016, 0.013, 1))
    wp = g.E(unreal.MaterialExpressionWorldPosition, -2300, 0)
    mx, my, mz = g.canal(wp, 'r', -2100, -80), g.canal(wp, 'g', -2100, 20), g.canal(wp, 'b', -2100, 120)
    h = g.op(A, mx, my, -1950, -40)                       # a lo largo del muro, mire a donde mire
    cero = g.E(unreal.MaterialExpressionConstant, -1950, 260, r=0.0)
    hc = g.op(AP, h, cero, -1800, 0)
    # los hilos: 11 cm de ancho medio, y cada uno dura metros en vertical
    p1 = g.op(AP, hc, g.op(M, mz, 0.03, -1950, 140), -1650, 60)
    n1 = g.ruido(-1500, 60, 0.09, 2, -0.45, 1.0, pos=p1)
    hilo_fino = g.sat(g.op(M, n1, g.esc('Contraste', 2.6, -1500, 240), -1300, 100), -1150, 100)
    # los regueros anchos: el mismo dibujo tres veces más ancho; el fino queda dentro y en los bordes
    p1b = g.op(AP, g.op(AP, h, g.E(unreal.MaterialExpressionConstant, -1950, -260, r=170.0), -1800, -260), g.op(M, mz, 0.012, -1950, -160), -1650, -220)
    n1b = g.ruido(-1500, -220, 0.028, 2, -0.35, 1.0, pos=p1b)
    hilo_ancho = g.sat(g.op(M, n1b, g.esc('ContrasteAncho', 2.2, -1500, -60), -1300, -180), -1150, -180)
    hilo_mx = g.E(unreal.MaterialExpressionMax, -1000, -40)
    g.une(g.op(M, hilo_ancho, g.esc('Ancho', 0.85, -1150, -320), -1000, -220), hilo_mx, 'A'); g.une(hilo_fino, hilo_mx, 'B')
    hilo = hilo_mx
    # los grupos: tramos de muro con regueros y tramos limpios
    n2 = g.ruido(-1500, 380, 0.0045, 1, 0.0, 1.0, pos=g.op(AP, hc, cero, -1650, 380), rapido=True)
    grupo = g.sat(g.op(M, g.op(S, n2, g.esc('Grupos', 0.30, -1500, 500), -1300, 380), 3.5, -1150, 380), -1000, 380)
    # lo que baja cada hilo: Largo x (0,12 + 1,9 x ruido²)
    p3 = g.op(AP, g.op(AP, h, g.E(unreal.MaterialExpressionConstant, -1950, 600, r=40.0), -1800, 600), cero, -1650, 600)
    n3 = g.ruido(-1500, 600, 0.021, 1, 0.0, 1.0, pos=p3, rapido=True)
    largo = g.op(M, g.op(A, g.op(M, g.op(M, n3, n3, -1300, 600), 1.9, -1150, 600), 0.12, -1000, 600), g.esc('Largo', 280.0, -1150, 760), -850, 640)
    dz = g.op(S, g.esc('Techo', 462.0, -1300, 900), mz, -1100, 900)
    baja = g.E(unreal.MaterialExpressionOneMinus, -700, 800)
    g.uno(g.op(D, dz, largo, -850, 800), baja)
    f = g.sat(baja, -560, 800)
    arriba = g.sat(g.op(M, dz, 0.25, -850, 980), -700, 980)          # nada por encima de lo alto del muro
    hilos = g.op(M, g.op(M, hilo, grupo, -850, 200), f, -420, 400)
    # la franja de arriba: 1 - dz / (35 + 110 x ruido) cm, solo en los tramos con regueros
    alto_f = g.op(A, g.op(M, n3, 110.0, -1300, 1100), 35.0, -1150, 1100)
    fr = g.E(unreal.MaterialExpressionOneMinus, -850, 1100)
    g.uno(g.op(D, dz, alto_f, -1000, 1100), fr)
    franja = g.op(M, g.op(M, g.sat(fr, -700, 1100), grupo, -560, 1100), g.esc('Franja', 0.6, -700, 1240), -420, 1150)
    mx_ = g.E(unreal.MaterialExpressionMax, -300, 700)
    g.une(hilos, mx_, 'A'); g.une(franja, mx_, 'B')
    o = g.op(M, mx_, arriba, -200, 600)
    opa = g.sat(g.op(M, o, g.esc('Fuerza', 1.0, -200, 760), -80, 600), 40, 600)
    g.sale(opa, unreal.MaterialProperty.MP_OPACITY)
    g.sale(col, unreal.MaterialProperty.MP_BASE_COLOR)
    return g.fin()


def mancha(nombre, pos, ancho, alto, hacia, fuerza=0.85, color_=None, rug=0.35, giro=0.0):
    """color_: color de la mancha (M_Mancha modulado lo mezcla con la opacidad). rug ya no se usa.
    hacia: 'abajo' (suelo), 'arriba' (techo) o el yaw al que mira la pared que recibe la mancha (la calcomanía
    proyecta a lo largo de su X)."""
    base = material_mancha()
    # unreal.Rotator(roll, pitch, yaw)
    if hacia == 'abajo':
        rot = unreal.Rotator(0, -90, giro)
    elif hacia == 'arriba':
        rot = unreal.Rotator(0, 90, giro)
    else:
        rot = unreal.Rotator(giro, 0, hacia)
    a = poner(unreal.DecalActor, nombre, pos, rot)
    d = a.decal
    # instancia por mancha (fuerza, color, brillo distintos)
    ruta = DM + '/Manchas/MI_' + nombre
    inst = unreal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset('MI_' + nombre, DM + '/Manchas', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(inst, base)
    mel.set_material_instance_scalar_parameter_value(inst, 'Fuerza', fuerza)
    if color_:
        mel.set_material_instance_vector_parameter_value(inst, 'Color', unreal.LinearColor(*color_, 1))
    eal.save_loaded_asset(inst, False)
    d.set_decal_material(inst)
    d.set_editor_property('decal_size', V(20, ancho / 2.0, alto / 2.0))
    return a


def manchas():
    # muro sur (mira a -Y desde dentro: la calcomanía apunta a +Y): humedad que sube del suelo junto a la gotera y bajo las literas
    mancha('Mancha_HumedadSur', V(1900, 2990, 60), 320, 140, 90, 0.9, (0.05, 0.045, 0.035), 0.3)
    mancha('Mancha_LiterasSur', V(650, 2990, 45), 500, 100, 90, 0.7, (0.06, 0.05, 0.04), 0.55)
    # muro oeste (apunta a -X) tras la estantería, y el muro norte junto a la puerta (apunta a -Y)
    mancha('Mancha_Oeste', V(155, 2700, 90), 380, 180, 180, 0.75, (0.05, 0.045, 0.035), 0.45)
    mancha('Mancha_NortePuerta', V(1700, 2210, 50), 260, 110, -90, 0.7, (0.06, 0.05, 0.04), 0.5)
    # techo: el cerco de la gotera; suelo: el charco bajo ella y el paso sucio de la puerta
    mancha('Mancha_TechoGotera', V(1960, 2930, 350), 220, 180, 'arriba', 0.9, (0.07, 0.06, 0.04), 0.4)
    mancha('Mancha_Charco', V(1960, 2930, 6), 140, 110, 'abajo', 0.8, (0.02, 0.02, 0.018), 0.08)
    mancha('Mancha_PasoPuerta', V(1500, 2300, 6), 180, 220, 'abajo', 0.55, (0.05, 0.042, 0.03), 0.7)
    # fuera: salitre y lluvia bajo la lámpara y junto a los bidones (muro norte por fuera mira a -Y: apunta a +Y)
    mancha('Mancha_FueraPuerta', V(1500, 2010, 40), 420, 120, 90, 0.7, (0.05, 0.045, 0.038), 0.5)
    mancha('Mancha_FueraBidones', V(700, 2010, 70), 360, 200, 90, 0.8, (0.045, 0.04, 0.03), 0.45)


# ---------------------------------------------------------------- tela: colchones y mantas dobladas (Poly Haven no tiene)

def _malla_tela(ruta, dx, dy, dz, bisel, material):
    GS = unreal
    dm = unreal.DynamicMesh()
    _caja(dm, 0, 0, dz / 2.0, dx, dy, dz)
    bev = unreal.GeometryScriptMeshBevelOptions()
    bev.set_editor_property('bevel_distance', bisel)
    GS.GeometryScript_MeshModeling.apply_mesh_polygroup_bevel(dm, bev)
    GS.GeometryScript_Normals.compute_split_normals(dm, unreal.GeometryScriptSplitNormalsOptions(), unreal.GeometryScriptCalculateNormalsOptions())
    if eal.does_asset_exist(ruta):
        eal.delete_asset(ruta)
    r = GS.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm, ruta, unreal.GeometryScriptCreateNewStaticMeshAssetOptions())
    sm = r[0] if isinstance(r, tuple) else r
    mi = unreal.load_asset(DM + '/' + material)
    if sm and mi:
        sm.set_material(0, mi)
        eal.save_loaded_asset(sm, False)
    return sm


def telas():
    """Colchón de tela basta (85 x 186 x 13 cm) y manta de lana doblada (70 x 45 x 9 cm), como piezas de atrezo
    («colchon» y «manta» en atrezo.json). Material: MI_colchon y MI_manta de materiales.py."""
    _malla_tela('/Game/Tarsis/Atrezo/colchon/SM_colchon', 85, 186, 13, 3.5, 'MI_colchon')
    _malla_tela('/Game/Tarsis/Atrezo/manta/SM_manta', 70, 45, 9, 2.5, 'MI_manta')


def _malla_cajas(ruta, cajas, bisel, material):
    """Una malla hecha de cajas (cx, cy, cz, dx, dy, dz en cm; el origen, en el suelo): una sola pieza y un material."""
    GS = unreal
    dm = unreal.DynamicMesh()
    for c in cajas:
        _caja(dm, *c)
    if bisel > 0:
        bev = unreal.GeometryScriptMeshBevelOptions()
        bev.set_editor_property('bevel_distance', bisel)
        GS.GeometryScript_MeshModeling.apply_mesh_polygroup_bevel(dm, bev)
    GS.GeometryScript_Normals.compute_split_normals(dm, unreal.GeometryScriptSplitNormalsOptions(), unreal.GeometryScriptCalculateNormalsOptions())
    if eal.does_asset_exist(ruta):
        eal.delete_asset(ruta)
    r = GS.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm, ruta, unreal.GeometryScriptCreateNewStaticMeshAssetOptions())
    sm = r[0] if isinstance(r, tuple) else r
    mi = unreal.load_asset(DM + '/' + material)
    if sm and mi:
        sm.set_material(0, mi)
        eal.save_loaded_asset(sm, False)
    return sm


def _fila_legajos(semilla, ancho=88.0):
    """Una fila de legajos de pie a lo largo de X (centrada, de ancho cm): gruesos y finos, altos y bajos, alguno más
    metido que otro, un hueco y un par tumbados encima. Siempre igual para la misma semilla."""
    import random
    r = random.Random(semilla)
    cajas, x = [], -ancho / 2.0
    while x < ancho / 2.0 - 3.0:
        g = r.choice((2.5, 3.5, 3.5, 5.0, 6.5, 8.0))
        if r.random() < 0.12:
            x += r.uniform(3.0, 7.0)      # hueco: uno que falta
            continue
        if x + g > ancho / 2.0:
            break
        alto, fondo = r.uniform(25.0, 32.0), r.uniform(21.0, 25.0)
        cajas.append((x + g / 2.0, r.uniform(-1.5, 1.5), alto / 2.0, g, fondo, alto))
        x += g + r.uniform(0.2, 0.7)
    return cajas


def legajos():
    """Tanda 34: lo que le faltaba al archivo y a transmisiones. «legajos» y «legajos_oscuros» (filas de carpetas de
    pie, 88 cm de ancho, para las baldas) y «papeles» (hojas sueltas y un taco, para las mesas). Sin texturas nuevas:
    tela basta clara (MI_colchon) y madera oscura (MI_madera), así que no suman memoria de vídeo."""
    _malla_cajas('/Game/Tarsis/Atrezo/legajos/SM_legajos', _fila_legajos(34), 0.25, 'MI_colchon')
    _malla_cajas('/Game/Tarsis/Atrezo/legajos_oscuros/SM_legajos_oscuros', _fila_legajos(35), 0.25, 'MI_madera')
    # tanda 39: lomos. A cada legajo, la cinta que lo ata (una banda algo más ancha que la carpeta) y el tejuelo en
    # el lomo, por las dos caras (la fila se coloca girada a un lado o a otro). Sin texturas: es geometría con el
    # material contrario al de la carpeta (oscuro sobre las claras, claro sobre las oscuras)
    def lomos(cajas):
        out = []
        for cx, cy, cz, g, fondo, alto in cajas:
            out.append((cx, cy, alto * 0.30, g + 0.3, fondo + 0.3, 1.0))
            for lado in (-1.0, 1.0):
                out.append((cx, cy + lado * (fondo / 2.0 + 0.1), alto * 0.68, g * 0.72, 0.3, min(6.5, alto * 0.22)))
        return out
    _malla_cajas('/Game/Tarsis/Atrezo/legajos_lomo/SM_legajos_lomo', lomos(_fila_legajos(34)), 0.0, 'MI_madera')
    _malla_cajas('/Game/Tarsis/Atrezo/legajos_oscuros_lomo/SM_legajos_oscuros_lomo', lomos(_fila_legajos(35)), 0.0, 'MI_colchon')
    hojas = [(0, 0, 0.6, 21.0, 29.7, 1.2), (17, 9, 0.15, 21.0, 29.7, 0.3), (-15, -12, 0.15, 29.7, 21.0, 0.3), (6, -24, 0.15, 21.0, 14.8, 0.3)]
    _malla_cajas('/Game/Tarsis/Atrezo/papeles/SM_papeles', hojas, 0.0, 'MI_colchon')


def mallas():
    """Las mallas que hace este script (taquilla, colchón, manta, legajos, papeles): antes de colocar el atrezo."""
    taquilla()
    telas()
    legajos()


# ---------------------------------------------------------------- tanda 19: techo, instalación, detalles, luz de ventana

CUBO = '/Engine/BasicShapes/Cube.Cube'
CILINDRO = '/Engine/BasicShapes/Cylinder.Cylinder'


def pieza(nombre, malla, pos, tam, material, rot=unreal.Rotator(0, 0, 0), sombra=True, tags=()):
    """Pieza hecha con las formas básicas del motor (cubo/cilindro de 100 uu, centrados): tam en cm."""
    m = unreal.load_asset(malla)
    a = eas().spawn_actor_from_object(m, pos, rot)
    a.set_actor_label(nombre)
    a.set_folder_path(CARPETA)
    a.set_actor_scale3d(V(tam[0] / 100.0, tam[1] / 100.0, tam[2] / 100.0))
    if tags:
        a.tags = [unreal.Name(t) for t in tags]
    c = a.static_mesh_component
    c.set_mobility(unreal.ComponentMobility.STATIC)
    c.set_collision_profile_name('NoCollision')
    c.set_editor_property('cast_shadow', sombra)
    mi = unreal.load_asset(material) if isinstance(material, str) else material
    if mi:
        c.set_material(0, mi)
    return a


def material_emisivo():
    """M_TuboEncendido: el tubo del fluorescente que está encendido (emisivo frío; no ilumina, la luz es la del foco)."""
    ruta = DM + '/M_TuboEncendido'
    if eal.does_asset_exist(ruta):
        return unreal.load_asset(ruta)
    m = tools.create_asset('M_TuboEncendido', DM, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    c = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c.set_editor_property('constant', unreal.LinearColor(7.0, 8.5, 9.5, 1))
    mel.connect_material_property(c, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m)
    eal.save_loaded_asset(m, False)
    return m


def material_barrotes():
    """M_Barrotes: función de luz con franjas cada 12 cm a lo largo de X (los barrotes de la ventana sobre el suelo)."""
    ruta = DM + '/M_Barrotes'
    if eal.does_asset_exist(ruta):
        return unreal.load_asset(ruta)
    m = tools.create_asset('M_Barrotes', DM, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_LIGHT_FUNCTION)
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
    wp = E(unreal.MaterialExpressionWorldPosition, -900, 0)
    mx = E(unreal.MaterialExpressionComponentMask, -750, 0)
    for k, v in (('r', True), ('g', False), ('b', False), ('a', False)):
        mx.set_editor_property(k, v)
    uno(wp, mx)
    dv = E(unreal.MaterialExpressionDivide, -600, 0)
    dv.set_editor_property('const_b', 12.0)
    mel.connect_material_expressions(mx, '', dv, 'A')
    fr = E(unreal.MaterialExpressionFrac, -480, 0)
    uno(dv, fr)
    st = E(unreal.MaterialExpressionStep, -360, 0)   # luz donde frac > 0,22 (el 22 % es barrote)
    st.set_editor_property('const_y', 0.22)
    if not mel.connect_material_expressions(fr, '', st, 'X'):
        mel.connect_material_expressions(fr, '', st, '')
    mel.connect_material_property(st, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m)
    eal.save_loaded_asset(m, False)
    return m


def techo():
    """Cerchas de madera a la vista cada 2,5 m, tres correas a lo largo, las pantallas de los fluorescentes (una
    encendida, con su tubo emisivo; las otras apagadas), el tubo del cable hasta el interruptor junto a la puerta
    y la salida de humos de la estufa hasta el techo. Sin colisión y fuera del paso."""
    madera = DM + '/MI_madera'
    hierro = DM + '/MI_hierro'
    for i, x in enumerate(range(270, 2200, 250)):
        pieza('Techo_Cercha_%d' % i, CUBO, V(x, 2600, 345), (15, 800, 22), madera)
    for i, y in enumerate((2400, 2600, 2800)):
        pieza('Techo_Correa_%d' % i, CUBO, V(1172, y, 329), (2055, 8, 10), madera, sombra=False)
    fluor = unreal.load_asset('/Game/Tarsis/Atrezo/mounted_fluorescent_lights/mounted_fluorescent_lights/StaticMeshes/mounted_fluorescent_lights_a')
    for i, x in enumerate((450, 1750)):
        a = eas().spawn_actor_from_object(fluor, V(x, 2570, 324), unreal.Rotator(0, 0, 0)) if fluor else None
        if a:
            a.set_actor_label('Techo_FluorescenteApagado_%d' % i); a.set_folder_path(CARPETA)
            a.static_mesh_component.set_collision_profile_name('NoCollision')
    pieza('Techo_TuboEncendido', CUBO, V(1150, 2600, 351), (86, 2.5, 2.5), material_emisivo(), sombra=False)
    # cable: por el techo hasta el muro norte y bajando hasta el interruptor, al lado de la puerta
    pieza('Cable_Techo', CUBO, V(1300, 2400, 352), (3, 400, 3), hierro, sombra=False)
    pieza('Cable_Pared', CUBO, V(1300, 2206, 245), (3, 3, 215), hierro, sombra=False)
    pieza('Interruptor', CUBO, V(1300, 2208, 132), (8, 4, 12), hierro, sombra=False)
    # salida de humos de la estufa (la estufa de bidón mide 86 cm)
    pieza('Estufa_Chimenea', CILINDRO, V(560, 2260, 86 + 135), (15, 15, 270), hierro)


def ventanas_luz():
    """La luna por las ventanas del muro norte: un foco frío sin sombra por ventana que pinta en el suelo la franja
    de luz con los barrotes (función de luz M_Barrotes). El muro es macizo: el foco va dentro y no proyecta sombra."""
    lf = material_barrotes()
    for i, x in enumerate((1120, 1700)):
        a = poner(unreal.SpotLight, 'Luz_Ventana_%d' % i, V(x, 2215, 230), unreal.Rotator(0, -55, 90))
        c = a.spot_light_component
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
        c.set_editor_property('intensity', 260.0)
        c.set_editor_property('light_color', color(0.55, 0.7, 1.0))
        # 400 cm: el haz llega al suelo a unos 2,8 m; con más radio la función de luz se calcula en más pantalla
        c.set_editor_property('attenuation_radius', 400.0)
        c.set_editor_property('outer_cone_angle', 22.0)
        c.set_editor_property('inner_cone_angle', 14.0)
        c.set_editor_property('cast_shadows', False)
        c.set_editor_property('light_function_material', lf)


def detalles():
    """Tablón de avisos con papeles en el muro este y una toalla colgada de una litera."""
    madera = DM + '/MI_madera'
    papel = DM + '/MI_colchon'
    pieza('Tablon', CUBO, V(2197, 2420, 170), (3, 100, 70), madera)
    import random
    r = random.Random(7)
    for i in range(6):
        pieza('Tablon_Papel_%d' % i, CUBO, V(2194.5, 2420 + r.uniform(-38, 38), 170 + r.uniform(-24, 24)),
              (0.3, r.choice((21, 15)), r.choice((29.7, 21))), papel, rot=unreal.Rotator(r.uniform(-6, 6), 0, 0), sombra=False)
    pieza('Toalla', CUBO, V(750, 2412, 98), (40, 2, 55), papel, sombra=False)


def interior():
    """Exposición propia del barracón por dentro (el interior se lee sin aclarar la captura)."""
    v = poner(unreal.PostProcessVolume, 'PP_BarraconDentro', V(1172, 2600, 180))
    v.set_actor_scale3d(V(10.3, 4.0, 1.8))
    v.set_editor_property('unbound', False)
    v.set_editor_property('priority', 2.0)
    v.set_editor_property('blend_radius', 150.0)
    s = v.settings
    s.set_editor_property('override_auto_exposure_bias', True)
    s.set_editor_property('auto_exposure_bias', 1.4)
    v.settings = s


def manchas_19():
    # humedad bajo las ventanas del muro norte (apunta a -Y) y desconchones en el zócalo (manchas claras pequeñas)
    for i, x in enumerate((1120, 1700)):
        mancha('Mancha_Ventana_%d' % i, V(x, 2210, 120), 150, 160, -90, 0.8, (0.05, 0.045, 0.035))
    for i, (pos, hacia) in enumerate(((V(400, 2990, 60), 90), (V(1650, 2990, 45), 90), (V(2190, 2350, 70), 0), (V(155, 2900, 50), 180))):
        mancha('Desconchon_%d' % i, pos, 34, 26, hacia, 0.9, (0.42, 0.40, 0.34))
    # el camino gastado del pasillo central
    mancha('Mancha_Pasillo', V(1200, 2600, 6), 1900, 260, 'abajo', 0.3, (0.03, 0.028, 0.024))
    # cuando llueve: charco y pisadas mojadas desde la puerta norte (etiqueta «lluvia»: solo se ven con lluvia)
    a = mancha('Charco_Puerta', V(1500, 2275, 6), 170, 120, 'abajo', 0.85, (0.015, 0.015, 0.014))
    a.tags = [unreal.Name('lluvia')]
    for i in range(6):
        a = mancha('Pisada_%d' % i, V(1490 + (18 if i % 2 else -18), 2340 + i * 55, 6), 26, 12, 'abajo', 0.6, (0.02, 0.02, 0.018), giro=90)
        a.tags = [unreal.Name('lluvia')]


def todo():
    mallas()
    limpiar()
    luces()
    sonidos()
    posproceso()
    manchas()
    techo()
    ventanas_luz()
    detalles()
    interior()
    manchas_19()


if __name__ == '__main__':
    todo()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
