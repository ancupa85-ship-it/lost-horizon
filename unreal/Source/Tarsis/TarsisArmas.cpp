// Lost Horizon: De Profundis - tanda B, primer paso (2026-11-21): el fusil de los guardias.
//
// - El M14 (CC0 de Stein Games; tools/unreal/armas.py lo importa en /Game/Tarsis/Armas/M14 con su socket Muzzle) va
//   pegado al hueso de la mano derecha del cuerpo visible (Pose, UPoseableMesh) con RifleGripLoc/Rot.
// - Para que no lo lleve con los brazos de andar desarmado, de cintura para arriba se pone una pose de fusil de Lyra
//   retargeteada a la persona (armas.py: MM_Rifle_Idle_Hipfire_<persona> de ronda, MM_Rifle_Idle_ADS_<persona> en
//   alerta). La hace una copia oculta de la persona (RifleRef) en bucle; cada tick, despues de copiar la pose del GASP
//   al cuerpo visible, los huesos de spine_02 hacia arriba (sin cuello ni cabeza, que mira LookTick) toman la pose de
//   RifleRef relativa a spine_01: el torso sigue a la cadera de la locomocion y los brazos sujetan el fusil. Sin grafo
//   de animacion: Python no puede editar el ABP del GASP y asi no hace falta.
// - Tanda C: el fusil se coloca respecto al hombro derecho (a la cadera, o apuntando con la culata al hombro), se mece
//   al andar, y las dos manos van a el con un IK de dos huesos hecho a mano (RifleArmIK). La pose de Lyra, por las
//   proporciones de las personas, lo dejaba al pecho con los brazos estirados y la izquierda en el aire.
// Textos solo en ASCII.
#include "TarsisGuard.h"

#include "Animation/AnimSequenceBase.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

namespace
{
	const TCHAR* RiflePath = TEXT("/Game/Tarsis/Armas/M14/SM_M14.SM_M14");

	UAnimSequenceBase* LoadRifleAnim(const FString& Name, const FString& Persona)
	{
		const FString N = FString::Printf(TEXT("%s_%s"), *Name, *Persona);
		return LoadObject<UAnimSequenceBase>(nullptr, *FString::Printf(TEXT("/Game/Tarsis/Armas/Anims/%s.%s"), *N, *N));
	}
}

void ATarsisGuard::SetupRifle()
{
	if (!bRifleRule || Rifle || !Pose || !BodyMesh || !GetWorld() || !GetWorld()->IsGameWorld()) return;
	const FName Hand = ArmBones[0][2];
	UStaticMesh* SM = LoadObject<UStaticMesh>(nullptr, RiflePath);
	if (!SM || Hand.IsNone()) return;
	Rifle = NewObject<UStaticMeshComponent>(this, TEXT("Fusil"));
	Rifle->SetStaticMesh(SM);
	Rifle->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Rifle->SetupAttachment(Pose, Hand);
	Rifle->SetRelativeLocationAndRotation(RifleGripLoc, RifleGripRot);
	Rifle->RegisterComponent();
	// la pose de fusil, retargeteada a esta persona (la malla de la persona se llama como ella)
	const FString Persona = BodyMesh->GetName().ToLower();
	RifleIdleAnim = LoadRifleAnim(TEXT("MM_Rifle_Idle_Hipfire"), Persona);
	RifleAimAnim = LoadRifleAnim(TEXT("MM_Rifle_Idle_ADS"), Persona);
	if (!RifleIdleAnim) return;   // fusil en la mano, sin pose (se ve, pero con los brazos de siempre)
	RifleRef = NewObject<USkeletalMeshComponent>(this, TEXT("PoseFusil"));
	RifleRef->SetSkeletalMesh(BodyMesh);
	RifleRef->SetupAttachment(GetRootComponent());
	RifleRef->SetHiddenInGame(true);
	RifleRef->SetCastShadow(false);
	RifleRef->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	RifleRef->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	RifleRef->RegisterComponent();
	RifleRef->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	RifleRef->PlayAnimation(RifleIdleAnim, true);
	// los huesos: todos los que cuelgan de spine_02, menos cuello y cabeza (y lo que cuelga de ellos)
	const FReferenceSkeleton& Ref = BodyMesh->GetRefSkeleton();
	const int32 Root = Ref.FindBoneIndex(TEXT("spine_01"));
	const int32 Spine2 = Ref.FindBoneIndex(TEXT("spine_02"));
	if (Root == INDEX_NONE || Spine2 == INDEX_NONE) return;
	RifleRootBone = TEXT("spine_01");
	// tanda D: la altura de la persona (la del hombro derecho en su pose de referencia) frente a la del maniqui con que se
	// midieron los ajustes del fusil (unos 145 cm): los sitios del fusil y de las manos se escalan con ella
	const int32 Sh = Ref.FindBoneIndex(ArmBones[0][0]);
	if (Sh != INDEX_NONE)
	{
		FTransform T = FTransform::Identity;
		for (int32 b = Sh; b != INDEX_NONE; b = Ref.GetParentIndex(b)) T = T * Ref.GetRefBonePose()[b];
		if (T.GetLocation().Z > 50.0f) RiflePersonaScale = FMath::Clamp(T.GetLocation().Z / RifleRefShoulder, 0.8f, 1.2f);
	}
	for (int32 i = 0; i < Ref.GetNum(); ++i)
	{
		bool bUnder = false, bHead = false;
		for (int32 p = i; p != INDEX_NONE; p = Ref.GetParentIndex(p))
		{
			const FString N = Ref.GetBoneName(p).ToString().ToLower();
			if (N.StartsWith(TEXT("neck")) || N == TEXT("head")) bHead = true;
			if (p == Spine2) { bUnder = true; break; }
		}
		if (!bUnder || bHead) continue;
		const FString N = Ref.GetBoneName(i).ToString().ToLower();
		RifleBones.Add(Ref.GetBoneName(i));
		RifleBoneIsSpine.Add(N.StartsWith(TEXT("spine")));
	}
}

