// Lost Horizon: De Profundis - tanda 46: el perro del hangar.
// Un pastor ronda el hangar de lado a lado y se sienta un rato en cada punta. No ve: huele. Si te acercas (da igual la
// sombra, ir agachado o la caja de carton) se planta y grune unos segundos: es el aviso. Si no te apartas, ladra, y los
// guardias mas cercanos vienen a ver que le pasa. Con el hueso de la olla de la cocina se le puede callar para siempre:
// se sienta, y desde entonces es amigo.
//
// Tanda B (2026-11-21): el perro es un lobo (Animal Variety Pack de Protofactor, /Game/AnimalVarietyPack/Wolf; si no esta,
// el perro de antes). Amigo, va a por la piedra que tiras (Q) si cae a menos de DogFetchRadius, la coge con la boca y te
// la trae; y el guardia tranquilo que lo ve cerca cree que es un perro suelto: va, se agacha y lo acaricia un rato (y
// mientras mira al suelo).
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Animation/AnimationAsset.h"
#include "AssetRegistry/AssetData.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "PhysicsEngine/PhysicsHandleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

void ATarsisDirector::SpawnDog()
{
	bDogTried = true;
	// lo importa tools/unreal/perro.py en /Game/Tarsis/Perro: una malla con esqueleto y cuatro animaciones
	USkeletalMesh* SK = nullptr;
	// tanda B: el lobo, si esta el pack (nombres del pack: ANIM_Wolf_<x>)
	bDogWolf = false;
	if (!WolfDir.IsEmpty())
	{
		SK = LoadObject<USkeletalMesh>(nullptr, *FString::Printf(TEXT("%s/Meshes/SK_Wolf.SK_Wolf"), *WolfDir));
		if (SK)
		{
			static const TCHAR* Wolf[DogAnimSlots] = { TEXT("IdleBreathe"), TEXT("Walk"), TEXT("GoToRest"), TEXT("Rest"), TEXT("Run"), TEXT("IdleAggressive"), TEXT("Howl"), TEXT("RestToGoBackUp"), TEXT("Bite") };
			for (int32 i = 0; i < DogAnimSlots; ++i)
			{
				DogAnims[i] = LoadObject<UAnimationAsset>(nullptr, *FString::Printf(TEXT("%s/Animations/ANIM_Wolf_%s.ANIM_Wolf_%s"), *WolfDir, Wolf[i], Wolf[i]));
			}
			bDogWolf = DogAnims[0] && DogAnims[1] && DogAnims[3];
			if (!bDogWolf) { SK = nullptr; for (int32 i = 0; i < DogAnimSlots; ++i) DogAnims[i] = nullptr; }
		}
	}
	if (!SK)
	{
		// el perro de antes: lo importa tools/unreal/perro.py en /Game/Tarsis/Perro, una malla y cuatro animaciones
		TArray<FAssetData> List;
		IAssetRegistry::GetChecked().GetAssetsByPath(FName(TEXT("/Game/Tarsis/Perro")), List, true);
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
	DogMesh->SetWorldScale3D(FVector(bDogWolf ? WolfScale : DogScale));
	DogMesh->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	DogMesh->RegisterComponent();
	// tanda C: sin saltos entre animaciones. Dos copias ocultas (DogMesh y DogMeshB) tocan la animacion de antes y la
	// nueva; la que se ve (DogVis) mezcla sus poses durante DogBlendSeconds
	DogMesh->SetHiddenInGame(true);
	DogMesh->SetCastShadow(false);
	DogMeshB = NewObject<USkeletalMeshComponent>(this);
	DogMeshB->SetSkeletalMesh(SK);
	DogMeshB->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	DogMeshB->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	DogMeshB->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	DogMeshB->SetHiddenInGame(true);
	DogMeshB->SetCastShadow(false);
	DogMeshB->SetupAttachment(DogMesh);
	DogMeshB->RegisterComponent();
	DogVis = NewObject<UPoseableMeshComponent>(this);
	DogVis->SetSkinnedAssetAndUpdate(SK);
	DogVis->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	DogVis->SetupAttachment(DogMesh);
	DogVis->RegisterComponent();
	DogCur = 0;
	DogBlendT = 0.0f;
	// el lobo: hacia donde mira la malla (de la pelvis a la cabeza, en la pose de referencia) y el hueso de la boca
	DogHeadBone = NAME_None;
	if (bDogWolf)
	{
		const FReferenceSkeleton& Ref = SK->GetRefSkeleton();
		FName Pelvis = NAME_None;
		for (int32 i = 0; i < Ref.GetNum(); ++i)
		{
			const FString N = Ref.GetBoneName(i).ToString().ToLower();
			if (DogBackBone.IsNone() && N.EndsWith(TEXT("spine1"))) DogBackBone = Ref.GetBoneName(i);
			if (N.Contains(TEXT("tail")) && DogTailBones.Num() < 4) DogTailBones.Add(Ref.GetBoneName(i));
			if (DogHeadBone.IsNone() && N.EndsWith(TEXT("head"))) DogHeadBone = Ref.GetBoneName(i);
			if (Pelvis.IsNone() && N.EndsWith(TEXT("pelvis"))) Pelvis = Ref.GetBoneName(i);
		}
		if (bDogAutoYaw && !DogHeadBone.IsNone() && !Pelvis.IsNone())
		{
			auto CS = [&Ref](FName B) { FTransform T = FTransform::Identity; for (int32 i = Ref.FindBoneIndex(B); i != INDEX_NONE; i = Ref.GetParentIndex(i)) T = T * Ref.GetRefBonePose()[i]; return T.GetLocation(); };
			const FVector F = CS(DogHeadBone) - CS(Pelvis);
			if (F.SizeSquared2D() > 1.0f) DogMeshYaw = -F.Rotation().Yaw;
		}
		UE_LOG(LogTemp, Log, TEXT("Tarsis: lobo (%s), giro de la malla %.0f, cabeza %s"), *WolfDir, DogMeshYaw, *DogHeadBone.ToString());
	}
	DogFetch = 0;
	DogStone = nullptr;
	DogPetG = nullptr;
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
	DogPoseTick();
}

void ATarsisDirector::DogPoseTick()
{
	USkeletalMeshComponent* Cur = DogCur == 0 ? DogMesh.Get() : DogMeshB.Get();
	USkeletalMeshComponent* Prev = DogCur == 0 ? DogMeshB.Get() : DogMesh.Get();
	if (!DogVis || !Cur) return;
	WolfFootprint();   // tanda D: en el barro tambien deja huellas (las del perro: no alarman)
	// tanda C: al paso de la animacion (la velocidad de verdad entre la de la animacion) para que no patine
	const float Dt = FMath::Max(DogDt, 1e-4f);
	DogSpeedNow = FMath::FInterpTo(DogSpeedNow, FVector::Dist2D(DogLoc, DogPrevLoc) / Dt, Dt, 10.0f);
	DogPrevLoc = DogLoc;
	const float Scale = bDogWolf ? WolfScale : DogScale;
	if (bDogWolf && (DogAnimNow == 1 || DogAnimNow == 4))
	{
		const float Nat = (DogAnimNow == 1 ? WolfWalkAnimSpeed : WolfRunAnimSpeed) * Scale;
		DogRate = FMath::Clamp(DogSpeedNow / FMath::Max(Nat, 1.0f), 0.45f, 1.8f);
	}
	else DogRate = 1.0f;
	Cur->SetPlayRate(DogRate);
	// la mezcla entre la animacion de antes y la nueva
	if (DogBlendT > 0.0f) DogBlendT -= Dt;
	const TArray<FTransform>& B = Cur->GetBoneSpaceTransforms();
	if (DogBlendT <= 0.0f || !Prev || Prev->GetBoneSpaceTransforms().Num() != B.Num() || DogVis->BoneSpaceTransforms.Num() != B.Num())
	{
		DogVis->CopyPoseFromSkeletalComponent(Cur);
		DogWagTick(Dt);
		return;
	}
	const TArray<FTransform>& A = Prev->GetBoneSpaceTransforms();
	const float Alpha = FMath::SmoothStep(0.0f, 1.0f, 1.0f - DogBlendT / FMath::Max(DogBlendSeconds, 0.01f));
	for (int32 i = 0; i < B.Num(); ++i) DogVis->BoneSpaceTransforms[i].Blend(A[i], B[i], Alpha);
	DogVis->MarkRefreshTransformDirty();
	DogWagTick(Dt);
}

void ATarsisDirector::DogWagTick(float Dt)
{
	// tanda C: mueve la cola mientras lo acarician: una onda de lado a lado por los huesos de la cola, sobre la pose
	const ATarsisGuard* G = DogPetG.Get();
	DogWagW = FMath::FInterpConstantTo(DogWagW, (G && G->PetCrouched()) ? 1.0f : 0.0f, Dt, 2.0f);
	if (DogWagW <= 0.0f || !DogVis || DogTailBones.Num() == 0) return;
	DogWagPhase = FMath::Fmod(DogWagPhase + Dt * DogWagHz * 2.0f * PI, 2.0f * PI);
	const FVector Up = DogVis->GetComponentTransform().InverseTransformVectorNoScale(FVector::UpVector).GetSafeNormal();
	for (int32 i = 0; i < DogTailBones.Num(); ++i)
	{
		const float Ang = FMath::DegreesToRadians(DogWagDegrees * DogWagW * FMath::Sin(DogWagPhase - 0.6f * i) * (i == 0 ? 1.0f : 0.5f));
		FTransform T = DogVis->GetBoneTransformByName(DogTailBones[i], EBoneSpaces::ComponentSpace);
		T.SetRotation((FQuat(Up, Ang) * T.GetRotation()).GetNormalized());
		DogVis->SetBoneTransformByName(DogTailBones[i], T, EBoneSpaces::ComponentSpace);
	}
}

void ATarsisDirector::DogAnim(int32 Which, bool bLoop)
{
	if (!DogMesh || DogAnimNow == Which) return;
	const bool bFirst = DogAnimNow < 0;
	DogAnimNow = Which;
	// sin esa animacion (el perro de antes solo tiene cuatro): correr = andar, grunir = quieto, levantarse = quieto
	int32 A = Which;
	if (A >= 0 && A < DogAnimSlots && !DogAnims[A]) A = (A == 4) ? 1 : 0;
	if (A < 0 || A >= DogAnimSlots || !DogAnims[A]) return;
	// tanda C: la nueva en la otra copia, y la que se ve pasa de una a otra (la primera vez, sin mezcla)
	if (!bFirst && DogMeshB) DogCur = 1 - DogCur;
	USkeletalMeshComponent* Cur = DogCur == 0 ? DogMesh.Get() : DogMeshB.Get();
	Cur->PlayAnimation(DogAnims[A], bLoop);
	Cur->SetPlayRate(1.0f);
	DogBlendT = bFirst ? 0.0f : DogBlendSeconds;
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

void ATarsisDirector::DogForgetPets()
{
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It) It->PetDoneAt = -1e9f;
	DogPetScanT = 0.0f;
}

FVector ATarsisDirector::DogMouth() const
{
	if (!DogMesh) return DogLoc;
	const FVector Fwd = FRotator(0.0f, DogYaw, 0.0f).Vector();
	if (!DogHeadBone.IsNone() && DogVis) return DogVis->GetBoneLocationByName(DogHeadBone, EBoneSpaces::WorldSpace) + Fwd * DogMouthFwd - FVector(0.0f, 0.0f, DogMouthDown);
	return DogLoc + Fwd * 45.0f + FVector(0.0f, 0.0f, 35.0f);
}

FVector ATarsisDirector::DogStoneLocation() const
{
	return DogStone.IsValid() ? DogStone->GetComponentLocation() : FVector::ZeroVector;
}

void ATarsisDirector::DogStoneThrown(const FVector& Where, UStaticMeshComponent* Stone)
{
	// solo el lobo amigo, tranquilo (ni trayendo otra ni con un guardia encima), y si la piedra cae a su alcance y a su altura
	if (!bDog || !DogMesh || DogState != 3 || DogFetch != 0 || !Stone) return;
	if (DogPetG.IsValid() && DogPetG->PetCrouched()) return;
	if (FVector::Dist2D(Where, DogLoc) > DogFetchRadius || FMath::Abs(Where.Z - DogZ) > 150.0f) return;
	// por el suelo de verdad (navmesh), no a traves de las paredes; si no hay camino o es mucho mas largo, no va
	if (!DogPathTo(Where) || DogPathLen > DogFetchRadius * 1.6f) return;
	DogStone = Stone;
	DogFetchAt = Where;
	DogFetch = 1;
	DogFetchT = 0.0f;
	if (DogPetG.IsValid()) { DogPetG->StopPet(); DogPetG->EndErrand(); DogPetG = nullptr; }   // se le escapa al que venia a acariciarlo
}

bool ATarsisDirector::DogPathTo(const FVector& Goal)
{
	DogPath.Reset();
	DogPathI = 0;
	DogPathLen = 0.0f;
	DogPathGoal = Goal;
	UNavigationPath* Path = UNavigationSystemV1::FindPathToLocationSynchronously(GetWorld(), FVector(DogLoc.X, DogLoc.Y, DogZ + 20.0f), Goal, this);
	if (!Path || !Path->IsValid() || Path->IsPartial() || Path->PathPoints.Num() < 1)
	{
		// sin navmesh (o el sitio no esta en ella): solo si se ve en linea recta y sin nada en medio
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisLoboCamino), false, this);
		if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, FVector(DogLoc.X, DogLoc.Y, DogZ + 40.0f), FVector(Goal.X, Goal.Y, Goal.Z + 25.0f), ECC_Visibility, Q)) return false;
		DogPath.Add(Goal);
		DogPathLen = FVector::Dist2D(DogLoc, Goal);
		return true;
	}
	FVector Prev = DogLoc;
	for (const FVector& P : Path->PathPoints)
	{
		DogPathLen += FVector::Dist2D(Prev, P);
		Prev = P;
		DogPath.Add(P);
	}
	// tanda D: el navmesh es el de los guardias y el lobo es largo: en las esquinas rozaba el muro. Cada punto de en medio
	// se aparta de lo que tenga cerca (ocho rayos de DogWallClear a media altura)
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisLoboEsquina), false, this);
	if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
	for (int32 k = 1; k + 1 < DogPath.Num(); ++k)
	{
		FVector Push = FVector::ZeroVector;
		const FVector At = DogPath[k] + FVector(0.0f, 0.0f, 40.0f);
		for (int32 a = 0; a < 8; ++a)
		{
			const FVector Dir = FRotator(0.0f, a * 45.0f, 0.0f).Vector();
			FHitResult Hit;
			if (GetWorld()->LineTraceSingleByChannel(Hit, At, At + Dir * DogWallClear, ECC_Visibility, Q)) Push -= Dir * (DogWallClear - Hit.Distance);
		}
		if (!Push.IsNearlyZero()) { DogPath[k] += Push.GetClampedToMaxSize(DogWallClear); ++DogCornerPushes; }
	}
	return true;
}

