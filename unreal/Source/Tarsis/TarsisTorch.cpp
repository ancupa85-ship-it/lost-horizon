// Lost Horizon: De Profundis — linternas (tanda 31). Parte de ATarsisDirector: ver el bloque «linternas» de
// TarsisDirector.h. La de los guardias vive en ATarsisGuard (AutoTorchTick); aquí van la del jugador y el cristal
// encendido de los proyectores de las torres.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Camera/CameraComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

void ATarsisDirector::ToggleTorch()
{
	if (bCodec || bMenu || bCine || bDone) return;
	if (!bTorch && BoxBlocks()) return;
	SetTorch(!bTorch);
}

void ATarsisDirector::SetTorch(bool bOn)
{
	if (bOn && !bHasTorch) { bOn = false; GearNag(); }
	if (bOn && !PlayerTorch)
	{
		ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
		UCameraComponent* Cam = C ? C->FindComponentByClass<UCameraComponent>() : nullptr;
		if (!Cam) return;
		PlayerTorch = NewObject<USpotLightComponent>(C);
		PlayerTorch->SetMobility(EComponentMobility::Movable);
		PlayerTorch->SetupAttachment(Cam);
		// en la mano izquierda, un palmo por debajo de los ojos: el haz no nace del centro de la pantalla
		PlayerTorch->SetRelativeLocationAndRotation(FVector(20.0f, -16.0f, -14.0f), FRotator(-1.5f, 1.5f, 0.0f));
		PlayerTorch->SetIntensityUnits(ELightUnits::Lumens);
		PlayerTorch->SetLightColor(FLinearColor(0.86f, 0.93f, 1.0f));   // fria: las de los guardias son calidas, no se confunden
		PlayerTorch->SetSourceRadius(2.0f);
		PlayerTorch->SetVolumetricScatteringIntensity(6.0f);
		PlayerTorch->RegisterComponent();
	}
	bTorch = bOn;
	if (PlayerTorch)
	{
		if (!bOn) TorchDim = 1.0f;
		PlayerTorch->SetIntensity(TorchLumens * TorchDim);
		PlayerTorch->SetAttenuationRadius(TorchRange);
		PlayerTorch->SetOuterConeAngle(TorchCone);
		PlayerTorch->SetInnerConeAngle(TorchCone * 0.45f);
		PlayerTorch->SetCastShadows(bTorchShadows);
		PlayerTorch->SetVisibility(bOn);
	}
	ATarsisGuard::SetPlayerTorch(bOn ? PlayerTorch.Get() : nullptr);
	if (bOn) Teach(TEXT("ensena_linterna"), TEXT("LINTERNA\nVes en lo oscuro, pero con ella encendida te ven como a plena luz. Si alumbras a un guardia, viene a mirar."), {}, 4.5f);
}