FVector ATarsisGuard::RifleMuzzle() const
{
	if (Rifle && Rifle->DoesSocketExist(TEXT("Muzzle"))) return Rifle->GetSocketLocation(TEXT("Muzzle"));
	return GetActorLocation() + GetActorForwardVector() * 60.0f + FVector(0.0f, 0.0f, 50.0f);
}

void ATarsisGuard::RifleTick(float DeltaSeconds)
{
	if (!Pose || !Rifle) return;
	if (RifleSlungTick(DeltaSeconds)) return;   // tanda D: acariciando al lobo, el fusil a la espalda
	// tumbado, con una animacion suelta de la persona (caer), en la escena de la detencion (culatazo) o en una reaccion
	// a un golpe (tanda C), sin pose de fusil
	const bool bOn = RifleRef && RifleBones.Num() > 0 && State != ETarsisGuardState::Down && !bSceneLock && !bGaspSingle && StunT <= 0.0f && HitAnimT <= 0.0f && !bRagdoll;
	RifleW = FMath::FInterpConstantTo(RifleW, bOn ? 1.0f : 0.0f, DeltaSeconds, 3.0f);
	if (!RifleRef || RifleW <= 0.001f) return;
	// alerta: apunta; si no, el fusil a la cadera
	const bool bAim = State == ETarsisGuardState::Alert && RifleAimAnim != nullptr;
	if (bAim != bRifleAim)
	{
		bRifleAim = bAim;
		RifleRef->PlayAnimation(bAim ? RifleAimAnim.Get() : RifleIdleAnim.Get(), true);
	}
	RifleAimW = FMath::FInterpConstantTo(RifleAimW, bRifleAim ? 1.0f : 0.0f, DeltaSeconds, 4.0f);
	// tanda C: andando, el torso deja pasar mas de la locomocion y el fusil se mece con el paso (sin maniqui rigido)
	const float Speed = GetVelocity().Size2D();
	const float Move = FMath::Clamp(Speed / 170.0f, 0.0f, 1.0f);
	RifleMoveW = FMath::FInterpTo(RifleMoveW, Move, DeltaSeconds, 5.0f);
	RiflePhase = FMath::Fmod(RiflePhase + Speed * DeltaSeconds / FMath::Max(RifleStepLength, 10.0f) * PI, 2.0f * PI);
	const float SpineW = FMath::Lerp(RifleSpineWeight, RifleSpineWeightMoving, RifleMoveW);
	// la pose de RifleRef relativa a spine_01, puesta sobre el spine_01 del cuerpo visible
	const FTransform RefRoot = RifleRef->GetSocketTransform(RifleRootBone, RTS_Component);
	const FTransform PoseRoot = Pose->GetBoneTransformByName(RifleRootBone, EBoneSpaces::ComponentSpace);
	for (int32 i = 0; i < RifleBones.Num(); ++i)
	{
		const FName B = RifleBones[i];
		const FTransform Want = RifleRef->GetSocketTransform(B, RTS_Component).GetRelativeTransform(RefRoot) * PoseRoot;
		const FTransform Cur = Pose->GetBoneTransformByName(B, EBoneSpaces::ComponentSpace);
		const float W = RifleW * (RifleBoneIsSpine[i] ? SpineW : 1.0f);
		FTransform T = Cur;
		T.SetRotation(FQuat::Slerp(Cur.GetRotation(), Want.GetRotation(), W).GetNormalized());
		T.SetLocation(FMath::Lerp(Cur.GetLocation(), Want.GetLocation(), W));
		Pose->SetBoneTransformByName(B, T, EBoneSpaces::ComponentSpace);
	}
	// tanda C: el fusil ya no va donde lo deje la mano de Lyra (con las proporciones de las personas quedaba al pecho y
	// con los brazos estirados): se coloca respecto al hombro derecho (a la cadera, culata bajo la axila; apuntando,
	// culata al hombro y el canon a la altura de la mejilla) y las dos manos van a el con IK
	const FTransform Grip(FQuat::Slerp(RifleGripRot.Quaternion(), RifleAimGripRot.Quaternion(), RifleAimW).GetNormalized(), RifleGripLoc);
	FTransform RifleCS;
	if (bRifleHold && RifleHoldTransform(RifleCS))
	{
		FTransform HandCS = Grip.Inverse() * RifleCS;
		// tanda D: sin estirar el brazo del todo (las personas bajas llegaban justas): si la mano no llega con holgura, el
		// fusil se acerca al hombro lo que falte
		const FVector Sh = Pose->GetBoneTransformByName(ArmBones[0][0], EBoneSpaces::ComponentSpace).GetLocation();
		const float Reach = RifleMaxReach * (FVector::Dist(Sh, Pose->GetBoneTransformByName(ArmBones[0][1], EBoneSpaces::ComponentSpace).GetLocation())
			+ FVector::Dist(Pose->GetBoneTransformByName(ArmBones[0][1], EBoneSpaces::ComponentSpace).GetLocation(), Pose->GetBoneTransformByName(ArmBones[0][2], EBoneSpaces::ComponentSpace).GetLocation()));
		const FVector D = HandCS.GetLocation() - Sh;
		if (Reach > 1.0f && D.Size() > Reach)
		{
			RifleCS.AddToTranslation(-D.GetSafeNormal() * (D.Size() - Reach));
			HandCS = Grip.Inverse() * RifleCS;
			++RifleReachClamps;
		}
		RifleArmIK(0, HandCS.GetLocation(), &HandCS, RifleW);
	}
	// el fusil, donde ha quedado de verdad la mano derecha
	RifleCS = Grip * Pose->GetBoneTransformByName(ArmBones[0][2], EBoneSpaces::ComponentSpace);
	RifleCSNow = RifleCS;
	Rifle->SetRelativeTransform(Grip);
	if (!bRifleLeftIK) return;
	// la izquierda: al guardamanos; o, acariciando al lobo (tanda C), al lomo del lobo con un vaiven
	FVector LeftT = RifleCS.TransformPosition(RifleLeftHand * RiflePersonaScale);
	PetHandW = FMath::FInterpConstantTo(PetHandW, (PetCrouched() && !PetHandWorld.IsNearlyZero()) ? 1.0f : 0.0f, DeltaSeconds, 2.0f);
	if (PetHandW > 0.0f)
	{
		const FVector Pet = Pose->GetComponentTransform().InverseTransformPosition(PetHandWorld);
		LeftT = FMath::Lerp(LeftT, Pet, FMath::SmoothStep(0.0f, 1.0f, PetHandW));
	}
	RifleArmIK(1, LeftT, nullptr, RifleW);
}