float ATarsisDirector::DogSteer(const FVector& Goal, float Speed, float StopAt, float DeltaSeconds)
{
	// rehace el camino si el destino se ha movido (vuelves a por ti: le sigues moviendote)
	DogRepathT -= DeltaSeconds;
	if (DogPath.Num() == 0 || (DogRepathT <= 0.0f && FVector::DistSquared2D(Goal, DogPathGoal) > 80.0f * 80.0f))
	{
		DogRepathT = 0.8f;
		if (!DogPathTo(Goal)) { DogPath.Reset(); DogPath.Add(Goal); }
	}
	// el siguiente punto del camino (el ultimo es el destino)
	while (DogPathI < DogPath.Num() - 1 && FVector::Dist2D(DogLoc, DogPath[DogPathI]) < 40.0f) ++DogPathI;
	const FVector To = DogPathI < DogPath.Num() - 1 ? DogPath[DogPathI] : Goal;
	const float Left = FVector::Dist2D(DogLoc, Goal);
	const FVector Dir(To.X - DogLoc.X, To.Y - DogLoc.Y, 0.0f);
	if (Left <= StopAt || Dir.IsNearlyZero()) return Left;
	DogFace(To, DeltaSeconds * 2.5f);
	const float Ahead = FVector::DotProduct(FRotator(0.0f, DogYaw, 0.0f).Vector(), Dir.GetSafeNormal());
	const float Step = FMath::Min(FMath::Min(Dir.Size(), Left - StopAt), Speed * FMath::Clamp(Ahead, 0.25f, 1.0f) * DeltaSeconds);
	DogLoc += Dir.GetSafeNormal() * FMath::Max(Step, 0.0f);
	return Left;
}

