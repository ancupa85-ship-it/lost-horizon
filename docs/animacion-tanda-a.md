# Tanda A: locomoción natural (diseño)

Pedido de Andres (2026-11-21): los movimientos se ven robóticos. Orden elegido: A locomoción, B apuntado y armas, C física.

## Por qué se ve robótico hoy
- No hay Animation Blueprint: guardias, Cuttlas, brazos de primera persona y perro usan `AnimationSingleNode` y
  `PlayAnimation`; cada cambio de animación es un salto sin mezcla.
- Guardias: BlendSpace 1D (quieto, andar, trotar), apuntar y caer sueltos; giro de cabeza con un `UPoseableMesh`
  que copia la pose cada tick (una segunda malla por guardia).
- Cuttlas en tercera: idle, walk y sneak; agachado y parado congela la pose (PlayRate 0).
- Sin direcciones, arranques, paradas, giro en el sitio, IK de pies ni reacción a impactos.

## Enfoque
1. Del Game Animation Sample (Epic, versión 5.8; licencia de contenido de Epic, válida para Steam con Unreal) se
   toma su Animation Blueprint con Motion Matching y las bases de datos de Pose Search que use. Antes:
   `tools/unreal/gasp_inventario.py` en D:\GASP para saber qué hay y qué variables lee el ABP.
2. **Conductor oculto + retarget en tiempo real** (como hace el propio GASP con otros personajes): un maniquí del GASP
   invisible corre el ABP y la malla visible (MakeHuman) copia la pose con el nodo de retarget de IK Retargeter. Para
   los guardias sustituye al `UPoseableMesh` actual, así que no añade mallas.
3. Cuttlas: Motion Matching completo. Guardias: el mismo ABP con LOD de actualización (URO) o una máquina de estados
   más barata si el coste por guardia pasa de ~0,15 ms; se mide con 12 en el patio.
4. Mirar (cabeza y cuello) y apuntar con nodos del ABP (LookAt / aim offset) en vez de tocar huesos a mano.
5. IK de pies del GASP (o de ALS-Refactored, MIT, como referencia) para escaleras y desniveles.

## Coste esperado
VRAM: casi nulo (las animaciones viven en RAM; la malla del conductor no se dibuja). CPU: lo que hay que medir.
Disco y RAM: solo se migran las secuencias que usen las bases de datos elegidas.

## Lo que dijo el inventario (2026-11-21, `gasp_inventario.py` y `gasp_abp.py` en el PC)
- `SandboxCharacter_CMC_ABP` (esqueleto SK_UEFN_Mannequin) no hace cast a su personaje: llama a la interfaz Blueprint
  `BPI_SandboxCharacter_Pawn::Get_PropertiesForAnimation` del pawn dueño (struct `S_CharacterPropertiesForAnimation`:
  velocidad, aceleración, Gait, Stance, MovementMode, RotationMode, InputState...). La trayectoria la genera el ABP con
  el modelo del CharacterMovementComponent estándar. Nodos: Motion Matching, Blend Stack, Offset Root Bone, Orientation
  Warping, Steering, Foot Placement, Leg IK, Aim Offset, Pose History.
- Cadena por defecto: `CHT_PoseSearchDatabases` → LOD 0 Dense (718 secuencias, 958 MB de .uasset de editor),
  1 Sparse (307, 399 MB), 2 ExtremeSparse (232, 322 MB), elegido con la cvar `DDCvar.MMDatabaseLOD`.
- Retarget en tiempo real: `ABP_GenericRetarget` (sin esqueleto propio) con Retarget Pose From Mesh y la variable
  `IKRetargeter`; los RTG van de IK_UEFN_Mannequin a cada destino. Para MakeHuman: IK_<persona> + RTG_UEFN_to_<persona>.
- No hay animaciones de armas (solo 42 poses de Aim Offset): pistola y fusil vendrán de Lyra en la tanda B.

## Decisión de montaje
Como Python no puede editar grafos, no se reescribe el ABP: se copia `SandboxCharacter_CMC` a /Game/Tarsis y se
**reparenta a ATarsisGuard** (y otra copia a la clase C++ del jugador), con lo que su implementación de la interfaz,
que lee el CharacterMovementComponent, sigue valiendo. guardias.py coloca esa clase Blueprint en vez de la C++.
Desde C++ se escriben por reflexión `Gait` y `CharacterInputState` (andar, correr, agacharse, apuntar) según el
estado del guardia. La malla UEFN queda oculta y conduce; la malla MakeHuman visible lleva `ABP_GenericRetarget` con
su RTG. Se empieza con `MMDatabaseLOD` = 1 (Sparse) y se mide; Dense solo si sobra CPU y RAM.

