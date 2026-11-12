#include "TarsisGuard.h"

#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimationAsset.h"
#include "Engine/SkeletalMesh.h"
#include "Components/LocalLightComponent.h"
#include "Components/SpotLightComponent.h"
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
	Move->bUseAccelerationForPaths = true;   // si no, al seguir un camino no gira hacia donde anda

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

void ATarsisGuard::UpdateAnim()
{
	USkeletalMeshComponent* M = GetMesh();
	if (!BodyMesh || !M) return;
	const float Speed = GetVelocity().Size2D();
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

void ATarsisGuard::BeginPlay()
{
	Super::BeginPlay();
	SetupBody();
	Home = GetActorLocation();
	if (PatrolPoints.Num() == 0)
	{
		PatrolPoints.Add(Home);
	}
	SetState(ETarsisGuardState::Patrol);
}

void ATarsisGuard::SetState(ETarsisGuardState NewState)
{
	State = NewState;
	StateT = 0.0f;
	WaitT = 0.0f;
	GetCharacterMovement()->MaxWalkSpeed = (State == ETarsisGuardState::Alert) ? RunSpeed : WalkSpeed;
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
	Mark->SetTextRenderColor(bAlert ? FColor(255, 59, 47) : FColor(255, 210, 58));
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

float ATarsisGuard::LightAt(const UObject* WorldContext, FVector Point)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!World) return 1.0f;
	float Sum = 0.12f;   // luna y cielo: de noche siempre se ve una silueta de cerca
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisLuz), false);
	for (TActorIterator<ALight> It(World); It; ++It)
	{
		const ULocalLightComponent* L = Cast<ULocalLightComponent>(It->GetLightComponent());
		if (!L || !L->IsVisible() || L->Intensity <= 0.0f) continue;
		const FVector LP = L->GetComponentLocation();
		const float D = FVector::Dist(LP, Point);
		const float R = L->AttenuationRadius;
		if (D >= R) continue;
		float F = FMath::Square(1.0f - D / R);
		if (const USpotLightComponent* S = Cast<USpotLightComponent>(L))
		{
			const float CosA = FVector::DotProduct(S->GetForwardVector(), (Point - LP).GetSafeNormal());
			const float CosOut = FMath::Cos(FMath::DegreesToRadians(S->OuterConeAngle));
			if (CosA < CosOut) continue;
			F *= 1.5f;   // dentro del foco de una torre se ve de lejos
		}
		// las luces están en lúmenes: una farola (~3000) cuenta como 1 a su pie
		F *= FMath::Clamp(L->Intensity / 3000.0f, 0.2f, 2.0f);
		if (F < 0.02f) continue;
		Q.ClearIgnoredSourceObjects();   // ClearIgnoredActors está obsoleto en 5.8
		Q.AddIgnoredActor(*It);
		FHitResult Hit;
		if (World->LineTraceSingleByChannel(Hit, LP, Point, ECC_Visibility, Q) && FVector::Dist(Hit.ImpactPoint, Point) > 40.0f)
		{
			continue;   // algo hace sombra entre la luz y el punto
		}
		Sum += F;
	}
	return FMath::Clamp(Sum, 0.0f, 1.0f);
}

float ATarsisGuard::Visibility(const AActor* Target) const
{
	if (!Target) return 0.0f;
	const FVector Eye = GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
	const FVector Aim = Target->GetActorLocation() + FVector(0.0f, 0.0f, 40.0f);
	const float D = FVector::Dist(Eye, Aim);
	if (D > ViewDistance) return 0.0f;
	if (D > NearDistance)
	{
		const float CosA = FVector::DotProduct(GetActorForwardVector(), (Aim - Eye).GetSafeNormal2D());
		if (CosA < FMath::Cos(FMath::DegreesToRadians(ViewHalfAngle))) return 0.0f;
	}
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisVista), true, this);
	FHitResult Hit;
	if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, Aim, ECC_Visibility, Q) && Hit.GetActor() != Target)
	{
		return 0.0f;   // pared, cajas o contenedor por medio
	}
	const float Light = LightAt(this, Aim);
	float V = (1.0f - FMath::Pow(D / ViewDistance, 1.5f)) * (0.2f + 0.8f * Light);
	if (const ACharacter* C = Cast<ACharacter>(Target))
	{
		if (C->bIsCrouched) V *= 0.55f;
	}
	if (D < NearDistance) V = FMath::Max(V, 0.6f);
	return FMath::Clamp(V, 0.0f, 1.0f);
}

void ATarsisGuard::Caught(APawn* Player)
{
	if (GEngine)
	{
		GEngine->AddOnScreenDebugMessage(-1, 4.0f, FColor::Red, TEXT("TE HAN COGIDO"));
	}
	// de momento vuelve a la salida de Cuttlas (luego irá la celda, como en el juego web)
	if (AActor* Start = UGameplayStatics::GetActorOfClass(this, APlayerStart::StaticClass()))
	{
		Player->TeleportTo(Start->GetActorLocation(), Start->GetActorRotation());
		if (AController* PC = Player->GetController()) PC->SetControlRotation(Start->GetActorRotation());
	}
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		It->Meter = 0.0f;
		It->SetState(ETarsisGuardState::Return);
	}
}

void ATarsisGuard::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	StateT += DeltaSeconds;
	UpdateAnim();

	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	const float V = Visibility(Player);
	if (V > 0.0f)
	{
		LastSeen = Player->GetActorLocation();
		UnseenT = 0.0f;
		const float Gain = (State == ETarsisGuardState::Alert || State == ETarsisGuardState::Search) ? 3.0f : 1.0f;
		Meter = FMath::Min(1.0f, Meter + V * SuspicionRate * Gain * DeltaSeconds);
	}
	else
	{
		UnseenT += DeltaSeconds;
		if (State != ETarsisGuardState::Alert)
		{
			Meter = FMath::Max(0.0f, Meter - SuspicionDecay * DeltaSeconds);
		}
	}

	switch (State)
	{
	case ETarsisGuardState::Patrol:
	{
		if (Meter >= 1.0f) { SetState(ETarsisGuardState::Alert); break; }
		if (Meter > 0.3f) { SetState(ETarsisGuardState::Suspicious); break; }
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
		FaceTowards(LastSeen, DeltaSeconds);
		if (StateT > 1.5f && !Near2D(LastSeen, 120.0f)) Walk(LastSeen, WalkSpeed * 0.7f);
		if (Meter <= 0.0f && StateT > 3.0f) SetState(ETarsisGuardState::Return);
		break;
	case ETarsisGuardState::Alert:
		if (Player && V > 0.0f && FVector::Dist2D(GetActorLocation(), Player->GetActorLocation()) < CatchDistance)
		{
			Caught(Player);
			break;
		}
		Walk(LastSeen, RunSpeed);
		if (UnseenT > 4.0f || (Near2D(LastSeen, 80.0f) && V <= 0.0f)) SetState(ETarsisGuardState::Search);
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
