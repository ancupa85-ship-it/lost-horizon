"""Tanda J: pulido y aspecto visual. Se monta en el editor con el nivel Tarsis abierto (sin PIE):

    py tools/unreal/visual_j.py

Hace (todo se puede repetir: lo que ya está, se deja o se rehace):
  1. Agujeros en la malla de las vallas: MPC_Cortes (Corte0..3 = x, y, z, radio) y, en M_TelaMalla, un nodo que recorta
     la tela alrededor de cada corte; MI_TelaSolapa (la misma malla, sin recorte) para la solapa doblada.
  2. Materiales pequeños: M_Ascua (la brasa del cigarro), M_Humo (las bocanadas) y M_AlambreBrillo (el cable de las
     trampas, que brilla un poco con la linterna).
  3. El plano de la jefatura: las filas del mapa de base.json en el director (PlanRows) para dibujarlo en el mapa mental.
  4. Lo que más rompía la imagen en el repaso de la tanda J (capturas-tandaJ/antes):
     - el pie de los muros: una sombra de suciedad donde el suelo toca la pared (calcomanías por tramos de muro);
     - las losas de hormigón de los caminos, casi blancas y limpias: más oscuras y con más desgaste;
     - los sacos terreros casi blancos: color de arpillera;
     - las cajas de madera de la entrada, negras: la madera, un punto más clara;
     - el cartel amarillo en blanco del portón: con su texto.
Los ajustes de material se apuntan en el registro ([Tarsis] visual_j ...).
"""
import json, os
import unreal

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DM = '/Game/Tarsis/Materiales'
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
V = unreal.Vector
NOTAS = []


def log(*a):
    t = ' '.join(str(x) for x in a)
    NOTAS.append(t)
    unreal.log('[Tarsis] visual_j ' + t)


def mundo():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def director():
    ds = unreal.GameplayStatics.get_all_actors_of_class(mundo(), unreal.load_class(None, '/Script/PruebaLumen.TarsisDirector'))
    return ds[0] if ds else None


def nuevo_material(nombre):
    ruta = '%s/%s' % (DM, nombre)
    if eal.does_asset_exist(ruta):
        eal.delete_asset(ruta)
    return tools.create_asset(nombre, DM, unreal.Material, unreal.MaterialFactoryNew())


def E(m, cls, x, y):
    return mel.create_material_expression(m, cls, x, y)


def conecta(a, b, entrada, salida=''):
    if not mel.connect_material_expressions(a, salida, b, entrada):
        log('AVISO: no conecta', a.get_name(), salida, '->', b.get_name(), entrada)


def escalar(m, nombre, valor, x, y):
    p = E(m, unreal.MaterialExpressionScalarParameter, x, y)
    p.set_editor_property('parameter_name', nombre)
    p.set_editor_property('default_value', valor)
    return p


