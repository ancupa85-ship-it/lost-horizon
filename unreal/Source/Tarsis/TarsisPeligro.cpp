// Lost Horizon: De Profundis - tanda N, primera parte (2026-11-26): que los tiros se sientan.
//
// Antes un tiro era un fogonazo y, si acertaba, un «HERIDO 1/3»: no se veia donde daba ni se notaba el peligro.
// - Impacto: el tiro que falla da en algo de verdad (traza desde la boca del fusil hacia el punto al que fallo, que
//   FireAt elige cerca de ti: a un lado o al suelo delante). Alli, polvo (dos bolas translucidas que crecen y se
//   desvanecen) y, en metal, chispas (las barritas de la trazadora), sin texturas; y un sonido segun la superficie.
//   (Se probo el impacto de Twinblast: cargaba ~110 Mpx de texturas, +330 MB de VRAM y -12 fps.)
// - Trazadora: de noche, una barra fina que brilla y vuela de la boca al impacto (M_Trazadora, sin luz propia ni
//   sombras: barata). Se reutilizan los componentes (TracerPool).
// - Silbido: si la bala pasa a menos de WhizRadius de tu cabeza, silba, la vista da un tiron y se encoge (vineta y
//   algo de desaturacion, SuppressT).
// - Camara lenta (SlowMo): un instante en el golpe de los remates; se mide en tiempo real para que no dure mas.
// Ideas tomadas (sin codigo): el «casi te dan» con una traza junto al tiro (foro de Unreal) y que el fuego cercano
// encoja la vista (la supresion de Arma 3). Textos solo en ASCII.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Components/PostProcessComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "PhysicalMaterials/PhysicalMaterial.h"

namespace
{
	// la superficie por el nombre del material o de la malla (no hay materiales fisicos propios en el nivel)
	const TCHAR* ImpactKind(const FHitResult& H)
	{
		FString N;
		if (const UPrimitiveComponent* P = H.GetComponent())
		{
			if (const UMaterialInterface* M = P->GetMaterial(0)) N += M->GetName();
			if (const UStaticMeshComponent* S = Cast<UStaticMeshComponent>(P)) if (S->GetStaticMesh()) N += S->GetStaticMesh()->GetName();
		}
		if (const AActor* A = H.GetActor()) N += A->GetName();
		N = N.ToLower();
		if (N.Contains(TEXT("metal")) || N.Contains(TEXT("chapa")) || N.Contains(TEXT("contenedor")) || N.Contains(TEXT("container")) || N.Contains(TEXT("camion")) || N.Contains(TEXT("valla")) || N.Contains(TEXT("bidon"))) return TEXT("metal");
		if (N.Contains(TEXT("madera")) || N.Contains(TEXT("wood")) || N.Contains(TEXT("caja")) || N.Contains(TEXT("crate")) || N.Contains(TEXT("puerta"))) return TEXT("madera");
		return TEXT("tierra");
	}
}

