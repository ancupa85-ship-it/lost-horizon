// Lost Horizon: De Profundis - tanda D (2026-11-22): huellas.
//
// Cuttlas deja huellas (calcomanias de M_Huella, de tools/unreal/huellas.py) en el suelo blando: el barro, los charcos y
// sus cercos (las calcomanias MI_Per_Agua/AguaBarro/Barro/Charco de las tandas 22 y 23; las de lluvia solo cuando
// llueve) y la hierba mojada. Sobre suelo duro, ninguna; pero al salir de un charco deja PrintWetSteps pisadas mojadas que
// se van secando. Agachado, mas tenues. Un anillo fijo de PrintPool calcomanias (la mas vieja se reutiliza) que se borran
// en PrintLife segundos (antes si llueve).
// Un guardia tranquilo que pase cerca (PrintSeeDist) de una huella fresca, de frente, con luz (o con su linterna encima)
// y sin nada en medio, la ve: lo dice y sigue el rastro en orden (un recado por huella, mirando al suelo con la
// linterna); en la ultima se pone a buscar. Las del lobo no alarman: es el perro.
// Enfoque: anillo de calcomanias reutilizadas y una lista ordenada de pisadas (numero de secuencia) que el guardia sigue
// como «migas de pan». Las referencias abiertas que se miraron estan en docs (informe de la tanda D).
// Textos solo en ASCII.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/SpotLightComponent.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"

namespace
{
	const TCHAR* PrintMatPath = TEXT("/Game/Tarsis/Materiales/M_Huella.M_Huella");
}

void ATarsisDirector::ScanSoftGround()
{
	bSoftScanned = true;
	SoftPatches.Reset();
	// las calcomanias de barro y agua del suelo (perimetro.py y ambiente.py): por el nombre de su material
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		TInlineComponentArray<UDecalComponent*> Ds(*It);
		for (UDecalComponent* D : Ds)
		{
			const UMaterialInterface* M = D ? D->GetDecalMaterial() : nullptr;
			if (!M) continue;
			const FString N = M->GetName();
			const bool bWater = N.Contains(TEXT("Agua"));
			const bool bMud = N.Contains(TEXT("Barro")) || N.Contains(TEXT("Charco"));
			if (!bWater && !bMud) continue;
			// solo las del suelo (las de los muros miran de lado)
			if (FMath::Abs(D->GetForwardVector().Z) < 0.7f) continue;
			FTarsisSoft S;
			S.Decal = D;
			S.bWater = bWater;
			S.bRain = It->ActorHasTag(FName(TEXT("lluvia")));
			SoftPatches.Add(S);
		}
	}
	UE_LOG(LogTemp, Log, TEXT("Tarsis: huellas: %d manchas de suelo blando"), SoftPatches.Num());
}

bool ATarsisDirector::SoftGroundAt(const FVector& Foot, bool& bWater) const
{
	bWater = false;
	bool bSoft = false;
	for (const FTarsisSoft& S : SoftPatches)
	{
		const UDecalComponent* D = S.Decal.Get();
		if (!D || (S.bRain && Weather != 1) || !D->IsVisible()) continue;
		// dentro de la caja de la calcomania (en su espacio: X es el fondo, Y y Z el ancho y el largo), en la elipse de
		// dentro: el agua ocupa algo mas de la mitad de la caja (M_Charco v6)
		const FVector L = D->GetComponentTransform().InverseTransformPosition(Foot);
		const FVector Sz = D->DecalSize;
		if (FMath::Abs(L.X) > Sz.X + 40.0f || Sz.Y <= 1.0f || Sz.Z <= 1.0f) continue;
		const float E = FMath::Square(L.Y / Sz.Y) + FMath::Square(L.Z / Sz.Z);
		if (E > (S.bWater ? 0.45f : 0.75f)) continue;
		bSoft = true;
		if (S.bWater) bWater = true;
	}
	// la hierba, cuando llueve
	if (!bSoft && Weather == 1 && SurfaceIndex(Foot + FVector(0.0f, 0.0f, 30.0f), UGameplayStatics::GetPlayerPawn(this, 0)) == 4) bSoft = true;
	return bSoft;
}

