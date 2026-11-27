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
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
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
#include "EngineUtils.h"

// tanda Q: giro de camara de escena con tope de velocidad (grados/s) y zona muerta (no persigue giros pequenos)
static FRotator TarsisCapTurn(const FRotator& Cur, const FRotator& Want, float Dt, float Speed, float MaxDegS, float DeadZone)
{
	const FRotator Delta = (Want - Cur).GetNormalized();
	if (DeadZone > 0.0f && FMath::Abs(Delta.Yaw) < DeadZone && FMath::Abs(Delta.Pitch) < DeadZone) return Cur;
	FRotator Step = (FMath::RInterpTo(Cur, Want, Dt, Speed) - Cur).GetNormalized();
	const float Cap = MaxDegS * Dt;
	Step.Yaw = FMath::Clamp(Step.Yaw, -Cap, Cap);
	Step.Pitch = FMath::Clamp(Step.Pitch, -Cap, Cap);
	return Cur + Step;
}

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
			// tanda O: con otra camara, el cuerpo de la plantilla (oculto solo para tu vista) se veia blanco y
			// descolocado junto a Cuttlas: oculto mientras tanto (sigue dando sombra)
			if (ACharacter* PCChar = Cast<ACharacter>(PC->GetPawn())) if (PCChar->GetMesh()) PCChar->GetMesh()->SetHiddenInGame(true);
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
			PC->SetControlRotation(TarsisCapTurn(Cur, Want, DeltaSeconds, 2.5f, SceneTurnMaxSpeed, SceneTurnDeadZone));
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
	if (C && C->GetMesh() && C->GetMesh()->bHiddenInGame) C->GetMesh()->SetHiddenInGame(false);   // tanda O
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

// ---------------------------------------------------------------- tanda M: el golpe al fusil, la pareja al reves
// Cuttlas hace la parte _A del empujon parado y el guardia la _V. El guardia no se mueve: su raiz de _V queda donde esta
// (girado hacia ti si la pareja lo pide) y Cuttlas se abalanza en DisarmLungeTime hasta donde empieza su raiz de _A.
// Las dos empiezan ya avanzadas (el contacto llega DisarmLeadIn tras la E); el guardia suelta su parte poco despues del
// contacto, antes de la caida (el traspie lo sigue la reaccion de Lyra) y Cuttlas recupera el control enseguida.
bool ATarsisDirector::DisarmSceneBegin(ATarsisGuard* G)
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!bDisarmAnimRule || !G || !C || !PC || bCapturing || !G->UsesGasp() || !G->GetMesh()) return false;
	if (DSGuard.IsValid()) DisarmSceneEnd();
	// la pareja cuyo atacante viene del lado en que estas tu respecto al guardia
	const FTransform GuardRel = G->GetMesh()->GetRelativeTransform();
	const float GroundZ = G->GetActorLocation().Z - G->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FTransform GuardFrame(FRotator(0.0f, G->GetActorRotation().Yaw + GuardRel.Rotator().Yaw, 0.0f),
		FVector(G->GetActorLocation().X, G->GetActorLocation().Y, GroundZ + GuardRel.GetLocation().Z + G->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()));
	const FVector Local = GuardFrame.InverseTransformPosition(C->GetActorLocation()).GetSafeNormal2D();
	int32 Best = INDEX_NONE;
	float BestDot = -2.0f;
	for (int32 i = 0; i < UE_ARRAY_COUNT(ScenePairs); ++i)
	{
		const FScenePair& Pr = ScenePairs[i];
		if (FCString::Strcmp(Pr.Kind, TEXT("shove")) != 0) continue;
		const FVector Rel = RootAt(Pr.RootV, Pr.YawV).InverseTransformPosition(Pr.RootA).GetSafeNormal2D();
		const float Dot = FVector::DotProduct(Local, Rel);
		if (Dot > BestDot) { BestDot = Dot; Best = i; }
	}
	if (Best == INDEX_NONE) return false;
	const FScenePair& Pr = ScenePairs[Best];
	UAnimSequenceBase* A = LoadPairAnim(Pr, true);
	if (!A) return false;
	DSComp = RootAt(Pr.RootV, Pr.YawV).Inverse() * GuardFrame;
	const FTransform HeroRoot = RootAt(Pr.RootA, Pr.YawA) * DSComp;
	// el guardia: la parte _V del GASP acaba en el suelo (es la entrada al ragdoll) y, cortada, se le veia hundido; en su
	// lugar la reaccion fuerte de Lyra, sin moverlo de su sitio (medido en las capturas de la tanda M)
	DSGuardRel = GuardRel;
	// tanda O: la reaccion (y el golpe) en el contacto, DisarmLeadIn despues de la E (antes reaccionaba al pulsar, antes
	// de que llegaran tus manos): DisarmSceneTick
	bDSHit = false;
	bDSSounded = false;
	bDSGuardOn = false;
	// Cuttlas: se abalanza hasta su sitio, mirando al guardia
	DSLungeFrom = C->GetActorLocation();
	DSLungeTo = FVector(HeroRoot.GetLocation().X, HeroRoot.GetLocation().Y, C->GetActorLocation().Z);
	if (FVector::Dist2D(DSLungeFrom, DSLungeTo) > 260.0f) DSLungeTo = DSLungeFrom;   // muy lejos: sin abalanzarse
	DSYawTo = (G->GetActorLocation() - DSLungeTo).Rotation().Yaw;
	PC->SetIgnoreMoveInput(true);
	bDSHero = false;
	if (HeroDriver && HeroBody && !bSceneHero)
	{
		HeroSceneFrom = HeroDriver->GetComponentTransform();   // tanda O: del sitio de antes al de la pareja, con el abalanzarse
		HeroDriver->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		HeroDriver->PlayAnimation(A, false);
		HeroDriver->SetPosition(FMath::Min(FMath::Max(0.0f, Pr.Hit - DisarmLeadIn), A->GetPlayLength() - 0.05f), false);
		bSceneHero = true;
		bDSHero = true;
	}
	DSGuard = G;
	DST = 0.0f;
	++DisarmScenes;
	DisarmScenePair = FString::Printf(TEXT("shove_%s"), Pr.Dir);
	return true;
}

