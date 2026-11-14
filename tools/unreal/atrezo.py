"""Atrezo real del nivel Tarsis: modelos escaneados de Poly Haven (CC0) con texturas a 1K.

Tres pasos:
  1) descargar()  (Python normal o el del editor): glTF a assets/modelos-ph/<id>/ (no se guarda en git).
  2) importar()   (en el editor): a /Game/Tarsis/Atrezo/<id>, con LOD automáticos, colisión simple (caja)
                  y texturas de 1024 como mucho (la tarjeta tiene 4 GB).
  3) colocar()    (en el editor): pone en el nivel lo que dice assets/unreal/atrezo.json (modelo, posición,
                  giro, escala; los actores van a la carpeta Atrezo y se quitan y se vuelven a poner cada vez).
Uso en el editor: py tools/unreal/atrezo.py   (hace los tres y guarda el nivel)
Fuera del editor: python tools/unreal/atrezo.py descargar
"""
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DESCARGAS = os.path.join(ROOT, 'assets', 'modelos-ph')
LISTA = os.path.join(ROOT, 'assets', 'unreal', 'atrezo.json')
DESTINO = '/Game/Tarsis/Atrezo'


def datos():
    return json.load(open(LISTA, encoding='utf-8'))


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'lost-horizon-build'}), timeout=180).read()


def descargar(res='1k'):
    for i in datos()['modelos']:
        d = os.path.join(DESCARGAS, i)
        main = os.path.join(d, i + '.gltf')
        if os.path.exists(main):
            continue
        f = json.loads(_get('https://api.polyhaven.com/files/' + i))['gltf']
        f = f.get(res, f[sorted(f)[0]])['gltf']
        os.makedirs(d, exist_ok=True)
        tot = 0
        for path, inc in f.get('include', {}).items():
            p = os.path.join(d, path)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            b = _get(inc['url'])
            open(p, 'wb').write(b)
            tot += len(b)
        open(main, 'wb').write(_get(f['url']))
        print('  +', i, tot // 1024, 'KB', flush=True)


# ---------------------------------------------------------------- en el editor

def _log(*a):
    import unreal
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))


def partes(i):
    import unreal
    out = []
    for a in unreal.EditorAssetLibrary.list_assets(DESTINO + '/' + i, recursive=True):
        o = unreal.load_asset(a)
        if isinstance(o, unreal.StaticMesh) and not o.get_name().startswith('SM_'):
            out.append(o)
    return out


def malla(i):
    """La malla de una pieza: SM_<id>, que junta todas sus partes (cajones, tapón, agujas...) en la escala buena."""
    import unreal
    ruta = '%s/%s/SM_%s' % (DESTINO, i, i)
    return unreal.load_asset(ruta) if unreal.EditorAssetLibrary.does_asset_exist(ruta) else None


def juntar(i):
    """Interchange importa cada nodo del glTF como una malla aparte (ya en su sitio dentro del modelo): se ponen todas
    en el origen y se funden en SM_<id> con sus materiales (y la escala de «escala_import» si el modelo viene en otra)."""
    import unreal
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    k = datos().get('escala_import', {}).get(i, 1.0)
    actores = []
    for m in partes(i):
        a = eas.spawn_actor_from_object(m, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
        a.set_actor_scale3d(unreal.Vector(k, k, k))
        actores.append(a)
    if not actores:
        return None
    o = unreal.MergeStaticMeshActorsOptions()
    o.set_editor_property('base_package_name', '%s/%s/%s' % (DESTINO, i, i))   # la fusión le pone SM_ delante
    o.set_editor_property('destroy_source_actors', True)
    o.set_editor_property('spawn_merged_actor', False)
    ms = o.get_editor_property('mesh_merging_settings')
    ms.set_editor_property('pivot_type', unreal.MeshMergePivotType.WORLD_ORIGIN)
    ms.set_editor_property('merge_materials', False)
    o.set_editor_property('mesh_merging_settings', ms)
    unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).merge_static_mesh_actors(actores, o)
    for a in actores:
        if a and unreal.SystemLibrary.is_valid(a):
            eas.destroy_actor(a)
    return malla(i)


def importar(forzar=False):
    import unreal
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    sms = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for i in datos()['modelos']:
        if malla(i) and not forzar:
            continue
        if unreal.EditorAssetLibrary.does_directory_exist(DESTINO + '/' + i):
            unreal.EditorAssetLibrary.delete_directory(DESTINO + '/' + i)
        t = unreal.AssetImportTask()
        t.filename = os.path.join(DESCARGAS, i, i + '.gltf')
        t.destination_path = DESTINO + '/' + i
        t.automated = True
        t.replace_existing = True
        t.save = True
        tools.import_asset_tasks([t])
        m = juntar(i)
        if not m:
            _log('AVISO: no se ha importado', i)
            continue
        # LOD automáticos (3 niveles), colisión simple de caja y luz en el mapa de luces por si se hornea algo
        opts = unreal.EditorScriptingMeshReductionOptions()
        opts.reduction_settings = [unreal.EditorScriptingMeshReductionSettings(1.0, 1.0),
                                   unreal.EditorScriptingMeshReductionSettings(0.5, 0.45),
                                   unreal.EditorScriptingMeshReductionSettings(0.2, 0.2)]
        sms.set_lods(m, opts)
        sms.remove_collisions(m)
        sms.add_simple_collisions(m, unreal.ScriptCollisionShapeType.BOX)
        # texturas: 1024 como mucho
        for a in unreal.EditorAssetLibrary.list_assets(DESTINO + '/' + i, recursive=True):
            o = unreal.load_asset(a)
            if isinstance(o, unreal.Texture2D):
                o.set_editor_property('max_texture_size', 1024)
                unreal.EditorAssetLibrary.save_loaded_asset(o)
        unreal.EditorAssetLibrary.save_loaded_asset(m)
        _log('atrezo importado:', i)


