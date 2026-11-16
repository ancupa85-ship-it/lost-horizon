"""Perfil IES del faro del camión (tanda 26): el haz de cruce de un camión de 1983, escrito por nosotros.

Un .ies es un archivo de texto (norma IESNA LM-63) con una tabla de candelas: cuánta luz sale en cada dirección.
Unreal lo importa como perfil de luz y lo usa de máscara de un foco: el dibujo del haz en el asfalto sale del perfil, y
los lúmenes los sigue poniendo el director (TruckLampLumens), así que el sigilo no cambia.

El haz (faro de dos filamentos con bombilla incandescente, cruce europeo para circular por la derecha):
  - una mancha ancha y baja delante del camión, con el punto más fuerte algo por debajo del horizonte y un poco a la derecha;
  - corte por arriba: a la izquierda, plano y justo bajo el horizonte (no deslumbra al que viene); a la derecha sube en
    cuña de 15 grados (alumbra el arcén y las señales). El corte es blando, como en un faro de 1983, no una raya;
  - algo de luz perdida por encima del corte: el cristal estriado nunca cortaba del todo.

Se ejecuta fuera de Unreal y no necesita nada más que Python:
    python3 tools/unreal/ies.py                 escribe assets/unreal/luces/faro_cruce.ies
    python3 tools/unreal/ies.py --comprobar     lo vuelve a leer y comprueba la forma del haz
    python3 tools/unreal/ies.py --pgm X.pgm     además, deja una imagen del haz contra una pared (para mirarlo)

Ejes del perfil (fotometría de tipo C): el ángulo vertical se cuenta desde el eje del faro (0 = justo al frente) y el
horizontal gira alrededor de ese eje: aquí 0 = hacia la derecha del camión y 90 = hacia arriba. Qué giro del foco pone
«arriba» arriba en Unreal se comprueba en el PC con una captura contra el muro (el foco se rueda de 90 en 90 grados).
"""
import math
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SALIDA = os.path.join(RAIZ, 'assets', 'unreal', 'luces', 'faro_cruce.ies')

PICO_CD = 11000.0          # candelas en el punto más fuerte (un cruce de 40/45 W de la época)
PASO_V, MAX_V = 1.0, 90.0  # ángulo desde el eje: de 0 a 90 grados
PASO_H = 5.0               # alrededor del eje: de 0 a 360 grados

# corte: grados sobre el eje en los que la luz se acaba. A la izquierda plano; a la derecha sube en cuña
CORTE_IZQ = -0.6
CUNA_GRADOS = 15.0
CORTE_MAX = 4.0
CORTE_BLANDO = (-0.8, 1.8)   # desde cuánto por debajo hasta cuánto por encima del corte se va apagando
LUZ_PERDIDA = 0.018          # lo que escapa por encima del corte, sobre el pico


def _campana(x, centro, ancho):
    return math.exp(-0.5 * ((x - centro) / ancho) ** 2)


