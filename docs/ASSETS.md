# Assets: de Blender (y Gemini) al juego

El juego dibuja todo con cajas y cilindros hechos en código. Cada pieza repetida del mundo es un **hueco**: mientras no
exista su modelo se ve la versión de cajas; en cuanto hay un `.glb` con su nombre, el juego usa el modelo. No hay que
tocar código para cambiar una pieza.

## Flujo

1. Abre en Blender la plantilla del hueco: `assets/plantillas/<hueco>.glb` (Archivo → Importar → glTF 2.0). Tiene el
   tamaño, el origen y la orientación exactos. `referencia-persona.glb` es un guardia de 1,80 m para comparar escala.
2. Modela encima, borra la plantilla y exporta como **glTF Binary (.glb)** con el mismo nombre en `assets/models/`
   (por ejemplo `assets/models/caja.glb`).
3. `python3 tools/build-models.py` empaqueta todos los `.glb` en `assets/models/pack.js`.
4. Abre `index.html`: el modelo ya está en todas las zonas. `python3 tools/build-artifact.py` lo mete en el Artifact.

Para quitar un modelo, borra su `.glb` y vuelve a ejecutar el paso 3.

## Huecos disponibles

| Hueco | Qué es | Huella (ancho × alto × fondo, m) | Triángulos (máx.) | Notas |
|---|---|---|---|---|
| `caja` | Caja de madera de los patios | 1,8 × 1,3 × 1,8 | 400 | Tapa la vista: no la hagas más baja de 1,2 m. El juego la gira de 90 en 90 grados para que no se repita. |
| `camion` | Camión aparcado (bloque de 2 × 2 casillas) | 4 × 2,2 × 4 | 3 000 | La huella es cuadrada: un camión de 2,4 × 4 m con su lona, o camión y remolque. Es pared: no se pasa ni se ve a través. |
| `generador` | Grupo electrógeno | 1,8 × 1,4 × 1,4 (tubo de escape hasta 2,9) | 1 500 | El punto de uso (apagar y encender) está delante, hacia +Z. |
| `farola` | Poste de farola exterior | 0,3 × 3,3 × 0,3 | 300 | La bombilla encendida la pone el juego a 3,25 m de altura, en el eje del poste. |
| `torreta` | Torre del foco giratorio | 1,2 × 7 × 1,2 | 1 200 | El foco y su haz los pone el juego a 7 m, en el eje. |

La colisión y la línea de visión van por casillas de 2 × 2 m, no por la malla: el modelo no debe salirse de su huella.

## Convenio del modelo

- **Unidades:** metros. 1 unidad de Blender = 1 m en el juego.
- **Origen:** en el suelo, en el centro de la huella. Aplica las transformaciones antes de exportar (Ctrl+A → Todas).
- **Ejes:** en Blender, Z arriba y el frente del objeto mirando hacia −Y (el exportador lo convierte a Y arriba y frente +Z).
- **Materiales:** Principled BSDF con **Base Color** liso. El juego convierte cada material a cel-shading (cuatro tonos y
  contorno negro), así que rugosidad, metal y normales se ignoran. Un material por color es lo que mejor queda.
  Emisión sí se respeta (pilotos, pantallas).
- **Texturas:** opcionales, de 512 px como mucho, incrustadas en el `.glb`. Con colores planos el estilo sale más limpio.
- **Peso:** cada `.glb` por debajo de 1,5 MB. El Artifact entero no puede pasar de 16 MB y la música ya ocupa 2,5.
- **Sin animación** en estas piezas, sin cámaras ni luces.

### Ajustes de exportación en Blender (Archivo → Exportar → glTF 2.0)

- Formato: **glTF Binary (.glb)**
- Incluir: solo objetos seleccionados; sin cámaras ni luces
- Transformación: **+Y arriba** activado
- Malla: aplicar modificadores, UV y normales activados
- Material: Exportar; imágenes en Automático
- **Compresión (Draco): desactivada** (el juego no lleva descompresor)
- Animación: desactivada

## Paleta del juego

| Uso | Color |
|---|---|
| Uniforme de tropa | `#4f5a3c` |
| Casco | `#4a5a3a` |
| Hormigón | `#7a7f7c` |
| Madera | `#8c5e2c` (vetas `#4a2e12`) |
| Metal | `#5b6468` |
| Verde oliva de vehículo | `#4f5a3c` (bajos `#2f3824`) |
| Luz de sodio | `#ffb060` |
| Cielo de noche | `#070a12` |
| Agua de la excavación | `#16323e` |
| Luz de la Fuente | verde `#40ff60` atenuado |

## Modelos y retratos que ya están dentro

- `caja` y `camion` salen de `tools/blender/modelos.py`, un script de Blender (bpy) que construye el modelo, lo mide y lo
  exporta. Se ejecuta con `npm run blender` (necesita `pip install bpy`) o pegándolo en la pestaña Scripting de Blender para
  retocar el modelo a mano antes de exportar. Para cambiar una pieza, edita su función y vuelve a ejecutar.
- Retratos del códec: `assets/retratos/<personaje>.jpg` (192 × 192; `cuttlas`, `roig`, `control`, `fuente`) y
  `python3 tools/build-portraits.py`. El juego les pone el tinte verde y las líneas de la pantalla. Sin retrato, se ve el pixelado.
  El de Cuttlas está hecho con Gemini.

## Lo siguiente (aún sin hueco: se añade al llegar el primer modelo)

- **Atrezo de zona:** bote del embarcadero, antena de la torre, archivadores, escritorio con teletipo, radio, silla de
  las sesiones, columnas del templo, bidones de gasolina, verja y valla, montacargas.
- **Personajes:** una malla de guardia (los colores de uniforme los cambia el juego), Cuttlas, Roig, Alarcón y Halloran.
  Hasta 3 000 triángulos, esqueleto humanoide de unos 20 huesos y estos clips: `Idle`, `Walk`, `Run`, `Crouch`,
  `CrouchWalk`, `Aim`, `Down`. Requiere ampliar el cargador (mallas con esqueleto), así que va en un PR aparte.
- **Imagen 2D (Gemini):** retratos del códec (PNG de 192 × 192, fondo liso), ilustración de la pantalla de carga de
  cada zona (1280 × 720, WebP), fondo del menú y lámina de cada final. Cada imagen por debajo de 200 KB.