## Cuttlas en tercera persona (2026-11-21)
- **Peón**: `BP_CuttlasGASP` = copia entera de `SandboxCharacter_CMC` reparentada a **`BP_FirstPersonCharacter`** (no a la
  clase C++): hereda sus acciones de entrada, su malla y su cámara de primera persona. `gasp_cuttlas.py` (modo `montar`)
  le copia del peón de antes malla, cápsula, CMC y giro con el control; tras compilar no queda ninguna diferencia.
  Motivo: en la plantilla la cámara cuelga de la cabeza de la malla de primera persona, que cuelga de `GetMesh()` y copia
  su pose (`ABP_FP_Copy`); si el GASP fuera en `GetMesh()`, la primera persona se movería con el Motion Matching.
- **GameMode**: `BP_TarsisGameModeGASP` (copia de `BP_FirstPersonGameMode` con ese peón) y el nivel Tarsis apuntando a
  él en WorldSettings. El GameMode global no cambia; para volver, `DefaultGameMode` del nivel a ninguno.
- **C++** (`TarsisGaspHero.cpp`): `SetupGaspPlayer` (antes de `SetupArms`) apaga PreCMCTick, traversal, smart objects,
  foley y VisualOverride, destruye las cámaras, el brazo de muelle y el actor hijo del GASP, quita `IMC_Sandbox` (sus
  acciones duplicaban la vista con el ratón y la C) y sus eventos de rueda y cruceta, y devuelve la vista al peón.
  `SetupGaspHero` crea `ConductorGASP` (maniquí UEFN oculto con el ABP) y cuelga de él `CuerpoCuttlas` con
  `ABP_GenericRetarget` y `RTG_UEFN_cuttlas`. `GaspHeroTick` pone el Gait por `MaxWalkSpeed` (menos de 320 Walk, hasta
  650 Run, más Sprint) y baja el maniquí con la cápsula al agacharse. Sin el peón del GASP, el HeroBody de antes.
- **Giro parado**: con el ABP del GASP en vista estrafe, al girar la cámara sin andar giran el torso y la cabeza (aim
  offset, hasta 115°) y las piernas esperan al primer paso: el giro en el sitio solo salta apuntando o justo al pararse
  (`ShouldTurnInPlace`). Arreglado en la sección siguiente.

## Giro en el sitio estando quieto (2026-11-21, Cuttlas y guardias)
- **Causa**: `ShouldTurnInPlace` = |desfase| ≥ 50° **y** (`CharacterInputState.WantsToAim` o recién parado). El 50 es un
  literal del grafo y no hay variable expuesta. Parado y sin apuntar, el ABP acumula el giro del actor en el hueso raíz
  (Offset Root Bone) y las piernas se quedan. Los guardias van en «orientar al movimiento», sin aim offset: parados se
  quedaba quieto el cuerpo entero (hasta 89° de desfase) hasta echar a andar.
- **Arreglo** (`TarsisGaspTurn.h/.cpp`, `FTarsisGaspTurn`): el desfase se lee del hueso raíz del maniquí que conduce
  (giro en espacio de la malla; en reposo es la identidad). Parado (menos de 10 cm/s) y con el desfase por encima de
  `From`, se pone `WantsToAim` en el `CharacterInputState` del peón; se quita al quedar por debajo de `Release` (15°),
  al andar o a `MaxSeconds` (1,5 s). Umbrales: Cuttlas `HeroGaspTurnFrom` 95° (por debajo, el aim offset ya lleva el
  torso con la cámara); guardias `GaspTurnFrom` 60° (no tienen aim offset). Al pasar a una animación suelta (apuntar, caer)
  el guardia lo suelta.
- **Sin pose de apuntar**: ninguna tabla de chooser ni nodo del ABP de pose mira `WantsToAim`; en el peón solo lo leen la
  cámara del GASP y `UpdateRotation_PreCMC`, apagados aquí. Medido: las manos siguen a la altura de la pelvis (±6 cm) y en
  las capturas no se levantan los brazos.
- **Resultado** (`capturas-gaspA/giro_medidas.txt`): Cuttlas parado gira 90° y 160° y las piernas quedan alineadas en
  0,6 s; el guardia que se vuelve hacia un ruido a 90° y 160°, en 0,4-0,6 s, antes de echar a andar.

## Agacharse en tercera persona (2026-11-21)
- **Medido fotograma a fotograma** (`tools/unreal/visual_agachar.py`, `capturas-gaspA/agachar*`): dos cortes. La cámara
  bajaba 55 cm de golpe (`Tick` del director: `AddWorldOffset(-55)` en el fotograma del cambio) y, al agacharse parado, el
  cuerpo salía 54 cm más alto un fotograma. El cuerpo en sí baja suave con el ABP del GASP (pelvis de 87 a 40 cm en unos
  0,6 s); las bases de agachado del GASP no saltan de pose.
