// Lost Horizon: De Profundis - tanda A, novena (2026-11-21): la deteccion con las parejas del Game Animation Sample.
//
// Depende de como te pillen (lo decide BeginCapture; la logica de cuando te cogen no cambia):
//  - Rendido (te quedaste quieto con el alto, viene ArrestGuard; o te coge de cerca, la taquilla, el camion): la pareja
//    de empujon parado (shove) del GASP. El guardia hace la parte _A con su maniqui (ScenePlay; la persona la copia con
//    el retarget) y Cuttlas la _V con ConductorGASP (CuerpoCuttlas la copia). En el segundo del aviso TriggerRagdoll,
//    ConductorGASP pasa a fisica (PA_UEFN_Mannequin). El guardia suelta su parte donde acabo su raiz, se acerca, se
//    agacha sobre ti (pose de agachado del ABP del GASP), suena el clic de las esposas y funde a negro.
//  - Golpe (huyendo, bFleeing, o el tercer tiro): la pareja de derribo parado (takedown), con su sacudida en cada
//    golpe; al caer, vista borrosa y doble medio segundo, la camara al suelo y negro. Al despertar, la vista se aclara.
// La pareja se elige por la direccion en que esta el guardia (F, B, L, R) y se colocan a mano: las raices de _A y _V
// al empezar estan grabadas en el mismo espacio (TarsisCapturaDatos.inl, de tools/unreal/captura_datos.py), asi que
// las dos mallas se ponen en el mismo sitio (SceneComp) y el guardia se lleva a donde empieza su raiz.
// Camara: en primera persona una ACameraActor sigue a la cabeza de ConductorGASP (con sacudida) y queda de lado en el
// suelo mirando las botas del guardia; en tercera se queda la de siempre y se ve la caida.
// Sin el GASP en el guardia o en Cuttlas, o sin las animaciones, la escena de antes (giro, empujon y negro).
// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "AIController.h"
#include "Animation/AnimSequenceBase.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/CapsuleComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"

namespace
{
	struct FScenePair
	{
		const TCHAR* Kind;   // shove, takedown
		const TCHAR* Dir;    // F, B, L, R
		float LenA, LenV;
		FVector RootA; float YawA;   // raiz al empezar, en el espacio comun de la grabacion
		FVector RootV; float YawV;
		float Fall;   // segundo en que Cuttlas pasa a fisica (TriggerRagdoll)
		float Hit;    // primer golpe del guardia
		float Free;   // el guardia ya puede soltar su parte (MontageBlendOut)
	};
	const FScenePair ScenePairs[] = {
#include "TarsisCapturaDatos.inl"
	};

	UAnimSequenceBase* LoadPairAnim(const FScenePair& P, bool bAttacker)
	{
		const TCHAR* Who = bAttacker ? TEXT("A") : TEXT("V");
		const FString Path = FCString::Strcmp(P.Kind, TEXT("shove")) == 0
			? FString::Printf(TEXT("/Game/Characters/UEFN_Mannequin/Animations/Interactions/Shoves/M_relaxed_ragdoll_shove_stand_%s_%s"), P.Dir, Who)
			: FString::Printf(TEXT("/Game/Characters/UEFN_Mannequin/Animations/Interactions/Takedowns/M_relaxed_takedown_stand_%s_%s_"), P.Dir, Who);
		return LoadObject<UAnimSequenceBase>(nullptr, *(Path + TEXT(".") + FPackageName::GetShortName(Path)));
	}

	FTransform RootAt(const FVector& L, float Yaw) { return FTransform(FRotator(0.0f, Yaw, 0.0f), L); }
}

