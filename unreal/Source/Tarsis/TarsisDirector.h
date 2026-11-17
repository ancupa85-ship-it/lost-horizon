// Director del sigilo en el nivel Tarsis: luz del jugador, agacharse con C, HUD (ATarsisHUD), mensajes y captura.
// Va un ejemplar en el nivel (lo coloca tools/unreal/guardias.py).
// Captura: la primera vez despiertas en el calabozo (como en el juego web) y al rato Vidal abre la reja;
// las siguientes vuelves a la salida.
// Misión 1 (como en el juego web): la llave de la jefatura la lleva Ibarra; en la mesa de Alarcón, la nota con la
// clave del archivo (0129, el salmo CXXIX); en el archivo, el expediente LH-07; y salir por el control de salida.
// La E hace todo: derribar, arrastrar o soltar un cuerpo, quitar la llave, abrir, leer y coger.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "InputCoreTypes.h"
#include "TarsisDirector.generated.h"

/** Punto de interacción sencillo de la misión (assets/unreal/mision1.json, tools/unreal/mision.py): con la E, si tienes la
 *  bandera Need, pone Sets, suena Sound, sale el texto Text, quita el bloque RemoveBlock y guarda un punto de control. */
USTRUCT(BlueprintType)
struct FTarsisPoint
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Id;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FVector Pos = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") float Radius = 170.0f;
	/** Clave del aviso de la E; PromptLocked, si falta la bandera Need (vacío: no hay aviso). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Prompt;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName PromptLocked;
	/** Bandera que exige; si falta: texto NeedText, sonido NeedSound y bandera NeedSets (p. ej. «ya sabes de Ramos»). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Need;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName NeedText;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName NeedSound;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName NeedSets;
	/** Banderas que pone al usarlo; con Sets ya puesta el punto desaparece (salvo bRepeat, p. ej. releer una nota). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Sets;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName AlsoSets;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") bool bRepeat = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Sound;
	/** Clave del texto que sale y segundos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Text;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") float TextSeconds = 5.0f;
	/** Clave del nombre del punto de control que guarda (vacío: no guarda). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Checkpoint;
	/** Lo notan los guardias si lo ven cambiado (puerta que estaba cerrada). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") bool bChange = false;
	/** Bloque de la misión que quita (puerta_jefatura, puerta_botiquin, carta, expediente...). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName RemoveBlock;
	/** Dardos que te da (pistola del botiquín). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") int32 Darts = 0;
};

/** Objetivo del HUD: el primero de la lista cuya bandera If esté puesta (If vacía: siempre). */
USTRUCT(BlueprintType)
struct FTarsisObjective
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName If;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Text;
};

UCLASS()
class ATarsisDirector : public AActor
{
	GENERATED_BODY()

public:
	ATarsisDirector();
	virtual void Tick(float DeltaSeconds) override;

