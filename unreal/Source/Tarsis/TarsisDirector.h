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
};
