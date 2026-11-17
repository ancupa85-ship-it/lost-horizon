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

### Materia, noche con cielo, agua y señales que se leen (tanda 25)

**El diagnóstico (medido).** Las texturas de Poly Haven que usa la base son casi un color liso (desviación relativa del 9 % en el hormigón y el yeso), y el color del visor multiplicado por la textura daba albedos imposibles: el suelo y el camino devolvían un 2 % de la luz, el muro un 6 %, el tejado un 1,3 %. Con farolas 140 veces más fuertes que la luna, la noche solo tenía dos valores: círculo quemado o negro.

**Arte: materia en lo grande** (`materiales.py`, `M_LH` «lh v25c»).

- **Albedo de verdad.** El color es `Tinte` (el albedo lineal del material, tabla `ALBEDO`) por la textura dividida por su color medio (`Medio`, tabla `MEDIO`), con `Contraste` alrededor de 1. La textura ya no decide el tono, solo el grano.
- **Variación que se ve de lejos**, toda en el material y sin texturas nuevas: nubes de tono (`Macro`), manchas, zócalo sucio irregular de 20 a 90 cm, **losas** en lo horizontal (`Losa`, `LosaTono`, `LosaFaseX`) y **paneles de encofrado** en lo vertical (`Panel`, `PanelTono`) con su junta oscura (`Junta`), regueros verticales que bajan por muros y chapa (`Chorreo`) y relieve reforzado (`Relieve`). Cada losa desplaza la textura al azar (`Desfase`): la grieta del asfalto ya no se repite cada tres metros.
- **Contenedores.** `exportar_base.py` añade una malla de detalle por color (`contenedordet_N`): pilares de esquina, largueros, costillas cada 26 cm, puertas con sus cuatro barras de cierre y bisagras. Solo se ve: se choca y se dispara contra la caja de siempre.
- **Camión** verde oliva militar oscuro (antes, verde lima): `M_LH_Movil` usa el mismo esquema de albedo.

**Luz y cielo.**

- **Farolas que no queman.** Farolas (300 lm), focos de torre (800 lm), farol del control (300 lm), faros del camión y linternas se pintan a un décimo de lo que eran. Para el sigilo cuentan lo mismo: las luces con la etiqueta `luz_fuerte` valen × 10 en `ATarsisGuard::LightAt` (`StrongLightBoost`). La exposición, la luna y la luz del cielo no cambian: lo que cambia es que el suelo ya devuelve luz.
- **Relleno.** Cada farola lleva una luz puntual sin sombras de 250 lm (`Brillo_<farola>`, etiqueta `decorado`): saca la luz fuera del cono y es la que se refleja en el suelo mojado. `LightAt` la ignora, se apaga con su farola y no entra en el apagón como luz propia.
- **Halos** (`M_Halo`): una esfera aditiva alrededor de cada luminaria de fuera (etiqueta `halo`), que crece con la humedad (`Nublado`) y se apaga con su luz.
- **Cielo** (`cielo.py`, `M_Cielo`): cúpula de 1,2 km sin iluminar con degradado de cenit a horizonte, estrellas (textura propia de 2048, `tools/texturas/estrellas.py`), disco y halo de la luna en la dirección contraria a la luz `Luna`, y nubes de ruido que se mueven. Con lluvia o niebla se cubre: el director sube `Nublado` en `MPC_Tarsis` (`CloudTick`, `CloudSeconds`).
- **Posprocesado:** algo de grano, florecimiento suave y un punto frío en las sombras y cálido en las luces.

**Agua.**

- El suelo mojado se oscurece más (`MojadoOscuro` 0,5) y los parches encharcados del maestro son espejo (rugosidad 0,06, relieve plano) con forma de mancha amplia, no de lunares.
- **Charcos** (`M_Charco` v6): la forma es la distancia al centro más un ruido lento (lóbulos de un metro), no una máscara redonda comida por ruido fino; dejan ver más fondo y son más grandes (`CHARCO_ESCALA` 1,7 en `perimetro.py`).
- **Regueros** (`M_Chorreton` v5): además de los hilos finos llevan regueros anchos de un palmo largo, que son los que se ven a diez metros, y la franja húmeda de arriba es más alta.