void ATarsisDirector::PlayerFootprint(ACharacter* C)
{
	if (!bPrintRule || !C || bRiding || bCine) return;
	bPrintLeft = !bPrintLeft;
	const float Half = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FVector Foot = C->GetActorLocation() - FVector(0.0f, 0.0f, Half) + C->GetActorRightVector() * (bPrintLeft ? -11.0f : 11.0f);
	FVector Dir = C->GetVelocity();
	Dir.Z = 0.0f;
	const float Yaw = Dir.SizeSquared() > 100.0f ? Dir.Rotation().Yaw : C->GetActorRotation().Yaw;
	LeavePrint(Foot, Yaw, C->bIsCrouched, false, bPrintLeft);
}

void ATarsisDirector::TestFootstep(FVector Where, float Yaw, bool bCrouched)
{
	if (!bSoftScanned) ScanSoftGround();
	bPrintLeft = !bPrintLeft;
	LeavePrint(Where, Yaw, bCrouched, false, bPrintLeft);
}

void ATarsisDirector::LeavePrint(const FVector& Foot, float Yaw, bool bCrouched, bool bWolf, bool bLeft)
{
	if (!bSoftScanned) ScanSoftGround();
	bool bWater = false;
	const bool bSoft = SoftGroundAt(Foot, bWater);
	float Strength = 0.0f;
	bool bWet = false;
	if (bWater && !bWolf)
	{
		WetStepsLeft = PrintWetSteps;   // dentro del agua no queda huella, pero sales con las botas chorreando
		LastPrintKind = TEXT("agua");
		return;
	}
	if (bSoft)
	{
		Strength = bCrouched ? PrintCrouch : 1.0f;
		LastPrintKind = TEXT("blando");
	}
	else if (WetStepsLeft > 0 && !bWolf)
	{
		// suelo duro con las botas mojadas: pisadas de agua que se van quedando sin agua
		Strength = 0.85f * WetStepsLeft / FMath::Max(PrintWetSteps, 1) * (bCrouched ? PrintCrouch : 1.0f);
		--WetStepsLeft;
		bWet = true;
		LastPrintKind = TEXT("mojada");
	}
	else
	{
		LastPrintKind = TEXT("duro");
		return;   // asfalto, tablas, hormigon secos: nada
	}
	// el suelo de verdad bajo el pie
	FVector At = Foot;
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisHuella), false, this);
	if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
	if (GetWorld()->LineTraceSingleByChannel(Hit, Foot + FVector(0.0f, 0.0f, 40.0f), Foot - FVector(0.0f, 0.0f, 80.0f), ECC_Visibility, Q)) At = Hit.ImpactPoint;
	if (PrintPool <= 0) return;
	if (Prints.Num() != PrintPool) { Prints.SetNum(PrintPool); PrintDecals.SetNum(PrintPool); PrintMids.SetNum(PrintPool); }
	const int32 i = PrintNext;
	PrintNext = (PrintNext + 1) % PrintPool;
	FTarsisPrint& P = Prints[i];
	P.Loc = At;
	P.Yaw = Yaw;
	P.Age = 0.0f;
	P.Strength = Strength;
	P.Seq = ++PrintSeq;
	P.bWet = bWet;
	P.bWolf = bWolf;
	P.bSeen = false;
	P.bLeft = bLeft;
	++PrintsMade;
	if (bWolf) ++WolfPrintsMade;
	UDecalComponent* D = PrintDecals[i];
	if (!D)
	{
		if (!PrintMat) PrintMat = LoadObject<UMaterialInterface>(nullptr, PrintMatPath);
		if (!PrintMat) return;   // sin M_Huella (falta tools/unreal/huellas.py): se cuentan, no se ven
		D = NewObject<UDecalComponent>(this);
		D->SetMobility(EComponentMobility::Movable);
		D->RegisterComponent();
		UMaterialInstanceDynamic* Mid = UMaterialInstanceDynamic::Create(PrintMat, this);
		D->SetDecalMaterial(Mid);
		D->SortOrder = 3;   // encima de las manchas y del agua
		PrintDecals[i] = D;
		PrintMids[i] = Mid;
	}
	// la calcomania mira hacia abajo; el largo de la suela, en la direccion del paso; la izquierda, en espejo
	D->DecalSize = bWolf ? FVector(6.0f, 4.0f, 4.0f) : FVector(6.0f, 14.5f, 14.5f);   // cuadrada: la suela va en la textura (Girar la endereza)
	D->SetWorldLocationAndRotation(At + FVector(0.0f, 0.0f, 1.0f), FRotator(-90.0f, Yaw, 0.0f));
	D->SetWorldScale3D(FVector(1.0f, bLeft ? -1.0f : 1.0f, 1.0f));
	D->SetVisibility(true);
	if (UMaterialInstanceDynamic* Mid = PrintMids[i])
	{
		Mid->SetScalarParameterValue(TEXT("Fuerza"), Strength);
		Mid->SetScalarParameterValue(TEXT("Mojada"), bWet ? 1.0f : 0.0f);
	}
}

