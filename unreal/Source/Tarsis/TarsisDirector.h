// Director del sigilo en el nivel Tarsis: indicador de luz, agacharse con C y avisos de alerta.
// Va un ejemplar en el nivel (lo coloca tools/unreal/guardias.py). Provisional: los avisos usan los mensajes en pantalla del motor;
// el HUD definitivo irá con UMG.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
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

protected:
	virtual void BeginPlay() override;

private:
	float LightT = 0.0f;
	bool bWasAlert = false;
	void ToggleCrouch();
	void SetupPlayer();
	bool bPlayerReady = false;
};
