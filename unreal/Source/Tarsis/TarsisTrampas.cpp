// Lost Horizon: De Profundis - tanda G. Parte de ATarsisDirector: ver el bloque «tanda G» de TarsisDirector.h.
// (1) Cuerpos escondidos: arrastrando a un caido, E junto a una taquilla o un cajon grande y se mete dentro. Asi
//     tardan mas en echarlo de menos, nadie lo ve al pasar y solo lo encuentra quien abra ese escondite.
// (2) Pulso al apuntar: la mira se mueve sola, mas tras correr, herido o con la base en alerta; Mayus contiene la
//     respiracion unos segundos (quieta) y luego tiembla mas.
// (3) Trampas: latas con piedras en un alambre (suenan y atraen) y cable a ras de suelo en un paso estrecho (el que
//     tropieza cae aturdido). Agachado, E las pone y las recoge; un guardia que las ve con luz las desmonta.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

// ---------------------------------------------------------------- cuerpos escondidos

FVector ATarsisDirector::StashSlotLoc(int32 Index) const
{
	if (HideSpots.IsValidIndex(Index))
	{
		// delante de la puerta de la taquilla
		return HideSpots[Index] + FRotator(0.0f, HideYaws.IsValidIndex(Index) ? HideYaws[Index] : 0.0f, 0.0f).Vector() * 75.0f;
	}
	const int32 J = Index - HideSpots.Num();
	return BodyCrates.IsValidIndex(J) ? BodyCrates[J] : FVector::ZeroVector;
}

ATarsisGuard* ATarsisDirector::StashSlotBody(int32 Index) const
{
	return StashBodies.IsValidIndex(Index) ? StashBodies[Index].Get() : nullptr;
}

int32 ATarsisDirector::StashSlotNear() const
{
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || bHiding) return -1;
	int32 Best = -1;
	float BestD = TNumericLimits<float>::Max();
	for (int32 i = 0; i < StashSlotCount(); ++i)
	{
		if (StashSlotBody(i)) continue;
		const FVector L = StashSlotLoc(i);
		const float Reach = HideSpots.IsValidIndex(i) ? 120.0f : StashReach;
		const float D = FVector::Dist2D(P->GetActorLocation(), L);
		if (D > Reach || D >= BestD) continue;
		if (HideSpots.IsValidIndex(i) && FMath::Abs(P->GetActorLocation().Z - HideSpots[i].Z) > 200.0f) continue;
		BestD = D;
		Best = i;
	}
	return Best;
}

float ATarsisDirector::StashProgress() const
{
	return StashWorkIdx < 0 ? 0.0f : FMath::Clamp(StashT / FMath::Max(StashSeconds, 0.1f), 0.0f, 1.0f);
}

FString ATarsisDirector::StashPrompt() const
{
	if (StashWorkIdx >= 0)
	{
		return Tx(TEXT("p_esconder_metiendo"), TEXT("METIENDO EL CUERPO... {0}%      E   DEJARLO"), { FString::FromInt(FMath::RoundToInt(StashProgress() * 100.0f)) });
	}
	if (!Dragged) return FString();
	const int32 S = StashSlotNear();
	if (S < 0) return FString();
	return HideSpots.IsValidIndex(S) ? Tx(TEXT("p_esconder_taquilla"), TEXT("E   METER EL CUERPO EN LA TAQUILLA"))
		: Tx(TEXT("p_esconder_cajon"), TEXT("E   METER EL CUERPO EN EL CAJON"));
}

bool ATarsisDirector::StashInteract()
{
	if (StashWorkIdx >= 0)
	{
		StashWorkIdx = -1;
		StashT = 0.0f;
		ShowMessage(Tx(TEXT("sabotaje_dejado"), TEXT("LO DEJAS A MEDIAS")), 1.5f);
		return true;
	}
	if (!Dragged) return false;
	const int32 S = StashSlotNear();
	if (S < 0) return false;
	StashWorkIdx = S;
	StashT = 0.0f;
	PlaySfx(TEXT("taquilla"), StashSlotLoc(S) + FVector(0.0f, 0.0f, 80.0f), 0.5f);
	return true;
}