**Juego.**

- **El alto de Sanz.** Brazo más separado del cuerpo y, sobre todo, un **bastón luminoso rojo** en la mano derecha durante todo el control del camión (`HoldBaton`, `BatonOn`): de noche un brazo oscuro contra un fondo oscuro no se lee; un bastón encendido, sí. Su resplandor (16 lm) es un componente del guardia y no cuenta para el sigilo.
- **«ZONA MILITAR»** pasa a 2 × 1 m, con menos óxido encima, y lleva luz propia como la pintura reflectante (`brillo` en `carteles.json`, parámetro `Brillo` de `M_Cartel`): se lee de noche sin añadir un foco, que cambiaría el sigilo. El lema del muro, menos comido.

**Pruebas.** `prueba_materia` y `prueba_cielo` (familia nueva), el bastón en `prueba_gestos` y `prueba_camion`, los halos y el relleno en `prueba_generador`, y el tamaño y el brillo de las chapas en `prueba_carteles`.

### Farolas que se apagan de un dardo (tanda 27)

- Cualquier farola de la base (luz con la etiqueta `luz_fuerte`) se rompe de un dardo, como ya pasaba con el farol de la garita (`ATarsisDirector::ShootLamp`, `BreakableLamp`). No valen los focos de las torres, los faros del camión ni los rellenos; la etiqueta `irrompible` excluye una a mano.
- El dardo se gasta. La farola no vuelve con el generador, pierde su halo y su relleno, deja de alumbrarte y de darte sombra, y se guarda con el punto de control.
- El guardia más cercano (a menos de 25 m) oye los cristales y va a mirar. El primero que pisa esa sombra, él u otro en su ronda, da parte por radio, la base se pone en guardia un minuto y él sigue la noche con la linterna encendida (`LampsTick`).
- El parte del día siguiente cuenta las farolas rotas.
- El cristal de las bombillas ya no da sombra (dejaba un disco negro en el techo).
- Prueba: `prueba_farola`.

### «Responde, Carmona», apoyo a oscuras y salas con vida (tanda 28)

- **Contestar por la radio de otro** (`bRadioAnswer`): cada guardia da su parte a su manera (textos `parte_<nombre>` de `mision1.json`) cada `ParteEvery` segundos; si estás a menos de 16 m lo oyes, con subtítulo siempre. Cuando la central llama a uno que has dejado en el suelo y estás junto a él, eliges entre tres partes con 1, 2 y 3 (`StartRadioAsk`, `AnswerRadio`): el suyo cuela y no viene nadie; «Todo tranquilo» es la frase de coacción y trae a dos con la base en guardia; el de otro, o callar, manda a uno como siempre. Se eligió ampliar `mision1.json` en vez de un plugin de diálogo: se escribe en texto, lee nuestras banderas y se prueba desde `pruebas.py`.
- **Nadie entra solo a oscuras** (`bBuddyRule`): el guardia que va a mirar un ruido a menos de `DarkZoneRadius` de una farola rota se planta, saca la linterna, pide apoyo por radio y espera al compañero libre más cercano (`ATarsisGuard::WaitForBuddy`, hasta `BuddyWaitSeconds`). Luego entran los dos. Mientras, esa sombra es tuya y el compañero ha dejado su ronda.
- La voz del que encuentra una farola rota ya habla de la farola y no del farol del control.
- **Salas**: jefatura (el despacho de Ibarra, con su catre), archivo (estanterías, archivadores y cajas), transmisiones (las radios de la central), cuarto de revelado (la luz roja) y cosas en el cuerpo de guardia. Fuera: mesa junto al barracón, material del generador, ruedas y un acopio en el patio central. 73 piezas en `atrezo.json`; cuatro modelos nuevos de Poly Haven (CC0): `WoodenChair_01`, `cardboard_box_01`, `Camera_01`, `wooden_picnic_table`.
- Pruebas: `prueba_radio` y `prueba_apoyo`.