void ATarsisDirector::DisarmSceneTick(float DeltaSeconds)
{
	ATarsisGuard* G = DSGuard.Get();
	if (!G) return;
	if (bCapturing || G->State == ETarsisGuardState::Down) { DisarmSceneEnd(); return; }
	DST += DeltaSeconds;
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (C && DST <= DisarmLungeTime + DeltaSeconds)
	{
		const float S = FMath::SmoothStep(0.0f, 1.0f, FMath::Clamp(DST / FMath::Max(DisarmLungeTime, 0.01f), 0.0f, 1.0f));
		C->SetActorLocation(FMath::Lerp(DSLungeFrom, DSLungeTo, S), true);
	}
	if (PC)
	{
		FRotator R = PC->GetControlRotation();
		R.Yaw = TarsisCapTurn(R, FRotator(R.Pitch, DSYawTo, 0.0f), DeltaSeconds, 14.0f, SceneTurnMaxSpeed, 0.0f).Yaw;   // tanda Q: con tope
		PC->SetControlRotation(R);
	}
	if (bDSHero && HeroDriver)
	{
		// tanda O: antes saltaba al sitio de la pareja de golpe mientras la capsula aun se abalanzaba
		const float S = FMath::SmoothStep(0.0f, 1.0f, FMath::Clamp(DST / FMath::Max(DisarmLungeTime, 0.01f), 0.0f, 1.0f));
		FTransform X; X.Blend(HeroSceneFrom, DSComp, S);
		HeroDriver->SetWorldTransform(X);
	}
	if (!bDSSounded && DST >= DisarmLeadIn - ImpactSoundLead)
	{
		bDSSounded = true;   // tanda P: en capas, una pizca antes del contacto
		PlayImpact(G->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 1, false, 0, true);
	}
	if (!bDSHit && DST >= DisarmLeadIn)
	{
		bDSHit = true;
		if (C) G->HitReact(G->GetActorLocation() - C->GetActorLocation(), true, TEXT("spine_03"));
		ContactHitStop(G, 1.2f);
		++ContactEvents;
	}
	if (bDSGuardOn && DST >= DisarmLeadIn + DisarmGuardRelease)
	{
		// el guardia suelta su parte donde acabo su raiz y sigue con el traspie
		const FVector Root = G->GetMesh()->GetSocketLocation(TEXT("root"));
		G->GetMesh()->SetRelativeTransform(DSGuardRel);
		G->SetActorLocation(FVector(Root.X, Root.Y, G->GetActorLocation().Z), true);
		G->SceneEnd();
		G->bSceneLock = false;
		bDSGuardOn = false;
		if (C) G->HitReact(G->GetActorLocation() - C->GetActorLocation(), true);
	}
	if (DST >= DisarmLeadIn + FMath::Max(DisarmHeroRelease, DisarmGuardRelease)) DisarmSceneEnd();
}

