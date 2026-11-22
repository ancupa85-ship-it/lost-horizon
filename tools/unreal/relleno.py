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
import os, random, sys
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

    # sacos terreros: una fila de 6 x 7 capas (1,05 m: tapa agachado), de dos en fondo, a tresbolillo
    sa = Malla()
    rs = random.Random(1983)          # cada saco un poco torcido y de su tamaño (si no, parece un muro de ladrillo)
    for capa in range(7):
        des = 26.0 if capa % 2 else 0.0
        for fila in (-15.0, 15.0):
            for k in range(5 if capa % 2 else 6):
                cx, cy, cz = -130 + k * 52 + des + rs.uniform(-3, 3), fila + rs.uniform(-2.5, 2.5), 7.5 + capa * 14.5 + rs.uniform(-1, 1)
                yaw = rs.uniform(-6, 6)
                la, an = rs.uniform(46, 52), rs.uniform(26, 30)
                sa.caja(cx, cy, cz, la, an, 15, yaw)
    sm = sa.biselar(4.5).asset('SM_Sacos_fila', M['saco'], 'caja')     # canto muy redondo: saco, no ladrillo
    for i, (x, y, yaw) in enumerate(((8250, 3950, 0), (8250, 4350, 0), (7450, 4350, 0), (8560, 4150, 90))):
        colocar_malla(sm, 'Sacos_%d' % i, V(x, y, suelo(x, y)), yaw)

    # tejadillo de chapa sobre cuatro postes (y un banco debajo, en atrezo.json)
    tx, ty = 8750, 3780
    pt = Malla()
    for dx in (-140, 140):
        for dy in (-90, 90):
            pt.caja(tx + dx, ty + dy, 125 + (8 if dy < 0 else 0), 8, 8, 250 + (16 if dy < 0 else 0))
    pt.caja(tx, ty - 90, 245, 300, 6, 10).caja(tx, ty + 90, 237, 300, 6, 10)
    colocar_malla(pt.asset('SM_Tejadillo_postes', M['hierro'], 'caja'), 'Tejadillo_postes', V(0, 0, suelo(tx, ty)))
    ch = Malla().caja(tx, ty, 0, 330, 220, 3)
    a = colocar_malla(ch.asset('SM_Tejadillo_chapa', M['tejado'], 'caja'), 'Tejadillo_chapa', V(0, 0, suelo(tx, ty) + 252))
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


def del_pack(nombre, max_tex=2048):
    """Malla del pack de Fab «Post-Apocalyptic Factory» (Andres lo añadió en la tanda E1). Sus texturas, a 2K como
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
    t = del_pack('SM_LightTruck_01')
    if t:
        colocar_malla(t, 'Camion_ligero', V(7800, 4520, suelo(7700, 4150)), 90.0)   # el suelo de la plaza (junto a la valla el rayo da en ella)
    ne = del_pack('SM_Tyres_01')
    if ne:
        for i, (x, y, z, rot) in enumerate(((8200, 4600, 46, R(0, 0, 10)), (8235, 4590, 46, R(0, 0, -5)))):
            a = colocar_malla(ne, 'Neumatico_%d' % i, V(x, y, suelo(x, y) + z), 0.0)
            a.set_actor_rotation(rot, False)
    bo = del_pack('SM_WoodenCableDrum_01')
    if bo:
        colocar_malla(bo, 'Bobina', V(8900, 4400, suelo(8900, 4400) + 87), 90.0)


def montar():
    limpiar()
    sacos_sin_ingles()
    M = materiales()
    enfermeria(M)
    plaza(M)
    hangar(M)
    vehiculos()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log('relleno de la tanda E1 montado y guardado')


if __name__ == '__main__':
    montar()
