"""Tanda O: los brazos de primera persona con las mangas y las manos de Cuttlas.

Los brazos de la vista son el maniqui de Lyra (SKM_Manny_Simple), blanco. Este script lo duplica en
/Game/Tarsis/Personas/Brazos/SKM_Brazos_Cuttlas con un material propio (M_BrazosCuttlas): el tejido oscuro del traje de
Cuttlas y piel en las manos. El maniqui solo tiene dos huecos (cabeza y piernas / torso con brazos y manos), asi que las
manos se separan en el material por la posicion en la pose de referencia (PreSkinnedPosition, que solo existe en el
sombreador de vertices: pasa por un VertexInterpolator): lo que pasa de la muneca a
lo largo del antebrazo es piel (las munecas de SKM_Manny_Simple, medidas: hand_r (-47.8, 15.7, 104.5), lowerarm_r
(-35.0, -1.9, 120.9); simetrico en X). El director carga esa malla (ArmsMeshPath); si no existe, sigue el maniqui blanco.
No toca el maniqui original. Sin texturas nuevas (VRAM igual).

Uso, en el editor: py brazos_cuttlas.py  (rehace el material si ya estaba).
"""
import unreal

SRC = '/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple'
DIR = '/Game/Tarsis/Personas/Brazos'
DST = DIR + '/SKM_Brazos_Cuttlas'
MAT = DIR + '/M_BrazosCuttlas'
MI = DIR + '/MI_BrazosCuttlas'
TELA = unreal.LinearColor(0.016, 0.017, 0.021, 1.0)   # el traje negro azulado, mate
PIEL = unreal.LinearColor(0.40, 0.25, 0.17, 1.0)
MUNECA = unreal.LinearColor(47.8, 15.7, 104.5, 0.0)    # |x|, y, z de hand_r en la pose de referencia
ANTEBRAZO = (12.8, 17.6, -16.4)                          # de lowerarm a hand (|x|)
ANCHO = 2.5                                              # cm de transicion en la muneca

at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
E = unreal

if not eal.does_directory_exist(DIR):
    eal.make_directory(DIR)
if eal.does_asset_exist(MAT):
    mat = eal.load_asset(MAT)
    mel.delete_all_material_expressions(mat)
else:
    mat = at.create_asset('M_BrazosCuttlas', DIR, unreal.Material, unreal.MaterialFactoryNew())


def nodo(cls, x, y):
    return mel.create_material_expression(mat, cls, x, y)


def une(a, salida, b, entrada):
    if not mel.connect_material_expressions(a, salida, b, entrada):
        raise RuntimeError('no conecta %s -> %s.%s' % (a.get_name(), b.get_name(), entrada))


pre = nodo(E.MaterialExpressionPreSkinnedPosition, -1600, 0)
# PreSkinnedPosition solo existe en el sombreador de vertices: se pasa al de pixeles con un interpolador
vi = nodo(E.MaterialExpressionVertexInterpolator, -1400, 0)
mx = nodo(E.MaterialExpressionComponentMask, -1200, -60)
for c, v in (('r', True), ('g', False), ('b', False), ('a', False)):
    mx.set_editor_property(c, v)
myz = nodo(E.MaterialExpressionComponentMask, -1200, 80)
for c, v in (('r', False), ('g', True), ('b', True), ('a', False)):
    myz.set_editor_property(c, v)
ab = nodo(E.MaterialExpressionAbs, -1050, -60)
ap = nodo(E.MaterialExpressionAppendVector, -900, 0)
w = nodo(E.MaterialExpressionConstant3Vector, -900, 160)
w.set_editor_property('constant', MUNECA)
sub = nodo(E.MaterialExpressionSubtract, -750, 0)
n = (sum(v * v for v in ANTEBRAZO)) ** 0.5
dv = nodo(E.MaterialExpressionConstant3Vector, -750, 160)
dv.set_editor_property('constant', unreal.LinearColor(ANTEBRAZO[0] / n, ANTEBRAZO[1] / n, ANTEBRAZO[2] / n, 0.0))
dot = nodo(E.MaterialExpressionDotProduct, -600, 0)
add = nodo(E.MaterialExpressionAdd, -450, 0)
add.set_editor_property('const_b', 1.0)
mul = nodo(E.MaterialExpressionMultiply, -320, 0)
mul.set_editor_property('const_b', 1.0 / ANCHO)
sat = nodo(E.MaterialExpressionSaturate, -200, 0)
tela = nodo(E.MaterialExpressionVectorParameter, -320, -260)
tela.set_editor_property('parameter_name', 'Tela')
tela.set_editor_property('default_value', TELA)
piel = nodo(E.MaterialExpressionVectorParameter, -320, -120)
piel.set_editor_property('parameter_name', 'Piel')
piel.set_editor_property('default_value', PIEL)
lc = nodo(E.MaterialExpressionLinearInterpolate, -60, -160)
rt = nodo(E.MaterialExpressionScalarParameter, -320, 220)
rt.set_editor_property('parameter_name', 'RugosidadTela')
rt.set_editor_property('default_value', 0.8)
rp = nodo(E.MaterialExpressionScalarParameter, -320, 320)
rp.set_editor_property('parameter_name', 'RugosidadPiel')
rp.set_editor_property('default_value', 0.5)
lr = nodo(E.MaterialExpressionLinearInterpolate, -60, 220)

une(pre, '', vi, 'VS')
une(vi, '', mx, '')
une(vi, '', myz, '')
une(mx, '', ab, '')
une(ab, '', ap, 'A')
une(myz, '', ap, 'B')
une(ap, '', sub, 'A')
une(w, '', sub, 'B')
une(sub, '', dot, 'A')
une(dv, '', dot, 'B')
une(dot, '', add, 'A')
une(add, '', mul, 'A')
une(mul, '', sat, '')
une(tela, '', lc, 'A')
une(piel, '', lc, 'B')
une(sat, '', lc, 'Alpha')
une(rt, '', lr, 'A')
une(rp, '', lr, 'B')
une(sat, '', lr, 'Alpha')
mel.connect_material_property(lc, '', unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(lr, '', unreal.MaterialProperty.MP_ROUGHNESS)
mat.set_editor_property('used_with_skeletal_mesh', True)
mel.recompile_material(mat)
eal.save_asset(MAT)

if eal.does_asset_exist(MI):
    mi = eal.load_asset(MI)
else:
    mi = at.create_asset('MI_BrazosCuttlas', DIR, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
mel.set_material_instance_parent(mi, mat)
eal.save_asset(MI)

if not eal.does_asset_exist(DST):
    eal.duplicate_asset(SRC, DST)
sk = eal.load_asset(DST)
mats = list(sk.get_editor_property('materials'))
out = []
for i, m in enumerate(mats):
    m.set_editor_property('material_interface', mi)
    mats[i] = m
    out.append('%d %s -> MI_BrazosCuttlas' % (i, m.get_editor_property('material_slot_name')))
sk.set_editor_property('materials', mats)
eal.save_asset(DST)
print('\n'.join(out))