void ATarsisDirector::DisarmSceneEnd()
{
	ATarsisGuard* G = DSGuard.Get();
	if (G && !bDSHit)
	{
		// se corta antes del contacto: la reaccion igualmente
		bDSHit = true;
		if (ACharacter* C0 = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0))) G->HitReact(G->GetActorLocation() - C0->GetActorLocation(), true);
	}
	if (G && bDSGuardOn)
	{
		const FVector Root = G->GetMesh()->GetSocketLocation(TEXT("root"));
		G->GetMesh()->SetRelativeTransform(DSGuardRel);
		if (G->State != ETarsisGuardState::Down) G->SetActorLocation(FVector(Root.X, Root.Y, G->GetActorLocation().Z), true);
		G->SceneEnd();
		G->bSceneLock = false;
	}
	bDSGuardOn = false;
	if (bDSHero && HeroDriver)
	{
		ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
		if (C && HeroDriver->GetAttachParent() != C->GetCapsuleComponent()) HeroDriver->AttachToComponent(C->GetCapsuleComponent(), FAttachmentTransformRules::KeepWorldTransform);
		HeroDriver->SetAnimationMode(EAnimationMode::AnimationBlueprint);
		bSceneHero = false;   // GaspHeroTick vuelve a colocarlo con la capsula
	}
	bDSHero = false;
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0)) PC->SetIgnoreMoveInput(false);
	DSGuard = nullptr;
}

