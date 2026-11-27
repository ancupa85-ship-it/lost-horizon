# Tanda Q: por qué el combate se sentía caótico, y el pulido

Andrés: «va cogiendo forma pero aún se siente caótico». Lo que más le pesaba era no saber cuándo le toca, es decir, el ritmo y los turnos. Esta tanda no añade mecánicas: solo pule las que hay.

## 1. Cómo se midió

Dos peleas jugadas por guion, con tiempos reales y sin congelar nada. Se registra cada fotograma.

- **Pelea 1:** un guardia.
- **Pelea 3:** el mismo duelo con otros dos guardias en alerta.

El guion es siempre el mismo:

1. Golpe de apertura, que el guardia para.
2. Dos amagos que se dejan pasar.
3. Un culatazo que te da.
4. Un culatazo parado a 0,12 s del golpe, que es la contra.
5. El remate.

Herramientas:

- `registro_pelea.py` escribe el CSV con todo lo que se dispara en cada fotograma.
- `analizar_pelea.py` saca la línea de tiempo, los solapes, la cámara y los saltos.

Las dos están en la carpeta de pruebas de la sesión; sus salidas están en `capturas-tandaP/diagnostico`.

## 2. Diagnóstico (tanda P)

| Problema | Medida |
|---|---|
| Momentos amontonados | 11 y 13 ventanas de 300 ms con 3 o más tipos de efecto a la vez |
| Peor racimo: contra + remate | 2 cámaras lentas separadas 0,46 s, 2 paradas de golpe, sonido de 5 capas, cámara a 195–345 °/s y la radio («refuerzos») encima |
| Acercamiento a saltos | el guardia se echaba encima en los 0,07 s del latigazo: 84 cm en 46 ms (31 cm por fotograma a 60 fps) |
| Turnos rotos | un flanqueador disparó 30 ms después del culatazo recibido |
| Flanqueo nervioso | órdenes de flanqueo cada 0,5 s (17 en 9 s) |
| Sacudida de más | tu propio golpe parado sacudía la cámara a 74 °/s |
| Aviso equivocado | los 3 primeros segundos del duelo el aviso decía «E GOLPEAR EL FUSIL» |
| Distancia irregular | 140 → 175 → 105 → 4 → 106 cm |
| Sin pausa fija | la guardia duraba al azar entre 1,0 y 1,3 s; después del culatazo no había pose final |

## 3. Fuentes

Lo que repiten, aplicado aquí:

- **Signals and Light** (ataques por fichas, cámara): un solo atacante y una cámara que no persigue cada giro.
- **God of War, GDC 2019:** como mucho dos agresivos, y los demás en media luna sin atacar.
- **Doom 2016:** fichas de ataque, solo dispara quien tiene ficha.
- **Anatomía de Dark Souls 3:**
  - señal más golpe activo de 340 ms o más;
  - pose final de 170 ms o más;
  - amago de 240 ms o más.
- **Sakurai:** la parada de golpe crece con la fuerza; un momento fuerte cada vez.
- **Pichlmair y Johansen** (estudio del *juice*): el exceso de efectos simultáneos borra la información.
- **Swink, *Game Feel*:** la legibilidad viene de las pausas.
- **DICE, audio HDR:** lo fuerte manda y lo débil se aparta.

## 4. Los 10 puntos

Todos están en una sola compilación. Los ajustes están en el director, categoría *Tarsis|Combate*.

| # | Qué | Ajustes |
|---|---|---|
| 1 | **Turnos.** En el duelo, y `TurnQuietSeconds` (0,8 s) después de cada intercambio, nadie más dispara. Fuera del duelo, un tirador a la vez: la ficha dura `ShooterTokenSeconds` (1,5 s). `ShotsHeld` cuenta los disparos aguantados. | `bTurnRule`, `MayFire`, `ExchangeHappened` |
| 2 | **Una cámara lenta por encuentro.** Fuera la de la contra. La del remate solo sale si no queda nadie más en alerta. | — |
| 3 | **Contra y remate separados.** La E pulsada en los primeros `StaggerRemateDelay` (0,35 s) del tambaleo se guarda y sale después. | `bRemateQueued` |
| 4 | **Cámara.** Los giros de escena tienen tope de `SceneTurnMaxSpeed` (90 °/s) y la tercera persona tiene una zona muerta de 30°. La sacudida es de ±`KickAmplitude` (0,25) y solo sale cuando te dan, en la contra y en el remate. Ya no sale por tu golpe, por lo parado ni por el forcejeo. | — |
| 5 | **Distancia sin saltos.** El guardia se coloca a `DuelDistance` (120 cm) andando, como mucho a `DuelSpacingSpeed` (260 cm/s). En el culatazo se acerca a `MeleeContactDistance` (95 cm) repartido en todo el golpe. | — |
| 6 | **Pose final y pausa fija.** Tras el culatazo, la animación sigue `MeleeRecoverSeconds` (0,25 s) antes de volver a la guardia. La guardia dura siempre 1,3 s. | `MeleeGuardUpSeconds` (1,3, 1,3) |
| 7 | **Prioridad del sonido.** Ligero, 2 capas; medio, 3; fuerte, 5 con voces. Lo de menos rango que suena 0,3 s después de algo más fuerte baja a la mitad. | — |
| 8 | **Avisos coherentes.** En el duelo solo sale el aviso del duelo, y en el duelo la E no desarma: un aviso, una acción. La radio espera y los guardias se callan 1,5 s tras la contra o el remate (`BigHitQuietSeconds`), salvo las frases urgentes. | — |
| 9 | **Flanqueo con histéresis.** El punto se conserva si es reciente (menos de 2 s) y el nuevo está a menos de 300 cm, o si está a menos de 150 cm. Solo cuenta como orden cuando cambia. | — |
| 10 | **Medido otra vez**, a continuación. | — |

