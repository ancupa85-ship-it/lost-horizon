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
- Tanda 23: charcos de verdad (M_Charco: agua quieta que refleja las farolas y el cielo) junto a cada farola del camino
  y de la base, en los cercos de los bordillos y en la grava del anillo; con lluvia salen más (etiqueta «lluvia»: los
  enciende y apaga el director). Regueros de humedad que bajan por la cara de dentro del muro y por las garitas
  (M_Chorreton) y juntas de la losa que rezuman. Todo con la etiqueta «mancha_perimetro».
Se puede ejecutar varias veces: borra lo que puso antes (por su etiqueta) y lo vuelve a poner.
"""
import os, sys, json, random
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
# tanda 23. tipo -> (material: 'mancha', 'charco' o 'chorreton'; color lineal; fuerza; resto de parámetros de la instancia)
TIPOS_23 = {
    # tanda 24: el charco lleva cerco húmedo (Cerco, RugosidadCerco) y el agua deja ver algo del fondo (Fondo)
    'Agua': ('charco', (0.012, 0.012, 0.011), 1.0, {'Rugosidad': 0.05, 'Fondo': 0.9, 'Cerco': 0.5, 'RugosidadCerco': 0.32}),       # charco en la losa o el asfalto
    'AguaBarro': ('charco', (0.03, 0.024, 0.015), 1.0, {'Rugosidad': 0.09, 'Fondo': 0.95, 'Cerco': 0.6, 'RugosidadCerco': 0.4}),  # agua turbia en la grava del anillo
    # tanda 24: regueros más marcados (más oscuros, hilos más finos, más tramos y la franja húmeda bajo la coronación)
    'Chorreton': ('chorreton', (0.018, 0.016, 0.013), 1.0, {'Techo': 462.0, 'Largo': 300.0, 'Contraste': 2.6, 'Grupos': 0.30, 'Franja': 0.6}),          # muro de 4,6 m
    'ChorretonGarita': ('chorreton', (0.018, 0.016, 0.013), 0.95, {'Techo': 251.0, 'Largo': 140.0, 'Contraste': 2.6, 'Grupos': 0.26, 'Franja': 0.5}),   # garitas de 2,5 m
    'Junta': ('mancha', (0.022, 0.021, 0.02), 0.5, {}),                              # junta de la losa que rezuma
}
MURO_ALTO = 460.0
# farolas del camino y faroles de los dos portones (x, y de la luminaria, en cm): los charcos de al lado las reflejan
FAROLAS_CAMINO = ((1070, 5770), (3600, 5770), (6130, 5770), (-1460, 5640), (8660, 5640))


def _tipos():
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import ambiente, importlib
    importlib.reload(ambiente)   # en la misma sesión del editor, que coja los cambios de ambiente.py (CHARCO_NORMAL...)
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
    bases = {'mancha': base}
    for tipo, (mat, col, fuerza, resto) in TIPOS_23.items():
        if mat not in bases:
            bases[mat] = ambiente.material_charco() if mat == 'charco' else ambiente.material_chorreton()
        ruta = '/Game/Tarsis/Materiales/Manchas/MI_Per_' + tipo
        mi = unreal.load_asset(ruta) if eal.does_asset_exist(ruta) else tools.create_asset(
            'MI_Per_' + tipo, '/Game/Tarsis/Materiales/Manchas', unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(mi, bases[mat])
        mel.set_material_instance_scalar_parameter_value(mi, 'Fuerza', fuerza)
        mel.set_material_instance_vector_parameter_value(mi, 'Color', unreal.LinearColor(col[0], col[1], col[2], 1))
        for k, v in resto.items():
            mel.set_material_instance_scalar_parameter_value(mi, k, v)
        eal.save_loaded_asset(mi)
        out[tipo] = mi
    return out


def _plano():
    """El plano de la base (assets/unreal/base.json): filas de casillas de 2 m; '.' es suelo libre."""
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    j = json.load(open(os.path.join(raiz, 'assets', 'unreal', 'base.json')))
    return j['map'], j.get('T', 2.0) * 100.0, j


def _despejada(mapa, cx, cy):
    """La casilla y las ocho de alrededor son suelo libre: cabe un charco de dos metros sin meterse bajo nada."""
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            y, x = cy + dy, cx + dx
            if not (0 <= y < len(mapa) and 0 <= x < len(mapa[y]) and mapa[y][x] == '.'):
                return False
    return True


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
    cercos = []
    for k in range(6):
        lado = -1 if k % 2 else 1
        q = (V(rs.uniform(-1500, 8800), CAMINO_Y + lado * rs.uniform(255, 285), LOSA_Z), rs.uniform(60, 95), rs.uniform(130, 240), rs.uniform(-8, 8))
        calco('Charco', q[0], q[1], q[2], giro=q[3]); cercos.append(q)
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
    n22 = n[0]
    # ------------------------------------------------------------ tanda 23 (otra semilla: lo de la 22 no se mueve)
    r3 = random.Random(2323)
    def agua(tipo, pos, ancho, largo, giro=0.0, lluvia=False):
        a = calco(tipo, pos, ancho, largo, giro=giro)
        a.decal.set_editor_property('sort_order', 2)          # el agua, por encima de las manchas mates
        if lluvia:
            a.tags = [unreal.Name(MANCHA_TAG), unreal.Name('lluvia')]
        return a
    cuenta = {'agua': 0, 'lluvia': 0, 'muro': 0, 'junta': 0}
    # 1) camino: un charco o dos al lado de cada farola (no debajo: desde el camino se ve la luminaria reflejada en el
    #    agua), agua en cuatro de los cercos de los bordillos y, solo con lluvia, en las rodadas y por la losa
    for lx, ly in FAROLAS_CAMINO:
        for k in range(r3.choice((1, 2))):
            lado = r3.choice((-1, 1))
            agua('Agua', V(lx + lado * r3.uniform(170, 390), CAMINO_Y + r3.uniform(-215, 215), LOSA_Z), r3.uniform(110, 210), r3.uniform(160, 330), r3.uniform(-25, 25))
            cuenta['agua'] += 1
    for pos, an, la, gi in r3.sample(cercos, 4):
        agua('Agua', pos, an * 0.75, la * 0.8, gi); cuenta['agua'] += 1
    for k in range(4):
        agua('Agua', V(r3.uniform(-1300, 8200), CAMINO_Y + r3.choice((-1, 1)) * RUEDA + r3.uniform(-10, 10), LOSA_Z), r3.uniform(55, 80), r3.uniform(220, 420), r3.uniform(-4, 4), lluvia=True)
    for k in range(6):
        agua('Agua', V(r3.uniform(-1600, 8700), CAMINO_Y + r3.uniform(-240, 240), LOSA_Z), r3.uniform(90, 190), r3.uniform(120, 300), r3.uniform(-40, 40), lluvia=True)
    cuenta['lluvia'] += 10
    # 2) grava del anillo sur y de los dos portones: charcos grandes y turbios (tres fijos; con lluvia, cuatro más)
    for k in range(7):
        agua('AguaBarro', V(r3.uniform(-1300, 8500), r3.uniform(6260, 7230), 1.0), r3.uniform(180, 340), r3.uniform(230, 430), r3.uniform(0, 180), lluvia=k >= 3)
        cuenta['lluvia' if k >= 3 else 'agua'] += 1
    # 3) patios de la base: un charco junto a cada farola (en una casilla despejada) y, con lluvia, ocho más repartidos
    datos = {}
    try:
        mapa, T, datos = _plano()
        puestos = []
        for l in datos.get('lights', []):
            if l.get('name') != 'farola':
                continue
            fx, fy = int(l['pos'][0] * 100.0 // T), int(-l['pos'][1] * 100.0 // T)
            if not (0 <= fy < len(mapa) and 0 <= fx < len(mapa[0])):
                continue          # las del camino ya tienen los suyos
            cand = [(fx + dx, fy + dy) for dx in range(-2, 3) for dy in range(-2, 3) if max(abs(dx), abs(dy)) >= 1 and _despejada(mapa, fx + dx, fy + dy)]
            if cand:
                cx, cy = r3.choice(cand); puestos.append((cx, cy))
                agua('Agua', V((cx + 0.5) * T + r3.uniform(-40, 40), (cy + 0.5) * T + r3.uniform(-40, 40), 2.0), r3.uniform(130, 230), r3.uniform(150, 260), r3.uniform(0, 180))
                cuenta['agua'] += 1
        libres = [(x, y) for y in range(len(mapa)) for x in range(len(mapa[y])) if _despejada(mapa, x, y)]
        r3.shuffle(libres)
        k = 0
        for cx, cy in libres:
            if k >= 8:
                break
            if any(max(abs(cx - a), abs(cy - b)) < 4 for a, b in puestos):
                continue
            puestos.append((cx, cy)); k += 1
            agua('Agua', V((cx + 0.5) * T + r3.uniform(-50, 50), (cy + 0.5) * T + r3.uniform(-50, 50), 2.0), r3.uniform(120, 260), r3.uniform(140, 300), r3.uniform(0, 180), lluvia=True)
        cuenta['lluvia'] += k
    except Exception as e:
        log('AVISO: charcos de los patios no puestos:', repr(e))
    # 4) juntas de la losa que rezuman: una banda oscura a lo largo de alguna junta (cada 6 m, en x = 100 + 600 k)
    for xj in r3.sample(range(-1700, 8900, 600), 8):
        calco('Junta', V(xj + r3.uniform(-6, 6), CAMINO_Y + r3.uniform(-60, 60), LOSA_Z), r3.uniform(330, 560), r3.uniform(36, 70), giro=r3.uniform(-2, 2))
        cuenta['junta'] += 1
    # 5) regueros en el muro, por dentro (caras: oeste -1855, este 9055, sur 7455, norte -1855) y en las dos garitas.
    #    La caja coge el muro de arriba abajo; el dibujo lo pone el material con la posición en el mundo
    def muro(tipo, pos, ancho, alto, hacia):
        calco(tipo, pos, ancho, alto, hacia=hacia, fondo=22.0); cuenta['muro'] += 1
    zm = MURO_ALTO / 2.0
    for ym, yaw, salto in ((7455, 90, (100, 520)), (-1855, -90, None)):        # sur (con el portillo) y norte
        x = -1700.0 + r3.uniform(0, 300)
        while x < 8750.0:
            L = r3.uniform(420, 820)
            if not (salto and salto[0] < x + L / 2 < salto[1]):
                muro('Chorreton', V(x + L / 2, ym, zm), L, MURO_ALTO, yaw)
            x += L + r3.uniform(250, 700)
    for xm, yaw in ((-1855, 180), (9055, 0)):                                   # oeste y este, a los dos lados de cada portón
        for y in (-1200, -200, 900, 2000, 3100, 4100, 4850, 6950):
            L = r3.uniform(380, 640)
            muro('Chorreton', V(xm, y + r3.uniform(-120, 120), zm), L, MURO_ALTO, yaw)
    for key, s in (('entrada', 1), ('salida', -1)):                             # garitas: la cara del camino y la de la base
        g = datos.get('ext', {}).get(key, {}).get('garita')
        if not g:
            continue
        gx, gy = g[0] * 100.0, g[1] * 100.0
        muro('ChorretonGarita', V(gx + r3.uniform(-30, 30), gy + 120.0, 125.0), 210, 250, -90)
        muro('ChorretonGarita', V(gx + s * 120.0, gy + r3.uniform(-30, 30), 125.0), 210, 250, 180 if s > 0 else 0)
    log('manchas del perímetro:', n[0], '(tanda 22: %d; charcos fijos %d, con lluvia %d, regueros %d, juntas %d)' % (n22, cuenta['agua'], cuenta['lluvia'], cuenta['muro'], cuenta['junta']))
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
