# Lost Horizon: De Profundis

Misión 1 de *Project Lost Horizon* en primera/tercera persona: sigilo, acción, puzle e interrogatorio,
con estética cel-shading y puesta en escena tipo MGS2. Todo en JavaScript plano sobre Three.js r128,
sin empaquetador: se abre `index.html` y funciona.

## Jugar

```bash
npm start          # sirve la carpeta en http://localhost:8080
```
o simplemente abre `index.html` en Chrome/Firefox (el juego pide el ratón al hacer clic).

Controles: WASD mover · ratón mirar · C agacharse · Shift correr · E usar/hablar · F agarrar/patada ·
G cargar cuerpo · clic disparar · V cambiar vista 1ª/3ª persona · Q fumar (8 s quieto, +2 vida) · Tab cuaderno.

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
  11-cinematics.js  cámaras guiadas, bandas y títulos
  12-endings.js     finales
  13-loop.js        update(), IA de guardias y perros, render, HUD y radar
tests/smoke.js      prueba sin cabeza con Playwright
tools/build-artifact.py  empaqueta todo en un solo HTML para publicarlo como Artifact
```

Los archivos de `src/` se cargan en orden como scripts clásicos y comparten ámbito, así que el orden
numérico importa. `window.__LH` expone el estado para depurar desde la consola.

## Pruebas

```bash
npm i -D playwright     # una vez; necesita Chromium (npx playwright install chromium)
npm test
```

## Diseño

- Clave del archivo: **0129** (salmo 130 *De profundis*, numerado como la Vulgata, CXXIX). Dos errores y suena la alarma.
- Reloj de misión desde las 02:10. A los 7 minutos Control avisa; a las 02:19 sueltan 7 perros.
- Si te capturan despiertas en la celda con Halloran. Solo sales convenciendo al cabo Vidal en tres preguntas,
  cuyas respuestas correctas dependen de las pistas reunidas (la Fuente, el expediente o el teletipo, el salmo).
- Los guardias leales mienten bajo interrogatorio; apretar de más los hace gritar.
