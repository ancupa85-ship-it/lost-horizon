#include "TarsisGuard.h"
#include "Animation/BlendSpace.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "TarsisDirector.h"

#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Animation/AnimationAsset.h"
#include "Engine/SkeletalMesh.h"
#include "Components/LocalLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInterface.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/Engine.h"
#include "Engine/Light.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerStart.h"
#include "Kismet/GameplayStatics.h"
#include "AIController.h"
#include "Navigation/PathFollowingComponent.h"
#include "UObject/ConstructorHelpers.h"

ATarsisGuard::ATarsisGuard()
{
	PrimaryActorTick.bCanEverTick = true;
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	AIControllerClass = AAIController::StaticClass();

	bUseControllerRotationYaw = false;
	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->bOrientRotationToMovement = true;
	Move->RotationRate = FRotator(0.0f, 240.0f, 0.0f);
	Move->MaxWalkSpeed = WalkSpeed;
	Move->GetNavMovementProperties()->bUseAccelerationForPaths = true;   // si no, al seguir un camino no gira hacia donde anda (en 5.8 va en NavMovementProperties)

	// cuerpo provisional con formas básicas del motor (luego irá el modelo con animaciones)
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Cyl(TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	static ConstructorHelpers::FObjectFinder<UStaticMesh> Sph(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Cuerpo"));
	Body->SetupAttachment(GetCapsuleComponent());
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Body->SetRelativeScale3D(FVector(0.55f, 0.45f, 1.5f));
	Body->SetRelativeLocation(FVector(0.0f, 0.0f, -15.0f));
	Head = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Cabeza"));
	Head->SetupAttachment(GetCapsuleComponent());
	Head->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Head->SetRelativeScale3D(FVector(0.28f));
	Head->SetRelativeLocation(FVector(6.0f, 0.0f, 72.0f));
	if (Cyl.Succeeded()) Body->SetStaticMesh(Cyl.Object);
	if (Sph.Succeeded()) Head->SetStaticMesh(Sph.Object);

	Mark = CreateDefaultSubobject<UTextRenderComponent>(TEXT("Marca"));
	Mark->SetupAttachment(GetCapsuleComponent());
	Mark->SetRelativeLocation(FVector(0.0f, 0.0f, 125.0f));
	Mark->SetHorizontalAlignment(EHTA_Center);
	Mark->SetWorldSize(60.0f);
	Mark->SetText(FText::FromString(TEXT("?")));
	Mark->SetHiddenInGame(true);
}

void ATarsisGuard::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	SetupBody();
}

// posición de un hueso en la pose de referencia, en espacio de la malla
static FVector RefBonePos(const USkeletalMesh* Mesh, FName Bone)
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

void ATarsisGuard::SetupBody()
{
	USkeletalMeshComponent* M = GetMesh();
	const bool bHasBody = BodyMesh != nullptr;
	Body->SetVisibility(!bHasBody);
	Head->SetVisibility(!bHasBody);
	if (!bHasBody || !M) return;
	M->SetSkeletalMesh(BodyMesh);
	M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	M->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	M->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPose;
	M->SetRelativeLocationAndRotation(FVector::ZeroVector, FRotator::ZeroRotator);
	// Los modelos vienen de glTF y no sabemos de antemano hacia dónde miran ni dónde tienen el suelo:
	// se deduce del esqueleto en reposo. Hacia delante = del tobillo a la punta del pie; suelo = punta del pie.
	const FVector Foot = RefBonePos(BodyMesh, TEXT("foot_l"));
	const FVector Ball = RefBonePos(BodyMesh, TEXT("ball_l"));
	const FVector FootR = RefBonePos(BodyMesh, TEXT("foot_r"));
	const FVector BallR = RefBonePos(BodyMesh, TEXT("ball_r"));
	FVector Fwd = (Ball - Foot) + (BallR - FootR);
	Fwd.Z = 0.0f;
	const float Yaw = Fwd.IsNearlyZero() ? 0.0f : -FMath::RadiansToDegrees(FMath::Atan2(Fwd.Y, Fwd.X));
	const float BallZ = FMath::Min(Ball.Z, BallR.Z);
	const float HalfH = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const float Z = (BallZ == 0.0f && Foot.Z == 0.0f) ? -HalfH : (-HalfH - BallZ + 3.0f);
	M->SetRelativeLocationAndRotation(FVector(0.0f, 0.0f, Z), FRotator(0.0f, Yaw, 0.0f));
	if (IdleAnim)
	{
		M->PlayAnimation(IdleAnim, true);
		CurrentAnim = IdleAnim;
	}
}

bool ATarsisGuard::RebuildBlendSpace(UBlendSpace* BS)
{
#if WITH_EDITOR
	if (!BS) return false;
	BS->Modify();
	BS->ResampleData();   // también valida las muestras (duración, marcas de sincronía)
	BS->MarkPackageDirty();
	return true;
#else
	return false;
#endif
}

void ATarsisGuard::UpdateAnim()
{
	USkeletalMeshComponent* M = GetMesh();
	if (!BodyMesh || !M || State == ETarsisGuardState::Down) return;
	const float Speed = GetVelocity().Size2D();
	// con la mezcla, de quieto a andar sin saltos; apuntar (en alerta y parado) sigue siendo una animación suelta
	if (MoveBlend && !(State == ETarsisGuardState::Alert && Speed <= 15.0f && AimAnim))
	{
		if (CurrentAnim != MoveBlend)
		{
			M->PlayAnimation(MoveBlend, true);
			CurrentAnim = MoveBlend;
		}
		// Las muestras de la mezcla están a su velocidad real (idle 0, andar WalkAnimSpeed, trotar RunAnimSpeed) y la
		// mezcla de dos muestras avanza más o menos a la velocidad de su posición. Por debajo de andar no se mezcla con
		// idle (arrastraría los pies): se anda más despacio; entre andar y trotar se mezcla; por encima se acelera.
		const float Vw = FMath::Max(WalkAnimSpeed, 1.0f);
		const float Vtop = RunAnimSpeed > Vw ? RunAnimSpeed : Vw;
		// girando en el sitio (más de ~40 grados por segundo, parado): da pasos cortos en vez de rotar rígido
		bTurnStepping = Speed < 25.0f && YawRate > 40.0f;
		const float Target = bTurnStepping ? Vw : (Speed < 8.0f ? 0.0f : FMath::Clamp(FMath::Max(Speed, Vw * FMath::Min(Speed / 40.0f, 1.0f)), 0.0f, Vtop));
		if (UAnimSingleNodeInstance* SI = M->GetSingleNodeInstance())
		{
			// la posición en la mezcla se suaviza: aunque la cápsula frene en seco, las piernas no saltan de pose
			BlendPos = FMath::FInterpTo(BlendPos, Target, GetWorld()->GetDeltaSeconds(), 6.0f);
			SI->SetBlendSpacePosition(FVector(BlendPos, 0.0f, 0.0f));
		}
		// ritmo = velocidad de la cápsula / velocidad de la pose de la mezcla, para que el pie apoyado no patine
		if (bTurnStepping) M->SetPlayRate(FMath::Clamp(YawRate / 200.0f, 0.35f, 0.7f));
		else M->SetPlayRate(BlendPos > 20.0f && Speed >= 8.0f ? FMath::Clamp(Speed / BlendPos, 0.4f, RunAnimSpeed > Vw ? 1.6f : 2.6f) : 1.0f);
		return;
	}
	UAnimationAsset* Want = IdleAnim;
	if (Speed > 15.0f && WalkAnim) Want = WalkAnim;
	else if (State == ETarsisGuardState::Alert && AimAnim) Want = AimAnim;
	if (Want && Want != CurrentAnim)
	{
		M->PlayAnimation(Want, true);
		CurrentAnim = Want;
	}
	M->SetPlayRate(Want == WalkAnim ? FMath::Clamp(Speed / FMath::Max(WalkAnimSpeed, 1.0f), 0.5f, 2.6f) : 1.0f);
}

void ATarsisGuard::SetupPose()
{
	USkeletalMeshComponent* M = GetMesh();
	if (!BodyMesh || !M || Pose || !GetWorld() || !GetWorld()->IsGameWorld()) return;
	const FReferenceSkeleton& Ref = BodyMesh->GetRefSkeleton();
	auto Pick = [&Ref](std::initializer_list<const TCHAR*> Names) -> FName
	{
		for (const TCHAR* N : Names) { if (Ref.FindBoneIndex(FName(N)) != INDEX_NONE) return FName(N); }
		return NAME_None;
	};
	HeadBone = Pick({ TEXT("head") });
	NeckBone = Pick({ TEXT("neck_01"), TEXT("neck") });
	SpineBone = Pick({ TEXT("spine_03"), TEXT("spine_02"), TEXT("spine_01") });
	ArmBones[0][0] = Pick({ TEXT("upperarm_r") }); ArmBones[0][1] = Pick({ TEXT("lowerarm_r") }); ArmBones[0][2] = Pick({ TEXT("hand_r") });
	ArmBones[1][0] = Pick({ TEXT("upperarm_l") }); ArmBones[1][1] = Pick({ TEXT("lowerarm_l") }); ArmBones[1][2] = Pick({ TEXT("hand_l") });
	Pose = NewObject<UPoseableMeshComponent>(this, TEXT("CuerpoVisible"));
	Pose->SetupAttachment(M);
	Pose->SetSkinnedAssetAndUpdate(BodyMesh);
	Pose->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Pose->RegisterComponent();
	Pose->CopyPoseFromSkeletalComponent(M);
	// la malla animada ya no se ve, pero sigue evaluando: de ella salen la pose (copiada cada tick) y los pasos
	M->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	M->SetHiddenInGame(true);
	M->SetCastShadow(false);
}

void ATarsisGuard::LookTick(float DeltaSeconds)
{
	// cuánto gira el cuerpo por segundo (UpdateAnim da pasos al girar en el sitio)
	const float Yaw = GetActorRotation().Yaw;
	if (DeltaSeconds > 0.0f)
	{
		YawRate = FMath::FInterpTo(YawRate, FMath::Abs(FMath::FindDeltaAngleDegrees(PrevYaw, Yaw)) / DeltaSeconds, DeltaSeconds, 8.0f);
	}
	PrevYaw = Yaw;
	if (!Pose) return;
	Pose->CopyPoseFromSkeletalComponent(GetMesh());
	// adónde mira la cabeza, respecto al cuerpo: el cuerpo gira despacio y la cabeza se adelanta
	auto Toward = [this](const FVector& P) -> float
	{
		FVector D = P - GetActorLocation();
		D.Z = 0.0f;
		return D.IsNearlyZero() ? 0.0f : FMath::FindDeltaAngleDegrees(GetActorRotation().Yaw, D.Rotation().Yaw);
	};
	float Want = 0.0f;
	float WantLean = 0.0f;
	switch (State)
	{
	case ETarsisGuardState::Suspicious:
	case ETarsisGuardState::Alert:
		Want = Toward(LastSeen);
		break;
	case ETarsisGuardState::Search:
		// buscando: barre con la cabeza a un lado y a otro, algo agachado hacia delante
		Want = 55.0f * FMath::Sin(StateT * 1.7f);
		WantLean = 12.0f;
		break;
	case ETarsisGuardState::Patrol:
		if (!bTowerSentry && WaitT > 0.6f) Want = 45.0f * FMath::Sin((WaitT - 0.6f) * 0.9f);   // parado en su punto: echa un vistazo
		break;
	default:
		break;
	}
	if (bRepairing && RepairLookT > 0.0f) Want = Toward(RepairLook);
	if (StunT > 0.0f) { Want = 25.0f * FMath::Sin(StateT * 7.0f); WantLean = -12.0f; }   // tambaleándose hacia atrás
	if (BodyTarget)
	{
		Want = Toward(BodyTarget->GetActorLocation());
		if (BodyCheckT > 0.0f) WantLean = 30.0f;   // agachado sobre el cuerpo
	}
	if (State == ETarsisGuardState::Down) { Want = 0.0f; LookYaw = 0.0f; Lean = 0.0f; }
	LookTarget = FMath::Clamp(Want, -75.0f, 75.0f);
	LookYaw = FMath::FInterpTo(LookYaw, LookTarget, DeltaSeconds, 4.0f);
	Lean = FMath::FInterpTo(Lean, WantLean, DeltaSeconds, 2.5f);
	if (FMath::Abs(LookYaw) < 0.2f && FMath::Abs(Lean) < 0.2f) return;
	// ejes del guardia en el espacio de la malla (que va girada respecto al actor)
	const FTransform CT = Pose->GetComponentTransform();
	const FVector Up = CT.InverseTransformVectorNoScale(FVector::UpVector);
	const FVector Right = CT.InverseTransformVectorNoScale(GetActorRightVector());
	auto Turn = [this](FName Bone, const FQuat& Q)
	{
		if (Bone.IsNone()) return;
		const FQuat Cur = Pose->GetBoneRotationByName(Bone, EBoneSpaces::ComponentSpace).Quaternion();
		Pose->SetBoneRotationByName(Bone, (Q * Cur).Rotator(), EBoneSpaces::ComponentSpace);
	};
	if (FMath::Abs(Lean) > 0.2f) Turn(SpineBone, FQuat(Right, FMath::DegreesToRadians(Lean)));
	Turn(NeckBone, FQuat(Up, FMath::DegreesToRadians(LookYaw * 0.4f)));
	Turn(HeadBone, FQuat(Up, FMath::DegreesToRadians(LookYaw * 0.6f)));
}

// ---------------------------------------------------------------- gestos (tanda 24)

void ATarsisGuard::PlayGesture(FName Name, float Seconds, FVector Toward)
{
	if (Name.IsNone() || Seconds <= 0.0f) { GestureLeft = 0.0f; return; }
	if (Gesture != Name || GestureLeft <= 0.0f)
	{
		GestureT = 0.0f;
		GestureLog.Add(Name);
		if (GestureLog.Num() > 40) GestureLog.RemoveAt(0);
	}
	Gesture = Name;
	GestureLeft = Seconds;
	GestureDir = Toward;
}

float ATarsisGuard::HandHeight(bool bRight)
{
	const FName Hand = ArmBones[bRight ? 0 : 1][2];
	if (!Pose || Hand.IsNone()) return 0.0f;
	const float Feet = GetActorLocation().Z - GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	return Pose->GetBoneLocationByName(Hand, EBoneSpaces::WorldSpace).Z - Feet;
}

void ATarsisGuard::AimBone(FName Bone, FName Child, const FVector& DirCS, float W)
{
	// gira el hueso para que apunte (hacia su hijo) en la dirección pedida, en el espacio de la malla
	if (!Pose || Bone.IsNone() || Child.IsNone() || W <= 0.001f) return;
	const FVector A = Pose->GetBoneLocationByName(Bone, EBoneSpaces::ComponentSpace);
	const FVector B = Pose->GetBoneLocationByName(Child, EBoneSpaces::ComponentSpace);
	const FVector Cur = (B - A).GetSafeNormal();
	const FVector Want = DirCS.GetSafeNormal();
	if (Cur.IsNearlyZero() || Want.IsNearlyZero()) return;
	const FQuat Q = FQuat::Slerp(FQuat::Identity, FQuat::FindBetweenNormals(Cur, Want), FMath::Clamp(W, 0.0f, 1.0f));
	const FQuat R = Pose->GetBoneRotationByName(Bone, EBoneSpaces::ComponentSpace).Quaternion();
	Pose->SetBoneRotationByName(Bone, (Q * R).Rotator(), EBoneSpaces::ComponentSpace);
}

void ATarsisGuard::GestureTick(float DeltaSeconds)
{
	// Después de LookTick: la pose visible ya es la de la animación con la cabeza girada; aquí se le ponen los brazos.
	// Sin grafo de animación (SingleNode) no hay capas: se apunta cada hueso del brazo hacia donde debe ir. Cada brazo
	// tiene su peso y su dirección suavizada: de un gesto a otro (tender la mano -> leer) el brazo va, no salta.
	static const FName NAlto(TEXT("alto")), NPapeles(TEXT("papeles")), NLeer(TEXT("leer")), NPase(TEXT("pase")), NLona(TEXT("lona")), NManos(TEXT("manos"));
	if (!Pose) return;
	if (GestureLeft > 0.0f) GestureLeft -= DeltaSeconds;
	const bool bCalm = (State == ETarsisGuardState::Patrol || State == ETarsisGuardState::Return) && StunT <= 0.0f
		&& (Gesture == NAlto || GetVelocity().Size2D() < 45.0f);
	// manos arriba (interrogado): es justo mientras esta aturdido
	const bool bOn = GestureLeft > 0.0f && (bCalm || (Gesture == NManos && State != ETarsisGuardState::Down));
	if (!bOn && ArmW[0] <= 0.0f && ArmW[1] <= 0.0f && FMath::Abs(GestureHead) < 0.05f && FMath::Abs(GestureLean) < 0.05f)
	{
		GestureW = 0.0f;
		return;
	}
	GestureT += DeltaSeconds;
	// lo que pide el gesto: hacia dónde van el brazo y el antebrazo de cada lado, en los ejes del guardia
	// (X al frente, Y a su derecha, Z arriba)
	FVector Want[2][2];
	bool bUse[2] = { false, false };
	float HeadPitch = 0.0f, SpineLean = 0.0f;
	if (bOn)
	{
		if (Gesture == NManos)
		{
			// los dos brazos abiertos y los antebrazos arriba
			for (int32 Side = 0; Side < 2; ++Side)
			{
				const float Sg = Side == 0 ? 1.0f : -1.0f;
				bUse[Side] = true;
				Want[Side][0] = FVector(0.1f, 0.85f * Sg, 0.5f);
				Want[Side][1] = FVector(0.05f, 0.15f * Sg, 0.98f);
			}
		}
		else if (Gesture == NAlto)
		{
			// la mano derecha en alto y separada del cuerpo (tanda 25: con el brazo por delante del pecho, de frente y
			// de espaldas la silueta era la misma que sin gesto): el brazo sale hacia su derecha y el antebrazo sube recto
			bUse[0] = true;
			Want[0][0] = FVector(0.2f, 0.8f, 0.55f);
			Want[0][1] = FVector(0.1f, 0.12f, 0.98f);
		}
		else if (Gesture == NPapeles)
		{
			// tiende la mano: el codo algo doblado, el antebrazo al frente
			bUse[0] = true;
			Want[0][0] = FVector(0.7f, 0.25f, -0.65f);
			Want[0][1] = FVector(0.95f, -0.1f, 0.15f);
		}
		else if (Gesture == NLeer)
		{
			// los dos antebrazos delante del pecho y la cabeza baja: mira los papeles
			for (int32 Side = 0; Side < 2; ++Side)
			{
				const float S = Side == 0 ? 1.0f : -1.0f;
				bUse[Side] = true;
				Want[Side][0] = FVector(0.3f, 0.2f * S, -0.92f);
				Want[Side][1] = FVector(0.75f, -0.4f * S, 0.5f);
			}
			HeadPitch = 24.0f;
		}
		else if (Gesture == NLona)
		{
			// levanta la lona con la derecha y se asoma
			bUse[0] = true;
			Want[0][0] = FVector(0.55f, 0.2f, 0.78f);
			Want[0][1] = FVector(0.6f, 0.0f, 0.75f);
			SpineLean = 8.0f;
			HeadPitch = -8.0f;
		}
		else if (Gesture == NPase)
		{
			// da paso: el brazo del lado hacia donde manda, y el antebrazo va y viene de arriba hacia allí
			FVector D = GestureDir - GetActorLocation();
			D.Z = 0.0f;
			D = D.IsNearlyZero() ? GetActorRightVector() : D.GetSafeNormal();
			const FVector L(D | GetActorForwardVector(), D | GetActorRightVector(), 0.0f);
			const int32 Side = L.Y >= 0.0f ? 0 : 1;
			const float S = 0.5f + 0.5f * FMath::Sin(GestureT * 6.5f);
			bUse[Side] = true;
			Want[Side][0] = L * 0.85f + FVector(0.2f, 0.0f, 0.25f);
			Want[Side][1] = FMath::Lerp(FVector(0.0f, 0.0f, 0.9f) + L * 0.3f, L * 0.95f + FVector(0.0f, 0.0f, 0.1f), S);
		}
	}
	const FVector F = GetActorForwardVector(), R = GetActorRightVector();
	const FTransform CT = Pose->GetComponentTransform();
	GestureW = 0.0f;
	for (int32 Side = 0; Side < 2; ++Side)
	{
		if (bUse[Side])
		{
			for (int32 k = 0; k < 2; ++k)
			{
				const FVector N = Want[Side][k].GetSafeNormal();
				ArmDir[Side][k] = ArmW[Side] <= 0.0f ? N : FMath::VInterpTo(ArmDir[Side][k], N, DeltaSeconds, 9.0f);
			}
		}
		ArmW[Side] = FMath::FInterpConstantTo(ArmW[Side], bUse[Side] ? 1.0f : 0.0f, DeltaSeconds, bUse[Side] ? 3.2f : 2.6f);
		GestureW = FMath::Max(GestureW, ArmW[Side]);
		if (ArmW[Side] <= 0.0f) continue;
		const float W = ArmW[Side] * ArmW[Side] * (3.0f - 2.0f * ArmW[Side]);
		for (int32 k = 0; k < 2; ++k)
		{
			const FVector World = F * ArmDir[Side][k].X + R * ArmDir[Side][k].Y + FVector::UpVector * ArmDir[Side][k].Z;
			AimBone(ArmBones[Side][k], ArmBones[Side][k + 1], CT.InverseTransformVectorNoScale(World), W);
		}
	}
	GestureHead = FMath::FInterpTo(GestureHead, HeadPitch, DeltaSeconds, 5.0f);
	GestureLean = FMath::FInterpTo(GestureLean, SpineLean, DeltaSeconds, 5.0f);
	auto Turn = [this](FName Bone, const FQuat& Q)
	{
		if (Bone.IsNone()) return;
		const FQuat Cur = Pose->GetBoneRotationByName(Bone, EBoneSpaces::ComponentSpace).Quaternion();
		Pose->SetBoneRotationByName(Bone, (Q * Cur).Rotator(), EBoneSpaces::ComponentSpace);
	};
	const FVector Right = CT.InverseTransformVectorNoScale(R);
	if (FMath::Abs(GestureLean) > 0.05f) Turn(SpineBone, FQuat(Right, FMath::DegreesToRadians(GestureLean)));
	if (FMath::Abs(GestureHead) > 0.05f)
	{
		Turn(NeckBone, FQuat(Right, FMath::DegreesToRadians(GestureHead * 0.4f)));
		Turn(HeadBone, FQuat(Right, FMath::DegreesToRadians(GestureHead * 0.6f)));
	}
}

void ATarsisGuard::StopGesture()
{
	GestureLeft = 0.0f;
	GestureW = 0.0f;
	ArmW[0] = ArmW[1] = 0.0f;
	GestureHead = GestureLean = 0.0f;
}

// ---------------------------------------------------------------- bastón luminoso (tanda 25)

void ATarsisGuard::HoldBaton(float Seconds)
{
	BatonLeft = FMath::Max(BatonLeft, Seconds);
}

bool ATarsisGuard::BatonOn() const
{
	return Baton && Baton->IsVisible();
}

void ATarsisGuard::BatonTick(float DeltaSeconds)
{
	// Después de GestureTick: el bastón sigue al antebrazo derecho de la pose que se ve, con gesto o sin él. De noche el
	// brazo en alto no se leía (silueta oscura contra fondo oscuro); un bastón rojo encendido sí, y de lejos.
	if (BatonLeft > 0.0f) BatonLeft -= DeltaSeconds;
	const bool bCalm = (State == ETarsisGuardState::Patrol || State == ETarsisGuardState::Return) && StunT <= 0.0f;
	const FName Hand = ArmBones[0][2], Fore = ArmBones[0][1];
	if (BatonLeft <= 0.0f || !bCalm || !Pose || Hand.IsNone() || Fore.IsNone())
	{
		BatonLeft = bCalm ? BatonLeft : 0.0f;      // si deja la ronda (te ve, lo tumban) lo guarda
		if (Baton && Baton->IsVisible()) Baton->SetVisibility(false);
		if (BatonGlow && BatonGlow->IsVisible()) BatonGlow->SetVisibility(false);
		return;
	}
	if (!Baton)
	{
		Baton = NewObject<UStaticMeshComponent>(this, TEXT("Baston"));
		Baton->SetMobility(EComponentMobility::Movable);
		Baton->SetupAttachment(GetRootComponent());
		Baton->SetUsingAbsoluteLocation(true);
		Baton->SetUsingAbsoluteRotation(true);
		Baton->SetUsingAbsoluteScale(true);
		Baton->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder")));
		if (UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Tarsis/Materiales/M_Baston.M_Baston"))) Baton->SetMaterial(0, M);
		Baton->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Baton->SetCastShadow(false);
		Baton->RegisterComponent();
		Baton->SetWorldScale3D(FVector(0.034f, 0.034f, BatonLength / 100.0f));
		// su resplandor: es un componente del guardia, no una luz del nivel, así que no cuenta para LightAt
		BatonGlow = NewObject<UPointLightComponent>(this, TEXT("BastonLuz"));
		BatonGlow->SetMobility(EComponentMobility::Movable);
		BatonGlow->SetupAttachment(GetRootComponent());
		BatonGlow->SetUsingAbsoluteLocation(true);
		BatonGlow->SetIntensityUnits(ELightUnits::Lumens);
		BatonGlow->SetIntensity(BatonLumens);
		BatonGlow->SetAttenuationRadius(280.0f);
		BatonGlow->SetLightColor(FLinearColor(1.0f, 0.16f, 0.05f));
		BatonGlow->SetCastShadows(false);
		BatonGlow->SetVolumetricScatteringIntensity(0.0f);
		BatonGlow->RegisterComponent();
	}
	const FVector H = Pose->GetBoneLocationByName(Hand, EBoneSpaces::WorldSpace);
	const FVector E = Pose->GetBoneLocationByName(Fore, EBoneSpaces::WorldSpace);
	FVector Dir = (H - E).GetSafeNormal();
	if (Dir.IsNearlyZero()) Dir = FVector::UpVector;
	// sale del puño siguiendo el antebrazo
	Baton->SetWorldLocationAndRotation(H + Dir * (BatonLength * 0.5f + 5.0f), FRotationMatrix::MakeFromZ(Dir).Rotator());
	BatonGlow->SetWorldLocation(H + Dir * (BatonLength * 0.6f) + GetActorForwardVector() * 6.0f);
	if (!Baton->IsVisible()) Baton->SetVisibility(true);
	if (!BatonGlow->IsVisible()) BatonGlow->SetVisibility(true);
}

void ATarsisGuard::FootTick(float DeltaSeconds)
{
	// un paso cuando un pie llega al suelo según la animación: el sonido va a compás de las piernas
	if (!Pose || State == ETarsisGuardState::Down) { bFootInit = false; return; }
	USkeletalMeshComponent* M = GetMesh();
	const float Speed = GetVelocity().Size2D();
	const bool bMoving = Speed > 40.0f || bTurnStepping;
	static const FName Feet[2] = { FName(TEXT("ball_l")), FName(TEXT("ball_r")) };
	for (int32 i = 0; i < 2; ++i)
	{
		const float Z = M->GetBoneLocation(Feet[i], EBoneSpaces::ComponentSpace).Z;
		if (!bFootInit) { FootMin[i] = Z; bFootUp[i] = false; continue; }
		FootMin[i] = FMath::Min(FootMin[i] + 3.0f * DeltaSeconds, Z);   // el suelo de la animación (sube despacio por si cambia)
		if (bFootUp[i] && Z < FootMin[i] + 2.5f)
		{
			bFootUp[i] = false;
			if (bMoving)
			{
				++StepsTaken;
				for (TActorIterator<ATarsisDirector> It(GetWorld()); It; ++It) { It->GuardStep(this, Speed > 300.0f); break; }
			}
		}
		else if (!bFootUp[i] && Z > FootMin[i] + 6.0f)
		{
			bFootUp[i] = true;
		}
	}
	bFootInit = true;
}

void ATarsisGuard::BeginPlay()
{
	Super::BeginPlay();
	SetupBody();
	SetupPose();
	PrevYaw = GetActorRotation().Yaw;
	Home = GetActorLocation();
	if (PatrolPoints.Num() == 0)
	{
		PatrolPoints.Add(Home);
	}
	SetState(ETarsisGuardState::Patrol);
	if (bTowerSentry)
	{
		GetCharacterMovement()->DisableMovement();   // se queda en la plataforma, sin caer ni andar
		// tanda 26: arranque fijo. Con FRand el foco salía mirando a un sitio distinto en cada partida (y en cada
		// captura): ni se podía aprender ni dos medidas del mismo punto valían lo mismo
		TowerT = SweepPhase;
		if (TowerLight) LightPitch = TowerLight->GetActorRotation().Pitch;
		if (HasSweepPath())
		{
			const ALight* LA = Cast<ALight>(TowerLight);
			const ULightComponent* LC = LA ? LA->GetLightComponent() : nullptr;
			if (LC && SweepRefDist > 0.0f) { BeamLumens = LC->Intensity; BeamPaint = BeamLumens; }
			SweepAim = SweepPointAt(TowerT);
			AimBeam(0.0f, true);
		}
	}
}

void ATarsisGuard::Alarm(const FVector& Where)
{
	if (bTowerSentry || State == ETarsisGuardState::Alert || State == ETarsisGuardState::Down) return;
	BodyTarget = nullptr;   // una alarma (radio, torre) manda más que ir a mirar un cuerpo
	BodyCheckT = 0.0f;
	LastSeen = Where;
	UnseenT = 0.0f;
	Meter = 1.0f;
	SetState(ETarsisGuardState::Alert);
}

void ATarsisGuard::GoTo(const FVector& Where)
{
	PatrolPoints.Reset();
	PatrolPoints.Add(Where);
	PatrolWaits.Reset();
	PointIndex = 0;
	if (State != ETarsisGuardState::Down) SetState(ETarsisGuardState::Return);
}

void ATarsisGuard::Hold(float Seconds)
{
	HoldT = Seconds;
	if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
}

bool ATarsisGuard::Errand(const FVector& Where, const FVector& Face, float Seconds)
{
	if (bTowerSentry || bAlly || bRepairing || BodyTarget || HoldT > 0.0f || StunT > 0.0f) return false;
	if (State != ETarsisGuardState::Patrol && State != ETarsisGuardState::Return) return false;
	if (State != ETarsisGuardState::Patrol) SetState(ETarsisGuardState::Patrol);
	bErrand = true;
	bErrandThere = false;
	ErrandLoc = Where;
	ErrandFace = Face;
	ErrandT = Seconds;
	WaitT = 0.0f;
	MoveDest = FVector(1e9f);   // que pida el camino nuevo
	return true;
}

void ATarsisGuard::EndErrand()
{
	if (!bErrand) return;
	bErrand = false;
	bErrandThere = false;
	MoveDest = FVector(1e9f);
	if (State == ETarsisGuardState::Patrol) SetState(ETarsisGuardState::Return);   // al punto de ronda más cercano
}

void ATarsisGuard::HearNoise(const FVector& Where)
{
	if (bTowerSentry || bAlly || State == ETarsisGuardState::Alert || State == ETarsisGuardState::Down) return;
	if (bRepairing)
	{
		// el primer ruido: gira la linterna hacia él unos segundos y sigue con el generador.
		// Un segundo ruido en menos de 20 s ya no cuela: deja el generador y va a mirar.
		const float Now = GetWorld()->GetTimeSeconds();
		if (Now - LastRepairNoise > 20.0f)
		{
			LastRepairNoise = Now;
			RepairLook = Where;
			RepairLookT = 4.0f;
			UpdateMark();
			return;
		}
		LastRepairNoise = -100.0f;
		bRepairing = false;
		bNoiseSearch = true;
		LastSeen = Where;
		Meter = FMath::Max(Meter, 0.6f);
		SetState(ETarsisGuardState::Suspicious);
		bInvestigate = true;
		UpdateMark();
		return;
	}
	if (State == ETarsisGuardState::Suspicious && bInvestigate) { LastSeen = Where; return; }   // ya va a mirar: sigue el ruido
	bNoiseSearch = true;
	LastSeen = Where;
	Meter = FMath::Max(Meter, 0.5f);
	SetState(ETarsisGuardState::Suspicious);
	bInvestigate = true;
	UpdateMark();   // el «?» de un ruido sale azulado: te ha oído, no te ha visto
}

bool ATarsisGuard::CanBeTakenDown(const AActor* Who) const
{
	if (!Who || bAlly || State == ETarsisGuardState::Down) return false;   // tanda 37: al centinela de la torre tambien, si has subido (la altura lo decide)   // a un aliado (Ramos) no se le derriba por error
	const FVector D = Who->GetActorLocation() - GetActorLocation();
	// aturdido por un empujón: se le derriba por cualquier lado
	if (StunT > 0.0f) return D.Size2D() <= 170.0f && FMath::Abs(D.Z) <= 120.0f;
	if (D.Size2D() > 160.0f || FMath::Abs(D.Z) > 120.0f) return false;
	// por la espalda: el jugador queda detrás de él (o de lado-atrás); de frente solo si no te ve venir
	return FVector::DotProduct(GetActorForwardVector(), D.GetSafeNormal2D()) < -0.2f;
}

void ATarsisGuard::KnockOut()
{
	if (State == ETarsisGuardState::Down) return;
	if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
	State = ETarsisGuardState::Down;
	StateT = 0.0f;
	DownT = KnockOutTime;
	bNoiseSearch = false;
	StunT = 0.0f;
	BodyTarget = nullptr;
	BodyCheckT = 0.0f;
	KnockLoc = GetActorLocation();
	Meter = 0.0f;
	bFound = false;
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);   // se le puede pasar por encima
	USkeletalMeshComponent* M = GetMesh();
	if (BodyMesh && M)
	{
		if (DownAnim) { M->PlayAnimation(DownAnim, false); CurrentAnim = DownAnim; }
		M->SetPlayRate(1.0f);
	}
	else
	{
		Body->SetRelativeRotation(FRotator(90.0f, 0.0f, 0.0f));   // cilindro tumbado
	}
	UpdateMark();
}

void ATarsisGuard::WakeUp()
{
	GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, ECR_Block);
	Body->SetRelativeRotation(FRotator::ZeroRotator);
	CurrentAnim = nullptr;   // UpdateAnim vuelve a poner la que toque
	LastSeen = GetActorLocation();
	Meter = 0.6f;
	bFound = false;
	bDarted = false;   // al despertar se lo ha quitado él: si no, tras otro derribo a mano se recuperaba el dardo otra vez
	SetState(ETarsisGuardState::Search);   // se levanta buscando a quien le ha tumbado
	for (TActorIterator<ATarsisDirector> It(GetWorld()); It; ++It)
	{
		It->GuardSay(this, TEXT("despierta"));   // voz y subtítulo; el «?» encima dice que busca
		break;
	}
}

