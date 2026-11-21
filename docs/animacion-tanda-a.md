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
