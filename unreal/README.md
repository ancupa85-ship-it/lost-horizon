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

## Sonidos

`tools/sonido/generar_sonidos.py` sintetiza los .wav (pasos de gravilla y cemento, piedra, dardo, viento y lluvia) en `assets/unreal/sonidos`, y `tools/unreal/sonidos.py` (Python del editor) los importa en `/Game/Tarsis/Sonidos`. El director los carga por su ruta: si faltan, el juego va igual pero mudo.
