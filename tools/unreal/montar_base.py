"""Monta la base de Tarsis en Unreal Engine 5 a partir de assets/unreal/base.glb y base.json.

Se ejecuta dentro del editor (Python del editor de Unreal), por ejemplo:
  UnrealEditor.exe "<proyecto>.uproject" -ExecutePythonScript="<repo>/tools/unreal/montar_base.py"
o desde el editor: Herramientas > Ejecutar script de Python.

Qué hace (se puede repetir: rehace el nivel cada vez):
1. Importa base.glb en /Game/Tarsis/Base (mallas y materiales).
2. Crea el nivel /Game/Tarsis/Mapas/Tarsis y coloca todas las mallas en el origen (vienen con la posición aplicada).
   Las torres de vigilancia (torre1_*, torre2_*) van a la carpeta «Torres»; vallas y contenedores, a «Recintos»
   (la tela de las vallas con un material translúcido, M_Tela).
3. Deduce cómo quedaron los ejes con las marcas lh_marca_* y coloca con esa conversión las luces del visor,
   la luna, el cielo nocturno, la niebla y la salida de Cuttlas.
4. Pone colisión «compleja como simple» para poder andar por todo, y guarda.
"""
import os, json
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GLB = os.path.join(ROOT, 'assets', 'unreal', 'base.glb')
DATA = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json')))
DEST = '/Game/Tarsis/Base'
MAPA = '/Game/Tarsis/Mapas/Tarsis'

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))

# ------------------------------------------------------------------ 1. importar
eal = unreal.EditorAssetLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry()

def mallas():
    return [a.get_asset() for a in ar.get_assets_by_path(DEST, recursive=True)
            if str(a.asset_class_path.asset_name) == 'StaticMesh']

# si la base ya está importada se reutiliza (LH_REIMPORT=1 para importarla de nuevo)
# también se reimporta solo si base.glb trae mallas nuevas (p. ej. las torres)
if os.environ.get('LH_REIMPORT') or len(mallas()) < DATA.get('mallas', 1):
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', GLB)
    task.set_editor_property('destination_path', DEST)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    log('importados', len(list(task.get_editor_property('imported_object_paths') or [])))
else:
    log('base ya importada: se reutiliza')

meshes = mallas()
log('mallas', len(meshes))
if not meshes:
    raise RuntimeError('No se importó ninguna malla de ' + GLB)

# colisión: la propia malla, para poder andar por suelos, escaleras y tejados
for m in meshes:
    bs = m.get_editor_property('body_setup')
    if bs:
        bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    eal.save_loaded_asset(m)

# ------------------------------------------------------------------ 2. nivel nuevo
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if eal.does_asset_exist(MAPA):   # se rehace por dentro: vaciar el nivel existente
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if MAPA not in world.get_path_name():
        les.load_level(MAPA)
    for a in eas.get_all_level_actors():
        eas.destroy_actor(a)
else:
    les.new_level(MAPA)

def tela_mat(actor):
    """La tela metálica se ve a través (en el visor es una textura con agujeros): material translúcido gris metálico."""
    ruta = '/Game/Tarsis/Materiales/M_Tela'
    if eal.does_asset_exist(ruta):
        m = eal.load_asset(ruta)
    else:
        mel = unreal.MaterialEditingLibrary
        m = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_Tela', '/Game/Tarsis/Materiales',
                                                                     unreal.Material, unreal.MaterialFactoryNew())
        m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
        m.set_editor_property('two_sided', True)
        col = mel.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -300, 0)
        col.set_editor_property('constant', unreal.LinearColor(0.38, 0.41, 0.41, 1))
        mel.connect_material_property(col, '', unreal.MaterialProperty.MP_BASE_COLOR)
        op = mel.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 200)
        op.set_editor_property('r', 0.35)
        mel.connect_material_property(op, '', unreal.MaterialProperty.MP_OPACITY)
        mel.recompile_material(m)
        eal.save_loaded_asset(m)
    c = actor.get_component_by_class(unreal.StaticMeshComponent)
    if c:
        c.set_material(0, m)

