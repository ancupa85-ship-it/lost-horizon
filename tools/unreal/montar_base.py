"""Monta la base de Tarsis en Unreal Engine 5 a partir de assets/unreal/base.glb y base.json.

Se ejecuta dentro del editor (Python del editor de Unreal), por ejemplo:
  UnrealEditor.exe "<proyecto>.uproject" -ExecutePythonScript="<repo>/tools/unreal/montar_base.py"
o desde el editor: Herramientas > Ejecutar script de Python.

Qué hace (se puede repetir: rehace el nivel cada vez):
1. Importa base.glb en /Game/Tarsis/Base/v<huella> (mallas y materiales); al final borra las versiones anteriores.
2. Crea el nivel /Game/Tarsis/Mapas/Tarsis y coloca todas las mallas en el origen (vienen con la posición aplicada).
   Las torres de vigilancia (torre1_*, torre2_*) van a la carpeta «Torres»; vallas y contenedores, a «Recintos»
   (la tela de las vallas con un material recortado de malla metálica, M_TelaMalla; los hierbajos, con M_Hierbajo,
   sin colisión ni sombra).
   El camión que circula (camionmovil_*) y la hoja del portón de entrada (hojaentrada_*) quedan móviles y con etiqueta.
3. Deduce cómo quedaron los ejes con las marcas lh_marca_* y coloca con esa conversión las luces del visor,
   la luna, el cielo nocturno, la niebla y la salida de Cuttlas.
4. Pone colisión «compleja como simple» para poder andar por todo, y guarda.
"""
import os, json, hashlib
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GLB = os.path.join(ROOT, 'assets', 'unreal', 'base.glb')
DATA = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'base.json')))
BASE = '/Game/Tarsis/Base'
# cada versión de base.glb se importa en su propia carpeta (v + 8 cifras de su huella); al final se borran las viejas
VER = hashlib.md5(open(GLB, 'rb').read()).hexdigest()[:8]
DEST = BASE + '/v' + VER
MAPA = '/Game/Tarsis/Mapas/Tarsis'

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))

# ------------------------------------------------------------------ 1. importar
eal = unreal.EditorAssetLibrary
ar = unreal.AssetRegistryHelpers.get_asset_registry()

def mallas():
    return [a.get_asset() for a in ar.get_assets_by_path(DEST, recursive=True)
            if str(a.asset_class_path.asset_name) == 'StaticMesh']

# si esta versión de la base ya está importada se reutiliza (LH_REIMPORT=1 para importarla de nuevo)
if os.environ.get('LH_REIMPORT') or not mallas():
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

def respaldo_completo(m):
    """Nanite: la malla de respaldo sin simplificar. La colisión «compleja como simple» de una malla Nanite sale de esa
    malla de respaldo; con el objetivo automático se simplificaba y los dinteles de algunas puertas bajaban de 2,2 m a
    1,85 m: de pie no se pasaba (el archivo, «entro agachado y no puedo salir»). Solo en las mallas de estructura
    (base_*: pared, muro, hierro, tejado, suelos...), que son por donde se anda y se pasa; los camiones, las cajas, las
    farolas y demás se quedan con el respaldo automático: sin simplificar, los camiones pasaban de ~1.200 a ~30.000
    triángulos de respaldo por malla sin arreglar nada. Devuelve True si ha cambiado algo."""
    ns = m.get_editor_property('nanite_settings')
    if not ns.get_editor_property('enabled'):
        return False
    if ns.get_editor_property('fallback_target') == unreal.NaniteFallbackTarget.RELATIVE_ERROR and ns.get_editor_property('fallback_relative_error') == 0.0:
        return False
    ns.set_editor_property('fallback_target', unreal.NaniteFallbackTarget.RELATIVE_ERROR)
    ns.set_editor_property('fallback_relative_error', 0.0)
    m.set_editor_property('nanite_settings', ns)
    return True

