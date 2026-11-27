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
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "PhysicsEngine/PhysicalAnimationComponent.h"
#include "PhysicsControlComponent.h"
#include "PhysicsEngine/PhysicsAsset.h"
#include "TimerManager.h"

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
	if (Pl && FVector::Dist(Pl->GetActorLocation(), GetActorLocation()) >= PhysicsNear) return false;
	// tanda N2: como mucho MaxAwakeRagdolls cuerpos con fisica despierta a la vez (con tres se iba a 16 fps)
	if (!bRagdoll)
	{
		int32 Awake = 0, Cap = 2;
		for (TActorIterator<ATarsisDirector> Dt(GetWorld()); Dt; ++Dt) { Cap = Dt->MaxAwakeRagdolls; break; }
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It) if (It->bRagdoll && !It->bRagdollSlept) ++Awake;
		if (Awake >= Cap) return false;
	}
	return true;
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

void ATarsisGuard::PhysAnimRelease()
{
	if (PhysAnim && PhysAnim->GetSkeletalMesh()) PhysAnim->SetSkeletalMeshComponent(nullptr);
}

bool ATarsisGuard::HasPhysicsBodies() const
{
	const USkeletalMeshComponent* M = GetMesh();
	return M && M->Bodies.Num() > 0 && M->GetPhysicsAsset() != nullptr;
}

void ATarsisGuard::PhysicsBodies(bool bOn)
{
	USkeletalMeshComponent* M = GetMesh();
	if (!M) return;
	// sin cuerpos (NoCollision los destruye) la animacion fisica no puede seguir enganchada a la malla
	if (!bOn && !bPhysWarm) PhysAnimRelease();
	if (bOn)
	{
		// cuerpos que chocan con el mundo pero no con personas (ni con su propia capsula) ni con la camara
		M->SetCollisionProfileName(TEXT("Ragdoll"));
		M->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);
		M->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);
	}
	else
	{
		// tanda D: precalentado, los cuerpos se quedan creados (cinematicos, solo fisica): asi el siguiente arranque no
		// los tiene que crear de golpe
		M->SetCollisionEnabled(bPhysWarm ? ECollisionEnabled::PhysicsOnly : ECollisionEnabled::NoCollision);
	}
}

void ATarsisGuard::PhysicsWarm()
{
	// tanda D: el tiron al arrancar la fisica era crear los cuerpos del PA y el componente de animacion fisica la primera
	// vez. Se hace al entrar en el radio de la fisica (PhysicsNear), un guardia por fotograma como mucho
	USkeletalMeshComponent* M = GetMesh();
	if (bPhysWarm || !M || !GaspBody || !M->GetPhysicsAsset() || M->IsRunningParallelEvaluation()) return;
	const double T0 = FPlatformTime::Seconds();
	bPhysWarm = true;
	PhysicsBodies(true);
	M->SetAllBodiesSimulatePhysics(false);
	M->SetCollisionEnabled(ECollisionEnabled::PhysicsOnly);
	if (!PhysAnim)
	{
		PhysAnim = NewObject<UPhysicalAnimationComponent>(this, TEXT("AnimacionFisica"));
		PhysAnim->RegisterComponent();
		PhysAnim->SetSkeletalMeshComponent(M);
	}
	PhysWarmMs = (FPlatformTime::Seconds() - T0) * 1000.0;
}

namespace
{
	// tanda P: el pico de cada reaccion de Lyra (s), en el orden de HitAnims (Lgt F B L R, Med F B L R)
	const float GHitPeak[8] = { 0.20f, 0.36f, 0.17f, 0.50f, 0.17f, 0.30f, 0.23f, 0.29f };
}

