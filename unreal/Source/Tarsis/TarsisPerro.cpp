// Lost Horizon: De Profundis - tanda 46: el perro del hangar.
// Un pastor ronda el hangar de lado a lado y se sienta un rato en cada punta. No ve: huele. Si te acercas (da igual la
// sombra, ir agachado o la caja de carton) se planta y grune unos segundos: es el aviso. Si no te apartas, ladra, y los
// guardias mas cercanos vienen a ver que le pasa. Con el hueso de la olla de la cocina se le puede callar para siempre:
// se sienta, y desde entonces es amigo.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Animation/AnimationAsset.h"
#include "AssetRegistry/AssetData.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

void ATarsisDirector::SpawnDog()
{
	bDogTried = true;
	// lo importa tools/unreal/perro.py en /Game/Tarsis/Perro: una malla con esqueleto y cuatro animaciones
	TArray<FAssetData> List;
	IAssetRegistry::GetChecked().GetAssetsByPath(FName(TEXT("/Game/Tarsis/Perro")), List, true);
	USkeletalMesh* SK = nullptr;
	static const TCHAR* Names[4] = { TEXT("quieto"), TEXT("andar"), TEXT("sentarse"), TEXT("sentado") };
	for (const FAssetData& A : List)
	{
		const FString Cls = A.AssetClassPath.GetAssetName().ToString();
		const FString Nm = A.AssetName.ToString().ToLower();
		if (Cls == TEXT("SkeletalMesh")) { if (!SK) SK = Cast<USkeletalMesh>(A.GetAsset()); }
		else if (Cls == TEXT("AnimSequence"))
		{
			for (int32 i = 0; i < 4; ++i)
			{
				if (!DogAnims[i] && Nm.EndsWith(Names[i])) DogAnims[i] = Cast<UAnimationAsset>(A.GetAsset());
			}
		}
	}
	if (!SK)
	{
		UE_LOG(LogTemp, Warning, TEXT("Tarsis: no hay perro (ejecuta tools/unreal/perro.py en el editor)"));
		return;
	}
	DogMesh = NewObject<USkeletalMeshComponent>(this);
	DogMesh->SetSkeletalMesh(SK);
	DogMesh->SetMobility(EComponentMobility::Movable);
	DogMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	DogMesh->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	DogMesh->SetWorldScale3D(FVector(DogScale));
	DogMesh->RegisterComponent();
	// el suelo del hangar, medido una vez
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisPerro), false, this);
	DogZ = DogA.Z;
	if (GetWorld()->LineTraceSingleByChannel(Hit, DogA + FVector(0.0f, 0.0f, 250.0f), DogA - FVector(0.0f, 0.0f, 300.0f), ECC_Visibility, Q)) DogZ = Hit.ImpactPoint.Z;
	DogLoc = FVector(DogA.X, DogA.Y, DogZ);
	DogYaw = (DogB - DogA).Rotation().Yaw;
	DogToB = true;
	DogState = HasFlag(FName(TEXT("perro_amigo"))) ? 3 : 0;
	DogAnimNow = -1;
	DogPlace();
}

void ATarsisDirector::DogPlace()
{
	if (!DogMesh) return;
	DogMesh->SetWorldLocationAndRotation(DogLoc, FRotator(0.0f, DogYaw + DogMeshYaw, 0.0f));
}

void ATarsisDirector::DogAnim(int32 Which, bool bLoop)
{
	if (!DogMesh || DogAnimNow == Which) return;
	DogAnimNow = Which;
	if (Which >= 0 && Which < 4 && DogAnims[Which]) DogMesh->PlayAnimation(DogAnims[Which], bLoop);
}

void ATarsisDirector::DogFace(const FVector& To, float DeltaSeconds)
{
	const FVector D = To - DogLoc;
	if (D.SizeSquared2D() < 25.0f) return;
	const float Want = D.Rotation().Yaw;
	DogYaw = FMath::FixedTurn(DogYaw, Want, 240.0f * DeltaSeconds);
}

void ATarsisDirector::DogReset()
{
	if (DogState == 1 || DogState == 2) DogState = 0;
	DogGrowlT = DogCalmT = DogBarkT = 0.0f;
}

FString ATarsisDirector::DogPrompt() const
{
	if (!bDog || !DogMesh || DogState == 3 || !HasFlag(FName(TEXT("hueso")))) return FString();
	if (!NearPlayer(DogLoc, DogGiveDist)) return FString();
	return Tx(TEXT("p_perro_hueso"), TEXT("E   DARLE EL HUESO AL PERRO"));
}

bool ATarsisDirector::DogInteract()
{
	if (DogPrompt().IsEmpty()) return false;
	GiveBone();
	return true;
}

void ATarsisDirector::GiveBone()
{
	if (!DogMesh || DogState == 3) return;
	Flags.Remove(FName(TEXT("hueso")));
	SetFlag(FName(TEXT("perro_amigo")));
	DogState = 3;
	DogSitT = 0.0f;
	DogGrowlT = DogCalmT = DogBarkT = 0.0f;
	PlaySfx(TEXT("recoger"), DogLoc + FVector(0.0f, 0.0f, 40.0f));
	ShowMessage(Tx(TEXT("perro_amigo"), TEXT("EL PERRO\nSuelta el grunido a medias, olfatea el trapo y te quita el hueso de la mano. Se sienta a roerlo.\nYa no ladrara por ti.")), 7.0f);
}