	/** Luz que recibe ahora el jugador (0-1), la misma que usan los guardias. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	float PlayerLight = 0.0f;

	/** Mensaje en el centro de la pantalla (varias líneas con \n) y segundos que le quedan. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	FString Message;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	float MessageT = 0.0f;
	/** Mensajes de radio (los que empiezan por "RADIO"): van aparte, abajo a la izquierda, sin tapar el mensaje principal. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	FString Radio;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	float RadioT = 0.0f;

	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void ShowMessage(const FString& Text, float Seconds = 4.0f);

	/** Te han cogido: la primera vez al calabozo, luego a la salida. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void Captured(APawn* Player);

	/** Dónde despiertas en el calabozo, hacia dónde miras, y el centro de la reja (lo pone guardias.py). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	FVector CellSpot = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	float CellYaw = -90.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	FVector CellDoor = FVector::ZeroVector;

	/** Segundos hasta que Vidal abre la reja. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	float CellTime = 25.0f;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	int32 Captures = 0;

	/** Guardia que se puede derribar ahora con la E (o nullptr). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	class ATarsisGuard* TakedownTarget() const;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	int32 Takedowns = 0;

	/** Lo que hace la E: derriba al guardia a tiro, si lo hay. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void Takedown();

	/** La tecla E: lo que toque según dónde estés (ver InteractPrompt). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void Interact();

	/** Texto del aviso de la E ahora mismo («E  ABRIR LA JEFATURA»...), vacío si no hay nada a mano. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	FString InteractPrompt() const;

	/** Objetivo actual de la misión, para la esquina del HUD. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	FString Objective() const;

	/** Teclado del archivo: abierto, y cifras tecleadas. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bKeypad = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	FString KeypadInput;

	/** Teclea una cifra en el teclado (0-9; -1 borra la última). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void KeypadDigit(int32 Digit);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Mision")
	FString VaultCode = TEXT("0129");

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bKey = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bJefOpen = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bNoteRead = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bVaultOpen = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bFile = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bDone = false;

	/** Segundos de misión (hasta salir con el expediente). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	float MissionTime = 0.0f;

	/** Radio (cm) al que se oyen ahora tus pasos: 0 agachado o quieto; más corriendo (Shift) y fuera (gravilla) que dentro. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	float PlayerNoise = 0.0f;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	bool bSprint = false;

	/** Clima: 0 despejado, 1 lluvia (te ven menos de lejos y tus pasos se oyen menos), 2 niebla (te ven mucho menos). Tecla Y. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Clima")
	int32 Weather = 0;

	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void SetWeather(int32 NewWeather);

	/** Cuánto está mojada la base, 0-1 (tanda 24). Sube mientras llueve (WetSeconds para empaparse) y baja despacio al
	 *  escampar (DrySeconds). Va al escalar «Mojado» de la colección MPC_Tarsis: el material maestro oscurece y da brillo
	 *  a lo que está a la intemperie. Al empezar y al cargar partida se pone de golpe en su sitio. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Clima")
	float Wetness = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Clima")
	float WetSeconds = 25.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Clima")
	float DrySeconds = 90.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Clima")
	TSoftObjectPtr<class UMaterialParameterCollection> WetCollection = TSoftObjectPtr<class UMaterialParameterCollection>(FSoftObjectPath(TEXT("/Game/Tarsis/Materiales/MPC_Tarsis.MPC_Tarsis")));

	/** Pruebas: pone el mojado de golpe (0-1) sin esperar a la lluvia. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Pruebas")
	void SetWetnessNow(float Value);

	/** Lo que vale ahora «Mojado» en la colección (pruebas): -1 si no hay colección. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Pruebas")
	float WetnessInCollection() const;

	/** Cuánto está cubierto el cielo, 0-1 (tanda 25): 1 con lluvia o niebla. Va al escalar «Nublado» de MPC_Tarsis: el
	 *  cielo tapa las estrellas y la luna con nubes y los halos de las farolas crecen (tools/unreal/cielo.py). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Clima")
	float Cloudiness = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Clima")
	float CloudSeconds = 14.0f;

	/** Pruebas: pone el nublado de golpe (0-1). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Pruebas")
	void SetCloudinessNow(float Value);

	/** Lo que vale ahora «Nublado» en la colección (pruebas): -1 si no hay colección. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Pruebas")
	float CloudinessInCollection() const;

	/** Halos de luminarias que hay en el nivel (etiqueta «halo») y cuántos están encendidos ahora (pruebas: se apagan
	 *  con su luz). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Pruebas")
	FIntPoint HaloCounts() const { return FIntPoint(Halos.Num(), HalosLit()); }
	/** Farolas rotas de un dardo (sin contar el farol de la garita). */
	UFUNCTION(BlueprintPure, Category = "Tarsis")
	int32 BrokenLampCount() const { return BrokenLights.Num(); }
	/** Tapa negra que apaga la pantalla de una farola rota: dónde va respecto a su luz y cuánto mide (el cubo del motor
	 *  mide 100 cm). Medido en el PC en las farolas del camino: el panel va de x -33 a -17 e y -13 a 13, con la cara de
	 *  abajo a z +0,5; la tapa lo abraza por debajo sin salirse de la carcasa. Las del patio son otro modelo, sin panel ahí. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	FVector LampCoverOffset = FVector(-25.0f, 0.0f, 1.2f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	FVector LampCoverScale = FVector(0.26f, 0.40f, 0.036f);
	/** Tanda 30: las farolas del patio son otro modelo (un farol con la bombilla dentro, 26 a 38 cm por encima de la luz).
	 *  Se distinguen por la altura de la luz: por debajo de LampCoverPatioZ (285 en el patio, 380 en el camino). Medido en el PC. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	FVector LampCoverPatioOffset = FVector(-25.0f, 0.0f, 32.0f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	FVector LampCoverPatioScale = FVector(0.16f, 0.17f, 0.14f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	float LampCoverPatioZ = 330.0f;
	/** Repone las farolas rotas (pruebas y carga de partida). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void RepairLamps();
	/** Pruebas: deja la pistola con estos dardos. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Pruebas")
	void SetDarts(int32 N) { Darts = FMath::Max(0, N); }

	/** Ajuste de la tanda 25: cuánto dispersan en la niebla volumétrica los focos fuertes (torres; etiqueta «luz_fuerte»).
	 *  Con 16 el haz de la torre era un cono blanco macizo que se comía un tercio de la imagen con lluvia. Va aquí, y no
	 *  fijo en el código, para afinarlo desde el editor sin compilar. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Luz")
	float StrongSpotScattering = 5.0f;

	/** Con lluvia: por cuánto se multiplica la densidad de la niebla del nivel, y de qué color se enciende. Con 1,5 y un
	 *  gris claro la base entera quedaba lechosa y lo mojado no se leía. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Luz")
	float RainFogMul = 1.25f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Luz")
	FLinearColor RainFogColor = FLinearColor(0.016f, 0.020f, 0.027f);

	/** Presupuesto de render (tanda 24): variables de consola «nombre=valor» que se ponen al empezar la partida y se dejan
	 *  como estaban al acabar (en el editor las variables sobreviven al PIE). Las elige tools/unreal/render.py midiendo en
	 *  esta tarjeta y las escribe en el director del nivel: cambiar el presupuesto no pide compilar. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Render")
	TArray<FString> RenderCVars;

	/** Las que se han puesto de verdad esta partida, con el valor que tenían antes («nombre=antes->ahora»). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Render")
	TArray<FString> RenderApplied;

	/** Base en guardia tras una alarma (segundos que quedan): la sospecha sube un 50 % más deprisa, las rondas van a paso
	 *  ligero y en el control registran la caja del camión. Editable para que las pruebas la pongan en guardia a mano. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	float TensionT = 0.0f;

	/** Generador de la base (base.glb, «generador.001»). Con E se corta: se apagan farolas y focos hasta que alguien lo arregla. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Luz")
	FVector GeneratorLoc = FVector(4300.0f, 1700.0f, 0.0f);

	/** Sin luz: segundos que quedan hasta que vuelve sola (si nadie la arregla antes). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Luz")
	float PowerT = 0.0f;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Luz")
	bool bPowerOff = false;

	/** Barrera del control de salida (pie del poste), su orientación y largo: se levanta en el final por la salida. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cine")
	FVector ExitBarrierLoc = FVector(6780.0f, 5060.0f, 0.0f);   // atraviesa el pasillo que lleva a G

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cine")
	float ExitBarrierYaw = 90.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cine")
	float ExitBarrierLength = 390.0f;

	/** Camión de suministros (tanda 21): cada cierto tiempo entra por el portón del oeste (que se abre para él), cruza la
	 *  base por el camino, para en el control hasta que sube la barrera y sale por el este. Sus piezas son los actores con
	 *  la etiqueta «camion» y la hoja del portón, los de «hoja_entrada» (tools/unreal/montar_base.py). Sin ellos no hay camión. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	bool bTruck = true;

	/** Segundos hasta el primer paso y entre el final de un paso y el siguiente. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckFirstDelay = 75.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckInterval = 170.0f;

	/** Velocidad dentro de la base y por el terraplén de fuera (cm/s). Dentro va al paso de alguien que anda deprisa. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckSpeed = 400.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckSpeedOut = 900.0f;

	/** Donde espera oculto (principio del terraplén del oeste); su Y es el eje del camino y su Z, la losa. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	FVector TruckStart = FVector(-13500.0f, 5700.0f, 4.0f);

	/** X del centro del camión cuando para ante el portón de entrada, ante la barrera y donde desaparece. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckGateStopX = -2420.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckBarrierStopX = 8270.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckEndX = 20500.0f;

	/** Portón de entrada: centro de la hoja cerrada y lo que se corre al abrirse. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	FVector EntryGateLoc = FVector(-1840.0f, 5700.0f, 130.0f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	FVector EntryGateSlide = FVector(0.0f, 640.0f, 0.0f);

	/** Faros: lúmenes y si dan sombra (una sola luz con sombra; si pesa en la tarjeta, se quita aquí). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckLampLumens = 600.0f;      // lo que se pinta (tanda 25); para el sigilo cuenta diez veces más («luz_fuerte»)

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	bool bTruckShadows = true;

	/** Ajuste 26e: el cuerpo del jugador proyecta sombra en su propia vista (hace falta además calidad de sombras
	 *  Media o más, o r.ShadowQuality por encima de 0: va en RenderCVars). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sigilo")
	bool bPlayerShadow = true;

	/** Ajuste 26b: parte de TruckLampLumens que se pinta de verdad (el sigilo sigue contando el total). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckLampPaint = 1.0f;

	/** Tanda 26: dos faros de verdad en vez de una sola luz. Cada uno pinta la mitad de TruckLampLumens (entre los dos
	 *  cuentan para el sigilo lo mismo que antes la luz única) y solo el primero da sombra. Separación del eje (cm),
	 *  cabeceo (grados; el perfil ya lleva el punto fuerte 2,5 grados bajo el eje) y giro sobre el eje, para poner
	 *  derecho el dibujo del perfil (se calibra con una captura contra el muro: 0, 90, 180 o 270). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckLampSpread = 72.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckLampPitch = -3.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckLampRoll = 0.0f;

	/** Perfil del haz (haz de cruce escrito en tools/unreal/ies.py e importado por tools/unreal/cielo.py). Vacío o si
	 *  no existe: el cono liso de siempre. Solo cambia el dibujo de la luz en el suelo, no lo que cuenta para verte. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	FString TruckIESPath = TEXT("/Game/Tarsis/Luces/faro_cruce.faro_cruce");

	/** Cristal encendido y destello de cada faro (materiales de tools/unreal/cielo.py); diámetros en cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckLensSize = 17.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckGlowSize = 60.0f;

	/** Faros que tiene el camión, cuántos llevan perfil y cuántos cristales y destellos se le han puesto (pruebas). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Camion")
	FIntVector TruckLampCounts() const;

	// ---- tu sombra te delata (tanda 26) ----
	/** Interruptor: un guardia que no te ve pero ve tu sombra (bajo una luz que dibuje sombras) se mosquea. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sombra")
	bool bShadowTells = true;

	/** Sospecha por segundo con la sombra bien marcada y a sus pies; cae con la distancia hasta ShadowRange (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sombra")
	float ShadowRate = 0.5f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sombra")
	float ShadowRange = 1400.0f;

	/** Una sombra nunca da la alarma: la sospecha que mete no pasa de aquí. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sombra")
	float ShadowCap = 0.55f;

	/** Lo que tiene que aportarte una luz para que tu sombra cuente (0-1, la escala de LightAt) y cuánto tiene que
	 *  mandar esa luz en el sitio donde cae la sombra (1 = solo alumbra ella). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sombra")
	float ShadowMinLight = 0.3f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sombra")
	float ShadowMinContrast = 0.6f;

	/** Quieto, tu sombra llama mucho menos la atención que moviéndose. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sombra")
	float ShadowStillFactor = 0.25f;

	/** Dónde cae tu sombra ahora (puntos del mundo) y cuánto se marca cada punto (pruebas y ajuste). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sombra")
	TArray<FVector> ShadowTips;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sombra")
	TArray<float> ShadowContrasts;

	/** Veces que un guardia se ha mosqueado por tu sombra y quién fue el último. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sombra")
	int32 ShadowNoticed = 0;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sombra")
	FString ShadowWatcher;

	/** Mide las sombras ahora mismo, sin esperar al siguiente paso (pruebas). Devuelve cuántos puntos cuentan. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Sombra")
	int32 MeasureShadows();

	/** Hasta dónde ve el conductor a quien esté de pie delante, dentro del haz de los faros (agachado, la mitad). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckSight = 2200.0f;

	/** 0 espera fuera, 1 llega al portón, 2 parado mientras se abre, 3 cruza la base, 4 parado en el control, 5 sale. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckState = 0;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckPasses = 0;

	/** Veces que ha tocado el claxon (te ha visto en los faros o alguien le corta el paso). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckHorns = 0;

	/** Hoja del portón de entrada (0 cerrada, 1 abierta) y barrera del control (0 bajada, 1 levantada). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	float EntryGateT = 0.0f;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	float BarrierT = 0.0f;

	/** Para las pruebas y para probar a mano: el camión que espera fuera sale ya. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Camion")
	void TruckSkipWait() { if (TruckState == 0) TruckT = 0.05f; }

	UFUNCTION(BlueprintPure, Category = "Tarsis|Camion")
	FVector TruckLocation() const { return FVector(TruckX, TruckStart.Y, TruckStart.Z); }

	/** Tanda 22: vas escondido en la caja del camión. Se sube por detrás con la E cuando está parado o cruza la base al
	 *  paso; bajo la lona no te ven. En el control, un guardia va a la cabina a mirar los papeles; con la base en guardia
	 *  registra también la caja. Con el expediente, el camión te saca de la base; sin él, te bajas antes de que salga. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	bool bRiding = false;

	/** Veces que te has subido a la caja y registros de la caja que han hecho en el control. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckRides = 0;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckSearches = 0;

	/** Veces que un guardia ha llegado a la cabina a mirar los papeles. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckChecks = 0;

	/** El control, con el camión parado: 0 esperan a que venga alguien, 1 un guardia va hacia la cabina, 2 mira los papeles,
	 *  3 va a la trasera (base en guardia), 4 mira la caja, 5 barrera arriba. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckCheck = 0;

	/** Segundos que mira los papeles en la cabina. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckPapersTime = 4.5f;

	/** Si en el control no hay quien abra: a los TruckHornWait segundos el conductor toca el claxon y a los TruckSelfWait
	 *  se baja y levanta la barrera él. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckHornWait = 8.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckSelfWait = 30.0f;

	/** Nombre del guardia que está con el camión en el control («» si ninguno). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Camion")
	FString TruckInspectorName() const;

	/** ¿Puedes subirte ahora a la caja? Subir y bajar (lo que hace la E). LeaveTruck devuelve si has bajado. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Camion")
	bool CanBoardTruck() const;

	UFUNCTION(BlueprintCallable, Category = "Tarsis|Camion")
	void BoardTruck();

	UFUNCTION(BlueprintCallable, Category = "Tarsis|Camion")
	bool LeaveTruck(bool bForced = false);

	/** Saliste de la base en la caja del camión (sale en el final y en el parte). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	bool bLeftByTruck = false;

	// ---- la caja del camión por dentro (tanda 23)
	/** Luz de relleno dentro de la caja mientras viajas en ella, en lúmenes (0 = sin ella). Sin sombras y de radio corto:
	 *  deja ver los arcos, la lona, los bancos y la carga. Es una luz para tus ojos: no es un ALight (no cuenta para
	 *  LightAt) y fuera de la caja está apagada. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float RideFillLumens = 18.0f;

	/** Juntas de la losa del camino: una cada TruckJointPitch cm, con una de ellas en x = TruckJointPhase (las pone
	 *  desgaste_camino en tools/blender/escena_base.py; en base.json, ext.desgaste.juntas). Cada eje del camión que pisa
	 *  una da un golpe: se oye desde fuera y, dentro de la caja, sacude la vista. 0 = sin juntas. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckJointPitch = 600.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckJointPhase = 100.0f;

	/** Juntas que han pisado los ejes del camión desde que empezó la partida. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckJoints = 0;

	/** Cuánto de «dentro de la caja» suena el mundo: 0 fuera, 1 dentro (el ambiente baja y pierde los agudos). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Pruebas")
	float RideMuffle() const { return RideMuffleK; }

	/** ¿Está encendida la luz de relleno de la caja? */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Pruebas")
	bool RideLightOn() const;

