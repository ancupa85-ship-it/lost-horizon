"""Tanda E1: relleno visual de tres zonas vacías de Tarsis (hangar, enfermería con cuarto frío y plaza de armas).

Lo que no es un modelo de Poly Haven (eso va en assets/unreal/atrezo.json y lo pone atrezo.py) se hace aquí con
Geometry Script: el edificio de la enfermería, la puerta de la cámara frigorífica con su candado, el mástil y la
bandera (roja y gualda lisa: sin escudo, que no hay uno fiable de 1983), las filas de sacos terreros, el tejadillo,
el tablón de turnos y los flejes de las cajas. Rótulos con TextRender (sin texturas nuevas: el generador de carteles
pide Pillow). Manchas de aceite y escarcha con M_Mancha (DBuffer modulado, como las de ambiente.py).
Los materiales son instancias del maestro M_LH (proyección por coordenadas de mundo: no hacen falta UV).

Uso (en el editor, nivel Tarsis abierto): py tools/unreal/relleno.py   y después atrezo.py (los muebles se apoyan
en el suelo de la enfermería). Todo va a la carpeta «Relleno» del nivel y se quita y se vuelve a poner cada vez.
Planta (cm): enfermería x 7300-8500, y 2700-3550 (al este de la cocina, en un hueco libre sin rondas); plaza de
armas x 6900-9000, y 3600-4650 (entre la enfermería y el muro de y 4700); hangar x 4000-5800, y 6300-7360.
"""
import math, os, random, sys
import unreal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else r'D:\LostHorizon\lh-gasp\tools\unreal')

V = unreal.Vector
R = unreal.Rotator          # (roll, pitch, yaw)
CARPETA = 'Relleno'
DM = '/Game/Tarsis/Materiales'
DR = '/Game/Tarsis/Relleno'
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
GS = unreal

# enfermería
EX0, EX1, EY0, EY1 = 7300.0, 8500.0, 2700.0, 3550.0
EXT, EH = 20.0, 300.0                  # grosor y alto de los muros
EXP = 8150.0                           # tabique de la cámara frigorífica (x)
PUERTA = (7500.0, 7620.0)              # hueco de la puerta, muro norte
FRIA = (3050.0, 3160.0)                # hueco de la cámara, en el tabique (y)
# plaza de armas
MASTIL = V(7900, 4200, 0)
MASTIL_ALTO = 900.0


def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))


def eas():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def limpiar():
    for a in eas().get_all_level_actors():
        if str(a.get_folder_path()) == CARPETA:
            eas().destroy_actor(a)


def suelo(x, y, desde=400.0):
    h = unreal.SystemLibrary.line_trace_single(mundo(), V(x, y, desde), V(x, y, -200), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                               True, [], unreal.DrawDebugTrace.NONE, True)
    return h.to_tuple()[4].z if h else 0.0


def poner(cls, nombre, pos, rot=R(0, 0, 0), tags=()):
    a = eas().spawn_actor_from_class(cls, pos, rot)
    a.set_actor_label('Relleno_' + nombre)
    a.set_folder_path(CARPETA)
    if tags:
        a.tags = [unreal.Name(t) for t in tags]
    return a


# ---------------------------------------------------------------- materiales

def mi(nombre, padre='MI_pared', tinte=None, **esc):
    """Instancia de M_LH (copia de una que ya está bien: MI_pared, MI_hierro...) con su tinte y escalares."""
    ruta = DM + '/' + nombre
    if not eal.does_asset_exist(ruta):
        eal.duplicate_asset(DM + '/' + padre, ruta)
    m = unreal.load_asset(ruta)
    if tinte:
        mel.set_material_instance_vector_parameter_value(m, 'Tinte', unreal.LinearColor(*tinte, 1))
    for k, v in esc.items():
        mel.set_material_instance_scalar_parameter_value(m, k, v)
    eal.save_loaded_asset(m, False)
    return m


def materiales():
    return {
        'pared': unreal.load_asset(DM + '/MI_pared'),
        'suelo': unreal.load_asset(DM + '/MI_suelo_int'),
        'hormigon': unreal.load_asset(DM + '/MI_hormigon'),
        'tejado': unreal.load_asset(DM + '/MI_tejado'),
        'hierro': unreal.load_asset(DM + '/MI_hierro'),
        'madera': unreal.load_asset(DM + '/MI_madera'),
        'lona': unreal.load_asset(DM + '/MI_lona_camion'),
        'loza': mi('MI_loza', 'MI_pared', (0.82, 0.82, 0.78), Suciedad=0.35),
        'frio': mi('MI_puerta_fria', 'MI_hierro', (0.26, 0.28, 0.29), Suciedad=0.18),
        'blanco': mi('MI_placa_blanca', 'MI_pared', (0.85, 0.84, 0.8), Suciedad=0.25),
        'rojo': mi('MI_cruz_roja', 'MI_pared', (0.55, 0.04, 0.03), Suciedad=0.2),
        'saco': mi('MI_saco_terrero', 'MI_lona_camion', (0.15, 0.125, 0.085), Suciedad=0.9),
        'corcho': mi('MI_corcho', 'MI_madera', (0.55, 0.38, 0.22), Suciedad=0.4),
    }


