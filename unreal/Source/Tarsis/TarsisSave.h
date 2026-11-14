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

	// ---- parte del día siguiente (hueco "TarsisParte"): lo que la misión 2 encuentra en la base
	UPROPERTY() bool bByMarsh = false;
	UPROPERTY() int32 Detections = 0;
	UPROPERTY() int32 Takedowns = 0;
	UPROPERTY() bool bPowerCut = false;
	UPROPERTY() bool bReserveHalf = false;
	UPROPERTY() bool bRamosAlly = false;
	UPROPERTY() bool bRamosDowned = false;
	UPROPERTY() int32 Score = 0;
	UPROPERTY() FString Rank;
	UPROPERTY() TArray<FString> Downed;
	UPROPERTY() TArray<FString> Report;

	// ---- opciones
	UPROPERTY() float Sensitivity = 1.0f;
	UPROPERTY() bool bInvertY = false;
	UPROPERTY() float Volume = 1.0f;
	UPROPERTY() int32 Quality = -1;   // -1: la que tenga el motor
	UPROPERTY() bool bShowFps = false;
	UPROPERTY() float Music = 0.7f;
	UPROPERTY() bool bShowHelp = true;
	UPROPERTY() float TextScale = 1.0f;
	UPROPERTY() bool bColorblind = false;
	UPROPERTY() bool bSubtitles = false;
	UPROPERTY() int32 Difficulty = 1;
	UPROPERTY() TArray<FName> Keys;    // teclas de las acciones, en el orden de ATarsisDirector::ActionName
	UPROPERTY() TArray<FName> Flags;   // banderas de la misión (ATarsisDirector::SetFlag)
};
