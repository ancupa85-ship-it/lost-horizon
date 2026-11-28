# Tanda T2: cámara del remate, alineación del remate y umbral de los pies

Cierre de la tanda T, sin mecánicas nuevas. Base: origin e785097. Medido con la mediana de tres pasadas por pelea, como en la T. Las tablas están en `capturas-tandaR/diagnostico`: `mediana_fT.txt` es «antes» (e785097), `mediana_iT.txt` es «después» y `mediana_hT.txt` es la prueba del umbral de 12 cm.

## 1. De dónde salían los ~100 cm del remate

Leído dentro del PIE (`registro_r.py` guarda `LastPrealignSpot`, `LastLungeTo` y `LastTSFix` en cada fotograma):

| Valor | Medido |
|---|---|
| Sitio previsto (`LastPrealignSpot`) | x = 6334 |
| Abalanzamiento (`LastLungeTo`) | x = 6201 |
| Corrección (`LastTSFix`) | (−134, −16) |

La diferencia era exactamente la corrección de raíz de `TakedownSceneBegin`.

Esa corrección se calculaba evaluando la malla con `TickAnimation` y `RefreshBoneTransforms` en el mismo fotograma en que se ponía la animación. En ese fotograma la malla aún da la raíz en el origen de la pareja, así que salía una corrección falsa de ~134 cm. Lo que hacía:

- llevaba la malla del guardia hacia Cuttlas;
- y a Cuttlas casi encima del guardia (a 4 cm).

Además había un segundo error, de fondo: **la malla que se ve del guardia** (copia de la pose retargeteada) **no lleva la traslación de la raíz**. En la pareja de derribo, la raíz de la parte del guardia (V) está a ~135 cm de la de Cuttlas (A). Sin esa traslación, el guardia salía en el origen de la pareja, encima de Cuttlas. Por eso las pelvis quedaban a 17–23 cm.

No era la escala ni el espacio (componente frente a mundo), y el root motion no se aplicaba dos veces: era el tiempo de evaluación, más esta pérdida de la raíz en la copia visible.

**Arreglo:**

- La raíz en T0 sale de la pista de la animación (`UAnimSequence::GetBoneTransform`), no de evaluar la malla.
- En la escena, la malla del guardia se mueve fotograma a fotograma con la raíz de la pista de su parte (`bTakedownRootFollowRule`). Lo que empuja la separación mínima se acumula (`TSPush`).
- Al caer, la malla vuelve a la pareja para que el ragdoll salga de su sitio.

## 2. Cámara del remate en tercera

Va de un corte al empezar el remate, al primer ángulo válido de esta lista: detrás de Cuttlas mirando al guardia, y a 45 y 90° a cada lado. Válido quiere decir:

- el guardia a más de 60 cm de la línea entre la cámara y Cuttlas;
- y la cámara sin nada en medio.

Ya no gira durante el tambaleo.

## 3. Umbral del bloqueo de pies

Se probó a 12 cm, frente a los 18 de la T:

| Umbral | Pies de Cuttlas por apoyo (mediana) | Pasos con el pie levantado más de 4 cm |
|---|---|---|
| 18 cm | 11–15 cm | 1,0 por segundo de duelo |
| 12 cm | 2–5 cm | 1,3 por segundo |

Un paso más cada tres segundos. Se queda en 12 (`FootLockReleaseCm`). No lo he visto en pantalla, así que conviene que Andrés lo juzgue jugando.

## 4. Resultados

Mediana de tres pasadas, en este orden: uno, tres, agarre, pared.

| Objetivo | Meta | Antes (e785097) | Después (T2) | ¿Se cumple? |
|---|---|---|---|---|
| Remate en tercera: el guardia tapa a Cuttlas | menos que 81–83 % | 89, 94, —, 96 % | 3, 6, —, 3 % | **sí** |
| Pies de Cuttlas por apoyo | < 10 cm | 13, 15, 11, 12 | 4, 7, 2, 2,5 | **sí** |
| Pies del guardia del duelo | < 10 cm | 15, 16, 2,5, 31 | 13, 14, 25, 31 | **no** |
| Pelvis Cuttlas–guardia durante el remate | ≥ 35 cm | 17–23 durante toda la escena | 120–145 durante la escena; 6–8 un fotograma al caer | **sí** en la escena, salvo ese fotograma |
| Mano de Cuttlas al guardia en el golpe | toca | 85 cm | 54–57 cm | **no** (más cerca) |
| Flanqueador andando tras llegar | < 2 s | 2,1 | 2,1 | **no** |

### Lo que queda

- **Un fotograma al caer el guardia, encima de Cuttlas.** Al empezar el ragdoll, la malla vuelve a la pareja y, durante ese único fotograma, la copia visible (sin la raíz) sale en el origen. Arreglarlo pide que la copia visible lleve la raíz en la escena (o desplazar la copia ese fotograma). No lo he hecho: ya van dos compilaciones para este punto.
- **La mano no toca (54 cm).** La copia visible de Cuttlas probablemente tampoco lleva la raíz de su parte, que avanza unos 32 cm hacia el guardia durante el golpe. El arreglo sería el mismo que para el guardia. No está comprobado.
- **El medidor de «mano tocando» está bien definido:** es la distancia de la mano más cercana de Cuttlas a la cabeza o la pelvis del guardia en el fotograma del contacto. Los 85 cm de antes salían de la alineación rota.
- **Pies del guardia:** el bloqueo se aplica, pero lo que queda (13–31 cm) viene de los momentos sin duelo y de recolocarse contra el muro.

## 5. Pruebas y rendimiento

- **Pruebas:** las familias afectadas, las de movimiento y «tercera»: 301 de 301.
- **Rendimiento** (de noche, con el editor recién abierto, descartando la primera pasada): 42,1 / 39,3 / 36,4 fps y 3211 MB de VRAM. En la T, 42,2 / 38,5 / 37,6. Dentro del ruido. Detalle en `docs/rendimiento.md`.