### Códec y música nueva (tanda 29)

- **Códec** (`TarsisCodec.cpp`, parte de `ATarsisDirector`): la frecuencia de Control (141.12) y la de Roig (140.85), que no son la radio de la base, y una tercera voz (000.00) que solo aparece sin luz o con el expediente. Las llamadas entrantes (`CodecRing`: al empezar, con la alarma, al abrir el archivo, al coger el expediente y en el apagón; `bCodecCalls`) **no paran el juego**: suenan, se anuncian arriba y se cogen con la **R** cuando puedes. Con la R sin llamada sale el menú de frecuencias (1, 2, 3). Durante la conversación el juego está en pausa; E, Espacio, Intro o clic pasan de frase y Esc cuelga.
- Control contesta según la base y el objetivo (`CodecControlConv`: `control_llave`, `control_jefatura`... y `control_alerta`, `control_celda`) y añade una frase de las suyas; Roig da la pista del salmo una vez, cuando ya has leído la mesa de Alarcón y el archivo sigue cerrado.
- Los diálogos son textos `codec_<nombre>` de `mision1.json`, una frase por línea: `C|` Control, `T|` tú, `R|` Roig, `F|` la voz sin nombre. Vienen de la versión web (`src/07-codec.js`), adaptados a esta base.
- Retratos: `tools/unreal/retratos.py` importa `assets/retratos/*.jpg` en `/Game/Tarsis/Retratos` (el nombre del archivo es la clave: `cuttlas`, `roig`, `control`, `fuente`). A quien no tiene retrato ilustrado, el HUD le dibuja el de puntos de la web.
- **La pregunta de la central** («Responde, Carmona») tiene ahora su propia caja, con letra grande, y no se pisa con el aviso de la E.
- **Música**: `tools/sonido/generar_musica.py` escribe las tres capas juntas, sobre la misma armonía (16 compases a 75 ppm en re menor, 51,2 s, estéreo): colchón de cuerdas, bajo y un piano lejano con el tema; latido y ostinato de cuerda para la tensión; percusión, bajo y metales para la alerta. Con el códec abierto la música se aparta. También genera los sonidos del códec (`codec_llamada`, `codec_abrir`, `codec_cerrar`, `codec_tecla`).
- Prueba: `prueba_codec`.
- Pendiente: la R no se puede reasignar todavía; el códec no se guarda en el punto de control (lo ya hablado se olvida al cargar).

### Cuatro torres de esquina (tanda 30)

- Pedidas por Andres: una torre grande en cada esquina del muro perimetral, por dentro (`torre_grande` en `tools/unreal/exportar_base.py`). Plataforma de 4,4 m a 7,5 m de alto (el muro mide 4,6), tejadillo, escala y dos proyectores en la diagonal: uno hacia dentro de la base y otro hacia fuera.
- Dos centinelas por torre (`guardias.py`, «puestos» de `base.json`): «centinela de la torre N» lleva el foco de dentro y barre su tramo del anillo; «vigia de la torre N» lleva el de fuera y barre la marisma. Los recorridos y el segundo de arranque de cada uno, en `mision1.json` (`ajustes.guardias`).
- Los focos de fuera van sin sombras; todos con 65 m de alcance.
- Andres quitó las dos torres de dentro: las de esquina son ahora `torre1` (NO), `torre2` (NE), `torre3` (SE) y `torre4` (SO), a 7,5 m. Los focos de dentro barren el patio norte, el patio este y las dos mitades del camino, con sombra y haz prieto (5 grados); el patio central se queda sin foco, porque desde las esquinas lo tapan los edificios.
- La tapa negra de una farola rota ya distingue el farol del patio de la farola del camino (`LampCoverPatioOffset`, `LampCoverPatioScale`, `LampCoverPatioZ`).
- Prueba: `prueba_esquinas`. En las demás, los vigías de fuera están quietos (`_limpieza`).

