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
    'suelo': ('asphalt_02', 4.5), 'muro': ('concrete_wall_008', 3.2), 'hormigon': ('concrete_wall_008', 3.2),
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
# rugosidad y metal del visor (escenario/visor.js, tabla M). El color del visor (sRGB) ya no se usa desde la tanda 25:
# multiplicado por la textura daba albedos imposibles (el asfalto devolvía un 2 % de la luz, el hormigón del camino
# igual, la chapa verde un 1 %), y por eso de noche todo era «charco de luz quemado o negro». Ver ALBEDO.
VALORES = {
    'suelo': (0x777777, 0.75, 0.0), 'muro': (0x8a8a88, 0.82, 0.0), 'hormigon': (0x8a8a88, 0.82, 0.0),
    'pared': (0xa39c8e, 0.85, 0.0), 'madera': (0xb09a80, 0.75, 0.0), 'hierro': (0x999999, 0.6, 0.55),
    'oliva': (0x6f8a4c, 0.5, 0.1), 'tejado': (0x666668, 0.6, 0.4), 'suelo_int': (0x8c8c8c, 0.55, 0.0),
    'manta': (0x6b6e58, 0.95, 0.0), 'colchon': (0xb8ab90, 0.9, 0.0),
    'camino': (0x7d7c78, 0.7, 0.0), 'tierra': (0x6f675c, 0.9, 0.0),
    'contenedor_0': (0xe0785c, 0.62, 0.15), 'contenedor_1': (0x78aed0, 0.62, 0.15),
    'contenedor_2': (0x94c48a, 0.62, 0.15), 'contenedor_3': (0xe8cf70, 0.62, 0.15),
}

# tanda 25. Color medio (lineal) de cada textura de Poly Haven, medido sobre el JPG de 1K. El maestro divide la textura
# por él: queda el dibujo alrededor de 1 y el color lo pone ALBEDO. Al lado, lo que se desvía (cuánto dibujo trae): las
# de 0,09 son prácticamente un color liso y por eso llevan Contraste.
MEDIO = {
    'asphalt_02': (0.112, 0.110, 0.098),               # 0,60
    'concrete_floor_worn_001': (0.093, 0.094, 0.089),  # 0,09
    'concrete_wall_008': (0.267, 0.238, 0.162),        # 0,09
    'corrugated_iron_02': (0.100, 0.098, 0.083),       # 0,15
    'gravel_floor_02': (0.424, 0.402, 0.347),          # 0,40
    'green_metal_rust': (0.050, 0.074, 0.034),         # 0,16
    'painted_plaster_wall': (0.407, 0.366, 0.351),     # 0,09
    'poly_wool_herringbone': (0.194, 0.182, 0.167),    # 0,22
    'rough_linen': (0.287, 0.410, 0.616),              # 0,14
    'rusty_metal_02': (0.413, 0.289, 0.137),           # 0,52
    'wood_planks_dirt': (0.183, 0.109, 0.062),         # 0,40
}
# albedo (color lineal, lo que de verdad devuelve la superficie). Antes de la tanda 25 (textura x color del visor): suelo
# y camino 2 %, muro 6 %, tejado 1,3 %, chapa verde 1 %. Los contenedores, en colores de contenedor viejo (óxido rojo,
# azul, verde, ocre), no de juguete.
# Ajuste 25c, con las primeras capturas hechas de verdad con M_LH: la base quedaba demasiado oscura fuera de las farolas
# (muro a la luna 16 de 255 en pantalla, suelo 9) y por dentro. Los primeros valores (asfalto 5 %, losa 9 %, muro 10 %,
# enlucido 13 %) eran el extremo oscuro de cada material; ahora van a media tabla: asfalto viejo 7 %, losa 13 %,
# hormigón de muro 15 % (las barreras de hormigón del camino, que traen su propia textura, andan por el 30 % y
# cantaban), enlucido pintado y sucio 21 %. La otra mitad del ajuste es la luna y la luz ambiente (montar_base.py, EXPO).
ALBEDO = {
    'suelo': (0.070, 0.069, 0.064), 'camino': (0.135, 0.131, 0.121), 'tierra': (0.100, 0.086, 0.064),
    'muro': (0.150, 0.140, 0.117), 'hormigon': (0.150, 0.140, 0.117), 'pared': (0.240, 0.200, 0.160),
    'madera': (0.085, 0.045, 0.022), 'hierro': (0.120, 0.090, 0.050), 'oliva': (0.040, 0.048, 0.028),
    'tejado': (0.040, 0.040, 0.043), 'suelo_int': (0.070, 0.070, 0.065),
    'manta': (0.029, 0.028, 0.016), 'colchon': (0.150, 0.140, 0.115),
    'contenedor_0': (0.125, 0.035, 0.025), 'contenedor_1': (0.028, 0.056, 0.094),
    'contenedor_2': (0.035, 0.069, 0.040), 'contenedor_3': (0.175, 0.125, 0.031),
}
# cuánto se estira el dibujo de la textura alrededor de su media, y la fuerza de su relieve (las demás, 1)
CONTRASTE = {'camino': 2.6, 'muro': 2.6, 'hormigon': 2.6, 'pared': 2.2, 'suelo_int': 2.2, 'tejado': 1.6, 'oliva': 1.5,
             'contenedor_0': 1.3, 'contenedor_1': 1.3, 'contenedor_2': 1.3, 'contenedor_3': 1.3}
