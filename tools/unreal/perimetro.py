"""Piezas de juego del perímetro nuevo (tanda 20) que no vienen en base.glb.

Se ejecuta en el editor con el nivel Tarsis abierto:  py tools/unreal/perimetro.py
- Tope_Salida: pared invisible fuera del portón de salida (1 x 8 x 4 m, centrada en 9280, 5700, 200) para que nadie
  se vaya andando por el terraplén sin acabar la misión. El punto de salida del director (ExitLoc 9050, 5700, radio
  420) queda antes del tope: con el expediente la misión acaba al llegar; sin él, sale el aviso y el tope para.
- Tope_Entrada (tanda 21): lo mismo por fuera del portón de entrada (-2010, 5700, 200), que ahora se abre para el
  camión. El camión los atraviesa (el director lo mueve sin barrido); el jugador y los guardias, no.
- Manchas del camino y del anillo (tanda 22): calcomanías con el material M_Mancha de ambiente.py. Rodadas por donde
  pisan las ruedas del camión, goterones de aceite donde se para (ante el portón y en el control) y a lo largo del
  carril, barro que mete por la entrada, cercos de humedad junto a los bordillos y al pie del muro. Etiqueta
  «mancha_perimetro».
Se puede ejecutar varias veces: borra lo que puso antes (por su etiqueta) y lo vuelve a poner.
"""
import os, sys, random
import unreal

V = unreal.Vector
CUBO = '/Engine/BasicShapes/Cube.Cube'   # 100 cm de lado
CARPETA = 'Perimetro'


def log(*a):
    unreal.log('[Tarsis] ' + ' '.join(str(x) for x in a))


def tope(nombre, x):
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.actor_has_tag(nombre):
            eas.destroy_actor(a)
    a = eas.spawn_actor_from_class(unreal.StaticMeshActor, V(x, 5700, 200), unreal.Rotator(0, 0, 0))
    a.set_actor_label(nombre)
    a.set_folder_path(CARPETA)
    a.tags = [unreal.Name(nombre)]
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset(CUBO))
    a.set_actor_scale3d(V(1.0, 8.0, 4.0))
    c.set_collision_profile_name('BlockAll')
    c.set_cast_shadow(False)
    c.set_editor_property('can_ever_affect_navigation', False)
    a.set_actor_hidden_in_game(True)
    log(nombre, 'en', a.get_actor_location())
    return a


def tope_salida():
    return tope('Tope_Salida', 9280)


def tope_entrada():
    # tanda 21: el portón de entrada se abre cuando llega el camión; el tope queda justo por fuera de los pilares
    return tope('Tope_Entrada', -2010)


# ---------------------------------------------------------------- manchas (tanda 22)
MANCHA_TAG = 'mancha_perimetro'
# tipo -> (color lineal, fuerza). Una instancia por tipo (no por mancha): el dibujo de cada una sale del ruido del mundo
TIPOS = {
    'Rodada': ((0.028, 0.027, 0.026), 0.6),     # goma y polvo por donde pisan las ruedas (0.42 antes de premultiplicar M_Mancha)
    'Aceite': ((0.010, 0.009, 0.008), 0.9),
    'Barro': ((0.075, 0.058, 0.036), 0.62),
    'Charco': ((0.02, 0.02, 0.019), 0.6),       # cerco oscuro de agua junto al bordillo
    'Humedad': ((0.05, 0.045, 0.036), 0.72),    # pie del muro
}
CAMINO_Y, RUEDA = 5700.0, 86.0       # eje del camino y media vía del camión (cm)
LOSA_Z = 4.0


def _tipos():
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import ambiente
    base = ambiente.material_mancha()
    eal = unreal.EditorAssetLibrary
    mel = unreal.MaterialEditingLibrary
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    out = {}
    for tipo, (col, fuerza) in TIPOS.items():
        ruta = '/Game/Tarsis/Materiales/Manchas/MI_Per_' + tipo
        mi = unreal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset(
            'MI_Per_' + tipo, '/Game/Tarsis/Materiales/Manchas', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, base)
        mel.set_material_instance_scalar_parameter_value(mi, 'Fuerza', fuerza)
        mel.set_material_instance_vector_parameter_value(mi, 'Color', unreal.LinearColor(col[0], col[1], col[2], 1))
        eal.save_loaded_asset(mi)
        out[tipo] = mi
    return out


