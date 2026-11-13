// Lost Horizon: De Profundis — guardado de Tarsis: el último punto de control de la misión y las opciones del menú.
// Dos huecos: "TarsisPartida" (se escribe en cada punto de control) y "TarsisOpciones" (al cambiar una opción).
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "TarsisSave.generated.h"

UCLASS()
class UTarsisSave : public USaveGame
{
	GENERATED_BODY()

public:
	// ---- partida (punto de control)
	UPROPERTY() FString Checkpoint;
	UPROPERTY() FVector Loc = FVector::ZeroVector;
	UPROPERTY() FRotator Rot = FRotator::ZeroRotator;
	UPROPERTY() float MissionTime = 0.0f;
	UPROPERTY() int32 Captures = 0;
	UPROPERTY() int32 Darts = 0;
	UPROPERTY() bool bKey = false;
	UPROPERTY() bool bJefOpen = false;
	UPROPERTY() bool bNoteRead = false;
	UPROPERTY() bool bVaultOpen = false;
	UPROPERTY() bool bFile = false;
	UPROPERTY() bool bLetter = false;
	UPROPERTY() bool bVetKey = false;
	UPROPERTY() bool bVetOpen = false;
	UPROPERTY() bool bRamosKnown = false;
	UPROPERTY() bool bLampBroken = false;
	UPROPERTY() int32 Weather = 0;

	// ---- opciones
	UPROPERTY() float Sensitivity = 1.0f;
	UPROPERTY() bool bInvertY = false;
	UPROPERTY() float Volume = 1.0f;
	UPROPERTY() int32 Quality = -1;   // -1: la que tenga el motor
	UPROPERTY() bool bShowFps = false;
};
