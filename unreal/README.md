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
- **Camión de suministros** (`ATarsisDirector`, categoría «Tarsis|Camion»). El modelo (`camionmovil_*`) y la hoja del portón de entrada (`hojaentrada_*`) van en `base.glb` con el origen en el origen del mundo; `montar_base.py` los deja móviles, sin navegación y con las etiquetas de actor `camion` y `hoja_entrada`, que es por donde los encuentra el director. Estados (`TruckState`): 0 espera fuera, 1 llega al portón, 2 parado mientras la hoja se corre (5 s), 3 cruza la base a 4 m/s, 4 parado en el control hasta que sube la barrera (desde la tanda 22, hasta que un guardia mira los papeles), 5 sale. Los tiempos y la velocidad están en `mision1.json` → `ajustes.director` (`truck_first_delay`, `truck_interval`, `truck_speed`); `bTruck` lo apaga y `bTruckShadows` quita la sombra de sus faros (una sola luz, con la etiqueta `camion`, que el apagón del generador no toca). En el juego: los faros cuentan como luz para los guardias; el conductor toca el claxon si te ve de pie en el haz (a menos de 22 m, la mitad agachado) o si le cortas el paso, y los guardias a menos de 45 m van a mirar; frena ante cualquier personaje que tenga delante. `TruckSkipWait()` lo hace salir ya (pruebas y pruebas a mano).
- **Topes.** `perimetro.py` pone también `Tope_Entrada` (-2010, 5700): con la hoja abierta para el camión no se sale andando por el terraplén.
- **Grava a 1K.** `materiales.py` limita `gravel_floor_02` a 1024 px (`LADO_MAX`) para aliviar la memoria de vídeo.
- **Sonidos nuevos** (`generar_sonidos.py`): `camion_motor` (bucle), `claxon` y `porton`.
- **Pruebas**: familia nueva `anillo` y `camion` en `pruebas.py`; en las demás el camión va apagado y los centinelas del anillo se dejan quietos donde la prueba planta al jugador a su lado. `medir.py` añade el sitio «camino con el camion».

### Camino gastado y viaje en el camión (tanda 22)

**Arte: que el camino y el anillo parezcan usados.**

- **Losa.** `desgaste_camino()` en `escena_base.py` añade al camino juntas de dilatación selladas con alquitrán, grietas reparadas y parches (`ext.desgaste` en `base.json`; material `lh_alquitran`, que `superficies.py` trata como cemento).
- **Hierbajos.** `exportar_base.py` → `hierbajos()` siembra 545 matas (dos planos cruzados cada una, 4 360 triángulos en total, una sola malla `hierbajos`) al pie de las vallas y de los muros, en los bordes del camino y del terraplén, alrededor de hitos, báculos y garitas y en las juntas de la losa. La textura es `assets/unreal/texturas_propias/hierbajo.png` (cuatro matas en 2 × 2: hierba seca alta, mata verde, cardo y roseta; la genera `tools/texturas/hierbajo.py`). `montar_base.py` → `hierbajo_material()` crea `M_Hierbajo_<md5>`: recortado, sin sombra, sin colisión ni navegación, y con un vaivén de viento de un par de centímetros que pesa más en la punta que en la raíz. Las caras van duplicadas con el giro contrario y la normal hacia arriba, para que la luz les dé igual por los dos lados. Si el material no se puede crear, la malla se esconde y sale un aviso.
- **Manchas.** `perimetro.py` → `manchas()` pone calcomanías (etiqueta `mancha_perimetro`, material `M_Mancha` de `ambiente.py`, una instancia por tipo en `/Game/Tarsis/Materiales/Manchas/MI_Per_*`): rodadas por donde pisan las ruedas del camión, aceite donde se para y goterones por el carril, barro que mete por la entrada, cercos de agua junto a los bordillos y humedad al pie del muro. Cada vez que se ejecuta borra las suyas y las pone de nuevo.
- **Camión y hoja del portón.** El material maestro `M_LH` proyecta desde la posición del mundo, y en algo que se mueve la textura resbala. `materiales.py` (sección 2b) crea `M_LH_Movil`, que usa las UV en metros que ya traen las piezas, con óxido en la pintura y una máscara de barro que sube desde el suelo hasta la altura que diga cada pieza (bajos y ruedas hasta arriba, la chapa solo en la parte baja). Instancias `MI_<pieza>_camion` y `MI_<pieza>_hoja` (tabla `MOVIL`). Las piezas móviles no reciben calcomanías.