void ATarsisGuard::LookForBodies()
{
	if (State == ETarsisGuardState::Alert || bAlly || BodyTarget || StunT > 0.0f) return;
	const FVector Eye = GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* O = *It;
		if (O == this || O->State != ETarsisGuardState::Down || O->bFound) continue;
		const FVector P = O->GetActorLocation();
		const float D = FVector::Dist(Eye, P);
		if (D > ViewDistance * 0.7f) continue;
		if (D > NearDistance && FVector::DotProduct(GetActorForwardVector(), (P - Eye).GetSafeNormal2D()) < FMath::Cos(FMath::DegreesToRadians(ViewHalfAngle))) continue;
		// escondido en la sombra: solo lo ve quien pasa muy cerca
		if (D > 350.0f && LightAt(this, P + FVector(0.0f, 0.0f, 40.0f)) < 0.25f) continue;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisCuerpo), true, this);
		Q.AddIgnoredActor(O);
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, P, ECC_Visibility, Q)) continue;
		O->bFound = true;
		if (bTowerSentry)
		{
			// el de la torre no puede bajar: da la voz desde arriba
			O->DownT = FMath::Min(O->DownT, 6.0f);
			Alarm(P);
			for (TActorIterator<ATarsisDirector> Dt(GetWorld()); Dt; ++Dt)
			{
				Dt->GuardSay(this, TEXT("suelo"), true);
				Dt->CentralSay(TEXT("todos"), Dt->Tx(TEXT("radio_todos"), TEXT("A todas las unidades: {0} esta en el suelo. Hay alguien dentro. Buscadlo."), { O->GuardName }), 3.2f);
				break;
			}
			break;
		}
		// lo ha visto: va a mirarlo, se agacha sobre él y avisa por radio (BodyTick); el caído se despierta pronto
		O->DownT = FMath::Min(O->DownT, 14.0f);
		BodyTarget = O;
		BodyCheckT = 0.0f;
		MoveDest = FVector(1e9f);
		Mark->SetHiddenInGame(false);
		Mark->SetText(FText::FromString(TEXT("?")));
		Mark->SetTextRenderColor(FColor(255, 210, 58));
		for (TActorIterator<ATarsisDirector> Dt(GetWorld()); Dt; ++Dt)
		{
			Dt->GuardSay(this, TEXT("cuerpo"));   // «¿ese de ahí está en el suelo?»: va a mirarlo; mientras se agacha, aún puedes irte
			break;
		}
		break;
	}
}

