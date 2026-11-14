"""Materiales realistas para la base de Tarsis en Unreal (texturas PBR de Poly Haven, CC0).

Se ejecuta dentro del editor después de montar_base.py (montar_base lo llama al final si existen las texturas):
1. Importa las texturas de assets/texturas/ (las descarga tools/blender/texturas.py; no van en el repositorio)
   en /Game/Tarsis/Texturas.
2. Crea un material maestro M_LH con proyección alineada al mundo (no depende de las UV de las mallas):
   color = textura x tinte, relieve (normal), rugosidad, metal; tamaño de la textura en cm como parámetro.
3. Crea una instancia MI_<clave> por cada material del visor que tiene textura (muro, pared, suelo, madera...)
   con el tinte, la rugosidad y el metal de escenario/visor.js, y la pone en las mallas en lugar de lh_<clave>.
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

def lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

# ------------------------------------------------------------------ 1. texturas
def textura(nombre, tipo):
    ruta = '%s/T_%s_%s' % (DT, nombre, tipo)
    if eal.does_asset_exist(ruta):
        return eal.load_asset(ruta)
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
    return tx

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
    ruido.set_editor_property('noise_function', unreal.NoiseFunction.NOISEFUNCTION_GRADIENT_TEX)
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
    mel.connect_material_property(sucio if CON_SUCIEDAD else mul, '', unreal.MaterialProperty.MP_BASE_COLOR)
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
    mel.connect_material_property(rsat if CON_SUCIEDAD else mask, '', unreal.MaterialProperty.MP_ROUGHNESS)
    met = E(unreal.MaterialExpressionScalarParameter, -400, 600)
    met.set_editor_property('parameter_name', 'Metal'); met.set_editor_property('default_value', 0.0)
    mel.connect_material_property(met, '', unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m

# ------------------------------------------------------------------ 3. instancias y asignación
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
    return n

if __name__ == '__main__':
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    ms = [a.get_asset() for a in ar.get_assets_by_path('/Game/Tarsis/Base', recursive=True)
          if str(a.asset_class_path.asset_name) == 'StaticMesh']
    aplicar(ms)