marks = {}
for m in meshes:
    a = eas.spawn_actor_from_object(m, unreal.Vector(0, 0, 0))
    name = m.get_name()
    a.set_actor_label(name)
    a.set_folder_path('Torres' if name.startswith('torre') else
                      'Recintos' if name.startswith(('valla', 'contenedor')) else 'Base')
    if name.startswith('valla_tela'):
        tela_mat(a)
    for k in ('lh_marca_o', 'lh_marca_x', 'lh_marca_y', 'lh_marca_z'):
        if name.startswith(k):
            o, _ = a.get_actor_bounds(False)
            marks[k] = o
            a.set_actor_hidden_in_game(True)

# ------------------------------------------------------------------ 3. ejes: Blender (m) -> Unreal (cm)
if len(marks) == 4:
    O = marks['lh_marca_o']
    ax = [(marks[k] - O) * (1.0 / 10.0) for k in ('lh_marca_x', 'lh_marca_y', 'lh_marca_z')]
    log('ejes', O, ax)
else:
    log('AVISO: faltan marcas', list(marks), '- se usa la conversión típica de glTF')
    O = unreal.Vector(0, 0, 0)
    ax = [unreal.Vector(100, 0, 0), unreal.Vector(0, -100, 0), unreal.Vector(0, 0, 100)]

def ue(p):
    return O + ax[0] * p[0] + ax[1] * p[1] + ax[2] * p[2]

def ue_dir(d):
    return ax[0] * d[0] + ax[1] * d[1] + ax[2] * d[2]

def spawn(cls, loc, label, rot=None):
    a = eas.spawn_actor_from_class(cls, loc, rot or unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    a.set_folder_path('Luces')
    return a

for i, l in enumerate(DATA['lights']):
    col = unreal.LinearColor(l['color'][0], l['color'][1], l['color'][2], 1)
    if l['kind'] == 'SUN':
        rot = unreal.MathLibrary.make_rot_from_x(ue_dir(l['dir']))
        a = spawn(unreal.DirectionalLight, ue(l['pos']), 'Luna', rot)
        c = a.get_component_by_class(unreal.DirectionalLightComponent)
        c.set_editor_property('intensity', 0.6)
        c.set_light_color(col)
        c.set_editor_property('atmosphere_sun_light', True)
        continue
    if l['kind'] == 'SPOT':
        rot = unreal.MathLibrary.make_rot_from_x(ue_dir(l['dir']))
        a = spawn(unreal.SpotLight, ue(l['pos']), '%s_%d' % (l['name'], i), rot)
        c = a.get_component_by_class(unreal.SpotLightComponent)
        c.set_editor_property('outer_cone_angle', 13.0)
        c.set_editor_property('inner_cone_angle', 9.0)
        c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
        c.set_editor_property('intensity', 60000.0)
        c.set_editor_property('attenuation_radius', 4000.0)
    else:
        a = spawn(unreal.PointLight, ue(l['pos']), '%s_%d' % (l['name'], i))
        c = a.get_component_by_class(unreal.PointLightComponent)
        c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
        c.set_editor_property('intensity', min(l['power'] * 2.0, 4000.0))
        c.set_editor_property('attenuation_radius', 1800.0 if l['name'] == 'farola' else 900.0)
    c.set_light_color(col)

# noche: cielo, luz ambiente tenue y niebla
spawn(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), 'Cielo')
sky = spawn(unreal.SkyLight, unreal.Vector(0, 0, 500), 'LuzAmbiente')
sc = sky.get_component_by_class(unreal.SkyLightComponent)
sc.set_editor_property('real_time_capture', True)
sc.set_editor_property('intensity', 0.25)
fog = spawn(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0), 'Niebla')
fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
fc.set_editor_property('fog_density', 0.03)

# salida de Cuttlas (casilla P del plano), un poco por encima del suelo
if DATA.get('spawn'):
    p = DATA['spawn']
    ps = eas.spawn_actor_from_class(unreal.PlayerStart, ue([p[0], p[1], 1.0]), unreal.Rotator(0, 0, 0))
    ps.set_actor_label('SalidaCuttlas')

les.save_current_level()
log('nivel guardado en', MAPA)
