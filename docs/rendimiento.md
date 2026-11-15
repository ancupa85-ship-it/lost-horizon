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

## 0019: barracón lleno (literas, baúles, techo, luz de ventana, calcomanías de lluvia)

Medido con `tools/unreal/medir.py` (calidad Media, ventana 1080p del PIE, guardias quietos), con el editor recién
abierto, dos pasadas (medio / peor 1 %). VRAM de toda la tarjeta con el editor abierto (nvidia-smi).

| Sitio | Pasada 1 | Pasada 2 | VRAM (MB) |
|---|---|---|---|
| Entrada | 34,7 / 26,2 | 34,9 / 30,6 | 3784 / 3712 |
| Patio central | 34,3 / 32,8 | 32,3 / 29,8 | 3784 / 3712 |
| Barracón oeste | 30,6 / 28,4 | 29,7 / 27,4 | 3784 / 3712 |

Antes de recortar, el barracón daba 28,7 y 30,3 fps (editor recién abierto) y 28,0–28,5 con el editor cargado.
Comparación dentro de una misma sesión (barracón oeste, fps medios):

| Cambio | fps |
|---|---|
| Todo | 28,4 |
| Fluorescente sin sombra | 30,3 |
| Sin las dos luces de ventana | 29,1 |
| Flexo sin sombra | 28,9 |
| Sin el atrezo | 29,5 |
| Sin el techo (cerchas, correas, pantallas, chimenea) | 29,2 |
| Sin manchas, charco y pisadas | 29,0 |
| Sombra del fluorescente a media resolución | sin cambio |
| Sin niebla volumétrica / Lumen con menos sondas | sin cambio |

Qué se quitó:
- **La sombra del fluorescente** (1,3–1,9 fps): con cerchas, literas y baúles debajo era lo más caro. La sombra dura
  dentro la pone el flexo; Lumen sigue oscureciendo bajo las literas.
- **Radio de las luces de ventana de 520 a 400 cm** (la función de luz de los barrotes se calcula en menos pantalla;
  el haz llega al suelo a 2,8 m, no se ve diferencia).

El barracón queda justo en el límite de 30 fps de media con el editor abierto; la VRAM, por debajo de 3,8 GB salvo
algún pico de 3823 MB en la primera medida tras abrir el editor (texturas aún cargándose).

## 0020: muro 20 m más afuera, portones y camino

`tools/unreal/medir.py` con los dos sitios nuevos (portón de entrada desde dentro, -600 5850, y portón de salida, 7600
5860), calidad Media, editor recién abierto, dos pasadas (medio / peor 1 %):

| Sitio | Pasada 1 | Pasada 2 | VRAM (MB) |
|---|---|---|---|
| Entrada | 38,7 / 35,1 | 38,1 / 33,2 | 3821 / 3743 |
| Patio central | 37,9 / 34,4 | 37,0 / 32,4 | 3821 / 3743 |
| Barracón oeste | 33,3 / 29,3 | 31,7 / 28,5 | 3893 / 3743 |
| Portón de entrada | 40,4 / 38,7 | 38,9 / 33,3 | 3890 / 3744 |
| Portón de salida | 41,6 / 38,5 | 41,0 / 36,0 | 3889 / 3743 |

El anillo nuevo no baja nada de 30 fps; los portones son lo más ligero (poca geometría a la vista). La VRAM (toda la
tarjeta, con el editor abierto) pasa de 3,8 GB en la primera medida tras abrir el editor (3893 MB) y vuelve a 3,74 en la
segunda: la grava nueva (gravel_floor_02 a 2K) suma; si hiciera falta, bajarla a 1K.

## 0021: farolas, malla de las vallas, guardias del anillo y camión

`tools/unreal/medir.py` con un sitio más (el camión entrando por el portón con los faros hacia la cámara, jugador en
1500 6150), calidad Media, una pasada (medio / peor 1 %):

| Sitio | fps | VRAM (MB) |
|---|---|---|
| Entrada | 40,0 / 37,1 | 3769 |
| Patio central | 39,4 / 37,4 | 3650 |
| Barracón oeste | 32,7 / 30,4 | 3780 |
| Portón de entrada | 40,8 / 37,9 | 3780 |
| Portón de salida | 42,1 / 39,0 | 3781 |
| Camino con el camión | 37,6 / 33,2 | 3782 |

Las tres farolas (sin sombra), la malla recortada de las vallas (sin sombra propia) y los tres guardias nuevos no se
notan. Los faros del camión, que son la única luz nueva con sombra, cuestan unos 3 fps de media cuando viene de frente;
no hizo falta apagar su sombra (`bTruckShadows`). Con la grava a 1K la VRAM ya no pasa de 3,8 GB.

## 0022: camino gastado (juntas, rodadas, hierbajos) y viaje en la caja del camión

`tools/unreal/medir.py`, calidad Media, ventana 1080p del PIE, una pasada (medio / peor 1 %). VRAM de toda la tarjeta con
el editor abierto.

