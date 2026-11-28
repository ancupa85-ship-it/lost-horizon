# Tanda S: pies, remate y flanqueador (tercer pulido del combate)

Andrés jugó la R: «algo menos caótico». Esta tanda va a lo que no llegó a la meta en la R, sin mecánicas nuevas y con el mismo método: medir, arreglar y volver a medir.

## 1. Antes de cambiar nada

- **Capturas del juego** con origin 3a8bd89 tal cual: 12 fotos en `D:\LostHorizon\capturas-tandaS\antes`, tomadas en la contra, el remate, el fin del remate, la suelta del agarre y la guardia con tres guardias. Las de «después» están en `capturas-tandaS\despues`.
- **Sonda del puñetazo de Cuttlas** (`sonda_raiz.py`):
  - el ABP de Cuttlas está en «root motion solo de montajes»;
  - el root motion del golpe sí llega a la cápsula (24,5 cm);
  - pero el pie apoyado se mueve con la cápsula: de x = 6254 a 6234 cm.

  La ranura del golpe solo manda de cintura para arriba; las piernas salen de la locomoción del GASP. Esa locomoción no se enteraba del movimiento, porque la cápsula se movía con `AddActorWorldOffset`, sin velocidad. Lo mismo pasaba con el empujón (`LaunchCharacter`) y con los acercamientos cortos del guardia.

## 2. Pies: enfoques comparados

| Enfoque | Qué hace | Por qué sí o no |
|---|---|---|
| Ajustar el nodo Foot Placement del ABP | Clava los pies que la animación da por apoyados | No da pasos si la cápsula la mueve el código. Habría que editar el ABP del GASP, que comparten guardias y héroe, y es el nodo del NaN que ya cerró el editor. **No.** |
| Stride y Orientation Warping | Ajustan la zancada a la velocidad | Solo actúan con locomoción en marcha. **No.** |
| Que el desplazamiento pase por el movimiento del personaje | Entrada de movimiento con velocidad y aceleración: el motion matching del GASP elige pasos de verdad | Barato, sin tocar el ABP ni el tiempo global, con interruptor. **Elegido.** |

Todo es del motor y del GASP; no hay código externo.

## 3. Cambios

### Pies

- **Cuttlas** (`bHeroStepRule`):
  - lo que avanza por el root motion de su golpe se convierte en un desplazamiento pendiente que se recorre andando (`HeroStepTick`, como mucho a `HeroStepSpeed`, 160 cm/s), igual que lo que retrocede por el culatazo (`HeroHitPushCm`, 22 cm);
  - hacia el guardia del duelo no baja de `MeleeContactDistance`.
- **Guardia:**
  - solo se recoloca si le faltan `DuelStepDeadband` (20 cm) o más, y entonces de una vez, sin pasitos;
  - no se recoloca mientras Cuttlas da su paso.

### Remate

- **Separación de la pareja** (`TakedownPairGap`): se probó separarla 12 y 20 cm al empezar. El golpe tocaba peor (mano a 48–67 cm de la cabeza o la pelvis del guardia, frente a 20–40) y las pelvis no pasaban de 22–25 cm.
  - Lo que junta los cuerpos no es la pareja: el mínimo cae en el primer fotograma del remate, cuando la contra ha dejado a Cuttlas encima del guardia tambaleándose.
  - Por eso no se rehízo la pareja en Blender, y `TakedownPairGap` queda en 0.
- **Salida de brazos:** el fundido pasa de 0,5 a 0,7 s (`TakedownEndBlendSeconds`).

### Flanqueador

- Al acabar un duelo, los papeles y los puntos de flanqueo se quedan como están 4 s (`FlankFreezeAfterDuel`).
- El relevo no se toca.

## 4. Resultados

Comparación hecha el mismo día con la misma herramienta: «antes» con 3a8bd89, «después» con la S, sin fotos durante la medida, porque cada foto frena el editor. Las medidas varían bastante de una pasada a otra (las pelvis, entre 23 y 33 cm en dos pasadas de «antes»).

| Objetivo | Meta | Antes (3a8bd89) | Después (S) | ¿Se cumple? |
|---|---|---|---|---|
| Pies de Cuttlas por apoyo | < 10 cm | 26–42 | 26–37 | **no** (baja algo) |
| Pies del guardia por apoyo | < 10 cm | 22–82 | 18–31 | **no** (baja) |
| Pelvis Cuttlas–guardia | ≥ 35 cm | 23–33 | 17–19 | **no** |
| Mano de Cuttlas al guardia en el golpe del remate | toca | 20–40 cm | 24–89 cm | igual de variable |
| Salida de brazos del remate | ≤ 15 cm/fot | 5–18 | 9–19 | **no** |
| Flanqueador andando tras llegar | < 2 s | 2,2–2,6 | 0–2,1 | casi (2,1 s) |
| Órdenes de flanqueo (tres guardias) | — | 7 | 4 | mejora |
| Guardia del agarre, salto al soltarse | ≤ 15 cm/fot | 53 | 37 | **no** (baja) |
| Pelvis de Cuttlas a su cápsula | < 40 cm | 22–27 | 22–34 | sí |
| Giro del guardia del duelo | ≤ 180 °/s | 180 | 180 | sí (240 fuera del duelo, al alertarse) |
| Ninguno detrás de la cámara a < 3 m | 0 | 0 | 0 | sí |

Los objetivos de la Q siguen igual: nadie más dispara durante el duelo, la guardia es de 1,3 s y hay una sola cámara lenta.

### Lo que no se alcanza

- **Pies (de 26 a 37 cm en Cuttlas y de 18 a 31 en el guardia).** Andar en vez de deslizarse ayuda, pero con desplazamientos de 20–25 cm el GASP no siempre arranca un paso completo. Para bajar de 10 cm hace falta un bloqueo de pies propio (un IK que clave el pie apoyado mientras la cápsula se mueve) o editar el Foot Placement del ABP. Las dos cosas son un sistema nuevo o tocar el ABP del GASP, y no lo he forzado.
- **Pelvis en el remate (17–19 cm).** El mínimo está en el primer fotograma del remate, cuando Cuttlas ya está encima del guardia que se tambalea. Separar la pareja hacía que el golpe no tocara. Arreglarlo sería poner a Cuttlas a su sitio de la pareja antes de que empiece el golpe, lo que cambia el remate; lo dejo para decidir.
- **Salida de brazos.** Con el fundido de 0,7 s varía entre 9 y 19 cm por fotograma según la pasada: la animación de la pareja mueve los brazos deprisa justo al acabar.

## 5. Pruebas y rendimiento

- **Pruebas:** las familias afectadas más las de movimiento («paso», «frente», «apuntar») y «tercera»: 301 de 301.
- **Rendimiento:** ver `docs/rendimiento.md`, apartado de la tanda S.
