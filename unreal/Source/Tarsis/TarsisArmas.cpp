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
// - La mano izquierda va al guardamanos con un IK de dos huesos hecho a mano (RifleLeftHandIK): la pose de Lyra, por las
//   proporciones de las personas, la dejaba en el aire encima del canon.
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
	// tumbado, con una animacion suelta de la persona (caer) o en la escena de la detencion (culatazo), sin pose de fusil
	const bool bOn = RifleRef && RifleBones.Num() > 0 && State != ETarsisGuardState::Down && !bSceneLock && !bGaspSingle && StunT <= 0.0f;
	RifleW = FMath::FInterpConstantTo(RifleW, bOn ? 1.0f : 0.0f, DeltaSeconds, 3.0f);
	if (!RifleRef || RifleW <= 0.001f) return;
	// alerta: apunta; si no, el fusil a la cadera
	const bool bAim = State == ETarsisGuardState::Alert && RifleAimAnim != nullptr;
	if (bAim != bRifleAim)
	{
		bRifleAim = bAim;
		RifleRef->PlayAnimation(bAim ? RifleAimAnim.Get() : RifleIdleAnim.Get(), true);
	}
	// la pose de RifleRef relativa a spine_01, puesta sobre el spine_01 del cuerpo visible
	const FTransform RefRoot = RifleRef->GetSocketTransform(RifleRootBone, RTS_Component);
	const FTransform PoseRoot = Pose->GetBoneTransformByName(RifleRootBone, EBoneSpaces::ComponentSpace);
	for (int32 i = 0; i < RifleBones.Num(); ++i)
	{
		const FName B = RifleBones[i];
		const FTransform Want = RifleRef->GetSocketTransform(B, RTS_Component).GetRelativeTransform(RefRoot) * PoseRoot;
		const FTransform Cur = Pose->GetBoneTransformByName(B, EBoneSpaces::ComponentSpace);
		const float W = RifleW * (RifleBoneIsSpine[i] ? RifleSpineWeight : 1.0f);
		FTransform T = Cur;
		T.SetRotation(FQuat::Slerp(Cur.GetRotation(), Want.GetRotation(), W).GetNormalized());
		T.SetLocation(FMath::Lerp(Cur.GetLocation(), Want.GetLocation(), W));
		Pose->SetBoneTransformByName(B, T, EBoneSpaces::ComponentSpace);
	}
	// el agarre de la mano derecha cambia entre cadera y apuntar (medido en el PC con las dos poses)
	RifleAimW = FMath::FInterpConstantTo(RifleAimW, bRifleAim ? 1.0f : 0.0f, DeltaSeconds, 4.0f);
	const FQuat Grip = FQuat::Slerp(RifleGripRot.Quaternion(), RifleAimGripRot.Quaternion(), RifleAimW);
	Rifle->SetRelativeRotation(Grip);
	if (bRifleLeftIK) RifleLeftHandIK(RifleW);
}

void ATarsisGuard::RifleLeftHandIK(float W)
{
	// IK de dos huesos a mano (ley del coseno), en el espacio de la malla visible: el codo se queda del lado en que estaba
	const FName UpN = ArmBones[1][0], LoN = ArmBones[1][1], HaN = ArmBones[1][2], GripN = ArmBones[0][2];
	if (UpN.IsNone() || LoN.IsNone() || HaN.IsNone() || GripN.IsNone() || W <= 0.01f) return;
	const FTransform Up = Pose->GetBoneTransformByName(UpN, EBoneSpaces::ComponentSpace);
	const FTransform Lo = Pose->GetBoneTransformByName(LoN, EBoneSpaces::ComponentSpace);
	const FTransform Ha = Pose->GetBoneTransformByName(HaN, EBoneSpaces::ComponentSpace);
	// el fusil cuelga de la mano derecha: su transform en el espacio de la malla, sin esperar a que se refresque el adjunto
	const FTransform GripCS = FTransform(Rifle->GetRelativeRotation(), Rifle->GetRelativeLocation()) * Pose->GetBoneTransformByName(GripN, EBoneSpaces::ComponentSpace);
	const FVector A = Up.GetLocation(), B = Lo.GetLocation(), C = Ha.GetLocation();
	const FVector T = FMath::Lerp(C, GripCS.TransformPosition(RifleLeftHand), W);
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
	NHa.SetRotation((Q2 * Q1 * Ha.GetRotation()).GetNormalized());
	NHa.SetLocation(NC);
	Pose->SetBoneTransformByName(UpN, NUp, EBoneSpaces::ComponentSpace);
	Pose->SetBoneTransformByName(LoN, NLo, EBoneSpaces::ComponentSpace);
	Pose->SetBoneTransformByName(HaN, NHa, EBoneSpaces::ComponentSpace);
}