### Linternas y retoques de las torres (tanda 31)

- **Linterna según el sitio** (`bContextTorch` en el director, `ATarsisGuard::AutoTorchTick`): cada 0,6 s el guardia de suelo mide la luz que le llega sin contar linternas (`AmbientAt`). La enciende por debajo de `TorchOnBelow` si además está bajo techo (`IsIndoors`) o va a mirar algo (ajuste 31c: de noche casi toda la base está a la misma luz de luna y solo por luz la llevaban encendida 7,8 de 8; `bTorchOutdoors` vuelve a lo de antes). Para guardarla necesita tres medidas seguidas sin motivo y `TorchMinOn` segundos encendida. La del apagón, la de la farola rota y la del apoyo siguen mandando sobre esta. Lo oscuro deja de ser terreno libre: la ves venir de lejos, pero su cono le alarga la vista.
- La linterna pinta `TorchPaintLumens` (700; antes 250, casi no se veía) y para el sigilo cuenta 2500 como siempre. Lleva cristal encendido y un destello pequeño (los materiales de los faros del camión).
- **Tu linterna** (`TarsisTorch.cpp`, tecla F, reasignable; `bHasTorch` para una misión que empiece sin ella): luz fría en la cámara, con sombra (`bTorchShadows`). Con ella encendida los guardias te ven como a plena luz (`ATarsisGuard::SetPlayerTorch`) y el indicador de luz lo marca; al guardia que alumbras a menos de `TorchNoticeDist` le llama la atención y viene a mirar, así que también sirve de señuelo.
- **Deslumbrar** (pedido por Andres): a menos de `TorchBlindDist` (4,5 m), con el guardia de cara y dentro del centro del haz, se queda `TorchBlindSeconds` sin ver ni andar (`ATarsisGuard::Dazzle`, el mismo aturdimiento del empujón) y al rehacerse va a por ti. No repite hasta `TorchBlindAgain` segundos después: la segunda vez se tapa los ojos.
- **Torres**: cristal encendido y destello en cada proyector (`SetupBeamLenses`, `BeamLensSize`, `BeamGlowSize`) y una luz cálida de 300 lm bajo el tejadillo (`guardias.py`, etiquetas `decorado` y `luz_caseta`): el centinela se recorta y la garita se lee ocupada. No cuenta para el sigilo y sigue encendida en el apagón, como los focos.
- Los focos de fuera ya no barren la marisma a 12 m: repasan el borde del muro a 7 m (más cerca el propio muro les hace sombra) y llegan a los dos portones y al portillo.
- Mientras hablas por el códec ya no se ve de fondo el mensaje de ayuda.
- Prueba: `prueba_linternas`. En las demás la regla está apagada (`_limpieza`), como el apoyo o la radio.

### Radio: tecla, charla y emisora (tanda 32)

- **La radio es una acción más** (la octava, `RADIO`, R por defecto): se reasigna en CONTROLES y el códec, la ayuda y los avisos de llamada muestran la tecla puesta.
- **El códec viaja con el punto de control**: `UTarsisSave::CodecTaken`. Al cargar, lo ya oído vuelve y no queda llamada pendiente.
- **Linternas**: `TorchMinOn` 9 s y bajo techo solo se guarda con luz por encima de 0,6 (Ramos la sacaba y guardaba cada poco). La tuya baja de intensidad según la distancia a lo que alumbra el centro del haz (`TorchNearDist`, `TorchNearMin` 0,008): el guardia deslumbrado y la pared a un palmo ya no salen blancos.
- **La charla** (`TarsisEmisora.cpp`, `bRadioChat`, `RadioChatAfter`): pasados dos minutos, con Lobato y Carmona de ronda y tú a menos de `ParteHearDist` de uno, Lobato pregunta por la red qué decir si le apuntan y Carmona le explica «Todo tranquilo» y que trae a los dos más cercanos. Pone la bandera `sabe_coaccion`. Es la pista de «Responde, Carmona» dentro del mundo, y también la de que la frase sirve para mover a dos hombres a propósito.
- **La emisora** (punto `emisora` de `mision1.json`, en transmisiones; banderas `emisora_muda` y `emisora_reparada`; `RadioDead()`): con la red muda la central no llama a los caídos, no hay partes y la central no se oye. A los 20 s el guardia más cercano prueba la radio en vano; a los `RadioDeadSeconds` (90) sale el más cercano de recado a arreglarla (`RadioFixSeconds`, 14 s ante la mesa). Si lo tumbas, tardan en mandar a otro. Arreglada, la base queda en guardia 90 s y la central llama entonces a quien no conteste.
- Prueba: `prueba_emisora`. La charla va apagada en las demás (`_limpieza`).