	/** Lo que se mueve la vista dentro de la caja respecto a su sitio (traqueteo, golpe de junta e inercia), en cm. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Pruebas")
	FVector RideOffset() const { return RideShake; }

	/** Punto de salida de la base (portón de salida): llegar con el expediente acaba la misión (final por la salida). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Mision")
	FVector ExitLoc = FVector(6900.0f, 5300.0f, 0.0f);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Mision")
	float ExitRadius = 260.0f;

	/** Portillo de la marisma (final con Ramos). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Mision")
	FVector WicketLoc = FVector(310.0f, 4900.0f, 0.0f);

	/** Cinemáticas de Sequencer (tools/unreal/cinematicas.py las crea en /Game/Tarsis/Cine). Sin ellas, el juego va igual. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Cine")
	bool bPlayIntro = true;

	/** Hay una cinemática en marcha (E o Espacio la saltan). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Cine")
	bool bCine = false;

	UFUNCTION()
	void OnCineFinished();

	/** Segundos que tarda el guardia en arrancar el generador una vez junto a él. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Luz")
	float RepairSeconds = 12.0f;

	/** Trozos del nombre de los materiales de ventana iluminada y bombillas (lh_ventana_on, lh_bombilla): con el apagón se cambian por uno oscuro. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Luz")
	TArray<FString> WindowMaterialKeys = { TEXT("ventana"), TEXT("window"), TEXT("emis"), TEXT("bombilla") };

	/** Dónde está el guardia que te oyó por última vez (para la flecha del HUD). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	FVector HeardFrom = FVector::ZeroVector;

	/** Segundos que queda el aviso «TE HAN OIDO». */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	float HeardT = 0.0f;