**Juego: la caja del camión.**

- **Subir.** La caja va hueca, con la trasera abierta y la carga contra el frontal. Con el camión dentro de la base y al paso (cruzando o parado en el control), detrás de él sale «E SUBIR A LA CAJA DEL CAMION» (`CanBoardTruck()`, `BoardTruck()`). Dentro vas oculto (los guardias no te ven), miras por la trasera y el camión te lleva (`bRiding`, `RidePlace()`). Con E te bajas por detrás (`LeaveTruck()`); saltar en marcha hace ruido para los que estén a menos de 10 m. Si un guardia en alerta te vio subir, te saca al llegar a la trasera (como en las taquillas).
- **El control.** Ya no levantan la barrera desde lejos (`TruckControlTick()`, fases en `TruckCheck`): el guardia de ronda más cercano (Sanz, si está) deja la ronda con un recado (`ATarsisGuard::Errand()`), va a la puerta del conductor y mira los papeles (`TruckPapersTime`, 4,5 s). Con la base tranquila da paso. Con la base en guardia (`BaseState() >= 1`) rodea el camión y mira la caja: si vas dentro, te saca. Si no hay quien vaya, el conductor toca el claxon a los `TruckHornWait` segundos (y los guardias que lo oyen se acercan) y a los `TruckSelfWait` levanta la barrera él. Mientras el guardia está en la cabina, su ronda queda sin nadie y el camión le tapa el lado sur del camino.
- **Salir.** Con el expediente, el camión te saca de la base: final propio (`final_salida_camion`), línea nueva en el parte y `bByTruck` en la partida de la misión 2 («en el control registran todos los camiones»). Sin el expediente, te bajas cuando sube la barrera.
- **Voces y sonido.** Tres frases nuevas por guardia (`papeles`, `pase`, `registro`) y el sonido `camion_subir`.
- **Pruebas.** `prueba_desgaste` (losa, hierbajos, manchas y materiales del camión), el control en `prueba_camion` y `prueba_viaje` (subir, viajar, saltar, papeles sin que te vean, bajarte sin el expediente, registro con la base en guardia y final en la caja). La prueba del perímetro ya no llama a `find_path_to_location_synchronously`, que hacía saltar un aviso del motor con ventana de informe de errores.

### Agua en el suelo y en los muros, y la caja del camión por dentro (tanda 23)

**Arte: suelo y muros con vida.**

- **Charcos.** `ambiente.py` → `material_charco()` crea `M_Charco`: una calcomanía de agua quieta (contorno irregular hecho con ruido del mundo, color oscuro, rugosidad 0,05 y relieve plano), que es la que refleja las farolas. Usa mezcla translúcida, que escribe color, rugosidad y relieve solo dentro de la máscara; la mezcla hay que ponerla antes que el dominio de calcomanía o la primera compilación falla. Con `CHARCO_NORMAL = False` queda un charco de alfa compuesto, que solo vale de reserva: no refleja. `perimetro.py` pone 18 fijos (uno o dos al lado de cada farola del camino, en cuatro de los cercos de los bordillos, tres turbios en la grava del anillo sur y uno junto a cada farola de los patios, en una casilla despejada del plano) y 22 más con la etiqueta `lluvia`, que el director solo enseña cuando llueve (`RainDecals`).
- **Regueros en el muro.** `material_chorreton()` → `M_Chorreton`: hilos verticales oscuros que bajan desde lo alto del muro, a grupos y cada uno con su largo. El dibujo sale de la posición en el mundo, no de las UV de la calcomanía, así que vale para un muro que mire a cualquier lado y no se repite. 40 cajas en las cuatro caras de dentro del muro y dos en cada garita (parámetros `Techo`, `Largo`, `Contraste` por instancia).
- **Mezclas con Substrate.** El proyecto usa `r.Substrate=True`, y ahí una calcomanía de alfa compuesto suma su color a lo de debajo: no oscurece. Por eso `M_Mancha` y `M_Chorreton` usan la mezcla modulada con el color tal cual y la máscara en la opacidad, que oscurece solo dentro de la mancha y no deja ver la caja. El detalle y las medidas están en `docs/rendimiento.md`.
- **Juntas que rezuman.** Ocho bandas oscuras (`MI_Per_Junta`) sobre juntas de verdad de la losa (una cada 6 m).
- **Hierbajos.** Paleta más apagada y briznas muertas en `tools/texturas/hierbajo.py`; `hierbajo_material()` añade un tinte y rodales (zonas más secas y más verdes según la posición), sube la rugosidad y borra los `M_Hierbajo_*` de tandas anteriores. Los ajustes están en `HIERBA_AJUSTES` (`montar_base.py`).
- **Suciedad por superficie.** `SUCIEDAD` en `materiales.py` da a cada instancia su dosis (el camino, más). `RUIDO_RAPIDO` hace que el ruido del maestro `M_LH` use la variante de una sola lectura por nivel.
- La clase `Grafo` de `ambiente.py` monta estos materiales nodo a nodo, con una marca de versión: si el material ya está en esa versión no se toca, y las conexiones que fallen salen en el registro como `AVISO`.

