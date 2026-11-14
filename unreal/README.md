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

## Sonidos

`tools/sonido/generar_sonidos.py` sintetiza los .wav (pasos de gravilla y cemento, piedra, dardo, viento y lluvia) en `assets/unreal/sonidos`, y `tools/unreal/sonidos.py` (Python del editor) los importa en `/Game/Tarsis/Sonidos`. El director los carga por su ruta: si faltan, el juego va igual pero mudo.