	/** Q: lanza una piedra hacia donde miras; los guardias a menos de NoiseRadius van a mirar. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void ThrowStone();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis")
	float NoiseRadius = 900.0f;

	/** Dónde cayó la última piedra (para pruebas). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	FVector LastStone = FVector::ZeroVector;

	/** B: prismáticos (zoom); el guardia al que miras queda marcado. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void ToggleBinoculars();

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	bool bBinoculars = false;

	// ---- tanda 31: linternas. Los guardias la sacan donde no llega la luz (ATarsisGuard::AutoTorchTick) y tú llevas
	// la tuya (F): ves en lo oscuro, pero con ella encendida te ven como a plena luz, y el guardia al que alumbras
	// de cerca viene a mirar. Los proyectores de las torres llevan cristal encendido y destello para que se lean de lejos.
	/** Los guardias de suelo encienden la linterna donde no llega luz. Las pruebas viejas lo apagan. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	bool bContextTorch = true;
	/** Llevas linterna (un objeto del equipo: una misión puede empezar sin ella). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	bool bHasTorch = true;
	/** Tu linterna está encendida. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Linterna")
	bool bTorch = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	/** Tanda 32: lo que alumbras a menos de esta distancia (cm) recibe menos luz, hasta TorchNearMin de cerca: como el ojo que se
	 *  acostumbra, y el guardia deslumbrado o la pared a un palmo dejan de salir blancos. 0 lo quita. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchNearDist = 600.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchNearMin = 0.18f;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Linterna")
	float TorchDimNow() const { return TorchDim; }
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchLumens = 300.0f;   // ajuste 31c: con 450 quemaba el suelo y a los guardias a 2-3 m
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchRange = 2200.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchCone = 21.0f;
	/** Tu linterna da sombra (una sola luz con sombra; quitar si la tarjeta no puede). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	bool bTorchShadows = true;
	/** Hasta dónde nota un guardia que le alumbras (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchNoticeDist = 1400.0f;
	/** A bocajarro (cm) y con el guardia de cara, tu linterna le deslumbra TorchBlindSeconds; no repite hasta TorchBlindAgain s despues. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchBlindDist = 450.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchBlindSeconds = 2.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchBlindAgain = 9.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Linterna")
	int32 TorchBlinds = 0;
	/** Veces que un guardia ha ido a mirar porque le has alumbrado. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Linterna")
	int32 TorchNotices = 0;
	/** Cristal y destello de los proyectores de torre (cm; 0 los quita). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float BeamLensSize = 34.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float BeamGlowSize = 80.0f;
	/** Proyectores de torre con cristal encendido puesto. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Linterna")
	int32 BeamLenses = 0;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Linterna")
	void ToggleTorch();
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Linterna")
	void SetTorch(bool bOn);
	/** La luz de tu linterna (nullptr si aún no la has encendido nunca). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Linterna")
	class USpotLightComponent* TorchComp() const { return PlayerTorch; }
	void SetupBeamLenses();
	void TorchTick(float DeltaSeconds);
	UPROPERTY() TObjectPtr<class USpotLightComponent> PlayerTorch;
	UPROPERTY() TArray<TObjectPtr<class UStaticMeshComponent>> BeamGlows;
	float TorchNoticeT = 0.0f;
	float TorchDim = 1.0f;   // tanda 32: 1 = toda la luz; baja cuando alumbras algo a un palmo

	// misión secundaria de Ramos: carta en su litera, agarrarlo por la espalda (1 te lo llevas, 2 lo derribas),
	// llave del botiquín del veterinario con la pistola de dardos, y salida alternativa por el portillo de la marisma

	/** Línea «SECUNDARIA» del HUD (vacía si no hay). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	FString SideObjective() const;

	/** Clic izquierdo: dispara un dardo al guardia que tienes en el centro (lo duerme sin ruido). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void ShootDart();

	// ---- tanda 29: códec (TarsisCodec.cpp). Control (141.12) y Roig (140.85) hablan contigo por una frecuencia que no
	// es la de la base; la tercera voz (000.00) solo aparece sin luz o con el expediente. Las llamadas entrantes no
	// paran el juego: suenan y se cogen con la R cuando puedes. Con la R sin llamada, eliges a quién llamar (1, 2, 3).
	// Durante la conversación el juego está en pausa. Los diálogos son textos «codec_<nombre>» de mision1.json: una
	// línea por frase, «C|...» Control, «T|...» tú, «R|...» Roig, «F|...» la voz sin nombre.
	/** Llamadas entrantes automáticas (inicio, alarma, archivo, expediente, apagón). Las pruebas las apagan. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Codec")
	bool bCodecCalls = true;
	/** Conversación abierta (juego en pausa). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Codec")
	bool bCodec = false;
	/** Menú de frecuencias abierto (el juego sigue). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Codec")
	bool bCodecMenu = false;
	/** Llamada entrante sin coger. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Codec")
	FName CodecPending;
	/** Conversaciones que ya has tenido, en orden. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Codec")
	TArray<FString> CodecTaken;
	/** Frase por la que va la conversación. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Codec")
	int32 CodecIdx = 0;
	/** Segundos que suena una llamada entrante y que aguanta abierto el menú de frecuencias, y letras por segundo. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Codec")
	float CodecRingSeconds = 14.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Codec")
	float CodecMenuSeconds = 9.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Codec")
	float CodecCharsPerSecond = 46.0f;
	float CodecRingT = 0.0f;
	float CodecMenuT = 0.0f;

	/** Entra una llamada: suena, se anuncia en pantalla y espera a la R. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Codec")
	void CodecRing(FName Conv);
	/** La tecla R: coge la llamada pendiente o abre y cierra el menú de frecuencias. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Codec")
	void CodecKey();
	/** Abre una conversación por su nombre (texto «codec_<nombre>»). Devuelve si se ha abierto. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Codec")
	bool OpenCodec(FName Conv);
	/** Completa la frase que se está escribiendo o pasa a la siguiente; tras la última, cuelga. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Codec")
	void CodecNext();
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Codec")
	void CloseCodec();
	/** Llamas tú desde el menú: 1 Control, 2 Roig, 3 la voz sin nombre (si está). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Codec")
	void CodecCall(int32 Option);
	/** Qué conversación de Control toca ahora, según la base y el objetivo. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Codec")
	FName CodecControlConv() const;
	/** La tercera frecuencia ya se puede marcar. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Codec")
	bool CodecVoiceOpen() const { return bPowerOff || bCodecVoiceHeard; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Codec")
	TArray<FString> CodecMenuLines() const;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Codec")
	int32 CodecLineCount() const { return CodecLines.Num(); }
	/** La frase actual como «QUIEN|FRECUENCIA|texto». */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Codec")
	FString CodecLine() const;
	/** Aviso de la llamada entrante para el HUD (vacío si no hay). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Codec")
	FString CodecPendingText() const;
	/** Pruebas: olvida la llamada pendiente, lo ya hablado y la cuenta de llamadas. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Pruebas")
	void CodecReset();

	struct FCodecLine { FString Who; FString Freq; FName Port; FString Text; bool bMe = false; };
	TArray<FCodecLine> CodecLines;
	/** Letras ya escritas de la frase actual (va con el reloj real: el juego está en pausa). */
	int32 CodecTyped() const;
	/** Lo llama el HUD en cada fotograma con el códec abierto: los pitidos de la escritura. */
	void CodecFrame();
	/** Retrato ilustrado de /Game/Tarsis/Retratos (tools/unreal/retratos.py); si falta, el HUD dibuja el de puntos. */
	class UTexture* Portrait(FName Key);
	FString CodecHelp() const;
	bool bCodecVoiceHeard = false;

