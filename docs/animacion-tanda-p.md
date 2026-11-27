# Tanda P: impacto, sonido y piezas propias del combate

La tanda P aplica lo que repiten las charlas y los manuales de combate cuerpo a cuerpo: God of War, Sakurai, The Last of Us Part II, Bourne Conspiracy, Arkane y Epic. La investigación está en el informe de la tanda O. Son siete puntos, en el orden que pidió Andrés.

## 1. La reacción entra de golpe

**Antes:** fundido de 0,1 s hacia la reacción. Suavizaba justo el momento que tiene que doler.

**Ahora:** la víctima salta directamente a su pose de dolor. Los dos se congelan en ese fotograma con la parada de golpe (punto 2). El puente de pose se mantiene para todo lo demás.

| Ajuste | Valor | Para qué |
|---|---|---|
| `bHitReactSnapRule` | — | activa la entrada sin fundido |
| `HitReactPeakLead` | 0,03 s | la reacción arranca este tiempo antes de su pico |

Picos medidos en las reacciones de Lyra: de 0,17 a 0,50 s.

- `ATarsisGuard::HitReact`.
- En Cuttlas, `HeroReactAnim` entra sin fundido, a 0,14 s.

## 2. La parada de golpe tiembla y escala

Sigue la columna de Sakurai:

- **El que recibe** se congela y tiembla. El temblor desplaza su malla visible, empieza fuerte y se apaga.
- **El que pega** sigue al 5 %: su malla de animación va a `GlobalAnimRateScale` 0,05.
- **La duración crece con la fuerza**, con tope.
- **Todo en tiempo real.** No se toca la dilatación global: con el tiempo casi a cero, el nodo de pies del GASP daba NaN y cerraba el editor.

| Golpe | Escala | Duración |
|---|---|---|
| Bloqueado | 0,6–0,7 | 0,04–0,05 s |
| Puñetazo | 1,0 | 0,07 s |
| Empujón al fusil | 1,2 | 0,08 s |
| Culatazo recibido | 1,3 | 0,09 s |
| Contra | 1,6 | 0,11 s |
| Remate | 2,0 | 0,14 s |
| Remate contra pared | 2,3 | 0,16 s (tope) |

- Ajustes: `HitStopSeconds` 0,07, `HitStopMax` 0,16, `HitStopShake` 2,5 cm, `HitStopAttackerRate` 0,05.
- Código: `ContactHitStop(G, Escala, bGuardiaVictima)`, `ATarsisGuard::HitStop` y `HitStopTick`.

## 3. Sonido en capas

`PlayImpact(punto, fuerza, pared, atacante, voz)` hace sonar a la vez:

- **grave** (el peso del golpe), **medio** (carne y tela) y **chasquido** agudo;
- **pared**, si el golpe es contra el entorno;
- el **esfuerzo** del que pega y el **dolor** del que recibe.

Cada capa elige al azar entre 3 variantes y lleva tono aleatorio. Cuando el contacto se conoce de antemano, el sonido se adelanta `ImpactSoundLead` (0,03 s) al fotograma: puñetazo, empujón, remate y agarre.

- Generación: `tools/sonido/generar_golpes.py`. Es síntesis con numpy, sin bancos de sonidos: provisional.
- Importación: `tools/unreal/golpes.py`.

## 4. Aviso con voz

Antes de soltar el culatazo, con la culata ya arriba, el guardia grita «¡Toma!». Así el aviso tiene gesto, sonido y voz.

- La frase sale de la voz sintética de Windows, como las demás, con `TARSIS_FRASES=toma tools/sonido/generar_voces.py`.
- El contador `MeleeWarnings` registra cada aviso.

## 5. Física desde el hueso golpeado, y PhysicsControl

**Física desde el hueso** (receta de Epic): `HitReact(Dir, Fuerte, Hueso)` simula desde el hueso golpeado.

| Golpe | Hueso |
|---|---|
| Puñetazo | Cabeza (simula desde el cuello) |
| Contra | Pecho (`spine_03`) |
| Empujón | Pecho (`spine_03`) |
| Al soltarte | `spine_02` |

**PhysicsControl** es el plugin del motor que usa la muestra del GASP 5.8. Hace dos cosas:

- **Tambaleo:** motores en espacio del padre que tiran hacia la animación, más los empujones alternos.
- **Caída:** motores flojos los primeros `FallControlSeconds`, que luego se sueltan.

Detalles:

- Se activa con `bPhysicsControlRule` y se ajusta con `StaggerControlStrength` 6, `FallControlStrength` 2,5 y `FallControlSeconds` 0,7.
- Medido en la misma sesión, da los mismos fps con y sin él, con 41 MB más de VRAM, así que se queda.
- Un fallo encontrado en las pruebas y ya corregido: al acabar el fundido de la caída no se destruían los controles y el guardia no terminaba de levantarse.
- Necesita el plugin `PhysicsControl` en el `.uproject` y el módulo en el `Build.cs` (ver `unreal/README.md`).

## 6. Primera persona exagerada

- **El puño al centro:** en el contacto se desplaza `FPPunchCenterShift` (12 cm adelante, 10 cm al centro y 4 cm arriba), con forma de campana.
- **Alcance más permisivo:** `MeleeEngageRangeFP` de 215 cm, sin exigir que el guardia te encare de frente.

## 7. Piezas propias en Blender

`tools/blender/cqc_anims.py` rehace cada pieza a partir de una base:

- le da su propio ritmo, remapeando el tiempo por tramos;
- exagera las poses clave, alejando la rotación de cada hueso respecto a la pose del principio de la ventana, en el mapa exponencial.

`tools/unreal/cqc_piezas.py` exporta las bases e importa las piezas en `/Game/Tarsis/Armas/Anims/CQC`. También apunta el director del nivel a ellas: `MeleeStrikeAnimPath`, `HeroPunchAnimPaths`, `HeroCounterAnimPath`, `GrabGuardAnimPath` y `GrabHeroAnimPath`, con sus segundos clave. Las rutas son configurables y no hace falta recompilar para cambiarlas.

| Pieza | Base | Ritmo | Clave |
|---|---|---|---|
| Culatazo | MM_Rifle_Melee | sube despacio y más alta hasta 0,45 s, latigazo, seguimiento largo | arriba 0,45, contacto 0,52 |
| Puñetazo de Cuttlas | MM_Attack_01 | anticipación de 0,12 s, golpe, más alcance | contacto 0,20 |
| Contra | MM_Attack_02 | brazo izquierdo arriba cubriendo y el derecho que entra | contacto 0,22 |
| Agarre (pareja) | empujón F del GASP | hasta las manos encima, antes del empujón; tirón | manos 0,40 |

La pareja del agarre sale en el espacio de Cuttlas: su raíz en el origen en el fotograma 0, y el guardia a 86 cm delante, de cara a él. Al rebasar, la raíz de Unreal es el objeto de la armadura en Blender, no un hueso.

## Pruebas

`prueba_contacto` comprueba además:

- que el golpe suena en 3 capas o más;
- que las piezas propias están puestas;
- que el aviso lleva voz;
- que el tambaleo usa PhysicsControl;
- que la reacción entra sin fundido.

La familia `fisica` pasa con el límite de 40 cm de la tanda O.