## 5. Resultados

### Cómo se cuenta ahora

En la tanda P cada contacto contaba como tres tipos de efecto por sí solo: el contacto, su parada de golpe y su sonido. Con esa cuenta, ningún contacto podía bajar de 3.

Ahora se cuenta también agrupado:

- la parada, el sonido, la reacción y el tambaleo que salen a la vez que un contacto (100 ms) son ese contacto;
- la cámara lenta cuenta una vez.

Las peleas de la tanda P se han vuelto a analizar con la misma cuenta.

### Peleas de control

| Medida | Objetivo | P, pelea 1 | Q, pelea 1 | P, pelea 3 | Q, pelea 3 |
|---|---|---|---|---|---|
| Ventanas con 3+ tipos, cuenta bruta | — | 11 | 6 | 13 | 5 |
| Ventanas con 3+ sucesos distintos, fuera del remate | 0 | 2 | **0** | 4 | **0** |
| Mayor velocidad sin ragdoll, en cm por fotograma a 60 fps | ≤ 30 | 30,7 | **1,3** | 27,1 | **7,2** |
| Cámara más rápida, en tiempo real | < 120 °/s | 175 | **61** | 228 | **39** |
| Disparos en el duelo o 0,8 s después | 0 | 0 | **0** | 1 | **0** |
| Cámaras lentas | 1 por encuentro | 2 | 1 | 2 | 0 (quedaban dos en alerta) |
| Guardia entre intercambios | constante | 1,0–1,3 s | 1,29–1,31 s | 1,0–1,3 s | 1,29–1,31 s |
| Distancia en guardia / al contacto | 120 / 95 cm | 140–175 / 4–105 | 120 / 95–97 | — | 120 / 95–96 |
| Órdenes de flanqueo | menos | — | — | 17 en 9 s | 11 en 9 s |

La mayor distancia recorrida en un fotograma registrado fue de 64 cm en la pelea 3. Fue un tirón del editor: 165 ms de juego en un solo fotograma, al compilar un sombreador la primera vez que salió la contra. A 387 cm/s, es un guardia corriendo.

Lo que queda solapado es solo el remate: su contacto, su parada, su sonido y la cámara lenta, cuando la hay. Es el momento que debe ser fuerte, y es la excepción que se fijó.

## 6. Pruebas y rendimiento

**Pruebas:** las 17 familias afectadas:

- contacto, combate, revolverse, armados, cuerpo, fisica, tercera, datos, fusil;
- controles, opciones, disparo, letal, combate2, empezar, tactica, captura.

Pasaron 270 de 272. Los dos fallos eran pruebas escritas para el ritmo de antes, y se han ajustado:

- **combate2:** la E pulsada justo tras la contra ahora espera 0,35 s. La prueba comprueba primero que espera y después que remata.
- **contacto:** un puñetazo ligero suena ahora en 2 capas, no en 3.

Con los cambios, combate2 y contacto pasan 36 de 36.

**Rendimiento:** de noche, con el editor recién abierto y tras el calentamiento:

- 38,2 / 34,1 / 31,3 fps de media;
- peor 1 % de 32,8 / 31,0 / 25,6 fps;
- 3353 MB de VRAM, 41 MB más que en la P.

El detalle está en `docs/rendimiento.md`.

## 7. Herramientas de medida

- `registro_pelea.py` y `analizar_pelea.py` viven en la carpeta de pruebas de la sesión, no en el repositorio.
- La cuenta agrupada, la velocidad por fotograma y la cámara en tiempo real se añadieron en esta tanda.
- La cámara se mide en tiempo real porque, en cámara lenta, los grados por segundo de juego salen inflados.
