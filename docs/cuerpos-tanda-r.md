# Tanda R: cuerpos que no se mueven raro y pelea con varios guardias

Segunda pasada de pulido del combate, sin mecánicas nuevas: solo se quita, se baja, se separa o se corrige. Trata los puntos C (cuerpos que se mueven raro) y D (pelea con varios guardias) de la lista de Andrés. El método es el de la tanda Q: medir, arreglar y volver a medir.

## 1. Cómo se midió

Hay cinco peleas jugadas por guion, en tiempo real, sobre el código de origin 60aecc2 (antes) y el de esta tanda (después):

- **uno:** un guardia. Golpe de apertura, culatazo que te da, contra y remate.
- **tres:** el mismo duelo con otros dos guardias en alerta.
- **agarre:** el guardia te agarra y te sueltas con la E.
- **pared:** contra y remate con una pared 50 cm detrás del guardia.
- **uno1:** la pelea «uno» en primera persona.

Las herramientas están en la carpeta de pruebas de la sesión, no en el repositorio:

- `registro_r.py` registra cada fotograma las manos, la pelvis, la cabeza y los pies de la malla que se ve:
  - de Cuttlas, `CuerpoCuttlas` (en primera, los brazos);
  - de cada guardia, su `Pose`.
- `analizar_r.py` saca las medidas:
  - pies que patinan en cada apoyo;
  - giros;
  - saltos de pose en cm por fotograma a 60 fps, quitando lo que se mueve el actor;
  - cuerpos metidos uno en otro;
  - dónde se colocan los demás guardias respecto a la cámara.
- Los datos están en `capturas-tandaR/diagnostico`.

## 2. Diagnóstico (antes)

Ordenado por lo que más se veía:

1. **Puñetazo y contra.** Las piezas parten de los ataques de Lyra `MM_Attack_01` y `MM_Attack_02`, que son acometidas: la raíz avanza 151 y 81 cm. Se importaron sin root motion, así que el cuerpo visible de Cuttlas se separaba de su cápsula hasta 115 cm (148 en primera persona), se metía en el guardia y volvía de golpe, con saltos de 75 a 101 cm por fotograma.
   El culatazo y las reacciones de golpe tienen la raíz quieta.
2. **Cambios de escena sin fundido:**
   - la malla del guardia saltaba a su sitio en la pareja de derribo (de 60 a 134 cm);
   - Cuttlas salía del remate de un fotograma: la mano saltaba 67 cm;
   - al soltarse del agarre, la pose de la pareja seguía congelada con la malla ya en la cápsula: la pelvis del guardia se metía 70 cm en Cuttlas.
3. **Cuerpos metidos uno en otro:** pelvis a 4 cm en el remate y a 12 cm tras el agarre.
4. **Giro del guardia** al abrir el duelo: de 400 a 500 °/s.
5. **Pies que patinan:**
   - el guardia, de 21 a 27 cm, cuando se colocaba a 120 cm (lo movía el actor, sin pasos);
   - Cuttlas, de 18 a 35 cm, por el empujón de 220 cm/s cuando le dan.
6. **Varios guardias:**
   - **Colocación:** delante de la cámara y lejos (de 24 a 40° y de 6 a 11 m); ninguno detrás ni tapando.
   - **Papeles:** el que fija y el que flanquea se intercambiaban (fijaba siempre el más cercano). Eso daba 11 órdenes de flanqueo en 11 s y un flanqueador que no paraba de corregir.

## 3. Arreglos

### Cuttlas

