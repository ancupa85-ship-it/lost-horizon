"""Carteles, rótulos y etiquetas del nivel Tarsis (tanda 24).

Las texturas las dibuja tools/carteles/generar.py (assets/unreal/carteles/<tex>.png, en git) y la lista de dónde va
cada uno es assets/unreal/carteles.json. Aquí, en el editor con el nivel Tarsis abierto:  py tools/unreal/carteles.py
  1) importa las texturas a /Game/Tarsis/Carteles (T_Cartel_<tex>);
  2) hace los dos materiales y una instancia por textura:
     - M_Cartel: chapa esmaltada (superficie con recorte: el canal alfa recorta la señal redonda). Satinada.
     - M_Rotulo: pintura de plantilla sobre un muro o la losa (calcomanía «modulada», como M_Mancha: con Substrate mezcla
       el color de la pintura con lo de debajo según la opacidad, así que el blanco aclara y coge el grano del muro);
  3) coloca cada cartel: las placas son planos a 1,5 cm de la pared (o en un poste clavado en el suelo); lo pintado,
     calcomanías. Todo va a la carpeta «Carteles» con la etiqueta «cartel» y se quita y se vuelve a poner cada vez.

Orientación: lo que no se puede saber sin mirar es si el motor pinta la textura del plano y de la calcomanía del derecho.
Si en la captura un cartel sale en espejo o cabeza abajo, se corrige aquí arriba (ESPEJO_*), no en cada cartel.
"""
import os, sys, json
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LISTA = os.path.join(ROOT, 'assets', 'unreal', 'carteles.json')
PNG = os.path.join(ROOT, 'assets', 'unreal', 'carteles')
DC = '/Game/Tarsis/Carteles'
CARPETA = 'Carteles'
TAG = 'cartel'
PLANO = '/Engine/BasicShapes/Plane.Plane'          # 100 x 100 cm en XY, normal +Z
CILINDRO = '/Engine/BasicShapes/Cylinder.Cylinder'  # radio 50, alto 100
CUBO = '/Engine/BasicShapes/Cube.Cube'
V = unreal.Vector

# (u, v) -> 1 del derecho, -1 en espejo. Por clase: placa (plano), pintado (calcomanía en pared), suelo (calcomanía en la losa)
ESPEJO = {'placa': (1.0, 1.0), 'pintado': (1.0, 1.0), 'suelo': (1.0, 1.0)}
# calcomanía de pared: el motor pone la U de la textura a lo largo de la Z de la calcomanía (en vertical). Sin girarla, el
# lema de 8 x 1 m salía como rayas horizontales (el texto, de lado, aplastado en 1 m de alto). Se gira la calcomanía
# sobre su eje de proyección y se cambian ancho y alto de la caja (comprobado con capturas del 2 del portillo y del lema)
RODAR_PINTADO = 90.0
SEPARA = 1.5          # cm entre la placa y su poste

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))


def datos():
    return json.load(open(LISTA, encoding='utf-8'))


def _ambiente():
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import ambiente, importlib
    importlib.reload(ambiente)
    return ambiente


def textura(tex):
    ruta = '%s/T_Cartel_%s' % (DC, tex)
    f = os.path.join(PNG, tex + '.png')
    if eal.does_asset_exist(ruta):
        t = eal.load_asset(ruta)
        # si el PNG es más nuevo que lo importado se vuelve a importar (se guarda su fecha en los metadatos)
        if not os.path.exists(f) or eal.get_metadata_tag(t, 'lh_fecha') == str(int(os.path.getmtime(f))):
            return t
    if not os.path.exists(f):
        log('AVISO: falta', f, '(python tools/carteles/generar.py)')
        return None
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', f)
    t.set_editor_property('destination_path', DC)
    t.set_editor_property('destination_name', 'T_Cartel_' + tex)
    t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True)
    t.set_editor_property('save', False)
    tools.import_asset_tasks([t])
    tx = eal.load_asset(ruta)
    if tx is None:
        return None
    tx.set_editor_property('srgb', True)
    tx.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT)   # con alfa: BC3
    tx.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_WORLD)
    eal.set_metadata_tag(tx, 'lh_fecha', str(int(os.path.getmtime(f))))
    eal.save_loaded_asset(tx, False)
    return tx


def _uv(g, x, y):
    """UV con espejo por parámetro: (uv - 0,5) x (EspejoU, EspejoV) + 0,5."""
    uv = g.E(unreal.MaterialExpressionTextureCoordinate, x, y)
    c05 = g.E(unreal.MaterialExpressionConstant2Vector, x, y + 120, r=0.5, g=0.5)
    esp = g.op(unreal.MaterialExpressionAppendVector, g.esc('EspejoU', 1.0, x, y + 240), g.esc('EspejoV', 1.0, x, y + 340), x + 200, y + 280)
    d = g.op(unreal.MaterialExpressionSubtract, uv, c05, x + 200, y)
    return g.op(unreal.MaterialExpressionAdd, g.op(unreal.MaterialExpressionMultiply, d, esp, x + 380, y), c05, x + 540, y)