void ATarsisGuard::BodyTick(float DeltaSeconds, APawn* Player, float V)
{
	// si te ve mientras tanto, va a por ti
	if (Meter >= 1.0f && V > 0.0f && Player)
	{
		BodyTarget = nullptr;
		BodyCheckT = 0.0f;
		LastSeen = Player->GetActorLocation();
		SetState(ETarsisGuardState::Alert);
		return;
	}
	// se ha levantado antes de que llegara: da la alarma igual
	if (!BodyTarget || BodyTarget->State != ETarsisGuardState::Down)
	{
		const FVector P = BodyTarget ? BodyTarget->GetActorLocation() : GetActorLocation();
		BodyTarget = nullptr;
		BodyCheckT = 0.0f;
		Alarm(P);
		return;
	}
	const FVector P = BodyTarget->GetActorLocation();
	if (BodyCheckT <= 0.0f && !Near2D(P, 130.0f))
	{
		Walk(P, RunSpeed * 0.6f);
		return;
	}
	if (BodyCheckT <= 0.0f)
	{
		if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
	}
	FaceTowards(P, DeltaSeconds);
	BodyCheckT += DeltaSeconds;   // agachado sobre él (LookTick inclina la espalda)
	if (BodyCheckT < 2.0f) return;
	ATarsisGuard* O = BodyTarget;
	BodyTarget = nullptr;
	BodyCheckT = 0.0f;
	for (TActorIterator<ATarsisDirector> Dt(GetWorld()); Dt; ++Dt)
	{
		Dt->GuardSay(this, TEXT("suelo"), true);
		Dt->CentralSay(TEXT("todos"), Dt->Tx(TEXT("radio_todos"), TEXT("A todas las unidades: {0} esta en el suelo. Hay alguien dentro. Buscadlo."), { O->GuardName }), 3.2f);
		break;
	}
	Alarm(P);
}