| Sitio | fps | VRAM (MB) |
|---|---|---|
| Entrada | 39,7 / 36,9 | 3734 |
| Patio central | 38,8 / 36,8 | 3606 |
| Barracón oeste | 33,3 / 31,4 | 3731 |
| Portón de entrada | 39,9 / 36,7 | 3731 |
| Portón de salida | 41,2 / 37,6 | 3731 |
| Camino con el camión | 36,6 / 33,8 | 3731 |

Igual que en la 0021 (dentro del margen de una medida a otra): los hierbajos (recortados, con viento), las 51
calcomanías del perímetro, la caja hueca y el material de las piezas móviles no se notan.

## 0023: agua en el suelo y los muros, caja del camión por dentro

`tools/unreal/medir.py` con el editor recién abierto, calidad Media, una pasada (medio / peor 1 %). **Ojo:** la ventana
del PIE es ahora de 2032x1125 (en la 0022 era 1080p), un 10 % más de píxeles; por eso las cifras no se comparan una a una
con la tabla anterior. VRAM de toda la tarjeta con el editor abierto.

| Sitio | fps | VRAM (MB) |
|---|---|---|
| Entrada | 31,1 / 12,5 | 3787 |
| Patio central | 34,7 / 28,8 | 3725 |
| Barracón oeste | 29,7 / 27,5 | 3803 |
| Portón de entrada | 36,1 / 30,7 | 3802 |
| Portón de salida | 35,3 / 32,0 | 3803 |
| Camino con el camión | 32,7 / 29,7 | 3840 |

El 12,5 de peor 1 % en la entrada es un tirón suelto al empezar (el primer sitio que se mide); en otra pasada fue 17,8.

Comparaciones A/B en la misma sesión (jugador en 1500 6150, mirando al camino; ventana 1080p):

- Las 88 calcomanías nuevas (charcos, regueros, juntas), ocultas o no: 36,7 / 37,1 sin ellas y 36,8 / 37,0 con ellas.
  No cuestan nada medible. (Antes del arreglo de mezclas, con alfa compuesto: 37,1 / 37,5 frente a 35,0 / 36,5).
- `RUIDO_RAPIDO` (ruido de textura 3D en los materiales del suelo) True frente a False: entre 33 y 38 fps en los dos
  casos, sin diferencia clara; se queda en True.

Mezclas de las calcomanías con Substrate (`r.Substrate=True`), probado en esta tanda:

- **Alfa compuesto** (lo de antes): el color se SUMA a lo de debajo. Las manchas oscuras casi no se ven y, si se conecta
  la rugosidad, se escribe en toda la caja (sale un rectángulo).
- **Modulado** (`BLEND_MODULATE`, en Substrate es la transmitancia de color sola): en calcomanía no multiplica, sino que
  mezcla el color con lo de debajo según la opacidad. Con un color absoluto oscuro y la máscara en la opacidad, oscurece
  solo dentro de la máscara: así quedan M_Mancha (v4) y M_Chorreton (v3).
- **Translúcido** (`BLEND_TRANSLUCENT`): escribe color, rugosidad y relieve dentro de la máscara. Es el del agua (M_Charco
  v4): oscuro, liso, y desde el ángulo bueno se ve el reflejo de la farola dentro del charco. El «Failed to compile» de
  antes era el orden: la mezcla tiene que ponerse ANTES que el dominio de calcomanía.

Memoria (`tools/unreal/memoria.py`, todo cargado): 292 texturas, 228,3 MB. Las 30 de más de 1K piden 91,4 MB; con un
tope de 1K se ahorrarían 64,1 MB. Hay 4 texturas que no usa nadie. Por carpetas: Atrezo 102 MB y Texturas 94,1 MB.

## 0024: puertas, lluvia que moja, carteles, cobertura, gestos y presupuesto de render

**La colisión de una malla Nanite es su malla de reserva.** `base_pared` lleva Nanite y colisión «compleja como simple».
La colisión compleja no sale de la malla Nanite, sino de su malla de reserva (la que se dibuja donde no hay Nanite), y con
el objetivo automático esa reserva se simplifica: los dinteles de tres puertas (archivo, despacho y barracón) bajaron de
2,20 m a entre 1,85 y 2,15 m y de pie no se pasaba. Arreglo: reserva con error relativo 0 en las mallas de estructura
(`base_*`). No se pone en todo: en los camiones la reserva pasaba de unos 1.200 a unos 30.000 triángulos por malla sin
arreglar nada.

**Presupuesto de render.** Las texturas no eran el problema (228 MB de 3,8 GB, tanda 23): lo que llena la tarjeta son los
búferes del render y el editor. `tools/unreal/render.py` prueba cada ajuste solo, en una partida limpia, contra la partida
sin tocar (memoria de toda la tarjeta con `nvidia-smi`, fps en tres sitios). Candidatos: páginas físicas de las sombras
virtuales (4096 → 2048), atlas de la caché de superficies de Lumen (4096 → 2048), reserva de transmisión de Nanite
(512 → 128 MB), tope de la reserva de texturas (400 MB), resolución interna al 80 % y niebla volumétrica con celdas más
gordas.