void ATarsisDirector::TorchTick(float DeltaSeconds)
{
	ATarsisGuard::SetContextTorch(bContextTorch);
	// el cristal de cada proyector se apaga con su luz (apagon)
	for (UStaticMeshComponent* G : BeamGlows)
	{
		if (!G) continue;
		const USpotLightComponent* L = Cast<USpotLightComponent>(G->GetAttachParent());
		const bool bOn = L && L->IsVisible();
		if (G->IsVisible() != bOn) G->SetVisibility(bOn);
	}
	if (TorchNoticeT > 0.0f) TorchNoticeT -= DeltaSeconds;
	if (!bTorch || !PlayerTorch) return;
	if (bCine || bDone || !bHasTorch) { SetTorch(false); return; }
	// lo que tienes a un palmo no se quema: la luz baja con la distancia a lo que alumbra el centro del haz
	if (TorchNearDist > 1.0f)
	{
		const FVector A = PlayerTorch->GetComponentLocation();
		FCollisionQueryParams NQ(SCENE_QUERY_STAT(TarsisLinternaCerca), true, this);
		if (APawn* Me = UGameplayStatics::GetPlayerPawn(this, 0)) NQ.AddIgnoredActor(Me);
		FHitResult Near;
		float Want = 1.0f;
		// por tipo de objeto y no por Visibility: la capsula del guardia no bloquea Visibility y el deslumbrado salia blanco
		FCollisionObjectQueryParams NO;
		NO.AddObjectTypesToQuery(ECC_WorldStatic);
		NO.AddObjectTypesToQuery(ECC_WorldDynamic);
		NO.AddObjectTypesToQuery(ECC_Pawn);
		if (GetWorld()->LineTraceSingleByObjectType(Near, A, A + PlayerTorch->GetForwardVector() * TorchNearDist, NO, NQ))
		{
			// la luz cae con el cuadrado de la distancia: se compensa casi del todo, con un suelo
			Want = FMath::Clamp(FMath::Square(Near.Distance / TorchNearDist), TorchNearMin, 1.0f);
		}
		TorchDim = FMath::FInterpTo(TorchDim, Want, DeltaSeconds, Want < TorchDim ? 9.0f : 3.0f);
		PlayerTorch->SetIntensity(TorchLumens * TorchDim);
	}
	// a bocajarro y de cara: le deslumbras. Se queda unos segundos sin ver ni andar (puedes pasar, huir o derribarle
	// como tras un empujon) y al rehacerse va a por ti; la segunda vez seguida ya se tapa los ojos
	if (APawn* Me = UGameplayStatics::GetPlayerPawn(this, 0))
	{
		const FVector BP = PlayerTorch->GetComponentLocation();
		const FVector BF = PlayerTorch->GetForwardVector();
		const float CosIn = FMath::Cos(FMath::DegreesToRadians(TorchCone * 0.6f));
		FCollisionQueryParams BQ(SCENE_QUERY_STAT(TarsisDeslumbrar), true, this);
		BQ.AddIgnoredActor(Me);
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (It->bTowerSentry || It->bAlly || It->State == ETarsisGuardState::Down) continue;
			const FVector Head = It->GetActorLocation() + FVector(0.0f, 0.0f, 65.0f);
			const FVector D = Head - BP;
			if (D.SizeSquared() > FMath::Square(TorchBlindDist) || FVector::DotProduct(BF, D.GetSafeNormal()) < CosIn) continue;
			if (FVector::DotProduct(It->GetActorForwardVector(), -D.GetSafeNormal2D()) < 0.5f) continue;   // de espaldas o de lado no le da en los ojos
			FHitResult Hit;
			if (GetWorld()->LineTraceSingleByChannel(Hit, BP, Head, ECC_Visibility, BQ) && Hit.GetActor() != *It) continue;
			if (!It->Dazzle(TorchBlindSeconds, TorchBlindAgain)) continue;
			++TorchBlinds;
			Teach(TEXT("ensena_deslumbrar"), TEXT("DESLUMBRADO\n{0} no ve nada unos segundos. Luego ira a por ti, y la segunda vez se tapara los ojos."), { It->GuardName.ToUpper() }, 3.5f);
		}
	}
	if (TorchNoticeT > 0.0f) return;
	// el guardia al que alumbras de cerca lo nota y viene a mirar (uno cada dos segundos y medio: tambien sirve de señuelo)
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P) return;
	const FVector LP = PlayerTorch->GetComponentLocation();
	const FVector Fwd = PlayerTorch->GetForwardVector();
	const float CosOut = FMath::Cos(FMath::DegreesToRadians(TorchCone));
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisLinternaJugador), true, this);
	Q.AddIgnoredActor(P);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->bTowerSentry || It->bAlly) continue;
		if (It->State != ETarsisGuardState::Patrol && It->State != ETarsisGuardState::Return) continue;
		const FVector Chest = It->GetActorLocation() + FVector(0.0f, 0.0f, 40.0f);
		const FVector D = Chest - LP;
		if (D.SizeSquared() > FMath::Square(TorchNoticeDist) || FVector::DotProduct(Fwd, D.GetSafeNormal()) < CosOut) continue;
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, LP, Chest, ECC_Visibility, Q) && Hit.GetActor() != *It) continue;
		It->HearNoise(P->GetActorLocation());
		++TorchNotices;
		TorchNoticeT = 2.5f;
		Teach(TEXT("ensena_linterna_guardia"), TEXT("LE HAS ALUMBRADO\n{0} viene a mirar de donde sale esa luz. Apagala ({1}) y muevete."), { It->GuardName.ToUpper(), ActionKeys[6].GetDisplayName().ToString().ToUpper() }, 3.5f);
		break;
	}
}

// cristal encendido y destello en cada proyector de torre, como los faros del camion: de noche la torre era una
// silueta y no se leia ni de donde salia el haz ni que alli arriba hubiera alguien
void ATarsisDirector::SetupBeamLenses()
{
	BeamGlows.Reset();
	BeamLenses = 0;
	UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	UMaterialInterface* LensMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Tarsis/Materiales/MI_Faro_Cristal.MI_Faro_Cristal"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	UMaterialInterface* GlowMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Tarsis/Materiales/MI_Halo_Faro.MI_Halo_Faro"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	if (!Sphere) return;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (!It->bTowerSentry || !It->TowerLight) continue;
		USpotLightComponent* L = It->TowerLight->FindComponentByClass<USpotLightComponent>();
		if (!L) continue;
		struct FGlow { UMaterialInterface* Mat; float Size; float Flat; };
		const FGlow Glows[2] = { { LensMat, BeamLensSize, 0.3f }, { GlowMat, BeamGlowSize, 1.0f } };
		bool bAny = false;
		for (const FGlow& G : Glows)
		{
			if (!G.Mat || G.Size <= 0.0f) continue;
			UStaticMeshComponent* M = NewObject<UStaticMeshComponent>(It->TowerLight);
			M->SetMobility(EComponentMobility::Movable);
			M->SetStaticMesh(Sphere);
			M->SetMaterial(0, G.Mat);
			M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			M->SetCastShadow(false);
			M->bAffectDynamicIndirectLighting = false;
			M->bAffectDistanceFieldLighting = false;
			M->SetupAttachment(L);
			M->SetRelativeLocation(FVector(-6.0f, 0.0f, 0.0f));
			M->SetRelativeScale3D(FVector(G.Size * G.Flat, G.Size, G.Size) / 100.0f);
			M->RegisterComponent();
			BeamGlows.Add(M);
			bAny = true;
		}
		if (bAny) ++BeamLenses;
	}
}