void ATarsisGuard::Stun(float Seconds)
{
	if (State == ETarsisGuardState::Down || bTowerSentry) return;
	StunT = Seconds;
	BodyTarget = nullptr;
	BodyCheckT = 0.0f;
	bRepairing = false;
	if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
	Mark->SetHiddenInGame(false);
	Mark->SetText(FText::FromString(TEXT("?!")));
	Mark->SetTextRenderColor(FColor(255, 150, 60));
}

// ---- tanda 26: el foco de la torre sigue un recorrido por el suelo ----
// La vuelta es: parada en un punto (si la tiene), tramo recto hasta el siguiente, y así. Cerrado: 0,1..N-1 y otra vez 0.
// Ida y vuelta: 0,1..N-1,N-2..1 y otra vez 0. Todo sale del tiempo, sin estado: dos partidas hacen lo mismo.
void ATarsisGuard::SweepSequence(TArray<int32>& Out) const
{
	const int32 N = SweepPath.Num();
	for (int32 i = 0; i < N; ++i) Out.Add(i);
	if (!bSweepLoop) for (int32 i = N - 2; i >= 1; --i) Out.Add(i);
}

float ATarsisGuard::SweepPeriod() const
{
	if (SweepPath.Num() < 2) return 0.0f;
	TArray<int32> S;
	SweepSequence(S);
	const float Speed = FMath::Max(10.0f, SweepSpeed);
	float T = 0.0f;
	for (int32 k = 0; k < S.Num(); ++k)
	{
		const int32 A = S[k], B = S[(k + 1) % S.Num()];
		T += (SweepStops.IsValidIndex(A) ? FMath::Max(0.0f, SweepStops[A]) : 0.0f) + FVector::Dist(SweepPath[A], SweepPath[B]) / Speed;
	}
	return T;
}

FVector ATarsisGuard::SweepPointAt(float T) const
{
	if (SweepPath.Num() == 0) return GetActorLocation();
	if (SweepPath.Num() < 2) return SweepPath[0];
	const float Period = SweepPeriod();
	if (Period <= KINDA_SMALL_NUMBER) return SweepPath[0];
	T = FMath::Fmod(T, Period);
	if (T < 0.0f) T += Period;
	TArray<int32> S;
	SweepSequence(S);
	const float Speed = FMath::Max(10.0f, SweepSpeed);
	for (int32 k = 0; k < S.Num(); ++k)
	{
		const int32 A = S[k], B = S[(k + 1) % S.Num()];
		const float Stop = SweepStops.IsValidIndex(A) ? FMath::Max(0.0f, SweepStops[A]) : 0.0f;
		if (T < Stop) return SweepPath[A];
		T -= Stop;
		const float Leg = FVector::Dist(SweepPath[A], SweepPath[B]) / Speed;
		if (T < Leg) return FMath::Lerp(SweepPath[A], SweepPath[B], T / FMath::Max(Leg, KINDA_SMALL_NUMBER));
		T -= Leg;
	}
	return SweepPath[0];
}

// segundo de la vuelta en el que el recorrido pasa más cerca de P (para retomarlo donde pilla, sin dar un salto)
float ATarsisGuard::SweepTimeNear(const FVector& P) const
{
	const float Period = SweepPeriod();
	float Best = 0.0f, BestD = TNumericLimits<float>::Max();
	for (float T = 0.0f; T < Period; T += 0.25f)
	{
		const float D = FVector::DistSquared2D(SweepPointAt(T), P);
		if (D < BestD) { BestD = D; Best = T; }
	}
	return Best;
}

bool ATarsisGuard::CallBeam(const FVector& Where, float Seconds)
{
	if (!bTowerSentry || !HasSweepPath() || State != ETarsisGuardState::Patrol || HoldT > 0.0f) return false;
	if (FVector::Dist2D(Where, GetActorLocation()) > BeamCallRadius) return false;
	BeamCall = Where;
	BeamCallT = FMath::Max(BeamCallT, Seconds);
	return true;
}

// apunta el foco al punto del suelo SweepAim y ajusta lo que pinta según lo lejos que alumbra
void ATarsisGuard::AimBeam(float DeltaSeconds, bool bSnap)
{
	if (!TowerLight) return;
	const FVector LP = TowerLight->GetActorLocation();
	const FVector Dir = (SweepAim - LP).GetSafeNormal();
	if (Dir.IsNearlyZero()) return;
	const FRotator Want = Dir.Rotation();
	TowerLight->SetActorRotation(FRotator(Want.Pitch, Want.Yaw, 0.0f));
	if (BeamLumens <= 0.0f || SweepRefDist <= 0.0f) return;
	ALight* LA = Cast<ALight>(TowerLight);
	ULightComponent* LC = LA ? LA->GetLightComponent() : nullptr;
	if (!LC) return;
	// lo que alumbra de verdad: si en medio hay un camión o un contenedor, la distancia es hasta él (para no quemarlo)
	float D = FVector::Dist(LP, SweepAim);
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisHaz), false, this);
	Q.AddIgnoredActor(TowerLight);
	FHitResult Hit;
	if (GetWorld()->LineTraceSingleByChannel(Hit, LP + Dir * 150.0f, SweepAim, ECC_Visibility, Q)) D = FVector::Dist(LP, Hit.ImpactPoint);
	// la luz que llega cae con el cuadrado de la distancia: se compensa, con tope por los dos lados
	const float Want2 = BeamLumens * FMath::Clamp(FMath::Square(D / SweepRefDist), 0.35f, 2.5f);
	BeamPaint = bSnap ? Want2 : FMath::FInterpTo(BeamPaint, Want2, DeltaSeconds, 4.0f);
	LC->SetIntensity(BeamPaint);
}

