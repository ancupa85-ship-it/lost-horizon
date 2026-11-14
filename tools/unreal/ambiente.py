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
    c.set_editor_property('cast_shadows', True)
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
    fx = poner(unreal.SpotLight, 'Luz_Flexo', V(1172, 2448, 152), unreal.Rotator(0, -80, 200), tags=('electrico_luz',))
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
    eal.save_loaded_asset(s)
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
    eal.save_loaded_asset(mi)
    sm.set_material(0, mi)
    sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    sms.remove_collisions(sm)
    sms.add_simple_collisions(sm, unreal.ScriptCollisionShapeType.BOX)
    eal.save_loaded_asset(sm)
    log('taquilla creada:', TAQUILLA)
    return sm


# ---------------------------------------------------------------- manchas: humedad, salitre y mugre (calcomanías)

def material_mancha():
    """M_Mancha: calcomanía de mancha irregular (máscara redonda difusa x ruido del mundo), oscura y algo húmeda.
    Parámetros: Color y Fuerza (opacidad)."""
    ruta = DM + '/M_Mancha'
    if eal.does_asset_exist(ruta):
        return unreal.load_asset(ruta)
    m = tools.create_asset('M_Mancha', DM, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    # las calcomanías en 5.8 solo admiten transmitancia o alfa premultiplicado; con colores tan oscuros da igual premultiplicar
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ALPHA_COMPOSITE)
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
    col = E(unreal.MaterialExpressionVectorParameter, -600, -200)
    col.set_editor_property('parameter_name', 'Color'); col.set_editor_property('default_value', unreal.LinearColor(0.045, 0.038, 0.028, 1))
    mel.connect_material_property(col, '', unreal.MaterialProperty.MP_BASE_COLOR)
    # sin rugosidad: con alfa premultiplicado se escribiría en toda la caja de la calcomanía (se vería un rectángulo)
    uv = E(unreal.MaterialExpressionTextureCoordinate, -900, 200)
    sm = E(unreal.MaterialExpressionSphereMask, -700, 200)
    c05 = E(unreal.MaterialExpressionConstant2Vector, -900, 320)
    c05.set_editor_property('r', 0.5); c05.set_editor_property('g', 0.5)
    mel.connect_material_expressions(uv, '', sm, 'A')
    mel.connect_material_expressions(c05, '', sm, 'B')
    sm.set_editor_property('attenuation_radius', 0.5); sm.set_editor_property('hardness_percent', 15.0)
    ruido = E(unreal.MaterialExpressionNoise, -700, 400)
    ruido.set_editor_property('scale', 0.03); ruido.set_editor_property('levels', 3)
    ruido.set_editor_property('noise_function', unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX)
    ruido.set_editor_property('output_min', -0.4); ruido.set_editor_property('output_max', 1.0)
    mu = E(unreal.MaterialExpressionMultiply, -500, 300)
    mel.connect_material_expressions(sm, '', mu, 'A')
    mel.connect_material_expressions(ruido, '', mu, 'B')
    fu = E(unreal.MaterialExpressionScalarParameter, -500, 450)
    fu.set_editor_property('parameter_name', 'Fuerza'); fu.set_editor_property('default_value', 0.85)
    mu2 = E(unreal.MaterialExpressionMultiply, -350, 350)
    mel.connect_material_expressions(mu, '', mu2, 'A')
    mel.connect_material_expressions(fu, '', mu2, 'B')
    sat = E(unreal.MaterialExpressionSaturate, -220, 350)
    uno(mu2, sat)
    mel.connect_material_property(sat, '', unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m


def mancha(nombre, pos, ancho, alto, hacia, fuerza=0.85, color_=None, rug=0.35, giro=0.0):
    """hacia: 'abajo' (suelo), 'arriba' (techo) o el yaw al que mira la pared que recibe la mancha (la calcomanía
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
    eal.save_loaded_asset(inst)
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
        eal.save_loaded_asset(sm)
    return sm


def telas():
    """Colchón de tela basta (85 x 186 x 13 cm) y manta de lana doblada (70 x 45 x 9 cm), como piezas de atrezo
    («colchon» y «manta» en atrezo.json). Material: MI_colchon y MI_manta de materiales.py."""
    _malla_tela('/Game/Tarsis/Atrezo/colchon/SM_colchon', 85, 186, 13, 3.5, 'MI_colchon')
    _malla_tela('/Game/Tarsis/Atrezo/manta/SM_manta', 70, 45, 9, 2.5, 'MI_manta')


def mallas():
    """Las mallas que hace este script (taquilla, colchón, manta): antes de colocar el atrezo."""
    taquilla()
    telas()


def todo():
    mallas()
    limpiar()
    luces()
    sonidos()
    posproceso()
    manchas()


if __name__ == '__main__':
    todo()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