bool ATarsisGuard::RifleHoldTransform(FTransform& Out) const
{
	const FName Shoulder = ArmBones[0][0];
	if (Shoulder.IsNone()) return false;
	const FTransform CompXf = Pose->GetComponentTransform();
	const FVector F = CompXf.InverseTransformVectorNoScale(GetActorForwardVector()).GetSafeNormal();
	const FVector R = CompXf.InverseTransformVectorNoScale(GetActorRightVector()).GetSafeNormal();
	const FVector U = CompXf.InverseTransformVectorNoScale(FVector::UpVector).GetSafeNormal();
	const FVector Sh = Pose->GetBoneTransformByName(Shoulder, EBoneSpaces::ComponentSpace).GetLocation();
	const float A = FMath::SmoothStep(0.0f, 1.0f, RifleAimW);
	// el balanceo: sube y baja con cada paso, va de lado a lado con cada zancada y se ladea un poco
	const float K = RifleMoveW * (1.0f - 0.6f * A);
	const float Bob = FMath::Sin(RiflePhase * 2.0f) * RifleSwayBob * K;
	const float Side = FMath::Sin(RiflePhase) * RifleSwaySide * K;
	const float Roll = FMath::Sin(RiflePhase) * RifleSwayRoll * K;
	// tanda F: con alguien al lado, el canon abajo y algo cruzado (sin apuntar)
	const float Tk = FMath::SmoothStep(0.0f, 1.0f, RifleTuckW) * (1.0f - A);
	const FVector Off = (FMath::Lerp(RifleHipButt, RifleAimButt, A) + FVector(4.0f, 0.0f, -2.0f) * Tk + FVector(0.0f, Side, Bob)) * RiflePersonaScale;
	const FVector Butt = Sh + F * Off.X + R * Off.Y + U * Off.Z;
	const float P = FMath::DegreesToRadians(FMath::Lerp(FMath::Lerp(RifleHipPitch, RifleAimPitch, A), RifleTuckPitch, Tk));
	const float Y = FMath::DegreesToRadians(FMath::Lerp(FMath::Lerp(RifleHipYaw, RifleAimYaw, A), RifleTuckYaw, Tk));
	const FVector Barrel = (F * FMath::Cos(P) * FMath::Cos(Y) + R * FMath::Cos(P) * FMath::Sin(Y) + U * FMath::Sin(P)).GetSafeNormal();
	const FVector Up = FQuat(Barrel, FMath::DegreesToRadians(Roll)).RotateVector(U);
	const FQuat Q = FRotationMatrix::MakeFromYZ(Barrel, Up).ToQuat();   // el M14 tiene el canon hacia +Y y arriba +Z
	Out = FTransform(Q, Butt + Barrel * RifleButtBack);
	return true;
}

