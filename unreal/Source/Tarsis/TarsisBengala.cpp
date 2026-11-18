// Lost Horizon: De Profundis - tanda 42: bengalas de las torres, dia o noche y brillo.
// La bengala: de vez en cuando un centinela de torre lanza una. Sube en segundo y medio, estalla sobre la base y cae
// despacio unos catorce segundos. Es un foco con sombra que mira hacia abajo: lo que queda al abrigo de un muro o bajo
// techo sigue a oscuras, y lo demas se ve como de dia. Para el sigilo cuenta sola: ATarsisGuard::LightAt recorre las
// luces del nivel y mira si algo les hace sombra.
// Dia o noche: la mision 1 es de noche. El dia (para la de los inspectores) cambia la luna por el sol, la boveda y la
// niebla, y sube el fondo de luz del sigilo. Se afina sin compilar con las propiedades «Tarsis|Dia».
// Brillo: pasos de un cuarto de diafragma sobre la exposicion fija del nivel (el volumen «Exposicion»).
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SpotLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/Light.h"
#include "Components/LightComponent.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SpotLight.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

static const float FlareRise = 1.6f;   // segundos de subida
static const float FlareFade = 2.2f;   // segundos de apagarse al final

FVector ATarsisDirector::FlareLocation() const
{
	return FlareLight ? FlareLight->GetActorLocation() : FVector::ZeroVector;
}

void ATarsisDirector::FireFlare()
{
	if (FlareT > 0.0f) return;
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	// la lanza un centinela de torre que siga en pie, al azar
	TArray<ATarsisGuard*> Towers;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->bTowerSentry && It->State != ETarsisGuardState::Down) Towers.Add(*It);
	}
	if (Towers.Num() == 0 && !P) return;
	const FVector Mid(3600.0f, 2800.0f, 0.0f);   // el centro de la base
	if (Towers.Num() > 0)
	{
		FlareFrom = Towers[FMath::RandRange(0, Towers.Num() - 1)]->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f);
	}
	else
	{
		FlareFrom = P->GetActorLocation() + FVector(1500.0f, 0.0f, 300.0f);
	}
	FlareTop = FMath::Lerp(FVector(FlareFrom.X, FlareFrom.Y, 0.0f), Mid, 0.6f) + FVector(FMath::FRandRange(-600.0f, 600.0f), FMath::FRandRange(-600.0f, 600.0f), FlareHeight);
	FlareDrift = FVector(FMath::FRandRange(-90.0f, 90.0f), FMath::FRandRange(-90.0f, 90.0f), 0.0f);   // el viento, cm/s
	if (!FlareLight)
	{
		FActorSpawnParameters SP;
		SP.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
		FlareLight = GetWorld()->SpawnActor<ASpotLight>(ASpotLight::StaticClass(), FlareFrom, FRotator(-90.0f, 0.0f, 0.0f), SP);
		if (!FlareLight) return;
		FlareLight->Tags.Add(FName(TEXT("bengala")));
		if (USpotLightComponent* L = Cast<USpotLightComponent>(FlareLight->GetLightComponent()))
		{
			L->SetMobility(EComponentMobility::Movable);
			L->SetIntensityUnits(ELightUnits::Candelas);
			L->SetSourceRadius(30.0f);
			L->SetVolumetricScatteringIntensity(0.4f);
			// la brasa que se ve en el cielo: la esfera del destello de los faros, sin sombra ni colision
			UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
			UMaterialInterface* GlowMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Tarsis/Materiales/MI_Halo_Faro.MI_Halo_Faro"), nullptr, LOAD_NoWarn | LOAD_Quiet);
			if (Sphere && GlowMat)
			{
				FlareGlow = NewObject<UStaticMeshComponent>(FlareLight);
				FlareGlow->SetMobility(EComponentMobility::Movable);
				FlareGlow->SetStaticMesh(Sphere);
				FlareGlow->SetMaterial(0, GlowMat);
				FlareGlow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				FlareGlow->SetCastShadow(false);
				FlareGlow->bAffectDynamicIndirectLighting = false;
				FlareGlow->bAffectDistanceFieldLighting = false;
				FlareGlow->SetupAttachment(L);
				FlareGlow->SetRelativeLocation(FVector(-40.0f, 0.0f, 0.0f));   // por encima del foco (mira hacia abajo): no le hace sombra
				FlareGlow->SetRelativeScale3D(FVector(2.2f));
				FlareGlow->RegisterComponent();
			}
		}
	}
	if (USpotLightComponent* L = Cast<USpotLightComponent>(FlareLight->GetLightComponent()))
	{
		L->SetLightColor(FlareColor);
		L->SetAttenuationRadius(FlareRadius);
		L->SetOuterConeAngle(FlareCone);
		L->SetInnerConeAngle(FlareCone * 0.7f);
		L->SetCastShadows(bFlareShadows);
		L->SetIntensity(0.0f);
		L->SetVisibility(true);
	}
	FlareLight->SetActorLocation(FlareFrom);
	FlareLight->SetActorRotation(FRotator(-90.0f, 0.0f, 0.0f));   // mirando abajo: el giro de SpawnActor no se quedaba (alumbraba de lado)
	if (FlareGlow) FlareGlow->SetVisibility(true);
	FlareT = 0.001f;
	++FlaresFired;
	PlaySfx(TEXT("bengala"), FlareFrom, 0.7f, false);
	Teach(TEXT("ensena_bengala"), TEXT("BENGALA\nMientras cae, la base se ve como de dia. A la sombra de un muro o bajo techo sigues a oscuras: no cruces lo abierto hasta que se apague."), {}, 6.0f);
}