void ATarsisDirector::DogFetchTick(const FVector& PlayerLoc, bool bReach, float DeltaSeconds)
{
	DogFetchT += DeltaSeconds;
	UStaticMeshComponent* St = DogStone.Get();
	auto Drop = [this, St]()
	{
		if (St)
		{
			// la deja en el suelo, delante del hocico
			const FVector At = DogLoc + FRotator(0.0f, DogYaw, 0.0f).Vector() * 55.0f;
			St->SetWorldLocationAndRotation(FVector(At.X, At.Y, DogZ + 3.0f), FRotator(0.0f, FMath::FRandRange(0.0f, 360.0f), 0.0f));
		}
		DogFetch = 0;
		DogSitT = -0.8f;   // un momento de pie antes de volver a tumbarse
		DogStone = nullptr;
	};
	if (!St && DogFetch != 4) { DogFetch = 0; DogSitT = 0.0f; return; }   // la piedra ya no esta (se limpian las viejas)
	if (DogFetch == 1)
	{
		// arranca a correr (si estaba tumbado, se levanta de un salto: la de levantarse dura 1,5 s y no queda bien)
		if (DogSteer(DogFetchAt, DogRunSpeed, 40.0f, DeltaSeconds) <= 45.0f || DogFetchT > 15.0f) { DogFetch = 2; DogFetchT = 0.0f; DogAnim(8, false); DogPath.Reset(); }
		else DogAnim(4, true);
	}
	else if (DogFetch == 2)
	{
		// baja el hocico (morder) y a los 0,3 s la piedra ya esta en la boca
		if (DogFetchT > 0.3f) St->SetWorldLocation(DogMouth());
		if (DogFetchT > 0.65f) { DogFetch = 3; DogFetchT = 0.0f; }
	}
	else if (DogFetch == 3)
	{
		St->SetWorldLocation(DogMouth());
		// no le llegas (en el camion, preso, en otra planta) o tarda demasiado: la suelta donde este
		if (!bReach || DogFetchT > 25.0f) { Drop(); return; }
		const float Far = FVector::Dist2D(PlayerLoc, DogLoc);
		const float Sp = Far > 500.0f ? DogRunSpeed : FMath::Max(bDogWolf ? WolfWalkSpeed : DogSpeed, DogRunSpeed * 0.45f);
		if (DogSteer(PlayerLoc, Sp, 140.0f, DeltaSeconds) < 150.0f) { DogFetch = 4; DogFetchT = 0.0f; DogAnim(0, true); DogPath.Reset(); }
		else DogAnim(Far > 500.0f ? 4 : 1, true);
	}
	else if (DogFetch == 4)
	{
		// de cara a ti, la suelta a tus pies
		DogFace(PlayerLoc, DeltaSeconds * 2.0f);
		if (St) St->SetWorldLocation(DogMouth());
		if (DogFetchT > 0.45f)
		{
			Drop();
			++DogFetches;
			PlaySfx(TEXT("piedra"), DogLoc + FVector(0.0f, 0.0f, 10.0f), 0.35f);
		}
	}
}