- **A. Puñetazo y contra rehechos en Blender** (`tools/blender/cqc_anims.py`, `clavar_pies`):
  - **Acometida:** la raíz se queda en 25 cm.
  - **Pies:** IK de dos huesos a mano, fotograma a fotograma. El IK de Blender no servía, porque en el FBX la cola de la pantorrilla no cae en el pie. Clava los pies en sus apoyos: el pie apoyado conserva el sitio que tendría al final de su apoyo, y el que va al aire reparte la diferencia.
  - **Resultado en Blender:** el pie apoyado se desliza como mucho 6,4 cm en el puñetazo y 0,6 cm en la contra.
  - **En Unreal:** se importan con root motion (`tools/unreal/cqc_piezas.py`) y `HeroRootMotionTick` se lo da a la cápsula de Cuttlas, con barrido y sin acercarse a menos de `MeleeContactDistance` − 15 cm del guardia.
  - **Lyra fuera:** el segundo puñetazo, que era `MM_Attack_02` de Lyra tal cual, se quita.
- **E. Empujón más corto:** el de cuando te dan baja de 220 a 90 cm/s (`HeroHitPushSpeed`).

### Fundidos de escena (B)

- **Entrada al remate:** la pose de la pareja de derribo se evalúa en el segundo en que empieza y la malla se lleva para que la raíz quede donde está el guardia. Cuttlas va a su sitio con la misma corrección, y lo que queda se funde en `SceneAlignSeconds` (0,2 s).
- **Salida del remate:** Cuttlas sale como montaje en la ranura del ABP, que se va en `TakedownEndBlendSeconds` (0,5 s), y su maniquí vuelve a la cápsula en ese mismo tiempo.
- **Suelta del agarre:**
  - no hay parada de golpe;
  - la reacción, con su física, sale un fotograma después;
  - y llega fundiendo.
- **Entrada del golpe de Cuttlas:** 0,15 s (`HeroStrikeBlendIn`).

### Guardia del duelo

- **C. Separación:** en el remate se aparta al guardia si las pelvis quedan a menos de `MinBodyGap` (35 cm).
- **D. Giro:** el guardia del duelo gira con un tope de `DuelTurnMaxSpeed` (180 °/s) y no se gira hacia donde anda.
- **E. Pasos:**
  - el guardia se coloca andando, con entrada de movimiento para que el GASP le ponga pasos;
  - se acerca a 95 cm en los últimos `DuelApproachSeconds` (0,45 s) de la guardia;
  - en el amago y el culatazo ya no se mueve.

### Varios guardias (F)

- **Papeles:** el que fija lo sigue siendo salvo que otro quede `FixerSwapMargin` (3 m) más cerca.
- **Ángulo de flanqueo:** se sortea una vez por alerta.
- **En su punto:** el flanqueador llega con 120 cm de holgura, no se va hasta alejarse 250 y allí se queda apuntando, sin buscar cobertura.
- **Giro de los que esperan:** 120 °/s durante el duelo (`WaitTurnSpeed`).
- **Coberturas:** ya no se buscaban otra vez mientras seguían valiendo, así que no hubo que tocarlas.
- **Relevo:** sigue como estaba. Cambiarlo sería una mecánica nueva.

## 4. Resultados

Una compilación para A–F y una segunda para lo que la primera no resolvió:

- la alineación del remate;
- la suelta del agarre;
- el giro al colocarse andando;
- el flanqueador que rondaba su punto.

Fuera de escena quiere decir sin contar el remate, el agarre ni al guardia ya derribado.

| Objetivo | Meta | Antes | Después | ¿Se cumple? |
|---|---|---|---|---|
| Pelvis de Cuttlas a su cápsula, fuera de escena | < 40 cm | 115 | 22–34 | sí |
| Saltos de manos y cabeza del guardia, fuera del contacto | ≤ 15 cm/fot | 6–85 (agarre 85) | 8,5–13,3 | sí |
| Saltos de manos y cabeza de Cuttlas fuera del contacto y de la escena del remate | ≤ 15 cm/fot | 75–101 | 17–18 (al salir del remate) | **no** |
| Saltos de Cuttlas dentro de la escena del remate (la animación de la pareja) | — | 67–83 al salir | 30 | — |
| Pelvis Cuttlas–guardia, mínimo | ≥ 35 cm | 4 (remate), 12 (agarre) | 14–26 (remate), 89 (agarre) | **no** (remate) |
| Giro del guardia del duelo | ≤ 180 °/s | 400–500 | 68 (uno); 240 antes de abrir el duelo, al darse la alarma | sí en el duelo |
| Pies del guardia por apoyo, fuera de escena | < 10 cm | 25–30 | 13–31 | **no** |
| Pies de Cuttlas por apoyo, fuera de escena | < 10 cm | 23–35 | 42–46 | **no** |
| Ningún guardia detrás de la cámara a menos de 3 m | 0 | 0 | 0 | sí |
| Órdenes de flanqueo | menos | 11 en 11 s | 5 | sí |
| Flanqueador andando después de llegar a su punto | < 2 s | 2,0 | 2,5 | **no** |
| Separación entre guardias | — | 4,99 m | 4,51 m | — |