void ATarsisDirector::EndFlare()
{
	FlareT = 0.0f;
	if (FlareLight)
	{
		if (ULightComponent* L = FlareLight->GetLightComponent()) { L->SetIntensity(0.0f); L->SetVisibility(false); }
	}
	if (FlareGlow) FlareGlow->SetVisibility(false);
	FlareNext = FMath::FRandRange(FlareEveryMin, FMath::Max(FlareEveryMin, FlareEveryMax));
}

void ATarsisDirector::FlareTick(float DeltaSeconds)
{
	if (FlareT <= 0.0f)
	{
		if (!bFlares || bDay || bCine || bDone || bCodec) return;
		FlareNext -= DeltaSeconds;
		if (FlareNext <= 0.0f) { FlareNext = FMath::FRandRange(FlareEveryMin, FMath::Max(FlareEveryMin, FlareEveryMax)); FireFlare(); }
		return;
	}
	FlareT += DeltaSeconds;
	const float Total = FlareRise + FlareSeconds;
	if (FlareT >= Total || !FlareLight || bCine || bDone) { EndFlare(); return; }
	FVector Where;
	float K;
	if (FlareT < FlareRise)
	{
		const float A = FlareT / FlareRise;
		Where = FMath::Lerp(FlareFrom, FlareTop, 1.0f - FMath::Square(1.0f - A));   // sale deprisa y se frena arriba
		K = 0.04f + 0.1f * A;
	}
	else
	{
		const float B = FlareT - FlareRise;
		Where = FlareTop + FlareDrift * B - FVector(0.0f, 0.0f, (FlareHeight - FlareEndHeight) * B / FMath::Max(1.0f, FlareSeconds));
		// estalla de golpe, tiembla como el magnesio y al final se consume
		K = FMath::Min(1.0f, B / 0.25f) * FMath::Min(1.0f, (Total - FlareT) / FlareFade);
		K *= 0.88f + 0.12f * FMath::Sin(B * 31.0f) * FMath::Sin(B * 7.3f);
	}
	FlareLight->SetActorLocation(Where);
	if (ULightComponent* L = FlareLight->GetLightComponent()) L->SetIntensity(FlareCandelas * K);
	if (FlareGlow) FlareGlow->SetRelativeScale3D(FVector(1.2f + 3.2f * K));
}

// ---------------------------------------------------------------- dia o noche

