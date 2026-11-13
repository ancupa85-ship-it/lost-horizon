#include "TarsisGuard.h"
#include "Animation/BlendSpace.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "TarsisDirector.h"

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
		if (UAnimSingleNodeInstance* SI = M->GetSingleNodeInstance())
		{
			// la posición en la mezcla se suaviza: aunque la cápsula frene en seco, las piernas no saltan de pose
			BlendPos = FMath::FInterpTo(BlendPos, FMath::Min(Speed, WalkAnimSpeed), GetWorld()->GetDeltaSeconds(), 6.0f);
			SI->SetBlendSpacePosition(FVector(BlendPos, 0.0f, 0.0f));
		}
		M->SetPlayRate(Speed > WalkAnimSpeed ? FMath::Clamp(Speed / FMath::Max(WalkAnimSpeed, 1.0f), 1.0f, 2.6f) : 1.0f);
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
	if (bTowerSentry)
	{
		GetCharacterMovement()->DisableMovement();   // se queda en la plataforma, sin caer ni andar
		TowerT = FMath::FRand() * 10.0f;
		if (TowerLight) LightPitch = TowerLight->GetActorRotation().Pitch;
	}
}

void ATarsisGuard::Alarm(const FVector& Where)
{
	if (bTowerSentry || State == ETarsisGuardState::Alert || State == ETarsisGuardState::Down) return;
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

void ATarsisGuard::HearNoise(const FVector& Where)
{
	if (bTowerSentry || bAlly || State == ETarsisGuardState::Alert || State == ETarsisGuardState::Down) return;
	if (State == ETarsisGuardState::Suspicious && bInvestigate) { LastSeen = Where; return; }   // ya va a mirar: sigue el ruido
	LastSeen = Where;
	Meter = FMath::Max(Meter, 0.5f);
	SetState(ETarsisGuardState::Suspicious);
	bInvestigate = true;
	UpdateMark();   // el «?» de un ruido sale azulado: te ha oído, no te ha visto
}

bool ATarsisGuard::CanBeTakenDown(const AActor* Who) const
{
	if (!Who || bTowerSentry || bAlly || State == ETarsisGuardState::Down) return false;   // a un aliado (Ramos) no se le derriba por error
	const FVector D = Who->GetActorLocation() - GetActorLocation();
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
	SetState(ETarsisGuardState::Search);   // se levanta buscando a quien le ha tumbado
	for (TActorIterator<ATarsisDirector> It(GetWorld()); It; ++It)
	{
		It->ShowMessage(FString::Printf(TEXT("%s SE HA DESPERTADO\nBusca a quien le ha tumbado."), *GuardName.ToUpper()), 4.0f);
		break;
	}
}

void ATarsisGuard::LookForBodies()
{
	if (State == ETarsisGuardState::Alert || bAlly) return;
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
		// lo ha visto: da la voz, va corriendo y el caído se despierta pronto
		O->bFound = true;
		O->DownT = FMath::Min(O->DownT, 6.0f);
		Alarm(P);
		for (TActorIterator<ATarsisDirector> Dt(GetWorld()); Dt; ++Dt)
		{
			Dt->ShowMessage(FString::Printf(TEXT("%s HA ENCONTRADO A %s EN EL SUELO\nToda la base te busca."), *GuardName.ToUpper(), *O->GuardName.ToUpper()), 5.0f);
			break;
		}
		break;
	}
}

void ATarsisGuard::TowerTick(float DeltaSeconds, APawn* Player, float V)
{
	TowerT += DeltaSeconds;
	if (State == ETarsisGuardState::Search || State == ETarsisGuardState::Return)
	{
		SetState(ETarsisGuardState::Patrol);   // tras una captura todos vuelven; el de la torre ya está en su sitio
	}
	if (State == ETarsisGuardState::Alert)
	{
		// te sigue con la vista y con el foco mientras te vea; si te pierde, vuelve a barrer
		FaceTowards(LastSeen, DeltaSeconds * 1.5f);
		if (UnseenT > 5.0f) { Meter = 0.5f; SetState(ETarsisGuardState::Suspicious); }
	}
	else
	{
		if (Meter >= 1.0f)
		{
			SetState(ETarsisGuardState::Alert);
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
			FaceTowards(LastSeen, DeltaSeconds);
			if (Meter <= 0.0f) SetState(ETarsisGuardState::Patrol);
		}
		else
		{
			if (Meter > 0.3f) { SetState(ETarsisGuardState::Suspicious); }
			const float Yaw = TowerYaw + FMath::Sin(TowerT * 0.42f) * TowerSweep;
			SetActorRotation(FMath::RInterpTo(GetActorRotation(), FRotator(0.0f, Yaw, 0.0f), DeltaSeconds, 3.0f));
		}
	}
	if (TowerLight)
	{
		TowerLight->SetActorRotation(FRotator(LightPitch, GetActorRotation().Yaw, 0.0f));
	}
}