def color(m, rgb, x, y):
    c = E(m, unreal.MaterialExpressionConstant3Vector, x, y)
    c.set_editor_property('constant', unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    return c


# ---------------------------------------------------------------- 1. agujeros en la malla

def mpc_cortes():
    ruta = DM + '/MPC_Cortes'
    if eal.does_asset_exist(ruta):
        return eal.load_asset(ruta)
    c = tools.create_asset('MPC_Cortes', DM, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    vs = []
    for i in range(4):
        p = unreal.CollectionVectorParameter()
        p.set_editor_property('parameter_name', 'Corte%d' % i)
        p.set_editor_property('default_value', unreal.LinearColor(0.0, 0.0, 0.0, 0.0))
        vs.append(p)
    c.set_editor_property('vector_parameters', vs)
    eal.save_loaded_asset(c, False)
    log('MPC_Cortes creada')
    return c


CODIGO_CORTES = '''float m = Op;
float4 C[4] = { C0, C1, C2, C3 };
for (int i = 0; i < 4; i++)
{
    if (C[i].w > 0.0)
    {
        float h = length(WP.xy - C[i].xy);
        float z = WP.z - C[i].z;
        float e = 5.0 * sin(z * 0.23 + h * 0.41) + 3.0 * sin(z * 0.61);
        if (h < C[i].w + e && z > -30.0 && z < 108.0 + e) m = 0.0;
    }
}
return lerp(m, Op, Ign);'''


def tela_con_cortes(mpc):
    rutas = [a for a in eal.list_assets(DM, recursive=False) if os.path.basename(a).split('.')[0].startswith('M_TelaMalla_')]
    if not rutas:
        log('AVISO: no hay M_TelaMalla')
        return None
    m = eal.load_asset(rutas[0])
    ts = mel.get_material_property_input_node(m, unreal.MaterialProperty.MP_OPACITY_MASK)
    if ts is not None and ts.get_class().get_name() == 'MaterialExpressionCustom':
        log('la tela ya recorta los cortes', m.get_name())
    else:
        wp = E(m, unreal.MaterialExpressionWorldPosition, -600, 520)
        cu = E(m, unreal.MaterialExpressionCustom, -120, 420)
        cu.set_editor_property('code', CODIGO_CORTES)
        cu.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
        cu.set_editor_property('description', 'TarsisCortes')
        ins = []
        for n in ('Op', 'WP', 'C0', 'C1', 'C2', 'C3', 'Ign'):
            ci = unreal.CustomInput()
            ci.set_editor_property('input_name', n)
            ins.append(ci)
        cu.set_editor_property('inputs', ins)
        conecta(ts, cu, 'Op', 'A')
        conecta(wp, cu, 'WP')
        for i in range(4):
            cp = E(m, unreal.MaterialExpressionCollectionParameter, -600, 600 + 70 * i)
            cp.set_editor_property('collection', mpc)
            cp.set_editor_property('parameter_name', 'Corte%d' % i)
            conecta(cp, cu, 'C%d' % i)
        ign = escalar(m, 'SinCortes', 0.0, -600, 900)
        conecta(ign, cu, 'Ign')
        mel.connect_material_property(cu, '', unreal.MaterialProperty.MP_OPACITY_MASK)
        mel.recompile_material(m)
        eal.save_loaded_asset(m, False)
        log('la tela recorta los cortes', m.get_name())
    ruta = DM + '/MI_TelaSolapa'
    mi = eal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset('MI_TelaSolapa', DM, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property('parent', m)
    mel.set_material_instance_scalar_parameter_value(mi, 'SinCortes', 1.0)
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi, False)
    return m


# ---------------------------------------------------------------- 2. la brasa, el humo y el alambre

def materiales_pequenos():
    # la brasa: sin luz propia del motor (la da la PointLight); solo el color que quema
    m = nuevo_material('M_Ascua')
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    c = color(m, (1.0, 0.32, 0.06), -500, 0)
    b = escalar(m, 'Brillo', 20.0, -500, 150)
    mu = E(m, unreal.MaterialExpressionMultiply, -250, 50)
    conecta(c, mu, 'A'); conecta(b, mu, 'B')
    mel.connect_material_property(mu, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m); eal.save_loaded_asset(m, False)
    # el humo: translúcido con luz (solo se ve donde le da algo: la brasa, una farola, la linterna), bordes blandos
    m = nuevo_material('M_Humo')
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('two_sided', False)
    try:
        m.set_editor_property('translucency_lighting_mode', unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    except Exception:
        pass
    mel.connect_material_property(color(m, (0.42, 0.42, 0.40), -500, -100), '', unreal.MaterialProperty.MP_BASE_COLOR)
    fr = E(m, unreal.MaterialExpressionFresnel, -700, 100)
    fr.set_editor_property('exponent', 1.6)
    om = E(m, unreal.MaterialExpressionOneMinus, -500, 100)
    if not mel.connect_material_expressions(fr, '', om, 'Input'):
        conecta(fr, om, '')
    op = escalar(m, 'Opacidad', 0.3, -500, 250)
    mu = E(m, unreal.MaterialExpressionMultiply, -250, 150)
    conecta(om, mu, 'A'); conecta(op, mu, 'B')
    mel.connect_material_property(mu, '', unreal.MaterialProperty.MP_OPACITY)
    rg = E(m, unreal.MaterialExpressionConstant, -250, 300)
    rg.set_editor_property('r', 1.0)
    mel.connect_material_property(rg, '', unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(m); eal.save_loaded_asset(m, False)
    # el alambre: acero galvanizado; Brillo (0..1, la linterna) le pone un hilo de luz que se ve a unos metros
    m = nuevo_material('M_AlambreBrillo')
    mel.connect_material_property(color(m, (0.42, 0.42, 0.40), -500, -100), '', unreal.MaterialProperty.MP_BASE_COLOR)
    for prop, val, y in ((unreal.MaterialProperty.MP_METALLIC, 1.0, 0), (unreal.MaterialProperty.MP_ROUGHNESS, 0.28, 80)):
        k = E(m, unreal.MaterialExpressionConstant, -500, y)
        k.set_editor_property('r', val)
        mel.connect_material_property(k, '', prop)
    b = escalar(m, 'Brillo', 0.0, -500, 200)
    c = color(m, (2.2, 2.2, 2.0), -500, 300)
    mu = E(m, unreal.MaterialExpressionMultiply, -250, 250)
    conecta(c, mu, 'A'); conecta(b, mu, 'B')
    mel.connect_material_property(mu, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m); eal.save_loaded_asset(m, False)
    log('M_Ascua, M_Humo y M_AlambreBrillo')


# ---------------------------------------------------------------- 3. el plano

def plano():
    d = director()
    b = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))
    d.set_editor_property('plan_rows', [str(r) for r in b['map']])
    d.set_editor_property('plan_cell', float(b.get('T', 2.0)) * 100.0)
    log('plano: %d filas' % len(b['map']))


# ---------------------------------------------------------------- 4. lo que rompía la imagen

def suciedad_material():
    """Calcomanía de suciedad al pie del muro: oscurece el suelo junto a la pared (V de la calcomanía: 1 en el muro, que queda en su -Y) y
    el pie de la pared (Z del mundo: hasta 45 cm). Sin textura nueva: no gasta memoria."""
    m = nuevo_material('M_SuciedadPie')
    m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    try:
        m.set_editor_property('decal_blend_mode', unreal.DecalBlendMode.DBM_DBUFFER_COLOR_NORMAL_ROUGHNESS)
    except Exception:
        pass
    cu = E(m, unreal.MaterialExpressionCustom, -300, 100)
    cu.set_editor_property('code', '''float v = saturate(UV.y);
float g = pow(v, 1.8);
float zf = saturate(1.0 - max(WP.z - 2.0, 0.0) / 45.0);
float n = 0.75 + 0.25 * sin(WP.x * 0.013 + WP.y * 0.011) * sin(WP.x * 0.031 - WP.y * 0.027);
return saturate(g * zf * n) * 0.72;''')
    cu.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    ins = []
    for n in ('UV', 'WP'):
        ci = unreal.CustomInput(); ci.set_editor_property('input_name', n); ins.append(ci)
    cu.set_editor_property('inputs', ins)
    tc = E(m, unreal.MaterialExpressionTextureCoordinate, -600, 50)
    wp = E(m, unreal.MaterialExpressionWorldPosition, -600, 150)
    conecta(tc, cu, 'UV'); conecta(wp, cu, 'WP')
    mel.connect_material_property(cu, '', unreal.MaterialProperty.MP_OPACITY)
    mel.connect_material_property(color(m, (0.035, 0.03, 0.022), -300, -100), '', unreal.MaterialProperty.MP_BASE_COLOR)
    k = E(m, unreal.MaterialExpressionConstant, -300, 300)
    k.set_editor_property('r', 0.95)
    mel.connect_material_property(k, '', unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(m)
    eal.save_loaded_asset(m, False)
    return m


def suciedad_muros():
    """Tramos rectos de muro ('#', 'W') junto a suelo pisable: una calcomanía por tramo, por el lado del suelo."""
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        if a.get_actor_label().startswith('Suciedad_pie_'):
            a.destroy_actor()
    mat = suciedad_material()
    b = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json'), encoding='utf-8'))
    M = b['map']
    T = float(b.get('T', 2.0)) * 100.0
    filas, cols = len(M), len(M[0])
    muro = lambda r, c: 0 <= r < filas and 0 <= c < cols and M[r][c] in '#W'
    suelo = lambda r, c: 0 <= r < filas and 0 <= c < cols and M[r][c] not in '#W'
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    n = 0
    ANCHO = 70.0   # cm de suelo que se ensucia desde la pared
    # (dr, dc): hacia donde está el suelo. Un tramo: celdas de muro seguidas con suelo al mismo lado
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        hecho = set()
        for r in range(filas):
            for c in range(cols):
                if (r, c) in hecho or not (muro(r, c) and suelo(r + dr, c + dc)):
                    continue
                # el tramo sigue a lo largo de la pared (perpendicular a dr, dc)
                ar, ac = (0, 1) if dr != 0 else (1, 0)
                k = 0
                while muro(r + ar * k, c + ac * k) and suelo(r + ar * k + dr, c + ac * k + dc):
                    hecho.add((r + ar * k, c + ac * k))
                    k += 1
                # la cara del muro hacia el suelo
                cx0 = (c + 0.5) * T + dc * T * 0.5
                cy0 = (r + 0.5) * T + dr * T * 0.5
                largo = k * T
                mx = cx0 + ac * (largo - T) * 0.5 + dc * (ANCHO * 0.5 - 10.0)   # 10 cm dentro del muro: coge su pie
                my = cy0 + ar * (largo - T) * 0.5 + dr * (ANCHO * 0.5 - 10.0)
                dec = eas.spawn_actor_from_class(unreal.DecalActor, V(mx, my, 20.0), unreal.Rotator(0, -90, 0))
                dc_ = dec.get_editor_property('decal')
                dc_.set_editor_property('decal_material', mat)
                # la calcomanía proyecta por su X (aquí, hacia abajo); su Y cruza la franja, del muro al suelo
                yaw = {(-1, 0): 180.0, (1, 0): 0.0, (0, -1): 90.0, (0, 1): -90.0}[(dr, dc)]   # su Y, del muro al suelo
                dec.set_actor_rotation(unreal.Rotator(0.0, -90.0, yaw), False)
                dc_.set_editor_property("decal_size", V(60.0, ANCHO * 0.5 + 10.0, largo * 0.5))
                dec.set_actor_label('Suciedad_pie_%d' % n)
                dec.set_folder_path('Relleno/Suciedad')
                n += 1
    log('suciedad al pie de los muros: %d tramos' % n)


def mat_inst(nombre):
    ruta = '%s/%s' % (DM, nombre)
    return eal.load_asset(ruta) if eal.does_asset_exist(ruta) else None


def ajusta(mi, **params):
    """Cambia parámetros de una instancia de material (los que tenga) y apunta lo que había."""
    if mi is None:
        return
    for k, v in params.items():
        try:
            if isinstance(v, tuple):
                old = mel.get_material_instance_vector_parameter_value(mi, k)
                mel.set_material_instance_vector_parameter_value(mi, k, unreal.LinearColor(v[0], v[1], v[2], 1.0))
            else:
                old = mel.get_material_instance_scalar_parameter_value(mi, k)
                mel.set_material_instance_scalar_parameter_value(mi, k, v)
            log('%s.%s: %s -> %s' % (mi.get_name(), k, old, v))
        except Exception as e:
            log('AVISO: %s sin %s (%r)' % (mi.get_name(), k, e))
    mel.update_material_instance(mi)
    eal.save_loaded_asset(mi, False)


def parametros(mi):
    if mi is None:
        return []
    out = []
    for f in (mel.get_scalar_parameter_names, mel.get_vector_parameter_names):
        try:
            out += [str(x) for x in f(mi)]
        except Exception:
            pass
    return out


RETOQUES = {
    # la madera de las cajas y cajones salía casi negra a la sombra (Tinte 0,085): madera vieja, pero se lee
    'MI_madera': {'Tinte': (0.13, 0.075, 0.04), 'Medio': (0.24, 0.15, 0.085)},
    # las losas de los caminos, casi blancas y limpias con el sol: más oscuras y más sucias
    'MI_camino': {'Tinte': (0.105, 0.102, 0.094), 'Medio': (0.075, 0.076, 0.072), 'Suciedad': 1.35},
}


def retoques():
    for n, ps in RETOQUES.items():
        ajusta(mat_inst(n), **ps)


def reves_carteles():
    """Los carteles de poste son un plano: por detrás se veía la pintura lisa (el amarillo en blanco del portón).
    Detrás de cada uno, una chapa de hierro un poco mayor."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.get_actor_label().startswith('Chapa_'):
            a.destroy_actor()
    cubo = unreal.load_asset('/Engine/BasicShapes/Cube')
    hierro = mat_inst('MI_hierro')
    n = 0
    for a in eas.get_all_level_actors():
        l = a.get_actor_label()
        if not l.startswith('Cartel_') or l.endswith('_poste') or l.endswith('_panel'):
            continue
        poste = any(b.get_actor_label() == l + '_poste' for b in eas.get_all_level_actors())
        if not poste:
            continue
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        if not c or not c.static_mesh or c.static_mesh.get_name() != 'Plane':
            continue
        t = c.get_world_transform()
        up = t.rotation.get_up_vector() if hasattr(t.rotation, 'get_up_vector') else unreal.MathLibrary.get_up_vector(t.rotation.rotator())
        sc = t.scale3d
        loc = t.translation - up * 0.8
        ch = eas.spawn_actor_from_object(cubo, loc, t.rotation.rotator())
        ch.set_actor_scale3d(V(sc.x * 1.04, sc.y * 1.04, 0.012))
        mc = ch.get_component_by_class(unreal.StaticMeshComponent)
        if hierro:
            mc.set_material(0, hierro)
        mc.set_collision_profile_name('NoCollision')
        ch.set_actor_label('Chapa_' + l)
        ch.set_folder_path('Relleno/Carteles')
        n += 1
    log('chapa detrás de %d carteles de poste' % n)


def montar():
    mpc = mpc_cortes()
    tela_con_cortes(mpc)
    materiales_pequenos()
    plano()
    suciedad_muros()
    retoques()
    reves_carteles()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    log('montado y guardado')


if __name__ == '__main__':
    montar()
