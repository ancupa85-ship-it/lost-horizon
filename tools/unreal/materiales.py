"""Materiales realistas para la base de Tarsis en Unreal (texturas PBR de Poly Haven, CC0).

Se ejecuta dentro del editor después de montar_base.py (montar_base lo llama al final si existen las texturas):
1. Importa las texturas de assets/texturas/ (las descarga tools/blender/texturas.py; no van en el repositorio)
   en /Game/Tarsis/Texturas.
2. Crea un material maestro M_LH con proyección alineada al mundo (no depende de las UV de las mallas):
   color = textura x tinte, relieve (normal), rugosidad, metal; tamaño de la textura en cm como parámetro.
3. Crea una instancia MI_<clave> por cada material del visor que tiene textura (muro, pared, suelo, madera...)
   con el tinte, la rugosidad y el metal de escenario/visor.js, y la pone en las mallas en lugar de lh_<clave>.
4. Tanda 22: un segundo maestro, M_LH_Movil, para las piezas que se mueven (el camión de suministros, la hoja del portón)
   y los camiones aparcados: usa las UV de la malla (con el maestro alineado al mundo la textura se quedaba quieta y la
   pieza pasaba por debajo) y añade barro en la parte baja. Instancias MI_<clave>_camion y MI_<clave>_hoja.
"""
import os, json
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TEX = os.path.join(ROOT, 'assets', 'texturas')
DATA = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json')))
DT = '/Game/Tarsis/Texturas'
DM = '/Game/Tarsis/Materiales'
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def uno(a, b):
    """Conecta a la única entrada de b (OneMinus, Saturate, Abs, ComponentMask): según el nodo se llama «Input» o «»."""
    if not mel.connect_material_expressions(a, '', b, 'Input'):
        mel.connect_material_expressions(a, '', b, '')

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))

# clave del visor -> (textura de Poly Haven, metros que ocupa una repetición, como tex(name, rep) en visor.js)
TEXTURAS = {
    'suelo': ('asphalt_02', 3.0), 'muro': ('concrete_wall_008', 3.2), 'hormigon': ('concrete_wall_008', 3.2),
    # pared: en la tanda 18 se probó peeling_painted_wall; sale rojiza y cambia también las fachadas
    'pared': ('painted_plaster_wall', 2.6), 'madera': ('wood_planks_dirt', 1.6), 'hierro': ('rusty_metal_02', 1.4),
    'oliva': ('green_metal_rust', 2.2), 'tejado': ('corrugated_iron_02', 2.0), 'suelo_int': ('concrete_floor_worn_001', 2.0),
    # contenedores (exportar_base.py, lh_contenedor_N): chapa ondulada teñida con los cuatro colores del visor
    'contenedor_0': ('corrugated_iron_02', 1.2), 'contenedor_1': ('corrugated_iron_02', 1.2),
    'contenedor_2': ('corrugated_iron_02', 1.2), 'contenedor_3': ('corrugated_iron_02', 1.2),
    # tanda 18: mantas de lana y colchones de tela basta (mallas de tools/unreal/ambiente.py)
    'manta': ('poly_wool_herringbone', 0.6), 'colchon': ('rough_linen', 0.8),
    # tanda 20: anillo exterior. El camino reutiliza el hormigón gastado de los interiores (no gasta memoria de vídeo);
    # la tierra del anillo es grava suelta
    'camino': ('concrete_floor_worn_001', 4.0), 'tierra': ('gravel_floor_02', 2.5),
}
# tinte, rugosidad y metal del visor (escenario/visor.js, tabla M; color en sRGB)
VALORES = {
    'suelo': (0x777777, 0.75, 0.0), 'muro': (0x8a8a88, 0.82, 0.0), 'hormigon': (0x8a8a88, 0.82, 0.0),
    'pared': (0xa39c8e, 0.85, 0.0), 'madera': (0xb09a80, 0.75, 0.0), 'hierro': (0x999999, 0.6, 0.55),
    'oliva': (0x6f8a4c, 0.5, 0.1), 'tejado': (0x666668, 0.6, 0.4), 'suelo_int': (0x8c8c8c, 0.55, 0.0),
    'manta': (0x6b6e58, 0.95, 0.0), 'colchon': (0xb8ab90, 0.9, 0.0),
    'camino': (0x7d7c78, 0.7, 0.0), 'tierra': (0x6f675c, 0.9, 0.0),
    # colores de KC en visor.js, aclarados: la chapa gris ya oscurece al multiplicar
    'contenedor_0': (0xe0785c, 0.62, 0.15), 'contenedor_1': (0x78aed0, 0.62, 0.15),
    'contenedor_2': (0x94c48a, 0.62, 0.15), 'contenedor_3': (0xe8cf70, 0.62, 0.15),
}

# tanda 23: cuánta suciedad lleva cada instancia (parámetro Suciedad del maestro; las demás se quedan con 0,6). Con más,
# las manchas grandes de ruido oscurecen más el color y, sobre todo, abren más la rugosidad: bajo una farola el brillo de
# la losa deja de ser un óvalo liso y sale a parches, unos mates y otros como recién mojados. En los muros sube además
# el zócalo oscuro del pie. No cuesta nada: el ruido ya se calculaba.
SUCIEDAD = {'camino': 1.25, 'tierra': 1.0, 'muro': 1.0, 'suelo': 0.85}
# ruido del maestro por textura 3D (una lectura por nivel en vez de ocho). Se repite cada 40 m, que en manchas difusas no
# se nota. Para medir lo que ahorra en la GTX 1050 Ti: False lo deja como hasta la tanda 22.
RUIDO_RAPIDO = True