**Sensación: el viaje en la caja.**

- **Interior.** `truck()` en `escena_base.py` añade bancos de tablas a los lados, respaldo, correas colgando del último arco, un farol apagado, un rollo de cuerda y un cajón con una lona doblada.
- **Juntas.** Cada eje del camión que pisa una junta de la losa (`TruckJointPitch`, `TruckJointPhase`) da un golpe (`camion_junta`): se oye desde fuera, que avisa de por dónde va el camión, y dentro sacude la vista (un muelle amortiguado). `TruckJoints` las cuenta.
- **Inercia.** Al frenar el cuerpo se va hacia la cabina y al arrancar hacia el portalón (`TruckFeel()`); parado en el control queda el temblor del motor. `RideOffset()` da lo que se mueve la vista.
- **Sonido.** Bajo la lona el viento, la lluvia, los grillos y el generador bajan a la mitad y pierden los agudos (filtro paso bajo), el motor se oye a través de la cabina y suena un bucle propio de tablas, lona y hebillas (`camion_caja`), más fuerte cuanto más corre el camión. `RideMuffle()` va de 0 (fuera) a 1 (dentro).
- **Luz.** Una luz de relleno muy tenue (`RideFillLumens`, 18 lm, sin sombras, radio 3 m) deja ver la caja. Es un componente del director, no una luz del nivel: no cuenta para `LightAt` y solo existe mientras viajas.

**Memoria de vídeo.** `py tools/unreal/memoria.py` hace el inventario de las texturas de `/Game` (tamaño, formato, lo que ocupan con todos sus niveles, quién las usa y lo que se ahorraría limitándolas a 1K). No cambia nada: resumen en el registro y lista completa en `Saved/Tarsis/memoria.json`.

**Pruebas.** `prueba_charcos` (charcos fijos y de lluvia, regueros en las cuatro caras, juntas en su sitio, un solo material de hierbajos, la mezcla de cada material) y, en `prueba_viaje`, el traqueteo, la luz, el sonido apagado y el golpe de cada eje en cada junta.

### Puertas, lluvia que moja, carteles, cobertura y gestos (tanda 24)

**Puertas (fallo arreglado).** No se podía salir del archivo de pie. La malla `base_pared` lleva Nanite y colisión «compleja como simple»: la colisión compleja sale de la malla de reserva de Nanite, y esa malla, simplificada en automático, había bajado los dinteles de 2,20 m a entre 1,85 y 2,15 m. La cápsula de pie no cabía; agachado se pasaba. `montar_base.py` deja ahora la reserva de Nanite de las mallas de estructura sin simplificar (error relativo 0) y `prueba_puertas` cruza las puertas de pie en los dos sentidos. Lección: con colisión compleja, la reserva de Nanite es la colisión.

**Arte: la lluvia moja la base entera.**

- **Mojado.** `materiales.py` crea la colección `MPC_Tarsis` con el escalar `Mojado`. El maestro `M_LH` lo multiplica por el parámetro `Mojable` de cada instancia (tabla `MOJABLE`: 1 en suelo, camino, tierra, tejados y contenedores; 0,6 a 0,7 en muros y chapa; 0 en interiores y fachadas) y por la inclinación (los planos verticales, el 60 %). Lo mojado se oscurece (hasta × 0,58) y baja de rugosidad: 0,40 húmedo y hasta 0,10 en los parches encharcados del suelo, que salen del mismo ruido que la suciedad. Nunca queda más mate que en seco.
- **El director** (`WetTick`) sube `Wetness` mientras llueve (`WetSeconds`, 25 s) y lo baja al escampar (`DrySeconds`, 90 s). Al empezar y al cargar partida se pone de golpe en su sitio; al salir del PIE vuelve a 0. `SetWetnessNow()` lo fija para capturas y pruebas.
- **Charcos con cerco** (`M_Charco` v5): el agua ya no acaba en un borde duro. Hay un centro de agua lisa (rugosidad 0,05) y alrededor un cerco húmedo más ancho, oscuro y satinado (`Cerco`, `RugosidadCerco`).
- **Regueros marcados** (`M_Chorreton` v4): hilos más oscuros y contrastados, en grupos (`Grupos`), y una franja húmeda bajo la albardilla (`Franja`).