- **Cámara**: baja y sube con una curva suave (smoothstep) en `CrouchCamSeconds` (0,3 s), reversible a medias;
  `CrouchCamDrop` 55 cm. Vale para primera y tercera persona.
- **Cuerpo**: `ConductorGASP` no tenía al CMC como requisito de tick (`ACharacter` se lo pone a `GetMesh()`): el ABP podía
  actualizarse antes que el movimiento y el fotograma en que la cápsula encoge leía el sitio de antes. Ahora
  `AddTickPrerequisiteComponent(CMC)`.
- **Resultado**: por cada 1/30 s, la cámara se mueve 9-11 cm como mucho y la pelvis 2,5-6,5 cm; el pie no pasa de 6 cm
  sobre el suelo. Prueba nueva en `prueba_tercera`: «agacharse y levantarse en tercera, sin saltos de un fotograma».

## La detención (2026-11-21, novena)
- **Qué**: sustituye la escena de antes (giro de 0,75 s, «empujón» y negro) por dos, según cómo te pillen. La lógica de
  cuándo te cogen no cambia; `BeginCapture` solo decide la escena (`TarsisCapturaEscena.cpp`).
  - **Rendido** (te quedaste quieto con el alto y viene `ArrestGuard`, o te coge de cerca, o te saca de la taquilla o
    del camión): pareja de **empujón parado** del GASP (`shove_stand`). El guardia hace `_A` con su maniquí (su persona
    la copia con el retarget); Cuttlas hace `_V` con `ConductorGASP` (y `CuerpoCuttlas` la copia) y, en el segundo del
    aviso `TriggerRagdoll`, pasa a física con `PA_UEFN_Mannequin`. El guardia suelta su parte donde acabó su raíz, se
    acerca, se agacha sobre ti (agachado del ABP del GASP), suenan las esposas (`esposas.wav`, provisional, de
    `tools/sonido/esposas.py`) y funde a negro. Despiertas en la celda como siempre.
  - **Golpe** (huyendo, `bFleeing`, o el tercer tiro): pareja de **derribo parado** (`takedown_stand`) con sacudida y
    «golpe» en el puñetazo; al caer, vista borrosa y doble (desenfoque, separación de colores y viñeta) medio segundo,
    la cámara al suelo y negro; al despertar la vista se aclara en 2 s. Provisional hasta tener fusil y culatazo.
- **Datos**: las 16 secuencias (`Interactions/Shoves` y `Interactions/Takedowns`, sin root motion, sin montajes) se
  copiaron del GASP. `tools/unreal/captura_datos.py` lee de los montajes del GASP (copia temporal, se borra) los avisos y
  de las secuencias la raíz al empezar, y escribe `TarsisCapturaDatos.inl`. Las raíces de `_A` y `_V` están grabadas en
  el mismo espacio: las dos mallas se ponen en el mismo sitio (`SceneComp`, para que la raíz de `_V` caiga donde está
  Cuttlas) y el guardia se lleva en 0,35 s a donde empieza la suya. La pareja (F, B, L, R) se elige por la dirección en
  que está el guardia.
- **Cámara**: en primera persona, una `ACameraActor` sigue a la cabeza de `ConductorGASP` con sacudida, mira del pecho
  a las botas del guardia según cae y queda de lado en el suelo (alabeo 72°). En tercera la cámara se queda y se ve la
  caída (`ThirdNow` admite la captura si ya estabas fuera).
- **Respaldo**: sin el GASP en el guardia o en Cuttlas, sin las animaciones o con `bCaptureSceneRule` apagado, la escena
  de antes.
- **Medido** (`capturas-gaspA/captura_medidas_sin_fotos.txt`): rendido 5,1 s hasta el calabozo, golpe 3,3 s; la cámara de
  primera persona baja de 162 a 16 cm. Capturas cada 0,1 s de juego en `capturas-gaspA/captura/`.
- **Assets fuera del repositorio** (en PruebaLumen): las 16 secuencias se copiaron a mano de
  `D:\GASP\Content\Characters\UEFN_Mannequin\Animations\Interactions\{Shoves,Takedowns}` (`M_relaxed_ragdoll_shove_stand_?_[AV]`
  y `M_relaxed_takedown_stand_?_[AV]_`, solo dependen del esqueleto UEFN) y se les quitó el root motion; `esposas.wav` se
  importa con `tools/unreal/sonidos.py` como los demás.
