# Lost Horizon: De Profundis

Misión 1 de *Project Lost Horizon* en primera/tercera persona: sigilo, acción, puzle e interrogatorio,
con estética cel-shading y puesta en escena tipo MGS2. Todo en JavaScript plano sobre Three.js r128,
sin empaquetador: se abre `index.html` y funciona.

## Jugar

```bash
npm start          # sirve la carpeta en http://localhost:8080
```
o simplemente abre `index.html` en Chrome/Firefox (el juego pide el ratón al hacer clic).

Controles: WASD mover · ratón mirar · Ctrl agacharse · Shift correr · E usar/hablar · F agarrar e interrogar / patada ·
C cargar cuerpo · clic disparar · X cambiar entre Cuttlas y Roig · V vista 1ª/3ª persona · Q fumar (8 s quieto, +2 vida) ·
Tab cuaderno · H guía · Esc pausa y opciones. El menú de inicio tiene "Cómo se juega", "Controles" y "Opciones".

## Estructura

```
index.html          maquetado de HUD, códec, diálogos y pantalla de inicio
css/style.css       estilos (fuentes pixel, letterbox, códec)
vendor/three.min.js Three.js r128 (MIT)
src/
  00-boot.js        comprobación del motor
  01-map.js         mapa de 36×28 casillas, leyenda y consultas (sólido, vista, sombra, interior)
  02-render.js      escena, materiales toon, texturas planas, luces, sombras, lluvia, postproceso de bordes
  03-figures.js     personajes de bloques con cara pixelada, perros, marcas ! y ?, brazos del jugador
  04-state.js       estado de partida, pistas, guardias, diálogos de interrogatorio, reset
  05-audio.js       sintetizador WebAudio (zumbido, sirena, ladridos, disparos)
  06-ui.js          avisos, cuaderno, diálogos, HUD
  07-codec.js       códec con retratos pixelados y texto mecanografiado; guiones
  08-input.js       teclado, ratón, pointer lock
  09-util.js        línea de visión, colisiones, visión de guardias, alarma
  10-actions.js     agarrar, interrogar, disparar, fumar, perros, captura, celda y cabo Vidal, teclado del archivo
  11-team.js        la compañera (Roig): sigue, se esconde, dispara con silenciador; X intercambia el control
  12-cinematics.js  cámaras guiadas, bandas y títulos
  13-endings.js     finales
  14-menu.js        menú principal, pausa, opciones (localStorage) y guía paso a paso
  15-loop.js        update(), IA de guardias y perros, render, HUD y radar
tests/smoke.js      prueba corta sin cabeza (perros, celda, Vidal)
tests/playthrough.js partida completa automática: menú, interrogatorio, llave, archivo, expediente, cambio de personaje, salida
tests/shots.js      capturas de referencia en tests/shots/
tools/build-artifact.py  empaqueta todo en un solo HTML para publicarlo como Artifact
```

Los archivos de `src/` se cargan en orden como scripts clásicos y comparten ámbito, así que el orden
numérico importa. `window.__LH` expone el estado para depurar desde la consola.

## Pruebas

```bash
npm i -D playwright     # una vez; necesita Chromium (npx playwright install chromium)
npm test                # prueba corta
node tests/playthrough.js   # partida completa (varios minutos sin GPU)
node tests/shots.js         # capturas
```

## Diseño

- Clave del archivo: **0129** (salmo 130 *De profundis*, numerado como la Vulgata, CXXIX). Dos errores y suena la alarma.
- Reloj de misión desde las 02:10. A los 7 minutos Control avisa; a las 02:19 sueltan 7 perros.
- Si te capturan despiertas en la celda con Halloran. Solo sales convenciendo al cabo Vidal en tres preguntas,
  cuyas respuestas correctas dependen de las pistas reunidas (la Fuente, el expediente o el teletipo, el salmo).
- Los guardias leales mienten bajo interrogatorio; apretar de más los hace gritar.
- Roig (teniente, segunda infiltrada) sigue al personaje controlado, se agacha con él, busca sombra si él se esconde y,
  cuando un guardia pasa a alerta o un perro se acerca, dispara con silenciador (duerme, no mata; 12 balas). Los guardias
  la ven igual que a Cuttlas; si la hieren cae 40 s y no se puede controlar. X cambia el control y el inventario (llave,
  expediente) viaja con quien controlas.