void ATarsisDirector::ShotFx(ATarsisGuard* G, const FVector& Muzzle, bool bHit, const FVector& MissAim)
{
	if (!bShotFxRule || !G) return;
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Pl) return;
	const FVector Head = Pl->GetActorLocation() + FVector(0.0f, 0.0f, 60.0f);
	FVector End = bHit ? Pl->GetActorLocation() + FVector(0.0f, 0.0f, 20.0f) : (MissAim.IsZero() ? Head + FVector(0.0f, 0.0f, 150.0f) : MissAim);
	FHitResult H;
	bool bImpact = false;
	if (!bHit)
	{
		// el tiro sigue mas alla del punto al que fallo hasta dar en algo (o perderse)
		const FVector Dir = (End - Muzzle).GetSafeNormal();
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisImpacto), false, G);
		Q.AddIgnoredActor(Pl);
		bImpact = GetWorld()->LineTraceSingleByChannel(H, Muzzle, Muzzle + Dir * 6000.0f, ECC_Visibility, Q);
		End = bImpact ? H.ImpactPoint : Muzzle + Dir * 6000.0f;
	}
	if (bImpact)
	{
		++ShotImpacts;
		const TCHAR* K = ImpactKind(H);
		if (!ImpactFxPath.IsEmpty())
		{
			if (UParticleSystem* PS = LoadObject<UParticleSystem>(nullptr, *ImpactFxPath))
				UGameplayStatics::SpawnEmitterAtLocation(GetWorld(), PS, FTransform(H.ImpactNormal.Rotation(), H.ImpactPoint, FVector(ImpactFxScale)), true, EPSCPoolMethod::AutoRelease);
		}
		else ImpactPuff(H.ImpactPoint, H.ImpactNormal, FCString::Strcmp(K, TEXT("metal")) == 0);
		if (USoundBase* S = Sfx(FString::Printf(TEXT("impacto_%s_%d"), K, FMath::RandRange(1, 3))))
		{
			UGameplayStatics::PlaySoundAtLocation(this, S, H.ImpactPoint, 0.9f, FMath::FRandRange(0.92f, 1.08f), 0.0f, Atten);
		}
	}
	// de noche, la trazadora
	if (!bDay && TracerSpeed > 1.0f)
	{
		UStaticMeshComponent* C = nullptr;
		for (UStaticMeshComponent* T : TracerPool) if (T && !T->IsVisible()) { C = T; break; }
		if (!C)
		{
			UStaticMesh* Cyl = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
			UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, *TracerMaterialPath);
			if (Cyl && Mat)
			{
				C = NewObject<UStaticMeshComponent>(this);
				C->SetMobility(EComponentMobility::Movable);
				C->SetStaticMesh(Cyl);
				C->SetMaterial(0, Mat);
				C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				C->SetCastShadow(false);
				C->RegisterComponent();
				TracerPool.Add(C);
			}
		}
		if (C)
		{
			FTarsisTracer T;
			T.C = C; T.From = Muzzle; T.To = End; T.T = 0.0f; T.Len = FVector::Dist(Muzzle, End);
			TracerList.Add(T);
			C->SetVisibility(true);
			++Tracers;
		}
	}
	// el silbido: la bala pasa cerca de la cabeza (punto de la recta mas cercano)
	const FVector Seg = End - Muzzle;
	const float L2 = Seg.SizeSquared();
	const float U = L2 > 1.0f ? FMath::Clamp(FVector::DotProduct(Head - Muzzle, Seg) / L2, 0.0f, 1.0f) : 0.0f;
	const float Pass = FVector::Dist(Head, Muzzle + Seg * U);
	if (!bHit && Pass < WhizRadius && U > 0.2f)
	{
		++NearMisses;
		if (USoundBase* S = Sfx(FString::Printf(TEXT("silbido_%d"), FMath::RandRange(1, 3))))
		{
			UGameplayStatics::PlaySound2D(this, S, FMath::GetMappedRangeValueClamped(FVector2D(40.0f, WhizRadius), FVector2D(1.0f, 0.45f), Pass));
		}
		SuppressT = FMath::Max(SuppressT, FMath::GetMappedRangeValueClamped(FVector2D(40.0f, WhizRadius), FVector2D(1.1f, 0.5f), Pass));
		KickT = FMath::Max(KickT, 0.12f);
	}
	if (bHit) SuppressT = FMath::Max(SuppressT, 1.2f);
}

UStaticMeshComponent* ATarsisDirector::PuffGet(bool bSpark)
{
	for (UStaticMeshComponent* C : PuffPool)
	{
		if (C && !C->IsVisible() && C->ComponentHasTag(bSpark ? FName(TEXT("chispa")) : FName(TEXT("polvo")))) return C;
	}
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, bSpark ? TEXT("/Engine/BasicShapes/Cylinder.Cylinder") : TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	UMaterialInterface* Mat = LoadObject<UMaterialInterface>(nullptr, bSpark ? *TracerMaterialPath : *DustMaterialPath);
	if (!Mesh || !Mat) return nullptr;
	UStaticMeshComponent* C = NewObject<UStaticMeshComponent>(this);
	C->SetMobility(EComponentMobility::Movable);
	C->SetStaticMesh(Mesh);
	C->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	C->SetCastShadow(false);
	C->ComponentTags.Add(bSpark ? FName(TEXT("chispa")) : FName(TEXT("polvo")));
	if (bSpark) C->SetMaterial(0, Mat);
	else C->SetMaterial(0, UMaterialInstanceDynamic::Create(Mat, this));
	C->RegisterComponent();
	PuffPool.Add(C);
	return C;
}

void ATarsisDirector::ImpactPuff(const FVector& At, const FVector& Normal, bool bMetal)
{
	// polvo: dos bolas translucidas que crecen y se desvanecen, saliendo de la superficie; en metal, chispas
	for (int32 i = 0; i < 2; ++i)
	{
		UStaticMeshComponent* C = PuffGet(false);
		if (!C) break;
		FTarsisPuff P;
		P.C = C;
		P.M = Cast<UMaterialInstanceDynamic>(C->GetMaterial(0));
		P.P = At + Normal * 4.0f;
		P.V = (Normal * FMath::FRandRange(60.0f, 140.0f) + FMath::VRand() * 40.0f + FVector(0.0f, 0.0f, 30.0f)) * (i == 0 ? 1.0f : 0.6f);
		P.T = -0.03f * i;
		C->SetWorldLocation(P.P);
		C->SetWorldScale3D(FVector(0.05f));
		C->SetVisibility(true);
		PuffList.Add(P);
	}
	const int32 NS = bMetal ? 5 : 2;
	for (int32 i = 0; i < NS; ++i)
	{
		UStaticMeshComponent* C = PuffGet(true);
		if (!C) break;
		FTarsisPuff P;
		P.C = C;
		P.bSpark = true;
		P.P = At + Normal * 2.0f;
		P.V = (Normal + FMath::VRand() * 0.8f).GetSafeNormal() * FMath::FRandRange(250.0f, 600.0f);
		C->SetVisibility(true);
		PuffList.Add(P);
	}
}