void ATarsisGuard::SetState(ETarsisGuardState NewState)
{
	State = NewState;
	StateT = 0.0f;
	bRepairing = false;
	if (NewState == ETarsisGuardState::Down && Flashlight) Flashlight->SetVisibility(false);
	if (NewState != ETarsisGuardState::Suspicious) bInvestigate = false;
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
	Mark->SetTextRenderColor(bAlert ? FColor(255, 59, 47) : (bInvestigate ? FColor(120, 200, 255) : FColor(255, 210, 58)));
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

// lo que aporta una luz local al punto: 0 si queda fuera de su radio o de su cono, o si algo hace sombra
static float LightContribution(const UWorld* World, const ULocalLightComponent* L, const FVector& Point, const AActor* Owner, FCollisionQueryParams& Q)
{
	if (!L || !L->IsVisible() || L->Intensity <= 0.0f) return 0.0f;
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
	// las luces están en lúmenes: una farola (~3000) cuenta como 1 a su pie
	F *= FMath::Clamp(L->Intensity / 3000.0f, 0.2f, 2.0f);
	if (F < 0.02f) return 0.0f;
	Q.ClearIgnoredSourceObjects();   // ClearIgnoredActors está obsoleto en 5.8
	if (Owner) Q.AddIgnoredActor(Owner);
	FHitResult Hit;
	if (World->LineTraceSingleByChannel(Hit, LP, Point, ECC_Visibility, Q) && FVector::Dist(Hit.ImpactPoint, Point) > 40.0f)
	{
		return 0.0f;   // algo hace sombra entre la luz y el punto
	}
	return F;
}

float ATarsisGuard::LightAt(const UObject* WorldContext, FVector Point)
{
	const UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContext, EGetWorldErrorMode::ReturnNull) : nullptr;
	if (!World) return 1.0f;
	float Sum = 0.12f;   // luna y cielo: de noche siempre se ve una silueta de cerca
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisLuz), false);
	for (TActorIterator<ALight> It(World); It; ++It)
	{
		Sum += LightContribution(World, Cast<ULocalLightComponent>(It->GetLightComponent()), Point, *It, Q);
	}
	// linternas de los guardias
	for (TActorIterator<ATarsisGuard> It(World); It; ++It)
	{
		if (It->HasFlashlightOn()) Sum += LightContribution(World, It->Flashlight, Point, *It, Q);
	}
	return FMath::Clamp(Sum, 0.0f, 1.0f);
}

void ATarsisGuard::StartRepair(const FVector& Center)
{
	if (State == ETarsisGuardState::Down || State == ETarsisGuardState::Alert) return;
	if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
	RepairCenter = Center;
	SweepT = 0.0f;
	bRepairing = true;
}

void ATarsisGuard::StopRepair()
{
	if (!bRepairing) return;
	SetState(ETarsisGuardState::Return);
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
	if (!bOn) { if (Flashlight) Flashlight->SetVisibility(false); return; }
	if (!Flashlight)
	{
		Flashlight = NewObject<USpotLightComponent>(this);
		Flashlight->SetMobility(EComponentMobility::Movable);
		Flashlight->SetupAttachment(GetRootComponent());
		Flashlight->SetRelativeLocationAndRotation(FVector(35.0f, 18.0f, 55.0f), FRotator(-12.0f, 0.0f, 0.0f));   // a la altura del pecho, algo hacia abajo
		Flashlight->SetIntensityUnits(ELightUnits::Lumens);
		Flashlight->SetIntensity(2500.0f);
		Flashlight->SetAttenuationRadius(2600.0f);   // más que la vista normal (ViewDistance 2000): de frente te ve antes
		Flashlight->SetInnerConeAngle(10.0f);
		Flashlight->SetOuterConeAngle(20.0f);
		Flashlight->SetLightColor(FLinearColor(1.0f, 0.93f, 0.8f));
		Flashlight->SetCastShadows(false);   // sin sombras: la 1050 no da para siete linternas con sombra
		Flashlight->SetVolumetricScatteringIntensity(3.0f);
		Flashlight->RegisterComponent();
	}
	Flashlight->SetVisibility(true);
}