int32 ATarsisDirector::PrintsActive() const
{
	int32 N = 0;
	for (const FTarsisPrint& P : Prints) { if (P.Seq > 0 && P.Age < PrintLife && P.Strength > 0.0f) ++N; }
	return N;
}

FVector ATarsisDirector::PrintLocation(int32 Back) const
{
	// la huella Back pisadas atras (0 la ultima)
	if (Prints.Num() == 0) return FVector::ZeroVector;
	const int32 i = ((PrintNext - 1 - Back) % Prints.Num() + Prints.Num()) % Prints.Num();
	return Prints[i].Seq > 0 ? Prints[i].Loc : FVector::ZeroVector;
}

float ATarsisDirector::PrintFade(int32 Back) const
{
	if (Prints.Num() == 0) return 0.0f;
	const int32 i = ((PrintNext - 1 - Back) % Prints.Num() + Prints.Num()) % Prints.Num();
	const FTarsisPrint& P = Prints[i];
	if (P.Seq <= 0) return 0.0f;
	return P.Strength * (1.0f - FMath::SmoothStep(PrintLife * 0.6f, PrintLife, P.Age));
}

void ATarsisDirector::PrintTick(float DeltaSeconds)
{
	if (!bPrintRule) return;
	if (!bSoftScanned) ScanSoftGround();
	// las huellas se borran: en PrintLife segundos, antes con lluvia
	const float Rate = Weather == 1 ? PrintRainMul : 1.0f;
	PrintFadeT -= DeltaSeconds;
	const bool bFadeNow = PrintFadeT <= 0.0f;
	if (bFadeNow) PrintFadeT = 0.5f;
	for (int32 i = 0; i < Prints.Num(); ++i)
	{
		FTarsisPrint& P = Prints[i];
		if (P.Seq <= 0 || P.Age >= PrintLife) continue;
		P.Age += DeltaSeconds * Rate;
		if (!bFadeNow) continue;
		const float F = P.Strength * (1.0f - FMath::SmoothStep(PrintLife * 0.6f, PrintLife, P.Age));
		if (UMaterialInstanceDynamic* Mid = PrintMids.IsValidIndex(i) ? PrintMids[i].Get() : nullptr) Mid->SetScalarParameterValue(TEXT("Fuerza"), F);
		if (P.Age >= PrintLife && PrintDecals.IsValidIndex(i) && PrintDecals[i]) PrintDecals[i]->SetVisibility(false);
	}
	PrintSightTick(DeltaSeconds);
	TrackTick(DeltaSeconds);
}

