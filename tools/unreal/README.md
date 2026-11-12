# Lost Horizon en Unreal Engine 5 (fase 1)

Plan completo: «Plan de migración a Unreal Engine 5 — Lost Horizon» (Claude Doc del proyecto).

1. `python3 tools/unreal/exportar_base.py` (necesita `pip install bpy`): genera `assets/unreal/base.glb` y `base.json`
   desde la misma escena que el visor realista, con las transformaciones aplicadas y los colores del visor.
2. En el PC con Unreal 5.8, con el editor cerrado:
   `D:\ue_5.8\Engine\Binaries\Win64\UnrealEditor.exe "<proyecto>.uproject" -ExecutePythonScript="<repo>\tools\unreal\montar_base.py"`
   Importa la base en `/Game/Tarsis/Base` y crea el nivel `/Game/Tarsis/Mapas/Tarsis` con luces, niebla y la salida de Cuttlas.
   Necesita el plugin «Python Editor Script Plugin» activo en el proyecto.

Sin texturas todavía: los materiales llevan el color, la rugosidad y la emisión del visor.
