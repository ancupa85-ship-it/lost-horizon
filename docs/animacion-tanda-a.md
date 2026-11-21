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