void ATarsisGuard::TowerTick(float DeltaSeconds, APawn* Player, float V)
{
	if (State == ETarsisGuardState::Search || State == ETarsisGuardState::Return)
	{
		SetState(ETarsisGuardState::Patrol);   // tras una captura todos vuelven; el de la torre ya está en su sitio
	}
	const bool bPath = HasSweepPath();
	// adónde quiere ir la mancha del foco y a qué paso (cm/s) cuando deja su recorrido
	FVector Target = SweepAim;
	float Chase = 0.0f;
	if (State == ETarsisGuardState::Alert)
	{
		// te sigue con la vista y con el foco mientras te vea; si te pierde, vuelve a barrer
		if (bPath) { Target = LastSeen; Chase = 1400.0f; }
		else FaceTowards(LastSeen, DeltaSeconds * 1.5f);
		if (UnseenT > 5.0f) { Meter = 0.5f; SetState(ETarsisGuardState::Suspicious); }
	}
	else
	{
		if (Meter >= 1.0f)
		{
			SetState(ETarsisGuardState::Alert);
			BeamCallT = 0.0f;
			// da la voz: los dos guardias de suelo más cercanos vienen corriendo a donde te ha visto
			TArray<ATarsisGuard*> Ground;
			for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
			{
				if (!It->bTowerSentry) Ground.Add(*It);
			}
			Ground.Sort([this](const ATarsisGuard& A, const ATarsisGuard& B)
			{
				return FVector::DistSquared2D(A.GetActorLocation(), LastSeen) < FVector::DistSquared2D(B.GetActorLocation(), LastSeen);
			});
			for (int32 i = 0; i < FMath::Min(2, Ground.Num()); ++i) Ground[i]->Alarm(LastSeen);
		}
		else if (State == ETarsisGuardState::Suspicious)
		{
			// le ha parecido ver algo: el foco se para y va hacia allí, despacio (se le ve venir)
			if (bPath) { Target = LastSeen; Chase = 700.0f; }
			else FaceTowards(LastSeen, DeltaSeconds);
			BeamCallT = 0.0f;
			if (Meter <= 0.0f) SetState(ETarsisGuardState::Patrol);
		}
		else
		{
			if (Meter > 0.3f) { SetState(ETarsisGuardState::Suspicious); }
			if (!bPath)
			{
				TowerT += DeltaSeconds;
				const float Yaw = TowerYaw + FMath::Sin(TowerT * 0.42f) * TowerSweep;
				SetActorRotation(FMath::RInterpTo(GetActorRotation(), FRotator(0.0f, Yaw, 0.0f), DeltaSeconds, 3.0f));
			}
			else if (BeamCallT > 0.0f)
			{
				// alarma abajo: el foco acude al sitio y se queda un rato
				BeamCallT -= DeltaSeconds;
				Target = BeamCall;
				Chase = 1000.0f;
			}
			else
			{
				if (bSweepAway)
				{
					// vuelve de mirar otra cosa: retoma el recorrido por el punto que le queda más cerca
					TowerT = SweepTimeNear(SweepAim);
					bSweepAway = false;
				}
				// va hacia el punto que toca; mientras no lo alcance (vuelve de lejos), el recorrido le espera
				const FVector Next = SweepPointAt(TowerT);
				if (FVector::DistSquared2D(SweepAim, Next) < FMath::Square(250.0f)) TowerT += DeltaSeconds;
				SweepAim = FMath::VInterpTo(SweepAim, Next, DeltaSeconds, 5.0f);
			}
		}
	}
	if (bPath)
	{
		if (Chase > 0.0f)
		{
			bSweepAway = true;
			SweepAim = FMath::VInterpConstantTo(SweepAim, Target, DeltaSeconds, Chase);
		}
		FaceTowards(SweepAim, DeltaSeconds);
		AimBeam(DeltaSeconds, false);
	}
	else if (TowerLight)
	{
		TowerLight->SetActorRotation(FRotator(LightPitch, GetActorRotation().Yaw, 0.0f));
	}
}

void ATarsisGuard::SetState(ETarsisGuardState NewState)
{
	// tanda 26: cuando uno de abajo da la alarma, el foco de la torre que lo tenga a mano acude a ese sitio
	if (NewState == ETarsisGuardState::Alert && State != ETarsisGuardState::Alert && !bTowerSentry && !bAlly && GetWorld())
	{
		const FVector Where = LastSeen.IsZero() ? GetActorLocation() : LastSeen;
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (It->bTowerSentry) It->CallBeam(Where, It->BeamCallSeconds);
		}
	}
	// tanda 43: el que te pierde deja marcado el sitio y llama a un companero (lo decide el director)
	if (NewState == ETarsisGuardState::Search && State == ETarsisGuardState::Alert && !bTowerSentry && !bAlly && GetWorld())
	{
		for (TActorIterator<ATarsisDirector> Dt(GetWorld()); Dt; ++Dt) { Dt->LostPlayer(this, LastSeen.IsZero() ? GetActorLocation() : LastSeen); break; }
	}
	if (NewState != ETarsisGuardState::Alert) { bRadioCall = false; bHasCover = false; AimT = 0.0f; }
	if (NewState == ETarsisGuardState::Alert || NewState == ETarsisGuardState::Patrol || NewState == ETarsisGuardState::Down) bNoiseSearch = false;
	State = NewState;
	StateT = 0.0f;
	bRepairing = false;
	if (NewState == ETarsisGuardState::Down) ShowTorch(false);
	if (NewState != ETarsisGuardState::Suspicious) { bInvestigate = false; bShadow = false; bWaitBuddy = false; }
	if (NewState == ETarsisGuardState::Patrol)
	{
		bDarkChecked = false;
		bEscort = false;
		if (bDarkTorch) { bDarkTorch = false; SetFlashlight(false); }
	}
	if (NewState != ETarsisGuardState::Patrol) { bErrand = false; bErrandThere = false; }   // un recado solo dura mientras nada le llame la atención
	WaitT = 0.0f;
	GetCharacterMovement()->MaxWalkSpeed = (State == ETarsisGuardState::Alert) ? RunSpeed : WalkSpeed;
	// arrancar y frenar poco a poco al andar (sin tirones); en alerta, reacción rápida
	GetCharacterMovement()->MaxAcceleration = (State == ETarsisGuardState::Alert) ? 1200.0f : 320.0f;
	GetCharacterMovement()->BrakingDecelerationWalking = (State == ETarsisGuardState::Alert) ? 1200.0f : 320.0f;
	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		AI->StopMovement();
	}
	bNoPath = false;
	UpdateMark();
}

void ATarsisGuard::UpdateMark()
{
	const bool bAlert = State == ETarsisGuardState::Alert;
	const bool bShow = bAlert || State == ETarsisGuardState::Suspicious || State == ETarsisGuardState::Search;
	Mark->SetHiddenInGame(!bShow);
	Mark->SetText(FText::FromString(bAlert ? TEXT("!") : TEXT("?")));
	Mark->SetTextRenderColor(bAlert ? FColor(255, 59, 47) : (bInvestigate ? FColor(120, 200, 255) : (bShadow ? FColor(205, 170, 255) : FColor(255, 210, 58))));   // ruido azulado, sombra malva, vista amarillo
}

bool ATarsisGuard::Near2D(const FVector& Dest, float Radius) const
{
	return FVector::Dist2D(GetActorLocation(), Dest) < Radius;
}

void ATarsisGuard::Walk(const FVector& Dest, float Speed)
{
	GetCharacterMovement()->MaxWalkSpeed = Speed;
	// con mapa de navegación (MapaNavegacion, lo pone tools/unreal/guardias.py) rodea paredes y vallas;
	// si no hay camino, va en línea recta como antes
	if (AAIController* AI = Cast<AAIController>(GetController()))
	{
		const bool bIdle = AI->GetMoveStatus() == EPathFollowingStatus::Idle;
		if (bIdle || FVector::DistSquared2D(MoveDest, Dest) > FMath::Square(60.0f))
		{
			MoveDest = Dest;
			const EPathFollowingRequestResult::Type R = AI->MoveToLocation(Dest, 30.0f, false, true, true, false);
			bNoPath = (R == EPathFollowingRequestResult::Failed);
		}
		if (!bNoPath) return;
	}
	FVector Dir = Dest - GetActorLocation();
	Dir.Z = 0.0f;
	if (Dir.SizeSquared() > 1.0f)
	{
		AddMovementInput(Dir.GetSafeNormal(), 1.0f);
	}
}

void ATarsisGuard::FaceTowards(const FVector& Dest, float DeltaSeconds)
{
	FVector Dir = Dest - GetActorLocation();
	Dir.Z = 0.0f;
	if (Dir.IsNearlyZero()) return;
	const FRotator Want = Dir.Rotation();
	SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), FRotator(0.0f, Want.Yaw, 0.0f), DeltaSeconds, 200.0f));
}

// Tanda 25: lo que se pinta y lo que cuenta para el sigilo van por separado en las luces fuertes de fuera. Con los
// lúmenes de antes (farola 3000, foco de torre 8000, linterna 2500) el suelo bajo cada luz salía quemado y el resto
// negro; ahora se pintan diez veces más flojas (etiqueta «luz_fuerte» en el actor; las linternas, siempre) y para el
// sigilo cuentan lo mismo que contaban. Las luces con la etiqueta «decorado» (el resplandor de relleno de cada farola,
// tools/unreal/cielo.py) no cuentan nada.
static const float StrongLightBoost = 10.0f;
static const FName NStrongLight(TEXT("luz_fuerte"));
static const FName NDecorLight(TEXT("decorado"));

