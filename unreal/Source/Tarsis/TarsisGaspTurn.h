// Tanda A (2026-11-21): giro en el sitio del GASP estando quieto, para los guardias y para Cuttlas.
//
// SandboxCharacter_CMC_ABP solo gira en el sitio (ShouldTurnInPlace) si la diferencia entre lo que se quiere mirar y la
// raiz (el desfase que guarda en el hueso raiz) llega a 50 grados Y ademas el personaje quiere
// apuntar (CharacterInputState.WantsToAim) o acaba de pararse. Sin apuntar, parado, las piernas se quedan donde estaban
// hasta el primer paso: el guardia que se vuelve hacia un ruido o Cuttlas al girar la camara. El umbral de 50 es un
// literal en el grafo, sin variable expuesta, y WantsToAim no cambia la pose (las tablas de chooser no lo miran; en el
// peon solo lo leen la camara del GASP y UpdateRotation_PreCMC, que aqui estan apagados): es el gatillo mas limpio.
// Aqui se pone WantsToAim un momento cuando la diferencia pasa de From grados, y se quita al alinearse (Release), al
// echar a andar o a los MaxSeconds.
#pragma once

#include "CoreMinimal.h"

class AActor;
class USkeletalMeshComponent;

struct FTarsisGaspTurn
{
	bool bAim = false;        // WantsToAim puesto por el giro
	float Seconds = 0.0f;     // desde que se puso
	float Delta = 0.0f;       // ultimo desfase de las piernas frente al actor (grados, del hueso raiz del que conduce)

	/** Pawn: el que implementa BPI_SandboxCharacter_Pawn (tiene CharacterInputState). Driver: la malla con el ABP del GASP. */
	void Tick(AActor* Pawn, USkeletalMeshComponent* Driver, float Speed2D, float DeltaSeconds, float From, float Release, float MaxSeconds);
	/** Quita el WantsToAim si lo habia puesto el giro. */
	void Stop(AActor* Pawn);

	static bool ReadDelta(const USkeletalMeshComponent* Driver, float& OutDelta);
	static bool SetWantsToAim(AActor* Pawn, bool bValue);
};