void ATarsisDirector::StashBody(int32 Index)
{
	ATarsisGuard* G = Dragged;
	if (!G || Index < 0 || Index >= StashSlotCount()) return;
	if (StashBodies.Num() < StashSlotCount()) StashBodies.SetNum(StashSlotCount());
	StopDrag();
	G->bStashed = true;
	G->PhysAnimRelease();   // sin colision la malla pierde sus cuerpos: antes, soltar la animacion fisica
	G->SetActorHiddenInGame(true);
	G->SetActorEnableCollision(false);
	StashBodies[Index] = G;
	++BodiesStashed;
	PlaySfx(TEXT("taquilla"), StashSlotLoc(Index) + FVector(0.0f, 0.0f, 80.0f), 0.8f);
	Teach(TEXT("ensena_escondido"), TEXT("CUERPO ESCONDIDO\nAhi dentro nadie lo ve al pasar y tardaran mas en echarlo de menos.\nSolo lo encuentra quien abra ese escondite."), {}, 4.0f);
}

void ATarsisDirector::UnstashBody(ATarsisGuard* G)
{
	if (!G) return;
	for (TWeakObjectPtr<ATarsisGuard>& W : StashBodies) if (W.Get() == G) W = nullptr;
	G->bStashed = false;
	G->SetActorHiddenInGame(false);
	G->SetActorEnableCollision(true);
}

int32 ATarsisDirector::OpenStashesNear(ATarsisGuard* By, FVector Where, float Radius)
{
	int32 Found = 0;
	for (int32 i = 0; i < StashSlotCount(); ++i)
	{
		ATarsisGuard* G = StashSlotBody(i);
		if (!G || FVector::Dist2D(StashSlotLoc(i), Where) > Radius) continue;
		UnstashBody(G);
		++StashesFound;
		++Found;
		PlaySfx(TEXT("taquilla"), StashSlotLoc(i) + FVector(0.0f, 0.0f, 80.0f), 0.9f);
		if (G->State != ETarsisGuardState::Down) continue;
		// lo ha encontrado: el aviso de siempre (va a mirarlo, se agacha y avisa por radio; el caido despierta pronto)
		G->bFound = true;
		G->DownT = FMath::Min(G->DownT, 14.0f);
		if (By && By->State != ETarsisGuardState::Down && !By->BodyTarget)
		{
			By->BodyTarget = G;
			By->BodyCheckT = 0.0f;
			By->MoveDest = FVector(1e9f);
			GuardSay(By, TEXT("cuerpo"));
		}
	}
	return Found;
}

bool ATarsisDirector::LookAroundFor(ATarsisGuard* By, float Radius)
{
	if (!By) return false;
	const FVector Eye = By->GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		if (G == By || G->State != ETarsisGuardState::Down || G->bFound || G->bStashed) continue;
		const FVector P = G->GetActorLocation();
		if (FVector::Dist(Eye, P) > Radius) continue;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisMiraAlrededor), true, By);
		Q.AddIgnoredActor(G);
		FHitResult H;
		if (GetWorld()->LineTraceSingleByChannel(H, Eye, P + FVector(0.0f, 0.0f, 30.0f), ECC_Visibility, Q)) continue;
		G->bFound = true;
		G->DownT = FMath::Min(G->DownT, 14.0f);
		By->BodyTarget = G;
		By->BodyCheckT = 0.0f;
		By->MoveDest = FVector(1e9f);
		GuardSay(By, TEXT("cuerpo"));
		return true;
	}
	return false;
}

void ATarsisDirector::StashTick(float DeltaSeconds)
{
	if (StashBodies.Num() < StashSlotCount()) StashBodies.SetNum(StashSlotCount());
	// dentro sigue sin sentido mientras nadie lo saque (atado y amordazado); si se ha levantado por otra via, fuera
	for (TWeakObjectPtr<ATarsisGuard>& W : StashBodies)
	{
		ATarsisGuard* G = W.Get();
		if (!G) continue;
		if (G->State != ETarsisGuardState::Down) { UnstashBody(G); continue; }
		G->DownT = FMath::Max(G->DownT, 5.0f);
	}
	if (StashWorkIdx < 0) return;
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Dragged || !P || bCine || bDone || bCapturing || StashSlotBody(StashWorkIdx)
		|| FVector::Dist2D(P->GetActorLocation(), StashSlotLoc(StashWorkIdx)) > StashReach + 60.0f)
	{
		StashWorkIdx = -1;
		StashT = 0.0f;
		return;
	}
	StashT += DeltaSeconds;
	if (StashT < StashSeconds) return;
	const int32 S = StashWorkIdx;
	StashWorkIdx = -1;
	StashT = 0.0f;
	StashBody(S);
}

// ---------------------------------------------------------------- pulso y respiracion