void ATarsisGuard::RifleArmIK(int32 Side, const FVector& Target, const FTransform* HandCS, float W)
{
	// IK de dos huesos a mano (ley del coseno), en el espacio de la malla visible: el codo se queda del lado en que estaba
	const FName UpN = ArmBones[Side][0], LoN = ArmBones[Side][1], HaN = ArmBones[Side][2];
	if (UpN.IsNone() || LoN.IsNone() || HaN.IsNone() || W <= 0.01f) return;
	const FTransform Up = Pose->GetBoneTransformByName(UpN, EBoneSpaces::ComponentSpace);
	const FTransform Lo = Pose->GetBoneTransformByName(LoN, EBoneSpaces::ComponentSpace);
	const FTransform Ha = Pose->GetBoneTransformByName(HaN, EBoneSpaces::ComponentSpace);
	const FVector A = Up.GetLocation(), B = Lo.GetLocation(), C = Ha.GetLocation();
	const FVector T = FMath::Lerp(C, Target, W);
	const float L1 = FVector::Dist(A, B), L2 = FVector::Dist(B, C);
	FVector Dir = T - A;
	const float D = FMath::Clamp(Dir.Size(), 1.0f, (L1 + L2) * 0.999f);
	if (L1 < 1.0f || L2 < 1.0f || !Dir.Normalize()) return;
	FVector Pole = (B - A) - Dir * FVector::DotProduct(B - A, Dir);
	if (!Pole.Normalize()) Pole = FVector(0.0f, 0.0f, -1.0f);
	const float Along = (L1 * L1 - L2 * L2 + D * D) / (2.0f * D);
	const float H = FMath::Sqrt(FMath::Max(L1 * L1 - Along * Along, 0.0f));
	const FVector NB = A + Dir * Along + Pole * H;
	const FVector NC = A + Dir * D;
	const FQuat Q1 = FQuat::FindBetweenNormals((B - A).GetSafeNormal(), (NB - A).GetSafeNormal());
	const FQuat Q2 = FQuat::FindBetweenNormals(Q1.RotateVector(C - B).GetSafeNormal(), (NC - NB).GetSafeNormal());
	FTransform NUp = Up, NLo = Lo, NHa = Ha;
	NUp.SetRotation((Q1 * Up.GetRotation()).GetNormalized());
	NLo.SetRotation((Q2 * Q1 * Lo.GetRotation()).GetNormalized());
	NLo.SetLocation(NB);
	const FQuat Follow = (Q2 * Q1 * Ha.GetRotation()).GetNormalized();
	NHa.SetRotation(HandCS ? FQuat::Slerp(Follow, HandCS->GetRotation(), W).GetNormalized() : Follow);
	NHa.SetLocation(NC);
	Pose->SetBoneTransformByName(UpN, NUp, EBoneSpaces::ComponentSpace);
	Pose->SetBoneTransformByName(LoN, NLo, EBoneSpaces::ComponentSpace);
	Pose->SetBoneTransformByName(HaN, NHa, EBoneSpaces::ComponentSpace);
}

