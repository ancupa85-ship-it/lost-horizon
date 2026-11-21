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
#include "TarsisGaspTurn.h"
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

/** Tanda 41. Dato del mapa mental: va en la ficha de un soldado (Card). Saberlo es tener la bandera dato_<Id>. */
USTRUCT(BlueprintType)
struct FTarsisFact
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Id;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FString Card;
	/** Clave del texto; clase (objeto, costumbre, debilidad, historia); ficha con la que lo une una linea; bandera que pone. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Text;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Kind;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FString Link;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Sets;
};

/** Tanda 41. Charla entre dos guardias (A y B) en Spot, a partir del segundo After de la mision. Por frase: quien la
dice (Who), la clave del texto (Lines) y el dato que da al oirla (Facts; None si ninguno). */
USTRUCT(BlueprintType)
struct FTarsisTalk
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FName Id;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FString A;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FString B;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") FVector Spot = FVector::ZeroVector;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") float After = 0.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") TArray<FString> Who;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") TArray<FName> Lines;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis") TArray<FName> Facts;
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
	float TruckStopX() const { return (bTruckStayed || TruckStaySeconds <= 0.0f) ? TruckBarrierStopX : TruckStayX; }
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
	/** Tanda 40: control tambien al entrar (segundos de papeles ante el porton; 0 = sin control) y parada ante el hangar
	(x del morro y segundos; 0 = no para). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckEntryPapers = 5.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckStayX = 4900.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Camion")
	float TruckStaySeconds = 45.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckStays = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckEntryChecks = 0;
	/** Veces que el registro del control miro la caja del camion contigo dentro de la de carton y no te encontro. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Camion")
	int32 TruckBoxPasses = 0;
	bool bTruckStayed = false;
	bool bEntryOpened = false;
	bool bEntryAsked = false;
	float TruckStayT = 0.0f;

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

	// ---- tanda 48: intro de anime (video antes de dar el mando; TarsisIntro.cpp)
	/** Poner el video de entrada si esta en Content/Movies. Sin el, el sobrevuelo de siempre. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Intro")
	bool bIntroMovie = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Intro")
	FString IntroMovie = TEXT("intro_brecha.mp4");
	/** A los cuantos segundos empieza a teclearse el rotulo, a cuantas letras por segundo, y tope de duracion. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Intro")
	float MovieCaptionAt = 4.5f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Intro")
	float MovieCaptionRate = 16.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Intro")
	float MovieMaxSeconds = 45.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Intro")
	bool bMovie = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Intro")
	float MovieT = 0.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Intro")
	int32 MoviesPlayed = 0;
	UPROPERTY()
	TObjectPtr<class UMediaPlayer> IntroPlayer;
	UPROPERTY()
	TObjectPtr<class UMediaTexture> IntroTexture;
	UPROPERTY()
	TObjectPtr<class UMediaSoundComponent> IntroSound;
	UPROPERTY()
	TObjectPtr<class UFileMediaSource> IntroSource;
	bool PlayIntroMovie();
	void CloseIntroMovie();
	void EndIntroMovie();
	void MovieTick(float DeltaSeconds);
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Intro")
	FString MovieCaption() const;

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
	/** Tanda 32: lo que alumbras a menos de esta distancia (cm) recibe menos luz, hasta TorchNearMin de cerca: como el ojo que se
	 *  acostumbra, y el guardia deslumbrado o la pared a un palmo dejan de salir blancos. 0 lo quita. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchNearDist = 1000.0f;   // tanda 33: con 600 todo lo cercano quedaba como a 6 m, casi blanco de noche
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchNearMin = 0.008f;   // tanda 33: con 0,05 la pared a 50 cm seguia siendo un disco blanco (compensa hasta unos 55 cm)
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
	/** Tanda 42: tu linterna parpadea cada pocos segundos (el hueco entre parpadeos sale al azar de TorchFlickerGaps). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	bool bTorchFlicker = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	TArray<float> TorchFlickerGaps = { 6.0f, 12.0f, 10.0f, 30.0f };
	/** Lo que dura un parpadeo (s), entre los dos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchFlickerMin = 0.35f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchFlickerMax = 0.9f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Linterna")
	int32 TorchFlickers = 0;
	/** Segundos hasta el proximo parpadeo (pruebas: ponerlo a 0,1). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Linterna")
	float TorchFlickerNext = 6.0f;
	/** Lumenes que da ahora mismo tu linterna (con el ajuste del menu, la atenuacion de cerca y el parpadeo). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Linterna")
	float TorchNow() const { return TorchLumens * OptTorchMul * TorchDim * TorchFlick; }
	float TorchFlick = 1.0f;
	float TorchFlickT = 0.0f;
	float TorchFlickStep = 0.0f;

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

	// ---- tanda 32: dos puzles de radio (TarsisEmisora.cpp)
	/** La charla por la red entre Lobato y Carmona sobre la frase de coaccion: suena pasados RadioChatAfter s de mision, con
	 *  los dos de ronda y tu a menos de ParteHearDist de uno. Oirla pone la bandera «sabe_coaccion». */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	bool bRadioChat = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	float RadioChatAfter = 120.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Radio")
	int32 RadioChats = 0;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Radio")
	bool StartRadioChat(bool bForce);
	/** La emisora de transmisiones (punto «emisora» de mision1.json, bandera «emisora_muda»). Muda, la central no llama a
	 *  los caidos, no hay partes ni voces de la central. A los RadioDeadSeconds sale el guardia mas cercano a arreglarla
	 *  (RadioFixSeconds plantado ante ella); arreglada (bandera «emisora_reparada»), la base queda en guardia. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	FVector EmisoraLoc = FVector(6275.0f, 2000.0f, 0.0f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	float RadioDeadSeconds = 90.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	float RadioFixSeconds = 14.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	float EmisoraStand = 110.0f;   // se planta a este lado de la mesa (cm hacia +X), de cara a la emisora
	/** Segundos que lleva muda la red. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Radio")
	float RadioDeadT = 0.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Radio")
	int32 RadioRepairsSent = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Radio")
	int32 RadioRepairs = 0;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Radio")
	bool RadioDead() const;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Radio")
	class ATarsisGuard* EmisoraFixerNow() const { return EmisoraFixer.Get(); }

	// ---- tanda 35: el calabozo (TarsisCalabozo.cpp). Convencer al cabo Vidal en tres pasos o la llave bajo la losa
	/** Con el puzle, la reja ya no se abre sola a los CellTime segundos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	bool bCellPuzzle = true;
	/** La losa suelta del rincon (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	FVector CellSlab = FVector(6545.0f, 2640.0f, 3.5f);
	/** Segundos entre salir con la llave y que alguien encuentre la celda vacia (la base queda en guardia). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	float CellAlertSeconds = 45.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	float CellAlertT = 0.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	int32 CellAlerts = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	bool bCellAsk = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	TArray<FString> CellOptions;
	/** Lo que dice o hace Vidal antes de las tres respuestas (la caja de conversacion del HUD, tanda 36). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	FString CellQuestion;
	/** Para las pruebas: fotogramas en que el HUD ha dibujado la caja de conversacion. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	int32 CellAskFrames = 0;
	/** Tanda 36: Vidal con cuerpo. Aparece al encerrarte, junto a la reja por fuera; lleva el cuerpo de este guardia. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	FString VidalLooksLike = TEXT("Vega");
	/** Donde se planta, respecto a CellDoor (cm), y hacia donde mira mientras hablais y cuando se vuelve a la pared. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	FVector VidalOffset = FVector(60.0f, -120.0f, 0.0f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	float VidalYaw = 120.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	float VidalWallYaw = 0.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	TObjectPtr<class USkeletalMeshComponent> VidalBody;
	/** Para las pruebas: hacia donde mira ahora (grados), o -1000 si no esta. */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Calabozo")
	float VidalFacing() const { return VidalBody ? VidalFace : -1000.0f; }
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	int32 CellRight = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	int32 CellStage = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	int32 CellFails = 0;
	/** Segundos junto a la reja hasta oir que reza Vidal (el De profundis: vale para rezar con el). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	float CellPraySeconds = 4.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	bool bCellHeardPrayer = false;
	/** Segundos que se lee lo que contesta Vidal antes de que vuelva la pregunta sola (0 = hay que pulsar E otra vez). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	float CellAutoAsk = 4.0f;
	/** Lumenes de la luz que alumbra la cara de Vidal desde el lado de la reja (0 = sin luz). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Calabozo")
	float VidalLightLm = 90.0f;
	/** Veces que has contestado sin saber bastante (no cuenta como error; el juego dice que te falta). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	int32 CellLacks = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	bool bVidalGone = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	int32 CellByVidal = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Calabozo")
	int32 CellByKey = 0;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Calabozo")
	bool InCell() const;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Calabozo")
	FString CellPrompt() const;
	/** La E dentro del calabozo: la losa, hablar con Vidal o abrir con la llave. Devuelve si ha hecho algo. */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Calabozo")
	bool CellInteract();

	// ---- tanda 39: tus cosas las tiene Peris (TarsisEquipo.cpp)
	/** Al encerrarte te quitan linterna, prismaticos y dardos; estan en el cajon de Peris (GearSpot). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Equipo")
	bool bGearRule = true;
	/** El cajon de la mesa de Peris, en la sala de guardia (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Equipo")
	FVector GearSpot = FVector(5700.0f, 1500.0f, 0.0f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Equipo")
	float GearRadius = 150.0f;
	/** Segundos registrando el cajon (se corta si te apartas). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Equipo")
	float GearSeconds = 5.0f;
	/** A que distancia se oye revolver el cajon (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Equipo")
	float GearHeard = 600.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Equipo")
	bool bGearTaken = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Equipo")
	bool bGearBack = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Equipo")
	bool bGearSearching = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Equipo")
	int32 GearTries = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Equipo")
	int32 GearDarts = 0;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Equipo")
	void TakeGear();
	// ---- tanda 42: bengalas de las torres, dia o noche y brillo (TarsisBengala.cpp)
	/** De vez en cuando una torre lanza una bengala: mientras cae, la base se ve como de dia salvo a la sombra o bajo techo. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	bool bFlares = true;
	/** Segundos entre bengalas (al azar entre los dos) y lo que dura cada una. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	float FlareEveryMin = 240.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	float FlareEveryMax = 420.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	float FlareSeconds = 14.0f;
	/** Altura a la que estalla y a la que se apaga (cm), fuerza en candelas, radio y cono. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	float FlareHeight = 6500.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	float FlareEndHeight = 3200.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	float FlareCandelas = 26000.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	float FlareRadius = 14000.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	float FlareCone = 62.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	FLinearColor FlareColor = FLinearColor(1.0f, 0.52f, 0.36f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	bool bFlareShadows = true;
	/** Bengalas lanzadas, y si hay una en el aire. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Bengala")
	int32 FlaresFired = 0;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Bengala")
	bool FlareUp() const { return FlareT > 0.0f; }
	/** Segundos que faltan para la siguiente (pruebas). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Bengala")
	float FlareNext = 150.0f;
	/** Lanza una ya, desde la torre mas cercana al jugador que tenga centinela (o sobre el jugador si no hay torres). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Bengala")
	void FireFlare();
	UFUNCTION(BlueprintPure, Category = "Tarsis|Bengala")
	FVector FlareLocation() const;
	void FlareTick(float DeltaSeconds);
	void EndFlare();
	UPROPERTY() TObjectPtr<class ASpotLight> FlareLight;
	UPROPERTY() TObjectPtr<class UStaticMeshComponent> FlareGlow;
	float FlareT = 0.0f;
	FVector FlareFrom = FVector::ZeroVector;
	FVector FlareTop = FVector::ZeroVector;

	// ---- tanda 43: interrogar, asomarse y el ultimo sitio donde te vieron (TarsisTactica.cpp)
	/** Interrogar (T) al guardia que tienes a mano por la espalda: suelta un dato y se queda quieto estos segundos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tactica")
	bool bInterrogation = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tactica")
	float InterrogateSeconds = 5.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Tactica")
	int32 Interrogations = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Tactica")
	int32 InterrogationFacts = 0;
	UPROPERTY() TSet<FString> Interrogated;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Tactica")
	void Interrogate();
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Tactica")
	bool CanInterrogate(const class ATarsisGuard* G) const;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Tactica")
	void ForgetInterrogations() { Interrogated.Reset(); }
	/** Asomarse (Z izquierda, V derecha, mantenidas): cuanto sale la camara de lado (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tactica")
	bool bLeanRule = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tactica")
	float LeanDist = 55.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Tactica")
	float LeanNow = 0.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Tactica")
	int32 Leans = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tactica")
	bool bLeanLeft = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tactica")
	bool bLeanRight = false;
	bool bLeanTaught = false;
	void LeanLeftOn() { bLeanLeft = true; }
	void LeanLeftOff() { bLeanLeft = false; }
	void LeanRightOn() { bLeanRight = true; }
	void LeanRightOff() { bLeanRight = false; }
	void LeanTick(float DeltaSeconds);
	/** Ultimo avistamiento: el que te pierde deja marcado el sitio y llama al companero libre mas cercano (a menos de PartnerDist). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tactica")
	bool bLastSeenRule = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tactica")
	float LastKnownSeconds = 14.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tactica")
	float PartnerDist = 3000.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Tactica")
	FVector LastKnown = FVector::ZeroVector;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Tactica")
	float LastKnownT = 0.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Tactica")
	int32 LastKnownMarks = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Tactica")
	int32 PartnerSearches = 0;
	float PartnerCoolT = 0.0f;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Tactica")
	void LostPlayer(class ATarsisGuard* G, const FVector& Where);
	/** Toda la base vuelve a su ronda y nadie queda en alerta (al encerrarte en el calabozo). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Tactica")
	void CalmBase();
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Tactica")
	int32 Calms = 0;
	void TacticsTick(float DeltaSeconds);

	// ---- tanda 47: las charlas salen cuando los dos se cruzan en sus rondas contigo cerca (idea de Andres), no en un
	// sitio fijo. Si en TalkCrossWait segundos contigo por la zona no se han cruzado, quedan en el sitio de siempre
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	bool bTalkCross = true;
	/** A menos de esto (cm) uno de otro, de ronda los dos, se paran a hablar. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkCrossDist = 900.0f;
	/** Y solo si tu estas a menos de esto (cm) de ellos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkNearDist = 1600.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkCrossWait = 75.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	int32 TalksCrossed = 0;
	/** Donde hablan ahora (el cruce, o el sitio fijo de la charla). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	FVector TalkSpotNow = FVector::ZeroVector;
	bool StartTalkAt(int32 Index, const FVector& Spot);
	/** Tanda 47 (idea de Andres): junto a la emisora de transmisiones, con la base tranquila y la red viva, se oyen las
	charlas como si estuvieras al lado, segun se van cruzando. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	bool bRadioTap = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float RadioTapDist = 320.0f;
	/** Junto a la emisora, si nadie se cruza en estos segundos, dos quedan a hablar en su sitio de siempre. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float RadioTapWait = 14.0f;
	/** Con los prismaticos, apuntando a los que hablan, se les oye hasta esta distancia (cm) y dentro de este angulo. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkScopeDist = 7000.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkScopeAngle = 7.0f;
	/** A menos de esto (cm) se ve un bocadillo sobre los que hablan. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkIconDist = 2500.0f;
	UPROPERTY(VisibleInstanceOnly, Category = "Tarsis")
	int32 TalkLinesHalf = 0;
	float TapHintT = 0.0f;
	UPROPERTY(VisibleInstanceOnly, Category = "Tarsis")
	int32 ScopeLinesHeard = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	int32 TapLinesHeard = 0;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Charlas")
	bool AtEmisora() const;
	float TalkCrossT = 0.0f;

	// ---- tanda 47: cuerpo de Cuttlas y tercera persona (TarsisTercera.cpp). La G alterna
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	bool bThirdRule = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	bool bThird = false;
	/** Donde va la camara respecto a la vista (cm: adelante, derecha, arriba). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	FVector ThirdOffset = FVector(-230.0f, 45.0f, 25.0f);
	/** Velocidad (cm/s) a la que las animaciones de andar y de ir agachado van a su ritmo. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	float HeroWalkSpeed = 280.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	float HeroSneakSpeed = 150.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Tercera")
	float ThirdAlpha = 0.0f;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Tercera")
	void ToggleThird();
	UFUNCTION(BlueprintPure, Category = "Tarsis|Tercera")
	bool ThirdNow() const;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Tercera")
	bool HeroReady() const { return HeroBody != nullptr; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Tercera")
	bool HeroShown() const { return bThirdShown; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Tercera")
	int32 HeroAnimIndex() const { return HeroAnimNow; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Tercera")
	FVector ThirdCamOffset() const { return ThirdAdded; }
	void SetupHero(class ACharacter* C);
	void ThirdTick(float DeltaSeconds);
	UPROPERTY()
	TObjectPtr<class USkeletalMeshComponent> HeroBody;
	UPROPERTY()
	TObjectPtr<class UAnimationAsset> HeroAnims[4];
	bool bHeroTried = false;
	bool bThirdShown = false;

	// ---- tanda A (TarsisGaspHero.cpp): Cuttlas con el ABP del Game Animation Sample. Si el peón del jugador implementa
	// BPI_SandboxCharacter_Pawn (BP_CuttlasGASP, copia de SandboxCharacter_CMC sobre BP_FirstPersonCharacter), HeroBody
	// copia la pose de un maniquí UEFN oculto que corre SandboxCharacter_CMC_ABP; si no, el HeroBody de siempre.
	/** Apagado, Cuttlas en tercera usa las animaciones sueltas de antes aunque el peón sea BP_CuttlasGASP. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	bool bHeroGaspRule = true;
	/** Gait del GASP según MaxWalkSpeed: por debajo, Walk; hasta HeroGaspSprintFrom, Run; por encima, Sprint. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	float HeroGaspRunFrom = 320.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	float HeroGaspSprintFrom = 650.0f;
	/** Giro extra del cuerpo respecto al maniquí que conduce (si la persona saliera torcida). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	float HeroGaspYaw = 0.0f;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Tercera")
	bool HeroUsesGasp() const { return HeroDriver != nullptr; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Tercera")
	FString HeroGait() const { return HeroGaitNow; }
	/** Giro en el sitio estando quieto (TarsisGaspTurn.h): con las piernas a HeroGaspTurnFrom grados o más de donde mira,
	 *  WantsToAim un momento para que el ABP gire en el sitio; se quita al quedar a HeroGaspTurnRelease, al andar o a los
	 *  HeroGaspTurnMaxSeconds. Por debajo de unos 115 grados el torso ya sigue a la cámara (aim offset del GASP). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	float HeroGaspTurnFrom = 95.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	float HeroGaspTurnRelease = 15.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	float HeroGaspTurnMaxSeconds = 1.5f;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Tercera")
	bool HeroGaspTurnAiming() const { return HeroGaspTurn.bAim; }
	/** Grados que las piernas van por detrás de hacia dónde mira el actor (del hueso raíz del maniquí que conduce). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Tercera")
	float HeroGaspTurnDelta() const { return HeroGaspTurn.Delta; }
	FTarsisGaspTurn HeroGaspTurn;
	/** Agacharse: la cápsula baja de golpe y la cámara bajaba CrouchCamDrop cm en un fotograma (un corte en tercera
	 *  persona). Ahora baja y sube con una curva suave en CrouchCamSeconds, como el cuerpo con el ABP del GASP. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	float CrouchCamDrop = 55.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Tercera")
	float CrouchCamSeconds = 0.3f;
	/** Lo que la cámara está bajada ahora por agacharse (cm, negativo). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Tercera")
	float CrouchCamOffset() const { return CrouchCamApplied; }
	float CrouchCamApplied = 0.0f;   // desplazamiento sumado a la cámara
	float CrouchCamAlpha = 0.0f;     // 0 de pie, 1 agachado (avanza a 1/CrouchCamSeconds por segundo)
	TWeakObjectPtr<class UCameraComponent> CrouchCam;
	bool bHeroGaspPawn = false;    // el peón implementa la interfaz del GASP (lo limpia SetupGaspPlayer)
	UPROPERTY()
	TObjectPtr<class USkeletalMeshComponent> HeroDriver;
	UPROPERTY()
	TObjectPtr<UObject> HeroRetargeter;
	UPROPERTY()
	TObjectPtr<class UInputMappingContext> HeroGaspImc;
	float HeroDriverBallZ = 0.0f;
	float HeroDriverYaw = 0.0f;
	float HeroBodyBallZ = 0.0f;
	float HeroBodyYawGasp = 0.0f;
	bool bHeroRetargetSet = false;
	FString HeroGaitNow;
	void SetupGaspPlayer(class ACharacter* C);
	bool SetupGaspHero(class ACharacter* C, class USkeletalMesh* SK);
	void GaspHeroTick(class ACharacter* C, bool bOut);
	float HeroYaw = 0.0f;
	float HeroFootZ = 0.0f;
	int32 HeroAnimNow = -1;
	FVector ThirdAdded = FVector::ZeroVector;
	FVector ThirdRelDelta = FVector::ZeroVector;

	// ---- tanda 47: apuntar (boton derecho mantenido): la vista se cierra, sale la mira y se pone roja sobre un guardia
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Apuntar")
	bool bAimRule = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Apuntar")
	float AimFov = 55.0f;
	/** Cuanto se mueven los brazos al apuntar (cm, en los ejes de ArmsOffset): la pistola hacia el centro. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Apuntar")
	FVector AimArmsShift = FVector::ZeroVector;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Apuntar")
	float AimAlpha = 0.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Apuntar")
	bool bAimHeld = false;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Apuntar")
	bool CanAim() const;
	/** El guardia que cruzaria ahora la linea de tiro (nullptr si ninguno). */
	UFUNCTION(BlueprintPure, Category = "Tarsis|Apuntar")
	class ATarsisGuard* DartAim() const;
	class ATarsisGuard* DartLine(const FVector& Loc, const FVector& Fwd, float& OutT) const;
	void AimOn() { bAimHeld = true; }
	void AimOff() { bAimHeld = false; }
	void AimTick(float DeltaSeconds);
	float AimBaseFov = 0.0f;

	// ---- tanda 46: el perro del hangar (TarsisPerro.cpp). No ve: huele. Grune de aviso, ladra y llama a los guardias;
	// con el hueso de la cocina se hace amigo
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	bool bDog = true;
	/** Las dos puntas de su ronda (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	FVector DogA = FVector(4350.0f, 6600.0f, 0.0f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	FVector DogB = FVector(5550.0f, 6600.0f, 0.0f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	float DogSpeed = 110.0f;
	/** Segundos sentado en cada punta. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	float DogRest = 7.0f;
	/** A menos de esto (cm) te huele, vayas como vayas. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	float DogSmell = 550.0f;
	/** A menos de esto (cm) te oye si corres; y hasta aqui sigue ladrando una vez que ha empezado. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	float DogHear = 1100.0f;
	/** Segundos de grunido antes de ladrar: el aviso. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	float DogGrowlSeconds = 3.5f;
	/** Los guardias a menos de esto (cm) oyen los ladridos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	float DogBarkRadius = 3000.0f;
	/** Desde aqui (cm) se le puede dar el hueso. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	float DogGiveDist = 480.0f;
	/** Giro de la malla respecto a su frente (grados) y escala: se ajustan al importar el modelo. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	float DogMeshYaw = 90.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Perro")
	float DogScale = 1.0f;
	/** 0 ronda, 1 grune, 2 ladra, 3 amigo. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Perro")
	int32 DogState = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Perro")
	int32 DogGrowls = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Perro")
	int32 DogBarks = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Perro")
	int32 DogCalls = 0;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Perro")
	bool DogReady() const { return DogMesh != nullptr; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Perro")
	FVector DogLocation() const { return DogLoc; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Perro")
	float DogFacing() const { return DogYaw; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Perro")
	int32 DogAnimIndex() const { return DogAnimNow; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Perro")
	int32 DogAnimCount() const { int32 N = 0; for (int32 i = 0; i < 4; ++i) if (DogAnims[i]) ++N; return N; }
	UFUNCTION(BlueprintPure, Category = "Tarsis|Perro")
	FString DogPrompt() const;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Perro")
	void GiveBone();
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Perro")
	void DogReset();
	bool DogInteract();
	void SpawnDog();
	void DogPlace();
	void DogAnim(int32 Which, bool bLoop);
	void DogFace(const FVector& To, float DeltaSeconds);
	void DogTick(float DeltaSeconds);
	UPROPERTY()
	TObjectPtr<class USkeletalMeshComponent> DogMesh;
	UPROPERTY()
	TObjectPtr<class UAnimationAsset> DogAnims[4];
	bool bDogTried = false;
	bool DogToB = true;
	FVector DogLoc = FVector::ZeroVector;
	float DogZ = 0.0f;
	float DogYaw = 0.0f;
	float DogSitT = 0.0f;
	float DogGrowlT = 0.0f;
	float DogCalmT = 0.0f;
	float DogBarkT = 0.0f;
	int32 DogBarkN = 0;
	int32 DogAnimNow = -1;
	FVector FlareDrift = FVector::ZeroVector;

	/** Dia (true) o noche. La mision 1 es de noche; la de los inspectores sera de dia. Se cambia en Pausa. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Dia")
	bool bDay = false;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Dia")
	void SetDay(bool bNewDay);
	/** Sol: lux (la luna da 0,8 con la exposicion fija del nivel), color, y cuanto baja (grados) sobre el horizonte. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	float DaySunLux = 8.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	FLinearColor DaySunColor = FLinearColor(1.0f, 0.95f, 0.86f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	float DaySunPitch = -48.0f;
	/** Boveda de dia (en la escala de la exposicion fija: valores pequenos). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	FLinearColor DayZenith = FLinearColor(0.18f, 0.30f, 0.55f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	FLinearColor DayHorizon = FLinearColor(0.40f, 0.44f, 0.50f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	FLinearColor DayCloud = FLinearColor(0.55f, 0.55f, 0.55f);
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	FLinearColor DayFogColor = FLinearColor(0.25f, 0.27f, 0.30f);
	/** Luz de sigilo de dia: a cielo abierto y bajo techo (de noche el fondo es 0,12). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	float DayAmbientOpen = 0.9f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	float DayAmbientRoofed = 0.4f;
	/** De dia las farolas, focos y apliques de fuera se apagan (las de dentro siguen). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	bool bDayLampsOff = true;
	/** Tanda 47: de dia los guardias de a pie ven esto mas lejos, y los de torre (sin foco) esto otro. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	float DayViewMul = 1.4f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Dia")
	float DayTowerViewMul = 3.0f;
	UPROPERTY() TObjectPtr<class UMaterialInterface> NightSkyMat;
	UPROPERTY() TArray<TObjectPtr<class ALight>> DayOffLights;
	float BaseMoonLux = -1.0f;
	FLinearColor BaseMoonColor = FLinearColor::White;
	FRotator BaseMoonRot = FRotator::ZeroRotator;

	/** Brillo (Pausa): pasos de un cuarto de diafragma sobre la exposicion fija del nivel, de -4 a +8. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Menu")
	int32 OptBrightness = 0;
	void ApplyBrightness();
	float BaseExposure = -1000.0f;
	/** Intensidad de tu linterna (Pausa): multiplica TorchLumens, de 0,3 a 3. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Menu")
	float OptTorchMul = 0.3f;   // Andres (2026-11-18): se queda con la linterna al minimo (90 lm)

	// ---- tanda 41: charlas que se oyen de cerca y mapa mental (TarsisCharlas.cpp)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	bool bTalkRule = true;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	TArray<FTarsisTalk> Talks;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	TArray<FTarsisFact> Facts;
	/** A menos de esto (cm) del sitio se oye cada frase; hasta TalkSeeDist, solo un murmullo. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkHearDist = 450.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkSeeDist = 1800.0f;
	/** Una charla solo empieza contigo a menos de esto de su sitio: no se gasta mientras estas en la otra punta. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkStartDist = 3000.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkLineSeconds = 4.0f;
	/** Segundos que tienen para juntarse, y pausa hasta la charla siguiente (o hasta repetir la que se corto). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkGather = 60.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkRetry = 45.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	float TalkWait = 20.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	int32 TalkIdx = -1;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	int32 TalkPhase = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	int32 TalkLine = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	int32 TalksStarted = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	int32 TalksEnded = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	int32 TalkCuts = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	int32 TalkLinesHeard = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	int32 FactsLearned = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Charlas")
	FName LastFact;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Charlas")
	bool bMindMap = false;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Charlas")
	bool StartTalk(int32 Index);
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Charlas")
	bool FactKnown(FName Id) const;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Charlas")
	int32 FactsKnown() const;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Charlas")
	bool LearnFact(FName Id);
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Charlas")
	void ToggleMindMap();
	bool TalkPending(int32 Index) const;
	void EndTalk(bool bCut);
	void TalkTick(float DeltaSeconds);
	UPROPERTY()
	TObjectPtr<class ATarsisGuard> TalkA;
	UPROPERTY()
	TObjectPtr<class ATarsisGuard> TalkB;
	float TalkT = 0.0f;
	float TalkLineWait = 4.0f;   // lo que dura la frase que se esta diciendo (tanda 42)
	int32 TalkNext = 0;
	bool bTalkHeardAny = false;
	bool bTalkMurmur = false;
	/** Tanda 47: charla por la red, oida desde la emisora: cada uno habla desde donde esta, sin dejar la ronda. */
	bool bTalkRadio = false;
	bool StartTalkRadio(int32 Index);
	// ---- tanda 40: la caja de carton (X) y el uniforme (TarsisCaja.cpp)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Caja")
	bool bBoxOn = false;
	/** Por debajo de esta velocidad (cm/s) la caja cuenta como quieta; y los segundos quieto hasta que deja de verse. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Caja")
	float BoxStillSpeed = 20.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Caja")
	float BoxSettle = 0.5f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Caja")
	int32 BoxUses = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Caja")
	bool bBoxSeen = false;
	/** Con uniforme, de pie y andando: mas lejos de esto (cm) los guardias te toman por uno de los suyos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Caja")
	float UniformDist = 900.0f;
	/** Un guardia que tiene la caja delante a menos de esto (cm) la mira dos veces: de cerca no engana. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Caja")
	float BoxNoticeDist = 150.0f;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Caja")
	void ToggleBox();
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Caja")
	bool BoxCloaked() const;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Caja")
	bool UniformWorks() const;
	bool BoxBlocks();
	void BoxTick(float DeltaSeconds);
	float BoxStillT = 0.0f;
	float BoxNagT = 0.0f;
	bool bUniformNow = false;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Equipo")
	FString GearPrompt() const;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Equipo")
	bool GearInteract();
	void GearNag();
	void GearTick(float DeltaSeconds);
	float GearT = 0.0f;
	float GearNoiseT = 0.0f;
	float GearNagT = 0.0f;
	bool bGearHadTorch = true;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Calabozo")
	void AnswerCell(int32 Option);
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Calabozo")
	void LockInCell(APawn* Player);
	/** Errores seguidos en el teclado del archivo que avisan a la central (0: nunca). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Mision")
	int32 KeypadMaxFails = 2;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	int32 KeypadFails = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Mision")
	int32 KeypadAlerts = 0;

	// ---- tanda 37 (TarsisCombat.cpp): guardias armados. Te apuntan y dan el alto; quieto te detienen, si huyes disparan
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	bool bArmedRule = true;
	/** Segundos de margen tras el alto antes de que moverse cuente como huir. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float HaltGrace = 1.5f;
	/** Segundos quieto para que uno se acerque a detenerte. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float SurrenderSeconds = 2.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float ShotInterval = 1.6f;
	/** Multiplica la punteria (1 normal; las pruebas la suben para no depender del azar, o la ponen a 0). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float ArmedAim = 1.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	int32 MaxWounds = 3;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float WoundHealSeconds = 45.0f;
	/** Segundos desde el alto hasta que llegan los refuerzos pedidos por radio, y cuantos. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float BackupDelay = 5.0f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	int32 BackupCount = 2;
	/** A que distancia se oye un disparo (cm). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float ShotHeard = 4000.0f;
	/** Para las pruebas: velocidad del jugador que se da por buena (menor que 0: la real). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float PlayerSpeedOverride = -1.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	bool bHalt = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	bool bFleeing = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	int32 Wounds = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	int32 Halts = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	int32 Surrenders = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	int32 Shots = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	int32 Hits = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	int32 ArmedBackups = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	int32 ArmedCovers = 0;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	TObjectPtr<class ATarsisGuard> ArrestGuard;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	TObjectPtr<class ATarsisGuard> Aimer;
	void ReportAim(class ATarsisGuard* G, float Dist);
	void ShotFired(class ATarsisGuard* G, bool bHit);
	void ArmedTick(float DeltaSeconds);
	float HitFlashT = 0.0f;
	float ShotFlashT = 0.0f;
	FVector ShotFlashAt = FVector::ZeroVector;
	UPROPERTY() TObjectPtr<class UPointLightComponent> ShotLight;
	/** Lumenes del fogonazo del disparo de un guardia (dura ShotFlashT). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Armado")
	float ShotFlashLm = 2500.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Armado")
	int32 ShotFlashes = 0;
	float AimHoldT = 0.0f;
	float AimerDist = 0.0f;
	float HaltT = 0.0f;
	float StillT = 0.0f;
	float UnaimedT = 0.0f;
	float BackupT = 0.0f;
	bool bBackupSent = false;
	float WoundT = 0.0f;

	// ---- tanda 37: escaleras de las torres. Pie y plataforma de cada una (cm; los pone tools/unreal/guardias.py)
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torres")
	TArray<FVector> Ladders;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torres")
	TArray<FVector> LadderTops;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tarsis|Torres")
	float ClimbSeconds = 4.0f;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Torres")
	bool bClimbing = false;
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis|Torres")
	int32 Climbs = 0;
	UFUNCTION(BlueprintPure, Category = "Tarsis|Torres")
	FString LadderPrompt() const;
	UFUNCTION(BlueprintCallable, Category = "Tarsis|Torres")
	bool LadderInteract();
	int32 LadderNear(bool& bTop) const;
	void ClimbTick(float DeltaSeconds);
	bool bClimbUp = true;
	float ClimbT = 0.0f;
	FVector ClimbBase = FVector::ZeroVector;
	FVector ClimbTop = FVector::ZeroVector;

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
	static constexpr int32 NumActions = 13;   // tanda 43: caja, mapa, interrogar y asomarse tambien se ven y se cambian en CONTROLES
	FKey ActionKeys[NumActions];
	/** Nombre de la tecla de una accion, en mayusculas y sin tildes (ToUpper dejaba «MAYuS» con la u minuscula). */
	FString KeyLabel(int32 I) const;
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
	void CellAsk();
	void OpenCellWith(bool bKeyUsed);
	void CellTick(float DeltaSeconds);
	void CellReset();
	bool bCellMedal = false;
	float CellPrayT = 0.0f;
	float CellCallT = 0.0f;
	float CellNextT = 0.0f;
	int32 CellOkMask = 0;
	int32 CellLackMask = 0;
	float CellOpenT = 0.0f;
	UPROPERTY()
	TObjectPtr<class UStaticMeshComponent> SlabProp;
	void SpawnVidal();
	void FaceVidal(float Yaw);
	float VidalFace = 0.0f;
	float VidalMeshYaw = 0.0f;
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
	void RadioChatTick();
	void EmisoraTick(float DeltaSeconds);
	bool bRadioChatOn = false;
	bool bEmisoraNoticed = false;
	float EmisoraFixT = 0.0f;
	float EmisoraSendT = 0.0f;
	TWeakObjectPtr<class ATarsisGuard> EmisoraFixer;
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