// ---------------------------------------------------------------- tanda N: el remate con la pareja de derribo del GASP
// La E por la espalda (o al aturdido) ya no tumba al guardia en el sitio: Cuttlas hace la parte _A del derribo parado
// (takedown_stand) y el guardia la _V, colocados como en la detencion (la raiz de _V donde esta el guardia; Cuttlas se
// abalanza hasta su raiz de _A). El guardia queda derribado al instante para la logica (State Down: las pruebas y el
// sigilo no esperan a la animacion), pero su caida la pone la escena: en el segundo en que la _V pasaria a ragdoll
// (Fall), suelta la animacion y cae con fisica. En el golpe (Hit) suena seco, la vista da un tiron y el tiempo va lento
// un instante (SlowMo). Si alguien coge al guardia antes (arrastrarlo), cae ya (TakedownSceneRelease).
bool ATarsisDirector::TakedownSceneBegin(ATarsisGuard* G)
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!bTakedownAnimRule || !G || !C || !PC || bCapturing || !G->UsesGasp() || !G->GetMesh() || G->bRagdoll) return false;
	if (TSGuard.IsValid()) TakedownSceneFall();
	if (DSGuard.IsValid()) DisarmSceneEnd();
	const FTransform GuardRel = G->GetMesh()->GetRelativeTransform();
	const FTransform GuardFrame(FRotator(0.0f, G->GetActorRotation().Yaw + GuardRel.Rotator().Yaw, 0.0f), G->GetActorLocation() + GuardRel.GetLocation());
	const FVector Local = GuardFrame.InverseTransformPosition(C->GetActorLocation()).GetSafeNormal2D();
	int32 Best = INDEX_NONE;
	float BestDot = -2.0f;
	for (int32 i = 0; i < UE_ARRAY_COUNT(ScenePairs); ++i)
	{
		const FScenePair& Pr = ScenePairs[i];
		if (FCString::Strcmp(Pr.Kind, TEXT("takedown")) != 0) continue;
		const FVector Rel = RootAt(Pr.RootV, Pr.YawV).InverseTransformPosition(Pr.RootA).GetSafeNormal2D();
		const float Dot = FVector::DotProduct(Local, Rel);
		if (Dot > BestDot) { BestDot = Dot; Best = i; }
	}
	if (Best == INDEX_NONE) return false;
	const FScenePair& Pr = ScenePairs[Best];
	UAnimSequenceBase* A = LoadPairAnim(Pr, true);
	UAnimSequenceBase* V = LoadPairAnim(Pr, false);
	if (!A || !V) return false;
	TSComp = RootAt(Pr.RootV, Pr.YawV).Inverse() * GuardFrame;
	const FTransform HeroRoot = RootAt(Pr.RootA, Pr.YawA) * TSComp;
	// tanda N2: contra el entorno (muro, mesa, barandilla a menos de WallTakedownDist detras del guardia): mas rapido y
	// mas ruidoso; cae contra eso
	{
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisRemateMuro), false, G);
		Q.AddIgnoredActor(C);
		FHitResult H;
		const FVector Away = (G->GetActorLocation() - C->GetActorLocation()).GetSafeNormal2D();
		const FVector From = G->GetActorLocation() + FVector(0.0f, 0.0f, 10.0f);
		bTSWall = GetWorld()->LineTraceSingleByChannel(H, From, From + Away * WallTakedownDist, ECC_Visibility, Q) && !Cast<ATarsisGuard>(H.GetActor());
	}
	const float LeadIn = bTSWall ? TakedownLeadIn * 0.5f : TakedownLeadIn;
	// las dos partes empiezan avanzadas: el golpe llega TakedownLeadIn despues de la E
	const float T0 = FMath::Max(0.0f, Pr.Hit - LeadIn);
	TSGuardRel = GuardRel;
	G->StopUpperPhysics();   // tanda O: sin el tambaleo encima de la pareja
	G->ScenePlay(V);
	G->GetMesh()->SetWorldTransform(TSComp);
	G->GetMesh()->SetPosition(FMath::Min(T0, V->GetPlayLength() - 0.05f), false);
	G->bSceneFallPending = true;
	TSFallAt = bTSWall ? LeadIn + 0.08f : FMath::Max(Pr.Fall - T0, TakedownLeadIn + 0.1f);
	TSHitAt = LeadIn;
	if (bTSWall) ++WallTakedowns;
	TSEndAt = TSFallAt + 0.25f;
	TSFallDir = (G->GetActorLocation() - C->GetActorLocation()).GetSafeNormal2D();
	// Cuttlas: se abalanza a su sitio mirando al guardia
	TSLungeFrom = C->GetActorLocation();
	TSLungeTo = FVector(HeroRoot.GetLocation().X, HeroRoot.GetLocation().Y, C->GetActorLocation().Z);
	if (FVector::Dist2D(TSLungeFrom, TSLungeTo) > 260.0f) TSLungeTo = TSLungeFrom;
	TSYawTo = (G->GetActorLocation() - TSLungeTo).Rotation().Yaw;
	PC->SetIgnoreMoveInput(true);
	bTSHero = false;
	if (HeroDriver && HeroBody && !bSceneHero)
	{
		HeroSceneFrom = HeroDriver->GetComponentTransform();   // tanda O
		HeroDriver->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		HeroDriver->PlayAnimation(A, false);
		HeroDriver->SetPosition(FMath::Min(T0, A->GetPlayLength() - 0.05f), false);
		bSceneHero = true;
		bTSHero = true;
	}
	TSGuard = G;
	TST = 0.0f;
	bTSFell = bTSHit = false;
	bTSSounded = false;
	++TakedownScenes;
	TakedownScenePair = FString::Printf(TEXT("takedown_%s"), Pr.Dir);
	return true;
}