int32 ATarsisDirector::PrintBestFor(ATarsisGuard* G, float& BestScore, FString* Why)
{
	BestScore = 0.0f;
	auto No = [Why](const TCHAR* R) { if (Why) *Why = R; return INDEX_NONE; };
	if (!G) return No(TEXT("sin guardia"));
	if (bCine || bDone || bCapturing) return No(TEXT("escena o captura"));
	if (G->bTowerSentry || G->bAlly || G->bSceneLock || G->IsStunned() || G->IsPetting() || G->bTrackingPrints) return No(TEXT("ocupado (torre, aliado, escena, aturdido, caricia o ya rastrea)"));
	if (G->State != ETarsisGuardState::Patrol && G->State != ETarsisGuardState::Return) return No(TEXT("no esta de ronda"));
	if (G->IsOnErrand() || G->IsInvestigating() || G->IsCheckingBody()) return No(TEXT("recado, investiga o mira un cuerpo"));
	const FVector Eye = G->GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
	const USpotLightComponent* Torch = G->HasFlashlightOn() ? G->FlashlightComp() : nullptr;
	int32 Best = INDEX_NONE;
	int32 NLive = 0, NFar = 0, NCone = 0, NDark = 0;
	for (int32 i = 0; i < Prints.Num(); ++i)
	{
		const FTarsisPrint& P = Prints[i];
		if (P.Seq <= 0 || P.bSeen || P.Age >= PrintLife * 0.85f) continue;
		const float Fade = P.Strength * (1.0f - FMath::SmoothStep(PrintLife * 0.6f, PrintLife, P.Age));
		if (Fade < 0.2f) continue;
		++NLive;
		const float D = FVector::Dist(Eye, P.Loc);
		if (D > PrintSeeDist) { ++NFar; continue; }
		const FVector To = (P.Loc - Eye).GetSafeNormal();
		if (FVector::DotProduct(G->GetActorForwardVector(), FVector(To.X, To.Y, 0.0f).GetSafeNormal()) < FMath::Cos(FMath::DegreesToRadians(G->ViewHalfAngle))) { ++NCone; continue; }
		// luz: la de la zona o la de su linterna (de noche, casi siempre la linterna)
		float Light = ATarsisGuard::LightAt(this, P.Loc + FVector(0.0f, 0.0f, 5.0f));
		if (Torch && D < Torch->AttenuationRadius && FVector::DotProduct(Torch->GetForwardVector(), (P.Loc - Torch->GetComponentLocation()).GetSafeNormal()) > FMath::Cos(FMath::DegreesToRadians(Torch->OuterConeAngle))) Light = FMath::Max(Light, 0.8f);
		if (Light < PrintMinLight) { ++NDark; continue; }
		const float PrintScore = Fade * Light * (1.0f - D / PrintSeeDist + 0.2f);
		if (PrintScore > BestScore) { BestScore = PrintScore; Best = i; }
	}
	if (Best == INDEX_NONE)
	{
		if (Why) *Why = FString::Printf(TEXT("ninguna: %d vivas, %d lejos, %d fuera del cono (medio angulo %.0f), %d a oscuras"), NLive, NFar, NCone, G->ViewHalfAngle, NDark);
		return INDEX_NONE;
	}
	// sin nada en medio
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisVeHuella), false, G);
	if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
	FHitResult Hit;
	if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, Prints[Best].Loc + FVector(0.0f, 0.0f, 8.0f), ECC_Visibility, Q))
	{
		if (Why) *Why = FString::Printf(TEXT("tapada por %s"), Hit.GetActor() ? *Hit.GetActor()->GetName() : TEXT("?"));
		return INDEX_NONE;
	}
	if (Why) Why->Reset();
	return Best;
}

FString ATarsisDirector::PrintSightWhy(ATarsisGuard* G)
{
	float S = 0.0f;
	FString Why;
	PrintBestFor(G, S, &Why);
	return Why;
}

void ATarsisDirector::PrintSightTick(float DeltaSeconds)
{
	PrintSightT -= DeltaSeconds;
	if (PrintSightT > 0.0f) return;
	const float Step = 0.2f;
	PrintSightT = Step;
	if (bCine || bDone || bCapturing || PrintsActive() == 0) return;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		float BestScore = 0.0f;
		const int32 Best = PrintBestFor(G, BestScore, nullptr);
		float& N = PrintNotice.FindOrAdd(G);
		if (Best == INDEX_NONE) { N = FMath::Max(0.0f, N - Step); continue; }
		N += Step * (0.5f + BestScore);
		if (N < PrintNoticeSeconds) continue;
		N = 0.0f;
		PrintsNoticed(G, Best);
	}
}

void ATarsisDirector::PrintsNoticed(ATarsisGuard* G, int32 Index)
{
	if (!G || !Prints.IsValidIndex(Index)) return;
	FTarsisPrint& P = Prints[Index];
	if (P.bWolf)
	{
		// el perro: ni caso (y no vuelve a fijarse en esas)
		for (FTarsisPrint& O : Prints) { if (O.bWolf && FVector::Dist2D(O.Loc, P.Loc) < 900.0f) O.bSeen = true; }
		++WolfPrintsSeen;
		GuardSay(G, TEXT("huellas_perro"));
		return;
	}
	// si ahora no puede ir (le han parado un momento, por ejemplo), no las da por vistas: las vera en cuanto pueda
	if (!StartTrack(G, Index)) return;
	P.bSeen = true;
	++PrintsSeen;
	GuardSay(G, TEXT("huellas"));
}

