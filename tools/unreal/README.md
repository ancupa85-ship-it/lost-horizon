# Lost Horizon en Unreal Engine 5 (fase 1)

Plan completo: «Plan de migración a Unreal Engine 5 — Lost Horizon» (Claude Doc del proyecto).

1. `python3 tools/unreal/exportar_base.py` (necesita `pip install bpy`): genera `assets/unreal/base.glb` y `base.json`
   desde la misma escena que el visor realista, con las transformaciones aplicadas y los colores del visor.
2. En el PC con Unreal 5.8, con el editor cerrado:
   `D:\ue_5.8\Engine\Binaries\Win64\UnrealEditor.exe "<proyecto>.uproject" -ExecutePythonScript="<repo>\tools\unreal\montar_base.py"`
   Importa la base en `/Game/Tarsis/Base` y crea el nivel `/Game/Tarsis/Mapas/Tarsis` con luces, niebla y la salida de Cuttlas.
   Con el editor ya abierto, también vale escribir en la consola (Cmd): `py "<repo>\tools\unreal\montar_base.py"`.
   Necesita el plugin «Python Editor Script Plugin» activo en el proyecto.

Sin texturas todavía: los materiales llevan el color, la rugosidad y la emisión del visor.

## Aspecto final por zonas (tanda 18: el barracón oeste)

Con el editor abierto y el nivel Tarsis cargado, en este orden (cada uno se puede repetir: quita lo suyo y lo vuelve a poner):

1. `py tools/unreal/materiales.py` (si cambia el maestro M_LH: ahora lleva suciedad, manchas de ruido y zócalo sucio).
2. `py tools/unreal/atrezo.py`: descarga de Poly Haven (CC0) los modelos de `assets/unreal/atrezo.json` (no van a git),
   los importa en `/Game/Tarsis/Atrezo` (una malla por modelo, con LOD, colisión simple y texturas de 1024), quita de las
   mallas fusionadas de la base los muebles de Blender de esa zona («vaciar») y coloca las piezas.
3. `py tools/unreal/ambiente.py`: la taquilla de chapa (Geometry Script), las luces de la zona, sus sonidos (zumbido,
   radio, gotera), el posprocesado y las manchas. Necesita el plugin **GeometryScripting** activo en el proyecto.
4. Reconstruir la navegación (`RebuildNavigation`) y guardar el nivel.

Para comprobar: `py tools/unreal/medir.py` (fps y VRAM en tres sitios; tabla en `docs/rendimiento.md`),
`py tools/unreal/capturas.py <prefijo>` (tres cámaras fijas, en `Saved/Capturas`) y `py tools/unreal/pruebas.py`.
Los sonidos nuevos salen de `python tools/sonido/generar_sonidos.py` (fluorescente, radio_barracon, gotera) y se importan
con `py tools/unreal/sonidos.py`.
