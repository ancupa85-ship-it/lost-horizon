// Lost Horizon: De Profundis - tanda C (2026-11-22): fisica de los guardias.
//
// El guardia del GASP tiene dos cuerpos: el maniqui UEFN oculto que conduce (GetMesh, con el ABP del GASP y
// PA_UEFN_Mannequin) y la persona (GaspBody), que copia su pose con ABP_GenericRetarget; el cuerpo visible (Pose) copia a
// la persona. Asi que la fisica se hace en el maniqui y llega sola a lo que se ve, como la de Cuttlas en la detencion.
// - HitReact: un golpe (el empujon) o el dardo. Reaccion de Lyra segun de donde viene (MM_HitReact_<Dir>_Lgt/Med_01,
//   importadas por tools/unreal/armas.py sobre el esqueleto UEFN) y, de spine_01 hacia arriba, los cuerpos simulados con
//   animacion fisica (UPhysicalAnimationComponent: tiran hacia la pose animada) y un empujon; la mezcla se va apagando.
// - Dormido (KnockOut, por dardo o por la espalda): ragdoll completo. El maniqui se suelta de la capsula y la capsula
//   le sigue (la pelvis) para que los demas encuentren el cuerpo donde ha caido. A los 4 s se duerme (sin coste) salvo
//   si lo arrastras (TarsisDirector::DragTick lo agarra de los hombros con un UPhysicsHandleComponent).
// - Al despertar: el maniqui vuelve a la capsula y al ABP, y el cuerpo visible pasa de la pose tumbada a la animada en
//   WakeBlendSeconds (WakeBlendTick, despues de copiar la pose).
// - Solo cerca del jugador (PhysicsNear): los de lejos caen con la animacion de siempre (y nadie los ve).
// Textos solo en ASCII.
#include "TarsisGuard.h"
#include "TarsisDirector.h"

#include "Animation/AnimSequenceBase.h"
#include "Components/CapsuleComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "PhysicsEngine/PhysicalAnimationComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"

namespace
{
	const FName GPelvis(TEXT("pelvis"));
	const FName GSpine1(TEXT("spine_01"));

	FName FirstBody(const USkeletalMeshComponent* M, std::initializer_list<const TCHAR*> Names)
	{
		for (const TCHAR* N : Names)
		{
			if (M && M->GetBodyInstance(FName(N))) return FName(N);
		}
		return NAME_None;
	}
}

bool ATarsisGuard::PhysicsCanRun() const
{
	const USkeletalMeshComponent* M = GetMesh();
	if (!bPhysicsRule || !GaspBody || !M || !M->GetPhysicsAsset() || !GetWorld()) return false;
	const APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	return !Pl || FVector::Dist(Pl->GetActorLocation(), GetActorLocation()) < PhysicsNear;
}

void ATarsisGuard::LoadHitAnims()
{
	if (bHitAnimsTried) return;
	bHitAnimsTried = true;
	static const TCHAR* Dirs[4] = { TEXT("Front"), TEXT("Back"), TEXT("Left"), TEXT("Right") };
	static const TCHAR* Lvl[2] = { TEXT("Lgt"), TEXT("Med") };
	for (int32 l = 0; l < 2; ++l)
	{
		for (int32 d = 0; d < 4; ++d)
		{
			const FString N = FString::Printf(TEXT("MM_HitReact_%s_%s_01"), Dirs[d], Lvl[l]);
			HitAnims[l * 4 + d] = LoadObject<UAnimSequenceBase>(nullptr, *FString::Printf(TEXT("/Game/Tarsis/Armas/Anims/%s.%s"), *N, *N));
		}
	}
}

FVector ATarsisGuard::PelvisLocation() const
{
	const USkeletalMeshComponent* M = GetMesh();
	if (M && M->GetBoneIndex(GPelvis) != INDEX_NONE) return M->GetBoneLocation(GPelvis);
	return GetActorLocation();
}

FVector ATarsisGuard::LeftHandLocation() const
{
	if (!Pose || ArmBones[1][2].IsNone()) return GetActorLocation();
	return Pose->GetBoneLocationByName(ArmBones[1][2], EBoneSpaces::WorldSpace);
}

void ATarsisGuard::PhysicsBodies(bool bOn)
{
	USkeletalMeshComponent* M = GetMesh();
	if (!M) return;
	if (bOn)
	{
		// cuerpos que chocan con el mundo pero no con personas (ni con su propia capsula) ni con la camara
		M->SetCollisionProfileName(TEXT("Ragdoll"));
		M->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
		M->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	}
	else
	{
		M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	}
}

