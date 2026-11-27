# Tanda O: acabado de animación y contacto del combate

Sin mecánicas nuevas: solo cómo se ve y cómo se siente lo que ya había (tandas M, N1 y N2). Primero el diagnóstico, fotograma a fotograma, y después los arreglos.

## Diagnóstico

Secuencias fotograma a fotograma, en tercera persona (cámara fija de lado) y en primera, de:

- el empujón al fusil;
- el golpe H, el amago, el culatazo, la parada con Alt y el tambaleo;
- el agarre y el forcejeo;
- el remate a dos cuerpos, por la espalda y contra la pared;
- la caída con física y el levantarse.

Están en `D:\LostHorizon\capturas-tandaO`: `antes_*`, `despues_*` y las hojas de contactos en `hojas` y `hojas_despues`. Las capturas del diagnóstico las hace un script del scratchpad. Las hojas las monta `hoja.ps1` con System.Drawing.

Las medidas de la animación salen de `get_bone_pose_for_time`, componiendo la cadena de huesos: la mano derecha, máxima extensión y altura.

| Animación | Arriba del todo | Contacto |
|---|---|---|
| MM_Attack_01 | — | 0,42 s |
| MM_Attack_02 | — | 0,40 s |
| MM_Rifle_Melee | 0,27 s | 0,34 s |

### Fallos encontrados

1. **Tu golpe H:** en tercera, Cuttlas no hacía nada. En primera, el empujón procedural apenas entraba en la imagen.
2. **Amago y culatazo:** eran la misma animación a 0,45 y a 1,5. Con ×1,5 la culata llegaba unos 0,06 s después de empezar el culatazo, pero el resultado (te da o lo paras) se decidía a 0,35 s.
3. **El culatazo no llegaba:** a 140 cm, la culata se quedaba a unos 50 cm.
4. **Saltos de pose:** cada cambio entre el ABP del GASP y una animación suelta saltaba de golpe.
5. **Tambaleo:** el guardia se quedaba de pie, quieto.
6. **Agarre:** no tenía ninguna animación.
7. **Empujón al fusil:** la reacción y el fusil salían al pulsar, 0,25 s antes del contacto.
8. **Remates:** la malla de Cuttlas saltaba al sitio de la pareja mientras la cápsula aún se abalanzaba.
9. **Remate contra la pared:** el cuerpo salía disparado por encima del muro.
10. **Ragdoll:** tras caer, seguía agitándose.
11. **Cuerpo de la plantilla:** con otra cámara se veía blanco junto a Cuttlas. En el juego pasa con la cámara de escena de la detención en primera persona.
12. **Cierre del editor:** con el tiempo global a 0,0001, `AnimNode_FootPlacement` del GASP da NaN y el editor se cierra (`!PelvisTransformCS.ContainsNaN()`). Por eso la parada de golpe no toca el tiempo del juego.

## Arreglos

| Qué | Dónde | Ajustes |
|---|---|---|
| Puente de pose: la pose que se ve, fundida con la nueva al cambiar de animación | `TarsisFisica.cpp` (`PoseBridge`, `BridgeTick`); llamadas en `ScenePlay`, `SceneEnd`, `HitReact`, `GaspSingle`, `GaspRestore` | `bPoseBridgeRule`, `PoseBridgeSeconds` 0,18 (reacción 0,1) |
| Parada de golpe: congela las animaciones del guardia y de Cuttlas (`bPauseAnims`), en tiempo real | `ATarsisGuard::HitStop`, `ATarsisDirector::ContactHitStop` | `bHitStopRule`, `HitStopSeconds` 0,06 |
| Tu golpe en tercera: puñetazo de Lyra en la ranura `DefaultSlot` del GASP, mezclado; el puño llega `HeroContactLead` tras la H y el efecto va ahí | `HeroStrikeAnim`, `ContactTick` (`TarsisDuelo.cpp`) | `bHeroStrikeAnimRule`, `HeroContactLead` 0,12 |
| Tu golpe en primera: el mismo puñetazo en los brazos de la vista | `ArmsPunch`, `ArmsTick` | — |
| Amago: sube despacio hasta arriba y se queda; el culatazo baja de golpe justo para el contacto y el guardia se echa encima | `DuelTick` | `MeleeWindupAt` 0,27, `MeleeContactAt` 0,34, `MeleeContactDistance` 95 |
| La contra: tu puño en el fotograma de la parada; si te da, reacción fuerte de Lyra en Cuttlas | `HeroStrikeAnim(0)`, `HeroReactAnim` | — |
| Tambaleo: física blanda de cintura arriba y empujones alternos | `StaggerSway`, `PhysicsTick` | `StaggerBlend` 0,6, `StaggerImpulse` 160, `StaggerKickEvery` 0,38 |
| Agarre: pareja de empujón del GASP parada justo antes del empujón (manos encima) y forcejeo a tirones | `GrabSceneBegin`, `GrabSceneTick`, `GrabSceneEnd` (`TarsisCapturaEscena.cpp`) | `GrabReachSeconds` 0,3, `GrabJitterEvery` 0,13, `GrabJitterAmount` 0,05 |
| Empujón al fusil: reacción, golpe y parada en el contacto | `DisarmSceneTick` | — |
| Cuttlas al entrar en una pareja: su malla va del sitio de antes al de la pareja mientras se abalanza | `DisarmSceneTick`, `TakedownSceneTick` | — |
| Pared y ragdoll: sin empujón doble contra la pared, tope al salir de lo que solapa, frenado de la pelvis y amortiguación | `StartRagdoll`, `PhysicsTick` | `RagdollMaxDepenetration` 120, `RagdollMaxSpeed` 650, `RagdollAngularDamping` 1,5, `RagdollLinearDamping` 0,2 |
| Cuerpo de la plantilla oculto con la cámara de escena (sigue dando sombra) | `SceneCameraBegin`, `SceneRestore` | — |
| Brazos de primera con mangas del traje y manos de piel | `tools/unreal/brazos_cuttlas.py`, `ArmsMeshPath` | — |

### Los brazos de primera persona

Son una copia de `SKM_Manny_Simple` con un material propio. Las manos se separan por la posición en la pose de referencia: `PreSkinnedPosition`, que pasa por un `VertexInterpolator` porque solo existe en el sombreador de vértices. No lleva texturas nuevas.

### Fuentes

Consultadas solo como idea, sin copiar código; todas MIT:

- CronusHitstop: la parada de golpe por actor.
- ALS-Refactored: la cámara disparada por notify y el levantarse desde la pose congelada del ragdoll.
- Vaei/ProcHitReact: las reacciones con física parcial.

No encontré ningún ejemplo de MotionWarping en pareja con licencia permisiva. La alineación se hace a mano, con los datos de las parejas del GASP (`TarsisCapturaDatos.inl`).

### Pruebas

`prueba_contacto` (familia `contacto`) comprueba:

- el puñetazo en tercera y en primera;
- que el efecto llega con el puño y no al pulsar;
- la contra con tambaleo físico y parada de golpe;
- el puente de pose;
- el agarre con pareja y la suelta;
- el remate contra la pared sin salir volando.