// lo que aporta una luz local al punto: 0 si queda fuera de su radio o de su cono, o si algo hace sombra
// FixedLumens: lúmenes de sigilo de un foco de torre con recorrido (lo que pinta cambia con la distancia; lo que cuenta, no)
static float LightContribution(const UWorld* World, const ULocalLightComponent* L, const FVector& Point, const AActor* Owner, FCollisionQueryParams& Q, bool bStrong, float FixedLumens = -1.0f, const AActor* Ignore2 = nullptr)
{
	if (!L || !L->IsVisible() || L->Intensity <= 0.0f) return 0.0f;
	const float Lumens = FixedLumens > 0.0f ? FixedLumens : L->Intensity;
	const FVector LP = L->GetComponentLocation();
	const float D = FVector::Dist(LP, Point);
	const float R = L->AttenuationRadius;
	if (D >= R) return 0.0f;
	float F = FMath::Square(1.0f - D / R);
	if (const USpotLightComponent* S = Cast<USpotLightComponent>(L))
	{
		const float CosA = FVector::DotProduct(S->GetForwardVector(), (Point - LP).GetSafeNormal());
		const float CosOut = FMath::Cos(FMath::DegreesToRadians(S->OuterConeAngle));
		if (CosA < CosOut) return 0.0f;
		F *= 1.5f;   // dentro de un foco (torre, farola, linterna) se ve de lejos
	}
	// las luces están en lúmenes: una farola (3000 de sigilo; se pinta con 300) cuenta como 1 a su pie
	F *= FMath::Clamp(Lumens * (bStrong ? StrongLightBoost : 1.0f) / 3000.0f, 0.2f, 2.0f);
	if (F < 0.02f) return 0.0f;
	Q.ClearIgnoredSourceObjects();   // ClearIgnoredActors está obsoleto en 5.8
	if (Owner) Q.AddIgnoredActor(Owner);
	if (Ignore2) Q.AddIgnoredActor(Ignore2);
	FHitResult Hit;
	if (World->LineTraceSingleByChannel(Hit, LP, Point, ECC_Visibility, Q) && FVector::Dist(Hit.ImpactPoint, Point) > 40.0f)
	{
		return 0.0f;   // algo hace sombra entre la luz y el punto
	}
	return F;
}

// focos de torre con recorrido: cuentan con sus lúmenes de sigilo, no con lo que pintan en ese momento (cambia con la
// distancia). Se recogen una vez por medida
typedef TArray<TPair<const AActor*, float>, TInlineAllocator<4>> FTarsisBeams;

static void CollectBeams(const UWorld* World, FTarsisBeams& Out)
{
	for (TActorIterator<ATarsisGuard> It(World); It; ++It)
	{
		if (It->bTowerSentry && It->BeamLumens > 0.0f && It->TowerLight) Out.Emplace(It->TowerLight.Get(), It->BeamLumens);
	}
}

// luces que pintan menos de lo que cuentan (los faros del camión, ajuste 26b): sus lúmenes de sigilo, apuntados aparte
static TMap<TWeakObjectPtr<const AActor>, float> GStealthLumens;

void ATarsisGuard::SetStealthLumens(const AActor* LightActor, float Lumens)
{
	for (auto It = GStealthLumens.CreateIterator(); It; ++It) { if (!It.Key().IsValid()) It.RemoveCurrent(); }
	if (!LightActor) return;
	if (Lumens > 0.0f) GStealthLumens.Add(TWeakObjectPtr<const AActor>(LightActor), Lumens);
	else GStealthLumens.Remove(TWeakObjectPtr<const AActor>(LightActor));
}

static float BeamLumensOf(const FTarsisBeams& Beams, const AActor* LightActor)
{
	for (const TPair<const AActor*, float>& B : Beams) if (B.Key == LightActor) return B.Value;
	if (GStealthLumens.Num() > 0)
	{
		if (const float* Fixed = GStealthLumens.Find(TWeakObjectPtr<const AActor>(LightActor))) return *Fixed;
	}
	return -1.0f;
}

// toda la luz que llega a un punto, sin tope. Ignore: actor que no hace sombra (el propio jugador al medir la suya)
static const float TorchStealthLumens = 2500.0f;   // lo que cuenta una linterna para el sigilo, pinte lo que pinte

static float GDayOpen = 0.0f;
static float GDayRoofed = 0.0f;
void ATarsisGuard::SetDayAmbient(float Open, float Roofed) { GDayOpen = Open; GDayRoofed = Roofed; }

static float LightSum(const UWorld* World, const FVector& Point, const AActor* Ignore, bool bTorches = true)
{
	float Sum = 0.12f;   // luna y cielo: de noche siempre se ve una silueta de cerca
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisLuz), false);
	if (GDayOpen > 0.0f)
	{
		// tanda 42, de dia: a cielo abierto se te ve como bajo una farola; bajo techo, penumbra
		FHitResult Roof;
		Sum = World->LineTraceSingleByChannel(Roof, Point + FVector(0.0f, 0.0f, 60.0f), Point + FVector(0.0f, 0.0f, 3000.0f), ECC_Visibility, Q) ? GDayRoofed : GDayOpen;
	}
	FTarsisBeams Beams;
	CollectBeams(World, Beams);
	for (TActorIterator<ALight> It(World); It; ++It)
	{
		if (It->ActorHasTag(NDecorLight)) continue;
		Sum += LightContribution(World, Cast<ULocalLightComponent>(It->GetLightComponent()), Point, *It, Q, It->ActorHasTag(NStrongLight), BeamLumensOf(Beams, *It), Ignore);
	}
	// linternas de los guardias
	if (!bTorches) return Sum;
	for (TActorIterator<ATarsisGuard> It(World); It; ++It)
	{
		if (It->HasFlashlightOn()) Sum += LightContribution(World, It->FlashlightComp(), Point, *It, Q, false, TorchStealthLumens, Ignore);
	}
	return Sum;
}

float ATarsisGuard::LightAt(const UObject* WorldContext, FVector Point)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!World) return 1.0f;
	return FMath::Clamp(LightSum(World, Point, nullptr), 0.0f, 1.0f);
}

float ATarsisGuard::AmbientAt(const UObject* WorldContext, FVector Point)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!World) return 1.0f;
	return FMath::Clamp(LightSum(World, Point, nullptr, false), 0.0f, 1.0f);
}

static bool GContextTorch = true;
static TWeakObjectPtr<const USpotLightComponent> GPlayerTorch;

void ATarsisGuard::SetContextTorch(bool bOn) { GContextTorch = bOn; }

bool ATarsisGuard::Dazzle(float Seconds, float Again)
{
	if (State == ETarsisGuardState::Down || bTowerSentry || bAlly || StunT > 0.0f || DazzleCoolT > 0.0f) return false;
	Stun(Seconds);
	bDazzled = true;
	DazzleCoolT = Seconds + Again;
	return true;
}
void ATarsisGuard::SetPlayerTorch(const USpotLightComponent* L) { GPlayerTorch = L; }

// bajo techo: el suelo que pisa es el de interior (lo mismo que mira el director para el jugador)
bool ATarsisGuard::IsIndoors() const
{
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisTecho), true, this);
	const FVector P = GetActorLocation();
	if (GetWorld()->LineTraceSingleByChannel(Hit, P, P - FVector(0.0f, 0.0f, 250.0f), ECC_Visibility, Q))
	{
		if (const UStaticMeshComponent* SM = Cast<UStaticMeshComponent>(Hit.GetComponent()))
		{
			return SM->GetStaticMesh() && SM->GetStaticMesh()->GetName().Contains(TEXT("suelo_int"));
		}
	}
	return false;
}

// Tanda 31: cada 0,6 s mira cuánta luz le llega (sin contar linternas) y dónde está. La saca si está a oscuras y
// además bajo techo o yendo a mirar algo (ajuste 31c: medido en el PC, de noche el 85 % de las rondas está a la misma
// luz de luna, 0,12, y solo por luz la llevaban encendida 7,8 de 8). Para guardarla tiene que llevar tres medidas
// seguidas sin motivo y al menos TorchMinOn segundos encendida
void ATarsisGuard::AutoTorchTick(float DeltaSeconds)
{
	if (bTowerSentry || bAlly || State == ETarsisGuardState::Down) return;
	if (!GContextTorch)
	{
		if (bAutoTorch) { bAutoTorch = false; SetFlashlight(false); }
		return;
	}
	TorchT -= DeltaSeconds;
	if (TorchT > 0.0f) return;
	TorchT = 0.6f;
	const bool bOn = HasFlashlightOn();
	if (bOn && !bAutoTorch) return;   // la lleva por otra cosa (apagón, farola rota, apoyo): no es asunto nuestro
	const float L = FMath::Clamp(LightSum(GetWorld(), GetActorLocation() + FVector(0.0f, 0.0f, 40.0f), this, false), 0.0f, 1.0f);
	const bool bReason = bTorchOutdoors || State == ETarsisGuardState::Suspicious || State == ETarsisGuardState::Search || IsIndoors();
	if (!bOn)
	{
		if (bReason && L < TorchOnBelow) { SetFlashlight(true); bAutoTorch = HasFlashlightOn(); TorchLit = 0; TorchOnFor = 0.0f; }
		return;
	}
	TorchOnFor += 0.6f;
	// tanda 32: bajo techo solo la guarda con luz de sobra (0,6), que una bombilla al pasar no basta
	const float Off = IsIndoors() ? FMath::Max(TorchOffAbove, 0.6f) : TorchOffAbove;
	if (L > Off || !bReason) { if (++TorchLit >= 3 && TorchOnFor >= TorchMinOn) { bAutoTorch = false; SetFlashlight(false); } }
	else TorchLit = 0;
}

int32 ATarsisGuard::ShadowsOf(const UObject* WorldContext, const AActor* Who, const TArray<float>& Heights, float MinLight, TArray<FVector>& Tips, TArray<float>& Contrast)
{
	Tips.Reset();
	Contrast.Reset();
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!World || !Who) return 0;
	FVector Feet = Who->GetActorLocation();
	if (const ACharacter* C = Cast<ACharacter>(Who)) Feet.Z -= C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FVector Chest = Feet + FVector(0.0f, 0.0f, Heights.Num() > 1 ? Heights[1] : 100.0f);
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisSombra), false);
	FTarsisBeams Beams;
	CollectBeams(World, Beams);
	for (TActorIterator<ALight> It(World); It; ++It)
	{
		if (It->ActorHasTag(NDecorLight)) continue;
		const ULocalLightComponent* L = Cast<ULocalLightComponent>(It->GetLightComponent());
		if (!L || !L->CastShadows) continue;   // sin sombra dibujada no hay nada que ver
		const bool bStrong = It->ActorHasTag(NStrongLight);
		const float Fixed = BeamLumensOf(Beams, *It);
		if (LightContribution(World, L, Chest, *It, Q, bStrong, Fixed, Who) < MinLight) continue;   // esa luz no te da de lleno
		const FVector LP = L->GetComponentLocation();
		for (const float H : Heights)
		{
			const FVector P = Feet + FVector(0.0f, 0.0f, H);
			const FVector Dir = (P - LP).GetSafeNormal();
			FCollisionQueryParams QR(SCENE_QUERY_STAT(TarsisSombraRayo), false, Who);
			QR.AddIgnoredActor(*It);
			FHitResult Hit;
			if (!World->LineTraceSingleByChannel(Hit, P + Dir * 20.0f, P + Dir * 1500.0f, ECC_Visibility, QR)) continue;   // la sombra se pierde a lo lejos
			const FVector S = Hit.ImpactPoint + Hit.ImpactNormal * 8.0f;
			if (FVector::DistSquared2D(S, Feet) < FMath::Square(60.0f)) continue;   // a tus pies: la tapas tú
			// allí tiene que seguir llegando esa luz (si no, tu sombra cae sobre otra sombra) y mandar sobre las demás
			const float Cs = LightContribution(World, L, S, *It, Q, bStrong, Fixed, Who);
			if (Cs < MinLight * 0.6f) continue;
			Tips.Add(S);
			Contrast.Add(Cs / FMath::Max(LightSum(World, S, Who), 0.01f));
		}
	}
	return Tips.Num();
}