	// ---- tanda 28: «Responde, Carmona». La central llama a un guardia que has dejado en el suelo; si estás junto a
	// él, contestas tú por su radio eligiendo entre tres partes. Solo cuela el suyo, que habrás oído antes si andabas
	// cerca cuando lo daba. «Todo tranquilo» es la frase de coacción: parece la natural y trae a dos con la base en guardia
	/** Interruptor general de contestar por radio y de los partes que se oyen. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	bool bRadioAnswer = true;
	/** La central espera tu respuesta (teclas 1, 2 y 3). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Radio")
	bool bRadioAsk = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Radio")
	TArray<FString> RadioOptions;
	/** Cuál de las tres cuela y cuál es la de coacción (1 a 3). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Radio")
	int32 RadioRight = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Radio")
	int32 RadioDuress = 0;
	/** Veces que has engañado a la central. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Radio")
	int32 RadioFooled = 0;
	/** Guardias a los que has oído dar el parte. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Radio")
	TArray<FString> HeardPartes;
	/** Segundos para contestar, cada cuánto da el parte cada guardia, a qué distancia lo oyes y a cuánto del cuerpo llegas a su radio (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	float RadioAnswerSeconds = 10.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	float ParteEvery = 75.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	float ParteHearDist = 1600.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	float RadioReach = 400.0f;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Radio")
	void AnswerRadio(int32 Option);
	/** El guardia da su parte ahora (lo oyes si estás a menos de ParteHearDist). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Radio")
	void SayParte(class ATarsisGuard* G);
	UFUNCTION(BlueprintPure, Category = "Tarsis|Radio")
	FString ParteOf(const FString& Name) const;

	// ---- tanda 28: nadie entra solo a mirar donde falta la farola (ATarsisGuard::WaitForBuddy)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sigilo")
	bool bBuddyRule = true;
	/** Radio de la sombra de una farola rota, hasta dónde se busca compañero y cuánto se le espera. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sigilo")
	float DarkZoneRadius = 900.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sigilo")
	float BuddyCallRadius = 7000.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Sigilo")
	float BuddyWaitSeconds = 22.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sigilo")
	int32 BuddyCalls = 0;

	/** Respuesta a Ramos: 1 llevarlo contigo, 2 derribarlo. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void Choose(int32 Option);

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ramos")
	bool bChoice = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ramos")
	bool bRamosKnown = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ramos")
	bool bRamosTalked = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ramos")
	bool bRamosAlly = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ramos")
	bool bVetKey = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ramos")
	bool bVetOpen = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ramos")
	bool bLetter = false;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ramos")
	int32 Darts = 0;

	/** Saliste por la marisma con Ramos. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ramos")
	bool bMarsh = false;

	// ---- menú de pausa (P o Esc; en el editor Esc para el PIE, así que P) y puntos de control

	/** Menú de pausa abierto (el juego está en pausa). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Menu")
	bool bMenu = false;

	/** Opción marcada del menú. */
	int32 MenuSel = 0;

	/** Líneas del menú tal como se ven (con el valor de cada opción). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Menu")
	TArray<FString> MenuLines() const;

	/** Pruebas automáticas: pulsa una tecla del menú por su nombre («P», «Down», «Right», «Enter»...) sin teclado real. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Pruebas")
	void PressKey(FName Key) { const FKey K(Key); MenuKey(K); AnyKey(K); }   // en el mismo orden que BindAll: menú y luego AnyKey

	/** Opciones: sensibilidad del ratón (0,2-3), invertir Y, volumen (0-1), calidad (0 baja - 3 épica) y contador de fps. */
	float OptSensitivity = 1.0f;
	bool bOptInvertY = false;
	float OptVolume = 1.0f;
	int32 OptQuality = 1;
	bool bShowFps = false;
	float OptMusic = 0.7f;
	bool bShowHelp = true;
	/** Accesibilidad: tamaño del texto del HUD (0,8-1,4), colores para daltonismo y subtítulos de sonidos. */
	float OptTextScale = 1.0f;
	bool bColorblind = false;
	bool bSubtitles = false;
	/** Dificultad: 0 fácil, 1 normal, 2 difícil (vista y oído de los guardias; en difícil no hay puntos de control). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Menu")
	int32 Difficulty = 1;

	/** Subtítulo de sonido ahora mismo («[PASOS - MOYA, DETRAS A LA IZQUIERDA, 8 m]») y segundos que le quedan. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Menu")
	FString Subtitle;
	float SubtitleT = 0.0f;

	/** Veces que un guardia te ha visto (pasa a alerta por verte, no por la radio). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	int32 Detections = 0;

	/** Puntuación de sigilo al acabar (0-1000) y su rango («FANTASMA»...). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	int32 Score = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	FString Rank;

	/** Parte del día siguiente: sale tras el mensaje final y resume lo que dejaste en la base (lo leerá la misión 2). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bReport = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	TArray<FString> ReportLines;

	/** Fotogramas en que el HUD ha dibujado el parte (para las pruebas). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	int32 ReportFrames = 0;

	/** Estado que pasa a la misión 2. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bPowerCutOnce = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bReserveHalf = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	bool bRamosDowned = false;

	/** Página del menú: 0 la principal, 1 los controles. Esperando tecla para la acción ActionSel (o -1). */
	int32 MenuPage = 0;
	int32 WaitKeyFor = -1;

	/** Acciones con tecla configurable (nombre en pantalla y tecla actual). */
	static constexpr int32 NumActions = 8;
	FKey ActionKeys[NumActions];
	static const TCHAR* ActionName(int32 I);

	/** Tira de ayuda de abajo a la derecha: teclas de lo que puedes hacer ahora. */
	UFUNCTION(BlueprintPure, Category = "Tarsis")
	FString HelpLine() const;

	/** Capas de música (0-1 cada una), para el HUD de pruebas. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Musica")
	float MusicTension = 0.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Musica")
	float MusicAlert = 0.0f;

	/** Último punto de control («la llave de Ibarra»...) y segundos que queda el aviso en pantalla. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Menu")
	FString CheckpointName;
	float CheckT = 0.0f;

	/** Hay partida guardada en disco (para «Continuar desde el último punto»). */
	bool bHasSave = false;

	/** Guarda un punto de control: dónde estás ahora y cómo va la misión (también en disco). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void Checkpoint(const FString& Name);

	/** Guardado en disco: vuelve al último punto de control con la misión como estaba. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	bool LoadCheckpoint();

	/** Guardia caído que vas arrastrando (o nullptr). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	TObjectPtr<class ATarsisGuard> Dragged;

	// ---- sonido del mundo: superficies, pasos de los guardias y voces

	/** Lo que hay bajo ese punto: "grava", "cemento", "metal", "madera" o "hierba" (material físico PM_*, o el nombre de
	 *  la malla o del material). De ello salen el sonido de los pasos y lo lejos que se oyen los tuyos. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Sonido")
	FString SurfaceAt(FVector Where) const;

	/** Superficie de tu último paso y pasos dados (para las pruebas). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sonido")
	FString LastStepSurface;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sonido")
	int32 PlayerSteps = 0;

	/** Pasos de guardias que han sonado (cerca de ti). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sonido")
	int32 GuardStepsPlayed = 0;

	/** Un guardia apoya un pie (lo llama ATarsisGuard a compás de su animación): suena en 3D según el suelo. */
	void GuardStep(class ATarsisGuard* G, bool bRun);

