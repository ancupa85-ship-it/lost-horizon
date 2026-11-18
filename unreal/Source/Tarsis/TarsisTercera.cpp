// Lost Horizon: De Profundis - tanda 47: el cuerpo de Cuttlas y la camara en tercera persona.
// La G alterna entre la vista de siempre (primera persona, solo los brazos) y una camara detras del hombro derecho.
// En tercera se ve el cuerpo de Cuttlas (el modelo del juego web, importado por tools/unreal/personas.py) andando,
// quieto o agachado; los brazos de primera persona se esconden. La camara no atraviesa paredes: se acerca. Dentro de la
// caja, con los prismaticos, escondido, en el camion o en una cinematica la vista vuelve sola a primera persona.
// Los guardias miran al cuerpo, no a la camara: desde atras ves por encima de una caja sin que te vean.
#include "TarsisDirector.h"

#include "Animation/AnimationAsset.h"
#include "AssetRegistry/AssetData.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

namespace
{
	FVector TerceraRefBone(const USkeletalMesh* Mesh, FName Bone)
	{
		const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
		int32 I = Ref.FindBoneIndex(Bone);
		if (I == INDEX_NONE) return FVector::ZeroVector;
		FTransform T = FTransform::Identity;
		while (I != INDEX_NONE)
		{
			T = T * Ref.GetRefBonePose()[I];
			I = Ref.GetParentIndex(I);
		}
		return T.GetLocation();
	}
}

void ATarsisDirector::SetupHero(ACharacter* C)
{
	bHeroTried = true;
	if (!C) return;
	TArray<FAssetData> List;
	IAssetRegistry::GetChecked().GetAssetsByPath(FName(TEXT("/Game/Tarsis/Personas")), List, true);
	USkeletalMesh* SK = nullptr;
	static const TCHAR* Names[4] = { TEXT("idle"), TEXT("walk"), TEXT("sneak"), TEXT("stand") };
	for (const FAssetData& A : List)
	{
		if (!A.PackagePath.ToString().ToLower().Contains(TEXT("cuttlas"))) continue;
		const FString Cls = A.AssetClassPath.GetAssetName().ToString();
		const FString Nm = A.AssetName.ToString().ToLower();
		if (Cls == TEXT("SkeletalMesh")) { if (!SK) SK = Cast<USkeletalMesh>(A.GetAsset()); }
		else if (Cls == TEXT("AnimSequence"))
		{
			for (int32 i = 0; i < 4; ++i)
			{
				if (!HeroAnims[i] && Nm.EndsWith(Names[i])) HeroAnims[i] = Cast<UAnimationAsset>(A.GetAsset());
			}
		}
	}
	if (!SK)
	{
		UE_LOG(LogTemp, Warning, TEXT("Tarsis: no hay cuerpo de Cuttlas en /Game/Tarsis/Personas (tools/unreal/personas.py)"));
		return;
	}
	HeroBody = NewObject<USkeletalMeshComponent>(C, TEXT("CuerpoCuttlas"));
	HeroBody->SetSkeletalMesh(SK);
	HeroBody->SetupAttachment(C->GetCapsuleComponent());
	HeroBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	HeroBody->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	HeroBody->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPose;
	HeroBody->SetOwnerNoSee(false);
	HeroBody->RegisterComponent();
	// como los guardias: hacia delante = del tobillo a la punta del pie; el suelo, la punta del pie
	const FVector Foot = TerceraRefBone(SK, TEXT("foot_l")), Ball = TerceraRefBone(SK, TEXT("ball_l"));
	const FVector FootR = TerceraRefBone(SK, TEXT("foot_r")), BallR = TerceraRefBone(SK, TEXT("ball_r"));
	FVector Fwd = (Ball - Foot) + (BallR - FootR);
	Fwd.Z = 0.0f;
	HeroYaw = Fwd.IsNearlyZero() ? 0.0f : -FMath::RadiansToDegrees(FMath::Atan2(Fwd.Y, Fwd.X));
	HeroFootZ = FMath::Min(Ball.Z, BallR.Z);
	HeroBody->SetVisibility(false);
	HeroAnimNow = -1;
}

