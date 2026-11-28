# Tanda T3: mano del remate y fotograma de la caída

Último cierre de la tanda T, sin mecánicas nuevas, en una sola compilación. Base: origin 3a82805. Medido con la mediana de tres pasadas de las peleas «uno», «tres» y «pared» (`capturas-tandaR/diagnostico/mediana_jT.txt`; el «antes» es `mediana_iT.txt`).

## Cambios

- **Raíz de Cuttlas en el remate.** La copia que se ve de Cuttlas (`CuerpoCuttlas`, retargeteada) tampoco llevaba la raíz de su parte de la pareja de derribo, que avanza unos 32 cm en el golpe. Ahora el maniquí que conduce se mueve con la raíz de la pista de su parte (A), en la posición del montaje, igual que el guardia desde la T2 (`TSAAnim`, con el mismo interruptor `bTakedownRootFollowRule`).
- **Fotograma de la caída.** Al pasar a ragdoll, la malla vuelve a la pareja. La copia que se ve del guardia se queda ahora donde estaba durante dos fotogramas, hasta que coge la pose de la física (`ATarsisGuard::HoldVisibleOffset`). Antes salía esos fotogramas en el origen de la pareja, encima de Cuttlas.

## Resultados

Mediana de tres pasadas, en el orden uno, tres, pared:

| Objetivo | Meta | Antes (3a82805) | Después (T3) | ¿Se cumple? |
|---|---|---|---|---|
| Mano de Cuttlas a la cabeza o la pelvis del guardia en el contacto | < 20 cm | 54, 57, 54 | 28, 34, 31 | **no** (se acerca 20–25 cm) |
| Pelvis al caer el guardia | ≥ 35 cm | 6–8 | 112–127 | **sí** |
| Pelvis, mínimo de toda la pelea | ≥ 35 cm | 7,5, 8, 16 | 19, 15, 26 | **no**: ahora el mínimo está en el primer fotograma del remate (ver abajo) |
| El guardia tapa a Cuttlas en el remate | igual o menos | 3, 6, 3 % | 4, 6, 4 % | sí |
| Pies de Cuttlas por apoyo | < 10 cm | 4, 7, 2,5 | 5, 22, 2,5 | sí en «uno» y «pared»; en «tres» una pasada se va a 22 (rango 2–25) |

## Lo que queda, documentado sin forzar

- **Primer fotograma del remate.** La malla del guardia se coloca en la pareja sin la raíz, y la raíz se le da en el tick siguiente. Durante ese primer fotograma la copia visible sale en el origen de la pareja (pelvis a 22–26 cm de Cuttlas) y luego el puente de pose la lleva a su sitio en unos 0,1 s. El arreglo sería dar la raíz ya en `TakedownSceneBegin`, antes del puente de pose: una línea, pero otra compilación.
- **La mano (28–34 cm, meta 20).** Con la raíz de Cuttlas se acerca 20–25 cm. Lo que falta puede ser la pareja misma, que en el GASP no está hecha para estos esqueletos, o el retarget de los brazos. No lo he investigado más.

## Pruebas

Las familias afectadas, las de movimiento y «tercera»: 300 de 300. Ninguna falla. Hay una comprobación menos que en la T2 (301), sin fallos que lo expliquen. No he localizado cuál: no lo atribuyo a esta tanda sin verlo. No hay medida de noche: solo cambia el remate.