void ATarsisDirector::HoldBreath()
{
	if (!bPulseRule || AimAlpha < 0.3f || BreathState != 0) return;
	BreathState = 1;
	BreathT = 0.0f;
	Teach(TEXT("ensena_respiracion"), TEXT("CONTIENES LA RESPIRACION\nUnos segundos con la mira quieta. Luego tiembla mas un rato."), {}, 3.0f);
}

void ATarsisDirector::PulseTick(float DeltaSeconds)
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	// cansancio: sube corriendo, baja despacio; alerta: mientras alguien te persigue y un rato despues
	const float Speed = C ? C->GetVelocity().Size2D() : 0.0f;
	if (bSprint && Speed > 250.0f) Exertion = FMath::Min(1.0f, Exertion + DeltaSeconds / 5.0f);
	else Exertion = FMath::Max(0.0f, Exertion - AimSwayCalm * DeltaSeconds);
	bool bAlertNow = false;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Alert && !It->bTowerSentry && !It->bAlly) { bAlertNow = true; break; }
	}
	SeenSway = bAlertNow ? 1.0f : FMath::Max(0.0f, SeenSway - 0.1f * DeltaSeconds);
	const float Hurt = MaxWounds > 0 ? FMath::Clamp(float(Wounds) / float(MaxWounds), 0.0f, 1.0f) : 0.0f;
	const float Amp = AimSwayBase * (1.0f + 2.5f * Exertion + 1.5f * Hurt + 1.2f * SeenSway);
	// la respiracion: contenida, casi quieta; al soltarla, tiembla mas un rato
	if (BreathState == 1)
	{
		BreathT += DeltaSeconds;
		if (BreathT >= BreathHoldSeconds || AimAlpha <= 0.05f) { BreathState = 2; BreathT = 0.0f; }
	}
	else if (BreathState == 2)
	{
		BreathT += DeltaSeconds;
		if (BreathT >= BreathShakeSeconds) { BreathState = 0; BreathT = 0.0f; }
	}
	const float BreathMul = BreathState == 1 ? 0.12f : (BreathState == 2 ? BreathShakeMul : 1.0f);
	// la amplitud cambia suave (al contener la respiracion la mira se asienta, no salta)
	SwayAmp = FMath::FInterpTo(SwayAmp, bPulseRule ? Amp * BreathMul : 0.0f, DeltaSeconds, 4.0f);
	WobbleTime += DeltaSeconds * (BreathState == 2 ? 1.8f : 1.0f);
	const float T = WobbleTime;
	// el latido: un tiron corto hacia arriba con cada pulso (mas rapido cansado)
	const float Beat = FMath::Pow(FMath::Max(0.0f, FMath::Sin(T * 2.0f * PI * (1.1f + 1.3f * Exertion))), 12.0f) * (BreathState == 1 ? 0.3f : 1.0f);
	FRotator Want(SwayAmp * (0.7f * FMath::Sin(0.9f * T + 2.0f) + 0.3f * FMath::Sin(1.9f * T)) + SwayAmp * 0.5f * Beat,
		SwayAmp * (0.6f * FMath::Sin(1.1f * T) + 0.4f * FMath::Sin(2.3f * T + 1.0f)), 0.0f);
	Want *= FMath::Clamp(AimAlpha, 0.0f, 1.0f);
	if (PC && !bCine && !bDone && !bCapturing)
	{
		const FRotator Delta = Want - WobbleApplied;
		PC->SetControlRotation(PC->GetControlRotation() + Delta);
		WobbleApplied = Want;
	}
	else WobbleApplied = FRotator::ZeroRotator;
}

// ---------------------------------------------------------------- trampas

namespace
{
	float SegDist2D(const FVector& P, const FVector& A, const FVector& B)
	{
		const FVector2D p(P), a(A), b(B);
		const FVector2D ab = b - a;
		const float L2 = ab.SizeSquared();
		const float t = L2 > 1.0f ? FMath::Clamp(FVector2D::DotProduct(p - a, ab) / L2, 0.0f, 1.0f) : 0.0f;
		return FVector2D::Distance(p, a + ab * t);
	}
}

bool ATarsisDirector::NarrowAt(const FVector& Where, const FVector& Fwd, FVector& OutA, FVector& OutB) const
{
	// paso estrecho: pared a los dos lados, a menos de 1,6 m entre las dos
	const FVector Right = FVector::CrossProduct(FVector::UpVector, Fwd.GetSafeNormal2D());
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisTrampa), false);
	if (APawn* P = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(P);
	FHitResult HR, HL;
	const FVector E = Where + FVector(0.0f, 0.0f, 15.0f);
	if (!GetWorld()->LineTraceSingleByChannel(HR, E, E + Right * 160.0f, ECC_Visibility, Q)) return false;
	if (!GetWorld()->LineTraceSingleByChannel(HL, E, E - Right * 160.0f, ECC_Visibility, Q)) return false;
	if (HR.Distance + HL.Distance > 160.0f) return false;
	OutA = HL.ImpactPoint;
	OutB = HR.ImpactPoint;
	return true;
}

