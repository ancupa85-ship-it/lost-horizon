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

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))

# clave del visor -> (textura de Poly Haven, metros que ocupa una repetición, como tex(name, rep) en visor.js)
TEXTURAS = {
    'suelo': ('asphalt_02', 3.0), 'muro': ('concrete_wall_008', 3.2), 'hormigon': ('concrete_wall_008', 3.2),
    'pared': ('painted_plaster_wall', 2.6), 'madera': ('wood_planks_dirt', 1.6), 'hierro': ('rusty_metal_02', 1.4),
    'oliva': ('green_metal_rust', 2.2), 'tejado': ('corrugated_iron_02', 2.0), 'suelo_int': ('concrete_floor_worn_001', 2.0),
}
# tinte, rugosidad y metal del visor (escenario/visor.js, tabla M; color en sRGB)
VALORES = {
    'suelo': (0x777777, 0.75, 0.0), 'muro': (0x8a8a88, 0.82, 0.0), 'hormigon': (0x8a8a88, 0.82, 0.0),
    'pared': (0xa39c8e, 0.85, 0.0), 'madera': (0xb09a80, 0.75, 0.0), 'hierro': (0x999999, 0.6, 0.55),
    'oliva': (0x6f8a4c, 0.5, 0.1), 'tejado': (0x666668, 0.6, 0.4), 'suelo_int': (0x8c8c8c, 0.55, 0.0),
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
WAT = '/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedTexture.WorldAlignedTexture'
WAN = '/Engine/Functions/Engine_MaterialFunctions01/Texturing/WorldAlignedNormal.WorldAlignedNormal'

def maestro():
    ruta = DM + '/M_LH'
    if eal.does_asset_exist(ruta):
        return eal.load_asset(ruta)
    m = tools.create_asset('M_LH', DM, unreal.Material, unreal.MaterialFactoryNew())
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
    # tamaño de la textura (cm) como vector para las funciones alineadas al mundo
    size = E(unreal.MaterialExpressionScalarParameter, -1200, 0)
    size.set_editor_property('parameter_name', 'Tamano'); size.set_editor_property('default_value', 300.0)
    def tex_obj(nombre, x, y, normal=False):
        p = E(unreal.MaterialExpressionTextureObjectParameter, x, y)
        p.set_editor_property('parameter_name', nombre)
        if normal:
            p.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        return p
    def wat(obj, x, y, fn=WAT):
        f = E(unreal.MaterialExpressionMaterialFunctionCall, x, y)
        f.set_editor_property('material_function', unreal.load_asset(fn))
        mel.connect_material_expressions(obj, '', f, 'TextureObject')
        mel.connect_material_expressions(size, '', f, 'TextureSize')
        return f
    col = wat(tex_obj('Color', -1000, -300), -700, -300)
    tint = E(unreal.MaterialExpressionVectorParameter, -700, -500)
    tint.set_editor_property('parameter_name', 'Tinte'); tint.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
    mul = E(unreal.MaterialExpressionMultiply, -400, -350)
    mel.connect_material_expressions(col, 'XYZ Texture', mul, 'A')
    mel.connect_material_expressions(tint, '', mul, 'B')
    mel.connect_material_property(mul, '', unreal.MaterialProperty.MP_BASE_COLOR)
    # relieve: si una instancia no tiene normal, se queda con la normal plana por defecto del parámetro
    nor = wat(tex_obj('Normal', -1000, 0, True), -700, 0, WAN)
    mel.connect_material_property(nor, 'XYZ Texture', unreal.MaterialProperty.MP_NORMAL)
    # rugosidad: textura (si hay) x escala
    rt = wat(tex_obj('Rugosidad', -1000, 300), -700, 300)
    rs = E(unreal.MaterialExpressionScalarParameter, -700, 500)
    rs.set_editor_property('parameter_name', 'RugosidadEscala'); rs.set_editor_property('default_value', 1.0)
    rm = E(unreal.MaterialExpressionMultiply, -400, 350)
    mel.connect_material_expressions(rt, 'XYZ Texture', rm, 'A')
    mel.connect_material_expressions(rs, '', rm, 'B')
    mask = E(unreal.MaterialExpressionComponentMask, -250, 350)
    mask.set_editor_property('r', True); mask.set_editor_property('g', False)
    mask.set_editor_property('b', False); mask.set_editor_property('a', False)
    mel.connect_material_expressions(rm, '', mask, '')
    mel.connect_material_property(mask, '', unreal.MaterialProperty.MP_ROUGHNESS)
    met = E(unreal.MaterialExpressionScalarParameter, -400, 600)
    met.set_editor_property('parameter_name', 'Metal'); met.set_editor_property('default_value', 0.0)
    mel.connect_material_property(met, '', unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(m)
    eal.save_loaded_asset(m)
    return m

# ------------------------------------------------------------------ 3. instancias y asignación
def instancias():
    base = maestro()
    blanco = unreal.load_asset('/Engine/EngineResources/WhiteSquareTexture')
    plana = unreal.load_asset('/Engine/EngineMaterials/FlatNormal')
    out = {}
    for clave, (nombre, rep) in TEXTURAS.items():
        c = textura(nombre, 'diff')
        if c is None:
            log('AVISO: falta la textura', nombre, '- se deja el color liso en', clave)
            continue
        n = textura(nombre, 'nor'); r = textura(nombre, 'rough')
        ruta = DM + '/MI_' + clave
        mi = eal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset(
            'MI_' + clave, DM, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, base)
        hexc, rough, metal = VALORES[clave]
        tinte = unreal.LinearColor(*[lin((hexc >> s) & 255) for s in (16, 8, 0)], 1)
        # igual que en el visor: textura x color (si queda oscuro con la luz de Unreal se sube el Tinte de la instancia)
        mel.set_material_instance_texture_parameter_value(mi, 'Color', c)
        mel.set_material_instance_texture_parameter_value(mi, 'Normal', n or plana)
        mel.set_material_instance_texture_parameter_value(mi, 'Rugosidad', r or blanco)
        mel.set_material_instance_scalar_parameter_value(mi, 'RugosidadEscala', 1.0 if r else rough)
        mel.set_material_instance_scalar_parameter_value(mi, 'Metal', metal)
        mel.set_material_instance_scalar_parameter_value(mi, 'Tamano', rep * 100.0)
        mel.set_material_instance_vector_parameter_value(mi, 'Tinte', tinte)
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
        for sm in mats:
            mi = sm.get_editor_property('material_interface')
            nombre = (mi.get_name() if mi else '') or str(sm.get_editor_property('material_slot_name'))
            # el material importado se llama lh_<clave> (a veces con prefijo MI_ o sufijo de Interchange)
            k = nombre.split('lh_', 1)[1] if 'lh_' in nombre else None
            for clave in sorted(mis, key=len, reverse=True):
                if k and (k == clave or k.startswith(clave + '_') or k.startswith(clave + '.')) and not (clave == 'suelo' and k.startswith('suelo_int')):
                    sm.set_editor_property('material_interface', mis[clave]); cambia = True; n += 1
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