def _escalon(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def corte(lado):
    """Altura del corte (grados) según el ángulo a los lados (derecha positivo)."""
    if lado <= 0.0:
        return CORTE_IZQ
    return min(CORTE_MAX, CORTE_IZQ + math.tan(math.radians(CUNA_GRADOS)) * lado)


def haz(lado, alto):
    """Luz relativa (0-1) en una dirección: «lado» grados a la derecha del eje y «alto» grados por encima."""
    punto = _campana(lado, 1.5, 9.0) * _campana(alto, -2.5, 2.2)             # el punto fuerte
    mancha = 0.35 * _campana(lado, 0.0, 24.0) * _campana(alto, -6.0, 5.0)    # la mancha ancha
    cerca = 0.12 * _campana(lado, 0.0, 32.0) * _campana(alto, -15.0, 8.0)    # lo de justo delante del morro
    c = corte(lado)
    tapa = 1.0 - _escalon(c + CORTE_BLANDO[0], c + CORTE_BLANDO[1], alto)
    perdida = LUZ_PERDIDA * _campana(lado, 0.0, 30.0) * _campana(alto, 2.0, 12.0)
    return (punto + mancha + cerca) * tapa + perdida


def _angulos(paso, tope):
    n = int(round(tope / paso))
    return [round(i * paso, 4) for i in range(n + 1)]


def tabla():
    """(verticales, horizontales, candelas[horizontal][vertical]) del perfil."""
    vs, hs = _angulos(PASO_V, MAX_V), _angulos(PASO_H, 360.0)
    filas = []
    for h in hs:
        fila = []
        for v in vs:
            t, f = math.radians(v), math.radians(h)
            # dirección: x al frente, y a la derecha, z arriba
            x, y, z = math.cos(t), math.sin(t) * math.cos(f), math.sin(t) * math.sin(f)
            lado = math.degrees(math.atan2(y, x))
            alto = math.degrees(math.asin(max(-1.0, min(1.0, z))))
            fila.append(haz(lado, alto) if x > 1e-6 else 0.0)
        filas.append(fila)
    pico = max(max(f) for f in filas)
    return vs, hs, [[PICO_CD * c / pico for c in f] for f in filas]


def _renglones(valores, formato, por_linea=12):
    out = []
    for i in range(0, len(valores), por_linea):
        out.append(' '.join(formato % v for v in valores[i:i + por_linea]))
    return out


def texto():
    vs, hs, cd = tabla()
    lineas = [
        'IESNA:LM-63-1995',
        '[TEST] Lost Horizon - faro de cruce, perfil calculado (no medido)',
        '[MANUFAC] Lost Horizon',
        '[LUMCAT] faro_cruce',
        '[LUMINAIRE] Faro de camion de 1983, cruce europeo',
        '[LAMP] incandescente de dos filamentos 40/45 W',
        'TILT=NONE',
        # lámparas, lúmenes por lámpara (-1: la tabla manda), factor, n.º de verticales, n.º de horizontales,
        # fotometría de tipo C (1), unidades en metros (2), ancho, largo y alto de la boca (un faro de 18 cm)
        '1 -1 1 %d %d 1 2 0.18 0.00 0.18' % (len(vs), len(hs)),
        '1 1 45',
    ]
    lineas += _renglones(vs, '%g')
    lineas += _renglones(hs, '%g')
    for fila in cd:
        lineas += _renglones(fila, '%.1f')
    return '\r\n'.join(lineas) + '\r\n'


def leer(ruta):
    """Lee un .ies de tipo C y devuelve (verticales, horizontales, candelas[horizontal][vertical])."""
    with open(ruta, encoding='ascii') as f:
        crudo = f.read().splitlines()
    i = next(k for k, l in enumerate(crudo) if l.startswith('TILT='))
    nums = [float(x) for l in crudo[i + 1:] for x in l.split()]
    nv, nh = int(nums[3]), int(nums[4])
    p = 13
    vs, hs = nums[p:p + nv], nums[p + nv:p + nv + nh]
    p += nv + nh
    cd = [nums[p + k * nv:p + (k + 1) * nv] for k in range(nh)]
    if len(nums) != p + nv * nh:
        raise ValueError('sobran o faltan números: %d frente a %d' % (len(nums), p + nv * nh))
    return vs, hs, cd


def mirar(vs, hs, cd, lado, alto):
    """Candelas del perfil leído en una dirección (el valor de la casilla más cercana)."""
    x = math.cos(math.radians(alto)) * math.cos(math.radians(lado))
    y = math.cos(math.radians(alto)) * math.sin(math.radians(lado))
    z = math.sin(math.radians(alto))
    v = math.degrees(math.acos(max(-1.0, min(1.0, x))))
    h = math.degrees(math.atan2(z, y)) % 360.0
    iv = min(range(len(vs)), key=lambda k: abs(vs[k] - v))
    ih = min(range(len(hs)), key=lambda k: abs(hs[k] - h))
    return cd[ih][iv]


def comprobar(ruta):
    vs, hs, cd = leer(ruta)
    pico = max(max(f) for f in cd)
    fallos = []

    def pide(nombre, bien, dato):
        print(('  bien  ' if bien else '  MAL   ') + nombre + ': ' + dato)
        if not bien:
            fallos.append(nombre)

    pide('tabla completa', len(vs) == 91 and len(hs) == 73 and vs[0] == 0 and vs[-1] == 90 and hs[-1] == 360,
         '%d verticales x %d horizontales' % (len(vs), len(hs)))
    pide('el pico es el pedido', abs(pico - PICO_CD) < 1.0, '%.0f cd' % pico)
    fuerte = mirar(vs, hs, cd, 1.5, -2.5)
    pide('el punto fuerte está bajo el horizonte y algo a la derecha', fuerte > 0.8 * pico, '%.0f cd' % fuerte)
    izq, der = mirar(vs, hs, cd, -8.0, 1.5), mirar(vs, hs, cd, 8.0, 1.5)
    pide('la cuña: a 1,5 grados sobre el eje hay luz a la derecha y no a la izquierda', der > 4.0 * izq and izq < 0.08 * pico,
         'derecha %.0f cd, izquierda %.0f cd' % (der, izq))
    arriba = max(mirar(vs, hs, cd, a, 8.0) for a in range(-40, 41, 5))
    pide('por encima del corte solo queda luz perdida', arriba < 0.05 * pico, '%.0f cd a 8 grados' % arriba)
    abajo = mirar(vs, hs, cd, 0.0, -15.0)
    pide('delante del morro hay algo de luz', 0.03 * pico < abajo < 0.4 * pico, '%.0f cd a -15 grados' % abajo)
    ancho = mirar(vs, hs, cd, 25.0, -6.0)
    pide('la mancha es ancha', ancho > 0.08 * pico, '%.0f cd a 25 grados a la derecha' % ancho)
    atras = max(f[-1] for f in cd)
    pide('nada hacia los lados del todo', atras < 0.002 * pico, '%.1f cd a 90 grados del eje' % atras)
    cierra = max(abs(a - b) for a, b in zip(cd[0], cd[-1]))
    pide('la vuelta cierra (0 y 360 iguales)', cierra < 0.11, '%.2f cd' % cierra)
    return not fallos


def pgm(ruta, lados=45.0, altos=(-25.0, 12.0), px=8):
    """El haz contra una pared, en grises: cada píxel es 1/px de grado. Solo para mirarlo."""
    ancho, alto = int(2 * lados * px), int((altos[1] - altos[0]) * px)
    datos = bytearray()
    for j in range(alto):
        e = altos[1] - j / px
        for i in range(ancho):
            a = -lados + i / px
            datos.append(int(255 * min(1.0, haz(a, e)) ** 0.45))
    with open(ruta, 'wb') as f:
        f.write(b'P5 %d %d 255\n' % (ancho, alto))
        f.write(bytes(datos))


if __name__ == '__main__':
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, 'w', encoding='ascii', newline='') as f:
        f.write(texto())
    print('escrito', os.path.relpath(SALIDA, RAIZ), os.path.getsize(SALIDA), 'bytes')
    if '--pgm' in sys.argv:
        destino = sys.argv[sys.argv.index('--pgm') + 1]
        pgm(destino)
        print('imagen del haz en', destino)
    if '--comprobar' in sys.argv:
        sys.exit(0 if comprobar(SALIDA) else 1)