void ATarsisGuard::HitReact(FVector Dir, bool bHeavy, FName Bone)
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
	int32 Idx = (bHeavy ? 4 : 0) + Side;
	UAnimSequenceBase* A = HitAnims[Idx];
	if (!A) { Idx = Side; A = HitAnims[Side]; }
	if (A)
	{
		// tanda P: el golpe entra de golpe en la pose de dolor (God of War); la mezcla, para todo lo demas
		if (bHitReactSnapRule) { BridgeT = 0.0f; BridgeFrom.Reset(); }
		else PoseBridge(0.1f);
		if (bGaspSingle) GaspRestore();   // la persona vuelve a copiar al maniqui
		M->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		M->PlayAnimation(A, false);
		const float Start = bHitReactSnapRule ? FMath::Clamp(GHitPeak[Idx] - HitReactPeakLead, 0.0f, A->GetPlayLength() - 0.05f) : 0.0f;
		if (Start > 0.0f) M->SetPosition(Start, false);
		HitAnimT = A->GetPlayLength() - Start;
		HitAnimName = A->GetName();
	}
	// de la cintura para arriba, cuerpos con fisica que tiran hacia la animacion, y el empujon
	if (!PhysicsCanRun()) return;
	PhysicsBodies(true);
	// arreglo del cierre al disparar (tras la tanda G): un guardia recien aparecido (un relevo) o sin precalentar aun no
	// tiene los cuerpos creados; sin ellos no hay reaccion fisica (solo la animacion), en vez de enganchar la animacion
	// fisica a una malla vacia
	if (!HasPhysicsBodies()) return;
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
	// tanda P: la fisica desde el hueso golpeado (la receta de Epic); la cabeza, desde el cuello. Sin hueso, de cintura arriba
	FName Root = GSpine1;
	if (!Bone.IsNone() && StaggerT <= 0.0f)
	{
		const FName Want = Bone == TEXT("head") ? FName(TEXT("neck_01")) : Bone;
		if (M->GetBodyInstance(Want)) Root = Want;
	}
	HitPhysRoot = Root;
	PhysAnim->ApplyPhysicalAnimationSettingsBelow(Root, D, true);
	M->SetAllBodiesBelowSimulatePhysics(Root, true, true);
	M->SetAllBodiesBelowPhysicsBlendWeight(Root, HitBlend, false, true);
	const FName Hit = (!Bone.IsNone() && M->GetBodyInstance(Bone)) ? Bone : FirstBody(M, { TEXT("spine_04"), TEXT("spine_03"), TEXT("spine_05"), TEXT("spine_02") });
	if (!Hit.IsNone()) M->AddImpulse(Dir * HitImpulse * (Root == GSpine1 ? 1.0f : 1.3f), Hit, true);
	const FName HeadBody = FirstBody(M, { TEXT("head") });
	if (!HeadBody.IsNone() && Hit != HeadBody) M->AddImpulse(Dir * HitImpulse * 0.6f, HeadBody, true);
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
	PhysAnimRelease();   // en ragdoll nadie tira hacia la pose animada (y asi no queda enganchada si se destruyen los cuerpos)
	PhysicsBodies(true);
	// suelto de la capsula: la capsula le seguira a el (PhysicsTick), no al reves
	M->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
	M->SetAllBodiesSimulatePhysics(true);
	M->SetAllBodiesPhysicsBlendWeight(1.0f);
	for (FBodyInstance* BI : M->Bodies)
	{
		if (!BI) continue;
		// tanda O: sin salir disparado de lo que solapa, y sin agitarse en el suelo
		BI->SetMaxDepenetrationVelocity(RagdollMaxDepenetration);
		BI->AngularDamping = FMath::Max(BI->AngularDamping, RagdollAngularDamping);
		BI->LinearDamping = FMath::Max(BI->LinearDamping, RagdollLinearDamping);
		BI->UpdateDampingProperties();
	}
	M->WakeAllRigidBodies();
	// sigue cayendo como iba (andando, o empujado por el dardo)
	M->SetAllPhysicsLinearVelocity((GetVelocity() * 0.7f + PendingFallDir * RagdollPush).GetClampedToMaxSize(500.0f));
	// tanda D: de que lado queda el pecho, medido de pie (para saber luego si cae boca arriba o boca abajo)
	FrontSign = FVector::DotProduct(BodyFront(), GetActorForwardVector()) >= 0.0f ? 1.0f : -1.0f;
	PendingFallDir = FVector::ZeroVector;
	// tanda P: al caer, motores flojos que tiran hacia la ultima pose animada los primeros FallControlSeconds (cae
	// con algo de tono, sin hacerse un trapo de golpe); luego se sueltan del todo
	if (bPhysicsControlRule && PhysCtlEnsure())
	{
		PhysCtlClear();
		FPhysicsControlData CD;
		CD.AngularStrength = FallControlStrength;
		CD.AngularDampingRatio = 1.0f;
		CD.LinearStrength = 0.0f;
		PhysCtl->CreateControlsFromSkeletalMeshBelow(M, GPelvis, false, EPhysicsControlType::ParentSpace, CD, TEXT("Caida"));
		PCFallT = FallControlSeconds;
		bPCAny = true;
		++PhysicsControlUses;
	}
	bRagdoll = true;
	bRagdollSlept = false;
	RagdollT = 0.0f;
}