void ATarsisGuard::HitReact(FVector Dir, bool bHeavy)
{
	USkeletalMeshComponent* M = GetMesh();
	if (!M || !GaspBody || State == ETarsisGuardState::Down || bSceneLock || bRagdoll) return;
	Dir.Z = 0.0f;
	if (!Dir.Normalize()) Dir = -GetActorForwardVector();
	LoadHitAnims();
	// de donde viene el golpe (el contrario de hacia donde va): delante, detras, izquierda o derecha
	const FVector From = -Dir;
	const float Fw = FVector::DotProduct(GetActorForwardVector(), From);
	const float Rt = FVector::DotProduct(GetActorRightVector(), From);
	const int32 Side = Fw > 0.7f ? 0 : (Fw < -0.7f ? 1 : (Rt < 0.0f ? 2 : 3));
	UAnimSequenceBase* A = HitAnims[(bHeavy ? 4 : 0) + Side];
	if (!A) A = HitAnims[Side];
	if (A)
	{
		if (bGaspSingle) GaspRestore();   // la persona vuelve a copiar al maniqui
		M->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		M->PlayAnimation(A, false);
		HitAnimT = A->GetPlayLength();
		HitAnimName = A->GetName();
	}
	// de la cintura para arriba, cuerpos con fisica que tiran hacia la animacion, y el empujon
	if (!PhysicsCanRun()) return;
	if (!PhysAnim)
	{
		PhysAnim = NewObject<UPhysicalAnimationComponent>(this, TEXT("AnimacionFisica"));
		PhysAnim->RegisterComponent();
	}
	PhysAnim->SetSkeletalMeshComponent(M);
	FPhysicalAnimationData D;
	D.bIsLocalSimulation = true;
	D.OrientationStrength = 1100.0f;
	D.AngularVelocityStrength = 110.0f;
	D.PositionStrength = 0.0f;
	D.VelocityStrength = 0.0f;
	PhysAnim->ApplyPhysicalAnimationSettingsBelow(GSpine1, D, true);
	PhysicsBodies(true);
	M->SetAllBodiesBelowSimulatePhysics(GSpine1, true, true);
	M->SetAllBodiesBelowPhysicsBlendWeight(GSpine1, HitBlend, false, true);
	const FName Chest = FirstBody(M, { TEXT("spine_04"), TEXT("spine_03"), TEXT("spine_05"), TEXT("spine_02") });
	if (!Chest.IsNone()) M->AddImpulse(Dir * HitImpulse, Chest, true);
	const FName HeadBody = FirstBody(M, { TEXT("head") });
	if (!HeadBody.IsNone()) M->AddImpulse(Dir * HitImpulse * 0.6f, HeadBody, true);
	HitPhysT = HitSeconds;
}

void ATarsisGuard::DartHit(FVector Dir)
{
	Dir.Z = 0.0f;
	Dir.Normalize();
	if (!PhysicsCanRun()) return;   // lejos: KnockOut cae con la animacion de siempre
	HitReact(Dir, false);
	PendingFallDir = Dir;
	RagdollPendingT = DartFallDelay;
}

void ATarsisGuard::StartRagdoll()
{
	USkeletalMeshComponent* M = GetMesh();
	if (bRagdoll || !M) return;
	if (!bDriverRelSaved && M->GetAttachParent() == GetCapsuleComponent())
	{
		DriverRel = M->GetRelativeTransform();
		bDriverRelSaved = true;
	}
	if (bGaspSingle) GaspRestore();
	HitPhysT = 0.0f;
	RagdollPendingT = -1.0f;
	PhysicsBodies(true);
	// suelto de la capsula: la capsula le seguira a el (PhysicsTick), no al reves
	M->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
	M->SetAllBodiesSimulatePhysics(true);
	M->SetAllBodiesPhysicsBlendWeight(1.0f);
	M->WakeAllRigidBodies();
	// sigue cayendo como iba (andando, o empujado por el dardo)
	M->SetAllPhysicsLinearVelocity((GetVelocity() * 0.7f + PendingFallDir * RagdollPush).GetClampedToMaxSize(500.0f));
	PendingFallDir = FVector::ZeroVector;
	bRagdoll = true;
	bRagdollSlept = false;
	RagdollT = 0.0f;
}