bool ATarsisGuard::NoticeShadow(const FVector& Tip, const FVector& From, float Amount, float Cap)
{
	if (bTowerSentry || bAlly || bRepairing || BodyTarget || HoldT > 0.0f || StunT > 0.0f) return false;
	if (State == ETarsisGuardState::Alert || State == ETarsisGuardState::Down || State == ETarsisGuardState::Search) return false;
	if (State == ETarsisGuardState::Suspicious && !bShadow) return false;   // ya va a mirar otra cosa (un ruido, algo que vio)
	ShadowHoldT = 0.4f;
	if (Meter < Cap) Meter = FMath::Min(Cap, Meter + FMath::Max(0.0f, Amount));
	if (State == ETarsisGuardState::Suspicious)
	{
		LastSeen = Tip;   // la sombra se mueve: la sigue
		ShadowFrom = From;
		return true;
	}
	if (Meter > 0.3f)
	{
		LastSeen = Tip;
		ShadowFrom = From;
		SetState(ETarsisGuardState::Suspicious);
		bShadow = true;
		UpdateMark();
		return true;
	}
	return false;
}

void ATarsisGuard::StartRepair(const FVector& Center)
{
	if (State == ETarsisGuardState::Down || State == ETarsisGuardState::Alert) return;
	// va a mirar un ruido lejos del generador (segunda piedra): que no lo vuelvan a poner a reparar en el mismo paso
	if (State == ETarsisGuardState::Suspicious && bInvestigate && FVector::Dist2D(LastSeen, Center) > 320.0f) return;
	if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
	RepairCenter = Center;
	SweepT = 0.0f;
	bRepairing = true;
}

void ATarsisGuard::StopRepair()
{
	if (!bRepairing) return;
	// derribado: KnockOut pone Down sin limpiar bRepairing; sacarlo de Down aquí lo levantaba tumbado
	if (State == ETarsisGuardState::Down) { bRepairing = false; return; }
	SetState(ETarsisGuardState::Return);
}

void ATarsisGuard::WaitForBuddy(ATarsisGuard* B, float Seconds)
{
	bDarkChecked = true;
	bWaitBuddy = true;
	WaitBuddyT = Seconds;
	Buddy = B;
	if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
	if (!HasFlashlightOn()) { SetFlashlight(true); bDarkTorch = true; }
	if (B)
	{
		B->bEscort = true;
		B->bDarkChecked = true;
		B->HearNoise(GetActorLocation());
		if (!B->HasFlashlightOn()) { B->SetFlashlight(true); B->bDarkTorch = true; }
	}
}

void ATarsisGuard::SetFlashlightShadows(bool bOn)
{
	if (Flashlight) Flashlight->SetCastShadows(bOn);   // solo la del reparador: una luz con sombra cuesta poco en la 1050
}

bool ATarsisGuard::HasFlashlightOn() const
{
	return Flashlight && Flashlight->IsVisible();
}

void ATarsisGuard::SetFlashlight(bool bOn)
{
	if (bOn && (bTowerSentry || bAlly || State == ETarsisGuardState::Down)) bOn = false;
	if (!bOn) { bAutoTorch = false; ShowTorch(false); return; }
	if (!Flashlight)
	{
		Flashlight = NewObject<USpotLightComponent>(this);
		Flashlight->SetMobility(EComponentMobility::Movable);
		Flashlight->SetupAttachment(GetRootComponent());
		Flashlight->SetRelativeLocationAndRotation(FVector(35.0f, 18.0f, 55.0f), FRotator(-12.0f, 0.0f, 0.0f));   // a la altura del pecho, algo hacia abajo
		Flashlight->SetIntensityUnits(ELightUnits::Lumens);
		Flashlight->SetIntensity(TorchPaintLumens);   // lo que pinta; para el sigilo cuenta 2500 (LightSum)
		Flashlight->SetAttenuationRadius(2600.0f);   // más que la vista normal (ViewDistance 2000): de frente te ve antes
		Flashlight->SetInnerConeAngle(10.0f);
		Flashlight->SetOuterConeAngle(20.0f);
		Flashlight->SetLightColor(FLinearColor(1.0f, 0.93f, 0.8f));
		Flashlight->SetCastShadows(false);   // sin sombras: la 1050 no da para siete linternas con sombra
		Flashlight->SetVolumetricScatteringIntensity(12.0f);    // con la lluvia el haz se sigue viendo
		Flashlight->SetSourceRadius(3.0f);
		Flashlight->RegisterComponent();
		// tanda 31: el cristal encendido y un destello pequeño, para que se vea de dónde sale el haz (como los faros del camión)
		UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
		UMaterialInterface* Mats[2] = {
			LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Tarsis/Materiales/MI_Faro_Cristal.MI_Faro_Cristal"), nullptr, LOAD_NoWarn | LOAD_Quiet),
			LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Tarsis/Materiales/MI_Halo_Faro.MI_Halo_Faro"), nullptr, LOAD_NoWarn | LOAD_Quiet) };
		const float Sizes[2] = { 5.0f, 13.0f };   // ajuste 31c: a 26 cm el destello se veia flotar junto a la mano
		for (int32 i = 0; i < 2; ++i)
		{
			if (!Sphere || !Mats[i]) continue;
			UStaticMeshComponent* M = NewObject<UStaticMeshComponent>(this);
			M->SetMobility(EComponentMobility::Movable);
			M->SetStaticMesh(Sphere);
			M->SetMaterial(0, Mats[i]);
			M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			M->SetCastShadow(false);
			M->bAffectDynamicIndirectLighting = false;
			M->bAffectDistanceFieldLighting = false;
			M->SetupAttachment(Flashlight);
			M->SetRelativeLocation(FVector(i == 0 ? -2.0f : 2.0f, 0.0f, 0.0f));
			M->SetRelativeScale3D(FVector(Sizes[i] * (i == 0 ? 0.4f : 1.0f), Sizes[i], Sizes[i]) / 100.0f);
			M->RegisterComponent();
			(i == 0 ? TorchLens : TorchGlow) = M;
		}
	}
	ShowTorch(true);
}

void ATarsisGuard::ShowTorch(bool bOn)
{
	if (Flashlight) Flashlight->SetVisibility(bOn);
	if (TorchLens) TorchLens->SetVisibility(bOn);
	if (TorchGlow) TorchGlow->SetVisibility(bOn);
}

float ATarsisGuard::GSeenMul = 1.0f;
float ATarsisGuard::GBoxNear = 0.0f;
float ATarsisGuard::GFarLimit = 0.0f;

float ATarsisGuard::Visibility(const AActor* Target) const
{
	// oculto: durante una cinemática o metido en una taquilla; aturdido por un empujón no ve nada
	if (!Target || State == ETarsisGuardState::Down || bAlly || Target->IsHidden() || StunT > 0.0f) return 0.0f;
	const FVector Eye = GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
	const FVector Aim = Target->GetActorLocation() + FVector(0.0f, 0.0f, 40.0f);
	const float D = FVector::Dist(Eye, Aim);
	// tanda 40: quieto dentro de la caja de carton no te ve; con uniforme, de lejos eres uno mas (si no te persigue ya)
	if (const APawn* TP = Cast<APawn>(Target))
	{
		if (TP->IsPlayerControlled() && ((GSeenMul <= 0.0f && D > GBoxNear) || (GFarLimit > 0.0f && D > GFarLimit && State != ETarsisGuardState::Alert))) return 0.0f;
	}
	// en el cono de su linterna te ve de más lejos que a simple vista (pero solo de frente: el cono es estrecho)
	bool bTorch = false;
	if (HasFlashlightOn() && D < Flashlight->AttenuationRadius)
	{
		const FVector LP = Flashlight->GetComponentLocation();
		bTorch = FVector::DotProduct(Flashlight->GetForwardVector(), (Aim - LP).GetSafeNormal()) >= FMath::Cos(FMath::DegreesToRadians(Flashlight->OuterConeAngle + 4.0f));
	}
	// tanda 42: el centinela de torre ve lo que alumbra su foco, llegue hasta donde llegue. Desde que las torres estan en
	// las esquinas, a 20 m del recinto, la mancha cae a 30-60 m y con su vista de 18 m podias cruzarla de pie sin que pasara nada
	float BeamV = 0.0f;
	if (bTowerSentry && TowerLight)
	{
		const USpotLightComponent* Beam = TowerLight->FindComponentByClass<USpotLightComponent>();
		if (Beam && Beam->IsVisible() && Beam->AttenuationRadius > 1.0f)
		{
			const FVector BP = Beam->GetComponentLocation();
			const float BD = FVector::Dist(BP, Aim);
			if (BD < Beam->AttenuationRadius && FVector::DotProduct(Beam->GetForwardVector(), (Aim - BP).GetSafeNormal()) >= FMath::Cos(FMath::DegreesToRadians(Beam->OuterConeAngle + 1.5f)))
			{
				BeamV = 0.9f * (1.0f - FMath::Pow(BD / Beam->AttenuationRadius, 3.0f));
			}
		}
	}
	const bool bBeam = BeamV > 0.0f;
	if (D > ViewDistance && !bTorch && !bBeam) return 0.0f;
	const float CosA = FVector::DotProduct(GetActorForwardVector(), (Aim - Eye).GetSafeNormal2D());
	const bool bInCone = bBeam || CosA >= FMath::Cos(FMath::DegreesToRadians(ViewHalfAngle));
	if (!bInCone && D > NearDistance) return 0.0f;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisVista), true, this);
	FHitResult Hit;
	// tanda 42: el de la torre mira desde la boca de su foco; desde sus ojos la linea chocaba con su propia caseta (medido en el PC)
	FVector From = Eye;
	if (bTowerSentry && TowerLight)
	{
		Q.AddIgnoredActor(TowerLight.Get());
		From = TowerLight->GetActorLocation() + (Aim - TowerLight->GetActorLocation()).GetSafeNormal() * 90.0f;
	}
	if (GetWorld()->LineTraceSingleByChannel(Hit, From, Aim, ECC_Visibility, Q) && Hit.GetActor() != Target)
	{
		return 0.0f;   // pared, cajas o contenedor por medio
	}
	float Light = LightAt(this, Aim);
	// tanda 31: con tu linterna encendida eres tú la luz
	if (GPlayerTorch.IsValid() && GPlayerTorch->IsVisible() && GPlayerTorch->GetOwner() == Target) Light = FMath::Max(Light, 0.85f);
	float V = D < ViewDistance ? (1.0f - FMath::Pow(D / ViewDistance, 1.5f)) * (0.2f + 0.8f * Light) : 0.0f;
	if (bTorch) V = FMath::Max(V, 0.9f * (1.0f - FMath::Pow(D / Flashlight->AttenuationRadius, 2.0f)));
	if (bBeam) V = FMath::Max(V, BeamV);
	if (const ACharacter* C = Cast<ACharacter>(Target))
	{
		if (C->bIsCrouched) V *= (bTorch || bBeam) ? 0.8f : 0.55f;   // agachado en plena luz de linterna te esconde poco
	}
	if (D < NearDistance)
	{
		if (bInCone) V = FMath::Max(V, 0.6f);
		else
		{
			// a su espalda no te ve: te oye. Agachado apenas (da tiempo a derribarlo), de pie algo más
			const ACharacter* C = Cast<ACharacter>(Target);
			V = (C && C->bIsCrouched) ? 0.12f : 0.35f;
		}
	}
	return FMath::Clamp(V, 0.0f, 1.0f);
}