bool ATarsisDirector::SceneBegin(ATarsisGuard* G, APawn* P)
{
	ACharacter* C = Cast<ACharacter>(P);
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!bCaptureSceneRule || !G || !C || !PC || !G->UsesGasp() || !G->GetMesh() || !HeroDriver || !HeroBody) return false;
	const bool bHit = bCaptureWounded || bFleeing;
	const TCHAR* Kind = bHit ? TEXT("takedown") : TEXT("shove");
	// donde esta ahora la raiz del maniqui de Cuttlas, de pie: ahi empieza la raiz de _V
	const float HalfH = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	SceneGroundZ = C->GetActorLocation().Z - HalfH;
	const FTransform Here(FRotator(0.0f, C->GetActorRotation().Yaw + HeroDriverYaw, 0.0f),
		FVector(C->GetActorLocation().X, C->GetActorLocation().Y, SceneGroundZ - HeroDriverBallZ + 2.0f));
	// tanda B: a golpes y con fusil, el culatazo de Lyra (sin pareja: el guardia delante, Cuttlas cae de espaldas)
	SceneMeleeAnim = nullptr;
	if (bHit && bCaptureMeleeRule && G->HasRifle())
	{
		SceneMeleeAnim = LoadObject<UAnimSequenceBase>(nullptr, TEXT("/Game/Tarsis/Armas/Anims/MM_Rifle_Melee.MM_Rifle_Melee"));
	}
	if (SceneMeleeAnim)
	{
		if (C->bIsCrouched) C->UnCrouch();
		FVector Dir = (G->GetActorLocation() - C->GetActorLocation()).GetSafeNormal2D();
		if (Dir.IsNearlyZero()) Dir = C->GetActorForwardVector().GetSafeNormal2D();
		SceneMeleeDir = -Dir;   // hacia donde le empuja el golpe
		SceneGuardRel = G->GetMesh()->GetRelativeTransform();
		SceneGuardFrom = G->GetActorLocation();
		SceneGuardFromRot = G->GetActorRotation();
		const FVector At = C->GetActorLocation() + Dir * CaptureMeleeDistance;
		SceneGuardTo = FVector(At.X, At.Y, G->GetActorLocation().Z);
		SceneGuardToRot = FRotator(0.0f, (-Dir).Rotation().Yaw + CaptureMeleeYaw, 0.0f);
		if (FVector::Dist2D(SceneGuardFrom, SceneGuardTo) > 300.0f) { SceneGuardFrom = SceneGuardTo; SceneGuardFromRot = SceneGuardToRot; }
		G->Hold(60.0f);
		G->bSceneLock = true;
		ScenePair = INDEX_NONE;
		ScenePairName = TEXT("culatazo");
		SceneKind = ETarsisSceneKind::Golpe;
		bScenePlaying = bSceneRagdoll = bSceneGuardFree = bSceneCrouched = bSceneCuffed = bSceneBlack = bScenePunched = bSceneImpact = false;
		bSceneHero = false;
		SceneShake = 0.0f;
		const float Lead = FMath::Max(CaptureSceneLead, 0.05f);
		SceneRagdollAt = Lead + CaptureMeleeHit;
		ScenePunchAt = SceneRagdollAt;
		SceneFreeAt = Lead + SceneMeleeAnim->GetPlayLength();
		SceneCrouchAt = 1e9f;
		SceneBlackAt = SceneRagdollAt + 0.9f;
		SceneEndAt = 1e9f;
		SceneCameraBegin(PC);
		UE_LOG(LogTemp, Log, TEXT("Tarsis: detencion a golpes con culatazo (%s)"), *G->GuardName);
		return true;
	}
	// la pareja cuyo guardia viene del lado en que esta
	const FVector Local = Here.InverseTransformPosition(G->GetActorLocation()).GetSafeNormal2D();
	int32 Best = INDEX_NONE;
	float BestDot = -2.0f;
	for (int32 i = 0; i < UE_ARRAY_COUNT(ScenePairs); ++i)
	{
		const FScenePair& Pr = ScenePairs[i];
		if (FCString::Strcmp(Pr.Kind, Kind) != 0) continue;
		const FVector Rel = RootAt(Pr.RootV, Pr.YawV).InverseTransformPosition(Pr.RootA).GetSafeNormal2D();
		const float Dot = FVector::DotProduct(Local, Rel);
		if (Dot > BestDot) { BestDot = Dot; Best = i; }
	}
	if (Best == INDEX_NONE) return false;
	const FScenePair& Pr = ScenePairs[Best];
	UAnimSequenceBase* A = LoadPairAnim(Pr, true);
	UAnimSequenceBase* V = LoadPairAnim(Pr, false);
	if (!A || !V) return false;
	if (C->bIsCrouched) C->UnCrouch();
	// las dos mallas en el mismo sitio (el espacio de la grabacion): la raiz de _V cae donde esta Cuttlas
	SceneComp = RootAt(Pr.RootV, Pr.YawV).Inverse() * Here;
	const FTransform GuardRoot = RootAt(Pr.RootA, Pr.YawA) * SceneComp;
	SceneGuardRel = G->GetMesh()->GetRelativeTransform();
	SceneGuardFrom = G->GetActorLocation();
	SceneGuardFromRot = G->GetActorRotation();
	SceneGuardTo = FVector(GuardRoot.GetLocation().X, GuardRoot.GetLocation().Y, G->GetActorLocation().Z);
	SceneGuardToRot = FRotator(0.0f, GuardRoot.Rotator().Yaw - SceneGuardRel.Rotator().Yaw, 0.0f);
	if (FVector::Dist2D(SceneGuardFrom, SceneGuardTo) > 300.0f) { SceneGuardFrom = SceneGuardTo; SceneGuardFromRot = SceneGuardToRot; }   // de lejos (el tiro): ya esta ahi
	G->Hold(60.0f);
	G->bSceneLock = true;
	ScenePair = Best;
	ScenePairName = FString::Printf(TEXT("%s_%s"), Pr.Kind, Pr.Dir);
	SceneKind = bHit ? ETarsisSceneKind::Golpe : ETarsisSceneKind::Rendido;
	bScenePlaying = bSceneRagdoll = bSceneGuardFree = bSceneCrouched = bSceneCuffed = bSceneBlack = bScenePunched = bSceneImpact = false;
	bSceneHero = false;
	SceneShake = 0.0f;
	const float Lead = FMath::Max(CaptureSceneLead, 0.05f);
	SceneRagdollAt = Lead + Pr.Fall;
	ScenePunchAt = Lead + Pr.Hit;
	SceneFreeAt = Lead + Pr.Free;
	SceneCrouchAt = SceneFreeAt + 0.9f;
	SceneBlackAt = bHit ? SceneRagdollAt + 0.9f : 1e9f;
	SceneEndAt = 1e9f;
	SceneCameraBegin(PC);
	UE_LOG(LogTemp, Log, TEXT("Tarsis: detencion %s con %s (%s)"), bHit ? TEXT("a golpes") : TEXT("rendido"), *ScenePairName, *G->GuardName);
	return true;
}