bool ATarsisDirector::StartTrack(ATarsisGuard* G, int32 Index)
{
	if (!G || !Prints.IsValidIndex(Index)) return false;
	const FTarsisPrint& P = Prints[Index];
	if (!G->Errand(P.Loc + FVector(0.0f, 0.0f, 90.0f), P.Loc + FRotator(0.0f, P.Yaw, 0.0f).Vector() * 200.0f, PrintStepSeconds)) return false;
	G->bTrackingPrints = true;
	// de noche lleva la linterna encendida (AutoTorchTick) y, mirando al suelo, la lleva a las huellas (LookTick)
	Tracks.Add(G, P.Seq);
	++TracksStarted;
	LastTrackGuard = G->GuardName;
	return true;
}

void ATarsisDirector::TrackTick(float DeltaSeconds)
{
	for (auto It = Tracks.CreateIterator(); It; ++It)
	{
		ATarsisGuard* G = It.Key().Get();
		if (!G) { It.RemoveCurrent(); continue; }
		// le ha llamado otra cosa (te ve, un ruido, lo han tumbado): se acabo el rastro
		if (G->State != ETarsisGuardState::Patrol || !G->IsOnErrand()) { G->bTrackingPrints = false; It.RemoveCurrent(); continue; }
		if (!G->AtErrand()) continue;
		// la siguiente: la de numero inmediatamente mayor, de las suyas, viva y a menos de 3,5 m
		const int32 Cur = It.Value();
		FVector From = G->GetActorLocation();
		int32 Next = INDEX_NONE;
		for (int32 i = 0; i < Prints.Num(); ++i)
		{
			const FTarsisPrint& P = Prints[i];
			if (P.Seq <= Cur || P.bWolf || P.Age >= PrintLife || P.Strength <= 0.0f) continue;
			if (FVector::Dist2D(P.Loc, From) > 450.0f) continue;
			if (Next == INDEX_NONE || P.Seq < Prints[Next].Seq) Next = i;
		}
		// de dos en dos (cada pie): mas natural que pararse en cada pisada
		if (Next != INDEX_NONE)
		{
			for (int32 i = 0; i < Prints.Num(); ++i)
			{
				const FTarsisPrint& P = Prints[i];
				if (P.Seq == Prints[Next].Seq + 1 && !P.bWolf && P.Age < PrintLife && FVector::Dist2D(P.Loc, From) < 450.0f) { Next = i; break; }
			}
		}
		if (Next == INDEX_NONE)
		{
			// la ultima: aqui se pierden. A buscar por la zona
			const FVector Last = G->GetActorLocation();
			G->bTrackingPrints = false;
			G->EndErrand();
			GuardSay(G, TEXT("rastro_fin"));
			G->HearNoise(Last + G->GetActorForwardVector() * 150.0f);
			++TracksFinished;
			It.RemoveCurrent();
			continue;
		}
		FTarsisPrint& N = Prints[Next];
		N.bSeen = true;
		It.Value() = N.Seq;
		++TrackSteps;
		G->Errand(N.Loc + FVector(0.0f, 0.0f, 90.0f), N.Loc + FRotator(0.0f, N.Yaw, 0.0f).Vector() * 200.0f, PrintStepSeconds);
	}
}

void ATarsisDirector::WolfFootprint()
{
	// el lobo tambien deja huellas en lo blando (las que los guardias toman por las del perro)
	if (!bPrintRule || !DogMesh) return;
	WolfStride += FVector::Dist2D(DogLoc, WolfPrintPrev);
	WolfPrintPrev = DogLoc;
	if (WolfStride < 45.0f) return;
	WolfStride = 0.0f;
	bWolfPrintLeft = !bWolfPrintLeft;
	const FVector Side = FRotator(0.0f, DogYaw + 90.0f, 0.0f).Vector() * (bWolfPrintLeft ? -9.0f : 9.0f);
	bool bWater = false;
	if (!SoftGroundAt(DogLoc + Side, bWater)) return;
	LeavePrint(DogLoc + Side, DogYaw, false, true, bWolfPrintLeft);
}

FVector ATarsisDirector::SoftPatchCenter(int32 i) const
{
	return SoftPatches.IsValidIndex(i) && SoftPatches[i].Decal.IsValid() ? SoftPatches[i].Decal->GetComponentLocation() : FVector::ZeroVector;
}
