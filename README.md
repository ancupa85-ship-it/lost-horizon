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
C cargar cuerpo · clic disparar · X cambiar entre Cuttlas y Roig · G orden a Roig (sígueme / espera) · V vista 1ª/3ª persona · Q fumar (8 s quieto, +2 vida) ·
Tab cuaderno · R radio (Control 141.12, Roig 140.85 y una frecuencia que no figura en el manual) · H guía · Esc pausa y opciones.
El menú de inicio tiene "Cómo se juega", "Controles", "Opciones" y, si hay partida guardada, CONTINUAR.

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
tests/smoke.js      prueba corta sin cabeza (perros, radio, captura → celda, Vidal, guardar/continuar, segunda derrota)
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
- Cualquier derrota (guardias, perros, forcejeo) pasa por `defeat()`: la primera vez hay cinemática de captura
  (la voz de Alarcón: «No lo maten. Llévenlo con la doctora.») y despiertas en la celda con Halloran; solo sales
  convenciendo al cabo Vidal en tres preguntas, cuyas respuestas dependen de las pistas reunidas (la Fuente, el
  expediente o el teletipo, el salmo). La segunda derrota es el final «Cuarta sesión».
- Guardado automático en los puntos clave (llave, despacho, archivo, expediente, celda, salida de la celda) en
  `localStorage`; CONTINUAR en el menú y ÚLTIMO PUNTO en la pantalla de derrota lo recuperan. Empezar una partida nueva lo borra.
- Cinemáticas con cámara guiada: intro, la perrera (02:19), la apertura del archivo, la captura y el final.
  Si el puntero se desbloquea (Esc del navegador, cambio de ventana) la partida se pausa sola.
- Radio (R) al estilo códec: Control responde según el momento (celda, perros, llave, archivo…); Roig da pistas,
  y con dos de las pistas del teclado una llamada suya suelta la de Roma; la frecuencia 000.00 aparece cuando has
  tocado la Fuente, cortado la luz o pasado por la celda.
- Los guardias leales mienten bajo interrogatorio; apretar de más los hace gritar.
- Roig (teniente, segunda infiltrada) espera agachada donde está hasta que G le ordena seguirte; siguiéndote se agacha
  contigo y busca sombra si tú te escondes. Solo dispara, con silenciador (duerme, no mata; 12 balas), cuando un guardia
  está en alerta (os han descubierto) o un perro se le echa encima. Los guardias
  la ven igual que a Cuttlas; si la hieren cae 40 s y no se puede controlar. X cambia el control y el inventario (llave,
  expediente) viaja con quien controlas.