void ATarsisDirector::SceneCameraBegin(APlayerController* PC)
{
	// camara: en tercera se queda; en primera, una camara suelta que empieza donde esta la tuya
	bSceneThird = bThirdShown;
	if (!bSceneThird)
	{
		if (!SceneCam)
		{
			FActorSpawnParameters Sp;
			Sp.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
			SceneCam = GetWorld()->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), FTransform::Identity, Sp);
			if (SceneCam) SceneCam->GetCameraComponent()->SetConstraintAspectRatio(false);
		}
		if (SceneCam && PC->PlayerCameraManager)
		{
			SceneCam->SetActorLocationAndRotation(PC->PlayerCameraManager->GetCameraLocation(), PC->PlayerCameraManager->GetCameraRotation());
			SceneCam->GetCameraComponent()->SetFieldOfView(PC->PlayerCameraManager->GetFOVAngle());
			PC->SetViewTarget(SceneCam);
		}
		if (Arms) Arms->SetVisibility(false, true);
	}
}

void ATarsisDirector::ScenePreload()
{
	// tanda B: la primera detencion daba un tiron (cargar animaciones, la fisica del maniqui, la camara y el
	// postproceso a la vez): se carga todo al empezar la partida
	bScenePreloaded = true;
	for (const FScenePair& Pr : ScenePairs) { LoadPairAnim(Pr, true); LoadPairAnim(Pr, false); }
	LoadObject<UAnimSequenceBase>(nullptr, TEXT("/Game/Tarsis/Armas/Anims/MM_Rifle_Melee.MM_Rifle_Melee"));
	if (!SceneCam && GetWorld())
	{
		FActorSpawnParameters Sp;
		Sp.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		SceneCam = GetWorld()->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), FTransform::Identity, Sp);
		if (SceneCam) SceneCam->GetCameraComponent()->SetConstraintAspectRatio(false);
	}
	Sfx(TEXT("golpe"));
}