int32 ATarsisDirector::TrapNear() const
{
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P) return -1;
	for (int32 i = 0; i < Traps.Num(); ++i)
	{
		if (!Traps[i].bDead && FVector::Dist2D(P->GetActorLocation(), Traps[i].Loc) < 110.0f) return i;
	}
	return -1;
}

FString ATarsisDirector::TrapPrompt() const
{
	const ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || Dragged || bHiding || bRiding || bBoxOn || bCine || bDone) return FString();
	if (const int32 T = TrapNear(); T >= 0)
	{
		return Traps[T].Kind == 0 ? Tx(TEXT("p_trampa_recoger_latas"), TEXT("E   RECOGER LAS LATAS")) : Tx(TEXT("p_trampa_recoger_cable"), TEXT("E   RECOGER EL CABLE"));
	}
	if (!C->bIsCrouched) return FString();
	FVector A, B;
	const FVector Ahead = C->GetActorLocation() + C->GetActorForwardVector() * 70.0f;
	if (TrapWires > 0 && NarrowAt(Ahead, C->GetActorForwardVector(), A, B)) return Tx(TEXT("p_trampa_cable"), TEXT("E   TENDER EL CABLE (te quedan {0})"), { FString::FromInt(TrapWires) });
	if (TrapCans > 0) return Tx(TEXT("p_trampa_latas"), TEXT("E   COLGAR LAS LATAS (te quedan {0})"), { FString::FromInt(TrapCans) });
	return FString();
}

bool ATarsisDirector::PlaceTrap()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C) return false;
	const FVector Fwd = C->GetActorForwardVector().GetSafeNormal2D();
	FVector Ahead = C->GetActorLocation() + Fwd * 70.0f;
	// al suelo
	FHitResult H;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisTrampaSuelo), false, C);
	if (GetWorld()->LineTraceSingleByChannel(H, Ahead + FVector(0.0f, 0.0f, 50.0f), Ahead - FVector(0.0f, 0.0f, 250.0f), ECC_Visibility, Q)) Ahead = H.ImpactPoint;
	FTarsisTrap T;
	T.Loc = Ahead;
	FVector A, B;
	if (TrapWires > 0 && NarrowAt(Ahead, Fwd, A, B))
	{
		T.Kind = 1;
		T.A = FVector(A.X, A.Y, Ahead.Z + 12.0f);
		T.B = FVector(B.X, B.Y, Ahead.Z + 12.0f);
		--TrapWires;
	}
	else if (TrapCans > 0)
	{
		T.Kind = 0;
		// dos latas colgadas de un alambre entre dos estaquillas, a un palmo del suelo
		const FVector R = FVector::CrossProduct(FVector::UpVector, Fwd);
		T.A = Ahead - R * 45.0f;
		T.B = Ahead + R * 45.0f;
		--TrapCans;
	}
	else return false;
	BuildTrapParts(T);   // tanda J: las piezas, aparte (tambien al cargar el punto de control)
	Traps.Add(T);
	++TrapsSet;
	PlaySfx(TEXT("llaves"), Ahead + FVector(0.0f, 0.0f, 20.0f), 0.25f);
	Teach(TEXT("ensena_trampas"), TEXT("TRAMPA PUESTA\nLas latas suenan y atraen al que pasa y a los de cerca; el cable hace tropezar.\nCon buena luz, un guardia puede verla y quitarla. E junto a ella para recogerla."), {}, 4.0f);
	return true;
}

void ATarsisDirector::RemoveTrap(int32 Index)
{
	if (!Traps.IsValidIndex(Index)) return;
	for (const TWeakObjectPtr<UStaticMeshComponent>& W : Traps[Index].Parts)
	{
		if (UStaticMeshComponent* M = W.Get()) { TrapMeshes.Remove(M); M->DestroyComponent(); }
	}
	Traps.RemoveAt(Index);
}