void ATarsisDirector::DogTick(float DeltaSeconds)
{
	if (!bDog)
	{
		if (DogMesh && DogMesh->IsVisible()) DogMesh->SetVisibility(false);
		return;
	}
	if (!DogMesh)
	{
		if (!bDogTried) SpawnDog();
		if (!DogMesh) return;
	}
	if (!DogMesh->IsVisible()) DogMesh->SetVisibility(true);
	if (DogState != 3 && HasFlag(FName(TEXT("perro_amigo")))) DogState = 3;   // partida cargada
	const APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	const FVector P = Pl ? Pl->GetActorLocation() : DogLoc;
	const float D = FVector::Dist2D(P, DogLoc);
	// no ve: huele (ni la sombra ni la caja le enganan) y oye correr. Dentro del camion o preso, no le llegas
	const bool bReach = Pl && !bCine && !bDone && !bCapturing && !bRiding && !InCell() && FMath::Abs(P.Z - DogZ) < 400.0f;
	const bool bRun = bSprint && Pl && Pl->GetVelocity().SizeSquared2D() > 300.0f * 300.0f;
	const bool bSense = bReach && (D < DogSmell || (bRun && D < DogHear));
	if (DogState == 3)
	{
		// amigo: sentado donde le diste el hueso; te sigue con la cabeza (con todo el cuerpo, que no tiene mas)
		DogSitT += DeltaSeconds;
		if (DogSitT < 0.6f) DogAnim(2, false); else DogAnim(3, true);
		if (bReach && D < 900.0f) DogFace(P, DeltaSeconds * 0.4f);
		DogPlace();
		return;
	}
	if (DogState == 0)
	{
		if (bSense)
		{
			DogState = 1;
			DogGrowlT = DogCalmT = 0.0f;
			++DogGrowls;
			PlaySfx(TEXT("grunido"), DogLoc + FVector(0.0f, 0.0f, 50.0f));
			Teach(TEXT("perro_grune"), TEXT("EL PERRO TE HA OLIDO\nGrune: todavia no ladra. Apartate despacio y se le pasa. La sombra y la caja no le enganan.\nQuiza algo de comer le haga cambiar de idea."), {}, 7.0f);
		}
		else if (DogSitT > 0.0f)
		{
			// sentado en una punta de la ronda
			DogSitT -= DeltaSeconds;
			DogAnim(DogSitT > DogRest - 0.6f ? 2 : 3, DogSitT <= DogRest - 0.6f);
		}
		else
		{
			const FVector To = DogToB ? DogB : DogA;
			const FVector Dir = FVector(To.X - DogLoc.X, To.Y - DogLoc.Y, 0.0f);
			if (Dir.SizeSquared() < 30.0f * 30.0f) { DogToB = !DogToB; DogSitT = DogRest; }
			else
			{
				DogFace(To, DeltaSeconds);
				DogLoc += Dir.GetSafeNormal() * DogSpeed * DeltaSeconds;
				DogAnim(1, true);
			}
		}
		DogPlace();
		return;
	}
	// grune (1) o ladra (2): plantado, de cara a ti
	DogSitT = 0.0f;
	DogAnim(0, true);
	if (bReach) DogFace(P, DeltaSeconds);
	const bool bGone = !bReach || D > (DogState == 2 ? DogHear : DogSmell * 1.25f);
	DogCalmT = bGone ? DogCalmT + DeltaSeconds : 0.0f;
	if (DogCalmT > (DogState == 2 ? 3.0f : 1.5f)) { DogState = 0; DogPlace(); return; }
	if (DogState == 1)
	{
		if (!bGone) DogGrowlT += DeltaSeconds;
		if (DogGrowlT > DogGrowlSeconds || (bReach && D < 180.0f && DogGrowlT > 0.8f)) { DogState = 2; DogBarkT = 0.0f; DogBarkN = 0; }
	}
	else
	{
		DogBarkT -= DeltaSeconds;
		if (DogBarkT <= 0.0f)
		{
			DogBarkT = 1.3f;
			++DogBarks;
			PlaySfx(TEXT("ladrido"), DogLoc + FVector(0.0f, 0.0f, 50.0f), 1.0f);
			// al primer ladrido y luego cada cuatro: los dos guardias libres mas cercanos vienen a ver que le pasa
			if (DogBarkN++ % 4 == 0)
			{
				TArray<ATarsisGuard*> Free;
				for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
				{
					if (It->bTowerSentry || It->bAlly || It->IsOnErrand()) continue;
					if (It->State != ETarsisGuardState::Patrol && It->State != ETarsisGuardState::Return) continue;
					if (FVector::DistSquared2D(It->GetActorLocation(), DogLoc) > DogBarkRadius * DogBarkRadius) continue;
					Free.Add(*It);
				}
				const FVector Here = DogLoc;
				Free.Sort([&Here](const ATarsisGuard& A, const ATarsisGuard& B) { return FVector::DistSquared(A.GetActorLocation(), Here) < FVector::DistSquared(B.GetActorLocation(), Here); });
				for (int32 i = 0; i < Free.Num() && i < 2; ++i) { Free[i]->HearNoise(DogLoc); ++DogCalls; }
				Teach(TEXT("perro_ladra"), TEXT("EL PERRO LADRA\nLos guardias de cerca vienen a ver que le pasa. Sal del hangar y espera a que se calle."), {}, 6.0f);
			}
		}
	}
	DogPlace();
}