void ATarsisDirector::SceneTick(float DeltaSeconds)
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	ATarsisGuard* G = Captor;
	if (!C || !PC || (ScenePair == INDEX_NONE && !SceneMeleeAnim))
	{
		SceneKind = ETarsisSceneKind::None; bCapturing = false; Captor = nullptr;
		return;
	}
	const bool bMelee = SceneMeleeAnim != nullptr;
	const FScenePair& Pr = ScenePairs[bMelee ? 0 : ScenePair];
	const bool bHit = SceneKind == ETarsisSceneKind::Golpe;
	// tanda B: en tercera, la camara gira hacia un lado para que se vea a Cuttlas y al guardia (antes el guardia lo tapaba)
	if (bSceneThird && G && !bCaptureDone)
	{
		const FVector Side = (G->GetActorLocation() - C->GetActorLocation()).GetSafeNormal2D();
		if (!Side.IsNearlyZero())
		{
			const FRotator Cur = PC->GetControlRotation();
			const FRotator Want(-12.0f, Side.Rotation().Yaw + CaptureThirdSideYaw, 0.0f);
			PC->SetControlRotation(FMath::RInterpTo(Cur, Want, DeltaSeconds, 2.5f));
		}
	}
	// el guardia se pone en su sitio y empiezan las dos partes
	if (!bScenePlaying && G)
	{
		const float Lead = FMath::Max(CaptureSceneLead, 0.05f);
		const float S = FMath::SmoothStep(0.0f, 1.0f, FMath::Clamp(CaptureT / Lead, 0.0f, 1.0f));
		G->SetActorLocationAndRotation(FMath::Lerp(SceneGuardFrom, SceneGuardTo, S), FQuat::Slerp(SceneGuardFromRot.Quaternion(), SceneGuardToRot.Quaternion(), S).Rotator());
		if (CaptureT >= Lead)
		{
			G->SetActorLocationAndRotation(SceneGuardTo, SceneGuardToRot);
			bSceneHero = true;
			if (bMelee)
			{
				// culatazo: el guardia en su sitio con la animacion de Lyra; Cuttlas sigue de pie con el ABP hasta el golpe
				G->ScenePlay(SceneMeleeAnim);
			}
			else
			{
				G->ScenePlay(LoadPairAnim(Pr, true));
				G->GetMesh()->SetWorldTransform(SceneComp);
				HeroDriver->SetWorldTransform(SceneComp);
				HeroDriver->SetAnimationMode(EAnimationMode::AnimationSingleNode);
				HeroDriver->PlayAnimation(LoadPairAnim(Pr, false), false);
			}
			SceneHeadZ0 = HeroDriver->GetSocketLocation(TEXT("head")).Z;
			ScenePelvisPrev = HeroDriver->GetSocketLocation(TEXT("pelvis"));
			bScenePlaying = true;
		}
	}
	if (bScenePlaying && DeltaSeconds > 0.0f)
	{
		const FVector Pel = HeroDriver->GetSocketLocation(TEXT("pelvis"));
		ScenePelvisVel = (Pel - ScenePelvisPrev) / DeltaSeconds;
		ScenePelvisPrev = Pel;
	}
	// los golpes (derribo): ruido y sacudida
	if (bHit && bScenePlaying && !bScenePunched && CaptureT >= ScenePunchAt)
	{
		bScenePunched = true;
		PlaySfx(TEXT("golpe"), FVector::ZeroVector, 1.0f, false);
		SceneShake = 1.0f;
	}
	if (bScenePlaying && !bSceneRagdoll && CaptureT >= SceneRagdollAt)
	{
		SceneRagdoll(C);
		if (bMelee)
		{
			// el culatazo lo tira de espaldas: velocidad hacia atras y algo hacia arriba
			HeroDriver->SetAllPhysicsLinearVelocity(SceneMeleeDir * CaptureMeleePush + FVector(0.0f, 0.0f, 120.0f));
		}
		else PlaySfx(bHit ? TEXT("golpe") : TEXT("empujon"), FVector::ZeroVector, 1.0f, false);
		SceneShake = FMath::Max(SceneShake, bHit ? 1.2f : 0.6f);
	}
	// rendido: el guardia suelta su parte donde acabo su raiz, se acerca y se agacha sobre ti
	if (!bHit && G && bScenePlaying && !bSceneGuardFree && CaptureT >= SceneFreeAt)
	{
		bSceneGuardFree = true;
		const FVector Root = G->GetMesh()->GetSocketLocation(TEXT("root"));
		const FVector Pel = HeroDriver->GetSocketLocation(TEXT("pelvis"));
		G->GetMesh()->SetRelativeTransform(SceneGuardRel);
		const FVector At(Root.X, Root.Y, G->GetActorLocation().Z);
		G->SetActorLocationAndRotation(At, FRotator(0.0f, (Pel - At).Rotation().Yaw, 0.0f));
		G->SceneEnd();
		const FVector Dir = (Pel - At).GetSafeNormal2D();
		if (FVector::Dist2D(At, Pel) > 95.0f)
		{
			if (AAIController* AI = Cast<AAIController>(G->GetController())) AI->MoveToLocation(FVector(Pel.X, Pel.Y, At.Z) - Dir * 70.0f, 10.0f, false, true, false, false);
		}
	}
	if (!bHit && G && bSceneGuardFree && !bSceneCrouched && (CaptureT >= SceneCrouchAt || (CaptureT > SceneFreeAt + 0.3f && G->GetVelocity().Size2D() < 5.0f)))
	{
		bSceneCrouched = true;
		if (AAIController* AI = Cast<AAIController>(G->GetController())) AI->StopMovement();
		const FVector Pel = HeroDriver->GetSocketLocation(TEXT("pelvis"));
		G->SetActorRotation(FRotator(0.0f, (Pel - G->GetActorLocation()).Rotation().Yaw, 0.0f));
		if (UCharacterMovementComponent* M = G->GetCharacterMovement()) M->GetNavAgentPropertiesRef().bCanCrouch = true;
		G->Crouch();
		SceneCrouchAt = CaptureT;
	}
	if (!bHit && bSceneCrouched && !bSceneCuffed && CaptureT >= SceneCrouchAt + 0.9f)
	{
		bSceneCuffed = true;
		PlaySfx(TEXT("esposas"), FVector::ZeroVector, 1.0f, false);
		SceneBlackAt = CaptureT + 0.8f;
	}
	if (!bSceneBlack && CaptureT >= SceneBlackAt)
	{
		bSceneBlack = true;
		if (PC->PlayerCameraManager) PC->PlayerCameraManager->StartCameraFade(0.0f, 1.0f, 0.6f, FLinearColor::Black, false, true);
		SceneEndAt = CaptureT + 0.7f;
	}
	if (!bSceneThird && !bCaptureDone) SceneCameraTick(DeltaSeconds, C);
	if (bSceneBlack && !bCaptureDone && CaptureT >= SceneEndAt)
	{
		SceneRestore(C);
		CaptureFinish(C);   // en negro: al calabozo (o adonde toque) y vuelve la imagen
		if (bHit) WakeBlurT = 2.4f;   // despiertas con la vista desenfocada
		SceneEndAt = CaptureT;
	}
	if (bCaptureDone && CaptureT >= SceneEndAt + 1.0f)
	{
		bCapturing = false;
		Captor = nullptr;
		SceneKind = ETarsisSceneKind::None;
	}
}