void ATarsisGuard::StopRagdoll(bool bBlend)
{
	USkeletalMeshComponent* M = GetMesh();
	RagdollPendingT = -1.0f;
	if (!bRagdoll || !M) return;
	// la pose tumbada tal como se ve, para pasar de ella a la animada
	WakeFrom.Reset();
	if (bBlend && Pose)
	{
		const int32 N = Pose->GetNumBones();
		WakeFrom.SetNum(N);
		for (int32 i = 0; i < N; ++i) WakeFrom[i] = Pose->GetBoneTransformByName(Pose->GetBoneName(i), EBoneSpaces::WorldSpace);
	}
	const FVector P = PelvisLocation();
	const FVector H = M->GetBoneIndex(TEXT("head")) != INDEX_NONE ? M->GetBoneLocation(TEXT("head")) : P + GetActorForwardVector();
	FVector Face = H - P;
	Face.Z = 0.0f;
	M->SetAllBodiesSimulatePhysics(false);
	PhysicsBodies(false);
	M->AttachToComponent(GetCapsuleComponent(), FAttachmentTransformRules::KeepWorldTransform);
	M->SetRelativeTransform(DriverRel);
	if (M->GetAnimationMode() != EAnimationMode::AnimationBlueprint) M->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	// se levanta donde ha caido, mirando hacia donde quedo la cabeza
	SetActorLocationAndRotation(FVector(P.X, P.Y, GetActorLocation().Z), FRotator(0.0f, Face.IsNearlyZero() ? GetActorRotation().Yaw : Face.Rotation().Yaw, 0.0f));
	bRagdoll = false;
	bRagdollSlept = false;
	bPhysDragged = false;
	WakeT = WakeFrom.Num() > 0 ? WakeBlendSeconds : 0.0f;
}

void ATarsisGuard::PhysicsTick(float DeltaSeconds)
{
	USkeletalMeshComponent* M = GetMesh();
	if (!M) return;
	// la reaccion de Lyra: al acabar, el ABP del GASP otra vez (si sigue de pie)
	if (HitAnimT > 0.0f)
	{
		HitAnimT -= DeltaSeconds;
		if (HitAnimT <= 0.0f && !bRagdoll && State != ETarsisGuardState::Down && !bSceneLock && M->GetAnimationMode() != EAnimationMode::AnimationBlueprint)
		{
			SceneEnd();
		}
	}
	// los cuerpos de la reaccion se apagan poco a poco
	if (HitPhysT > 0.0f && !bRagdoll)
	{
		HitPhysT -= DeltaSeconds;
		if (HitPhysT <= 0.0f)
		{
			HitPhysT = 0.0f;
			M->SetAllBodiesBelowSimulatePhysics(GSpine1, false, true);
			PhysicsBodies(false);
		}
		else M->SetAllBodiesBelowPhysicsBlendWeight(GSpine1, HitBlend * HitPhysT / FMath::Max(HitSeconds, 0.01f), false, true);
	}
	// el dardo: tras la reaccion, se desploma
	if (RagdollPendingT >= 0.0f)
	{
		RagdollPendingT -= DeltaSeconds;
		if (RagdollPendingT < 0.0f && State == ETarsisGuardState::Down) StartRagdoll();
	}
	if (!bRagdoll) return;
	RagdollT += DeltaSeconds;
	// la capsula, encima de la pelvis (los que buscan cuerpos miran donde esta el actor)
	const FVector P = PelvisLocation();
	SetActorLocation(FVector(P.X, P.Y, GetActorLocation().Z));
	// en reposo: a dormir (no cuesta nada), salvo que lo arrastres
	if (bPhysDragged) bRagdollSlept = false;
	else if (!bRagdollSlept && RagdollT > 4.0f && M->GetPhysicsLinearVelocity(GPelvis).Size() < 15.0f)
	{
		M->PutAllRigidBodiesToSleep();
		bRagdollSlept = true;
	}
}

void ATarsisGuard::WakeBlendTick(float DeltaSeconds)
{
	if (WakeT <= 0.0f || !Pose) return;
	WakeT -= DeltaSeconds;
	const int32 N = Pose->GetNumBones();
	if (WakeFrom.Num() != N || WakeT <= 0.0f) { WakeT = 0.0f; WakeFrom.Reset(); return; }
	const float Alpha = FMath::SmoothStep(0.0f, 1.0f, 1.0f - WakeT / FMath::Max(WakeBlendSeconds, 0.01f));
	// primero toda la pose animada (al tocar un padre se mueven los hijos), luego, de padres a hijos, la mezcla
	TArray<FTransform> Cur;
	Cur.SetNum(N);
	for (int32 i = 0; i < N; ++i) Cur[i] = Pose->GetBoneTransformByName(Pose->GetBoneName(i), EBoneSpaces::ComponentSpace);
	const FTransform CompXf = Pose->GetComponentTransform();
	for (int32 i = 0; i < N; ++i)
	{
		FTransform T;
		T.Blend(WakeFrom[i].GetRelativeTransform(CompXf), Cur[i], Alpha);
		Pose->SetBoneTransformByName(Pose->GetBoneName(i), T, EBoneSpaces::ComponentSpace);
	}
}