RELIEVE = {'suelo': 1.6, 'camino': 2.2, 'muro': 2.0, 'hormigon': 2.0, 'pared': 1.6, 'tierra': 1.4, 'suelo_int': 1.5}
# nubes de tono de 10-15 m (±): que un patio no sea un plano de un solo gris
MACRO = {'suelo': 0.22, 'camino': 0.16, 'tierra': 0.25, 'muro': 0.16, 'hormigon': 0.16, 'pared': 0.14, 'tejado': 0.20,
         'suelo_int': 0.10, 'contenedor_0': 0.12, 'contenedor_1': 0.12, 'contenedor_2': 0.12, 'contenedor_3': 0.12}
# losas y paneles: (Losa cm, LosaTono, Panel cm, PanelTono, Junta, LosaFaseX cm). El asfalto de los patios, en paños de
# 8 m con la costura apenas marcada; el camino, losas de 6 m casadas con las juntas de alquitrán que ya tiene (x = 100 +
# 600 k: por eso la fase, y sin junta pintada); el muro, paneles prefabricados de 3 m con su junta
LOSAS = {'suelo': (800.0, 0.10, 300.0, 0.0, 0.30, 0.0), 'camino': (600.0, 0.12, 300.0, 0.0, 0.0, 100.0),
         'muro': (400.0, 0.0, 300.0, 0.09, 0.30, 0.0), 'hormigon': (400.0, 0.0, 250.0, 0.07, 0.30, 0.0),
         'suelo_int': (400.0, 0.05, 300.0, 0.0, 0.20, 0.0)}
# la textura, corrida al azar en cada losa o panel (solo donde hay junta que tape el corte)
DESFASE = ('suelo', 'camino', 'muro', 'hormigon')
# regueros verticales del maestro (0 = ninguno). En los contenedores y la chapa son chorretones de óxido
CHORREO = {'muro': 0.6, 'hormigon': 0.5, 'pared': 0.3, 'hierro': 0.2, 'oliva': 0.25,
           'contenedor_0': 0.35, 'contenedor_1': 0.35, 'contenedor_2': 0.35, 'contenedor_3': 0.35}

# tanda 23: cuánta suciedad lleva cada instancia (parámetro Suciedad del maestro; las demás se quedan con 0,6). Con más,
# las manchas grandes de ruido oscurecen más el color y, sobre todo, abren más la rugosidad: bajo una farola el brillo de
# la losa deja de ser un óvalo liso y sale a parches, unos mates y otros como recién mojados. En los muros sube además
# el zócalo oscuro del pie. No cuesta nada: el ruido ya se calculaba.
SUCIEDAD = {'camino': 1.0, 'tierra': 1.0, 'muro': 1.0, 'suelo': 1.0, 'hormigon': 0.9, 'pared': 0.7}
# ruido del maestro por textura 3D (una lectura por nivel en vez de ocho). Se repite cada 40 m, que en manchas difusas no
# se nota. Para medir lo que ahorra en la GTX 1050 Ti: False lo deja como hasta la tanda 22.
RUIDO_RAPIDO = True

