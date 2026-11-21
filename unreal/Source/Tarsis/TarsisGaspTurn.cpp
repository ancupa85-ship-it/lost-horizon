// Giro en el sitio del GASP estando quieto: ver TarsisGaspTurn.h. Textos solo en ASCII.
#include "TarsisGaspTurn.h"

#include "Animation/AnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Actor.h"
#include "UObject/UnrealType.h"

bool FTarsisGaspTurn::ReadDelta(const USkeletalMeshComponent* Driver, float& OutDelta)
{
	// el ABP guarda el desfase en el hueso raiz (Offset Root Bone en modo Accumulate): parado, el actor gira y la raiz se
	// queda; su giro en espacio de la malla es lo que las piernas van por detras del actor (en reposo la raiz es la identidad)
	if (!Driver || !Driver->GetSkeletalMeshAsset() || Driver->GetBoneIndex(TEXT("root")) == INDEX_NONE) return false;
	OutDelta = FRotator::NormalizeAxis(-Driver->GetSocketTransform(TEXT("root"), RTS_Component).Rotator().Yaw);
	return true;
}

bool FTarsisGaspTurn::SetWantsToAim(AActor* Pawn, bool bValue)
{
	if (!Pawn) return false;
	const FStructProperty* SP = CastField<FStructProperty>(Pawn->GetClass()->FindPropertyByName(TEXT("CharacterInputState")));
	if (!SP || !SP->Struct) return false;
	void* Data = SP->ContainerPtrToValuePtr<void>(Pawn);
	// S_PlayerInputState es una estructura de Blueprint: sus campos llevan el GUID en el nombre (WantsToAim_7_...)
	for (TFieldIterator<FBoolProperty> It(SP->Struct); It; ++It)
	{
		if (It->GetName().StartsWith(TEXT("WantsToAim")))
		{
			It->SetPropertyValue_InContainer(Data, bValue);
			return true;
		}
	}
	return false;
}

void FTarsisGaspTurn::Tick(AActor* Pawn, USkeletalMeshComponent* Driver, float Speed2D, float DeltaSeconds, float From, float Release, float MaxSeconds)
{
	if (!ReadDelta(Driver, Delta)) { Stop(Pawn); return; }
	const bool bStill = Speed2D < 10.0f;
	if (!bAim)
	{
		if (bStill && FMath::Abs(Delta) >= From && SetWantsToAim(Pawn, true))
		{
			bAim = true;
			Seconds = 0.0f;
		}
		return;
	}
	Seconds += DeltaSeconds;
	if (!bStill || FMath::Abs(Delta) <= Release || Seconds >= MaxSeconds) Stop(Pawn);
}

void FTarsisGaspTurn::Stop(AActor* Pawn)
{
	if (!bAim) return;
	SetWantsToAim(Pawn, false);
	bAim = false;
	Seconds = 0.0f;
}