void ATarsisDirector::TakedownSceneTick(float DeltaSeconds)
{
	ATarsisGuard* G = TSGuard.Get();
	if (!G) return;
	if (bCapturing) { TakedownSceneFall(); TakedownSceneEnd(); return; }
	TST += DeltaSeconds;
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (C && TST <= DisarmLungeTime + DeltaSeconds)
	{
		const float S = FMath::SmoothStep(0.0f, 1.0f, FMath::Clamp(TST / FMath::Max(DisarmLungeTime, 0.01f), 0.0f, 1.0f));
		C->SetActorLocation(FMath::Lerp(TSLungeFrom, TSLungeTo, S), true);
	}
	if (PC)
	{
		FRotator R = PC->GetControlRotation();
		R.Yaw = TarsisCapTurn(R, FRotator(R.Pitch, TSYawTo, 0.0f), DeltaSeconds, 12.0f, SceneTurnMaxSpeed, 0.0f).Yaw;   // tanda Q: con tope
		PC->SetControlRotation(R);
	}
	if (bTSHero && HeroDriver)
	{
		const float S = FMath::SmoothStep(0.0f, 1.0f, FMath::Clamp(TST / FMath::Max(DisarmLungeTime, 0.01f), 0.0f, 1.0f));
		FTransform X; X.Blend(HeroSceneFrom, TSComp, S);
		HeroDriver->SetWorldTransform(X);
	}
	if (!bTSSounded && TST >= TSHitAt - ImpactSoundLead)
	{
		bTSSounded = true;   // tanda P: en capas (con la pared si la hay), una pizca antes del contacto
		PlayImpact(G->GetActorLocation() + FVector(0.0f, 0.0f, 100.0f), 2, bTSWall, 0, true);
	}
	if (!bTSHit && TST >= TSHitAt)
	{
		bTSHit = true;
		if (bTSWall) DuelNoise(G->GetActorLocation() + FVector(0.0f, 0.0f, 100.0f));
		KickT = FMath::Max(KickT, 0.2f);
		ContactHitStop(G, bTSWall ? 2.3f : 2.0f);   // tanda O: parada de golpe en el contacto, luego la camara lenta (P: mas larga)
		++ContactEvents;
		ExchangeHappened(true);
		// tanda Q: una camara lenta por encuentro, y solo si con el remate se acaba (nadie mas en alerta)
		bool bOthers = false;
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It) if (*It != G && It->State == ETarsisGuardState::Alert && !It->bAlly) { bOthers = true; break; }
		if (!bOthers) SlowMo();
	}
	if (!bTSFell && TST >= TSFallAt) TakedownSceneFall();
	if (TST >= TSEndAt) TakedownSceneEnd();
}

void ATarsisDirector::TakedownSceneFall()
{
	ATarsisGuard* G = TSGuard.Get();
	if (!G || bTSFell) return;
	bTSFell = true;
	// suelta la animacion donde va y cae con fisica (o con la caida de la persona si la fisica no corre)
	const FVector Root = G->GetMesh()->GetSocketLocation(TEXT("root"));
	G->bSceneFallPending = false;
	G->SceneEnd();
	G->bSceneLock = false;
	if (G->PhysicsCanRun())
	{
		G->PendingFallDir = TSFallDir * (bTSWall ? 0.3f : 1.0f);   // tanda O: contra la pared se derrumba contra ella (con 2x salia volando por encima)
		G->DriverRel = TSGuardRel;   // al despertar vuelve a su sitio de la capsula, no al de la escena
		G->bDriverRelSaved = true;
		G->StartRagdoll();
	}
	else
	{
		G->GetMesh()->SetRelativeTransform(TSGuardRel);
		G->SetActorLocation(FVector(Root.X, Root.Y, G->GetActorLocation().Z), true);
		G->State = ETarsisGuardState::Patrol;   // KnockOut otra vez, ahora con su caida de siempre
		G->KnockOut();
	}
}

