# Tanda T: bloqueo de pies, remate alineado y cámara del remate (cuarto pulido del combate)

Tanda sin mecánicas nuevas. Base: origin 434d574.

## 1. Medida repetible

En la S las medidas variaban demasiado entre pasadas: las pelvis iban de 23 a 33 cm en dos pasadas de «antes». Desde esta tanda, cada pelea de control se juega tres veces y se da la mediana y el rango:

- `mediana.py`, en la carpeta de pruebas de la sesión, junta las pasadas;
- las tablas están en `capturas-tandaR/diagnostico/mediana_aT.txt` (antes, 434d574) y `mediana_fT.txt` (después).

Medidas nuevas en `analizar_r.py`:

- en el golpe del remate, lo que le queda a la mano de Cuttlas hasta la cabeza o la pelvis del guardia;
- el porcentaje de fotogramas del remate en tercera persona en que el guardia queda entre la cámara y Cuttlas.

## 2. Bloqueo de pies: enfoques

| Enfoque | Qué pide | ¿Elegido? |
|---|---|---|
| Nodo Two Bone IK en un ABP de postproceso de la malla | Crear y editar un grafo de animación a mano en el editor | no |
| Control Rig de bloqueo de pies | Crear el rig y su grafo; más caro de mantener | no |
| IK de dos huesos en C++ sobre la malla que se ve (`UPoseableMeshComponent`) | Lo que ya hacen los guardias (malla visible copiada y el IK de brazos del fusil) | **sí** |

No toca el ABP compartido del GASP ni el tiempo global, y no hay código externo.

**`TarsisPies.h/.cpp`, `TarsisFootLockApply`:**

- **Clavar:** clava en el mundo el pie que la animación da por apoyado (a menos de 18 cm del suelo y moviéndose menos de 45 cm/s respecto a la malla).
- **Mantener:** mientras está clavado, solo cuenta la altura. Los pasitos del GASP apenas levantan el pie, así que si se mirase la velocidad se soltaría enseguida.
- **Soltar:** se suelta si la animación lo levanta o lo aleja más de 18 cm. Entonces va a su sitio nuevo en 0,15 s, con un arco de 7 cm: un paso, no un arrastre.
- **IK:** de dos huesos (muslo, pantorrilla y pie). La rodilla se queda de su lado y el pie conserva el giro de la animación.

**Dónde se aplica:**

- **Guardia del duelo:** sobre su `Pose`, encendido por el director (`bFootLockOn`).
- **Cuttlas:** sobre una copia visible nueva, `PiesCuttlas` (`UPoseableMeshComponent`), solo durante el duelo en tercera persona. `CuerpoCuttlas` se oculta en el juego (`SetHiddenInGame`) y sigue evaluando.
- **Interruptor:** `bFootLockRule`.

Dos fallos de la primera compilación, arreglados en las siguientes:

- La copia visible se alternaba cada fotograma: `IsVisible` da falso con `SetHiddenInGame`, así que la comprobación pasa a `GetVisibleFlag`.
- El guardia que iba a cubrirse seguía andando en pleno duelo (llegaba a 274 cm). Al empezar el duelo se para su IA (`StopMovement`).

## 3. Remate y cámara

- **Remate alineado** (`bTakedownPrealignRule`): en el tambaleo de la contra, Cuttlas va andando a su sitio de la pareja de derribo (`TakedownHeroSpot`, con la misma corrección de la raíz en T0 que `TakedownSceneBegin`), y el paso de la contra no cuenta.
  - Llega a su sitio (a unos 140 cm del guardia), pero al empezar el remate se sigue abalanzando unos 100 cm.
  - La corrección de la raíz que calcula `TakedownSceneBegin` al evaluar la pose no coincide con la que sale de la pista de la animación.
  - Quedan `LastPrealignSpot`, `LastLungeTo` y `LastTSFix` para seguirlo. Hay que leerlos dentro del PIE: leídos en el mundo del editor salieron a cero.
- **Cámara del remate en tercera** (`TakedownCamSideYaw`, 90°): de lado y por el lado libre. Empieza a girar ya en el tambaleo, con el mismo tope de 90 °/s de la Q, y durante el remate le frena la cámara lenta.

## 4. Resultados

Mediana de tres pasadas (rango entre paréntesis), antes con 434d574 y después con la T.

| Objetivo | Meta | Antes | Después | ¿Se cumple? |
|---|---|---|---|---|
| Pies de Cuttlas por apoyo (uno, tres, agarre, pared) | < 10 cm | 29, 27, 26, 27 | 13, 15, 11, 12 | **no**, pero baja a la mitad |
| Pies del guardia del duelo | < 10 cm | 39, 40, 29, 60 | 15, 16, 2,5, 31 | **no** salvo en el agarre; baja a la mitad o más |
| Pelvis Cuttlas–guardia, mínimo | ≥ 35 cm | 17, 17, —, 18 | 23, 19, —, 20 | **no** |
| Mano de Cuttlas al guardia en el golpe del remate | toca | 85, 84, 85 cm | 86, 86, 85 cm | igual |
| Remate en tercera: el guardia tapa a Cuttlas | menos | 81, 80, 83 % | 89, 94, 96 % | **no**, empeora |
| Flanqueador andando tras llegar | < 2 s | 2,1 (2,1–2,3) | 2,1 (1,9–2,2) | **no** |
| Guardia al soltarse del agarre, salto | ≤ 15 cm/fot | 26 (18–43) | 21 (21–21) | **no**, baja |
| Pelvis de Cuttlas a su cápsula | < 40 cm | 22–34 | 22–34 | sí |
| Ninguno detrás de la cámara a menos de 3 m | 0 | 0 | 0 | sí |

Lo de la Q sigue igual: nadie más dispara en el duelo, la guardia es de 1,3 s y hay una sola cámara lenta.

### Lo que no llega, y por qué

- **Pies (11–15 cm en Cuttlas; 2,5–31 en el guardia).** El bloqueo funciona: la mediana baja a la mitad. Lo que queda son los arrastres cortos de antes de clavar, que llegan hasta el umbral de 18 cm, y el guardia en la pelea de la pared, que se recoloca contra el muro. Bajar el umbral a 10 cm haría que el pie se soltara y diera un paso con el arco con más frecuencia; no lo he probado.
- **Remate.** Que Cuttlas llegue a su sitio funciona, pero el remate se lo come con su abalanzamiento de unos 100 cm (ver arriba). Las pelvis apenas suben (19–23 cm), y la cámara de lado no llega a girar lo bastante antes de la cámara lenta: el guardia tapa más que antes. Falta averiguar de dónde sale la diferencia de unos 100 cm entre las dos correcciones de la raíz.
- **Flanqueador (2,1 s).** Sin cambios en esta tanda.

## 5. Capturas, pruebas y rendimiento

- **Capturas del juego:** antes en `D:\LostHorizon\capturas-tandaT\antes` (las de «después» de la S, que es la misma versión que 434d574) y después en `capturas-tandaT\despues`.
- **Pruebas:** las familias afectadas, las de movimiento y «tercera»: 301 de 301.
- **Rendimiento:** ver `docs/rendimiento.md`, apartado de la tanda T.