float ATarsisGuard::Visibility(const AActor* Target) const
{
	if (!Target || State == ETarsisGuardState::Down || bAlly || Target->IsHidden()) return 0.0f;   // oculto: durante una cinemática
	const FVector Eye = GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
	const FVector Aim = Target->GetActorLocation() + FVector(0.0f, 0.0f, 40.0f);
	const float D = FVector::Dist(Eye, Aim);
	// en el cono de su linterna te ve de más lejos que a simple vista (pero solo de frente: el cono es estrecho)
	bool bTorch = false;
	if (HasFlashlightOn() && D < Flashlight->AttenuationRadius)
	{
		const FVector LP = Flashlight->GetComponentLocation();
		bTorch = FVector::DotProduct(Flashlight->GetForwardVector(), (Aim - LP).GetSafeNormal()) >= FMath::Cos(FMath::DegreesToRadians(Flashlight->OuterConeAngle + 4.0f));
	}
	if (D > ViewDistance && !bTorch) return 0.0f;
	const float CosA = FVector::DotProduct(GetActorForwardVector(), (Aim - Eye).GetSafeNormal2D());
	const bool bInCone = CosA >= FMath::Cos(FMath::DegreesToRadians(ViewHalfAngle));
	if (!bInCone && D > NearDistance) return 0.0f;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisVista), true, this);
	FHitResult Hit;
	if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, Aim, ECC_Visibility, Q) && Hit.GetActor() != Target)
	{
		return 0.0f;   // pared, cajas o contenedor por medio
	}
	const float Light = LightAt(this, Aim);
	float V = D < ViewDistance ? (1.0f - FMath::Pow(D / ViewDistance, 1.5f)) * (0.2f + 0.8f * Light) : 0.0f;
	if (bTorch) V = FMath::Max(V, 0.9f * (1.0f - FMath::Pow(D / Flashlight->AttenuationRadius, 2.0f)));
	if (const ACharacter* C = Cast<ACharacter>(Target))
	{
		if (C->bIsCrouched) V *= bTorch ? 0.8f : 0.55f;   // agachado en plena luz de linterna te esconde poco
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
		D->Captured(Player);
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
}

void ATarsisGuard::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	StateT += DeltaSeconds;
	if (State == ETarsisGuardState::Down)
	{
		DownT -= DeltaSeconds;
		if (DownT <= 0.0f) WakeUp();
		return;
	}
	UpdateAnim();
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
		const float Gain = (State == ETarsisGuardState::Alert || State == ETarsisGuardState::Search) ? 3.0f : 1.0f;
		Meter = FMath::Min(1.0f, Meter + V * SuspicionRate * Gain * AlertBoost * DeltaSeconds);
	}
	else
	{
		UnseenT += DeltaSeconds;
		if (State != ETarsisGuardState::Alert)
		{
			Meter = FMath::Max(0.0f, Meter - SuspicionDecay * DeltaSeconds);
		}
	}

	if (bTowerSentry)
	{
		TowerTick(DeltaSeconds, Player, V);
		return;
	}

	// arreglando el generador: quieto, barre a un lado y otro con la linterna; si te ve del todo, va a por ti
	if (bRepairing)
	{
		if (Meter >= 1.0f) { SetState(ETarsisGuardState::Alert); return; }
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
		if (bInvestigate)
		{
			// un ruido: va a mirar (aunque se le pase la sospecha) y allí busca; si no llega, lo deja a los 25 s
			if (StateT > 1.0f && !Near2D(LastSeen, 150.0f)) Walk(LastSeen, WalkSpeed * 0.8f);
			if (Near2D(LastSeen, 150.0f) || StateT > 25.0f) { bInvestigate = false; SetState(ETarsisGuardState::Search); }
			break;
		}
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
