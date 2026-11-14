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

	/** Base en guardia tras una alarma (segundos que quedan): la sospecha sube un 50 % más deprisa. */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
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

	// misión secundaria de Ramos: carta en su litera, agarrarlo por la espalda (1 te lo llevas, 2 lo derribas),
	// llave del botiquín del veterinario con la pistola de dardos, y salida alternativa por el portillo de la marisma

	/** Línea «SECUNDARIA» del HUD (vacía si no hay). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	FString SideObjective() const;

	/** Clic izquierdo: dispara un dardo al guardia que tienes en el centro (lo duerme sin ruido). */
	UFUNCTION(BlueprintCallable, Category = "Tarsis")
	void ShootDart();

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
	static constexpr int32 NumActions = 6;
	FKey ActionKeys[NumActions];
	static const TCHAR* ActionName(int32 I);

	/** Tira de ayuda de abajo a la derecha: teclas de lo que puedes hacer ahora. */
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
	void RadioTick(float DeltaSeconds);
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
	float BarrierT = 0.0f;
	UPROPERTY()
	TObjectPtr<class ASpotLight> GateLamp;
	bool bLampBroken = false;
	bool bLampReported = false;
	UPROPERTY()
	TObjectPtr<class ATarsisGuard> LampChecker;
	float RepairCallT = 0.0f;
	bool bRepairerSilent = false;
	bool ShootLamp(const FVector& From, const FVector& Fwd, float MaxT);
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
