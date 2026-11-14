"""Materiales físicos de las superficies de Tarsis: de ellos salen el sonido de los pasos y lo lejos que se oyen.

Crea PM_Grava, PM_Cemento, PM_Metal, PM_Madera y PM_Hierba en /Game/Tarsis/Fisica y se los pone a los materiales de la
base (MI_<clave> de materiales.py y lh_<clave> importados) según su nombre. Las mallas de la base usan su malla como
colisión (complex as simple), así que el trazo de los pasos devuelve el material físico del triángulo pisado.
ATarsisDirector::SurfaceAt lee el nombre del material físico (PM_*); si un material no tiene, mira el nombre de la malla
y el de sus materiales con las mismas palabras de abajo.
Uso: en el editor (montar_base.py lo llama después de materiales.py), o suelto: py tools/unreal/superficies.py
"""
import unreal

DEST = '/Game/Tarsis/Fisica'
eal = unreal.EditorAssetLibrary

# superficie -> palabras del nombre del material (en el orden en que se prueban, como en el C++)
SUPERFICIES = (
    ('Madera', ('madera', 'veta', 'wood')),
    ('Metal', ('hierro', 'metal', 'tejado', 'contenedor', 'oliva', 'chapa')),
    ('Hierba', ('hierba', 'cesped', 'marisma', 'grass')),
    ('Cemento', ('suelo_int', 'hormigon', 'cemento', 'muro', 'pared', 'camino')),
    ('Grava', ('suelo', 'grava', 'tierra')),
)
# rozamiento: la chapa y el cemento pulido resbalan algo más que la grava o la hierba (no afecta al personaje)
FRICCION = {'Grava': 0.9, 'Cemento': 0.7, 'Metal': 0.5, 'Madera': 0.65, 'Hierba': 0.8}

def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))

def fisicos():
    out = {}
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for nombre, _ in SUPERFICIES:
        ruta = DEST + '/PM_' + nombre
        pm = eal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset('PM_' + nombre, DEST, unreal.PhysicalMaterial, unreal.PhysicalMaterialFactoryNew())
        pm.set_editor_property('friction', FRICCION[nombre])
        eal.save_loaded_asset(pm)
        out[nombre] = pm
    return out

def superficie(nombre_material):
    n = nombre_material.lower()
    for sup, palabras in SUPERFICIES:
        if any(p in n for p in palabras):
            return sup
    return None

def aplicar():
    pms = fisicos()
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    n = 0
    for a in ar.get_assets_by_path('/Game/Tarsis', recursive=True):
        clase = str(a.asset_class_path.asset_name)
        if clase not in ('Material', 'MaterialInstanceConstant'):
            continue
        nombre = str(a.asset_name)
        if not (nombre.startswith('MI_') or nombre.startswith('lh_')):
            continue
        sup = superficie(nombre)
        if not sup:
            continue
        m = a.get_asset()
        try:
            if m.get_editor_property('phys_material') != pms[sup]:
                m.set_editor_property('phys_material', pms[sup])
                eal.save_loaded_asset(m)
            n += 1
        except Exception as e:
            log('AVISO: no se pudo poner el material físico a', nombre, repr(e))
    log('superficies: materiales físicos en', n, 'materiales')
    return n

if __name__ == '__main__':
    aplicar()