bool ATarsisGuard::RifleSlungTick(float DeltaSeconds)
{
	// tanda D: antes de agacharse junto al lobo, el fusil a la espalda (cruzado, la boca sobre el hombro derecho); la
	// mano izquierda, libre para el lomo. Al acabar, otra vez a la mano
	const bool bSling = bPetting && (bErrandThere || PetT > 0.0f) && State == ETarsisGuardState::Patrol;
	const FName Hand = ArmBones[0][2];
	if (bSling != bRifleSlung)
	{
		bRifleSlung = bSling;
		if (bSling && !SpineBone.IsNone()) Rifle->AttachToComponent(Pose, FAttachmentTransformRules::KeepWorldTransform, SpineBone);
		else if (!Hand.IsNone()) Rifle->AttachToComponent(Pose, FAttachmentTransformRules::KeepWorldTransform, Hand);
	}
	if (!bRifleSlung) return false;
	RifleW = FMath::FInterpConstantTo(RifleW, 0.0f, DeltaSeconds, 3.0f);
	const FVector F = GetActorForwardVector(), R = GetActorRightVector(), U = FVector::UpVector;
	const FVector Back = Pose->GetBoneTransformByName(SpineBone, EBoneSpaces::WorldSpace).GetLocation() - F * RifleSlingBack * RiflePersonaScale;
	const FVector Barrel = (U * 0.78f + R * 0.62f).GetSafeNormal();
	Rifle->SetWorldTransform(FTransform(FRotationMatrix::MakeFromYZ(Barrel, -F).ToQuat(), Back - Barrel * 30.0f));
	PetHandW = FMath::FInterpConstantTo(PetHandW, (PetCrouched() && !PetHandWorld.IsNearlyZero()) ? 1.0f : 0.0f, DeltaSeconds, 2.0f);
	if (PetHandW > 0.0f) RifleArmIK(1, Pose->GetComponentTransform().InverseTransformPosition(PetHandWorld), nullptr, FMath::SmoothStep(0.0f, 1.0f, PetHandW));
	return true;
}

bool ATarsisGuard::RifleOnBack() const
{
	return bRifleSlung;
}

FVector ATarsisGuard::RifleButt() const
{
	// la culata, en el mundo (para las pruebas y las fotos: al hombro apuntando)
	if (!Pose || !Rifle) return FVector::ZeroVector;
	return Pose->GetComponentTransform().TransformPosition(RifleCSNow.TransformPosition(FVector(0.0f, -RifleButtBack, 0.0f)));
}

FVector ATarsisGuard::RifleShoulder() const
{
	if (!Pose || ArmBones[0][0].IsNone()) return FVector::ZeroVector;
	return Pose->GetBoneLocationByName(ArmBones[0][0], EBoneSpaces::WorldSpace);
}