### Salas con más vida (tanda 33)

- Transmisiones y archivo: 22 piezas más en `atrezo.json` (archivadores, cajas, carpetas, taburetes, reloj, cuadrantes), todas de modelos ya cargados: no suman memoria de vídeo.
- Tanda 34: `ambiente.legajos()` hace tres mallas propias sin texturas nuevas (`legajos`, `legajos_oscuros`, `papeles`); las baldas del archivo llevan filas de legajos y las mesas, papeles.
- La sala roja del edificio este vuelve a ser lo que es, el **calabozo** donde apareces si te pillan: fuera el atrezo de «cuarto de revelado» de la tanda 28; dentro, catre con colchón y manta, cubo, taza y una lata.

### El calabozo: ¿por quién reza Vidal? (tanda 35)

La primera captura te deja en el calabozo (edificio este) y la reja ya no se abre sola (`bCellPuzzle`). Código en `TarsisCalabozo.cpp`.

- **Convencer al cabo Vidal** por la reja, en tres pasos y con las teclas 1 a 3. Amenazar o sobornar falla. El segundo paso pide saber que lo de abajo está vivo (la voz sin nombre del códec o el expediente) y el tercero, haber leído el expediente o saber el salmo (mesa de Alarcón o la pista de Roig). Tres errores y deja de escuchar. Si abre él, calla (bandera `vidal_calla`).
- **La losa suelta** del rincón (`CellSlab`) guarda la llave del hermano y su medalla, «VIDAL, J.». Siempre funciona, pero a los `CellAlertSeconds` (45 s) alguien encuentra la celda vacía y la base queda en guardia.
- Control, por el códec (`control_celda`), da las pistas que en la versión web daba Halloran desde el camastro.
- Cambios respecto a la web, por coherencia: nadie enseña papeles (te han registrado), el viento en lugar de los perros y el hermano consta como desertor.
- **Clave del archivo:** la mesa ya no da el número del salmo, solo el «De profundis» subrayado; el número sale de Roig o de los sueños. Dos claves malas seguidas (`KeypadMaxFails`) bloquean el teclado y avisan a la central.
- **Tanda 36:** Vidal tiene cuerpo (`SpawnVidal`: la malla y el reposo del guardia `VidalLooksLike`, sin IA; aparece al encerrarte en `CellDoor + VidalOffset`, de medio lado, y se vuelve a la pared al abrir o al dejar de escuchar) y la pregunta sale en una caja de conversación propia del HUD (`DrawCellAsk`), con letra grande.
- Prueba: `prueba_calabozo` (familia propia). En las demás pruebas la reja se abre sola, como antes.

## Sonidos

`tools/sonido/generar_sonidos.py` sintetiza los .wav (pasos de gravilla y cemento, piedra, dardo, viento y lluvia) en `assets/unreal/sonidos`, y `tools/unreal/sonidos.py` (Python del editor) los importa en `/Game/Tarsis/Sonidos`. El director los carga por su ruta: si faltan, el juego va igual pero mudo.
