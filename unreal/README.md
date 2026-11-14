# Código C++ de Lost Horizon para Unreal Engine 5

Fase 2 del plan de migración: el núcleo del sigilo.

- `Source/Tarsis/TarsisGuard.h/.cpp`: guardia con ronda por puntos, vista (cono, distancia, luz y agachado),
  sospecha con «?» y «!», alerta, búsqueda, vuelta a la ronda y captura.
- `Source/Tarsis/TarsisDirector.h/.cpp`: luz del jugador, agacharse con C, mensajes y captura (calabozo la primera vez).
- `Source/Tarsis/TarsisHUD.h/.cpp`: HUD dibujado con el Canvas (luz, postura, alerta, marcas de guardias fuera de pantalla, mensajes).

Por ahora se trabaja en el proyecto de prueba `PruebaLumen` (UE 5.8, plantilla de primera persona en C++):
se copia `Source/Tarsis/` a `D:\PruebaLumen\PruebaLumen\Source\PruebaLumen\Tarsis\` y se compila con el editor cerrado:

    "D:\ue_5.8\Engine\Build\BatchFiles\Build.bat" PruebaLumenEditor Win64 Development -Project="D:\PruebaLumen\PruebaLumen\PruebaLumen.uproject" -WaitMutex -NoHotReloadFromIDE

El `Build.cs` del módulo necesita `"AIModule"`, `"NavigationSystem"`, `"LevelSequence"` y `"MovieScene"` en `PublicDependencyModuleNames` (los dos últimos, para las cinemáticas que crea `tools/unreal/cinematicas.py`).

Después `tools/unreal/montar_base.py` (o `tools/unreal/guardias.py`) coloca a Ibarra y Moya con sus rondas del juego web.
No uses Live Coding en el PC de Andres: se queda colgado pidiendo unos 40 GB de memoria virtual. Compila siempre con Build.bat y el editor cerrado.

Los guardias llevan el cuerpo y las animaciones de las personas del juego web (`assets/unreal/personas/*.glb`, importadas por `tools/unreal/personas.py`): andar, quieto y apuntando. La orientación y la altura del modelo se deducen del esqueleto en reposo.

### Vestuario (rostros que no se ven)

Los cuerpos sin equipo (MakeHuman, tal como salen del visor) están en `assets/unreal/personas/sin_equipo/`. `python3 tools/vestuario/vestir.py [nombre ...]` (solo numpy y Pillow, sin Blender) los viste y escribe `assets/unreal/personas/<nombre>.glb`: pasamontañas con la ranura de los ojos, guantes, uniforme reteñido a verde oliva y, según el guardia (tabla `EQUIPO`), casco, gorra, braga, capote con o sin capucha, correaje o cinturón. Las prendas se añaden como mallas del mismo esqueleto; huesos y animaciones quedan intactos, así que `personas.py` las importa igual (carpeta nueva por huella del archivo) y `animaciones.py` vuelve a preparar el andar.

Seis siluetas: Ibarra (capote y capucha), Moya (casco y correaje), Peris (gorra), Vega (cuerpo de Moya, casco y capote), Ramos (cuerpo de Peris, casco) y el centinela de las torres (cuerpo de Ibarra, casco y capote).

Ojo: el esqueleto es el mismo en los tres cuerpos y no coincide con las mallas (codos y hombros hasta unos 8 cm fuera en Ibarra y Moya). Las medidas de las prendas se toman de la malla, no de los huesos.

### Perímetro, portones y camino (tanda 20)

`tools/unreal/exportar_base.py` exporta la base con el muro perimetral 10 casillas (20 m) más afuera que el plano del juego (`LH_EXT`, por defecto 10; con `LH_EXT=0` sale la base original, idéntica). Lo levanta `build_exterior()` en `tools/blender/escena_base.py`: muro nuevo de 112 × 96 m, portón de entrada al oeste (hoja corredera cerrada) y de salida al este (hoja corrida), cada uno con su garita y su báculo; un camino de 6 m que cruza de portón a portón por la franja sur y sigue fuera por un terraplén sobre la marisma, y el portillo de la marisma en el muro sur. El tabique entre el patio norte y la zona este llega hasta el muro nuevo y tres vallas con paso agachado cruzan el anillo, para que no sirva de atajo entre zonas.

Dentro del muro antiguo no se mueve nada: el plano (`map`) y sus coordenadas son los mismos. Donde un edificio se apoyaba en el muro (barracón y jefatura del oeste) queda su pared trasera, con la cara interior donde estaba. Todo lo nuevo está descrito en `base.json` → `ext`, en metros del plano (x al este, y al sur; en Unreal, × 100): límites `x0 x1 y0 y1`, `entrada` y `salida` (`pos`, `garita`, `farol`, `barrera`, `meta`), `camino`, `portillo`, `vallas` y `tabiques`. Materiales nuevos: `lh_camino` (losa de hormigón) y `lh_tierra` (grava del anillo).

En el juego: la salida es el portón este (`ExitLoc` 9050, 5700, radio 420; sin el expediente sale el aviso «NO PUEDES IRTE TODAVIA») y el portillo de la marisma está en el muro sur (`WicketLoc` 310, 7390). Los dos, la barrera de la garita de salida y su farol se ponen desde `mision1.json` → `ajustes.director` (`exit_loc`, `exit_radius`, `wicket_loc`, `exit_barrier_*`; `mision.py` pasa los `[x, y, z]` a vectores). `tools/unreal/perimetro.py` pone el tope invisible fuera del portón de salida (`Tope_Salida`, 1 × 8 × 4 m en 9280, 5700) para que no se salga andando por el terraplén sin acabar la misión.

### Vida y luz en el perímetro (tanda 21)

- **Farolas del camino y aplique del portillo.** `build_exterior()` pone tres báculos en el lado sur del camino con el brazo hacia el norte (`ext.farolas`) y una bombilla de pared sobre el portillo (`ext.portillo_luz`). `exportar_base.py` añade sus luces al final de `lights`, para que los índices de las anteriores (y las etiquetas `<nombre>_<índice>` del nivel) no se muevan. Las farolas son focos hacia abajo de 55°: dejan charcos de luz de unos 5 m de radio y 15 m de sombra entre uno y otro. El aplique (`aplique_18`, radio 7 m, sin sombras) alumbra la puerta y poco más.
- **Tela de las vallas.** Antes era una placa translúcida gris al 35 % (parecía cristal). Ahora `montar_base.py` → `tela_malla()` crea `M_TelaMalla_<md5>`: material recortado (masked, dos caras) con la textura `assets/unreal/texturas_propias/tela_metalica.png` (rombos de 8 cm, alambre de 4,5 mm; la genera `tools/texturas/tela_metalica.py`) proyectada desde la posición del mundo, 32 cm por repetición. No da sombra. Si la textura no se puede importar, se queda la placa translúcida de antes y sale un aviso.
- **Guardias del anillo** (`guardias.py`): Lobato en la garita de entrada, Sanz en el control de salida y Carmona de ronda por el anillo sur. Ninguno pisa el camino. Llevan el cuerpo del centinela y voz propia (`generar_voces.py`, solo en Windows).
- **Camión de suministros** (`ATarsisDirector`, categoría «Tarsis|Camion»). El modelo (`camionmovil_*`) y la hoja del portón de entrada (`hojaentrada_*`) van en `base.glb` con el origen en el origen del mundo; `montar_base.py` los deja móviles, sin navegación y con las etiquetas de actor `camion` y `hoja_entrada`, que es por donde los encuentra el director. Estados (`TruckState`): 0 espera fuera, 1 llega al portón, 2 parado mientras la hoja se corre (5 s), 3 cruza la base a 4 m/s, 4 parado 6 s en el control hasta que sube la barrera, 5 sale. Los tiempos y la velocidad están en `mision1.json` → `ajustes.director` (`truck_first_delay`, `truck_interval`, `truck_speed`); `bTruck` lo apaga y `bTruckShadows` quita la sombra de sus faros (una sola luz, con la etiqueta `camion`, que el apagón del generador no toca). En el juego: los faros cuentan como luz para los guardias; el conductor toca el claxon si te ve de pie en el haz (a menos de 22 m, la mitad agachado) o si le cortas el paso, y los guardias a menos de 45 m van a mirar; frena ante cualquier personaje que tenga delante. `TruckSkipWait()` lo hace salir ya (pruebas y pruebas a mano).
- **Topes.** `perimetro.py` pone también `Tope_Entrada` (-2010, 5700): con la hoja abierta para el camión no se sale andando por el terraplén.
- **Grava a 1K.** `materiales.py` limita `gravel_floor_02` a 1024 px (`LADO_MAX`) para aliviar la memoria de vídeo.
- **Sonidos nuevos** (`generar_sonidos.py`): `camion_motor` (bucle), `claxon` y `porton`.
- **Pruebas**: familia nueva `anillo` y `camion` en `pruebas.py`; en las demás el camión va apagado y los centinelas del anillo se dejan quietos donde la prueba planta al jugador a su lado. `medir.py` añade el sitio «camino con el camion».

## Sonidos

`tools/sonido/generar_sonidos.py` sintetiza los .wav (pasos de gravilla y cemento, piedra, dardo, viento y lluvia) en `assets/unreal/sonidos`, y `tools/unreal/sonidos.py` (Python del editor) los importa en `/Game/Tarsis/Sonidos`. El director los carga por su ruta: si faltan, el juego va igual pero mudo.