void ATarsisDirector::TakedownSceneEnd()
{
	if (!bTSFell) TakedownSceneFall();
	if (bTSHero && HeroDriver)
	{
		ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
		if (C && HeroDriver->GetAttachParent() != C->GetCapsuleComponent()) HeroDriver->AttachToComponent(C->GetCapsuleComponent(), FAttachmentTransformRules::KeepWorldTransform);
		HeroDriver->SetAnimationMode(EAnimationMode::AnimationBlueprint);
		bSceneHero = false;
	}
	bTSHero = false;
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0)) PC->SetIgnoreMoveInput(false);
	TSGuard = nullptr;
}

// ---------------------------------------------------------------- tanda O: el agarre del duelo
// Antes el agarre no tenia animacion: el guardia seguia apuntando y solo salia el aviso. Ahora la pareja de empujon del
// GASP como en la detencion (la raiz de _V donde esta Cuttlas, el guardia en la de _A): el guardia se echa encima en
// GrabReachSeconds y se queda en el contacto (las manos en ti); Cuttlas (en tercera) hace la _V parada ahi. El forcejeo:
// tirones de GrabJitterAmount s de animacion arriba y abajo, con sacudida. Al soltarte (E) o al acabar, cada uno a lo suyo.
bool ATarsisDirector::GrabSceneBegin(ATarsisGuard* G)
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!G || !C || !G->UsesGasp() || !G->GetMesh() || G->bRagdoll || GSGuard.IsValid()) return false;
	const float HalfH = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FTransform Here(FRotator(0.0f, C->GetActorRotation().Yaw + HeroDriverYaw, 0.0f),
		FVector(C->GetActorLocation().X, C->GetActorLocation().Y, C->GetActorLocation().Z - HalfH - HeroDriverBallZ + 2.0f));
	const FVector Local = Here.InverseTransformPosition(G->GetActorLocation()).GetSafeNormal2D();
	int32 Best = INDEX_NONE;
	float BestDot = -2.0f;
	for (int32 i = 0; i < UE_ARRAY_COUNT(ScenePairs); ++i)
	{
		const FScenePair& Pr = ScenePairs[i];
		if (FCString::Strcmp(Pr.Kind, TEXT("shove")) != 0) continue;
		const FVector Rel = RootAt(Pr.RootV, Pr.YawV).InverseTransformPosition(Pr.RootA).GetSafeNormal2D();
		const float Dot = FVector::DotProduct(Local, Rel);
		if (Dot > BestDot) { BestDot = Dot; Best = i; }
	}
	if (Best == INDEX_NONE) return false;
	const FScenePair& Pr = ScenePairs[Best];
	UAnimSequenceBase* A = LoadPairAnim(Pr, true);
	UAnimSequenceBase* V = LoadPairAnim(Pr, false);
	if (!A) return false;
	GSComp = RootAt(Pr.RootV, Pr.YawV).Inverse() * Here;
	GSGuardRel = G->GetMesh()->GetRelativeTransform();
	GSHit = Pr.Hit;
	// tanda P: la pareja propia (Blender, alineada en el origen: la raiz de Cuttlas en 0, los dos con el mismo sentido)
	if (!GrabGuardAnimPath.IsEmpty())
	{
		if (UAnimSequenceBase* CA = LoadObject<UAnimSequenceBase>(nullptr, *GrabGuardAnimPath))
		{
			A = CA;
			V = GrabHeroAnimPath.IsEmpty() ? nullptr : LoadObject<UAnimSequenceBase>(nullptr, *GrabHeroAnimPath);
			GSComp = Here;
			GSHit = GrabHoldAt + GrabJitterAmount;   // al parar se resta GrabJitterAmount: queda en GrabHoldAt
		}
	}
	bGSSounded = false;
	G->StopUpperPhysics();
	G->ScenePlay(A);
	G->GetMesh()->SetWorldTransform(GSComp);
	G->GetMesh()->SetPosition(FMath::Max(0.0f, GSHit - GrabReachSeconds), false);
	GSHeroMontage = nullptr;
	if (V && HeroDriver && !bSceneHero && HeroDriver->GetAnimationMode() == EAnimationMode::AnimationBlueprint)
	{
		if (UAnimInstance* AI = HeroDriver->GetAnimInstance())
		{
			GSHeroMontage = AI->PlaySlotAnimationAsDynamicMontage(V, TEXT("DefaultSlot"), 0.15f, 0.25f, 1.0f, 1, -1.0f, FMath::Max(0.0f, GSHit - GrabReachSeconds));
		}
	}
	GSGuard = G;
	GST = 0.0f;
	GSJitterT = 0.0f;
	bGSFrozen = false;
	++GrabScenes;
	return true;
}