void ATarsisDirector::SceneRagdoll(ACharacter* C)
{
	bSceneRagdoll = true;
	if (!HeroDriver) return;
	HeroDriver->SetCollisionProfileName(TEXT("Ragdoll"));
	HeroDriver->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
	HeroDriver->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	HeroDriver->SetAllBodiesSimulatePhysics(true);
	HeroDriver->WakeAllRigidBodies();
	// sigue cayendo como iba la animacion (la velocidad de la pelvis en los ultimos fotogramas)
	HeroDriver->SetAllPhysicsLinearVelocity(ScenePelvisVel.GetClampedToMaxSize(400.0f));
}

void ATarsisDirector::SceneRestore(ACharacter* C)
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (HeroDriver && C)
	{
		HeroDriver->SetAllBodiesSimulatePhysics(false);
		HeroDriver->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		if (HeroDriver->GetAttachParent() != C->GetCapsuleComponent()) HeroDriver->AttachToComponent(C->GetCapsuleComponent(), FAttachmentTransformRules::KeepWorldTransform);
		HeroDriver->SetAnimationMode(EAnimationMode::AnimationBlueprint);   // el ABP del GASP desde cero
	}
	bSceneHero = false;   // GaspHeroTick vuelve a colocarlo con la capsula
	if (ATarsisGuard* G = Captor)
	{
		if (AAIController* AI = Cast<AAIController>(G->GetController())) AI->StopMovement();
		if (!bSceneGuardFree && bScenePlaying)
		{
			const FVector Root = G->GetMesh()->GetSocketLocation(TEXT("root"));
			G->GetMesh()->SetRelativeTransform(SceneGuardRel);
			G->SetActorLocation(FVector(Root.X, Root.Y, G->GetActorLocation().Z));
		}
		else if (!bScenePlaying) G->GetMesh()->SetRelativeTransform(SceneGuardRel);
		if (G->bIsCrouched) G->UnCrouch();
		G->SceneEnd();
		G->bSceneLock = false;
		G->Hold(1.0f);
	}
	if (PC && SceneCam && PC->GetViewTarget() == SceneCam) PC->SetViewTarget(C);
	if (Arms) Arms->SetVisibility(!bThirdShown, true);
}

