# Rendimiento de Tarsis (Unreal 5.8)

Equipo: GTX 1050 Ti (4 GB), PIE en el editor con la ventana de 2032x1125 (la de 1920x1080 con el escalado de
Windows), calidad Media (`scalability 1`), sin límite de fps y con «usar menos CPU en segundo plano» apagado.
Mide `tools/unreal/medir.py`: 8 s de fotogramas en cada sitio, con los guardias quietos. VRAM: toda la tarjeta
(nvidia-smi), con el editor abierto.

## Tanda 18: el barracón oeste vestido (atrezo, luz, posprocesado, manchas, taquillas)

| Sitio | Antes: medio / peor 1 % | Después: medio / peor 1 % | VRAM antes / después |
|---|---|---|---|
| Entrada | 29,6 / 16,4 fps | 37,8–39,2 / 35,5 fps | 3746 / 3727–3757 MB |
| Patio central | 31,8 / 29,8 fps | 36,9–38,2 / 34,3–35,5 fps | 3730 / 3728–3749 MB |
| Barracón oeste | 26,7 / 25,1 fps | 30,2–32,9 / 27,9–30,5 fps | 3730 / 3728–3749 MB |

«Antes» y «después» se midieron con el editor recién abierto (dos medidas «después»), pero entre una sesión del
editor y otra la medida cambia mucho (±30 %): con el editor ya cargado de horas de PIE, los mismos «después» daban
26–27 / 25 / 23 fps. Por eso lo que vale para decidir es la comparación dentro de una misma sesión, quitando cada
cosa en el juego y midiendo enseguida:

| Dentro de una sesión (barracón oeste) | fps |
|---|---|
| Todo | 23,3 |
| Sin el atrezo | 23,5 |
| Luces nuevas sin sombra | 25,1 |
| Sin manchas (calcomanías) | 23,3 |
| Sin el posprocesado de la zona | 23,3 |
| Suciedad del material maestro: con / sin (entrada) | 27,2 / 27,3 |

- Las dos luces nuevas, como **puntuales** con sombra, costaban 3,2–3,7 fps dentro del barracón (la sombra de una luz
  puntual se calcula seis veces, una por cara del cubo). Como **focos** hacia abajo cuestan 1,8 fps: se quedan focos.
- El atrezo (19 modelos de Poly Haven con texturas de 1K y LOD), las manchas, el posprocesado de la zona y la
  suciedad del material maestro (ruido de textura, no de cálculo) no se notan.
- La VRAM ya estaba casi llena antes (3,7 de 4 GB con el editor): las texturas nuevas no la mueven.

Segunda pasada (colchones y mantas, estufa con su resplandor, flexo con sombra, cafetera, botas, cubo, archivador,
cuadrante, zócalo pintado y suelo mate; 42 piezas): 35,1 / 30,3 fps en la entrada, 34,4 / 31,8 en el patio central y
29,9 / 28,3 en el barracón oeste (medio / peor 1 %), con el editor ya cargado de la sesión.

## Luces horneadas o dinámicas

Las luces de la zona son **móviles** (dinámicas), con radio corto: fluorescente, lámpara de la puerta y flexo con sombra (focos), estufa sin ella. El apagón del generador y
el farol roto las apagan en juego, el fluorescente titila, y con dinámicas no hay que construir la iluminación
(Lightmass) cada vez que se toca el nivel. Lo que cuestan está medido arriba (1,8 fps) y no justifica hornear.