# tanda 24: con lluvia se moja la base entera. El director sube el parámetro «Mojado» de la colección MPC_Tarsis (0-1,
# en unos 25 s; al escampar baja en minuto y medio) y el maestro oscurece el color y baja la rugosidad de lo que está a
# la intemperie: cuánto, por instancia (parámetro Mojable; las que no salen aquí, 0: interiores y fachadas bajo el alero).
# En el suelo el brillo sale a parches (el mismo ruido de la suciedad): zonas encharcadas y zonas solo húmedas.
CON_MOJADO = True
MPC = DM + '/MPC_Tarsis'
MOJABLE = {'suelo': 1.0, 'camino': 1.0, 'tierra': 1.0, 'tejado': 1.0, 'muro': 0.7, 'hormigon': 0.7, 'oliva': 0.6, 'hierro': 0.6,
           'contenedor_0': 1.0, 'contenedor_1': 1.0, 'contenedor_2': 1.0, 'contenedor_3': 1.0}

def coleccion():
    """MPC_Tarsis con el escalar «Mojado» (0 por defecto: en el editor, todo seco). La crea si falta."""
    c = eal.load_asset(MPC) if eal.does_asset_exist(MPC) else tools.create_asset(
        'MPC_Tarsis', DM, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    if c is None:
        return None
    ps = list(c.get_editor_property('scalar_parameters'))
    if not any(str(q.get_editor_property('parameter_name')) == 'Mojado' for q in ps):
        q = unreal.CollectionScalarParameter()        # el constructor le da su identificador
        q.set_editor_property('parameter_name', 'Mojado')
        q.set_editor_property('default_value', 0.0)
        ps.append(q)
        c.set_editor_property('scalar_parameters', ps)
        eal.save_loaded_asset(c)
        log('MPC_Tarsis: parámetro Mojado creado')
    return c

def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

# ------------------------------------------------------------------ 1. texturas
# lado máximo (píxeles) de las texturas que no lucen sus 2K: la grava del anillo se ve de noche y a ras de suelo, y con
# 1K la tarjeta de 4 GB recupera unos 30 MB (tanda 21). El fichero descargado no cambia: lo reduce Unreal al cocinarla.
LADO_MAX = {'gravel_floor_02': 1024}

def limitar(tx, nombre):
    lado = LADO_MAX.get(nombre)
    if tx is not None and lado and tx.get_editor_property('max_texture_size') != lado:
        tx.set_editor_property('max_texture_size', lado)
        eal.save_loaded_asset(tx)
        log('textura', tx.get_name(), 'limitada a', lado, 'px')
    return tx

def textura(nombre, tipo):
    ruta = '%s/T_%s_%s' % (DT, nombre, tipo)
    if eal.does_asset_exist(ruta):
        return limitar(eal.load_asset(ruta), nombre)
    f = os.path.join(TEX, '%s_%s.jpg' % (nombre, tipo))
    if not os.path.exists(f):
        return None
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', f)
    t.set_editor_property('destination_path', DT)
    t.set_editor_property('destination_name', 'T_%s_%s' % (nombre, tipo))
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', False)
    tools.import_asset_tasks([t])
    tx = eal.load_asset(ruta)
    if tx is None:
        return None
    if tipo == 'nor':
        tx.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        tx.set_editor_property('srgb', False)
        tx.set_editor_property('flip_green_channel', True)   # Poly Haven nor_gl (OpenGL) -> Unreal (DirectX)
    elif tipo == 'rough':
        tx.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        tx.set_editor_property('srgb', False)
    eal.save_loaded_asset(tx)
    return limitar(tx, nombre)

# ------------------------------------------------------------------ 2. material maestro
# suciedad en el maestro (manchas de ruido y zócalo); False lo deja como antes (para medir lo que cuesta)
CON_SUCIEDAD = True
WAT = '/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedTexture.WorldAlignedTexture'
WAN = '/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedNormal.WorldAlignedNormal'

def maestro(defecto):
    """defecto: {'diff': textura, 'nor': textura, 'rough': textura} para los valores por defecto de los parámetros.
    Un TextureObjectParameter sin textura, o con una de otro tipo (sRGB / normal / máscara), no compila."""
    ruta = DM + '/M_LH'
    if eal.does_asset_exist(ruta):
        m = eal.load_asset(ruta)
        # se rehace el grafo en el mismo recurso (las instancias siguen apuntando a él).
        # delete_all_material_expressions deja nodos sueltos (máscaras sin entrada, parámetros repetidos) que impiden
        # compilar, así que se borran también uno a uno
        mel.delete_all_material_expressions(m)
        for e in list(mel.get_material_expressions(m)):
            mel.delete_material_expression(m, e)
    else:
        m = tools.create_asset('M_LH', DM, unreal.Material, unreal.MaterialFactoryNew())
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
    # tamaño de la textura (cm) como vector para las funciones alineadas al mundo
    size = E(unreal.MaterialExpressionScalarParameter, -1200, 0)
    size.set_editor_property('parameter_name', 'Tamano'); size.set_editor_property('default_value', 300.0)
    SAMPLER = {'diff': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, 'nor': unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
               'rough': unreal.MaterialSamplerType.SAMPLERTYPE_MASKS}
    def tex_obj(nombre, x, y, tipo):
        p = E(unreal.MaterialExpressionTextureObjectParameter, x, y)
        p.set_editor_property('parameter_name', nombre)
        p.set_editor_property('texture', defecto[tipo])
        p.set_editor_property('sampler_type', SAMPLER[tipo])
        return p
    def wat(obj, x, y, fn=WAT):
        f = E(unreal.MaterialExpressionMaterialFunctionCall, x, y)
        f.set_editor_property('material_function', unreal.load_asset(fn))
        mel.connect_material_expressions(obj, '', f, 'TextureObject')
        mel.connect_material_expressions(size, '', f, 'TextureSize')
        return f
    col = wat(tex_obj('Color', -1000, -300, 'diff'), -700, -300)
    tint = E(unreal.MaterialExpressionVectorParameter, -700, -500)
    tint.set_editor_property('parameter_name', 'Tinte'); tint.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
    mul = E(unreal.MaterialExpressionMultiply, -400, -350)
    mel.connect_material_expressions(col, 'XYZ Texture', mul, 'A')
    mel.connect_material_expressions(tint, '', mul, 'B')
    # suciedad (tanda 18): nada de superficies uniformes. Manchas grandes de ruido en el espacio del mundo (oscurecen
    # el color y cambian la rugosidad) y un zócalo sucio en las paredes (solo en superficies verticales, hasta ~45 cm)
    suc = E(unreal.MaterialExpressionScalarParameter, -1200, -800)
    suc.set_editor_property('parameter_name', 'Suciedad'); suc.set_editor_property('default_value', 0.6)
    ruido = E(unreal.MaterialExpressionNoise, -1000, -800)
    ruido.set_editor_property('scale', 0.004); ruido.set_editor_property('levels', 2)
    # ruido de textura (barato): el de cálculo en cada píxel de toda la base costaba ~8 fps en una GTX 1050 Ti
    fn = unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX
    if RUIDO_RAPIDO:
        fn = getattr(unreal.NoiseFunction, 'NOISEFUNCTION_GRADIENT_TEX3D', fn)
        if fn == unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX:
            log('AVISO: M_LH: este motor no tiene el ruido de textura 3D; se queda el de siempre')
    ruido.set_editor_property('noise_function', fn)
    ruido.set_editor_property('quality', 1)
    ruido.set_editor_property('output_min', 0.0); ruido.set_editor_property('output_max', 1.0)
    wp = E(unreal.MaterialExpressionWorldPosition, -1200, -1000)
    zm = E(unreal.MaterialExpressionComponentMask, -1000, -1000)
    for k, v in (('r', False), ('g', False), ('b', True), ('a', False)):
        zm.set_editor_property(k, v)
    uno(wp, zm)
    zdiv = E(unreal.MaterialExpressionDivide, -850, -1000)
    zdiv.set_editor_property('const_b', 45.0)
    mel.connect_material_expressions(zm, '', zdiv, 'A')
    zsat = E(unreal.MaterialExpressionSaturate, -720, -1000)
    uno(zdiv, zsat)
    zinv = E(unreal.MaterialExpressionOneMinus, -600, -1000)
    uno(zsat, zinv)
    vn = E(unreal.MaterialExpressionVertexNormalWS, -1000, -1150)
    nz = E(unreal.MaterialExpressionComponentMask, -850, -1150)
    for k, v in (('r', False), ('g', False), ('b', True), ('a', False)):
        nz.set_editor_property(k, v)
    uno(vn, nz)
    nza = E(unreal.MaterialExpressionAbs, -720, -1150)
    uno(nz, nza)
    pared = E(unreal.MaterialExpressionOneMinus, -600, -1150)
    uno(nza, pared)
    zocalo = E(unreal.MaterialExpressionMultiply, -480, -1080)
    mel.connect_material_expressions(zinv, '', zocalo, 'A')
    mel.connect_material_expressions(pared, '', zocalo, 'B')
    # oscurecer = 1 - Suciedad * (0,35 x ruido + 0,45 x zócalo)
    rk = E(unreal.MaterialExpressionMultiply, -800, -800)
    rk.set_editor_property('const_b', 0.35)
    mel.connect_material_expressions(ruido, '', rk, 'A')
    zk = E(unreal.MaterialExpressionMultiply, -360, -1080)
    zk.set_editor_property('const_b', 0.45)
    mel.connect_material_expressions(zocalo, '', zk, 'A')
    sm_ = E(unreal.MaterialExpressionAdd, -250, -950)
    mel.connect_material_expressions(rk, '', sm_, 'A')
    mel.connect_material_expressions(zk, '', sm_, 'B')
    sk = E(unreal.MaterialExpressionMultiply, -150, -900)
    mel.connect_material_expressions(sm_, '', sk, 'A')
    mel.connect_material_expressions(suc, '', sk, 'B')
    osc = E(unreal.MaterialExpressionOneMinus, -50, -900)
    uno(sk, osc)
    sucio0 = E(unreal.MaterialExpressionMultiply, -250, -350)
    mel.connect_material_expressions(mul, '', sucio0, 'A')
    mel.connect_material_expressions(osc, '', sucio0, 'B')
    # zócalo pintado (paredes de dentro): hasta ZocaloAltura cm el color se tiñe con ZocaloTinte; 0 = sin zócalo
    zalt = E(unreal.MaterialExpressionScalarParameter, -1200, -1300)
    zalt.set_editor_property('parameter_name', 'ZocaloAltura'); zalt.set_editor_property('default_value', 0.0)
    ztin = E(unreal.MaterialExpressionVectorParameter, -1200, -1450)
    ztin.set_editor_property('parameter_name', 'ZocaloTinte'); ztin.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
    zres = E(unreal.MaterialExpressionSubtract, -1000, -1300)
    mel.connect_material_expressions(zalt, '', zres, 'A')
    mel.connect_material_expressions(zm, '', zres, 'B')
    zesc = E(unreal.MaterialExpressionMultiply, -880, -1300)
    zesc.set_editor_property('const_b', 0.5)   # transición de 2 cm
    mel.connect_material_expressions(zres, '', zesc, 'A')
    zmsk = E(unreal.MaterialExpressionSaturate, -760, -1300)
    uno(zesc, zmsk)
    zpar = E(unreal.MaterialExpressionMultiply, -640, -1300)
    mel.connect_material_expressions(zmsk, '', zpar, 'A')
    mel.connect_material_expressions(pared, '', zpar, 'B')
    ztc = E(unreal.MaterialExpressionMultiply, -500, -1450)
    mel.connect_material_expressions(sucio0, '', ztc, 'A')
    mel.connect_material_expressions(ztin, '', ztc, 'B')
    sucio = E(unreal.MaterialExpressionLinearInterpolate, -150, -350)
    mel.connect_material_expressions(sucio0, '', sucio, 'A')
    mel.connect_material_expressions(ztc, '', sucio, 'B')
    mel.connect_material_expressions(zpar, '', sucio, 'Alpha')
    color_fin = sucio if CON_SUCIEDAD else mul
    # mojado (tanda 24): w = Mojado (colección) x Mojable (instancia) x (0,6 en vertical, 1 en horizontal)
    moj_w = moj_h = None
    mpc = coleccion() if CON_MOJADO else None
    if mpc is not None:
        cp = E(unreal.MaterialExpressionCollectionParameter, -1200, -1700)
        cp.set_editor_property('collection', mpc)           # la colección, antes que el nombre
        cp.set_editor_property('parameter_name', 'Mojado')
        mojable = E(unreal.MaterialExpressionScalarParameter, -1200, -1600)
        mojable.set_editor_property('parameter_name', 'Mojable'); mojable.set_editor_property('default_value', 0.0)
        mm_ = E(unreal.MaterialExpressionMultiply, -1000, -1650)
        mel.connect_material_expressions(cp, '', mm_, 'A')
        mel.connect_material_expressions(mojable, '', mm_, 'B')
        vert = E(unreal.MaterialExpressionLinearInterpolate, -850, -1550)
        vert.set_editor_property('const_a', 0.6); vert.set_editor_property('const_b', 1.0)
        mel.connect_material_expressions(nza, '', vert, 'Alpha')
        moj_w = E(unreal.MaterialExpressionMultiply, -700, -1650)
        mel.connect_material_expressions(mm_, '', moj_w, 'A')
        mel.connect_material_expressions(vert, '', moj_w, 'B')
        # en horizontal, a parches: donde el ruido es alto, encharcado
        par = E(unreal.MaterialExpressionMultiply, -850, -1800)
        par.set_editor_property('const_b', 1.5)
        mel.connect_material_expressions(ruido, '', par, 'A')
        par2 = E(unreal.MaterialExpressionSubtract, -720, -1800)
        par2.set_editor_property('const_b', 0.2)
        mel.connect_material_expressions(par, '', par2, 'A')
        par3 = E(unreal.MaterialExpressionSaturate, -600, -1800)
        uno(par2, par3)
        moj_h = E(unreal.MaterialExpressionMultiply, -470, -1800)       # parche x horizontal
        mel.connect_material_expressions(par3, '', moj_h, 'A')
        mel.connect_material_expressions(nza, '', moj_h, 'B')
        # color: lo mojado es más oscuro (hasta x 0,58)
        osc_m = E(unreal.MaterialExpressionLinearInterpolate, -470, -1650)
        osc_m.set_editor_property('const_a', 1.0); osc_m.set_editor_property('const_b', 0.58)
        mel.connect_material_expressions(moj_w, '', osc_m, 'Alpha')
        cm = E(unreal.MaterialExpressionMultiply, -20, -420)
        mel.connect_material_expressions(color_fin, '', cm, 'A')
        mel.connect_material_expressions(osc_m, '', cm, 'B')
        color_fin = cm
    elif CON_MOJADO:
        log('AVISO: M_LH: no hay MPC_Tarsis; el maestro se queda sin el mojado de la lluvia')
    mel.connect_material_property(color_fin, '', unreal.MaterialProperty.MP_BASE_COLOR)
    # relieve: si una instancia no tiene normal, se queda con la normal plana por defecto del parámetro
    nor = wat(tex_obj('Normal', -1000, 0, 'nor'), -700, 0, WAN)
    mel.connect_material_property(nor, 'XYZ Texture', unreal.MaterialProperty.MP_NORMAL)
    # rugosidad: textura (si hay) x escala
    rt = wat(tex_obj('Rugosidad', -1000, 300, 'rough'), -700, 300)
    rs = E(unreal.MaterialExpressionScalarParameter, -700, 500)
    rs.set_editor_property('parameter_name', 'RugosidadEscala'); rs.set_editor_property('default_value', 1.0)
    rm = E(unreal.MaterialExpressionMultiply, -400, 350)
    mel.connect_material_expressions(rt, 'XYZ Texture', rm, 'A')
    mel.connect_material_expressions(rs, '', rm, 'B')
    mask = E(unreal.MaterialExpressionComponentMask, -250, 350)
    mask.set_editor_property('r', True); mask.set_editor_property('g', False)
    mask.set_editor_property('b', False); mask.set_editor_property('a', False)
    uno(rm, mask)   # con '' a secas no conecta («Missing ComponentMask input»): uno() prueba «Input» primero
    # la rugosidad varía con las mismas manchas: donde hay mugre, más mate; donde no, algo más brillante (humedad)
    rvar = E(unreal.MaterialExpressionSubtract, -400, 700)
    rvar.set_editor_property('const_b', 0.5)
    mel.connect_material_expressions(ruido, '', rvar, 'A')
    rv2 = E(unreal.MaterialExpressionMultiply, -280, 700)
    mel.connect_material_expressions(rvar, '', rv2, 'A')
    mel.connect_material_expressions(suc, '', rv2, 'B')
    rv3 = E(unreal.MaterialExpressionMultiply, -160, 700)
    rv3.set_editor_property('const_b', 0.4)
    mel.connect_material_expressions(rv2, '', rv3, 'A')
    radd = E(unreal.MaterialExpressionAdd, -120, 400)
    mel.connect_material_expressions(mask, '', radd, 'A')
    mel.connect_material_expressions(rv3, '', radd, 'B')
    rsat = E(unreal.MaterialExpressionSaturate, 0, 400)
    uno(radd, rsat)
    rug_fin = rsat if CON_SUCIEDAD else mask
    if moj_w is not None:
        # rugosidad de lo mojado: 0,40 (húmedo) -> 0,10 (encharcado, solo en horizontal); nunca más mate que en seco
        rmoj = E(unreal.MaterialExpressionLinearInterpolate, 0, 600)
        rmoj.set_editor_property('const_a', 0.40); rmoj.set_editor_property('const_b', 0.10)
        mel.connect_material_expressions(moj_h, '', rmoj, 'Alpha')
        rmin = E(unreal.MaterialExpressionMin, 130, 520)
        mel.connect_material_expressions(rug_fin, '', rmin, 'A')
        mel.connect_material_expressions(rmoj, '', rmin, 'B')
        rl_ = E(unreal.MaterialExpressionLinearInterpolate, 260, 420)
        mel.connect_material_expressions(rug_fin, '', rl_, 'A')
        mel.connect_material_expressions(rmin, '', rl_, 'B')
        mel.connect_material_expressions(moj_w, '', rl_, 'Alpha')
        rug_fin = rl_
    mel.connect_material_property(rug_fin, '', unreal.MaterialProperty.MP_ROUGHNESS)
    met = E(unreal.MaterialExpressionScalarParameter, -400, 600)
    met.set_editor_property('parameter_name', 'Metal'); met.set_editor_property('default_value', 0.0)
    mel.connect_material_property(met, '', unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m

# ------------------------------------------------------------------ 2b. maestro de las piezas que se mueven (tanda 22)
# prefijo de la malla -> juego de instancias
PREFIJOS_MOVIL = {'camionmovil': 'camion', 'camiones': 'camion', 'hojaentrada': 'hoja'}
# juego -> clave del material -> (textura, metros por repetición, tinte sRGB, escala de rugosidad, metal, barro 0-1, altura del barro en cm)
MOVIL = {
    'camion': {
        'oliva': ('green_metal_rust', 2.2, 0x6f8a4c, 1.0, 0.1, 0.85, 120.0),       # cabina, laterales y portalón: chapa verde con óxido
        'lona': ('rough_linen', 0.9, 0x6a6844, 1.0, 0.0, 0.0, 110.0),              # el toldo queda por encima de las salpicaduras
        'bajos': ('rusty_metal_02', 1.4, 0x4a4338, 1.1, 0.3, 1.0, 130.0),          # chasis y bajos: óxido oscuro y barro
        'goma': ('concrete_floor_worn_001', 1.0, 0x1c1c1e, 1.3, 0.0, 1.0, 110.0),  # neumáticos: negro con el polvo del camino
        'metal': ('rusty_metal_02', 1.4, 0x8d949a, 0.9, 0.6, 0.8, 120.0),          # parachoques y llantas
        'madera': ('wood_planks_dirt', 1.6, 0xb09a80, 1.0, 0.0, 0.0, 110.0),       # suelo de la caja y cajones
    },
    'hoja': {
        'oliva': ('green_metal_rust', 2.2, 0x6f8a4c, 1.0, 0.1, 0.7, 45.0),
        'hierro': ('rusty_metal_02', 1.4, 0x999999, 1.0, 0.55, 0.7, 45.0),
    },
}

def maestro_movil(defecto):
    """M_LH_Movil: como M_LH pero con las UV de la malla (las mallas de la base llevan UV en metros, por proyección en caja:
    tools/blender/escena_base.py, box_uv), de modo que la textura viaja con la pieza. Barro: una franja desde el suelo hasta
    BarroAltura cm (por altura en el mundo: estas piezas solo se mueven en horizontal), rota por un ruido que sale de las UV
    para que tampoco resbale; tiñe el color, quita el metal y deja la superficie mate."""
    ruta = DM + '/M_LH_Movil'
    if eal.does_asset_exist(ruta):
        m = eal.load_asset(ruta)
        mel.delete_all_material_expressions(m)
        for e in list(mel.get_material_expressions(m)):
            mel.delete_material_expression(m, e)
    else:
        m = tools.create_asset('M_LH_Movil', DM, unreal.Material, unreal.MaterialFactoryNew())
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
    def esc(nombre, valor, x, y):
        p = E(unreal.MaterialExpressionScalarParameter, x, y)
        p.set_editor_property('parameter_name', nombre); p.set_editor_property('default_value', valor)
        return p
    SAMPLER = {'diff': unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, 'nor': unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL,
               'rough': unreal.MaterialSamplerType.SAMPLERTYPE_MASKS}
    uv0 = E(unreal.MaterialExpressionTextureCoordinate, -1500, 0)
    rep = esc('Repite', 0.5, -1500, 150)          # repeticiones por metro (1 / tamaño de la textura en metros)
    uv = E(unreal.MaterialExpressionMultiply, -1300, 50)
    mel.connect_material_expressions(uv0, '', uv, 'A')
    mel.connect_material_expressions(rep, '', uv, 'B')
    def muestra(nombre, y, tipo):
        p = E(unreal.MaterialExpressionTextureSampleParameter2D, -1050, y)
        p.set_editor_property('parameter_name', nombre)
        p.set_editor_property('texture', defecto[tipo])
        p.set_editor_property('sampler_type', SAMPLER[tipo])
        if not mel.connect_material_expressions(uv, '', p, 'UVs'):
            mel.connect_material_expressions(uv, '', p, 'Coordinates')
        return p
    col = muestra('Color', -300, 'diff')
    tint = E(unreal.MaterialExpressionVectorParameter, -1050, -520)
    tint.set_editor_property('parameter_name', 'Tinte'); tint.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
    mul = E(unreal.MaterialExpressionMultiply, -750, -350)
    mel.connect_material_expressions(col, 'RGB', mul, 'A')
    mel.connect_material_expressions(tint, '', mul, 'B')
    # barro: franja = saturar((BarroAltura - z) / BarroAltura)², x (0,2 + 1,3 x ruido) x Barro x 2
    alt = esc('BarroAltura', 110.0, -1500, -900)
    barro = esc('Barro', 0.0, -1500, -760)
    wp = E(unreal.MaterialExpressionWorldPosition, -1500, -1050)
    zm = E(unreal.MaterialExpressionComponentMask, -1320, -1050)
    for k in 'rgba':
        zm.set_editor_property(k, k == 'b')
    uno(wp, zm)
    res = E(unreal.MaterialExpressionSubtract, -1150, -1000)
    mel.connect_material_expressions(alt, '', res, 'A')
    mel.connect_material_expressions(zm, '', res, 'B')
    div = E(unreal.MaterialExpressionDivide, -1000, -1000)
    mel.connect_material_expressions(res, '', div, 'A')
    mel.connect_material_expressions(alt, '', div, 'B')
    franja = E(unreal.MaterialExpressionSaturate, -860, -1000)
    uno(div, franja)
    franja2 = E(unreal.MaterialExpressionMultiply, -720, -1000)
    mel.connect_material_expressions(franja, '', franja2, 'A')
    mel.connect_material_expressions(franja, '', franja2, 'B')
    ruido = E(unreal.MaterialExpressionNoise, -1000, -800)
    ruido.set_editor_property('scale', 3.0); ruido.set_editor_property('levels', 2)      # las UV van en metros: manchas de ~35 cm
    ruido.set_editor_property('noise_function', unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX)
    ruido.set_editor_property('quality', 1)
    ruido.set_editor_property('output_min', 0.0); ruido.set_editor_property('output_max', 1.0)
    cero = E(unreal.MaterialExpressionConstant, -1320, -700)
    cero.set_editor_property('r', 0.0)
    p3 = E(unreal.MaterialExpressionAppendVector, -1150, -780)
    mel.connect_material_expressions(uv0, '', p3, 'A')
    mel.connect_material_expressions(cero, '', p3, 'B')
    # en UE 5.8 la entrada del nodo Noise se llama «World Position» (antes, «Position»)
    if not (mel.connect_material_expressions(p3, '', ruido, 'World Position') or mel.connect_material_expressions(p3, '', ruido, 'Position')):
        log('AVISO: M_LH_Movil: el ruido del barro va por la posición del mundo (resbala un poco al moverse la pieza)')
    rk = E(unreal.MaterialExpressionMultiply, -860, -800)
    rk.set_editor_property('const_b', 1.3)
    mel.connect_material_expressions(ruido, '', rk, 'A')
    rk2 = E(unreal.MaterialExpressionAdd, -720, -800)
    rk2.set_editor_property('const_b', 0.2)
    mel.connect_material_expressions(rk, '', rk2, 'A')
    m1 = E(unreal.MaterialExpressionMultiply, -580, -900)
    mel.connect_material_expressions(franja2, '', m1, 'A')
    mel.connect_material_expressions(rk2, '', m1, 'B')
    m2 = E(unreal.MaterialExpressionMultiply, -440, -900)
    mel.connect_material_expressions(m1, '', m2, 'A')
    mel.connect_material_expressions(barro, '', m2, 'B')
    m3 = E(unreal.MaterialExpressionMultiply, -300, -900)
    m3.set_editor_property('const_b', 2.0)
    mel.connect_material_expressions(m2, '', m3, 'A')
    masc = E(unreal.MaterialExpressionSaturate, -160, -900)
    uno(m3, masc)
    btin = E(unreal.MaterialExpressionVectorParameter, -750, -560)
    btin.set_editor_property('parameter_name', 'BarroTinte'); btin.set_editor_property('default_value', unreal.LinearColor(0.105, 0.085, 0.06, 1))
    cfin = E(unreal.MaterialExpressionLinearInterpolate, -450, -400)
    mel.connect_material_expressions(mul, '', cfin, 'A')
    mel.connect_material_expressions(btin, '', cfin, 'B')
    mel.connect_material_expressions(masc, '', cfin, 'Alpha')
    mel.connect_material_property(cfin, '', unreal.MaterialProperty.MP_BASE_COLOR)
    nor = muestra('Normal', 0, 'nor')
    mel.connect_material_property(nor, 'RGB', unreal.MaterialProperty.MP_NORMAL)
    rt = muestra('Rugosidad', 300, 'rough')
    rs = esc('RugosidadEscala', 1.0, -1050, 520)
    rm = E(unreal.MaterialExpressionMultiply, -750, 350)
    mel.connect_material_expressions(rt, 'R', rm, 'A')
    mel.connect_material_expressions(rs, '', rm, 'B')
    rl = E(unreal.MaterialExpressionLinearInterpolate, -450, 350)
    rl.set_editor_property('const_b', 0.93)
    mel.connect_material_expressions(rm, '', rl, 'A')
    mel.connect_material_expressions(masc, '', rl, 'Alpha')
    rsat = E(unreal.MaterialExpressionSaturate, -300, 350)
    uno(rl, rsat)
    mel.connect_material_property(rsat, '', unreal.MaterialProperty.MP_ROUGHNESS)
    met = esc('Metal', 0.0, -750, 620)
    seco = E(unreal.MaterialExpressionOneMinus, -600, 700)
    uno(masc, seco)
    mm = E(unreal.MaterialExpressionMultiply, -450, 620)
    mel.connect_material_expressions(met, '', mm, 'A')
    mel.connect_material_expressions(seco, '', mm, 'B')
    mel.connect_material_property(mm, '', unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m

def instancias_movil(tex, defecto):
    """{juego: {clave: instancia}} de MOVIL. tex: {textura: {'diff', 'nor', 'rough'}} ya importadas."""
    base = maestro_movil(defecto)
    out = {}
    for juego, claves in MOVIL.items():
        for clave, (nombre, rep, hexc, rough, metal, barro, alto) in claves.items():
            if nombre not in tex:
                tex[nombre] = {t: textura(nombre, t) for t in ('diff', 'nor', 'rough')}
            c, n, r = tex[nombre]['diff'], tex[nombre]['nor'], tex[nombre]['rough']
            if c is None:
                continue
            nom = 'MI_%s_%s' % (clave, juego)
            ruta = DM + '/' + nom
            mi = eal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset(
                nom, DM, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
            mel.set_material_instance_parent(mi, base)
            mel.set_material_instance_texture_parameter_value(mi, 'Color', c)
            if n:
                mel.set_material_instance_texture_parameter_value(mi, 'Normal', n)
            if r:
                mel.set_material_instance_texture_parameter_value(mi, 'Rugosidad', r)
            mel.set_material_instance_scalar_parameter_value(mi, 'RugosidadEscala', rough if r else 0.7)
            mel.set_material_instance_scalar_parameter_value(mi, 'Metal', metal)
            mel.set_material_instance_scalar_parameter_value(mi, 'Repite', 1.0 / rep)
            mel.set_material_instance_scalar_parameter_value(mi, 'Barro', barro)
            mel.set_material_instance_scalar_parameter_value(mi, 'BarroAltura', alto)
            mel.set_material_instance_vector_parameter_value(mi, 'Tinte', unreal.LinearColor(*[lin((hexc >> s) & 255) for s in (16, 8, 0)], 1))
            eal.save_loaded_asset(mi)
            out.setdefault(juego, {})[clave] = mi
    return out

def aplicar_movil(meshes, mov):
    """Cada malla de PREFIJOS_MOVIL lleva un solo material y su clave va en el nombre (camionmovil_oliva): se le pone la
    instancia de su juego. Las claves sin instancia (cristal, faro, piloto, oscuro) se quedan con su color liso."""
    n = 0
    for m in meshes:
        nombre = m.get_name()
        juego = next((j for pre, j in PREFIJOS_MOVIL.items() if nombre.startswith(pre + '_')), None)
        if not juego:
            continue
        clave = nombre.split('_', 1)[1]
        mi = next((v for k, v in mov.get(juego, {}).items() if clave == k or clave.startswith(k + '_') or clave.startswith(k + '.')), None)
        if not mi:
            continue
        mats = m.get_editor_property('static_materials')
        cambia = False
        for idx in range(len(mats)):
            sm = mats[idx]
            if sm.get_editor_property('material_interface') != mi:
                sm.set_editor_property('material_interface', mi); mats[idx] = sm; cambia = True
        if cambia:
            m.set_editor_property('static_materials', mats)
            eal.save_loaded_asset(m)
        n += 1
    log('materiales de piezas móviles en', n, 'mallas')
    return n

# ------------------------------------------------------------------ 3. instancias y asignación
_PARA_MOVIL = []   # (texturas, valores por defecto) que deja instancias() para el maestro de las piezas móviles

def instancias():
    # primero las texturas: el maestro usa unas de ellas como valor por defecto de sus parámetros
    tex = {}
    for clave, (nombre, rep) in TEXTURAS.items():
        if nombre not in tex:
            tex[nombre] = {t: textura(nombre, t) for t in ('diff', 'nor', 'rough')}
    defecto = {}
    for t in ('diff', 'nor', 'rough'):
        defecto[t] = next((v[t] for v in tex.values() if v[t] is not None), None)
    if None in defecto.values():
        return {}
    base = maestro(defecto)
    _PARA_MOVIL[:] = [tex, defecto]
    out = {}
    for clave, (nombre, rep) in TEXTURAS.items():
        c, n, r = tex[nombre]['diff'], tex[nombre]['nor'], tex[nombre]['rough']
        if c is None:
            log('AVISO: falta la textura', nombre, '- se deja el color liso en', clave)
            continue
        ruta = DM + '/MI_' + clave
        mi = eal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset(
            'MI_' + clave, DM, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, base)
        hexc, rough, metal = VALORES[clave]
        tinte = unreal.LinearColor(*[lin((hexc >> s) & 255) for s in (16, 8, 0)], 1)
        if clave.startswith('contenedor'):   # la chapa gris x el color queda casi negra de noche: se permite pasar de 1
            tinte = unreal.LinearColor(tinte.r * 1.8, tinte.g * 1.8, tinte.b * 1.8, 1)
        # igual que en el visor: textura x color (si queda oscuro con la luz de Unreal se sube el Tinte de la instancia)
        mel.set_material_instance_texture_parameter_value(mi, 'Color', c)
        # si falta normal o rugosidad se deja el valor por defecto del maestro (misma clase de textura)
        if n:
            mel.set_material_instance_texture_parameter_value(mi, 'Normal', n)
        if r:
            mel.set_material_instance_texture_parameter_value(mi, 'Rugosidad', r)
        mel.set_material_instance_scalar_parameter_value(mi, 'RugosidadEscala', 1.0 if r else rough)
        mel.set_material_instance_scalar_parameter_value(mi, 'Metal', metal)
        mel.set_material_instance_scalar_parameter_value(mi, 'Tamano', rep * 100.0)
        mel.set_material_instance_vector_parameter_value(mi, 'Tinte', tinte)
        if clave == 'pared':   # zócalo pintado de cuartel: verde grisáceo hasta 1,15 m
            mel.set_material_instance_scalar_parameter_value(mi, 'ZocaloAltura', 115.0)
            mel.set_material_instance_vector_parameter_value(mi, 'ZocaloTinte', unreal.LinearColor(0.42, 0.55, 0.47, 1))
        if clave in SUCIEDAD:
            mel.set_material_instance_scalar_parameter_value(mi, 'Suciedad', SUCIEDAD[clave])
        mel.set_material_instance_scalar_parameter_value(mi, 'Mojable', MOJABLE.get(clave, 0.0) if CON_MOJADO else 0.0)
        if clave == 'suelo_int':   # hormigón mate: el brillo uniforme del fluorescente en el suelo parecía plástico
            mel.set_material_instance_scalar_parameter_value(mi, 'RugosidadEscala', 1.6)
        eal.save_loaded_asset(mi)
        out[clave] = mi
    return out

def aplicar(meshes):
    mis = instancias()
    if not mis:
        log('AVISO: no hay texturas en', TEX, '- ejecuta antes tools/blender/texturas.py')
        return 0
    n = 0
    for m in meshes:
        cambia = False
        mats = m.get_editor_property('static_materials')
        for idx in range(len(mats)):
            sm = mats[idx]   # copia del struct: hay que volver a escribirla en la lista (abajo)
            mi = sm.get_editor_property('material_interface')
            nombre = (mi.get_name() if mi else '') or str(sm.get_editor_property('material_slot_name'))
            # el material importado se llama lh_<clave> (a veces con prefijo MI_ o sufijo de Interchange)
            k = nombre.split('lh_', 1)[1] if 'lh_' in nombre else None
            if k is None and nombre[3:] in mis and nombre.startswith('MI_'):
                k = nombre[3:]   # ya tiene nuestra instancia de una ejecución anterior
            for clave in sorted(mis, key=len, reverse=True):
                if k and (k == clave or k.startswith(clave + '_') or k.startswith(clave + '.')) and not (clave == 'suelo' and k.startswith('suelo_int')):
                    sm.set_editor_property('material_interface', mis[clave]); mats[idx] = sm; cambia = True; n += 1
                    break
        if cambia:
            m.set_editor_property('static_materials', mats)
            eal.save_loaded_asset(m)
    log('materiales realistas en', n, 'huecos de material,', len(mis), 'instancias')
    try:      # después: si algo falla aquí, el camión se queda con los materiales de siempre
        if _PARA_MOVIL:
            aplicar_movil(meshes, instancias_movil(*_PARA_MOVIL))
    except Exception as e:
        log('AVISO: materiales de las piezas móviles no aplicados:', repr(e))
    return n

if __name__ == '__main__':
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    ms = [a.get_asset() for a in ar.get_assets_by_path('/Game/Tarsis/Base', recursive=True)
          if str(a.asset_class_path.asset_name) == 'StaticMesh']
    aplicar(ms)