void ATarsisGuard::StopRagdoll(bool bBlend)
{
	PhysCtlClear();   // tanda P
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
	// tanda D: boca arriba se incorpora y se levanta mirando hacia los pies; boca abajo, hacia donde tiene la cabeza
	bLastFaceUp = (BodyFront() * FrontSign).Z > 0.0f;
	FVector Face = bLastFaceUp ? P - H : H - P;
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
	// tanda D: no hay animaciones de levantarse en el GASP: de la pose del suelo a agachado (la mezcla de WakeBlendTick)
	// y de agachado a de pie (el GASP), quieto mientras tanto
	if (bBlend && GaspBody)
	{
		if (UCharacterMovementComponent* CM = GetCharacterMovement()) CM->GetNavAgentPropertiesRef().bCanCrouch = true;
		Crouch();
		GetUpT = GetUpKneelSeconds;
		HoldT = FMath::Max(HoldT, GetUpKneelSeconds + 0.5f);
	}
}

FVector ATarsisGuard::BodyFront() const
{
	// el pecho: de la columna (pelvis a cabeza) por la linea de los hombros
	const USkeletalMeshComponent* M = GetMesh();
	if (!M || M->GetBoneIndex(TEXT("clavicle_l")) == INDEX_NONE || M->GetBoneIndex(TEXT("clavicle_r")) == INDEX_NONE || M->GetBoneIndex(TEXT("head")) == INDEX_NONE) return GetActorForwardVector();
	const FVector Sp = M->GetBoneLocation(TEXT("head")) - M->GetBoneLocation(GPelvis);
	const FVector Sh = M->GetBoneLocation(TEXT("clavicle_l")) - M->GetBoneLocation(TEXT("clavicle_r"));
	return FVector::CrossProduct(Sp, Sh).GetSafeNormal();
}