void ATarsisDirector::SlowMo()
{
	if (!bSlowMoRule || SlowMoDilation >= 1.0f || SlowMoSeconds <= 0.0f) return;
	UGameplayStatics::SetGlobalTimeDilation(this, SlowMoDilation);
	SlowMoUntil = FPlatformTime::Seconds() + SlowMoSeconds;
	++SlowMos;
}

void ATarsisDirector::PeligroTick(float DeltaSeconds)
{
	// la camara lenta acaba en tiempo real (DeltaSeconds ya va escalado)
	if (SlowMoUntil > 0.0 && FPlatformTime::Seconds() >= SlowMoUntil)
	{
		UGameplayStatics::SetGlobalTimeDilation(this, 1.0f);
		SlowMoUntil = 0.0;
	}
	// las trazadoras vuelan
	for (int32 i = TracerList.Num() - 1; i >= 0; --i)
	{
		FTarsisTracer& T = TracerList[i];
		UStaticMeshComponent* C = T.C.Get();
		T.T += DeltaSeconds * TracerSpeed;
		if (!C || T.T - TracerLength > T.Len)
		{
			if (C) C->SetVisibility(false);
			TracerList.RemoveAt(i);
			continue;
		}
		const FVector Dir = (T.To - T.From).GetSafeNormal();
		const float Head = FMath::Min(T.T, T.Len);
		const float Tail = FMath::Clamp(T.T - TracerLength, 0.0f, T.Len);
		const float Len = FMath::Max(Head - Tail, 1.0f);
		// el cilindro basico mide 100 cm de alto en Z y 100 de diametro: Z a lo largo del tiro
		C->SetWorldLocationAndRotation(T.From + Dir * (Tail + Len * 0.5f), FRotationMatrix::MakeFromZ(Dir).ToQuat());
		C->SetWorldScale3D(FVector(TracerWidth / 100.0f, TracerWidth / 100.0f, Len / 100.0f));
	}
	// el polvo y las chispas de los impactos
	for (int32 i = PuffList.Num() - 1; i >= 0; --i)
	{
		FTarsisPuff& P = PuffList[i];
		UStaticMeshComponent* C = P.C.Get();
		P.T += DeltaSeconds;
		const float Life = P.bSpark ? 0.25f : DustSeconds;
		if (!C || P.T > Life)
		{
			if (C) C->SetVisibility(false);
			PuffList.RemoveAt(i);
			continue;
		}
		if (P.T < 0.0f) continue;
		const float A = P.T / Life;
		if (P.bSpark)
		{
			P.V += FVector(0.0f, 0.0f, -980.0f) * DeltaSeconds;
			const FVector Prev = P.P;
			P.P += P.V * DeltaSeconds;
			const FVector Dir = (P.P - Prev).GetSafeNormal();
			C->SetWorldLocationAndRotation(P.P, FRotationMatrix::MakeFromZ(Dir.IsNearlyZero() ? FVector::UpVector : Dir).ToQuat());
			C->SetWorldScale3D(FVector(0.006f, 0.006f, 0.05f * (1.0f - A)));
		}
		else
		{
			P.V *= FMath::Max(0.0f, 1.0f - 3.0f * DeltaSeconds);
			P.P += P.V * DeltaSeconds;
			C->SetWorldLocation(P.P);
			C->SetWorldScale3D(FVector(DustSize / 100.0f * (0.25f + 0.75f * FMath::Sqrt(A))));
			if (UMaterialInstanceDynamic* M = P.M.Get()) M->SetScalarParameterValue(TEXT("Opacidad"), 0.55f * (1.0f - A) * (1.0f - A));
		}
	}
	// la vista que se encoge (vineta y algo de desaturacion) tras un tiro cerca
	if (SuppressT > 0.0f) SuppressT = FMath::Max(0.0f, SuppressT - DeltaSeconds);
	const float W = FMath::Clamp(SuppressT, 0.0f, 1.0f);
	if (W <= 0.0f && !SuppressPP) return;
	if (!SuppressPP)
	{
		SuppressPP = NewObject<UPostProcessComponent>(this, TEXT("VistaEncogida"));
		SuppressPP->bUnbound = true;
		SuppressPP->Priority = 40.0f;
		FPostProcessSettings& S = SuppressPP->Settings;
		S.bOverride_VignetteIntensity = true; S.VignetteIntensity = 1.3f;
		S.bOverride_ColorSaturation = true; S.ColorSaturation = FVector4(0.65f, 0.65f, 0.65f, 1.0f);
		S.bOverride_SceneFringeIntensity = true; S.SceneFringeIntensity = 1.5f;
		SuppressPP->RegisterComponent();
	}
	SuppressPP->BlendWeight = W;
	SuppressPP->SetVisibility(W > 0.0f);
}
