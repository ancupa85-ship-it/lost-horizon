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
  (`ShouldTurnInPlace`). Si se quiere que gire las piernas parado, se puede activar `WantsToAim` un momento cuando el
  desfase pase de unos 100°.