Medida de los candidatos (`render.py`, editor recién abierto, calidad Media, GTX 1050 de 4 GB; cada uno solo, en una
partida limpia, contra la partida sin tocar: 3021 a 3023 MB y unos 81 fps en los tres sitios de la medida):

| Candidato | Valor de serie en Media → probado | VRAM | fps |
|---|---|---|---|
| sombras | `r.Shadow.Virtual.MaxPhysicalPages` 512 → 2048 | +91 MB | −1,9 |
| lumen_cache | `r.LumenScene.SurfaceCache.AtlasSize` 4096 → 2048 | +82 MB | −5,2 (peor 1 % hasta 16) |
| nanite | `r.Nanite.Streaming.StreamingPoolSize` 512 → 128 | **−291 MB** | −1,0 |
| texturas | `r.Streaming.PoolSize` (ya valía 400: no pone nada) | +92 MB | −0,6 |
| resolucion | `r.ScreenPercentage` 50 → 80 | +95 MB | −30,8 |
| niebla | `GridPixelSize` 8 → 16, `GridSizeZ` 128 → 64 | +130 MB | −4,8 |
| todo | | −226 MB | −29 |

Lo que enseña la tabla:

- **La calidad Media ya venía por debajo de varios candidatos** (sombras con 512 páginas, pantalla al 50 %): ponerlos
  «más bajos» era subirlos. Los valores de serie que supuse eran los de calidad alta.
- **Cada partida después de la primera gasta unos 90 MB más sin tocar nada** («texturas» no pone ninguna variable y da
  +92 MB): las diferencias de menos de 100 MB de esta tabla son ruido de esa deriva, no del ajuste.
- **Solo la reserva de Nanite devuelve memoria de verdad** (−291 MB, casi sin coste). Es el único que queda aplicado
  (`render.aplicar(['nanite'])` lo escribe en el director del nivel y en `mision1.json`, para que no se pierda al volver
  a montar). La captura del patio antes y después es idéntica.
- Desde esta medida `render.py` repite la partida sin tocar al final y compara la memoria con esa, y mira al patio y no a
  una pared.
- **La resolución interna está al 50 %** con el reescalado temporal. Subirla al 80 % cuesta 31 fps en esta tarjeta: no
  se aplica. Es buena parte de por qué la imagen se ve blanda; queda como decisión de calidad para cuando haya tarjeta.

`medir.py` con el presupuesto aplicado, editor recién abierto, ventana 2032x1125 (medio / peor 1 %):

| Sitio | fps | VRAM (MB) |
|---|---|---|
| Entrada | 40,2 / 37,1 | 3668 |
| Patio central | 39,1 / 36,4 | 3540 |
| Barracón oeste | 33,6 / 30,7 | 3668 |
| Portón de entrada | 40,4 / 36,9 | 3668 |
| Portón de salida | 41,2 / 37,8 | 3669 |
| Camino con el camión | 36,8 / 33,2 | 3669 |

Frente a la 0023, con la misma ventana: entre 5 y 9 fps más y unos 120 MB menos, con 93 piezas de cobertura, 24 carteles
y el mojado de la lluvia añadidos.

## 0025: materia, noche con cielo, agua y señales

Compilación: 992 s, sin errores ni avisos. Batería: 336 de 336 (514 s, 34 pruebas en 15 familias).

Medida con el editor recién abierto (GTX 1050, Media, resolución interna al 50 %; fps medio / peor 1 %; entre paréntesis, la media de la 0024):

| Sitio | fps | VRAM (MB) |
|---|---|---|
| Entrada | 36,3 / 34,6 (40,2) | 3531 |
| Patio central | 30,9 / 9,6 (39,1) | 3531 |
| Barracón oeste | 33,0 / 31,0 (33,6) | 3596 |
| Portón de entrada | 38,3 / 35,9 (40,4) | 3596 |
| Portón de salida | 39,0 / 36,3 (41,2) | 3596 |
| Camino con el camión | 35,0 / 17,0 (36,8) | 3596 |

Lectura: la tanda cuesta de 2 a 4 fps en casi todo y unos 8 en el patio central, que es donde se ven a la vez más halos y el cielo entero. La memoria de vídeo baja entre 70 y 140 MB. Los peores 1 % del patio (9,6) y del camino (17,0) no valen: hubo entrada en el PC durante la medida y son tirones sueltos; hay que repetirlos. Lo que cuesta de más: los ruidos nuevos del material maestro (losas, manchas, regueros), nueve luces de relleno sin sombras y trece esferas translúcidas de halo. Pendiente: medir qué parte se lleva cada cosa en el patio central antes de recortar.