def material_bandera():
    """M_Bandera: roja y gualda (1-2-1) hecha en el material con la posición local (sin textura) y ondeando con el
    viento: desplazamiento en Y que crece con la distancia al mástil (X local), dos ondas que corren hacia el vuelo."""
    import ambiente
    g = ambiente.Grafo(DM + '/M_Bandera', 'M_Bandera', 'bandera v1')
    if g.hecho:
        return g.m
    g.m.set_editor_property('two_sided', True)
    lp = g.E(unreal.MaterialExpressionLocalPosition, -1200, 0)
    lx = g.canal(lp, 'r', -1000, -100)
    lz = g.canal(lp, 'b', -1000, 100)
    # color: gualda entre 25 y 75 cm de alto, roja fuera
    c25 = g.E(unreal.MaterialExpressionConstant, -1000, 220, r=25.0)
    c75 = g.E(unreal.MaterialExpressionConstant, -1000, 300, r=75.0)
    k = g.E(unreal.MaterialExpressionConstant, -1000, 380, r=0.4)
    a = g.sat(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, lz, c25, -850, 220), k, -700, 220), -560, 220)
    b = g.sat(g.op(unreal.MaterialExpressionMultiply, g.op(unreal.MaterialExpressionSubtract, c75, lz, -850, 320), k, -700, 320), -560, 320)
    mask = g.op(unreal.MaterialExpressionMultiply, a, b, -420, 260)
    rojo = g.E(unreal.MaterialExpressionConstant3Vector, -420, 100, constant=unreal.LinearColor(0.42, 0.012, 0.014, 1))
    gualda = g.E(unreal.MaterialExpressionConstant3Vector, -420, 160, constant=unreal.LinearColor(0.72, 0.42, 0.0, 1))
    col = g.lerp(rojo, gualda, mask, -250, 160)
    g.sale(col, unreal.MaterialProperty.MP_BASE_COLOR)
    g.sale(g.E(unreal.MaterialExpressionConstant, -250, 300, r=0.85), unreal.MaterialProperty.MP_ROUGHNESS)
    # viento: y = (sin(4t - 0.045 x) * 0.12 + sin(7t - 0.09 x + 0.02 z) * 0.03) * x
    t = g.E(unreal.MaterialExpressionTime, -1200, 500)
    def onda(vel, fx, fz, amp, y):
        tt = g.op(unreal.MaterialExpressionMultiply, t, g.E(unreal.MaterialExpressionConstant, -1100, y + 40, r=vel), -950, y)
        fxn = g.op(unreal.MaterialExpressionMultiply, lx, g.E(unreal.MaterialExpressionConstant, -1100, y + 100, r=fx), -950, y + 80)
        arg = g.op(unreal.MaterialExpressionSubtract, tt, fxn, -800, y)
        if fz:
            arg = g.op(unreal.MaterialExpressionAdd, arg, g.op(unreal.MaterialExpressionMultiply, lz, g.E(unreal.MaterialExpressionConstant, -1100, y + 160, r=fz), -950, y + 160), -700, y)
        s = g.E(unreal.MaterialExpressionSine, -600, y)
        g.uno(arg, s)
        s.set_editor_property('period', 6.2831853)
        return g.op(unreal.MaterialExpressionMultiply, s, g.E(unreal.MaterialExpressionConstant, -600, y + 60, r=amp), -480, y)
    w = g.op(unreal.MaterialExpressionAdd, onda(4.0, 0.045, 0.0, 0.12, 500), onda(7.0, 0.09, 0.02, 0.03, 760), -360, 600)
    dy = g.op(unreal.MaterialExpressionMultiply, w, lx, -240, 600)
    cero = g.E(unreal.MaterialExpressionConstant, -240, 700, r=0.0)
    v = g.E(unreal.MaterialExpressionAppendVector, -120, 650)
    v2 = g.E(unreal.MaterialExpressionAppendVector, -20, 650)
    g.une(cero, v, 'A'); g.une(dy, v, 'B'); g.une(v, v2, 'A'); g.une(cero, v2, 'B')
    g.sale(v2, unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    return g.fin()


# ---------------------------------------------------------------- mallas

class Malla:
    """Cajas (y cilindros) en una DynamicMesh y de ahí a una StaticMesh en /Game/Tarsis/Relleno/<nombre>."""
    def __init__(self):
        self.dm = unreal.DynamicMesh()

    def caja(self, cx, cy, cz, dx, dy, dz, yaw=0.0, pasos=(0, 0, 0)):
        t = unreal.Transform(V(cx, cy, cz), R(0, 0, yaw), V(1, 1, 1))
        GS.GeometryScript_Primitives.append_box(self.dm, unreal.GeometryScriptPrimitiveOptions(), t, dx, dy, dz, pasos[0], pasos[1], pasos[2],
                                                unreal.GeometryScriptPrimitiveOriginMode.CENTER)
        return self

    def cilindro(self, cx, cy, z0, radio, alto, lados=12):
        t = unreal.Transform(V(cx, cy, z0), R(0, 0, 0), V(1, 1, 1))
        GS.GeometryScript_Primitives.append_cylinder(self.dm, unreal.GeometryScriptPrimitiveOptions(), t, radio, alto, lados, 1, True,
                                                     unreal.GeometryScriptPrimitiveOriginMode.BASE)
        return self

    def esfera(self, cx, cy, cz, radio, escala=(1, 1, 1)):
        t = unreal.Transform(V(cx, cy, cz), R(0, 0, 0), V(*escala))
        GS.GeometryScript_Primitives.append_sphere_lat_long(self.dm, unreal.GeometryScriptPrimitiveOptions(), t, radio, 8, 8,
                                                            unreal.GeometryScriptPrimitiveOriginMode.CENTER)
        return self

    def biselar(self, d=1.0):
        bev = unreal.GeometryScriptMeshBevelOptions()
        bev.set_editor_property('bevel_distance', d)
        GS.GeometryScript_MeshModeling.apply_mesh_polygroup_bevel(self.dm, bev)
        return self

    def asset(self, nombre, material, colision='compleja'):
        ruta = DR + '/' + nombre
        GS.GeometryScript_Normals.compute_split_normals(self.dm, unreal.GeometryScriptSplitNormalsOptions(), unreal.GeometryScriptCalculateNormalsOptions())
        if eal.does_asset_exist(ruta):
            eal.delete_asset(ruta)
        r = GS.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(self.dm, ruta, unreal.GeometryScriptCreateNewStaticMeshAssetOptions())
        sm = r[0] if isinstance(r, tuple) else r
        if not sm:
            log('AVISO: no se ha creado', nombre)
            return None
        sm.set_material(0, material)
        sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        sms.remove_collisions(sm)
        if colision == 'caja':
            sms.add_simple_collisions(sm, unreal.ScriptCollisionShapeType.BOX)
        elif colision == 'compleja':
            # muros con huecos: la caja simple taparía la puerta. Colisión con los propios triángulos
            bs = sm.get_editor_property('body_setup')
            bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        eal.save_loaded_asset(sm, False)
        return sm


def saco_dm():
    """Un saco terrero de 52 x 30 x 16 cm: caja subdividida, alisada (las esquinas se redondean y el centro abomba) y
    con la costura del canto largo de arriba."""
    dm = unreal.DynamicMesh()
    GS.GeometryScript_Primitives.append_box(dm, unreal.GeometryScriptPrimitiveOptions(), unreal.Transform(), 52, 30, 16, 8, 5, 3,
                                            unreal.GeometryScriptPrimitiveOriginMode.CENTER)
    o = unreal.GeometryScriptIterativeMeshSmoothingOptions()
    o.set_editor_property('num_iterations', 6)
    o.set_editor_property('alpha', 0.45)
    GS.GeometryScript_MeshDeformers.apply_iterative_smoothing_to_mesh(dm, unreal.GeometryScriptMeshSelection(), o)
    # el alisado lo encoge: se vuelve a su tamaño, algo más abombado de alto que de largo
    b = GS.GeometryScript_MeshQueries.get_mesh_bounding_box(dm)
    ex = b.max - b.min
    GS.GeometryScript_MeshTransforms.scale_mesh(dm, V(52.0 / max(ex.x, 1), 30.0 / max(ex.y, 1), 17.0 / max(ex.z, 1)), V(0, 0, 0))
    # la costura: un cordón fino a lo largo del canto de arriba, hacia un lado
    GS.GeometryScript_Primitives.append_box(dm, unreal.GeometryScriptPrimitiveOptions(), unreal.Transform(V(0, 9, 7.2), R(0, 0, 0), V(1, 1, 1)),
                                            44, 1.2, 1.2, 0, 0, 0, unreal.GeometryScriptPrimitiveOriginMode.CENTER)
    return dm


def fila_sacos(nombre, material, largo, capas, fondo=2, semilla=1983):
    """Fila de sacos a tresbolillo: `largo` sacos por capa, `capas` de alto, `fondo` de fondo; cada uno algo torcido."""
    base = saco_dm()
    dm = unreal.DynamicMesh()
    rs = random.Random(semilla)
    filas = [(-15.0 + 30.0 * f) - 15.0 * (fondo - 1) + 15.0 for f in range(fondo)] if fondo > 1 else [0.0]
    for capa in range(capas):
        des = 26.0 if capa % 2 else 0.0
        for fy in filas:
            for k in range(largo - 1 if capa % 2 else largo):
                cx = -26.0 * (largo - 1) + k * 52 + des + rs.uniform(-3, 3)
                t = unreal.Transform(V(cx, fy + rs.uniform(-2.5, 2.5), 8.0 + capa * 14.5 + rs.uniform(-1, 1)),
                                     R(rs.uniform(-3, 3), rs.uniform(-3, 3), rs.uniform(-7, 7)), V(rs.uniform(0.92, 1.04), rs.uniform(0.92, 1.05), 1.0))
                GS.GeometryScript_MeshEdits.append_mesh(dm, base, t)
    m = Malla()
    m.dm = dm
    return m.asset(nombre, material, 'caja')


def colocar_malla(sm, nombre, pos, yaw=0.0, colision=True, tags=()):
    if not sm:
        return None
    a = eas().spawn_actor_from_object(sm, pos, R(0, 0, yaw))
    a.set_actor_label('Relleno_' + nombre)
    a.set_folder_path(CARPETA)
    c = a.static_mesh_component
    c.set_mobility(unreal.ComponentMobility.STATIC)
    if not colision:
        c.set_collision_profile_name('NoCollision')
    if tags:
        a.tags = [unreal.Name(t) for t in tags]
    return a


def rotulo(nombre, texto, pos, yaw, tam, color=(22, 20, 18), alinear='centro'):
    """Letras de plantilla pintadas (TextRender con el material de texto opaco, con luz)."""
    a = poner(unreal.TextRenderActor, nombre, pos, R(0, 0, yaw))
    t = a.text_render
    t.set_text(texto)
    t.set_world_size(tam)
    t.set_text_render_color(unreal.Color(color[2], color[1], color[0], 255))
    t.set_horizontal_alignment(unreal.HorizTextAligment.EHTA_CENTER if alinear == 'centro' else unreal.HorizTextAligment.EHTA_LEFT)
    t.set_vertical_alignment(unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
    m = unreal.load_asset('/Engine/EngineMaterials/DefaultTextMaterialOpaque')
    if m:
        t.set_text_material(m)
    t.set_collision_profile_name('NoCollision')
    return a


def mancha(nombre, pos, ancho, alto, fuerza, color, giro=0.0, hacia='abajo'):
    import ambiente
    base = ambiente.material_mancha()
    rot = R(0, -90, giro) if hacia == 'abajo' else R(giro, 0, hacia)
    a = poner(unreal.DecalActor, nombre, pos, rot)
    ruta = DM + '/Manchas/MI_Relleno_' + nombre
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    inst = unreal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset('MI_Relleno_' + nombre, DM + '/Manchas', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(inst, base)
    mel.set_material_instance_scalar_parameter_value(inst, 'Fuerza', fuerza)
    mel.set_material_instance_vector_parameter_value(inst, 'Color', unreal.LinearColor(*color, 1))
    eal.save_loaded_asset(inst, False)
    a.decal.set_decal_material(inst)
    a.decal.set_editor_property('decal_size', V(20, ancho / 2.0, alto / 2.0))
    return a


def luz(nombre, pos, lumenes, radio, color, sombra=True, tags=()):
    a = poner(unreal.PointLight, nombre, pos, tags=tags)
    c = a.light_component
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
    c.set_editor_property('intensity', lumenes)
    c.set_editor_property('attenuation_radius', radio)
    c.set_editor_property('light_color', unreal.Color(color[2], color[1], color[0], 255))
    c.set_editor_property('cast_shadows', sombra)
    c.set_editor_property('source_length', 90.0)
    return a


# ---------------------------------------------------------------- enfermería

def enfermeria(M):
    z0 = suelo((EX0 + EX1) / 2, EY0 + 150)
    t, h = EXT, EH
    mu = Malla()
    # muros exteriores (el norte, en dos tramos a los lados del hueco de la puerta y un dintel)
    mu.caja((EX0 + EX1) / 2, EY0 + t / 2, h / 2, EX1 - EX0, t, h)                           # sur
    mu.caja(EX0 + t / 2, (EY0 + EY1) / 2, h / 2, t, EY1 - EY0, h)                           # oeste
    mu.caja(EX1 - t / 2, (EY0 + EY1) / 2, h / 2, t, EY1 - EY0, h)                           # este
    p0, p1 = PUERTA
    mu.caja((EX0 + p0) / 2, EY1 - t / 2, h / 2, p0 - EX0, t, h)
    mu.caja((p1 + EX1) / 2, EY1 - t / 2, h / 2, EX1 - p1, t, h)
    mu.caja((p0 + p1) / 2, EY1 - t / 2, (210 + h) / 2, p1 - p0, t, h - 210)
    # tabique de la cámara frigorífica, con su hueco
    f0, f1 = FRIA
    mu.caja(EXP, (EY0 + f0) / 2, h / 2, t, f0 - EY0, h)
    mu.caja(EXP, (f1 + EY1) / 2, h / 2, t, EY1 - f1, h)
    mu.caja(EXP, (f0 + f1) / 2, (210 + h) / 2, t, f1 - f0, h - 210)
    # zócalo pintado (un dedo más grueso) por dentro, en el muro sur y el oeste
    mu.caja((EX0 + EXP) / 2, EY0 + t + 1, 60, EXP - EX0 - 2 * t, 2, 120)
    sm = mu.asset('SM_Enfermeria_muros', M['pared'])
    colocar_malla(sm, 'Enfermeria_muros', V(0, 0, z0))
    sl = Malla().caja((EX0 + EX1) / 2, (EY0 + EY1) / 2, 1.0, EX1 - EX0 - 2 * t, EY1 - EY0 - 2 * t, 2.0)
    colocar_malla(sl.asset('SM_Enfermeria_suelo', M['suelo'], 'caja'), 'Enfermeria_suelo', V(0, 0, z0))
    te = Malla().caja((EX0 + EX1) / 2, (EY0 + EY1) / 2, h + 9, EX1 - EX0 + 40, EY1 - EY0 + 40, 18)
    colocar_malla(te.asset('SM_Enfermeria_techo', M['hormigon'], 'caja'), 'Enfermeria_techo', V(0, 0, z0))

    # puerta de la cámara frigorífica: chapa gruesa, bisagras, cierre de palanca y el candado en su aldaba
    x = EXP - t / 2 - 4
    pu = Malla().caja(x, (f0 + f1) / 2, 105, 8, f1 - f0 - 4, 208).biselar(1.2)
    for zz in (40, 170):
        pu.caja(x - 5, f0 + 6, zz, 4, 6, 14)
    pu.caja(x - 6, f1 - 14, 105, 4, 10, 40)            # palanca
    sm = pu.asset('SM_Puerta_fria', M['frio'], 'caja')
    colocar_malla(sm, 'Puerta_fria', V(0, 0, z0))
    ca = Malla().caja(x - 9, f1 - 14, 112, 3, 9, 3).caja(x - 10, f1 - 14, 100, 3, 6, 8)     # aldaba y cuerpo del candado
    ca.cilindro(x - 10, f1 - 14, 104, 2.2, 6, 8)
    colocar_malla(ca.asset('SM_Candado', M['hierro'], 'ninguna'), 'Candado', V(0, 0, z0), colision=False)
    # escarcha: en la chapa (abajo, donde se pega el frío) y en el suelo delante
    mancha('Escarcha_puerta', V(x - 6, (f0 + f1) / 2, z0 + 40), 120, 70, 0.55, (0.62, 0.68, 0.74), hacia=180.0)
    mancha('Escarcha_suelo', V(EXP - 60, (f0 + f1) / 2, z0 + 2), 110, 130, 0.45, (0.58, 0.64, 0.7))

    # lavabo y báscula, en el muro oeste
    la = Malla().caja(EX0 + t + 22, 2950, 82, 44, 56, 18).caja(EX0 + t + 6, 2950, 40, 12, 12, 80)
    la.caja(EX0 + t + 4, 2950, 102, 6, 4, 14)          # grifo
    colocar_malla(la.biselar(0.8).asset('SM_Lavabo', M['loza'], 'caja'), 'Lavabo', V(0, 0, z0))
    ba = Malla().caja(EX0 + t + 30, 3070, 4, 38, 38, 8).caja(EX0 + t + 14, 3070, 58, 5, 5, 104).caja(EX0 + t + 16, 3070, 116, 10, 26, 22)
    colocar_malla(ba.asset('SM_Bascula', M['hierro'], 'caja'), 'Bascula', V(0, 0, z0))
    # biombo de tres hojas: tubo y tela
    bi = Malla()
    for k in range(3):
        cx = 7790 + k * 52
        bi.caja(cx, 2980 + k * 10, 95, 50, 2.5, 150)
    colocar_malla(bi.asset('SM_Biombo_tela', M['blanco'], 'caja'), 'Biombo', V(0, 0, z0))
    bt = Malla()
    for k in range(4):
        bt.cilindro(7764 + k * 52, 2975 + k * 10, 0, 1.4, 175, 8)
    colocar_malla(bt.asset('SM_Biombo_tubo', M['hierro'], 'ninguna'), 'Biombo_tubo', V(0, 0, z0), colision=False)

    # cartel de la puerta: placa blanca con la cruz roja y el rótulo
    pl = Malla().caja((p0 + p1) / 2, EY1 + 2, 250, 150, 3, 40).biselar(0.5)
    colocar_malla(pl.asset('SM_Placa_enfermeria', M['blanco'], 'ninguna'), 'Placa_enfermeria', V(0, 0, z0), colision=False)
    cr = Malla().caja((p0 + p1) / 2 - 52, EY1 + 4, 250, 24, 2, 8).caja((p0 + p1) / 2 - 52, EY1 + 4, 250, 8, 2, 24)
    colocar_malla(cr.asset('SM_Cruz_roja', M['rojo'], 'ninguna'), 'Cruz_roja', V(0, 0, z0), colision=False)
    rotulo('Rotulo_enfermeria', 'ENFERMERIA', V((p0 + p1) / 2 + 14, EY1 + 6, z0 + 250), 90, 15)

    # fluorescentes fríos (el de la camilla titila) y el zumbido
    luz('Fluorescente_1', V(7560, 3120, z0 + 285), 320, 620, (205, 225, 255), True, ('electrico',))
    luz('Fluorescente_2', V(7900, 2950, z0 + 285), 260, 560, (200, 222, 255), True, ('parpadeo', 'electrico'))
    log('enfermería en x %d-%d, y %d-%d (suelo a %.0f)' % (EX0, EX1, EY0, EY1, z0))
    return z0


# ---------------------------------------------------------------- plaza de armas

def plaza(M):
    z0 = suelo(MASTIL.x, MASTIL.y)
    ma = Malla().caja(MASTIL.x, MASTIL.y, 15, 80, 80, 30).biselar(2.0)
    colocar_malla(ma.asset('SM_Mastil_base', M['hormigon'], 'caja'), 'Mastil_base', V(0, 0, z0))
    po = Malla().cilindro(MASTIL.x, MASTIL.y, 30, 6.0, MASTIL_ALTO - 30, 12).esfera(MASTIL.x, MASTIL.y, MASTIL_ALTO + 4, 8)
    po.cilindro(MASTIL.x + 7, MASTIL.y, 60, 0.6, MASTIL_ALTO - 70, 4)                     # driza
    colocar_malla(po.asset('SM_Mastil', M['hierro'], 'caja'), 'Mastil', V(0, 0, z0))
    # bandera: 150 x 100, de canto en Y; la X local va del mástil al vuelo (el material la ondea según la X)
    ba = Malla().caja(75, 0, 50, 150, 0.6, 100, pasos=(30, 0, 16))
    sm = ba.asset('SM_Bandera', material_bandera(), 'ninguna')
    colocar_malla(sm, 'Bandera', V(MASTIL.x + 7, MASTIL.y, z0 + MASTIL_ALTO - 110), 0.0, colision=False)

    # sacos terreros: una fila de 6 x 7 capas (1,05 m: tapa agachado), de dos en fondo, a tresbolillo. Tanda E2: cada
    # saco es un saco (caja subdividida y alisada hasta quedar abombada, con su costura), no un ladrillo biselado
    sm = fila_sacos('SM_Sacos_fila', M['saco'], 6, 7)
    for i, (x, y, yaw) in enumerate(((8250, 3950, 0), (8250, 4350, 0), (7450, 4350, 0), (8560, 4150, 90))):
        colocar_malla(sm, 'Sacos_%d' % i, V(x, y, suelo(x, y)), yaw)

    # tejadillo de chapa sobre cuatro postes (y un banco debajo, en atrezo.json)
    tx, ty = 8750, 3780
    pt = Malla()
    for dx in (-140, 140):
        for dy in (-90, 90):
            pt.caja(tx + dx, ty + dy, 125 + (8 if dy < 0 else 0), 8, 8, 250 + (16 if dy < 0 else 0))
    pt.caja(tx, ty - 90, 245, 300, 6, 10).caja(tx, ty + 90, 237, 300, 6, 10)
    colocar_malla(pt.asset('SM_Tejadillo_postes', M['hierro'], 'compleja'), 'Tejadillo_postes', V(0, 0, suelo(tx, ty)))
    ch = Malla().caja(0, 0, 0, 330, 220, 3)            # en el origen: el actor se inclina sobre su sitio, no sobre el del mundo
    a = colocar_malla(ch.asset('SM_Tejadillo_chapa', M['tejado'], 'caja'), 'Tejadillo_chapa', V(tx, ty, suelo(tx, ty) + 252))
    a.set_actor_rotation(R(2.5, 0, 0), False)          # cae hacia el frente

    # pintura del suelo: la línea de formación y las plazas (gastadas)
    for i in range(8):
        x = 7150 + i * 190
        mancha('Linea_formacion_%d' % i, V(x, 3880, z0 + 2), 12, 180, 0.55, (0.6, 0.55, 0.42), giro=0.0)
        mancha('Plaza_%d' % i, V(x, 3820, z0 + 2), 55, 10, 0.5, (0.6, 0.55, 0.42), giro=0.0)
    log('plaza de armas: mástil en', MASTIL.x, MASTIL.y)


# ---------------------------------------------------------------- hangar

def hangar(M):
    z0 = suelo(4900, 6900, 380)
    # tablón de turnos en el muro oeste (corcho con marco) y panel de herramientas sobre el banco
    ta = Malla().caja(4026, 6640, 165, 3, 110, 75).biselar(0.6)
    colocar_malla(ta.asset('SM_Tablon', M['corcho'], 'ninguna'), 'Tablon_turnos', V(0, 0, z0), colision=False)
    pa = Malla().caja(4026, 6960, 160, 2, 150, 70)
    colocar_malla(pa.asset('SM_Panel_herramientas', M['madera'], 'ninguna'), 'Panel_herramientas', V(0, 0, z0), colision=False)
    for i, (y, z) in enumerate(((6640 - 30, 175), (6640 + 25, 170), (6640, 150))):
        h = Malla().caja(4029, y, z, 0.4, 21, 29)
        colocar_malla(h.asset('SM_Hoja_tablon_%d' % i, M['blanco'], 'ninguna'), 'Hoja_tablon_%d' % i, V(0, 0, z0), colision=False)
    rotulo('Rotulo_tablon', 'TURNOS - TALLER', V(4030, 6640, z0 + 196), 0, 6)
    # flejes de las cajas precintadas (junto a la trampilla) y su estarcido
    fl = Malla()
    for cy in (6930, 7060):
        for dy in (-35, 35):
            fl.caja(4300, cy + dy, 23, 55, 2.5, 47.5)
    fl.caja(4300, 6930 - 35, 69, 55, 2.5, 47.5).caja(4300, 6930 + 35, 69, 55, 2.5, 47.5)
    colocar_malla(fl.asset('SM_Flejes', M['hierro'], 'ninguna'), 'Flejes', V(0, 0, z0), colision=False)
    # la caja ya trae una marca en el centro: se tapa con un parche de pintura oliva y encima, en crema, el estarcido
    pa = Malla()
    for cy, cz in ((6930, 23), (7060, 23), (6930, 69)):
        pa.caja(4327.2, cy, cz, 0.6, 58, 36)
    colocar_malla(pa.asset('SM_Parches_LH', unreal.load_asset(DM + '/MI_oliva'), 'ninguna'), 'Parches_LH', V(0, 0, z0), colision=False)
    for i, (cy, cz) in enumerate(((6930, 23), (7060, 23), (6930, 69))):
        rotulo('LH_%d' % i, 'LH', V(4328.2, cy, z0 + cz + 6), 0, 17, (205, 196, 168))
        rotulo('NoAbrir_%d' % i, 'NO ABRIR - ORDEN DE CONTROL', V(4328.2, cy, z0 + cz - 11), 0, 3.4, (205, 196, 168))
    rotulo('LH_larga', 'LH  -  NO ABRIR - ORDEN DE CONTROL', V(4560, 7140, z0 + 31), 0, 7, alinear='centro').set_actor_rotation(R(0, 90, 0), False)
    # manchas de aceite: bajo el coche, junto al banco y al carro de soldar
    mancha('Aceite_coche', V(5150, 7000, z0 + 2), 230, 170, 0.8, (0.025, 0.023, 0.02), 20)
    mancha('Aceite_coche_2', V(5240, 6800, z0 + 2), 90, 60, 0.75, (0.03, 0.026, 0.022), -10)
    mancha('Aceite_banco', V(4190, 6960, z0 + 2), 130, 90, 0.7, (0.03, 0.027, 0.024), 35)
    mancha('Aceite_soldar', V(5400, 6830, z0 + 2), 80, 70, 0.7, (0.03, 0.027, 0.024))
    mancha('Aceite_trampilla', V(4480, 7130, z0 + 2), 100, 50, 0.55, (0.035, 0.03, 0.026), 80)
    # la lámpara del banco (cálida, pequeña, sin sombra)
    luz('Lampara_banco', V(4150, 6950, z0 + 245), 110, 380, (255, 214, 160), False)
    log('hangar vestido (suelo a %.0f)' % z0)


def sacos_sin_ingles():
    """Los sacos de cemento de Poly Haven llevan «CEMENT» impreso (cocina, hangar, coberturas del anillo sur): la
    textura de color se cambia por la arpillera de la casa, teñida de saco viejo. Nada en inglés a la vista."""
    m = unreal.load_asset('/Game/Tarsis/Atrezo/cement_bag/cement_bag/Materials/cement_bag')
    t = unreal.load_asset('/Game/Tarsis/Texturas/T_rough_linen_diff')
    if not m or not t:
        log('AVISO: no se ha podido cambiar la tela de los sacos')
        return
    mel.set_material_instance_texture_parameter_value(m, 'BaseColorTexture', t)
    mel.set_material_instance_vector_parameter_value(m, 'BaseColorFactor', unreal.LinearColor(0.62, 0.5, 0.34, 1))
    eal.save_loaded_asset(m, False)
    log('sacos de cemento: arpillera sin letras')


PACK = '/Game/OvergrownFactoryENV/Meshes/Props/'


def del_pack(nombre, max_tex=1024):
    """Malla del pack de Fab «Post-Apocalyptic Factory» (Andres lo añadió en la tanda E1). Sus texturas, a 1K como
    mucho: la tarjeta tiene 4 GB y la VRAM ya iba por 3,5."""
    m = unreal.load_asset(PACK + nombre)
    if not m:
        log('AVISO: falta del pack', nombre)
        return None
    for sm in m.static_materials:
        if not sm.material_interface:
            continue
        tex, mat = [], sm.material_interface
        while isinstance(mat, unreal.MaterialInstance):      # las de la instancia y las de sus padres
            tex += [p.parameter_value for p in mat.get_editor_property('texture_parameter_values') if p.parameter_value]
            mat = mat.get_editor_property('parent')
        if isinstance(mat, unreal.Material):
            tex += list(mel.get_used_textures(mat))
        for t in tex:
            if isinstance(t, unreal.Texture2D) and t.get_editor_property('max_texture_size') != max_tex:
                t.set_editor_property('max_texture_size', max_tex)
                eal.save_loaded_asset(t, False)
    return m


def vehiculos():
    """Plaza de armas: un camión ligero del pack aparcado junto al muro norte (el coche bajo lona de Poly Haven al lado)
    y neumáticos de repuesto; en el hangar, una bobina de cable vacía junto al taller."""
    # tanda E2: el camión del pack (cabina moderna, musgo en el techo) no es de 1983: en la plaza, otro coche bajo lona
    # (atrezo.json); el camión, abandonado, va al desguace del anillo este (anillo_este)
    ne = del_pack('SM_Tyres_01')
    if ne:
        for i, (x, y, z, rot) in enumerate(((8200, 4600, 46, R(0, 0, 10)), (8235, 4590, 46, R(0, 0, -5)))):
            a = colocar_malla(ne, 'Neumatico_%d' % i, V(x, y, suelo(x, y) + z), 0.0)
            a.set_actor_rotation(rot, False)
    bo = del_pack('SM_WoodenCableDrum_01')
    if bo:
        colocar_malla(bo, 'Bobina', V(8900, 4400, suelo(8900, 4400) + 87), 90.0)


# ================================================================ tanda E2: el anillo exterior y la capilla

def tubo(m, a, b, radio, lados=6):
    """Cilindro de a a b (vientos, riostras, travesaños)."""
    d = V(b.x - a.x, b.y - a.y, b.z - a.z)
    largo = d.length()
    rot = unreal.MathLibrary.make_rot_from_z(d)
    t = unreal.Transform(a, rot, V(1, 1, 1))
    GS.GeometryScript_Primitives.append_cylinder(m.dm, unreal.GeometryScriptPrimitiveOptions(), t, radio, largo, lados, 1, True,
                                                 unreal.GeometryScriptPrimitiveOriginMode.BASE)
    return m


def anillo_norte(M):
    """Norte (entre el muro nuevo, y -1900, y el viejo): el depósito de gasoil del generador (que está dentro, en
    (4300, 1700)), la antena de la emisora con sus vientos y un nido de ametralladora abandonado junto a la brecha."""
    # depósito de gasoil: cilindro tumbado sobre dos cunas de hormigón, con su boca, la manguera y un cubeto bajo
    gx, gy = 4300, -700
    z0 = suelo(gx, gy, 600)
    cu = Malla()
    for dx in (-120, 120):
        cu.caja(gx + dx, gy, 30, 40, 150, 60)
    cu.caja(gx, gy, 6, 480, 230, 12)                      # cubeto
    colocar_malla(cu.asset('SM_Gasoil_cunas', M['hormigon'], 'caja'), 'Gasoil_cunas', V(0, 0, z0))
    de = tubo(Malla(), V(gx - 210, gy, 125), V(gx + 210, gy, 125), 70, 16)
    de.cilindro(gx + 60, gy, 190, 12, 22, 8)              # boca de carga
    tubo(de, V(gx + 210, gy - 30, 100), V(gx + 260, gy - 60, 20), 4, 6)   # manguera al suelo
    colocar_malla(de.asset('SM_Gasoil_deposito', M['oliva'], 'caja'), 'Gasoil_deposito', V(0, 0, z0))
    rotulo('Gasoil_rotulo', 'GASOIL - PROHIBIDO FUMAR', V(gx, gy + 72, z0 + 130), 90, 9, (215, 205, 175))
    # tanda F: la llave de purga en la tapa del depósito (VALVULA, la abre el jugador con la E: TarsisSabotaje.cpp); el
    # chorro (solo con la llave abierta) y el charco que deja (oculto hasta abrirla; es agua para las huellas: botas mojadas)
    vx, vy, vz = VALVULA
    ll = tubo(Malla(), V(gx + 205, vy, vz), V(vx - 4, vy, vz), 3.5, 8)
    tubo(ll, V(vx - 6, vy, vz), V(vx - 2, vy, vz), 11, 12)                        # volante
    tubo(ll, V(vx - 4, vy, vz - 11), V(vx - 4, vy, vz + 11), 1.2, 4)
    tubo(ll, V(vx - 4, vy - 11, vz), V(vx - 4, vy + 11, vz), 1.2, 4)
    colocar_malla(ll.asset('SM_Gasoil_llave', unreal.load_asset(DM + '/MI_hierro_oxidado'), 'ninguna'), 'Gasoil_llave', V(0, 0, z0), colision=False)
    ch = tubo(Malla(), V(vx - 2, vy, vz - 4), V(vx + 22, vy, 2), 3.2, 8)
    colocar_malla(ch.asset('SM_Gasoil_chorro', M['hierro'], 'ninguna'), 'Gasoil_chorro', V(0, 0, z0), colision=False, tags=('sabotaje_chorro',))
    a = poner(unreal.DecalActor, 'Gasoil_charco', V(gx + 300, vy - 10, z0 + 6), R(0, -90, 20), tags=('sabotaje_gasoil',))
    a.decal.set_decal_material(unreal.load_asset(DM + '/Manchas/MI_Per_AguaBarro'))
    a.decal.set_editor_property('decal_size', V(20, 150, 105))
    # el gasoil derramado, a la vista: una lámina negra y brillante (la calcomanía de agua turbia apenas se veía);
    # la calcomanía sigue ahí para las huellas (botas mojadas)
    ga = Malla()
    for (dx, dy, rx, ry) in ((50, -5, 120, 80), (125, 30, 60, 45), (5, -40, 45, 35)):
        ga.esfera(gx + 260 + dx, vy + dy, 0.4, 1.0, (rx, ry, 1.2))
    negro = mi('MI_gasoil_derramado', 'MI_hierro', (0.008, 0.007, 0.006), Suciedad=0.0)
    colocar_malla(ga.asset('SM_Gasoil_derramado', negro, 'ninguna'), 'Gasoil_derramado', V(0, 0, z0), colision=False, tags=('sabotaje_gasoil',))
    # antena de la emisora: mástil de 12 m de tramos, travesaños y tres vientos anclados al suelo. Tanda F: la colisión,
    # solo la del mástil (la caja de toda la malla con los vientos era un bloque invisible de 10 x 9 m)
    ax, ay = 1500, -1100
    z0 = suelo(ax, ay, 600)
    an = Malla().caja(ax, ay, 15, 70, 70, 30)
    an.cilindro(ax, ay, 30, 7, 1170, 8)
    for h in (300, 600, 900, 1150):
        tubo(an, V(ax - 60, ay, h), V(ax + 60, ay, h), 2.5)
    tubo(an, V(ax, ay - 40, 1150), V(ax, ay + 40, 1150), 2.5)
    colocar_malla(an.asset('SM_Antena', M['hierro'], 'caja'), 'Antena', V(0, 0, z0))
    vi = Malla()
    for k in range(3):
        ang = math.radians(90 + k * 120)
        px, py = ax + math.cos(ang) * 600, ay + math.sin(ang) * 600
        tubo(vi, V(ax, ay, 1100), V(px, py, 15), 0.8, 4)
        vi.caja(px, py, 15, 40, 40, 30)                  # muerto de hormigón
    colocar_malla(vi.asset('SM_Antena_vientos', M['hierro'], 'ninguna'), 'Antena_vientos', V(0, 0, z0), colision=False)
    # tanda F: la caja de empalme al pie del mástil, de cara a la base, con el cable que baja de lo alto y se va por el
    # suelo hacia transmisiones; cortado (ANTENA, la E del jugador) cuelgan los dos cabos
    cx, cy = ANTENA
    cj = Malla().caja(cx, cy - 4, 110, 26, 12, 34).caja(cx, cy + 3, 128, 6, 4, 6)
    colocar_malla(cj.asset('SM_Antena_caja', unreal.load_asset(DM + '/MI_hierro_oxidado'), 'ninguna'), 'Antena_caja', V(0, 0, z0), colision=False)
    sano = tubo(Malla(), V(cx + 4, cy + 2, 127), V(cx + 6, cy + 2, 1100), 1.3, 5)
    tubo(sano, V(cx - 6, cy + 2, 93), V(cx - 8, cy + 6, 4), 1.3, 5)
    tubo(sano, V(cx - 8, cy + 6, 4), V(cx - 8, cy + 400, 2), 1.3, 5)
    colocar_malla(sano.asset('SM_Antena_cable', M['lona'], 'ninguna'), 'Antena_cable', V(0, 0, z0), colision=False, tags=('sabotaje_antena_sano',))
    cor = tubo(Malla(), V(cx + 4, cy + 2, 127), V(cx + 6, cy + 2, 1100), 1.3, 5)
    tubo(cor, V(cx - 6, cy + 2, 93), V(cx - 4, cy + 14, 40), 1.3, 5)             # el cabo de abajo, colgando
    tubo(cor, V(cx - 4, cy + 14, 40), V(cx + 10, cy + 30, 3), 1.3, 5)
    tubo(cor, V(cx - 8, cy + 60, 3), V(cx - 8, cy + 400, 2), 1.3, 5)
    cor.caja(cx + 4, cy + 3, 133, 7, 7, 4)                                         # el cabo de arriba, pelado
    colocar_malla(cor.asset('SM_Antena_cable_cortado', M['lona'], 'ninguna'), 'Antena_cable_cortado', V(0, 0, z0), colision=False, tags=('sabotaje_antena',))
    # nido de ametralladora abandonado: un anillo de sacos con la tronera hacia la brecha y una caja de munición vacía
    nx, ny = 2800, -1250
    z0 = suelo(nx, ny, 600)
    seg = fila_sacos('SM_Sacos_nido', M['saco'], 3, 6, 2, 7)
    for k, yaw in enumerate((0, 60, 120, 180, 240)):      # cinco tramos: falta el de atrás (por donde se entra)
        ang = math.radians(yaw - 90)
        colocar_malla(seg, 'Nido_sacos_%d' % k, V(nx + math.cos(ang) * 180, ny + math.sin(ang) * 180, z0), yaw)
    log('anillo norte: gasoil (%d, %d), antena (%d, %d), nido (%d, %d)' % (gx, gy, ax, ay, nx, ny))


ANTENA = (1500, -1055)           # tanda F: caja de empalme de la antena (AntennaLoc del director)
VALVULA = (4545, -700, 55)        # tanda F: llave de purga del gasoil (ValveLoc del director es x + 20: donde te pones)
PASILLO = (-1050, 600, 1200)     # x del centro, y de inicio y de fin: pasillo de 1,20 m de la pista (lo usa prueba_paso)


def anillo_oeste(M):
    """Oeste: el campo de tiro (dianas contra el muro nuevo, el talud de sacos detrás y la línea de tiro) y la pista de
    obstáculos oxidada (vigas, tubos, neumáticos y un pasillo de tablones de 1,20 m): todo sirve de cobertura."""
    z0 = suelo(-1000, 3600, 600)
    # dianas: poste, tablero blanco y tres anillos negros pintados
    di, ne, po = Malla(), Malla(), Malla()
    for k, y in enumerate(range(2500, 5001, 500)):
        x = -1650
        po.caja(x, y - 32, 75, 8, 8, 150).caja(x, y + 32, 75, 8, 8, 150)
        di.caja(x + 2, y, 125, 3, 70, 90)
        for r, z in ((30, 0), (20, 0.4), (9, 0.8)):
            t = unreal.Transform(V(x + 4 + z, y, 125), R(0, 90, 0), V(1, 1, 1))
            GS.GeometryScript_Primitives.append_cylinder((ne if r != 20 else di).dm, unreal.GeometryScriptPrimitiveOptions(), t, r, 0.4, 20, 0, True,
                                                         unreal.GeometryScriptPrimitiveOriginMode.CENTER)
    colocar_malla(po.asset('SM_Dianas_postes', M['madera'], 'compleja'), 'Dianas_postes', V(0, 0, z0))
    colocar_malla(di.asset('SM_Dianas', M['blanco'], 'caja'), 'Dianas', V(0, 0, z0))
    colocar_malla(ne.asset('SM_Dianas_anillos', unreal.load_asset(DM + '/MI_hierro'), 'ninguna'), 'Dianas_anillos', V(0, 0, z0), colision=False)
    ta = fila_sacos('SM_Talud_tiro', M['saco'], 6, 5, 2, 11)
    for i, y in enumerate(range(2600, 5001, 300)):
        colocar_malla(ta, 'Talud_%d' % i, V(-1790, y, z0), 90)
    lt = Malla().caja(-300, 3750, 1, 20, 2600, 2)          # línea de tiro (un listón en el suelo)
    colocar_malla(lt.asset('SM_Linea_tiro', M['madera'], 'ninguna'), 'Linea_tiro', V(0, 0, z0), colision=False)
    ca = Malla().caja(-250, 2300, 110, 4, 160, 60).cilindro(-250, 2240, 0, 4, 150, 6).cilindro(-250, 2360, 0, 4, 150, 6)
    colocar_malla(ca.asset('SM_Cartel_tiro', M['blanco'], 'caja'), 'Cartel_tiro', V(0, 0, z0))
    rotulo('Cartel_tiro_txt', 'CAMPO DE TIRO', V(-246, 2300, z0 + 122), 0, 12)
    rotulo('Cartel_tiro_txt2', 'PROHIBIDO EL PASO DURANTE EL EJERCICIO', V(-246, 2300, z0 + 100), 0, 4.5, (150, 28, 22))
    # pista de obstáculos: vigas en equilibrio, tubos para arrastrarse, neumáticos y el pasillo de tablones
    z0 = suelo(-1000, 1000, 600)
    ob = Malla()
    for k, y in enumerate((300, 520)):                     # dos vigas sobre caballetes
        ob.caja(-600, y, 60, 400, 14, 10)
        for dx in (-180, 180):
            tubo(ob, V(-600 + dx, y - 30, 0), V(-600 + dx, y, 55), 3)
            tubo(ob, V(-600 + dx, y + 30, 0), V(-600 + dx, y, 55), 3)
    for k in range(3):                                     # vallas de salto
        x = -1500 + k * 120
        ob.caja(x, 1600, 45, 6, 150, 6).cilindro(x, 1530, 0, 3, 45, 6).cilindro(x, 1670, 0, 3, 45, 6)
    colocar_malla(ob.asset('SM_Pista_hierros', M['oxido'], 'compleja'), 'Pista_hierros', V(0, 0, z0))
    tu = Malla()
    for k in range(3):                                     # tubos de hormigón para arrastrarse
        tubo(tu, V(-1600, 300 + k * 160, 45), V(-1400, 300 + k * 160, 45), 45, 14)
    colocar_malla(tu.asset('SM_Pista_tubos', M['hormigon'], 'compleja'), 'Pista_tubos', V(0, 0, z0))
    px, py0, py1 = PASILLO                                 # pasillo de tablones: 1,20 m entre las caras de dentro
    pa = Malla().caja(px - 70, (py0 + py1) / 2, 100, 20, py1 - py0, 200).caja(px + 70, (py0 + py1) / 2, 100, 20, py1 - py0, 200)
    colocar_malla(pa.asset('SM_Pista_pasillo', M['madera'], 'compleja'), 'Pista_pasillo', V(0, 0, z0))   # tanda F: con 'caja' era un bloque macizo (los dos muros y el hueco): se rodeaba
    ty = del_pack('SM_Tyres_02')
    if ty:
        for i in range(8):
            x, y = -700 + (i % 4) * 95, 1000 + (i // 4) * 110
            a = colocar_malla(ty, 'Pista_neumatico_%d' % i, V(x, y, z0 + 10), 0.0)
            a.set_actor_rotation(R(0, 90, 0), False)       # tumbados
    log('anillo oeste: campo de tiro x -1800..-250, y 2300..5000; pista y 300..1700; pasillo x %d, y %d-%d' % PASILLO)


def anillo_este(M):
    """Este: el depósito de agua elevado, el gallinero con su corral y el huerto de la tropa, y el desguace (el camión
    del pack, que en la plaza no era de época, aquí abandonado con su musgo; el coche bajo lona y neumáticos)."""
    # depósito de agua sobre cuatro patas de 5 m, con riostras y escalera
    wx, wy = 8500, 500
    z0 = suelo(wx, wy, 900)
    de = Malla()
    for dx in (-110, 110):
        for dy in (-110, 110):
            de.cilindro(wx + dx, wy + dy, 0, 9, 520, 8)
    for h in (150, 350):
        for (ax_, ay_), (bx_, by_) in (((-110, -110), (110, -110)), ((110, -110), (110, 110)), ((110, 110), (-110, 110)), ((-110, 110), (-110, -110))):
            tubo(de, V(wx + ax_, wy + ay_, h), V(wx + bx_, wy + by_, h + 170), 3)
    de.caja(wx, wy, 525, 280, 280, 10)
    for k in range(17):                                    # escalera
        de.caja(wx - 135, wy - 20, 30 + k * 30, 4, 40, 3)
    de.caja(wx - 135, wy - 40, 260, 4, 4, 520).caja(wx - 135, wy, 260, 4, 4, 520)
    colocar_malla(de.asset('SM_Agua_patas', M['oxido'], 'compleja'), 'Agua_patas', V(0, 0, z0))
    ta = Malla().cilindro(wx, wy, 530, 130, 230, 20).cilindro(wx, wy, 760, 60, 25, 12)
    colocar_malla(ta.asset('SM_Agua_deposito', M['oliva'], 'caja'), 'Agua_deposito', V(0, 0, z0))
    # gallinero: caseta de tablas con tejado de chapa y el corral de tela metálica
    gx, gy = 7600, 500
    z0 = suelo(gx, gy, 600)
    ga = Malla().caja(gx, gy, 90, 300, 200, 180)
    colocar_malla(ga.asset('SM_Gallinero', M['madera'], 'caja'), 'Gallinero', V(0, 0, z0))
    te = Malla().caja(0, 0, 0, 340, 240, 3)
    a = colocar_malla(te.asset('SM_Gallinero_tejado', M['tejado'], 'caja'), 'Gallinero_tejado', V(gx, gy, z0 + 188))
    a.set_actor_rotation(R(4, 0, 0), False)
    co = Malla()
    for (x0, y0, x1, y1) in ((gx - 150, gy + 100, gx - 150, gy + 500), (gx - 150, gy + 500, gx + 150, gy + 500), (gx + 150, gy + 500, gx + 150, gy + 100)):
        co.caja((x0 + x1) / 2, (y0 + y1) / 2, 60, max(abs(x1 - x0), 2), max(abs(y1 - y0), 2), 120)
    colocar_malla(co.asset('SM_Corral', unreal.load_asset(DM + '/M_TelaMalla_2f8d8634'), 'compleja'), 'Corral', V(0, 0, z0))   # tanda F: la caja tapaba el corral entero
    rotulo('Gallinero_rotulo', 'GALLINERO - TROPA', V(gx, gy - 102, z0 + 150), -90, 8, (215, 205, 175))
    huerto(M)
    # desguace: el camión del pack abandonado, neumáticos, bidones y una bobina
    z0 = suelo(8600, 1900, 600)
    t = del_pack('SM_LightTruck_01')
    if t:
        a = colocar_malla(t, 'Desguace_camion', V(8650, 1800, z0), 8.0)
        a.set_actor_rotation(R(2.5, -1.5, 8.0), False)    # algo ladeado: sin una rueda
    ne = del_pack('SM_Tyres_01')
    if ne:
        for i, (x, y, z) in enumerate(((8350, 2250, 10), (8350, 2250, 30), (8420, 2290, 10), (8880, 1300, 46))):
            a = colocar_malla(ne, 'Desguace_neumatico_%d' % i, V(x, y, z0 + z), 0.0)
            a.set_actor_rotation(R(0, 90 if z < 40 else 0, i * 37), False)
    bo = del_pack('SM_WoodenCableDrum_02')
    if bo:
        colocar_malla(bo, 'Desguace_bobina', V(8300, 1500, z0 + 87), 30.0)
    log('anillo este: agua (%d, %d), gallinero (%d, %d), huerto, desguace (8650, 1800)' % (wx, wy, gx, gy))


def caballon_dm(largo, ancho, alto, semilla):
    """Tanda F: un caballón de tierra labrada: un cilindro tumbado a lo largo, aplastado y medio enterrado (el lomo
    redondo), con los extremos que bajan al surco: deja de parecer una losa."""
    dm = unreal.DynamicMesh()
    t = unreal.Transform(V(-largo / 2.0, 0, 0), R(0, 90, 0), V(ancho / 2.0, ancho / 2.0, 1))   # el eje del cilindro, a lo largo de X
    GS.GeometryScript_Primitives.append_cylinder(dm, unreal.GeometryScriptPrimitiveOptions(), t, 1.0, largo, 18, 24, True,
                                                 unreal.GeometryScriptPrimitiveOriginMode.BASE)
    # aplastado a la altura pedida (sobre el suelo, la mitad de arriba) y algo hundido
    GS.GeometryScript_MeshTransforms.scale_mesh(dm, V(1, 1, (alto * 2.0) / ancho), V(0, 0, 0))
    b = GS.GeometryScript_MeshQueries.get_mesh_bounding_box(dm)
    GS.GeometryScript_MeshTransforms.translate_mesh(dm, V(-(b.max.x + b.min.x) / 2, -(b.max.y + b.min.y) / 2, -(b.max.z + b.min.z) / 2 - 2))
    return dm


def huerto(M):
    """Tanda F: el huerto de la tropa, de tierra labrada (marrón, en lomos redondeados con su surco) y no de losas grises;
    con coles y matas de hoja (esferas aplastadas y alisadas) y las estacas de las tomateras."""
    tierra = mi('MI_tierra_huerto', 'MI_tierra', (0.07, 0.045, 0.028), Suciedad=1.0, Tamano=90.0)
    hoja = mi('MI_hoja_huerto', 'MI_lona_camion', (0.05, 0.085, 0.03), Suciedad=0.6)
    z0 = suelo(7850, 1500, 600)
    hu, es, pl = unreal.DynamicMesh(), Malla(), unreal.DynamicMesh()
    rs = random.Random(1983)
    # la base: la tierra suelta bajo todo el huerto (asoma en los surcos)
    GS.GeometryScript_Primitives.append_box(hu, unreal.GeometryScriptPrimitiveOptions(), unreal.Transform(V(7850, 1525, -2), R(0, 0, 0), V(1, 1, 1)),
                                            740, 680, 6, 0, 0, 0, unreal.GeometryScriptPrimitiveOriginMode.BASE)
    hoja_dm = unreal.DynamicMesh()
    GS.GeometryScript_Primitives.append_sphere_lat_long(hoja_dm, unreal.GeometryScriptPrimitiveOptions(), unreal.Transform(), 1.0, 8, 10,
                                                        unreal.GeometryScriptPrimitiveOriginMode.CENTER)
    for k in range(6):
        y = 1250 + k * 110
        GS.GeometryScript_MeshEdits.append_mesh(hu, caballon_dm(700, 62, 20, k), unreal.Transform(V(7850, y + rs.uniform(-3, 3), 0), R(0, 0, rs.uniform(-0.6, 0.6)), V(1, 1, 1)))
        if k % 3 == 2:
            for j in range(5):
                es.cilindro(7550 + j * 150, y, 0, 1.5, 80, 4)
            continue
        # coles en las filas de verdura; dejan claros (se han cogido)
        x = 7530.0
        while x < 8170:
            x += rs.uniform(42, 70)
            if rs.random() < 0.18:
                continue
            r = rs.uniform(9, 16) if k % 3 == 0 else rs.uniform(6, 10)
            t = unreal.Transform(V(x, y + rs.uniform(-6, 6), 18 + r * 0.35), R(rs.uniform(-8, 8), rs.uniform(-8, 8), rs.uniform(0, 360)),
                                 V(r * rs.uniform(0.9, 1.15), r * rs.uniform(0.9, 1.15), r * rs.uniform(0.5, 0.7)))
            GS.GeometryScript_MeshEdits.append_mesh(pl, hoja_dm, t)
    m = Malla(); m.dm = hu
    colocar_malla(m.asset('SM_Huerto', tierra, 'ninguna'), 'Huerto', V(0, 0, z0), colision=False)
    m = Malla(); m.dm = pl
    colocar_malla(m.asset('SM_Huerto_matas', hoja, 'ninguna'), 'Huerto_matas', V(0, 0, z0), colision=False)
    colocar_malla(es.asset('SM_Huerto_estacas', M['madera'], 'ninguna'), 'Huerto_estacas', V(0, 0, z0), colision=False)


CAPILLA = (6000, 6800, -1550, -950)    # x0, x1, y0, y1: barracón pequeño en el anillo norte, la puerta al sur


def capilla(M):
    """La capilla del páter Anselmo: barracón de 8 x 6 m con la puerta mirando a la base, bancos, altar sencillo con su
    paño, crucifijo, velas (luz cálida en la noche fría) y el libro de difuntos en un atril (se lee con la E)."""
    x0, x1, y0, y1 = CAPILLA
    z0 = suelo((x0 + x1) / 2, (y0 + y1) / 2, 900)
    t, h = 20.0, 320.0
    mu = Malla()
    mu.caja((x0 + x1) / 2, y0 + t / 2, h / 2, x1 - x0, t, h)
    mu.caja(x0 + t / 2, (y0 + y1) / 2, h / 2, t, y1 - y0, h)
    mu.caja(x1 - t / 2, (y0 + y1) / 2, h / 2, t, y1 - y0, h)
    cx = (x0 + x1) / 2
    mu.caja((x0 + cx - 60) / 2, y1 - t / 2, h / 2, cx - 60 - x0, t, h)
    mu.caja((cx + 60 + x1) / 2, y1 - t / 2, h / 2, x1 - cx - 60, t, h)
    mu.caja(cx, y1 - t / 2, (220 + h) / 2, 120, t, h - 220)
    mu.caja(cx, y1 - t / 2, h + 60, 30, t, 60)               # espadaña
    colocar_malla(mu.asset('SM_Capilla_muros', M['pared'], 'compleja'), 'Capilla_muros', V(0, 0, z0))
    sl = Malla().caja(cx, (y0 + y1) / 2, 1, x1 - x0 - 2 * t, y1 - y0 - 2 * t, 2)
    colocar_malla(sl.asset('SM_Capilla_suelo', M['suelo'], 'caja'), 'Capilla_suelo', V(0, 0, z0))
    te = Malla().caja(cx, (y0 + y1) / 2, h + 9, x1 - x0 + 40, y1 - y0 + 40, 18)
    colocar_malla(te.asset('SM_Capilla_techo', M['tejado'], 'caja'), 'Capilla_techo', V(0, 0, z0))
    cr = Malla().caja(cx, y1 + 2, h + 78, 4, 4, 40).caja(cx, y1 + 2, h + 85, 22, 4, 4)
    colocar_malla(cr.asset('SM_Capilla_cruz', M['hierro'], 'ninguna'), 'Capilla_cruz', V(0, 0, z0), colision=False)
    # altar, paño, crucifijo en la pared del fondo, atril con el libro y velas
    al = Malla().caja(cx, y0 + t + 50, 50, 180, 70, 100).caja(cx + 170, y0 + t + 160, 55, 40, 40, 110)   # altar y atril
    al.caja(cx, y0 + t + 2, 210, 6, 4, 120).caja(cx, y0 + t + 2, 240, 60, 4, 6)                         # crucifijo
    colocar_malla(al.asset('SM_Capilla_altar', M['madera'], 'caja'), 'Capilla_altar', V(0, 0, z0))
    pa = Malla().caja(cx, y0 + t + 50, 101, 190, 74, 2).caja(cx + 170, y0 + t + 160, 113, 34, 26, 5)    # paño y libro
    colocar_malla(pa.asset('SM_Capilla_pano', M['blanco'], 'ninguna'), 'Capilla_pano', V(0, 0, z0), colision=False)
    ve = Malla()
    for k, dx in enumerate((-70, -55, 55, 70)):
        ve.cilindro(cx + dx, y0 + t + 50, 102, 2.2, 18 + (k % 2) * 6, 8)
    for dx in (-15, 0, 15):
        ve.cilindro(cx - 260 + dx, y0 + t + 30, 0, 2.5, 30 + abs(dx), 8)     # velas votivas en el suelo, a un lado
    colocar_malla(ve.asset('SM_Capilla_velas', M['loza'], 'ninguna'), 'Capilla_velas', V(0, 0, z0), colision=False)
    for i, (dx, dy, z) in enumerate(((0, 50, 135), (-260, 30, 45))):
        luz('Vela_%d' % i, V(cx + dx, y0 + t + dy, z0 + z), 35 if i == 0 else 18, 420 if i == 0 else 260, (255, 170, 90), True)
    rotulo('Capilla_rotulo', 'CAPILLA', V(cx, y1 + 12, z0 + 245), 90, 13, (205, 196, 168))
    log('capilla en x %d..%d, y %d..%d (anillo norte; la puerta al sur)' % CAPILLA)


def montar():
    limpiar()
    sacos_sin_ingles()
    M = materiales()
    M['oliva'] = unreal.load_asset(DM + '/MI_oliva')
    M['oxido'] = mi('MI_hierro_oxidado', 'MI_hierro', (0.32, 0.17, 0.09), Suciedad=0.95)
    M['tierra'] = unreal.load_asset(DM + '/MI_tierra')
    enfermeria(M)
    plaza(M)
    hangar(M)
    vehiculos()
    anillo_norte(M)
    anillo_oeste(M)
    anillo_este(M)
    capilla(M)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log('relleno de las tandas E1 y E2 montado y guardado')


if __name__ == '__main__':
    montar()