void ATarsisDirector::DogPetTick(float DeltaSeconds)
{
	// el que ya va o ya lo acaricia: el lobo se queda quieto, de cara a el
	if (ATarsisGuard* G = DogPetG.Get())
	{
		if (!G->IsPetting()) { DogPetG = nullptr; DogSitT = 0.0f; return; }
		return;
	}
	if (DogFetch != 0 || bCine || bDone || bCapturing) return;
	DogPetScanT -= DeltaSeconds;
	if (DogPetScanT > 0.0f) return;
	DogPetScanT = 0.5f;
	const float Now = GetWorld()->GetTimeSeconds();
	ATarsisGuard* Best = nullptr;
	float BestD = DogPetRadius;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisLoboVisto), false, this);
	if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		// tranquilo: de ronda, sin recado, sin sospecha ni nada entre manos
		if (G->bTowerSentry || G->bAlly || G->bSceneLock || G->IsOnErrand() || G->IsStunned() || G->IsCheckingBody() || G->IsInvestigating()) continue;
		if (G->State != ETarsisGuardState::Patrol || G->Meter > 0.05f) continue;
		if (Now - G->PetDoneAt < DogPetCooldown) continue;
		const FVector E = G->GetActorLocation() + FVector(0.0f, 0.0f, 60.0f);
		const FVector W = DogLoc + FVector(0.0f, 0.0f, 40.0f);
		const float D = FVector::Dist2D(E, W);
		if (D > BestD || FMath::Abs(E.Z - W.Z) > 300.0f) continue;
		// lo ve: delante (o muy cerca) y sin nada en medio
		if (D > 300.0f && FVector::DotProduct(G->GetActorForwardVector(), (W - E).GetSafeNormal2D()) < 0.4f) continue;
		Q.ClearIgnoredSourceObjects();
		Q.AddIgnoredActor(this);
		Q.AddIgnoredActor(G);
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, E, W, ECC_Visibility, Q)) continue;
		Best = G;
		BestD = D;
	}
	if (!Best) return;
	if (!Best->StartPet(DogBackLocation(), DogPetSeconds)) return;
	DogPetG = Best;
	++DogPets;
	GuardSay(Best, TEXT("lobo"));
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
	DogDt = DeltaSeconds;
	if (!bDog)
	{
		if (DogVis && DogVis->IsVisible()) DogVis->SetVisibility(false);
		return;
	}
	if (!DogMesh)
	{
		if (!bDogTried) SpawnDog();
		if (!DogMesh) return;
	}
	if (DogVis && !DogVis->IsVisible()) DogVis->SetVisibility(true);
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
		// tanda B: a por la piedra
		if (DogFetch != 0)
		{
			DogFetchTick(P, bReach, DeltaSeconds);
			DogPlace();
			return;
		}
		DogPetTick(DeltaSeconds);
		if (ATarsisGuard* G = DogPetG.Get())
		{
			// un guardia viene a acariciarlo: de pie, quieto, de cara a el; cuando se agacha, se tumba y se deja (tanda C)
			// y la mano del guardia va al lomo con un vaiven
			if (G->PetCrouched())
			{
				// tanda C: de pie (tumbado, el lomo queda fuera del alcance del guardia agachado) y moviendo la cola (el pack
				// no trae animacion de cola: la mueve DogPoseTick sobre la pose que se ve)
				DogPetLieT += DeltaSeconds;
				DogAnim(0, true);
				FVector Back = DogLoc + FVector(0.0f, 0.0f, 45.0f);
				if (DogVis && !DogBackBone.IsNone()) Back = DogVis->GetBoneLocationByName(DogBackBone, EBoneSpaces::WorldSpace);
				const FVector Fwd = FRotator(0.0f, DogYaw, 0.0f).Vector();
				G->PetHandWorld = Back + FVector(0.0f, 0.0f, DogPetHandUp) + Fwd * FMath::Sin(GetWorld()->GetTimeSeconds() * DogPetStrokeHz * 2.0f * PI) * DogPetStroke;
			}
			else
			{
				DogPetLieT = 0.0f;
				DogSitT = 0.0f;
				DogAnim(0, true);
				DogFace(G->GetActorLocation(), DeltaSeconds * 0.6f);
				G->PetHandWorld = FVector::ZeroVector;
			}
			DogPlace();
			return;
		}
		DogPetLieT = 0.0f;
		// amigo: tumbado donde le diste el hueso (o donde te dejo la piedra); te sigue con la cabeza (con todo el cuerpo)
		DogSitT += DeltaSeconds;
		if (DogSitT < 0.0f) DogAnim(0, true);
		else if (DogSitT < 0.6f) DogAnim(2, false); else DogAnim(3, true);
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
				DogLoc += Dir.GetSafeNormal() * (bDogWolf ? WolfWalkSpeed : DogSpeed) * DeltaSeconds;
				DogAnim(1, true);
			}
		}
		DogPlace();
		return;
	}
	// grune (1) o ladra (2): plantado, de cara a ti (el lobo, con la de grunir)
	DogSitT = 0.0f;
	DogAnim(5, true);
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