# colisión: la propia malla, para poder andar por suelos, escaleras y tejados
for m in meshes:
    # Interchange añade a cada malla un envolvente convexo automático. El mapa de navegación usa ese convexo en vez
    # de los triángulos, y en mallas que abarcan toda la base (base_oscuro: postes y antena en las esquinas) tapaba
    # el suelo entero: no salía navmesh. Con «compleja como simple» el convexo sobra, así que se quita.
    unreal.EditorStaticMeshLibrary.remove_collisions(m)
    bs = m.get_editor_property('body_setup')
    if bs:
        bs.set_editor_property('collision_trace_flag', unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if m.get_name().startswith(('valla_tela', 'hierbajos')):   # ni translúcidos (M_Tela) ni recortados que se mueven con el viento
        ns = m.get_editor_property('nanite_settings')
        if ns.get_editor_property('enabled'):
            ns.set_editor_property('enabled', False)
            m.set_editor_property('nanite_settings', ns)
    elif m.get_name().startswith('base_'):
        respaldo_completo(m)
    eal.save_loaded_asset(m, False)

# materiales realistas (texturas de Poly Haven), si están descargadas en assets/texturas
try:
    import sys
    sys.path.insert(0, HERE)
    import importlib, materiales
    importlib.reload(materiales)
    materiales.aplicar(meshes)
except Exception as e:
    log('AVISO: materiales realistas no aplicados:', repr(e))
# materiales físicos (grava, cemento, metal, madera, hierba): el sonido de los pasos según lo que pisas
try:
    import superficies
    importlib.reload(superficies)
    superficies.aplicar()
except Exception as e:
    log('AVISO: materiales físicos no aplicados:', repr(e))

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

def tela_translucida():
    """Material de reserva (el de las primeras tandas): placa translúcida gris. Solo si falta la textura de la malla."""
    ruta = '/Game/Tarsis/Materiales/M_Tela'
    if eal.does_asset_exist(ruta):
        return eal.load_asset(ruta)
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
    eal.save_loaded_asset(m, False)
    return m

TELA_PNG = os.path.join(ROOT, 'assets', 'unreal', 'texturas_propias', 'tela_metalica.png')
TELA_CM = 32.0   # centímetros que cubre la textura (tools/texturas/tela_metalica.py)

def tela_malla():
    """Tanda 21: la tela metálica es una malla recortada (rombos de alambre con el hueco en el canal alfa), no una placa
    translúcida que de noche parecía cristal. La textura se proyecta según la posición en el mundo (las placas de la valla
    van a lo largo de X o de Y), así que no depende de las UV. Se rehace si cambia el PNG."""
    mel = unreal.MaterialEditingLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    dm = '/Game/Tarsis/Materiales'
    huella = hashlib.md5(open(TELA_PNG, 'rb').read()).hexdigest()[:8]
    ruta = '%s/M_TelaMalla_%s' % (dm, huella)
    if eal.does_asset_exist(ruta):
        return eal.load_asset(ruta)
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', TELA_PNG)
    t.set_editor_property('destination_path', dm)
    t.set_editor_property('destination_name', 'T_TelaMetalica_' + huella)
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', False)
    tools.import_asset_tasks([t])
    tx = eal.load_asset('%s/T_TelaMetalica_%s' % (dm, huella))
    if tx is None:
        raise RuntimeError('no se importó ' + TELA_PNG)
    # al reducirse con la distancia, el alambre (16 % de la superficie) desaparecería del recorte: se conserva su cobertura
    for prop, val in (('do_scale_mips_for_alpha_coverage', True), ('alpha_coverage_thresholds', unreal.Vector4(0.0, 0.0, 0.0, 0.4))):
        try:
            tx.set_editor_property(prop, val)
        except Exception as e:
            log('AVISO: textura de la tela sin', prop, repr(e))
    eal.save_loaded_asset(tx, False)
    m = tools.create_asset('M_TelaMalla_' + huella, dm, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('opacity_mask_clip_value', 0.4)
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
    def uno(a, b):   # la entrada única se llama «Input» o «» según el nodo (como en materiales.py)
        if not mel.connect_material_expressions(a, '', b, 'Input'):
            mel.connect_material_expressions(a, '', b, '')
    def canal(k, y):
        c = E(unreal.MaterialExpressionComponentMask, -900, y)
        for q in 'rgba':
            c.set_editor_property(q, q == k)
        uno(wp, c)
        return c
    wp = E(unreal.MaterialExpressionWorldPosition, -1150, 0)
    cx, cy, cz = canal('r', -150), canal('g', 0), canal('b', 150)
    u = E(unreal.MaterialExpressionAdd, -720, -80)      # a lo largo de la valla: X + Y (una de las dos no cambia en cada placa)
    mel.connect_material_expressions(cx, '', u, 'A')
    mel.connect_material_expressions(cy, '', u, 'B')
    uv = E(unreal.MaterialExpressionAppendVector, -560, 0)
    mel.connect_material_expressions(u, '', uv, 'A')
    mel.connect_material_expressions(cz, '', uv, 'B')
    esc = E(unreal.MaterialExpressionDivide, -400, 0)
    esc.set_editor_property('const_b', TELA_CM)
    mel.connect_material_expressions(uv, '', esc, 'A')
    ts = E(unreal.MaterialExpressionTextureSample, -220, 0)
    ts.set_editor_property('texture', tx)
    if not mel.connect_material_expressions(esc, '', ts, 'UVs'):
        mel.connect_material_expressions(esc, '', ts, 'Coordinates')
    mel.connect_material_property(ts, 'RGB', unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(ts, 'A', unreal.MaterialProperty.MP_OPACITY_MASK)
    for prop, val, y in ((unreal.MaterialProperty.MP_ROUGHNESS, 0.45, 250), (unreal.MaterialProperty.MP_METALLIC, 0.85, 350)):
        c = E(unreal.MaterialExpressionConstant, -220, y)
        c.set_editor_property('r', val)
        mel.connect_material_property(c, '', prop)
    mel.recompile_material(m)
    eal.save_loaded_asset(m, False)
    log('material de tela metálica recortada', ruta)
    return m

_TELA = []
def tela_mat(actor):
    if not _TELA:
        try:
            _TELA.append(tela_malla())
        except Exception as e:
            log('AVISO: tela metálica recortada no creada, se usa la translúcida:', repr(e))
            _TELA.append(tela_translucida())
    c = actor.get_component_by_class(unreal.StaticMeshComponent)
    if c:
        c.set_material(0, _TELA[0])
        c.set_editor_property('cast_shadow', False)   # miles de rombos dando sombra no compensan en una GTX 1050

HIERBA_PNG = os.path.join(ROOT, 'assets', 'unreal', 'texturas_propias', 'hierbajo.png')
# tinte: lo que multiplica al color de la textura (lineal); rodales: cuánto oscurecen los rodales más secos (0 = todas iguales)
HIERBA_AJUSTES = {'tinte': (0.66, 0.64, 0.56), 'rodales': 0.5}

_HIERBA = []     # la huella del material en uso (para borrar los de otras versiones al final)

def hierbajo_material():
    """Tanda 22: material de los hierbajos (malla «hierbajos» de exportar_base.py). Recortado, con las UV de la malla sobre la
    textura de cuatro matas (tools/texturas/hierbajo.py), mate y sin brillo. Las matas se mecen un poco: la punta se mueve
    unos 2 cm con una onda lenta que recorre la base (la raíz no se mueve: el peso sale de la UV). Se rehace si cambia el PNG."""
    mel = unreal.MaterialEditingLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    dm = '/Game/Tarsis/Materiales'
    # la huella lleva también los ajustes del material: al cambiarlos se rehace aunque el PNG sea el mismo
    huella = hashlib.md5(open(HIERBA_PNG, 'rb').read() + repr(HIERBA_AJUSTES).encode()).hexdigest()[:8]
    ruta = '%s/M_Hierbajo_%s' % (dm, huella)
    _HIERBA[:] = [huella]
    if eal.does_asset_exist(ruta):
        return eal.load_asset(ruta)
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', HIERBA_PNG)
    t.set_editor_property('destination_path', dm)
    t.set_editor_property('destination_name', 'T_Hierbajo_' + huella)
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', False)
    tools.import_asset_tasks([t])
    tx = eal.load_asset('%s/T_Hierbajo_%s' % (dm, huella))
    if tx is None:
        raise RuntimeError('no se importó ' + HIERBA_PNG)
    # las briznas son finas: al reducirse la textura con la distancia se conserva lo que cubren, o las matas se deshacen
    for prop, val in (('do_scale_mips_for_alpha_coverage', True), ('alpha_coverage_thresholds', unreal.Vector4(0.0, 0.0, 0.0, 0.35))):
        try:
            tx.set_editor_property(prop, val)
        except Exception as e:
            log('AVISO: textura de hierbajos sin', prop, repr(e))
    eal.save_loaded_asset(tx, False)
    m = tools.create_asset('M_Hierbajo_' + huella, dm, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    m.set_editor_property('two_sided', False)     # cada plano ya viene por las dos caras, con la normal hacia arriba
    m.set_editor_property('opacity_mask_clip_value', 0.35)
    E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
    ts = E(unreal.MaterialExpressionTextureSample, -400, 0)
    ts.set_editor_property('texture', tx)
    # tanda 23: color = textura x tinte x (rodales). Las matas reciben la luz como el suelo (normal hacia arriba) y con el
    # color de la textura a secas quedaban más claras que el hormigón bajo una farola: parecían recortes pegados. El tinte
    # las deja por debajo del suelo, y un dibujo lento en el mundo (dos senos, sin texturas) hace que unos rodales estén
    # más secos y oscuros que otros. Si algo no conecta, se quedan con textura x tinte
    tinte = E(unreal.MaterialExpressionConstant3Vector, -400, -220)
    tinte.set_editor_property('constant', unreal.LinearColor(*HIERBA_AJUSTES['tinte'], 1))
    cbase = E(unreal.MaterialExpressionMultiply, -200, -120)
    mel.connect_material_expressions(ts, 'RGB', cbase, 'A')
    mel.connect_material_expressions(tinte, '', cbase, 'B')
    color = cbase
    try:
        ok = []
        def U(a, sal, b, ent):
            ok.append(bool(mel.connect_material_expressions(a, sal, b, ent)))
        def U1(a, b):
            if not mel.connect_material_expressions(a, '', b, 'Input'):
                ok.append(bool(mel.connect_material_expressions(a, '', b, '')))
        wpc = E(unreal.MaterialExpressionWorldPosition, -1500, -700)
        def eje(k, y):
            c = E(unreal.MaterialExpressionComponentMask, -1320, y)
            for q in 'rgba':
                c.set_editor_property(q, q == k)
            U1(wpc, c)
            return c
        ex, ey = eje('r', -760), eje('g', -640)
        def onda(kx, ky, y):       # seno((x * kx + y * ky)), periodo 1
            a = E(unreal.MaterialExpressionMultiply, -1150, y); a.set_editor_property('const_b', kx); U(ex, '', a, 'A')
            b = E(unreal.MaterialExpressionMultiply, -1150, y + 60); b.set_editor_property('const_b', ky); U(ey, '', b, 'A')
            c = E(unreal.MaterialExpressionAdd, -1000, y); U(a, '', c, 'A'); U(b, '', c, 'B')
            sn = E(unreal.MaterialExpressionSine, -860, y); U1(c, sn)
            return sn
        s1, s2 = onda(1.0 / 730.0, 1.0 / 1150.0, -820), onda(1.0 / 1900.0, -1.0 / 1300.0, -640)
        pr = E(unreal.MaterialExpressionMultiply, -720, -740); U(s1, '', pr, 'A'); U(s2, '', pr, 'B')      # -1..1, a rodales de 4 a 10 m
        esc = E(unreal.MaterialExpressionMultiply, -600, -740); esc.set_editor_property('const_b', HIERBA_AJUSTES['rodales'] / 2.0); U(pr, '', esc, 'A')
        mas = E(unreal.MaterialExpressionAdd, -480, -740); mas.set_editor_property('const_b', 1.0 - HIERBA_AJUSTES['rodales'] / 2.0); U(esc, '', mas, 'A')
        cvar = E(unreal.MaterialExpressionMultiply, -60, -200); U(cbase, '', cvar, 'A'); U(mas, '', cvar, 'B')
        if all(ok):
            color = cvar
        else:
            log('AVISO: hierbajos sin rodales de color (no conectaron', ok.count(False), 'nodos)')
    except Exception as e:
        log('AVISO: hierbajos sin rodales de color:', repr(e))
    mel.connect_material_property(color, '', unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(ts, 'A', unreal.MaterialProperty.MP_OPACITY_MASK)
    for prop, val, y in ((unreal.MaterialProperty.MP_ROUGHNESS, 0.95, 250), (unreal.MaterialProperty.MP_SPECULAR, 0.05, 350)):
        c = E(unreal.MaterialExpressionConstant, -400, y)
        c.set_editor_property('r', val)
        mel.connect_material_property(c, '', prop)
    # viento: desplazamiento = dirección x 2,2 cm x peso² x seno(tiempo x 0,3 + posición / 5 m). Si algún nodo no conecta
    # (cambian de nombre entre versiones), las matas se quedan quietas: no se enchufa nada a medias
    try:
        bien = []
        def une(a, sal, b, ent):
            ok = mel.connect_material_expressions(a, sal, b, ent)
            bien.append(bool(ok))
            return ok
        def une1(a, b):
            if not mel.connect_material_expressions(a, '', b, 'Input'):
                bien.append(bool(mel.connect_material_expressions(a, '', b, '')))
        def canal(src, k, x, y):
            c = E(unreal.MaterialExpressionComponentMask, x, y)
            for q in 'rgba':
                c.set_editor_property(q, q == k)
            une1(src, c)
            return c
        uv = E(unreal.MaterialExpressionTextureCoordinate, -1500, 600)
        v2 = E(unreal.MaterialExpressionMultiply, -1150, 600)
        v2.set_editor_property('const_b', 2.0)
        une(canal(uv, 'g', -1320, 600), '', v2, 'A')
        fr = E(unreal.MaterialExpressionFrac, -1000, 600)
        une1(v2, fr)
        peso = E(unreal.MaterialExpressionOneMinus, -860, 600)     # 0 en la raíz (abajo de cada casilla), 1 en la punta
        une1(fr, peso)
        peso2 = E(unreal.MaterialExpressionMultiply, -720, 600)
        une(peso, '', peso2, 'A'); une(peso, '', peso2, 'B')
        wp = E(unreal.MaterialExpressionWorldPosition, -1500, 800)
        suma = E(unreal.MaterialExpressionAdd, -1150, 800)
        une(canal(wp, 'r', -1320, 760), '', suma, 'A'); une(canal(wp, 'g', -1320, 860), '', suma, 'B')
        fase = E(unreal.MaterialExpressionMultiply, -1000, 800)
        fase.set_editor_property('const_b', 1.0 / 500.0)
        une(suma, '', fase, 'A')
        tm = E(unreal.MaterialExpressionTime, -1150, 980)
        tk = E(unreal.MaterialExpressionMultiply, -1000, 980)
        tk.set_editor_property('const_b', 0.3)
        une(tm, '', tk, 'A')
        arg = E(unreal.MaterialExpressionAdd, -860, 880)
        une(fase, '', arg, 'A'); une(tk, '', arg, 'B')
        seno = E(unreal.MaterialExpressionSine, -720, 880)       # periodo 1: una onda por unidad
        une1(arg, seno)
        amp = E(unreal.MaterialExpressionMultiply, -560, 740)
        une(seno, '', amp, 'A'); une(peso2, '', amp, 'B')
        dire = E(unreal.MaterialExpressionConstant3Vector, -560, 920)
        dire.set_editor_property('constant', unreal.LinearColor(2.2, 0.8, 0.0, 0.0))
        wpo = E(unreal.MaterialExpressionMultiply, -400, 800)
        une(amp, '', wpo, 'A'); une(dire, '', wpo, 'B')
        if all(bien):
            mel.connect_material_property(wpo, '', unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        else:
            log('AVISO: hierbajos sin viento (no conectaron', bien.count(False), 'nodos)')
    except Exception as e:
        log('AVISO: hierbajos sin viento:', repr(e))
    mel.recompile_material(m)
    eal.save_loaded_asset(m, False)
    log('material de hierbajos', ruta)
    return m

def hierbajos(actor):
    """Las matas no estorban: ni colisión (no paran al jugador, ni las balas, ni la vista de los guardias), ni navegación, ni sombra."""
    c = actor.get_component_by_class(unreal.StaticMeshComponent)
    actor.set_actor_enable_collision(False)
    if not c:
        return
    c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    c.set_editor_property('can_ever_affect_navigation', False)
    c.set_editor_property('cast_shadow', False)
    # las manchas del suelo no se pintan en las hojas; y unas briznas no cuentan para la luz indirecta ni para los campos
    # de distancia (con Lumen dejarían borrones oscuros alrededor de cada mata)
    for prop in ('receives_decals', 'affect_distance_field_lighting', 'affect_dynamic_indirect_lighting', 'visible_in_ray_tracing'):
        try:
            c.set_editor_property(prop, False)
        except Exception as e:
            log('AVISO: hierbajos sin', prop, repr(e))
    try:
        c.set_material(0, hierbajo_material())
    except Exception as e:
        log('AVISO: material de hierbajos no creado (se quedan con el color liso):', repr(e))
        actor.set_actor_hidden_in_game(True)     # sin el recorte serían rectángulos verdes: mejor no verlos

marks = {}
# tanda 21: piezas que el director mueve en el juego (las busca por su etiqueta de actor, «tag»). Todas tienen el origen
# en el origen del mundo: la hoja del portón de entrada se corre hacia el sur y el camión (modelado en el origen, con el
# frente hacia +X) se lleva por el camino.
MOVILES = {'camionmovil': ('camion', 'Camion'), 'hojaentrada': ('hoja_entrada', 'Perimetro')}
moviles = {}
for m in meshes:
    a = eas.spawn_actor_from_object(m, unreal.Vector(0, 0, 0))
    name = m.get_name()
    a.set_actor_label(name)
    a.set_folder_path('Torres' if name.startswith('torre') else
                      'Recintos' if name.startswith(('valla', 'contenedor')) else 'Base')
    for clave, (tag, carpeta) in MOVILES.items():
        if name.startswith(clave):
            c = a.get_component_by_class(unreal.StaticMeshComponent)
            c.set_mobility(unreal.ComponentMobility.MOVABLE)
            c.set_editor_property('can_ever_affect_navigation', False)
            a.tags = [unreal.Name(tag)]
            a.set_folder_path(carpeta)
            moviles.setdefault(clave, []).append(a)
            try:
                c.set_editor_property('receives_decals', False)   # las manchas del camino no se pintan en los bajos del camión
            except Exception as e:
                log('AVISO:', name, 'sin receives_decals:', repr(e))
    if name.endswith('_bombilla'):
        # tanda 27: el cristal de las bombillas no da sombra (la suya propia dejaba un disco negro en el techo)
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        if c:
            c.set_editor_property('cast_shadow', False)
    if name.startswith('valla_tela'):
        tela_mat(a)
    if name.startswith('hierbajos'):
        a.set_folder_path('Recintos')
        hierbajos(a)
    if name.startswith('contenedordet'):
        # tanda 25: costillas, pilares y puertas de los contenedores. Solo se ven: se choca, se dispara y se mira contra
        # la caja de siempre (contenedor_N), y el mapa de navegación no se entera
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        a.set_actor_enable_collision(False)
        if c:
            c.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            c.set_editor_property('can_ever_affect_navigation', False)
        a.tags = [unreal.Name('contenedor_detalle')]
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

# el camión espera fuera, al principio del terraplén del oeste (el director lo pone ahí al empezar; así tampoco estorba
# en el editor ni en las capturas)
ext = DATA.get('ext') or {}
if moviles.get('camionmovil') and ext.get('camino'):
    cam = ext['camino']
    ini = ue([cam['x0'] + 5.0, -cam['y'], cam.get('alto', 0.04)])
    for a in moviles['camionmovil']:
        a.set_actor_location(ini, False, False)
    log('camión en', ini, '-', len(moviles['camionmovil']), 'piezas; hoja de entrada:', len(moviles.get('hojaentrada', [])), 'piezas')

# noche: exposición manual (EV) e intensidades de luna y luz ambiente, ajustadas con capturas en el patio
# Ajuste 25c: luna de 0,6 a 0,8 y luz ambiente de 2,5 a 4,0. Con los albedos de verdad lo que no alumbra una farola se
# quedaba en negro (zona_militar_10m: muro 16 de 255, suelo 9). La exposición no se toca (las farolas ya no queman y
# así siguen), y el sigilo tampoco cambia: para los guardias la luna y el cielo son un fijo (ATarsisGuard::LightAt,
# 0,12). La luz ambiente sube más que la luna porque la bóveda nueva (cielo.py, menos azul) le da un quinto menos.
# Ajuste 25e: luz ambiente de 4,0 a 2,0. A 4,0 aclaraba todas las sombras por igual: se veía todo, pero plano y gris,
# y a Andres le parecían más reales las capturas oscuras de antes (patio de la segunda pasada, chapa del contenedor en
# sombra). Poca luz de relleno y la luna con dirección: contraste de noche de verdad sin volver al negro total
# Ajuste 25f: exposición un paso abajo (0,5 a -0,5: la mitad de luz en toda la imagen, farolas incluidas). Medido en la
# 0025e, la luz ambiente casi no oscurecía (patio 18 a 17); lo que hacía más creíble la segunda pasada era el nivel
# general. Así vuelve la noche oscura con los materiales buenos. Solo es imagen: el sigilo no la usa
# Tanda 26 (Andres dejó la luz a mi criterio): exposición a 0,0, a medio camino entre la 25e (0,5: se veía todo, pero
# plano) y la 25f (-0,5: creíble, pero lo que no alumbra una farola se quedaba otra vez sin leer). Medio paso sube toda la
# imagen un 41 % sin tocar el reparto de luz: la noche sigue con contraste y con dirección. La luz ambiente sube un
# poco (2,0 a 2,2) para que las sombras cercanas tengan algo dentro. Farolas, halos y luna, igual. Solo es imagen
EXPO = {'ev': 0.0, 'luna': 0.8, 'cielo': 2.2}
# tanda 25: las luces fuertes de fuera se pintan diez veces más flojas de lo que cuentan para el sigilo (etiqueta
# «luz_fuerte»; ATarsisGuard::LightAt multiplica por 10). Con 3000 lm bajo cada farola el suelo salía blanco quemado y a
# cinco metros negro: 140 veces más luz que la de la luna, cuando una imagen aguanta unas 20. Ahora el suelo devuelve
# más (materiales.py, ALBEDO) y la farola da menos: el charco de luz tiene color y alrededor queda penumbra.
LUZ_FUERTE = 'luz_fuerte'
FAROLA_LM, FOCO_LM, HANGAR_SOMBRA = True   # si la VRAM no da, False (y la luz se ve algo por fuera de la nave)
APLIQUE_LM = 300.0, 800.0, 150.0
# tanda 26: qué farolas dibujan sombra (assets/unreal/mision1.json, ajustes.montaje). Hasta la 25 ninguna: bajo una
# farola no tenías sombra. Ahora la sombra del jugador delata (ATarsisDirector::ShadowTick) y solo cuentan las luces que
# la dibujan, así que la farola que no dé sombra tampoco delata. Lo que cuesta se mide con tools/unreal/barracon.py
try:
    MONTAJE = json.load(open(os.path.join(ROOT, 'assets', 'unreal', 'mision1.json'), encoding='utf-8')).get('ajustes', {}).get('montaje', {})
except Exception as e:
    MONTAJE = {}
    log('AVISO: no se lee el montaje de mision1.json:', repr(e))
FAROLAS_SOMBRA = MONTAJE.get('farolas_con_sombra', 'ninguna')

def farola_con_sombra(nombre):
    return FAROLAS_SOMBRA == 'todas' or (isinstance(FAROLAS_SOMBRA, list) and nombre in FAROLAS_SOMBRA)

# tanda 26: la luz de dentro, cuarto por cuarto. Clave: el número de la luz en base.json (el de su etiqueta, interior_N).
# lm: lúmenes (ninguna pasa de 600: por debajo, para el sigilo toda luz vale el mínimo, así que esto solo es imagen);
# radio en cm (corto: que no llegue al cuarto de al lado ni haya que calcular su sombra desde fuera); color; sombra.
# Bombilla cálida en los cuartos de tropa y tubo frío algo verdoso en archivo y despacho; la roja se queda roja.
# Objetivos al medir las capturas (0-255): pared a 2 m de la bombilla 110-140, rincón más lejano 25-40, suelo bajo la
# bombilla 170 como mucho, nada por encima de 220 y las jambas de la puerta sin quemar.
# La 0 es la del barracón oeste: ambiente.py la apaga y pone su fluorescente.
INTERIORES = {
    0: {'lm': 300.0, 'radio': 900.0, 'color': (1.0, 0.86, 0.62), 'sombra': True},
    1: {'lm': 380.0, 'radio': 800.0, 'color': (1.0, 0.80, 0.55), 'sombra': True},
    2: {'lm': 400.0, 'radio': 800.0, 'color': (0.80, 1.0, 0.86), 'sombra': True},    # archivo
    3: {'lm': 420.0, 'radio': 900.0, 'color': (1.0, 0.86, 0.62), 'sombra': True},
    4: {'lm': 340.0, 'radio': 800.0, 'color': (1.0, 0.86, 0.62), 'sombra': True},
    5: {'lm': 380.0, 'radio': 800.0, 'color': (0.84, 1.0, 0.90), 'sombra': True},    # despacho
    6: {'lm': 240.0, 'radio': 700.0, 'color': (1.0, 0.314, 0.251), 'sombra': True},
}

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
        c.set_editor_property('intensity', EXPO['luna'])
        c.set_light_color(col)
        c.set_editor_property('atmosphere_sun_light', True)
        try:
            c.set_editor_property('light_source_angle', 1.2)      # sombras de luna con algo de penumbra (0,54 por defecto)
        except Exception as e:
            log('AVISO: luna sin light_source_angle:', repr(e))
        continue
    if l['kind'] == 'SPOT':
        rot = unreal.MathLibrary.make_rot_from_x(ue_dir(l['dir']))
        a = spawn(unreal.SpotLight, ue(l['pos']), '%s_%d' % (l['name'], i), rot)
        c = a.get_component_by_class(unreal.SpotLightComponent)
        # tanda 26: el foco sigue un recorrido por el suelo (ATarsisGuard, SweepPath) y su mancha se aprende: más
        # prieta (13 a 10 grados) para que el borde sea claro y cruzarla sea una decisión
        c.set_editor_property('outer_cone_angle', 10.0)
        c.set_editor_property('inner_cone_angle', 7.0)
        c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
        c.set_editor_property('intensity', FOCO_LM)   # 8000 de sigilo (LUZ_FUERTE); pintados quemaban el suelo y las fachadas
        c.set_editor_property('attenuation_radius', 4000.0)
        a.tags = [unreal.Name(LUZ_FUERTE)]
    elif l['name'] == 'farola':
        # farola: foco hacia abajo (una puntual no dibuja haz en la niebla). Va 25 cm al lado del poste y 20 cm más
        # baja: en la posición original queda dentro del poste, que tapa el cono y la traza de LightAt
        a = spawn(unreal.SpotLight, ue(l['pos']) + unreal.Vector(25, 0, -20), '%s_%d' % (l['name'], i), unreal.Rotator(roll=0, pitch=-90, yaw=0))
        a.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)   # r.AllowStaticLighting=False con Lumen
        c = a.get_component_by_class(unreal.SpotLightComponent)
        c.set_editor_property('outer_cone_angle', 55.0)       # el cono de fuera es el que cuenta para el sigilo: no se toca
        c.set_editor_property('inner_cone_angle', 18.0)       # 35 hasta la tanda 24: el borde del charco de luz era un escalón
        c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
        c.set_editor_property('intensity', FAROLA_LM)         # 3000 de sigilo (LUZ_FUERTE)
        c.set_editor_property('attenuation_radius', 1800.0)
        a.tags = [unreal.Name(LUZ_FUERTE)]
        c.set_editor_property('cast_shadows', farola_con_sombra('%s_%d' % (l['name'], i)))
        c.set_editor_property('volumetric_scattering_intensity', 1.5)
    else:
        pos = list(l['pos'])
        # ajuste 25d: la bombilla del archivo (17, -35) iba en el eje de su puerta, a 3,75 m del hueco, y por el canto del
        # marco alumbraba las jambas del pasillo de fuera (placa_archivo: 31 y 51 de 255 con la pared a 21; 133 en la
        # 0025c). Tres metros más al fondo del cuarto (20, -35) las jambas quedan en sombra (8 y 35, lo que da la luna) y
        # el archivo sale algo más alumbrado (54 de media frente a 44)
        if l['name'] == 'interior' and abs(pos[0] - 17.0) < 0.01 and abs(pos[1] + 35.0) < 0.01:
            pos[0] = 20.0
        a = spawn(unreal.PointLight, ue(pos), '%s_%d' % (l['name'], i))
        c = a.get_component_by_class(unreal.PointLightComponent)
        c.set_editor_property('intensity_units', unreal.LightUnits.LUMENS)
        c.set_editor_property('intensity', min(l['power'] * 2.0, 4000.0))
        c.set_editor_property('attenuation_radius', 1800.0 if l['name'] == 'farola' else 900.0)
        if l['name'] == 'hangar':   # tanda 40: una sola bombilla en el centro de la nave; con sombra para que no traspase los muros
            c.set_editor_property('intensity', 600.0)
            c.set_editor_property('attenuation_radius', 1100.0)
            c.set_editor_property('cast_shadows', HANGAR_SOMBRA)
            c.set_editor_property('source_radius', 6.0)
        if l['name'] == 'aplique':   # bombilla de pared (portillo): alumbra la puerta y poco más, sin sombras
            c.set_editor_property('attenuation_radius', 700.0)
            c.set_editor_property('cast_shadows', False)
            # a medio metro del muro, 520 lm lo dejaban blanco. Para el sigilo cuenta igual: por debajo de 600 lm
            # toda luz vale el mínimo (0,2)
            c.set_editor_property('intensity', APLIQUE_LM)
        if l['name'] == 'interior' and i in INTERIORES:
            t = INTERIORES[i]
            c.set_editor_property('intensity', min(t['lm'], 600.0))
            c.set_editor_property('attenuation_radius', t['radio'])
            c.set_editor_property('cast_shadows', t['sombra'])
            c.set_editor_property('source_radius', 4.0)   # una bombilla, no un punto: la sombra tiene algo de penumbra
            col = unreal.LinearColor(t['color'][0], t['color'][1], t['color'][2], 1)
    c.set_light_color(col)

# noche: cielo, luz ambiente tenue y niebla
spawn(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), 'Cielo')
sky = spawn(unreal.SkyLight, unreal.Vector(0, 0, 500), 'LuzAmbiente')
sc = sky.get_component_by_class(unreal.SkyLightComponent)
sc.set_editor_property('real_time_capture', True)
sc.set_editor_property('intensity', EXPO['cielo'])
fog = spawn(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0), 'Niebla')
fc = fog.get_component_by_class(unreal.ExponentialHeightFogComponent)
fc.set_editor_property('fog_density', 0.03)
# ajuste 25c: lo lejano (la marisma tras el muro) lo tiñe la niebla con el azul de la atmósfera y salía más añil que el
# propio cielo, ya corregido. Se le quita azul a esa aportación. Sin comprobar aún en el PC: mirar el horizonte en las
# capturas de patio_seco
try:
    fc.set_editor_property('sky_atmosphere_ambient_contribution_color_scale', unreal.LinearColor(1.3, 0.9, 0.6, 1.0))
except Exception as e:
    log('AVISO: niebla sin sky_atmosphere_ambient_contribution_color_scale:', repr(e))

# exposición fija de noche: sin esto la exposición automática sube la escena hasta parecer de día (cielo azul)
pp = spawn(unreal.PostProcessVolume, unreal.Vector(0, 0, 0), 'Exposicion')
pp.set_editor_property('unbound', True)
st = pp.get_editor_property('settings')
st.set_editor_property('override_auto_exposure_method', True)
st.set_editor_property('auto_exposure_method', unreal.AutoExposureMethod.AEM_MANUAL)
st.set_editor_property('override_auto_exposure_apply_physical_camera_exposure', True)
st.set_editor_property('auto_exposure_apply_physical_camera_exposure', False)
st.set_editor_property('override_auto_exposure_bias', True)
st.set_editor_property('auto_exposure_bias', EXPO['ev'])
# tanda 25: un punto de película en toda la base (grano fino, que además rompe las bandas del degradado del cielo y de
# la niebla), sombras algo frías y luces algo cálidas. Lo del barracón oeste lo pone su propio volumen (ambiente.py)
for k, val in (('film_grain_intensity', 0.12), ('bloom_intensity', 0.8),
               ('color_gain_shadows', unreal.Vector4(0.95, 0.99, 1.06, 1.0)), ('color_gain_highlights', unreal.Vector4(1.04, 1.0, 0.94, 1.0))):
    try:
        st.set_editor_property('override_' + k, True)
        st.set_editor_property(k, val)
    except Exception as e:
        log('AVISO: posproceso sin', k, repr(e))
pp.set_editor_property('settings', st)

# salida de Cuttlas (casilla P del plano), un poco por encima del suelo, mirando hacia el espacio libre más cercano
if DATA.get('spawn'):
    p = DATA['spawn']
    yaw = 0.0
    mapa = DATA.get('map') or []
    T = DATA.get('T', 2.0)
    pr = next(((r, row.index('P')) for r, row in enumerate(mapa) if 'P' in row), None)
    if pr:
        sx = sy = 0.0
        for r, row in enumerate(mapa):
            for c, ch in enumerate(row):
                if ch == '.' and abs(r - pr[0]) <= 6 and abs(c - pr[1]) <= 6:
                    sx += c - pr[1]; sy += r - pr[0]
        d = ue_dir([sx * T, -sy * T, 0])   # columnas -> +x de Blender, filas -> -y de Blender
        if d.length() > 0:
            yaw = unreal.MathLibrary.make_rot_from_x(d).yaw
    ps = eas.spawn_actor_from_class(unreal.PlayerStart, ue([p[0], p[1], 1.0]), unreal.Rotator(roll=0, pitch=0, yaw=yaw))
    ps.set_actor_label('SalidaCuttlas')
    log('salida de Cuttlas', ps.get_actor_location(), 'mirando a', round(yaw))

# guardias de la fase 2 (si la clase C++ ATarsisGuard está compilada)
try:
    import sys, importlib
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import guardias
    importlib.reload(guardias)
    guardias.colocar()
    # tanda 25: la bóveda del cielo, los halos de las luminarias y su resplandor de relleno (después del director: de él
    # sale dónde está el farol del control). ambiente.py pone luego la lámpara de la puerta del barracón: para que tenga
    # halo, ejecutar cielo.py otra vez al final
    try:
        import cielo
        importlib.reload(cielo)
        cielo.todo()
    except Exception as e:
        log('AVISO: cielo no puesto:', repr(e))
    guardias.guardar_tras_navegacion()   # guarda ahora y otra vez cuando acaba el mapa de navegación
except Exception as e:
    log('AVISO: guardias no colocados:', repr(e))
    les.save_current_level()
log('nivel guardado en', MAPA)

# limpiar importaciones anteriores (el nivel ya no las usa)
viejas = [p for p in eal.list_assets(BASE, recursive=True, include_folder=False) if not p.startswith(DEST + '/')]
for p in viejas:
    eal.delete_asset(p.split('.')[0])
for d in eal.list_assets(BASE, recursive=False, include_folder=True):
    d = d.rstrip('/')
    if d != DEST and eal.does_directory_exist(d):
        eal.delete_directory(d)
log('versión', VER, '- borrados', len(viejas), 'recursos de importaciones anteriores')
# y los materiales y texturas de hierbajos de otras versiones (llevan la huella en el nombre): ya no los usa nadie y
# ocupan memoria de vídeo mientras el editor los tenga cargados
try:
    actual = _HIERBA[0] if _HIERBA else None
    if actual:
        n = 0
        for p in eal.list_assets('/Game/Tarsis/Materiales', recursive=False, include_folder=False):
            nombre = p.split('/')[-1].split('.')[0]
            if nombre.startswith(('M_Hierbajo_', 'T_Hierbajo_')) and not nombre.endswith('_' + actual):
                n += bool(eal.delete_asset(p.split('.')[0]))
        if n:
            log('borrados', n, 'recursos de hierbajos de versiones anteriores')
except Exception as e:
    log('AVISO: no se limpiaron los hierbajos antiguos:', repr(e))