void ATarsisDirector::ToggleThird()
{
	if (!bThirdRule || bMenu || bCodec || bKeypad || bCine || bDone) return;
	bThird = !bThird;
	Teach(TEXT("ensena_tercera"), TEXT("TERCERA PERSONA\nLa camara va detras del hombro: ves por encima de las cajas sin asomarte. Los guardias te ven igual que antes.\nG vuelve a la vista de siempre."), {}, 6.0f);
}

bool ATarsisDirector::ThirdNow() const
{
	return bThirdRule && bThird && !bBinoculars && !bBoxOn && !bHiding && !bRiding && !bCine && !bCapturing && !bClimbing;
}

void ATarsisDirector::ThirdTick(float DeltaSeconds)
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	UCameraComponent* Cam = C ? C->FindComponentByClass<UCameraComponent>() : nullptr;
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!C || !Cam || !PC) return;
	if (!HeroBody && !bHeroTried) SetupHero(C);
	const bool bWant = ThirdNow();
	ThirdAlpha = FMath::FInterpConstantTo(ThirdAlpha, bWant ? 1.0f : 0.0f, DeltaSeconds, 5.0f);
	const bool bOut = ThirdAlpha > 0.02f;
	// la camara: se quita lo que se le sumo el fotograma anterior y se le suma lo de este (asomarse va aparte, con su paso)
	// (en relativo al padre de la camara, que gira con la cabeza: en mundo el resto se iria acumulando al girar)
	if (!ThirdRelDelta.IsZero()) { Cam->SetRelativeLocation(Cam->GetRelativeLocation() - ThirdRelDelta); ThirdRelDelta = FVector::ZeroVector; }
	ThirdAdded = FVector::ZeroVector;
	if (bOut)
	{
		const FRotator R = PC->GetControlRotation();
		const FVector Base = Cam->GetComponentLocation();
		const FVector Want = Base + R.RotateVector(ThirdOffset) * ThirdAlpha;
		FHitResult Hit;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisTercera), false, C);
		FVector To = Want;
		if (GetWorld()->SweepSingleByChannel(Hit, Base, Want, FQuat::Identity, ECC_Camera, FCollisionShape::MakeSphere(14.0f), Q) && !Hit.bStartPenetrating) To = Hit.Location;
		ThirdAdded = To - Base;
		const FVector Rel0 = Cam->GetRelativeLocation();
		Cam->AddWorldOffset(ThirdAdded);
		ThirdRelDelta = Cam->GetRelativeLocation() - Rel0;
	}
	// brazos de primera persona fuera, cuerpo dentro
	if (bOut != bThirdShown)
	{
		bThirdShown = bOut;
		if (Arms) Arms->SetVisibility(!bOut, true);
		if (HeroBody) HeroBody->SetVisibility(bOut);
	}
	if (!HeroBody || !bOut) return;
	const float HalfH = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	HeroBody->SetRelativeLocationAndRotation(FVector(0.0f, 0.0f, -HalfH - HeroFootZ + 2.0f), FRotator(0.0f, HeroYaw, 0.0f));
	const float Speed = C->GetVelocity().Size2D();
	const bool bLow = C->bIsCrouched;
	// 0 quieto, 1 andar, 2 agachado (andando o parado, con la animacion detenida)
	const int32 Anim = bLow ? 2 : (Speed > 20.0f ? 1 : 0);
	if (Anim != HeroAnimNow)
	{
		HeroAnimNow = Anim;
		UAnimationAsset* A = HeroAnims[Anim] ? HeroAnims[Anim].Get() : HeroAnims[0].Get();
		if (A) HeroBody->PlayAnimation(A, true);
	}
	const float Ref = bLow ? HeroSneakSpeed : HeroWalkSpeed;
	HeroBody->SetPlayRate(Anim == 0 ? 1.0f : (Speed > 20.0f ? FMath::Clamp(Speed / FMath::Max(Ref, 1.0f), 0.4f, 2.2f) : 0.0f));
}