bool ATarsisDirector::TrapInteract()
{
	if (const int32 T = TrapNear(); T >= 0)
	{
		if (Traps[T].Kind == 0) ++TrapCans; else ++TrapWires;
		PlaySfx(TEXT("llaves"), Traps[T].Loc + FVector(0.0f, 0.0f, 20.0f), 0.25f);
		RemoveTrap(T);
		return true;
	}
	const ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || !C->bIsCrouched || Dragged) return false;
	return PlaceTrap();
}

void ATarsisDirector::TrapTick(float DeltaSeconds)
{
	if (bCine || bDone) return;
	for (int32 i = Traps.Num() - 1; i >= 0; --i)
	{
		FTarsisTrap& T = Traps[i];
		// la ha visto uno: la desmonta en un momento y avisa
		if (ATarsisGuard* F = T.Finder.Get())
		{
			T.FindT += DeltaSeconds;
			if (T.FindT >= 2.5f || F->State == ETarsisGuardState::Down)
			{
				if (F->State != ETarsisGuardState::Down)
				{
					++TrapsFound;
					TensionT = FMath::Max(TensionT, 90.0f);   // alguien la ha puesto: la base queda en guardia
					PlaySfx(TEXT("llaves"), T.Loc + FVector(0.0f, 0.0f, 20.0f), 0.4f);
				}
				RemoveTrap(i);
			}
			continue;
		}
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			ATarsisGuard* G = *It;
			if (G->bTowerSentry || G->bAlly || G->State == ETarsisGuardState::Down || G->bStashed) continue;
			const FVector GL = G->GetActorLocation();
			const float D = FVector::Dist2D(GL, T.Loc);
			if (D > TrapSeeDist || FMath::Abs(GL.Z - T.Loc.Z) > 200.0f) continue;
			// ¿la pisa? latas: al pasar por el alambre; cable: al cruzarlo andando
			const bool bMoving = G->GetVelocity().Size2D() > 40.0f;
			const float Seg = SegDist2D(GL, T.A, T.B);
			if (bMoving && Seg < (T.Kind == 0 ? 35.0f : 28.0f) && !G->IsStunned())
			{
				++TrapsSprung;
				if (T.Kind == 0)
				{
					PlaySfx(TEXT("llaves"), T.Loc + FVector(0.0f, 0.0f, 20.0f), 1.0f);
					PlaySfx(TEXT("piedra"), T.Loc + FVector(0.0f, 0.0f, 20.0f), 0.8f);
					GuardSay(G, TEXT("lata"));
					for (TActorIterator<ATarsisGuard> O(GetWorld()); O; ++O)
					{
						if (O->bTowerSentry || O->bAlly || O->State == ETarsisGuardState::Down || O->State == ETarsisGuardState::Alert) continue;
						if (FVector::Dist(O->GetActorLocation(), T.Loc) < CanNoiseRadius) O->HearNoise(T.Loc);
					}
				}
				else
				{
					PlaySfx(TEXT("empujon"), GL + FVector(0.0f, 0.0f, 60.0f), 1.0f);
					G->Stun(WireStunSeconds);
					G->HitReact(G->GetVelocity().GetSafeNormal2D(), true);
					GuardSay(G, TEXT("tropiezo"));
					for (TActorIterator<ATarsisGuard> O(GetWorld()); O; ++O)
					{
						if (*O == G || O->bTowerSentry || O->bAlly || O->State == ETarsisGuardState::Down || O->State == ETarsisGuardState::Alert) continue;
						if (FVector::Dist(O->GetActorLocation(), GL) < NoiseRadius) O->HearNoise(GL);
					}
				}
				RemoveTrap(i);   // las latas por el suelo, el cable roto
				break;
			}
			// ¿la ve? delante, con luz, sin nada en medio y no encima
			if (G->State == ETarsisGuardState::Alert || D < 120.0f) continue;
			const FVector Eye = GL + FVector(0.0f, 0.0f, 70.0f);
			if (FVector::DotProduct(G->GetActorForwardVector(), (T.Loc - Eye).GetSafeNormal2D()) < 0.6f) continue;
			if (ATarsisGuard::LightAt(this, T.Loc + FVector(0.0f, 0.0f, 15.0f)) < TrapSeeLight) continue;
			FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisTrampaVer), false, G);
			FHitResult H;
			if (GetWorld()->LineTraceSingleByChannel(H, Eye, T.Loc + FVector(0.0f, 0.0f, 15.0f), ECC_Visibility, Q)) continue;
			T.Finder = G;
			T.FindT = 0.0f;
			G->Hold(3.0f);
			GuardSay(G, TEXT("trampa"), true);
			break;
		}
	}
}