void ATarsisGuard::Caught(APawn* Player)
{
	// el director decide adónde vas (calabozo la primera vez); sin director, a la salida
	ATarsisDirector* D = nullptr;
	for (TActorIterator<ATarsisDirector> It(GetWorld()); It; ++It) { D = *It; break; }
	if (D)
	{
		// escena: «¡te tengo!», la cámara se vuelve hacia él, golpe y fundido a negro; luego Captured
		if (D->bCapturing) return;
		D->BeginCapture(this);
	}
	else if (AActor* Start = UGameplayStatics::GetActorOfClass(this, APlayerStart::StaticClass()))
	{
		Player->TeleportTo(Start->GetActorLocation(), Start->GetActorRotation());
		if (AController* PC = Player->GetController()) PC->SetControlRotation(Start->GetActorRotation());
	}
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Down) continue;
		It->Meter = 0.0f;
		It->SetState(ETarsisGuardState::Return);
	}
	if (D) Hold(1.5f);   // se queda delante mientras la cámara se vuelve hacia él
}

void ATarsisGuard::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	StateT += DeltaSeconds;
	if (DazzleCoolT > 0.0f) DazzleCoolT -= DeltaSeconds;
	if (StunT <= 0.0f) bDazzled = false;
	if (State == ETarsisGuardState::Down)
	{
		LookTick(DeltaSeconds);   // el cuerpo visible sigue copiando la caída
		if (GestureW > 0.0f || GestureLeft > 0.0f) StopGesture();   // en el suelo no hay gesto que valga, ni al levantarse
		BatonTick(DeltaSeconds);   // y el bastón se apaga
		DownT -= DeltaSeconds;
		if (DownT <= 0.0f) WakeUp();
		return;
	}
	UpdateAnim();
	AutoTorchTick(DeltaSeconds);
	LookTick(DeltaSeconds);
	GestureTick(DeltaSeconds);
	BatonTick(DeltaSeconds);
	FootTick(DeltaSeconds);
	// aturdido por un empujón: tambaleándose, no ve ni anda; al rehacerse va a por ti
	if (StunT > 0.0f)
	{
		StunT -= DeltaSeconds;
		if (StunT <= 0.0f)
		{
			APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
			if (Pl && !Pl->IsHidden() && GSeenMul > 0.0f) { Meter = 1.0f; UnseenT = 0.0f; LastSeen = Pl->GetActorLocation(); SetState(ETarsisGuardState::Alert); }
			else { LastSeen = GetActorLocation(); Meter = 0.6f; SetState(ETarsisGuardState::Search); }   // te has escondido: busca alrededor
		}
		return;
	}
	if (HoldT > 0.0f)
	{
		HoldT -= DeltaSeconds;
		if (HoldT <= 0.0f) MoveDest = FVector(1e9f);   // que vuelva a pedir el camino
		return;
	}
	LookForBodies();

	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	const float V = Visibility(Player);
	if (V > 0.0f)
	{
		LastSeen = Player->GetActorLocation();
		UnseenT = 0.0f;
		// el de la torre mira desde lejos: tarda mas en estar seguro (da tiempo a salir de la mancha del foco)
		const float Gain = ((State == ETarsisGuardState::Alert || State == ETarsisGuardState::Search) ? 3.0f : 1.0f) * (bTowerSentry ? TowerGain : 1.0f);
		Meter = FMath::Min(1.0f, Meter + V * SuspicionRate * Gain * AlertBoost * DeltaSeconds);
	}
	else
	{
		UnseenT += DeltaSeconds;
		if (ShadowHoldT > 0.0f) ShadowHoldT -= DeltaSeconds;   // mientras mira una sombra, la sospecha no se le pasa
		else if (State != ETarsisGuardState::Alert)
		{
			Meter = FMath::Max(0.0f, Meter - SuspicionDecay * DeltaSeconds);
		}
	}

	if (bTowerSentry)
	{
		TowerTick(DeltaSeconds, Player, V);
		return;
	}

	if (BodyTarget)
	{
		BodyTick(DeltaSeconds, Player, V);
		return;
	}

	// arreglando el generador: quieto, barre a un lado y otro con la linterna; si te ve del todo, va a por ti
	if (bRepairing)
	{
		if (Meter >= 1.0f) { SetState(ETarsisGuardState::Alert); return; }
		if (RepairLookT > 0.0f)
		{
			RepairLookT -= DeltaSeconds;
			FaceTowards(RepairLook, DeltaSeconds);
			return;
		}
		SweepT += DeltaSeconds;
		FVector Dir = RepairCenter - GetActorLocation();
		Dir.Z = 0.0f;
		const float BaseYaw = Dir.IsNearlyZero() ? GetActorRotation().Yaw : Dir.Rotation().Yaw;
		const float Want = BaseYaw + 180.0f + 75.0f * FMath::Sin(SweepT * 0.7f);   // de espaldas al generador, mirando el patio
		SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), FRotator(0.0f, Want, 0.0f), DeltaSeconds, 90.0f));
		return;
	}

	switch (State)
	{
	case ETarsisGuardState::Patrol:
	{
		if (Meter >= 1.0f) { SetState(ETarsisGuardState::Alert); break; }
		if (Meter > 0.3f) { SetState(ETarsisGuardState::Suspicious); break; }
		if (bErrand)
		{
			// recado del director: va al sitio, se queda mirando a donde le toca y, al acabar el tiempo, vuelve a la ronda
			ErrandT -= DeltaSeconds;
			if (ErrandT <= 0.0f) { EndErrand(); break; }
			if (Near2D(ErrandLoc, 70.0f))
			{
				if (!bErrandThere)
				{
					bErrandThere = true;
					if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
				}
				FaceTowards(ErrandFace, DeltaSeconds);
			}
			else Walk(ErrandLoc, WalkSpeed);
			break;
		}
		const FVector& P = PatrolPoints[PointIndex];
		if (Near2D(P, 60.0f))
		{
			WaitT += DeltaSeconds;
			if (WaitT >= (PatrolWaits.IsValidIndex(PointIndex) ? PatrolWaits[PointIndex] : WaitAtPoint)) { WaitT = 0.0f; PointIndex = (PointIndex + 1) % PatrolPoints.Num(); }
		}
		else
		{
			Walk(P, WalkSpeed);
		}
		break;
	}
	case ETarsisGuardState::Suspicious:
		// se para, mira hacia donde vio algo y, si sigue, se acerca despacio
		if (Meter >= 1.0f) { SetState(ETarsisGuardState::Alert); break; }
		// primero se para y se vuelve hacia allí con calma (la cabeza se adelanta: LookTick); luego va
		if (StateT < 1.4f)
		{
			FVector Dir = LastSeen - GetActorLocation();
			Dir.Z = 0.0f;
			if (!Dir.IsNearlyZero()) SetActorRotation(FMath::RInterpTo(GetActorRotation(), FRotator(0.0f, Dir.Rotation().Yaw, 0.0f), DeltaSeconds, 3.5f));
		}
		else FaceTowards(LastSeen, DeltaSeconds);
		if (bInvestigate && bWaitBuddy)
		{
			// tanda 28: plantado, con la linterna hacia lo oscuro, hasta que llegue el compañero (o se canse de esperar)
			WaitBuddyT -= DeltaSeconds;
			StateT = 2.0f;   // esperar no gasta los 25 s que tiene para llegar
			ATarsisGuard* B = Buddy.Get();
			const bool bHere = B && B->State != ETarsisGuardState::Down && FVector::Dist2D(B->GetActorLocation(), GetActorLocation()) < 450.0f;
			if (!bHere && WaitBuddyT > 0.0f && !(B && B->State == ETarsisGuardState::Down)) break;
			bWaitBuddy = false;
			MoveDest = FVector(1e9f);
			if (bHere && B->State == ETarsisGuardState::Suspicious) { B->LastSeen = LastSeen; B->bInvestigate = true; B->StateT = 2.0f; B->MoveDest = FVector(1e9f); }
		}
		if (bInvestigate)
		{
			// un ruido: va a mirar (aunque se le pase la sospecha) y allí busca; si no llega, lo deja a los 25 s
			if (StateT > 1.4f && !Near2D(LastSeen, 150.0f)) Walk(LastSeen, WalkSpeed * 0.8f);
			if (Near2D(LastSeen, 150.0f) || StateT > 25.0f) { bInvestigate = false; SetState(ETarsisGuardState::Search); }
			break;
		}
		// una sombra: al llegar a donde la vio se queda mirando hacia donde venía
		if (bShadow && StateT > 1.5f && Near2D(LastSeen, 150.0f)) FaceTowards(ShadowFrom, DeltaSeconds);
		if (StateT > 1.5f && !Near2D(LastSeen, 120.0f)) Walk(LastSeen, WalkSpeed * 0.7f);
		if (Meter <= 0.0f && StateT > 3.0f) SetState(ETarsisGuardState::Return);
		break;
	case ETarsisGuardState::Alert:
		if (ArmedTick(DeltaSeconds, Player, V)) break;   // tanda 37: con fusil no se corre a por nadie (y decide el cuando detenerte)
		if (Player && V > 0.0f && FVector::Dist2D(GetActorLocation(), Player->GetActorLocation()) < CatchDistance)
		{
			Caught(Player);
			break;
		}
		Walk(LastSeen, RunSpeed);
		// mandado por radio: no te ha visto, así que no se rinde a los 4 s; va corriendo hasta el sitio
		if ((UnseenT > 4.0f && (!bRadioCall || StateT > 20.0f)) || (Near2D(LastSeen, 80.0f) && V <= 0.0f)) SetState(ETarsisGuardState::Search);
		break;
	case ETarsisGuardState::Search:
		// mira a un lado y a otro donde te perdió
		if (Meter >= 1.0f && V > 0.0f) { SetState(ETarsisGuardState::Alert); break; }
		AddActorWorldRotation(FRotator(0.0f, FMath::Sin(StateT * 1.3f) * 70.0f * DeltaSeconds, 0.0f));
		Meter = FMath::Max(0.0f, Meter - SuspicionDecay * DeltaSeconds);
		if (StateT > 7.0f) { Meter = FMath::Min(Meter, 0.25f); SetState(ETarsisGuardState::Return); }
		break;
	case ETarsisGuardState::Return:
	{
		if (Meter > 0.3f) { SetState(ETarsisGuardState::Suspicious); break; }
		// vuelve al punto de ronda más cercano
		int32 Best = 0;
		float BestD = TNumericLimits<float>::Max();
		for (int32 i = 0; i < PatrolPoints.Num(); ++i)
		{
			const float D = FVector::Dist2D(GetActorLocation(), PatrolPoints[i]);
			if (D < BestD) { BestD = D; Best = i; }
		}
		if (BestD < 80.0f) { PointIndex = Best; SetState(ETarsisGuardState::Patrol); }
		else Walk(PatrolPoints[Best], WalkSpeed);
		break;
	}
	}
}
