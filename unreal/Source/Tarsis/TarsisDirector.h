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

	/** Guardia caído que vas arrastrando (o nullptr). */
	UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category = "Tarsis")
	TObjectPtr<class ATarsisGuard> Dragged;

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
	TArray<TObjectPtr<class USoundBase>> StepGravel;
	UPROPERTY()
	TArray<TObjectPtr<class USoundBase>> StepConcrete;
	UPROPERTY()
	TObjectPtr<class USoundBase> StoneSnd;
	UPROPERTY()
	TObjectPtr<class USoundBase> DartSnd;
	UPROPERTY()
	TObjectPtr<class USoundBase> WindSnd;
	UPROPERTY()
	TObjectPtr<class USoundBase> RainSnd;
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
	void StepSound(const FVector& Where, bool bIndoorStep, float Volume, bool b3D);
	bool IndoorAt(const FVector& P, const AActor* Ignore) const;
	void SoundTick(class ACharacter* C, float DeltaSeconds);
	void RainTick(float DeltaSeconds);
	bool bRamosSent = false;
};
