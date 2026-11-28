// Lost Horizon: De Profundis - tanda T: bloqueo de pies propio (Cuttlas y el guardia del duelo).
//
// Clava en el mundo el pie que la animacion da por apoyado (cerca del suelo y casi quieto respecto a la malla) mientras
// la capsula se desplaza (root motion, empujon, acercamiento), y lo suelta fundiendo cuando el pie se levanta en la
// animacion o se aleja demasiado de donde lo pone la animacion. IK de dos huesos (muslo, pantorrilla, pie) a mano, sobre
// la malla que se ve (UPoseableMeshComponent): no toca el ABP del GASP ni el tiempo global.
// Enfoques comparados (docs/combate-tanda-t.md): nodo Two Bone IK en un ABP de postproceso o un Control Rig de bloqueo de
// pies (los dos piden crear y editar grafos de animacion a mano en el editor) frente a esto, que reutiliza el patron de
// la malla visible copiada que ya llevan los guardias (y el IK de brazos del fusil). Sin codigo externo.
#pragma once

#include "CoreMinimal.h"

class UPoseableMeshComponent;

struct FTarsisFootLock
{
	bool bLocked = false;
	bool bHasPrev = false;
	FVector LockW = FVector::ZeroVector;   // donde se clavo el pie (mundo)
	FVector PrevCS = FVector::ZeroVector;  // el pie en espacio de la malla, el fotograma de antes (velocidad de la animacion)
	float Alpha = 0.0f;                    // cuanto manda el bloqueo (0 la animacion, 1 el sitio clavado)
	float Drift = 0.0f;                    // lo que se desliza el pie en el mundo mientras esta clavado (cm), para medir
	FVector ReleaseFrom = FVector::ZeroVector;
};

struct FTarsisFootLockSettings
{
	float PlantHeight = 18.0f;     // el pie (tobillo) a menos de esto sobre el suelo
	float PlantSpeed = 45.0f;      // para clavarlo, moviendose menos que esto respecto a la malla (cm/s); clavado, solo cuenta la altura
	float ReleaseDistance = 18.0f; // se suelta si la animacion lo lleva mas lejos que esto de donde esta clavado
	float StepLift = 7.0f;         // al soltarlo, el pie va a su sitio nuevo levantandose esto (un paso, no un deslizamiento)
	float BlendIn = 0.08f;         // s
	float BlendOut = 0.15f;        // s
};

/** Aplica el bloqueo a los dos pies de P. GroundZ: el suelo bajo la capsula (mundo). Locks[0] izquierdo, [1] derecho.
 *  bActive false: suelta fundiendo (y no clava nada nuevo). */
void TarsisFootLockApply(UPoseableMeshComponent* P, FTarsisFootLock (&Locks)[2], float DeltaSeconds, float GroundZ, bool bActive,
	const FTarsisFootLockSettings& S = FTarsisFootLockSettings());