void ATarsisGuard::PhysicsTick(float DeltaSeconds)
{
	USkeletalMeshComponent* M = GetMesh();
	if (!M) return;
	// tanda D: precalentar al entrar en el radio de la fisica (uno por fotograma en toda la base)
	if (!bPhysWarm && bPhysicsRule && bPhysWarmRule && GaspBody)
	{
		static uint64 GWarmFrame = 0;
		// fuera del tick: en mitad del tick la animacion de la malla puede estar evaluandose en otro hilo, y crear los
		// cuerpos entonces espera a esa tarea (al relevo, creado en partida, lo colgaba). El temporizador del siguiente
		// fotograma corre cuando ya han acabado todos los grupos de tick
		if (GWarmFrame != GFrameCounter && PhysicsCanRun())
		{
			GWarmFrame = GFrameCounter;
			TWeakObjectPtr<ATarsisGuard> Self(this);
			GetWorldTimerManager().SetTimerForNextTick([Self]() { if (Self.IsValid()) Self->PhysicsWarm(); });
		}
	}
	// tanda D: levantandose: agachado un momento (el GASP pasa de agachado a de pie con su transicion)
	if (GetUpT > 0.0f)
	{
		GetUpT -= DeltaSeconds;
		if (GetUpT <= 0.0f && bIsCrouched && !bPetting) UnCrouch();
	}
	// la reaccion de Lyra: al acabar, el ABP del GASP otra vez (si sigue de pie)
	if (HitAnimT > 0.0f)
	{
		HitAnimT -= DeltaSeconds;
		if (HitAnimT <= 0.0f && !bRagdoll && State != ETarsisGuardState::Down && !bSceneLock && M->GetAnimationMode() != EAnimationMode::AnimationBlueprint)
		{
			SceneEnd();
		}
	}
	// tanda O: el tambaleo, con fisica blanda y empujones alternos; al acabar se apaga como una reaccion
	if (StaggerT > 0.0f && !bRagdoll)
	{
		StaggerT -= DeltaSeconds;
		StaggerKickT -= DeltaSeconds;
		if (State == ETarsisGuardState::Down || StaggerT <= 0.0f)
		{
			StaggerT = 0.0f;
			if (bPCStagger)
			{
				// de los motores a la fisica de siempre, que se apaga como una reaccion
				PhysCtlClear();
				M->SetAllBodiesBelowSimulatePhysics(GSpine1, true, true);
				M->SetAllBodiesBelowPhysicsBlendWeight(GSpine1, HitBlend, false, true);
			}
			HitPhysT = HitSeconds;
		}
		else
		{
			if (!bPCStagger) M->SetAllBodiesBelowPhysicsBlendWeight(GSpine1, StaggerBlend, false, true);
			if (StaggerKickT <= 0.0f)
			{
				StaggerKickT = StaggerKickEvery * FMath::FRandRange(0.8f, 1.2f);
				StaggerSide = -StaggerSide;
				const FName Chest = FirstBody(M, { TEXT("spine_04"), TEXT("spine_03"), TEXT("spine_05"), TEXT("spine_02") });
				if (!Chest.IsNone()) M->AddImpulse((GetActorRightVector() * StaggerSide - GetActorForwardVector() * 0.4f) * StaggerImpulse, Chest, true);
			}
		}
	}
	// los cuerpos de la reaccion se apagan poco a poco
	else if (HitPhysT > 0.0f && !bRagdoll)
	{
		HitPhysT -= DeltaSeconds;
		if (HitPhysT <= 0.0f)
		{
			HitPhysT = 0.0f;
			M->SetAllBodiesBelowSimulatePhysics(GSpine1, false, true);
			PhysicsBodies(false);
			HitPhysRoot = GSpine1;
		}
		else M->SetAllBodiesBelowPhysicsBlendWeight(HitPhysRoot, HitBlend * HitPhysT / FMath::Max(HitSeconds, 0.01f), false, true);
	}
	// el dardo: tras la reaccion, se desploma
	if (RagdollPendingT >= 0.0f)
	{
		RagdollPendingT -= DeltaSeconds;
		if (RagdollPendingT < 0.0f && State == ETarsisGuardState::Down) StartRagdoll();
	}
	if (!bRagdoll) return;
	RagdollT += DeltaSeconds;
	if (PCFallT > 0.0f && PhysCtl)
	{
		PCFallT -= DeltaSeconds;
		if (PCFallT <= 0.0f) PhysCtlClear();
		else
		{
			FPhysicsControlData CD;
			CD.AngularStrength = FallControlStrength * PCFallT / FMath::Max(FallControlSeconds, 0.01f);
			CD.AngularDampingRatio = 1.0f;
			CD.LinearStrength = 0.0f;
			PhysCtl->SetControlDatasInSet(TEXT("Caida"), CD);
		}
	}
	// tanda O: si algo lo dispara (salir de una pared), se frena: nunca vuela
	if (RagdollT < 2.5f && !bPhysDragged)
	{
		const FVector V = M->GetPhysicsLinearVelocity(GPelvis);
		if (V.Size() > RagdollMaxSpeed)
		{
			const float K = RagdollMaxSpeed / V.Size();
			for (FBodyInstance* BI : M->Bodies) if (BI) BI->SetLinearVelocity(BI->GetUnrealWorldVelocity() * K, false);
			++RagdollClamps;
		}
	}
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

// ---------------------------------------------------------------- tanda O: puente de pose y parada de golpe
// PoseBridge: la pose que se ve ahora (la de Pose, en mundo) y, en PoseBridgeSeconds, de ella a la nueva (BridgeTick, despues
// de copiar la pose y del fusil). Lo llaman los cambios de animacion (ScenePlay, SceneEnd, HitReact, GaspSingle/Restore).
void ATarsisGuard::PoseBridge(float Seconds)
{
	if (!bPoseBridgeRule || !Pose || bRagdoll || WakeT > 0.0f) return;
	const float Len = Seconds >= 0.0f ? Seconds : PoseBridgeSeconds;
	if (Len <= 0.0f) return;
	const int32 N = Pose->GetNumBones();
	BridgeFrom.SetNum(N);
	for (int32 i = 0; i < N; ++i) BridgeFrom[i] = Pose->GetBoneTransformByName(Pose->GetBoneName(i), EBoneSpaces::WorldSpace);
	BridgeT = BridgeLen = Len;
	++PoseBridges;
}

void ATarsisGuard::BridgeTick(float DeltaSeconds)
{
	if (BridgeT <= 0.0f || !Pose) return;
	const int32 N = Pose->GetNumBones();
	if (bRagdoll || WakeT > 0.0f || BridgeFrom.Num() != N) { BridgeT = 0.0f; BridgeFrom.Reset(); return; }
	if (!HitStopped()) BridgeT -= DeltaSeconds;
	if (BridgeT <= 0.0f) { BridgeT = 0.0f; BridgeFrom.Reset(); return; }
	const float Alpha = FMath::SmoothStep(0.0f, 1.0f, 1.0f - BridgeT / FMath::Max(BridgeLen, 0.01f));
	TArray<FTransform> Cur;
	Cur.SetNum(N);
	for (int32 i = 0; i < N; ++i) Cur[i] = Pose->GetBoneTransformByName(Pose->GetBoneName(i), EBoneSpaces::ComponentSpace);
	const FTransform CompXf = Pose->GetComponentTransform();
	for (int32 i = 0; i < N; ++i)
	{
		FTransform T;
		T.Blend(BridgeFrom[i].GetRelativeTransform(CompXf), Cur[i], Alpha);
		Pose->SetBoneTransformByName(Pose->GetBoneName(i), T, EBoneSpaces::ComponentSpace);
	}
}

void ATarsisGuard::HitStop(float RealSeconds, bool bVictim, float ShakeAmp)
{
	if (RealSeconds <= 0.0f || bRagdoll) return;
	USkeletalMeshComponent* M = GetMesh();
	// tanda P (Sakurai): el que recibe se queda congelado en su pose de dolor y tiembla; el que pega sigue muy despacio
	bHitStopVictim = bVictim;
	HitStopLen = RealSeconds;
	HitShakeNow = bVictim ? (ShakeAmp >= 0.0f ? ShakeAmp : HitStopShake) : 0.0f;
	if (bVictim)
	{
		if (M) M->bPauseAnims = true;
		if (GaspBody) GaspBody->bPauseAnims = true;
	}
	else if (M) M->GlobalAnimRateScale = HitStopAttackerRate;
	HitStopUntil = FPlatformTime::Seconds() + RealSeconds;
	++HitStops;
}

void ATarsisGuard::HitStopTick()
{
	if (HitStopUntil <= 0.0) return;
	const double Now = FPlatformTime::Seconds();
	if (Now < HitStopUntil)
	{
		// el temblor, fuerte al principio y apagandose (la malla visible; la capsula y la logica no se mueven)
		if (bHitStopVictim && Pose && HitShakeNow > 0.0f)
		{
			const float K = FMath::Clamp(float(HitStopUntil - Now) / FMath::Max(HitStopLen, 0.001f), 0.0f, 1.0f);
			Pose->SetRelativeLocation(FVector(FMath::FRandRange(-1.0f, 1.0f), FMath::FRandRange(-1.0f, 1.0f), FMath::FRandRange(-0.3f, 0.3f)) * HitShakeNow * K);
		}
		return;
	}
	HitStopUntil = 0.0;
	if (USkeletalMeshComponent* M = GetMesh()) { M->bPauseAnims = false; M->GlobalAnimRateScale = 1.0f; }
	if (GaspBody) GaspBody->bPauseAnims = false;
	if (Pose) Pose->SetRelativeLocation(FVector::ZeroVector);
}

bool ATarsisGuard::PhysCtlEnsure()
{
	if (!PhysCtl)
	{
		PhysCtl = NewObject<UPhysicsControlComponent>(this, TEXT("ControlFisico"));
		if (PhysCtl) PhysCtl->RegisterComponent();
	}
	return PhysCtl != nullptr;
}

void ATarsisGuard::PhysCtlClear()
{
	// tanda P: se destruye siempre lo creado (antes, al acabar el fundido de la caida, PCFallT ya era 0 y los controles se
	// quedaban: el guardia no se levantaba del todo)
	if (PhysCtl && bPCAny) PhysCtl->DestroyAllControlsAndBodyModifiers();
	bPCAny = false;
	bPCStagger = false;
	PCFallT = 0.0f;
}

void ATarsisGuard::StaggerSway(float Seconds)
{
	USkeletalMeshComponent* M = GetMesh();
	if (!M || bRagdoll || State == ETarsisGuardState::Down || !PhysicsCanRun()) return;
	PhysicsBodies(true);
	if (!HasPhysicsBodies()) return;
	HitPhysRoot = GSpine1;
	// tanda P: con PhysicsControl, motores que tiran hacia la animacion (ragdoll activo) en vez de la animacion fisica
	if (bPhysicsControlRule && PhysCtlEnsure())
	{
		PhysCtlClear();
		PhysAnimRelease();
		FPhysicsControlData CD;
		CD.AngularStrength = StaggerControlStrength;
		CD.AngularDampingRatio = 1.0f;
		CD.LinearStrength = 0.0f;
		PhysCtl->CreateControlsFromSkeletalMeshBelow(M, GSpine1, true, EPhysicsControlType::ParentSpace, CD, TEXT("Tambaleo"));
		PhysCtl->CreateBodyModifiersFromSkeletalMeshBelow(M, GSpine1, true, TEXT("Tambaleo"), FPhysicsControlModifierData());
		bPCStagger = true;
		bPCAny = true;
		++PhysicsControlUses;
		StaggerT = Seconds;
		StaggerKickT = 0.0f;
		HitPhysT = FMath::Max(HitPhysT, 0.01f);
		return;
	}
	if (!PhysAnim)
	{
		PhysAnim = NewObject<UPhysicalAnimationComponent>(this, TEXT("AnimacionFisica"));
		PhysAnim->RegisterComponent();
	}
	PhysAnim->SetSkeletalMeshComponent(M);
	FPhysicalAnimationData D;
	D.bIsLocalSimulation = true;
	D.OrientationStrength = 600.0f;   // mas blanda que la reaccion: se le van los hombros
	D.AngularVelocityStrength = 70.0f;
	D.PositionStrength = 0.0f;
	D.VelocityStrength = 0.0f;
	PhysAnim->ApplyPhysicalAnimationSettingsBelow(GSpine1, D, true);
	M->SetAllBodiesBelowSimulatePhysics(GSpine1, true, true);
	M->SetAllBodiesBelowPhysicsBlendWeight(GSpine1, StaggerBlend, false, true);
	StaggerT = Seconds;
	StaggerKickT = 0.0f;
	HitPhysT = FMath::Max(HitPhysT, 0.01f);
}

void ATarsisGuard::StopUpperPhysics()
{
	USkeletalMeshComponent* M = GetMesh();
	StaggerT = 0.0f;
	if (bPCStagger) PhysCtlClear();
	if (!M || bRagdoll || HitPhysT <= 0.0f) return;
	HitPhysT = 0.0f;
	M->SetAllBodiesBelowSimulatePhysics(GSpine1, false, true);
	PhysicsBodies(false);
}