	/** Un guardia dice una frase (voz_<guardia>_<clave>, tools/sonido/generar_voces.py): en 3D sobre él, con subtítulo
	 *  si están activados. Claves: quien, ruido, viento, alto, nadie, suelo (por radio). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Sonido")
	void GuardSay(class ATarsisGuard* G, const FString& Key, bool bRadio = false);

	/** Última frase dicha («moya_ruido») y cuántas van (para las pruebas). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sonido")
	FString LastVoice;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sonido")
	int32 VoicesPlayed = 0;

	/** Últimas 30 frases dichas («moya_ruido»...), para las pruebas. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Sonido")
	TArray<FString> VoiceLog;

	/** Subtítulos de sonido (opción del menú); para las pruebas. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Sonido")
	void SetSubtitles(bool bOn) { bSubtitles = bOn; }

	// ---- tus brazos en primera persona (maniquí de la plantilla) con la pistola de dardos

	/** Se ven los brazos con la pistola (cuando tienes dardos y nada te ocupa las manos). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Jugador")
	bool bArmsVisible = false;

	/** Animación de los brazos sosteniendo la pistola y momento en que se congela (-1 = en bucle). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Jugador")
	FString ArmsAnimPath = TEXT("/Game/Characters/Mannequins/Anims/Pistol/MF_Pistol_Idle_ADS.MF_Pistol_Idle_ADS");

	/** Dónde quedan los brazos respecto a la cámara (cm: delante, derecha, arriba), con la cabeza del maniquí en la cámara. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Jugador")
	FVector ArmsOffset = FVector(16.0f, 5.0f, -8.0f);

	/** Malla de la pistola de dardos (la pistola de la plantilla) y su colocación en la mano (socket HandGrip_R). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Jugador")
	FString PistolMeshPath = TEXT("/Game/Weapons/Pistol/Meshes/SM_Pistol.SM_Pistol");
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Jugador")
	FTransform PistolGrip;

	/** Componentes de los brazos y la pistola (para las pruebas). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Jugador")
	TObjectPtr<class USkeletalMeshComponent> Arms;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Jugador")
	TObjectPtr<class UStaticMeshComponent> Pistol;

	// ---- empezar sin armas: consejos, empujón de frente y escondites

	/** Consejo de la esquina («CONSEJO: ...»): agacharse, la piedra y la E por la espalda, hasta que los usas. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ayuda")
	FString Hint;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ayuda")
	int32 HintStep = 0;

	/** Guardia al que puedes empujar ahora con la E (de frente, cerca, sin estar en alerta) o nullptr. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	class ATarsisGuard* ShoveTarget() const;

	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	int32 Shoves = 0;

	/** Metido en una taquilla: no te ven, oyes amortiguado y la vista va por las rendijas. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Escondites")
	bool bHiding = false;

	/** Taquillas (punto del suelo y hacia dónde abren): barracón oeste y sala de guardia. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Escondites")
	TArray<FVector> HideSpots = { FVector(1500.0f, 2965.0f, 0.0f), FVector(1700.0f, 2965.0f, 0.0f), FVector(5330.0f, 1235.0f, 0.0f) };
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Escondites")
	TArray<float> HideYaws = { -90.0f, -90.0f, 90.0f };

	/** Taquilla a mano (índice) o -1. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Escondites")
	int32 HideSpotNear() const;

	/** Cambios que han notado los guardias (puertas que estaban cerradas). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	int32 ChangesNoticed = 0;

	/** Pruebas: una tecla de verdad por PlayerController::InputKey (pasa por toda la pila de entrada, no como PressKey). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Pruebas")
	void SimulateKey(FName Key, bool bPress = true, bool bRelease = true);

	// ---- misión en datos (assets/unreal/mision1.json, tools/unreal/mision.py la vuelca aquí y se guarda con el nivel)

	/** Textos de la misión: clave -> texto ({0}, {1}... para los datos). Todo lo que sale en pantalla pasa por Tx. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Mision")
	TMap<FName, FString> Texts;

	/** Claves pedidas que no están en Texts (se usa el texto por defecto del C++): una prueba exige que esté vacía. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	TArray<FString> MissingTexts;

	/** Objetivos del HUD, en orden: sale el primero cuya bandera esté puesta. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Mision")
	TArray<FTarsisObjective> Objectives;

	/** Puntos de interacción sencillos (puertas, notas, objetos). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Mision")
	TArray<FTarsisPoint> Points;

	/** Banderas de la misión (llave, jefatura, nota, archivo, expediente, carta, llave_botiquin, botiquin...). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Mision")
	bool HasFlag(FName Flag) const;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Mision")
	void SetFlag(FName Flag);
	UFUNCTION(BlueprintPure, Category = "Tarsis|Mision")
	TArray<FName> FlagList() const;

	/** Texto de la misión por clave; Default si no está (y la clave se apunta en MissingTexts). */
	FString Tx(FName Key, const TCHAR* Default, const FStringFormatOrderedArguments& Args = FStringFormatOrderedArguments()) const;

	/** Explicaciones que solo salen la primera vez por partida (derribar, arrastrar, la pistola, la taquilla...). */
	void Teach(FName Key, const TCHAR* Default, const FStringFormatOrderedArguments& Args, float Seconds);
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Ayuda")
	TArray<FName> Taught;

	/** Estado de la base para el HUD: 0 tranquila, 1 en guardia, 2 alerta. */
	UFUNCTION(BlueprintPure, Category = "Tarsis")
	int32 BaseState() const;

	/** Te han cogido: escena (frase del guardia, la cámara gira hacia él, golpe y fundido a negro) y luego Captured. */
	void BeginCapture(class ATarsisGuard* G);
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	bool bCapturing = false;

	/** La central habla por radio: voz voz_central_<Key> y subtítulo (siempre, como las voces de los guardias). */
	void CentralSay(const FString& Key, const FString& Text, float Delay = 0.0f);