void ATarsisDirector::SceneCameraTick(float DeltaSeconds, ACharacter* C)
{
	if (!SceneCam || !HeroDriver) return;
	ATarsisGuard* G = Captor;
	const FVector CamLoc = SceneCam->GetActorLocation();
	FVector WantLoc = CamLoc;
	float Fall = 0.0f;
	if (bScenePlaying)
	{
		const FVector Head = HeroDriver->GetSocketLocation(TEXT("head"));
		WantLoc = Head + FVector(0.0f, 0.0f, 6.0f);
		WantLoc.Z = FMath::Max(WantLoc.Z, SceneGroundZ + 14.0f);
		// tanda B: nunca pegada al guardia (en el derribo su pierna tapaba la imagen)
		if (G)
		{
			FVector Off = WantLoc - G->GetActorLocation();
			Off.Z = 0.0f;
			const float D = Off.Size();
			if (D < CaptureCamMinDist) WantLoc += (D > 1.0f ? Off / D : -G->GetActorForwardVector()) * (CaptureCamMinDist - D);
			// tanda C: ni pegada a su pecho (en el culatazo se echa encima hacia el segundo 1): distancia en 3D al pecho
			if (USkeletalMeshComponent* GM = G->GetMesh())
			{
				const FName ChestBone = GM->GetBoneIndex(TEXT("spine_04")) != INDEX_NONE ? FName(TEXT("spine_04")) : FName(TEXT("spine_03"));
				if (GM->GetBoneIndex(ChestBone) != INDEX_NONE)
				{
					const FVector Chest = GM->GetBoneLocation(ChestBone);
					const float D3 = FVector::Dist(WantLoc, Chest);
					FVector Away = WantLoc - Chest;
					Away.Z = 0.0f;
					if (D3 < CaptureCamMinChest) WantLoc += (Away.Normalize() ? Away : -G->GetActorForwardVector()) * (CaptureCamMinChest - D3);
				}
			}
		}
		Fall = FMath::Clamp((SceneHeadZ0 - Head.Z) / FMath::Max(SceneHeadZ0 - SceneGroundZ - 25.0f, 1.0f), 0.0f, 1.0f);
	}
	// mira al guardia: al pecho de pie y, segun cae, a sus botas
	FVector Aim = CamLoc + SceneCam->GetActorForwardVector() * 100.0f;
	if (G)
	{
		const float GHalf = G->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		const FVector Chest = G->GetActorLocation() + FVector(0.0f, 0.0f, 45.0f);
		const FVector Boots = G->GetActorLocation() - FVector(0.0f, 0.0f, GHalf - 12.0f);
		Aim = FMath::Lerp(Chest, Boots, FMath::SmoothStep(0.2f, 1.0f, Fall));
	}
	FRotator Want = (Aim - WantLoc).Rotation();
	Want.Roll = 72.0f * FMath::SmoothStep(0.35f, 1.0f, Fall);   // de lado en el suelo
	if (Fall > 0.9f && !bSceneImpact) { bSceneImpact = true; SceneShake = FMath::Max(SceneShake, 0.9f); }
	SceneShake = FMath::Max(0.0f, SceneShake - DeltaSeconds * 2.0f);
	const float Amp = SceneShake * 4.0f + Fall * (1.0f - Fall) * 6.0f;
	Want.Pitch += Amp * FMath::PerlinNoise1D(CaptureT * 23.0f);
	Want.Yaw += Amp * FMath::PerlinNoise1D(CaptureT * 19.0f + 7.3f);
	Want.Roll += Amp * 0.6f * FMath::PerlinNoise1D(CaptureT * 17.0f + 3.1f);
	Want.Yaw += SceneBlurW * 1.4f * FMath::Sin(CaptureT * 31.0f);   // golpe: la vista se desdobla
	const FVector NewLoc = bScenePlaying ? FMath::VInterpTo(CamLoc, WantLoc, DeltaSeconds, 20.0f) : CamLoc;
	const FRotator NewRot = FMath::RInterpTo(SceneCam->GetActorRotation(), Want, DeltaSeconds, bScenePlaying ? 10.0f : 7.0f);
	SceneCam->SetActorLocationAndRotation(NewLoc, NewRot);
}