void ATarsisDirector::GrabSceneTick(float DeltaSeconds)
{
	ATarsisGuard* G = GSGuard.Get();
	if (!G) return;
	GST += DeltaSeconds;
	G->GetMesh()->SetWorldTransform(GSComp);   // el duelo le gira la capsula: la malla se queda en su sitio de la pareja
	UAnimInstance* AI = HeroDriver ? HeroDriver->GetAnimInstance() : nullptr;
	if (!bGSSounded && GST >= GrabReachSeconds - ImpactSoundLead)
	{
		bGSSounded = true;
		if (APawn* PP = UGameplayStatics::GetPlayerPawn(this, 0)) PlayImpact(PP->GetActorLocation() + FVector(0.0f, 0.0f, 110.0f), 1, false, 1, true);
	}
	if (!bGSFrozen && GST >= GrabReachSeconds)
	{
		// las manos encima: parado en el contacto, con su golpe
		bGSFrozen = true;
		G->GetMesh()->SetPlayRate(0.0f);
		GSHit = FMath::Max(0.0f, GSHit - GrabJitterAmount);   // tanda O: justo antes del empujon (despues, Cuttlas ya cae)
		G->GetMesh()->SetPosition(GSHit, false);
		if (AI && GSHeroMontage) { AI->Montage_SetPlayRate(GSHeroMontage, 0.0f); AI->Montage_SetPosition(GSHeroMontage, GSHit); }
		ContactHitStop(G, 0.8f, false);   // tanda P: te agarran a ti
		KickT = FMath::Max(KickT, 0.18f);
		++ContactEvents;
	}
	if (bGSFrozen)
	{
		GSJitterT -= DeltaSeconds;
		if (GSJitterT <= 0.0f)
		{
			// el forcejeo: tirones cortos adelante y atras
			GSJitterT = GrabJitterEvery * FMath::FRandRange(0.8f, 1.25f);
			GSJitterSign = -GSJitterSign;
			// hacia atras desde el contacto, nunca pasado (despues del empujon la pareja ya te tira al suelo)
			const float Pos = FMath::Max(0.0f, GSHit - (GSJitterSign > 0.0f ? 0.0f : GrabJitterAmount * FMath::FRandRange(0.5f, 1.0f)));
			G->GetMesh()->SetPosition(Pos, false);
			if (AI && GSHeroMontage) AI->Montage_SetPosition(GSHeroMontage, Pos);
		}   // tanda Q: el forcejeo ya no sacude la vista
	}
}

void ATarsisDirector::GrabSceneEnd(bool bEscaped)
{
	ATarsisGuard* G = GSGuard.Get();
	if (G)
	{
		// la capsula, donde quedo la raiz de la pareja; la malla vuelve a la capsula (el puente de pose lo suaviza)
		const FVector Root = G->GetMesh()->GetSocketLocation(TEXT("root"));
		G->SceneEnd();
		G->GetMesh()->SetRelativeTransform(GSGuardRel);
		G->bSceneLock = false;
		if (bEscaped) G->SetActorLocation(FVector(Root.X, Root.Y, G->GetActorLocation().Z), true);
	}
	if (HeroDriver && GSHeroMontage)
	{
		if (UAnimInstance* AI = HeroDriver->GetAnimInstance()) AI->Montage_Stop(0.25f, GSHeroMontage);
	}
	GSHeroMontage = nullptr;
	GSGuard = nullptr;
}