FVector ATarsisDirector::DogBackLocation() const
{
	if (DogVis && !DogBackBone.IsNone()) return DogVis->GetBoneLocationByName(DogBackBone, EBoneSpaces::WorldSpace);
	return DogLoc + FVector(0.0f, 0.0f, 45.0f);
}

bool ATarsisDirector::DragPhysics() const
{
	return Dragged && DragHandle && DragHandle->GetGrabbedComponent() != nullptr;
}

FString ATarsisDirector::LastStoneMesh() const
{
	const UStaticMeshComponent* S = Stones.Num() > 0 ? Stones.Last().Get() : nullptr;
	return S && S->GetStaticMesh() ? S->GetStaticMesh()->GetName() : FString();
}

FVector ATarsisDirector::LastStoneSize() const
{
	const UStaticMeshComponent* S = Stones.Num() > 0 ? Stones.Last().Get() : nullptr;
	return S ? S->Bounds.BoxExtent * 2.0f : FVector::ZeroVector;
}

// ---- el guardia que acaricia al lobo (tanda B)

bool ATarsisGuard::StartPet(const FVector& DogAt, float Seconds)
{
	// se pone al lado del lobo, por la parte de donde viene, y lo mira
	FVector Side = (GetActorLocation() - DogAt).GetSafeNormal2D();
	if (Side.IsNearlyZero()) Side = -GetActorForwardVector();
	// tanda C: el recado se da por llegado a 70 cm del punto, y la mano tiene que llegar al lomo agachado: el punto va
	// algo mas alla del lomo (PetStandOff negativo) para que se pare pegado al lobo
	const FVector Where = DogAt + Side * PetStandOff;
	const float Travel = FVector::Dist2D(GetActorLocation(), Where) / FMath::Max(WalkSpeed, 50.0f);
	if (!Errand(Where, DogAt, Travel * 1.6f + Seconds + 3.0f)) return false;
	bPetting = true;
	PetT = 0.0f;
	PetSeconds = Seconds;
	PetDog = DogAt;
	return true;
}

void ATarsisGuard::StopPet()
{
	if (!bPetting) return;
	bPetting = false;
	PetT = 0.0f;
	PetHandWorld = FVector::ZeroVector;
	if (bIsCrouched) UnCrouch();
	PetDoneAt = GetWorld() ? GetWorld()->GetTimeSeconds() : 0.0f;
}

void ATarsisGuard::PetTick(float DeltaSeconds)
{
	if (!bPetting) return;
	// en cuanto ve u oye algo (o le cae un recado mas urgente), se acabo el perro
	if (!bErrand || State != ETarsisGuardState::Patrol || StunT > 0.0f || bSceneLock) { StopPet(); return; }
	if (!bErrandThere) return;
	if (PetT <= 0.0f)
	{
		if (UCharacterMovementComponent* M = GetCharacterMovement()) M->GetNavAgentPropertiesRef().bCanCrouch = true;
		Crouch();
	}
	PetT += DeltaSeconds;
	if (PetT >= PetSeconds)
	{
		StopPet();
		EndErrand();   // vuelve a su ronda
	}
}