def material_cartel(defecto):
    """M_Cartel: chapa esmaltada. Textura (RGB color, A recorte), Rugosidad (satinado: 0,42), Tinte y Brillo.
    Brillo (tanda 25): la chapa devuelve un poco de luz propia, del color de su pintura, como las señales con pintura
    reflectante. Es lo que deja leer «ZONA MILITAR» de noche sin poner un foco (una luz más cambiaría el sigilo): con
    0,12 el amarillo queda entre el suelo a la luna y el suelo bajo una farola, y la letra negra sigue negra. 0 = nada."""
    amb = _ambiente()
    g = amb.Grafo(amb.DM + '/M_Cartel', 'M_Cartel', 'cartel v2 brillo')
    if g.hecho:
        return g.m
    g.m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MASKED)
    g.m.set_editor_property('two_sided', False)
    t = g.E(unreal.MaterialExpressionTextureSampleParameter2D, -500, 0, parameter_name='Textura', texture=defecto,
            sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    g.une(_uv(g, -1300, 0), t, ('UVs', 'Coordinates'))
    tinte = g.E(unreal.MaterialExpressionVectorParameter, -500, -260, parameter_name='Tinte', default_value=unreal.LinearColor(1, 1, 1, 1))
    col = g.E(unreal.MaterialExpressionMultiply, -200, -100)
    g.une(t, col, 'A', 'RGB'); g.une(tinte, col, 'B')
    g.sale(col, unreal.MaterialProperty.MP_BASE_COLOR)
    g.sale(g.op(unreal.MaterialExpressionMultiply, col, g.esc('Brillo', 0.0, -200, 120), 0, 60), unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    g.sale(t, unreal.MaterialProperty.MP_OPACITY_MASK, 'A')
    g.sale(g.esc('Rugosidad', 0.42, -500, 320), unreal.MaterialProperty.MP_ROUGHNESS)
    return g.fin()


def material_rotulo(defecto):
    """M_Rotulo: pintura de plantilla (calcomanía modulada). Textura (RGB color de la pintura, A cuánta queda) y Fuerza."""
    amb = _ambiente()
    g = amb.Grafo(amb.DM + '/M_Rotulo', 'M_Rotulo', 'rotulo v1')
    if g.hecho:
        return g.m
    g.m.set_editor_property('blend_mode', unreal.BlendMode.BLEND_MODULATE)        # antes que el dominio (ver M_Mancha)
    g.m.set_editor_property('material_domain', unreal.MaterialDomain.MD_DEFERRED_DECAL)
    t = g.E(unreal.MaterialExpressionTextureSampleParameter2D, -500, 0, parameter_name='Textura', texture=defecto,
            sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
    g.une(_uv(g, -1300, 0), t, ('UVs', 'Coordinates'))
    g.sale(t, unreal.MaterialProperty.MP_BASE_COLOR, 'RGB')
    opa = g.E(unreal.MaterialExpressionMultiply, -200, 200)
    g.une(t, opa, 'A', 'A'); g.une(g.esc('Fuerza', 0.8, -500, 360), opa, 'B')
    g.sale(g.sat(opa, -60, 200), unreal.MaterialProperty.MP_OPACITY)
    return g.fin()


def instancia(nombre, base, tx, clase, fuerza=None, brillo=None):
    ruta = '%s/MI_%s' % (DC, nombre)
    mi = eal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset(
        'MI_' + nombre, DC, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, base)
    mel.set_material_instance_texture_parameter_value(mi, 'Textura', tx)
    mel.set_material_instance_scalar_parameter_value(mi, 'EspejoU', ESPEJO[clase][0])
    mel.set_material_instance_scalar_parameter_value(mi, 'EspejoV', ESPEJO[clase][1])
    if fuerza is not None:
        mel.set_material_instance_scalar_parameter_value(mi, 'Fuerza', fuerza)
    if clase == 'placa':
        mel.set_material_instance_scalar_parameter_value(mi, 'Brillo', float(brillo or 0.0))
    eal.save_loaded_asset(mi, False)
    return mi


def ejes_placa(mira):
    """Giro del plano para que su normal (+Z local) mire hacia «mira», su X local sea la derecha de quien lo lee y su Y
    local, hacia abajo (la textura: u a la derecha, v hacia abajo)."""
    import math
    r = math.radians(mira)
    n = V(math.cos(r), math.sin(r), 0.0)
    derecha = V(n.y, -n.x, 0.0)          # la derecha de quien mira la placa de frente
    return unreal.MathLibrary.make_rotation_from_axes(derecha, V(0.0, 0.0, -1.0), n), n


def colocar():
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for a in eas.get_all_level_actors():
        if a.actor_has_tag(TAG):
            eas.destroy_actor(a)
    lista = datos()['carteles']
    tex = {}
    for c in lista:
        if c['tex'] not in tex:
            tex[c['tex']] = textura(c['tex'])
    defecto = next((t for t in tex.values() if t is not None), None)
    if defecto is None:
        log('AVISO: carteles: no hay texturas en', PNG)
        return 0
    m_placa, m_rot = material_cartel(defecto), material_rotulo(defecto)
    hierro = '/Game/Tarsis/Materiales/MI_hierro'
    muro = '/Game/Tarsis/Materiales/MI_muro'
    plano, cil, cubo = unreal.load_asset(PLANO), unreal.load_asset(CILINDRO), unreal.load_asset(CUBO)
    mis = {}
    n = 0

    def actor(cls_o_malla, nombre, pos, rot):
        a = (eas.spawn_actor_from_object(cls_o_malla, pos, rot) if isinstance(cls_o_malla, unreal.StaticMesh)
             else eas.spawn_actor_from_class(cls_o_malla, pos, rot))
        a.set_actor_label('Cartel_' + nombre)
        a.set_folder_path(CARPETA)
        a.tags = [unreal.Name(TAG)]
        return a

    def malla(a, material, sombra=False):
        c = a.static_mesh_component
        c.set_mobility(unreal.ComponentMobility.STATIC)
        c.set_collision_profile_name('NoCollision')
        c.set_editor_property('can_ever_affect_navigation', False)
        c.set_editor_property('cast_shadow', sombra)
        c.set_editor_property('receives_decals', False)       # los regueros del muro no pintan encima de la chapa
        mi = unreal.load_asset(material) if isinstance(material, str) else material
        if mi:
            c.set_material(0, mi)
        return c

    for c in lista:
        tx = tex.get(c['tex'])
        if tx is None:
            continue
        clase = c['clase']
        clave = (c['tex'], clase, c.get('fuerza'), c.get('brillo'))
        if clave not in mis:
            sufijo = '' if c.get('fuerza') is None else '_%d' % round(c['fuerza'] * 100)
            if c.get('brillo'):
                sufijo += '_b%d' % round(c['brillo'] * 100)
            mis[clave] = instancia('%s_%s%s' % (clase, c['tex'], sufijo), m_placa if clase == 'placa' else m_rot, tx, clase, c.get('fuerza'), c.get('brillo'))
        mi = mis[clave]
        x, y, z = c['pos']
        an, al = c['tam']
        if clase == 'placa':
            rot, nrm = ejes_placa(c['mira'])
            pos = V(x, y, z)
            if c.get('panel'):
                # murete detrás (el botiquín colgaba del muro viejo, que ya no está): solo si no hay ya una pared
                px, py, pan, pal, pgr = c['panel']
                h = unreal.SystemLibrary.line_trace_single(w, V(x, y, z) + nrm * 40.0, V(x, y, z) - nrm * 60.0, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                           True, [], unreal.DrawDebugTrace.NONE, True)
                if not h:
                    p = actor(cubo, c['nombre'] + '_panel', V(px, py, pal / 2.0), unreal.Rotator(0, 0, c['mira'] - 90.0))
                    p.set_actor_scale3d(V(pan / 100.0, pgr / 100.0, pal / 100.0))
                    cp = malla(p, muro, sombra=True)
                    cp.set_collision_profile_name('BlockAll')
                    cp.set_editor_property('receives_decals', True)
                    log('carteles: panel para', c['nombre'])
            if c.get('poste'):
                alto = float(c['poste'])
                p = actor(cil, c['nombre'] + '_poste', V(x, y, alto / 2.0), unreal.Rotator(0, 0, 0))
                p.set_actor_scale3d(V(0.05, 0.05, alto / 100.0))
                malla(p, hierro, sombra=True)
                pos = V(x, y, z) + nrm * (2.5 + SEPARA)
            a = actor(plano, c['nombre'], pos, rot)
            a.set_actor_scale3d(V(an / 100.0, al / 100.0, 1.0))
            malla(a, mi)
        else:
            if clase == 'pintado':
                # la calcomanía proyecta a lo largo de su X: hacia dentro de la pared (la contraria de «mira»)
                rot = unreal.Rotator(c.get('giro', 0.0) + RODAR_PINTADO, 0.0, c['mira'] + 180.0)
                fondo = 12.0
                if RODAR_PINTADO % 180.0:
                    an, al = al, an          # la caja girada 90: su Y va en vertical
            else:
                rot = unreal.Rotator(0.0, -90.0, c.get('giro', 0.0))
                fondo = 8.0
            a = actor(unreal.DecalActor, c['nombre'], V(x, y, z), rot)
            a.decal.set_decal_material(mi)
            a.decal.set_editor_property('decal_size', V(fondo, an / 2.0, al / 2.0))
            a.decal.set_editor_property('sort_order', int(c.get('orden', 1)))
        n += 1
    log('carteles colocados:', n, 'de', len(lista))
    return n


def todo():
    n = colocar()
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return n


if __name__ == '__main__':
    todo()