**Mundo: carteles, rótulos y etiquetas.**

- `python tools/carteles/generar.py` (Python normal, con Pillow y numpy) dibuja 21 texturas en `assets/unreal/carteles/`: chapas esmaltadas con óxido en los bordes y en los tornillos, chorretones y desconchones; pintura de plantilla gastada, y etiquetas de papel. La fuente de plantilla es Stardos Stencil (OFL, en `tools/carteles/fuentes/`).
- `py tools/unreal/carteles.py` (en el editor) las importa a `/Game/Tarsis/Carteles`, crea `M_Cartel` (chapa recortada por el alfa) y `M_Rotulo` (calcomanía modulada, como las manchas) y coloca lo que dice `assets/unreal/carteles.json`: placas en los dinteles (Jefatura, Archivo, Dormitorio, Cuerpo de guardia, Calabozo), «zona militar» en el muro, señales en poste (alto del control, 20 km/h, alta tensión, gasóleo), el lema y el número del portillo pintados en el muro, «ALTO» y la línea en la losa del control, y etiquetas en las taquillas. Todo va a la carpeta `Carteles` con la etiqueta `cartel`.
- Si un cartel sale en espejo o cabeza abajo se corrige en `ESPEJO` (por clase: placa, pintado, suelo), no cartel a cartel.

**Juego: cobertura en el anillo sur y gestos.**

- **Cobertura.** 93 piezas (`cob_*` en `atrezo.json`): barreras de hormigón, pilas de cajas, sacos de cemento y bidones en cinco grupos entre el camino y el muro sur. Las barreras tapan a uno agachado y no a uno de pie; las pilas de tres cajas tapan de pie. Las dos calles de la ronda de Carmona quedan libres. `giro_modelo` corrige el giro de un modelo entero si viene con lo largo en el otro eje.
- **Gestos.** `ATarsisGuard::PlayGesture(nombre, segundos, hacia)` pone los brazos encima de la animación que tenga el guardia (no hay grafo de animación: se apunta cada hueso del brazo en la malla visible, después de copiar la pose). Gestos: `alto`, `papeles`, `leer`, `pase` y `lona`. Cada brazo tiene su peso y su dirección suavizada, así que de un gesto a otro el brazo va y no salta. En el control del camión, Sanz va hacia la cabina con la mano en alto, tiende la mano, lee los papeles y da paso con el brazo hacia el portón (o levanta la lona si la base está en guardia). `GestureLog` y `HandHeight()` son para las pruebas.

**Técnica: presupuesto de render.** El director tiene `RenderCVars` (variables de consola «nombre=valor»): las pone al empezar la partida y las deja como estaban al acabar. `py tools/unreal/render.py` mide cada candidato solo, en una partida limpia (memoria de la tarjeta con `nvidia-smi` y fps en tres sitios), y `render.aplicar([...])` escribe los elegidos en el director del nivel. Cambiar el presupuesto no pide compilar. Las medidas están en `docs/rendimiento.md`. Ojo: una variable puesta a mano en la consola manda sobre el código, y una puesta por código manda sobre la escalabilidad (con `r.ScreenPercentage` en el presupuesto, la opción de resolución del menú dejaría de mandar).

**Pruebas.** `prueba_puertas`, `prueba_mojado`, `prueba_carteles`, `prueba_cobertura`, `prueba_gestos` y los gestos de Sanz en `prueba_camion` y `prueba_viaje`.

## Sonidos

`tools/sonido/generar_sonidos.py` sintetiza los .wav (pasos de gravilla y cemento, piedra, dardo, viento y lluvia) en `assets/unreal/sonidos`, y `tools/unreal/sonidos.py` (Python del editor) los importa en `/Game/Tarsis/Sonidos`. El director los carga por su ruta: si faltan, el juego va igual pero mudo.
