"""Tanda N, primera parte (Python del editor): lo que necesitan los tiros que se sienten.

1. M_Trazadora (/Game/Tarsis/Materiales): emisivo calido sin luz propia, para la barra de la trazadora (TarsisPeligro.cpp)
   y las chispas; M_PolvoImpacto: el polvo del impacto (translucido, parametro Opacidad).
2. Los sonidos nuevos de tools/sonido/generar_peligro.py (silbido_*, impacto_*_*, golpe_seco_*) en /Game/Tarsis/Sonidos,
   solo esos (no se reimporta lo demas).
Escribe en el registro «[Tarsis] peligro: ...»."""
import os
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
SON = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'assets', 'unreal', 'sonidos')
DM = '/Game/Tarsis/Materiales'
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
NUEVOS = ['silbido_%d' % k for k in (1, 2, 3)] + ['impacto_%s_%d' % (s, k) for s in ('tierra', 'metal', 'madera') for k in (1, 2, 3)] + ['golpe_seco_1', 'golpe_seco_2']


def trazadora():
    ruta = DM + '/M_Trazadora'
    if eal.does_asset_exist(ruta):
        return 'ya estaba'
    m = tools.create_asset('M_Trazadora', DM, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT)
    c = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
    c.set_editor_property('constant', unreal.LinearColor(9.0, 4.2, 1.2, 1))   # naranja de trazadora, se ve de noche
    mel.connect_material_property(c, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(m)
    eal.save_loaded_asset(m, False)
    return 'creado'


def polvo():
    """M_PolvoImpacto: translucido iluminado (de noche no brilla), color de tierra seca, opacidad por parametro
    (la baja el C++ mientras el polvo crece); las orillas de la bola mas transparentes (Fresnel) para que no parezca
    una esfera."""
    ruta = DM + '/M_PolvoImpacto'
    if eal.does_asset_exist(ruta):
        return 'ya estaba'
    m = tools.create_asset('M_PolvoImpacto', DM, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('two_sided', True)
    c = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -500, -100)
    c.set_editor_property('constant', unreal.LinearColor(0.36, 0.31, 0.25, 1))
    mel.connect_material_property(c, '', unreal.MaterialProperty.MP_BASE_COLOR)
    r = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -500, 0)
    r.set_editor_property('r', 1.0)
    mel.connect_material_property(r, '', unreal.MaterialProperty.MP_ROUGHNESS)
    op = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -700, 150)
    op.set_editor_property('parameter_name', 'Opacidad')
    op.set_editor_property('default_value', 0.5)
    fr = mel.create_material_expression(m, unreal.MaterialExpressionFresnel, -700, 300)
    inv = mel.create_material_expression(m, unreal.MaterialExpressionOneMinus, -550, 300)
    mel.connect_material_expressions(fr, '', inv, '')
    mul = mel.create_material_expression(m, unreal.MaterialExpressionMultiply, -350, 200)
    mel.connect_material_expressions(op, '', mul, 'A')
    mel.connect_material_expressions(inv, '', mul, 'B')
    mel.connect_material_property(mul, '', unreal.MaterialProperty.MP_OPACITY)
    mel.recompile_material(m)
    eal.save_loaded_asset(m, False)
    return 'creado'


def sonidos():
    tareas = []
    for n in NUEVOS:
        f = os.path.join(SON, n + '.wav')
        if not os.path.exists(f):
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property('filename', f)
        t.set_editor_property('destination_path', '/Game/Tarsis/Sonidos')
        t.set_editor_property('automated', True)
        t.set_editor_property('replace_existing', True)
        t.set_editor_property('save', True)
        tareas.append(t)
    tools.import_asset_tasks(tareas)
    return len(tareas)


r1 = trazadora()
r3 = polvo()
r2 = sonidos()
unreal.log('[Tarsis] peligro: M_Trazadora %s, M_PolvoImpacto %s, sonidos %d' % (r1, r3, r2))