def vaciar():
    """Quita de las mallas fusionadas de la base los muebles de Blender que el atrezo sustituye (atrezo.json, «vaciar»):
    cada pieza que toca una de las cajas se borra entera (componente conectado). Las mallas de la base están en el
    origen, así que sus coordenadas son las del mundo. Si ya están vaciadas no cambia nada."""
    import unreal
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    cajas = [c for k, v in datos().get('vaciar', {}).items() if not k.startswith('_') for c in v]
    def caja(c):
        b = unreal.Box()
        b.min = unreal.Vector(c[0], c[1], c[2]); b.max = unreal.Vector(c[3], c[4], c[5]); b.is_valid = True
        return b
    total = 0
    for a in eas.get_all_level_actors():
        if not isinstance(a, unreal.StaticMeshActor) or str(a.get_folder_path()) == 'Atrezo':
            continue
        o, e = a.get_actor_bounds(False)
        if not any(o.x + e.x >= c[0] and o.x - e.x <= c[3] and o.y + e.y >= c[1] and o.y - e.y <= c[4] and o.z - e.z <= c[5] for c in cajas):
            continue
        sm = a.static_mesh_component.static_mesh
        dm = unreal.DynamicMesh()
        unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(sm, dm, unreal.GeometryScriptCopyMeshFromAssetOptions(), unreal.GeometryScriptMeshReadLOD())
        quitados = 0
        for c in cajas:
            r = unreal.GeometryScript_MeshSelection.select_mesh_elements_in_box(dm, caja(c), unreal.GeometryScriptMeshSelectionType.TRIANGLES, False, 1)
            sel = r[1] if isinstance(r, tuple) else r
            r = unreal.GeometryScript_MeshSelection.expand_mesh_selection_to_connected(dm, sel)
            sel = r[1] if isinstance(r, tuple) else r
            r = unreal.GeometryScript_MeshEdits.delete_selected_triangles_from_mesh(dm, sel)
            quitados += r[1] if isinstance(r, tuple) else 0
        if quitados:
            unreal.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm, sm, unreal.GeometryScriptCopyMeshToAssetOptions(), unreal.GeometryScriptMeshWriteLOD())
            unreal.EditorAssetLibrary.save_loaded_asset(sm)
            _log('vaciado', a.get_actor_label(), quitados, 'triángulos')
            total += quitados
    return total


def colocar():
    import unreal
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    for a in eas.get_all_level_actors():
        if str(a.get_folder_path()) == 'Atrezo':
            eas.destroy_actor(a)
    n = 0
    for p in datos()['piezas']:
        m = malla(p['modelo'])
        if p.get('parte'):
            m = next((q for q in partes(p['modelo']) if q.get_name() == p['parte']), None)
        if not m:
            _log('AVISO: falta el modelo', p['modelo'], p.get('parte', ''))
            continue
        x, y, z = p['pos']
        if not p.get('colgar'):
            # se apoya en lo que haya debajo (suelo, mesa, caja ya colocada)
            h = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, z), unreal.Vector(x, y, z - 400), unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                       True, [], unreal.DrawDebugTrace.NONE, True)
            if h:
                z = h.to_tuple()[4].z
        a = eas.spawn_actor_from_object(m, unreal.Vector(x, y, z), unreal.Rotator(0.0, 0.0, p.get('giro', 0.0)))
        a.set_actor_scale3d(unreal.Vector(*([p.get('escala', 1.0)] * 3)))
        a.set_actor_label('Atrezo_' + p.get('nombre', p['modelo']))
        a.set_folder_path('Atrezo')
        c = a.get_component_by_class(unreal.StaticMeshComponent)
        if c:
            c.set_mobility(unreal.ComponentMobility.STATIC)
            # lo pequeño no tapa a nadie: sin colisión con personas ni con la vista de los guardias
            if p.get('pequeno'):
                c.set_collision_profile_name('NoCollision')
            # las lámparas no tapan su propia luz (si no, la jaula pinta una mancha negra en la pared)
            if p.get('sin_sombra'):
                c.set_editor_property('cast_shadow', False)
        n += 1
    _log('atrezo colocado:', n, 'piezas')
    return n


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'descargar':
        descargar()
    else:
        import unreal
        descargar()
        importar()
        vaciar()
        colocar()
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