# tanda 24: con lluvia se moja la base entera. El director sube el parámetro «Mojado» de la colección MPC_Tarsis (0-1,
# en unos 25 s; al escampar baja en minuto y medio) y el maestro oscurece el color y baja la rugosidad de lo que está a
# la intemperie: cuánto, por instancia (parámetro Mojable; las que no salen aquí, 0: interiores y fachadas bajo el alero).
# En el suelo el brillo sale a parches (el mismo ruido de la suciedad): zonas encharcadas y zonas solo húmedas.
CON_MOJADO = True
MPC = DM + '/MPC_Tarsis'
# tanda 25: «Nublado» (0 raso, 1 cubierto: con lluvia o niebla) lo leen el cielo y los halos de las farolas (cielo.py)
ESCALARES_MPC = ('Mojado', 'Nublado')
MOJABLE = {'suelo': 1.0, 'camino': 1.0, 'tierra': 1.0, 'tejado': 1.0, 'muro': 0.7, 'hormigon': 0.7, 'oliva': 0.6, 'hierro': 0.6,
           'contenedor_0': 1.0, 'contenedor_1': 1.0, 'contenedor_2': 1.0, 'contenedor_3': 1.0}

def coleccion():
    """MPC_Tarsis con los escalares «Mojado» y «Nublado» (0 por defecto: en el editor, seco y raso). La crea si falta."""
    c = eal.load_asset(MPC) if eal.does_asset_exist(MPC) else tools.create_asset(
        'MPC_Tarsis', DM, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    if c is None:
        return None
    ps = list(c.get_editor_property('scalar_parameters'))
    nuevos = []
    for nombre in ESCALARES_MPC:
        if not any(str(q.get_editor_property('parameter_name')) == nombre for q in ps):
            q = unreal.CollectionScalarParameter()        # el constructor le da su identificador
            q.set_editor_property('parameter_name', nombre)
            q.set_editor_property('default_value', 0.0)
            ps.append(q)
            nuevos.append(nombre)
    if nuevos:
        c.set_editor_property('scalar_parameters', ps)
        eal.save_loaded_asset(c, False)
        log('MPC_Tarsis: parámetros creados:', ', '.join(nuevos))
    return c

def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

# ------------------------------------------------------------------ 1. texturas
# lado máximo (píxeles) de las texturas que no lucen sus 2K: la grava del anillo se ve de noche y a ras de suelo, y con
# 1K la tarjeta de 4 GB recupera unos 30 MB (tanda 21). El fichero descargado no cambia: lo reduce Unreal al cocinarla.
LADO_MAX = {'gravel_floor_02': 1024}
# ajuste 25d: escala de rugosidad por clave (la textura x esto). La grava de Poly Haven trae una rugosidad media de 0,47
# (medida en el JPG de 1K): con la luna rasante cada piedra devolvía un punto blanco y el anillo parecía nevado (mediana
# 67/255 en la captura alto_losa, con el suelo al lado en 20). La grava suelta seca es mate: x 1,8 la deja en 0,85.
# El hormigón del interior ya iba a 1,6 desde la tanda 24 (el fluorescente le daba brillo de plástico)
# Ajuste 25e: x 1,3 (0,62). A x 1,8 dejaba de centellear pero parecía tierra lisa o barro; Andres veía más real la
# grava con brillo de piedra suelta. Punto medio: algo de centelleo sin que se vuelva nieve
RUGOSIDAD = {'tierra': 1.3, 'suelo_int': 1.6}

def limitar(tx, nombre):
    lado = LADO_MAX.get(nombre)
    if tx is not None and lado and tx.get_editor_property('max_texture_size') != lado:
        tx.set_editor_property('max_texture_size', lado)
        eal.save_loaded_asset(tx, False)
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
    eal.save_loaded_asset(tx, False)
    return limitar(tx, nombre)

# ------------------------------------------------------------------ 2. material maestro
# suciedad en el maestro (manchas de ruido y zócalo); False lo deja como antes (para medir lo que cuesta)
CON_SUCIEDAD = True
WAT = '/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedTexture.WorldAlignedTexture'
WAN = '/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedNormal.WorldAlignedNormal'
# versión del grafo de M_LH: si no cambia, montar la base no lo rehace (ni recompila sus sombreadores)
VER_LH = 'lh v25c'


def _ambiente():
    import sys, importlib
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import ambiente
    importlib.reload(ambiente)
    return ambiente


def maestro(defecto):
    """defecto: {'diff': textura, 'nor': textura, 'rough': textura} para los valores por defecto de los parámetros.
    Un TextureObjectParameter sin textura, o con una de otro tipo (sRGB / normal / máscara), no compila.

    Tanda 25: «materia en lo grande». Medidas las texturas (tools/unreal/materiales.py, MEDIO), casi todas son un color
    liso con grano fino (desviación del 9 %): a cinco metros, de noche y a media resolución no queda nada. El maestro
    pone ahora lo que falta a escala media y grande, todo por la posición en el mundo (no gasta memoria de vídeo):
      - el color es Tinte (el albedo de verdad) x la textura dividida por su color medio, con Contraste alrededor de 1;
      - Macro: nubes de tono de 10-15 m; Suciedad: manchas de 2-3 m con contraste y un zócalo sucio de altura irregular;
      - losas (suelo) y paneles (muros): cada pieza con su tono (Losa/Panel en cm, LosaTono/PanelTono) y la junta oscura
        entre ellas (Junta);
      - Chorreo: regueros verticales en las caras verticales, más oscuros (y brillantes) cuando llueve;
      - Relieve: fuerza del relieve de la textura;
      - mojado: más oscuro, satinado, y en horizontal charcos a parches con el relieve plano (espejo: ahí se alarga el
        reflejo de las farolas)."""
    amb = _ambiente()
    X = unreal
    ver = VER_LH + ('' if CON_SUCIEDAD else ' limpio') + ('' if CON_MOJADO else ' seco') + ('' if RUIDO_RAPIDO else ' lento')
    g = amb.Grafo(DM + '/M_LH', 'M_LH', ver)
    if g.hecho:
        return g.m
    M, A, S, D = X.MaterialExpressionMultiply, X.MaterialExpressionAdd, X.MaterialExpressionSubtract, X.MaterialExpressionDivide
    AP, MIN = X.MaterialExpressionAppendVector, X.MaterialExpressionMin
    pos = [-2600, -1800]
    def xy():                       # los nodos, en filas: solo para que el grafo se pueda leer en el editor
        pos[0] += 170
        if pos[0] > -200:
            pos[0] = -2600; pos[1] += 150
        return pos[0], pos[1]
    def E(cls, **p):
        return g.E(cls, *xy(), **p)
    def esc(nombre, valor):
        return g.esc(nombre, valor, *xy())
    def vec(nombre, r, gg, b):
        return E(X.MaterialExpressionVectorParameter, parameter_name=nombre, default_value=X.LinearColor(r, gg, b, 1))
    def op(cls, a, b):
        return g.op(cls, a, b, *xy())
    def f1(cls, ent, sal='', **p):    # nodo de una entrada («ent», no «a»: ComponentMask lleva la propiedad a=False)
        n = E(cls, **p)
        g.une(ent, n, ('Input', '', 'VectorInput'), sal)
        return n
    def sat(a):
        return f1(X.MaterialExpressionSaturate, a)
    def inv(a):
        return f1(X.MaterialExpressionOneMinus, a)
    def lerp(a, b, alfa):
        return g.lerp(a, b, alfa, *xy())
    def canal(src, k):
        return g.canal(src, k, *xy())
    def contraste(a, k):            # saturar((a - 0,5) x k + 0,5)
        return sat(op(A, op(M, op(S, a, 0.5), k), 0.5))
    def ruido(escala, niveles, posicion=None):
        fn = X.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX
        if RUIDO_RAPIDO:
            fn = getattr(X.NoiseFunction, 'NOISEFUNCTION_GRADIENT_TEX3D', fn)
        n = E(X.MaterialExpressionNoise, scale=escala, levels=niveles, noise_function=fn, quality=1, output_min=0.0, output_max=1.0)
        if posicion is not None:
            g.une(posicion, n, ('World Position', 'Position'))
        return n
    SAMPLER = {'diff': X.MaterialSamplerType.SAMPLERTYPE_COLOR, 'nor': X.MaterialSamplerType.SAMPLERTYPE_NORMAL,
               'rough': X.MaterialSamplerType.SAMPLERTYPE_MASKS}
    size = esc('Tamano', 300.0)
    donde = [None]                  # posición con la que se proyectan las texturas (corrida al azar en cada losa)
    def wat(nombre, tipo, fn=WAT):
        o = E(X.MaterialExpressionTextureObjectParameter, parameter_name=nombre, texture=defecto[tipo], sampler_type=SAMPLER[tipo])
        f = E(X.MaterialExpressionMaterialFunctionCall, material_function=X.load_asset(fn))
        g.une(o, f, 'TextureObject'); g.une(size, f, 'TextureSize')
        if donde[0] is not None:
            g.une(donde[0], f, ('WorldPosition', 'World Position'))
        return f1(X.MaterialExpressionComponentMask, f, 'XYZ Texture', r=True, g=True, b=True, a=False)

    # ---- posición y orientación
    wp = E(X.MaterialExpressionWorldPosition)
    mx, my, mz = canal(wp, 'r'), canal(wp, 'g'), canal(wp, 'b')
    nza = f1(X.MaterialExpressionAbs, canal(E(X.MaterialExpressionVertexNormalWS), 'b'))
    pared = inv(nza)                                           # 1 en vertical
    hor = sat(op(S, op(M, nza, 4.0), 1.5))                     # 1 en horizontal (suelos, tejados)
    suc = esc('Suciedad', 0.6)
    rui = ruido(0.004, 2)                                      # manchas de 2-3 m
    ruic = contraste(rui, 1.8)
    mac = contraste(ruido(0.0009, 2), 2.2)                     # nubes de tono de 10-15 m
    # losas y paneles: en horizontal, casillas de Losa cm (x - LosaFaseX, y); en vertical, tramos de Panel cm a lo largo
    # del muro (x + y vale para un muro que mire a cualquier lado). Cada pieza saca un número al azar (0-1)
    u = op(A, mx, my)
    tam = lerp(esc('Panel', 300.0), esc('Losa', 600.0), hor)
    cx = op(D, lerp(u, op(S, mx, esc('LosaFaseX', 0.0)), hor), tam)
    cy = lerp(0.5, op(D, my, tam), hor)
    c2 = op(AP, cx, cy)
    celda = f1(X.MaterialExpressionFloor, c2)
    punto = E(X.MaterialExpressionDotProduct)
    g.une(celda, punto, 'A'); g.une(E(X.MaterialExpressionConstant2Vector, r=0.129898, g=0.78233), punto, 'B')
    azar = f1(X.MaterialExpressionFrac, op(M, f1(X.MaterialExpressionSine, punto), 43758.5453))
    # la textura se repite cada Tamano y sus rasgos gordos (la grieta del asfalto) se veían en fila: en cada losa se
    # proyecta corrida una distancia al azar (Desfase 1; 0 = como siempre). El corte cae en la junta
    az2 = f1(X.MaterialExpressionFrac, op(M, azar, 7.31))
    corr = op(M, op(AP, op(AP, azar, az2), E(X.MaterialExpressionConstant, r=0.0)), op(M, size, esc('Desfase', 0.0)))
    donde[0] = op(A, wp, corr)

    # ---- color: Tinte x (textura / su color medio), con contraste alrededor de 1
    col = wat('Color', 'diff')
    rel = op(D, col, vec('Medio', 1, 1, 1))
    relc = E(X.MaterialExpressionMax, const_b=0.04)
    g.une(op(A, op(M, op(S, rel, 1.0), esc('Contraste', 1.0)), 1.0), relc, 'A')
    color = op(M, relc, vec('Tinte', 1, 1, 1))
    if CON_SUCIEDAD:
        macro = esc('Macro', 0.1)
        color = op(M, color, lerp(inv(macro), op(A, macro, 1.0), mac))
        # cada losa o panel, con su tono, y la junta oscura entre ellos
        tono = lerp(esc('PanelTono', 0.0), esc('LosaTono', 0.0), hor)
        color = op(M, color, op(A, op(M, op(S, azar, 0.5), op(M, tono, 2.0)), 1.0))
        fr = f1(X.MaterialExpressionFrac, c2)
        borde = E(MIN); g.une(fr, borde, 'A'); g.une(inv(fr), borde, 'B')
        bmin = E(MIN); g.une(canal(borde, 'r'), bmin, 'A'); g.une(canal(borde, 'g'), bmin, 'B')
        junta0 = inv(sat(op(D, op(M, bmin, tam), 3.5)))                                               # 3,5 cm a cada lado
        junta = op(M, op(M, junta0, junta0), esc('Junta', 0.0))
        color = op(M, color, inv(op(M, junta, 0.75)))
        # zócalo sucio: sube más o menos según la mancha (de 20 a 90 cm), solo en vertical
        zoc = op(M, inv(sat(op(D, mz, op(A, op(M, rui, 70.0), 20.0)))), pared)
        color = op(M, color, inv(op(M, op(A, op(M, op(S, ruic, 0.35), 0.36), op(M, zoc, 0.5)), suc)))
        # regueros: ruido estirado en vertical (hilos de 8-15 cm que duran metros); cada panel, corrido al azar para
        # que el dibujo (que se repite cada 3,2 m) no se vea repetido
        ps = op(AP, op(AP, op(A, u, op(M, canal(celda, 'r'), 137.0)), E(X.MaterialExpressionConstant, r=0.0)), op(M, mz, 0.035))
        hilo = sat(op(M, op(S, ruido(0.05, 2, ps), 0.5), 4.5))
        chorro = op(M, op(M, hilo, lerp(0.35, 1.0, ruic)), pared)
        chorreo = op(M, chorro, esc('Chorreo', 0.0))
    else:
        junta = chorro = chorreo = None
    # ---- mojado (tanda 24): w = Mojado (colección) x Mojable (instancia) x (0,6 en vertical, 1 en horizontal)
    w = moj_h = None
    mpc = coleccion() if CON_MOJADO else None
    if mpc is not None:
        cp = E(X.MaterialExpressionCollectionParameter, collection=mpc)           # la colección, antes que el nombre
        cp.set_editor_property('parameter_name', 'Mojado')
        w = op(M, op(M, cp, esc('Mojable', 0.0)), lerp(0.6, 1.0, nza))
        # charcos: a parches y solo en horizontal; por zonas (la nube grande) hay más o menos
        moj_h = op(M, sat(op(M, op(S, op(A, rui, op(M, op(S, mac, 0.5), 0.25)), 0.5), 3.5)), hor)
    elif CON_MOJADO:
        log('AVISO: M_LH: no hay MPC_Tarsis; el maestro se queda sin el mojado de la lluvia')
    if chorreo is not None:
        # el reguero oscurece el 45 %; mojado, el 80 %
        color = op(M, color, inv(op(M, chorreo, lerp(0.45, 0.8, w) if w is not None else 0.45)))
    # zócalo pintado (paredes de dentro): hasta ZocaloAltura cm el color se tiñe con ZocaloTinte; 0 = sin zócalo
    zmsk = op(M, sat(op(M, op(S, esc('ZocaloAltura', 0.0), mz), 0.5)), pared)       # transición de 2 cm
    color = lerp(color, op(M, color, vec('ZocaloTinte', 1, 1, 1)), zmsk)
    if w is not None:
        color = op(M, color, lerp(1.0, esc('MojadoOscuro', 0.5), w))                # lo mojado es más oscuro
    g.sale(color, X.MaterialProperty.MP_BASE_COLOR)

    # ---- relieve: el de la textura x Relieve; en los charcos, plano
    nor = wat('Normal', 'nor', WAN)
    rl = esc('Relieve', 1.0)
    rv = op(AP, op(AP, rl, rl), E(X.MaterialExpressionConstant, r=1.0))
    nfin = f1(X.MaterialExpressionNormalize, op(M, nor, rv))
    if moj_h is not None:
        nfin = lerp(nfin, E(X.MaterialExpressionConstant3Vector, constant=X.LinearColor(0, 0, 1, 0)), op(M, op(M, moj_h, w), 0.9))
    g.sale(nfin, X.MaterialProperty.MP_NORMAL)

    # ---- rugosidad: textura x escala, movida por las manchas (donde hay mugre, más mate)
    rug = op(M, canal(wat('Rugosidad', 'rough'), 'r'), esc('RugosidadEscala', 1.0))
    if CON_SUCIEDAD:
        rug = sat(op(A, rug, op(M, op(M, op(S, ruic, 0.5), suc), 0.35)))
    if w is not None:
        # mojado: satinado (0,42); los regueros, más (0,2); los charcos, espejo (0,06). Nunca más mate que en seco
        seco = rug
        rm = lerp(0.42, 0.2, chorro) if chorro is not None else E(X.MaterialExpressionConstant, r=0.42)
        rmin = E(MIN); g.une(seco, rmin, 'A'); g.une(lerp(rm, 0.06, moj_h), rmin, 'B')
        rug = lerp(seco, rmin, w)
    g.sale(rug, X.MaterialProperty.MP_ROUGHNESS)
    g.sale(esc('Metal', 0.0), X.MaterialProperty.MP_METALLIC)
    return g.fin()

# ------------------------------------------------------------------ 2b. maestro de las piezas que se mueven (tanda 22)
# prefijo de la malla -> juego de instancias
PREFIJOS_MOVIL = {'camionmovil': 'camion', 'camiones': 'camion', 'hojaentrada': 'hoja'}
# juego -> clave del material -> (textura, metros por repetición, albedo lineal, escala de rugosidad, metal, barro 0-1, altura del barro en cm)
# tanda 25: el albedo va directo (antes, textura verde x verde del visor: de noche bajo una farola el camión salía verde
# lima). Verde oliva militar apagado y con polvo; la lona, caqui; las llantas dejan de ser lo más claro del camión.
OLIVA_MILITAR = (0.045, 0.052, 0.030)
MOVIL = {
    'camion': {
        'oliva': ('green_metal_rust', 2.2, OLIVA_MILITAR, 1.0, 0.1, 0.85, 120.0),            # cabina, laterales y portalón: chapa verde con óxido
        'lona': ('rough_linen', 0.9, (0.060, 0.058, 0.038), 1.0, 0.0, 0.0, 110.0),           # el toldo queda por encima de las salpicaduras
        'bajos': ('rusty_metal_02', 1.4, (0.028, 0.018, 0.009), 1.1, 0.3, 1.0, 130.0),       # chasis y bajos: óxido oscuro y barro
        'goma': ('concrete_floor_worn_001', 1.0, (0.010, 0.010, 0.011), 1.3, 0.0, 1.0, 110.0),  # neumáticos: negro con el polvo del camino
        'metal': ('rusty_metal_02', 1.4, (0.055, 0.047, 0.032), 0.9, 0.6, 0.8, 120.0),       # parachoques y llantas: acero pintado y sucio
        'madera': ('wood_planks_dirt', 1.6, (0.085, 0.045, 0.022), 1.0, 0.0, 0.0, 110.0),    # suelo de la caja y cajones
    },
    'hoja': {
        'oliva': ('green_metal_rust', 2.2, OLIVA_MILITAR, 1.0, 0.1, 0.7, 45.0),
        'hierro': ('rusty_metal_02', 1.4, (0.120, 0.090, 0.050), 1.0, 0.55, 0.7, 45.0),
    },
}
# versión del grafo de M_LH_Movil (como VER_LH)
VER_MOVIL = 'movil v25'

def maestro_movil(defecto):
    """M_LH_Movil: como M_LH pero con las UV de la malla (las mallas de la base llevan UV en metros, por proyección en caja:
    tools/blender/escena_base.py, box_uv), de modo que la textura viaja con la pieza. Barro: una franja desde el suelo hasta
    BarroAltura cm (por altura en el mundo: estas piezas solo se mueven en horizontal), rota por un ruido que sale de las UV
    para que tampoco resbale; tiñe el color, quita el metal y deja la superficie mate."""
    ruta = DM + '/M_LH_Movil'
    if eal.does_asset_exist(ruta):
        m = eal.load_asset(ruta)
        if any(e.get_editor_property('desc') == VER_MOVIL for e in mel.get_material_expressions(m)):
            return m             # ya está en esta versión: no se rehace ni se recompila
        mel.delete_all_material_expressions(m)
        for e in list(mel.get_material_expressions(m)):
            mel.delete_material_expression(m, e)
    else:
        m = tools.create_asset('M_LH_Movil', DM, unreal.Material, unreal.MaterialFactoryNew())
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
    marca = E(unreal.MaterialExpressionConstant, -1800, -600)
    marca.set_editor_property('desc', VER_MOVIL)
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
    # tanda 25: la textura, dividida por su color medio (Medio); el color lo pone Tinte, que es el albedo
    medio = E(unreal.MaterialExpressionVectorParameter, -1050, -700)
    medio.set_editor_property('parameter_name', 'Medio'); medio.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
    rel = E(unreal.MaterialExpressionDivide, -900, -350)
    mel.connect_material_expressions(col, 'RGB', rel, 'A')
    mel.connect_material_expressions(medio, '', rel, 'B')
    mul = E(unreal.MaterialExpressionMultiply, -750, -350)
    mel.connect_material_expressions(rel, '', mul, 'A')
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
    eal.save_loaded_asset(m, False)
    return m

def instancias_movil(tex, defecto):
    """{juego: {clave: instancia}} de MOVIL. tex: {textura: {'diff', 'nor', 'rough'}} ya importadas."""
    base = maestro_movil(defecto)
    out = {}
    for juego, claves in MOVIL.items():
        for clave, (nombre, rep, albedo, rough, metal, barro, alto) in claves.items():
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
            mel.set_material_instance_vector_parameter_value(mi, 'Tinte', unreal.LinearColor(*albedo, 1))
            mel.set_material_instance_vector_parameter_value(mi, 'Medio', unreal.LinearColor(*MEDIO.get(nombre, (1.0, 1.0, 1.0)), 1))
            eal.save_loaded_asset(mi, False)
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
            m.modify()       # sin esto el paquete no se da por cambiado...
            m.set_editor_property('static_materials', mats)
            eal.save_loaded_asset(m, False)      # ...y con «solo si ha cambiado» (lo de serie) no se guardaba: al reabrir, lh_* otra vez
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
        # tanda 25: el Tinte es el albedo y la textura va dividida por su color medio (Medio)
        tinte = unreal.LinearColor(*ALBEDO[clave], 1) if clave in ALBEDO else unreal.LinearColor(*[lin((hexc >> s) & 255) for s in (16, 8, 0)], 1)
        medio = MEDIO.get(nombre, (1.0, 1.0, 1.0)) if clave in ALBEDO else (1.0, 1.0, 1.0)
        mel.set_material_instance_vector_parameter_value(mi, 'Medio', unreal.LinearColor(*medio, 1))
        mel.set_material_instance_scalar_parameter_value(mi, 'Contraste', CONTRASTE.get(clave, 1.0))
        mel.set_material_instance_scalar_parameter_value(mi, 'Relieve', RELIEVE.get(clave, 1.0))
        mel.set_material_instance_scalar_parameter_value(mi, 'Macro', MACRO.get(clave, 0.1))
        losa, ltono, panel, ptono, junta, fase = LOSAS.get(clave, (600.0, 0.0, 300.0, 0.0, 0.0, 0.0))
        for k, v in (('Losa', losa), ('LosaTono', ltono), ('Panel', panel), ('PanelTono', ptono), ('Junta', junta), ('LosaFaseX', fase),
                     ('Chorreo', CHORREO.get(clave, 0.0)), ('Desfase', 1.0 if clave in DESFASE else 0.0)):
            mel.set_material_instance_scalar_parameter_value(mi, k, v)
        mel.set_material_instance_texture_parameter_value(mi, 'Color', c)
        # si falta normal o rugosidad se deja el valor por defecto del maestro (misma clase de textura)
        if n:
            mel.set_material_instance_texture_parameter_value(mi, 'Normal', n)
        if r:
            mel.set_material_instance_texture_parameter_value(mi, 'Rugosidad', r)
        mel.set_material_instance_scalar_parameter_value(mi, 'RugosidadEscala', RUGOSIDAD.get(clave, 1.0) if r else rough)
        mel.set_material_instance_scalar_parameter_value(mi, 'Metal', metal)
        mel.set_material_instance_scalar_parameter_value(mi, 'Tamano', rep * 100.0)
        mel.set_material_instance_vector_parameter_value(mi, 'Tinte', tinte)
        if clave == 'pared':   # zócalo pintado de cuartel: verde grisáceo hasta 1,15 m
            mel.set_material_instance_scalar_parameter_value(mi, 'ZocaloAltura', 115.0)
            mel.set_material_instance_vector_parameter_value(mi, 'ZocaloTinte', unreal.LinearColor(0.42, 0.55, 0.47, 1))
        if clave in SUCIEDAD:
            mel.set_material_instance_scalar_parameter_value(mi, 'Suciedad', SUCIEDAD[clave])
        mel.set_material_instance_scalar_parameter_value(mi, 'Mojable', MOJABLE.get(clave, 0.0) if CON_MOJADO else 0.0)
        eal.save_loaded_asset(mi, False)
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
            m.modify()       # sin esto el paquete no se da por cambiado...
            m.set_editor_property('static_materials', mats)
            eal.save_loaded_asset(m, False)      # ...y con «solo si ha cambiado» (lo de serie) no se guardaba: al reabrir, lh_* otra vez
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