void ATarsisDirector::SceneBlurTick(float DeltaSeconds)
{
	float W = 0.0f;
	if (bCapturing && SceneKind == ETarsisSceneKind::Golpe && bSceneRagdoll) W = FMath::Clamp((CaptureT - SceneRagdollAt) / 0.15f, 0.0f, 1.0f);
	if (WakeBlurT > 0.0f)
	{
		WakeBlurT -= DeltaSeconds;
		W = FMath::Max(W, FMath::Clamp(WakeBlurT / 2.0f, 0.0f, 1.0f));
	}
	SceneBlurW = W;
	if (W <= 0.0f && !ScenePP) return;
	if (!ScenePP)
	{
		// vista borrosa y doble: desenfoque de lo que no esta pegado a los ojos, separacion de colores y vineta
		ScenePP = NewObject<UPostProcessComponent>(this, TEXT("VistaBorrosa"));
		ScenePP->bUnbound = true;
		ScenePP->Priority = 50.0f;
		FPostProcessSettings& S = ScenePP->Settings;
		S.bOverride_DepthOfFieldFocalDistance = true; S.DepthOfFieldFocalDistance = 8.0f;
		S.bOverride_DepthOfFieldFstop = true; S.DepthOfFieldFstop = 0.7f;
		S.bOverride_DepthOfFieldSensorWidth = true; S.DepthOfFieldSensorWidth = 60.0f;
		S.bOverride_SceneFringeIntensity = true; S.SceneFringeIntensity = 5.0f;
		S.bOverride_VignetteIntensity = true; S.VignetteIntensity = 1.1f;
		ScenePP->RegisterComponent();
	}
	ScenePP->BlendWeight = W;
	ScenePP->SetVisibility(W > 0.0f);
}