def manchas():
    """Calcomanías del camino y del pie del muro. En el suelo: ancho = a lo ancho del camino (Y), largo = a lo largo (X)."""
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in eas.get_all_level_actors():
        if a.actor_has_tag(MANCHA_TAG):
            eas.destroy_actor(a)
    mis = _tipos()
    rs = random.Random(2222)
    n = [0]
    def calco(tipo, pos, ancho, largo, hacia='abajo', giro=0.0, fondo=9.0):
        # fondo corto en el suelo: la mancha coge la losa (z 4) y el terraplén (z -2), no las botas de quien la pisa
        # unreal.Rotator(roll, pitch, yaw). En el suelo la calcomanía mira hacia abajo; en un muro, hacia el yaw «hacia»
        rot = unreal.Rotator(0, -90, giro) if hacia == 'abajo' else unreal.Rotator(giro, 0, hacia)
        a = eas.spawn_actor_from_class(unreal.DecalActor, pos, rot)
        n[0] += 1
        a.set_actor_label('Mancha_%s_%02d' % (tipo, n[0]))
        a.set_folder_path(CARPETA)
        a.tags = [unreal.Name(MANCHA_TAG)]
        a.decal.set_decal_material(mis[tipo])
        a.decal.set_editor_property('decal_size', V(fondo, ancho / 2.0, largo / 2.0))
        return a
    # rodadas: dos carriles a tramos, desde fuera del portón de entrada hasta pasado el de salida
    for lado in (-1, 1):
        x = -3000.0 + rs.uniform(0, 300)
        while x < 10100.0:
            L = rs.uniform(1400, 2600)
            calco('Rodada', V(x + L / 2, CAMINO_Y + lado * RUEDA + rs.uniform(-8, 8), LOSA_Z), rs.uniform(46, 68), L)
            x += L + rs.uniform(150, 600)
    # aceite: donde el camión espera con el motor en marcha (ante el portón y en el control) y goterones por el carril
    for x, a, l in ((-2300, 95, 120), (-2260, 40, 45), (8390, 110, 140), (8440, 45, 50), (8330, 35, 40)):
        calco('Aceite', V(x + rs.uniform(-15, 15), CAMINO_Y + rs.uniform(-18, 18), LOSA_Z), a, l, giro=rs.uniform(-30, 30))
    for k in range(7):
        t = rs.uniform(30, 62)
        calco('Aceite', V(rs.uniform(-1500, 8000), CAMINO_Y + rs.uniform(-28, 28), LOSA_Z), t, t * rs.uniform(1.0, 1.8), giro=rs.uniform(-20, 20))
    # barro que traen las ruedas de la marisma: se va perdiendo en los primeros metros
    for x, lado in ((-1720, -1), (-1560, 1), (-1250, -1), (-980, 1)):
        calco('Barro', V(x, CAMINO_Y + lado * RUEDA + rs.uniform(-12, 12), LOSA_Z), rs.uniform(60, 90), rs.uniform(170, 300))
    # cercos de agua junto a los bordillos
    for k in range(6):
        lado = -1 if k % 2 else 1
        calco('Charco', V(rs.uniform(-1500, 8800), CAMINO_Y + lado * rs.uniform(255, 285), LOSA_Z), rs.uniform(60, 95), rs.uniform(130, 240), giro=rs.uniform(-8, 8))
    # humedad al pie del muro por dentro (cara de dentro: oeste -1855, este 9055, sur 7455): lo que se ve desde el camino y el anillo sur
    x = -1650.0
    while x < 8900.0:
        L = rs.uniform(380, 720)
        if not (100 < x + L / 2 < 520):      # el portillo de la marisma
            calco('Humedad', V(x + L / 2, 7455, rs.uniform(35, 60)), L, rs.uniform(100, 160), hacia=90, fondo=22.0)
        x += L + rs.uniform(350, 900)
    for xm, yaw in ((-1855, 180), (9055, 0)):
        for y in (4350, 4900, 6950, 7300):   # a los dos lados del portón, fuera del carril de la hoja
            calco('Humedad', V(xm, y + rs.uniform(-80, 80), rs.uniform(35, 60)), rs.uniform(300, 480), rs.uniform(100, 150), hacia=yaw, fondo=22.0)
    log('manchas del perímetro:', n[0])
    return n[0]


def todo():
    tope_salida()
    tope_entrada()
    try:
        manchas()
    except Exception as e:
        log('AVISO: manchas del perímetro no puestas:', repr(e))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


if __name__ == '__main__':
    todo()