Los de la tanda Q siguen:

- ningún disparo de otros durante el duelo;
- la guardia fija de 1,3 s;
- una sola cámara lenta.

### Lo que no se alcanza, y por qué

- **Pies de Cuttlas (42–46 cm).** El detector toma como un solo apoyo todo el tiempo que un pie no se levanta. El pie izquierdo de Cuttlas no se levanta en toda la pelea (5 s), mientras la cápsula avanza con el root motion (2 × 25 cm) y retrocede con el empujón. Dentro de las piezas los pies van clavados, pero el ABP del GASP mezcla encima la pose de guardia y ese pie no da paso. Para arreglarlo hace falta que el ABP dé pasos al moverse la cápsula, o un bloqueo de pies en Cuttlas. Es un sistema nuevo y no lo he forzado.
- **Pies del guardia (13–31 cm).** Al colocarse andando ya no da media vuelta, pero el GASP del guardia no siempre pone pasos a 6–25 cm de recorrido. Mejora respecto a antes en «uno», «pared» y «agarre» (de 25–30 a 13–21 cm), pero no baja de 10.
- **Pelvis en el remate (14–26 cm).** La pareja de derribo junta mucho los cuerpos. El empuje para separarlos la sube de 4 a 14–26 cm, pero no llega a 35 sin que el golpe deje de tocar.
- **Saltos de Cuttlas al salir del remate (17–18 cm por fotograma).** Es la salida fundida en 0,5 s de un movimiento rápido de los brazos; antes eran 67–83 cm de golpe. Dentro de la escena (30 cm por fotograma) es la propia animación de la pareja, que mueve los brazos deprisa.
- **Flanqueador (2,5 s andando después de llegar).** Ya no ronda su punto, pero al acabar el duelo se recoloca otra vez, a su punto nuevo, porque al caer el del duelo cambia quién fija.

## 5. Capturas antes y después

Los monigotes (`D:\LostHorizon\capturas-tandaR\monigote_*.png`, en el PC de Andrés; no van en el parche para no engordarlo) muestran los dos cuerpos de lado, fotograma a fotograma alrededor de un momento:

- a la izquierda, antes; a la derecha, después;
- Cuttlas en azul y el guardia en rojo;
- los fantasmas van de más claro a más oscuro con el tiempo.

Las capturas del juego de «antes» no se sacaron a tiempo: las piezas y el código ya estaban cambiados cuando se compiló. Los monigotes salen de los datos registrados en las dos versiones.

- `monigote_uno_contra.png`: la contra. Antes, Cuttlas se abalanzaba más de un metro sobre el guardia; ahora da un paso.
- `monigote_agarre_suelta.png`: al soltarse del agarre. Antes, el guardia aparecía dentro de Cuttlas; ahora se queda en su sitio.
- `monigote_uno_remate.png` y `monigote_pared_remate.png`: la entrada al remate.
- `monigote_uno_fin_remate.png`: la salida del remate.

## 6. Pruebas y rendimiento

- **Pruebas:** las 17 familias afectadas pasan 273 de 273, «tercera» incluida («agacharse y levantarse sin saltos»).
- **Rendimiento:** ver `docs/rendimiento.md`, apartado de la tanda R.
