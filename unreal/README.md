# Código C++ de Lost Horizon para Unreal Engine 5

Fase 2 del plan de migración: el núcleo del sigilo.

- `Source/Tarsis/TarsisGuard.h/.cpp`: guardia con ronda por puntos, vista (cono, distancia, luz y agachado),
  sospecha con «?» y «!», alerta, búsqueda, vuelta a la ronda y captura.

Por ahora se trabaja en el proyecto de prueba `PruebaLumen` (UE 5.8, plantilla de primera persona en C++):
se copia `Source/Tarsis/` a `D:\PruebaLumen\PruebaLumen\Source\PruebaLumen\Tarsis\` y se compila con el editor cerrado:

    "D:\ue_5.8\Engine\Build\BatchFiles\Build.bat" PruebaLumenEditor Win64 Development -Project="D:\PruebaLumen\PruebaLumen\PruebaLumen.uproject" -WaitMutex -NoHotReloadFromIDE

El `Build.cs` del módulo necesita `"AIModule"` y `"NavigationSystem"` en `PublicDependencyModuleNames`.

Después `tools/unreal/montar_base.py` (o `tools/unreal/guardias.py`) coloca a Ibarra y Moya con sus rondas del juego web.
No uses Live Coding en el PC de Andres: se queda colgado pidiendo unos 40 GB de memoria virtual. Compila siempre con Build.bat y el editor cerrado.

Los guardias llevan el cuerpo y las animaciones de las personas del juego web (`assets/unreal/personas/*.glb`, importadas por `tools/unreal/personas.py`): andar, quieto y apuntando. La orientación y la altura del modelo se deducen del esqueleto en reposo.