void ATarsisDirector::SetDay(bool bNewDay)
{
	bDay = bNewDay;
	if (bDay && FlareT > 0.0f) EndFlare();
	// el sol es la misma luz direccional de la luna, con otra fuerza, color y altura
	for (TActorIterator<ADirectionalLight> It(GetWorld()); It; ++It)
	{
		ULightComponent* L = It->GetLightComponent();
		if (!L) continue;
		if (BaseMoonLux < 0.0f) { BaseMoonLux = L->Intensity; BaseMoonColor = L->GetLightColor(); BaseMoonRot = It->GetActorRotation(); }
		if (L->Mobility == EComponentMobility::Static) L->SetMobility(EComponentMobility::Movable);
		L->SetIntensity(bDay ? DaySunLux : BaseMoonLux);
		L->SetLightColor(bDay ? DaySunColor : BaseMoonColor);
		It->SetActorRotation(bDay ? FRotator(DaySunPitch, BaseMoonRot.Yaw, 0.0f) : BaseMoonRot);
		break;
	}
	// la boveda (actor con la etiqueta «cielo»): de dia, una copia del material con el cielo claro y sin estrellas
	for (TActorIterator<AStaticMeshActor> It(GetWorld()); It; ++It)
	{
		if (!It->ActorHasTag(FName(TEXT("cielo")))) continue;
		UStaticMeshComponent* M = It->GetStaticMeshComponent();
		if (!M) break;
		if (!NightSkyMat) NightSkyMat = M->GetMaterial(0);
		if (!bDay) { if (NightSkyMat) M->SetMaterial(0, NightSkyMat); break; }
		if (UMaterialInstanceDynamic* Sky = UMaterialInstanceDynamic::Create(NightSkyMat, this))
		{
			Sky->SetVectorParameterValue(TEXT("Cenit"), DayZenith);
			Sky->SetVectorParameterValue(TEXT("Horizonte"), DayHorizon);
			Sky->SetVectorParameterValue(TEXT("NubeLuz"), DayCloud);
			Sky->SetVectorParameterValue(TEXT("NubeSombra"), DayCloud * 0.6f);
			Sky->SetVectorParameterValue(TEXT("Cubierto1"), DayCloud * 0.5f);
			Sky->SetVectorParameterValue(TEXT("Cubierto2"), DayCloud * 0.8f);
			Sky->SetVectorParameterValue(TEXT("Resplandor"), FLinearColor::Black);
			Sky->SetVectorParameterValue(TEXT("LunaColor"), DaySunColor);
			Sky->SetScalarParameterValue(TEXT("EstrellasFuerza"), 0.0f);
			// la luna del material sigue a la luz direccional: el disco pasa a ser el sol
			const FVector SunDir = -FRotator(DaySunPitch, BaseMoonRot.Yaw, 0.0f).Vector();
			Sky->SetVectorParameterValue(TEXT("LunaDir"), FLinearColor(SunDir.X, SunDir.Y, SunDir.Z));
			M->SetMaterial(0, Sky);
		}
		break;
	}
	SetWeather(Weather);   // deja la niebla de noche como toca con este clima
	if (bDay)
	{
		for (TActorIterator<AExponentialHeightFog> It(GetWorld()); It; ++It)
		{
			if (UExponentialHeightFogComponent* F = It->GetComponent()) F->SetFogInscatteringColor(Weather == 2 ? DayFogColor * 1.5f : DayFogColor);
			break;
		}
	}
	// de dia las farolas de fuera se apagan (las de dentro y las de las casetas siguen); de noche vuelven
	for (ALight* A : DayOffLights) { if (A && A->GetLightComponent()) A->GetLightComponent()->SetVisibility(true); }
	DayOffLights.Reset();
	if (bDay && bDayLampsOff)
	{
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisDia), false, this);
		for (TActorIterator<ALight> It(GetWorld()); It; ++It)
		{
			ULightComponent* L = It->GetLightComponent();
			if (!L || !L->IsVisible() || BrokenLights.Contains(L) || (*It != GateLamp.Get() && !BreakableLamp(*It))) continue;
			FCollisionQueryParams Q2 = Q;
			Q2.AddIgnoredActor(*It);
			FHitResult Hit;
			const FVector P = It->GetActorLocation();
			if (GetWorld()->LineTraceSingleByChannel(Hit, P + FVector(0.0f, 0.0f, 60.0f), P + FVector(0.0f, 0.0f, 2500.0f), ECC_Visibility, Q2)) continue;   // bajo techo
			L->SetVisibility(false);
			DayOffLights.Add(*It);
		}
	}
	ATarsisGuard::SetDayAmbient(bDay ? DayAmbientOpen : 0.0f, bDay ? DayAmbientRoofed : 0.0f);
	if (HasActorBegunPlay()) ShowMessage(bDay ? Tx(TEXT("dia"), TEXT("DE DIA\nA cielo abierto se te ve desde lejos. Bajo techo, algo menos.")) : Tx(TEXT("noche"), TEXT("DE NOCHE")), 3.5f);
}

// ---------------------------------------------------------------- brillo

void ATarsisDirector::ApplyBrightness()
{
	for (TActorIterator<APostProcessVolume> It(GetWorld()); It; ++It)
	{
		if (!It->bUnbound || !It->Settings.bOverride_AutoExposureBias) continue;
		if (BaseExposure < -999.0f) BaseExposure = It->Settings.AutoExposureBias;
		It->Settings.AutoExposureBias = BaseExposure + 0.25f * OptBrightness;
		break;
	}
}