	/** Pruebas: los subtítulos de voz que han salido (los últimos 30). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Pruebas")
	TArray<FString> SubtitleLog;

	/** Hay una voz con subtítulo en pantalla (se ve aunque la opción de subtítulos esté apagada). */
	bool VoiceSubtitleOn() const { return VoiceSubT > 0.0f; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UPROPERTY()
	TArray<TObjectPtr<class UStaticMeshComponent>> Bars;
	float CellT = 0.0f;
	void CloseCell();
	void OpenCell();
	float LightT = 0.0f;
	void ToggleCrouch();
	void SetupPlayer();
	bool bPlayerReady = false;

	// misión
	UPROPERTY()
	TObjectPtr<class UStaticMeshComponent> DoorL;
	UPROPERTY()
	TObjectPtr<class UStaticMeshComponent> DoorV;
	UPROPERTY()
	TObjectPtr<class UStaticMeshComponent> NoteProp;
	UPROPERTY()
	TObjectPtr<class UStaticMeshComponent> FileProp;
	void SetupMission();
	class UStaticMeshComponent* AddBlock(const FVector& Loc, const FVector& Scale, const FLinearColor& Color, bool bCollide);
	static FVector Cell(int32 C, int32 R, float Z = 0.0f);
	bool NearPlayer(const FVector& P, float Radius) const;
	class ATarsisGuard* DownedNear(float Radius) const;
	void KeypadKey(FKey Key);
	void StartDrag(class ATarsisGuard* G);
	void StopDrag();
	void DragTick();
	float SavedWalk = 0.0f;
	float SavedCrouch = 0.0f;
	float KeypadErrT = 0.0f;
	float StoneT = 0.0f;
	float SavedFov = 0.0f;
	UPROPERTY()
	TArray<TObjectPtr<class UStaticMeshComponent>> Stones;
	void BinocularTick();
	UPROPERTY()
	TObjectPtr<class UStaticMeshComponent> VetDoor;
	UPROPERTY()
	TObjectPtr<class UStaticMeshComponent> LetterProp;
	class ATarsisGuard* FindGuard(const TCHAR* Name) const;
	void Finish(bool bByMarsh);
	float DartT = 0.0f;
	float StepT = 0.0f;
	float BobPhase = 0.0f;
	FVector BobApplied = FVector::ZeroVector;
	float BaseWalk = 0.0f;
	bool bIndoor = false;
	void SprintOn();
	void CycleWeather();
	void SprintOff();
	void NoiseTick(class ACharacter* C, float DeltaSeconds);
	void BobTick(class ACharacter* C, float DeltaSeconds);

	// sonido (tools/unreal/sonidos.py los importa en /Game/Tarsis/Sonidos)
	UPROPERTY()
	TObjectPtr<class USoundBase> StoneSnd;
	UPROPERTY()
	TObjectPtr<class USoundBase> DartSnd;
	UPROPERTY()
	TObjectPtr<class USoundBase> WindSnd;
	UPROPERTY()
	TObjectPtr<class USoundBase> RainSnd;
	UPROPERTY()
	TObjectPtr<class USoundBase> RadioSnd;
	UPROPERTY()
	TMap<TObjectPtr<class ATarsisGuard>, float> BaseWalkSpeed;
	UPROPERTY()
	TObjectPtr<class USoundAttenuation> Atten;
	UPROPERTY()
	TObjectPtr<class UAudioComponent> WindComp;
	UPROPERTY()
	TObjectPtr<class UAudioComponent> RainComp;
	UPROPERTY()
	TMap<TObjectPtr<class ATarsisGuard>, float> GuardStride;
	UPROPERTY()
	TMap<TObjectPtr<class ATarsisGuard>, float> BaseView;
	UPROPERTY()
	TObjectPtr<class UInstancedStaticMeshComponent> RainISM;
	TArray<FVector> Drops;
	float BaseFog = -1.0f;
	float PlayerStride = 0.0f;
	void SetupSound();
	/** Surface: 0 grava, 1 cemento, 2 metal, 3 madera, 4 hierba. */
	void StepSound(const FVector& Where, int32 Surface, float Volume, bool b3D);
	int32 SurfaceIndex(const FVector& P, const AActor* Ignore) const;
	/** Pasos por superficie: 5 superficies x 3 variantes (paso_<superficie>_N). */
	UPROPERTY()
	TArray<TObjectPtr<class USoundBase>> StepSnds;
	/** Efectos sueltos cargados la primera vez que suenan (puertas, teclado, objetos, voces...). */
	UPROPERTY()
	TMap<FName, TObjectPtr<class USoundBase>> SfxCache;
	class USoundBase* Sfx(const FString& Name);
	void PlaySfx(const FString& Name, const FVector& Where, float Volume = 1.0f, bool b3D = true);
	UPROPERTY()
	TObjectPtr<class UAudioComponent> CricketComp;
	UPROPERTY()
	TObjectPtr<class UAudioComponent> RumbleComp;
	UPROPERTY()
	TMap<TObjectPtr<class ATarsisGuard>, float> VoiceNext;
	UPROPERTY()
	TMap<TObjectPtr<class ATarsisGuard>, FString> VoicePrev;
	float VoiceSubT = 0.0f;
	int32 PlayerSurface = 0;
	// brazos
	void SetupArms(class ACharacter* C);
	void ArmsTick(class ACharacter* C, float DeltaSeconds);
	float ArmsShow = 0.0f;
	float RecoilT = 0.0f;
	FRotator LastViewRot = FRotator::ZeroRotator;
	FVector Sway = FVector::ZeroVector;
	// empezar: consejos, empujón, escondites y cambios que notan los guardias
	void HintTick();
	void Shove(class ATarsisGuard* G);
	class ATarsisGuard* FacingAlertGuard() const;
	float FrontMsgT = 0.0f;
	/** Enfriamiento del aviso «no puedes irte todavía» en la salida. */
	float ExitMsgT = 0.0f;
	void SetupHiding();
	void EnterHide(int32 Index);
	void ExitHide();
	void HideTick();
	int32 HideIdx = -1;
	bool bHideSeen = false;
	UPROPERTY()
	TArray<TObjectPtr<class UStaticMeshComponent>> Lockers;
public:
	/** Malla de la taquilla (chapa biselada con rendijas de verdad, tools/unreal/ambiente.py); sin ella, cubos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Escondites")
	TSoftObjectPtr<class UStaticMesh> LockerMesh = TSoftObjectPtr<class UStaticMesh>(FSoftObjectPath(TEXT("/Game/Tarsis/Atrezo/Taquilla/SM_Taquilla.SM_Taquilla")));
	/** Pruebas: componentes que parpadean, que callan sin luz y que suenan con lluvia. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Pruebas")
	FIntVector ZoneCounts() const { return FIntVector(FlickerLights.Num(), PowerSounds.Num(), RainSounds.Num()); }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Pruebas")
	int32 RainDecalCount() const { return RainDecals.Num(); }
private:
	void AddChange(const FVector& Where, const TCHAR* Key);
	void ChangesTick(float DeltaSeconds);
	TArray<FVector> ChangeLocs;
	TArray<FString> ChangeKeys;
	TArray<bool> ChangeSeen;
	float ChangeT = 0.0f;
	// misión en datos
	TSet<FName> Flags;
	bool* FlagBool(FName Flag);
	const FTarsisPoint* PointNear() const;
	void UsePoint(const FTarsisPoint& Pt);
	UPROPERTY()
	TMap<FName, TObjectPtr<class UStaticMeshComponent>> Blocks;
	void RemoveBlockNamed(FName Name);
	// captura como escena
	UPROPERTY()
	TObjectPtr<class ATarsisGuard> Captor;
	float CaptureT = 0.0f;
	bool bCaptureLocker = false;
	bool bCaptureHit = false;
	bool bCaptureDone = false;
	void DefaultMission();
	FRotator CaptureFrom = FRotator::ZeroRotator;
	void CaptureTick(float DeltaSeconds);
	/** Frase de un guardia sin sonido (para las que aún no tienen voz): solo subtítulo. */
	void SaySubtitle(const FString& Who, const FString& Text, float Seconds = 3.0f);
	void ShowSubtitleLine(const FString& Line, float Seconds = 3.0f);
	TArray<FString> PendingSubs;
	bool IndoorAt(const FVector& P, const AActor* Ignore) const;
	void SoundTick(class ACharacter* C, float DeltaSeconds);
	void RainTick(float DeltaSeconds);
	// ---- ambiente de las zonas (tanda 18): luces con la etiqueta «parpadeo» (fluorescente viejo), sonidos con
	// «electrico» (callan sin luz) y con «lluvia» (gotera: solo si llueve). Los coloca tools/unreal/ambiente.py
	void SetupZones();
	void ZonesTick(float DeltaSeconds);
	UPROPERTY() TArray<TObjectPtr<class ULightComponent>> FlickerLights;
	TArray<float> FlickerBase;
	TArray<float> FlickerT;
	UPROPERTY() TArray<TObjectPtr<class UAudioComponent>> PowerSounds;
	UPROPERTY() TArray<TObjectPtr<class UAudioComponent>> RainSounds;
	UPROPERTY() TArray<TObjectPtr<class UDecalComponent>> RainDecals;   // charco y pisadas mojadas: solo con lluvia
	UPROPERTY() TObjectPtr<class UMaterialParameterCollection> WetMPC;
	bool bWetInit = false;
	void WetTick(float DeltaSeconds);
	bool bCloudInit = false;
	void CloudTick(float DeltaSeconds);
	// halos de las luminarias (tanda 25) y la luz de cada uno
	UPROPERTY() TArray<TObjectPtr<AActor>> Halos;
	UPROPERTY() TArray<TObjectPtr<class ULightComponent>> HaloLights;
	// resplandores de relleno de las farolas (luces con la etiqueta «decorado») y la farola de cada uno
	UPROPERTY() TArray<TObjectPtr<class ULightComponent>> DecorLights;
	UPROPERTY() TArray<TObjectPtr<class ULightComponent>> DecorOf;
	int32 HalosLit() const;
	void ApplyRenderCVars();
	TArray<TPair<FString, FString>> RenderSaved;      // variable y valor de antes, para dejarlo como estaba
	void RadioTick(float DeltaSeconds);
	void RadioSend(class ATarsisGuard* Fallen, int32 HowMany);
	void PartesTick();
	void StartRadioAsk(class ATarsisGuard* G);
	UPROPERTY()
	TObjectPtr<class ATarsisGuard> RadioAskGuard;
	float RadioAskT = 0.0f;
	TMap<TObjectPtr<class ATarsisGuard>, float> ParteNext;
	UPROPERTY()
	TSet<TObjectPtr<class ATarsisGuard>> Called;
	FLinearColor BaseFogColor = FLinearColor::Black;
	int32 SavedVolFog = -1;

	// generador
	UPROPERTY()
	TObjectPtr<class USoundBase> HumSnd;
	UPROPERTY()
	TObjectPtr<class UAudioComponent> HumComp;
	UPROPERTY()
	TArray<TObjectPtr<class ULightComponent>> OffLights;
	/** El que han mandado a arreglar el generador (visible para las pruebas). */
	UPROPERTY(VisibleInstanceOnly, Category = "Tarsis|Luz")
	TObjectPtr<class ATarsisGuard> Repairer;
	float RepairT = 0.0f;
	UPROPERTY()
	TArray<TObjectPtr<class UMeshComponent>> WinComps;
	TArray<int32> WinSlots;
	UPROPERTY()
	TArray<TObjectPtr<class UMaterialInterface>> WinMats;
	UPROPERTY()
	TObjectPtr<class UMaterialInstanceDynamic> DarkWindow;
	void CutPower();
	void RestorePower(bool bByGuard);
	void PowerTick(float DeltaSeconds);
	void WindowsDark(bool bDark);
	UPROPERTY()
	TArray<TObjectPtr<class ULightComponent>> PendingOff;
	float OffClock = 0.0f;
	UPROPERTY()
	TObjectPtr<class UStaticMeshComponent> BarrierArm;
	UPROPERTY()
	TObjectPtr<class UStaticMeshComponent> BarrierPost;
	float BarrierTarget = 0.0f;
	// camión de suministros y hoja del portón de entrada
	UPROPERTY()
	TArray<TObjectPtr<AActor>> TruckParts;
	UPROPERTY()
	TArray<TObjectPtr<AActor>> EntryLeaf;
	UPROPERTY()
	TObjectPtr<class ASpotLight> TruckLamp;
	UPROPERTY()
	TObjectPtr<class ASpotLight> TruckLamp2;
	UPROPERTY()
	TArray<TObjectPtr<class UStaticMeshComponent>> TruckGlows;
	void ShadowTick(ACharacter* C, float DeltaSeconds);
	float ShadowT = 0.0f;
	int32 TruckProfiles = 0;
	UPROPERTY()
	TObjectPtr<class UAudioComponent> TruckAudio;
	UPROPERTY()
	TObjectPtr<class USoundAttenuation> TruckAtten;
	float TruckT = 0.0f;
	float TruckX = 0.0f;
	float TruckV = 0.0f;
	float TruckWaitT = 0.0f;
	float TruckSeenT = 0.0f;
	float TruckBlockT = 0.0f;
	float TruckHornT = 0.0f;
	float EntryGateTarget = 0.0f;
	bool bEntryGateShut = false;
	void SetupTruck();
	void TruckTick(float DeltaSeconds);
	void TruckReset(float Wait);
	void TruckShow(bool bShow);
	void TruckPlace();
	void TruckHorn(const FVector& Where, int32 Why);
	// control de salida y viaje en la caja (tanda 22)
	UPROPERTY()
	TObjectPtr<class ATarsisGuard> TruckInspector;
	float TruckCheckT = 0.0f;
	bool bTruckCalled = false;
	bool bRideSeen = false;
	bool bCaptureTruck = false;
	void TruckControlTick(float DeltaSeconds);
	void RidePlace();
	void RideTick();
	// la caja por dentro (tanda 23)
	UPROPERTY()
	TObjectPtr<class UPointLightComponent> RideLight;
	UPROPERTY()
	TObjectPtr<class UAudioComponent> RideAudio;
	float RideMuffleK = 0.0f;
	float RideKick = 0.0f;      // golpe vertical al pisar una junta (cm): un muelle amortiguado
	float RideKickV = 0.0f;
	float RideLurch = 0.0f;     // el cuerpo se va hacia la cabina al frenar y hacia el portalón al arrancar (cm)
	FVector RideShake = FVector::ZeroVector;
	void TruckFeel(float PrevX, float PrevV, float DeltaSeconds);
	void RideFeelTick(float DeltaSeconds);
	UPROPERTY()
	TObjectPtr<class ASpotLight> GateLamp;
	bool bLampBroken = false;
	bool bLampReported = false;
	UPROPERTY()
	TObjectPtr<class ATarsisGuard> LampChecker;
	float RepairCallT = 0.0f;
	bool bRepairerSilent = false;
	bool ShootLamp(const FVector& From, const FVector& Fwd, float MaxT);
	// tanda 27: farolas rotas de un dardo (no vuelven con el generador), y la que va a mirar el guardia que oyó los cristales
	UPROPERTY()
	TArray<TObjectPtr<class ULightComponent>> BrokenLights;
	UPROPERTY()
	TObjectPtr<class ALight> CheckLamp;
	FVector CheckSpot = FVector::ZeroVector;
	TArray<FVector> BrokenSpots;   // el suelo bajo cada farola rota, y si algún guardia la ha encontrado ya
	TArray<bool> BrokenSeen;
	void LampsTick();
	bool BreakableLamp(const class ALight* A) const;
	void CoverLamp(const class ALight* Lamp);
	UPROPERTY()
	TArray<TObjectPtr<class UStaticMeshComponent>> LampCovers;
	/** Dónde se pone el reparador: al sur del generador, despejado (encima de la malla el camino sale parcial). */
	FVector RepairSpot() const { return GeneratorLoc + FVector(0.0f, 280.0f, 0.0f); }
	void SetupBarrier();
	void BarrierTick(float DeltaSeconds);

	// menú y guardado
	bool bHasCheck = false;
	FVector CheckLoc = FVector::ZeroVector;
	FRotator CheckRot = FRotator::ZeroRotator;
	int32 CheckDarts = 0;
	float BaseYawScale = 1.0f;
	float BasePitchScale = 1.0f;
	bool bScalesRead = false;
	void TogglePause();
	void MenuKey(FKey Key);
	void MenuActivate(int32 Dir);
	void ApplyOptions();
	void SaveOptions() const;
	void LoadOptions();
	void BindMenuKeys();
	void BindAll();
	void AnyKey(FKey Key);
	uint64 KeyFrame = 0;
	void DefaultKeys();

	// música por capas (tools/sonido/generar_sonidos.py): ambiente siempre, tensión con la sospecha, alerta con la alarma
	UPROPERTY()
	TObjectPtr<class UAudioComponent> MusicBase;
	UPROPERTY()
	TObjectPtr<class UAudioComponent> MusicTen;
	UPROPERTY()
	TObjectPtr<class UAudioComponent> MusicAlr;
	void SetupMusic();
	void MusicTick(float DeltaSeconds);

	// códec (tanda 29)
	UPROPERTY()
	TMap<FName, TObjectPtr<class UTexture>> PortraitCache;
	bool OpenCodecList(const TArray<FName>& Convs);
	void CodecTick(float DeltaSeconds);
	void CodecInput(FKey Key);
	double CodecLineStart = 0.0;
	int32 CodecBlips = 0;
	int32 CodecControlCalls = 0;
	int32 CodecRoigCalls = 0;
	int32 CodecVoiceCalls = 0;
	bool bCodecInit = false;
	bool bCodecPrevAlert = false;
	bool bCodecPrevVault = false;
	bool bCodecPrevFile = false;
	bool bCodecPrevPower = false;
	UPROPERTY()
	TMap<TObjectPtr<class ATarsisGuard>, uint8> PrevState;
	void DetectTick();
	void BuildReport();
	float ReportWait = -1.0f;
	FString Direction(const FVector& Where) const;
	float SubtitleDist = 0.0f;

	// cinemáticas
	UPROPERTY()
	TObjectPtr<class ULevelSequencePlayer> CinePlayer;
	bool bCineIntro = false;
	bool PlayCine(const TCHAR* Name, bool bIntro);
	void SkipCine();
	void IntroText();
	bool bRamosSent = false;
};
