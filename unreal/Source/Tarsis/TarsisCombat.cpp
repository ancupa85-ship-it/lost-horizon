// Lost Horizon: De Profundis — tanda 37: guardias armados con cabeza («Alto, o disparo») y escaleras de las torres.
// Antes, en alerta, el guardia corria hasta tocarte. Ahora (bArmedRule) usa el fusil: busca donde cubrirse, te apunta
// a distancia y da el alto. Quieto unos segundos, uno se acerca andando y te detiene (la captura de siempre). Si te
// mueves con el arma encima, disparan: cada impacto es una herida y a la tercera caes. Al dar el alto piden refuerzos
// por radio (si la emisora esta muda, no llegan) y el tiro lo oye media base. Si te pierden de vista aguantan en su
// sitio y luego avanzan andando, no a la carrera. Tocar a un guardia que te ve sigue siendo captura.
// La cobertura no usa nada de fuera: puntos del mapa de navegacion alrededor del guardia; vale el que tapa de cintura
// para abajo y deja ver por encima (cajas, muretes), o el que tiene una pared pegada a un lado (esquinas).
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "AIController.h"
#include "Navigation/PathFollowingComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

static ATarsisDirector* CombatDirector(const UObject* Ctx)
{
	for (TActorIterator<ATarsisDirector> It(Ctx->GetWorld()); It; ++It) return *It;
	return nullptr;
}

bool ATarsisGuard::FindCover(const FVector& Threat, FVector& Out) const
{
	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	if (!Nav) return false;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisCobertura), false, this);
	const FCollisionObjectQueryParams Statics(ECC_WorldStatic);
	const float HalfH = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FVector Chest = Threat + FVector(0.0f, 0.0f, 30.0f);
	float Best = TNumericLimits<float>::Max();
	bool bGotCover = false;
	for (int32 i = 0; i < 18; ++i)
	{
		FNavLocation P;
		if (!Nav->GetRandomReachablePointInRadius(GetActorLocation(), CoverRadius, P)) continue;
		const FVector L = P.Location;
		const float D = FVector::Dist2D(L, Threat);
		if (D < 450.0f || D > ArmedRange) continue;
		const bool bLow = GetWorld()->LineTraceTestByObjectType(L + FVector(0.0f, 0.0f, 55.0f), Chest, Statics, Q);
		const bool bHigh = !GetWorld()->LineTraceTestByObjectType(L + FVector(0.0f, 0.0f, 165.0f), Chest, Statics, Q);
		if (!bHigh) continue;   // desde ahi no te veria: no sirve para apuntar
		float Score = FVector::Dist2D(L, GetActorLocation()) + FMath::Abs(D - 1000.0f) * 0.3f;
		if (!bLow)
		{
			// sin murete delante: vale si hay una pared pegada a un lado (una esquina a la que arrimarse)
			const FVector Side = FVector::CrossProduct((Threat - L).GetSafeNormal2D(), FVector::UpVector);
			const FVector Mid = L + FVector(0.0f, 0.0f, 110.0f);
			if (!GetWorld()->LineTraceTestByObjectType(Mid, Mid + Side * 130.0f, Statics, Q) && !GetWorld()->LineTraceTestByObjectType(Mid, Mid - Side * 130.0f, Statics, Q)) continue;
			Score += 500.0f;
		}
		// no dos en el mismo sitio
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (*It != this && It->bHasCover && FVector::Dist2D(It->CoverLoc, L) < 250.0f) Score += 800.0f;
		}
		if (Score < Best) { Best = Score; Out = L + FVector(0.0f, 0.0f, HalfH); bGotCover = true; }
	}
	return bGotCover;
}

// En alerta y con la regla puesta. Devuelve si se ha ocupado el (si no, sigue el comportamiento de antes)
bool ATarsisGuard::ArmedTick(float DeltaSeconds, APawn* Player, float V)
{
	if (bAlly || bTowerSentry || !Player) return false;
	ATarsisDirector* D = CombatDirector(this);
	if (!D || !D->bArmedRule || D->bCapturing) return false;
	if (ShotT > 0.0f) ShotT -= DeltaSeconds;
	if (CoverT > 0.0f) CoverT -= DeltaSeconds;
	AAIController* AI = Cast<AAIController>(GetController());
	const FVector PL = Player->GetActorLocation();
	const float Dist = FVector::Dist2D(GetActorLocation(), PL);
	// tocarte es detenerte, pero solo si no vas huyendo: al que corre se le dispara, no se le atrapa al vuelo
	// (ni al que se cruza andando con uno que llega de refuerzo: ese da el alto primero, como los demas)
	const float PlSpeed = D->PlayerSpeedOverride >= 0.0f ? D->PlayerSpeedOverride : Player->GetVelocity().Size2D();
	if (V > 0.0f && Dist < CatchDistance && !D->bFleeing && (D->ArrestGuard == this || PlSpeed < 40.0f)) { Caught(Player); return true; }
	if (V <= 0.0f)
	{
		// no te ve: aguanta en su sitio mirando a donde te perdio y luego avanza andando. Si le mandaron por radio,
		// corre hasta estar cerca y el ultimo tramo lo hace con cuidado
		AimT = 0.0f;
		if (D->ArrestGuard == this && UnseenT > 1.0f) D->ArrestGuard = nullptr;   // un parpadeo de la vista no le hace desistir
		if (UnseenT < ArmedHoldSeconds && !bRadioCall)
		{
			if (AI && AI->GetMoveStatus() != EPathFollowingStatus::Idle) AI->StopMovement();
			FaceTowards(LastSeen, DeltaSeconds);
			return true;
		}
		const bool bFar = bRadioCall && !Near2D(LastSeen, 900.0f);
		Walk(LastSeen, bFar ? RunSpeed : WalkSpeed * 1.3f);
		if (Near2D(LastSeen, 120.0f) || UnseenT > 30.0f || (bRadioCall && StateT > 40.0f)) { bHasCover = false; SetState(ETarsisGuardState::Search); }
		return true;
	}
	// te ve
	if (D->ArrestGuard == this)
	{
		// te has quedado quieto: se acerca andando, sin dejar de apuntarte, y te detiene al llegar (Caught, en Tick)
		Walk(PL, WalkSpeed * 1.2f);
		D->ReportAim(this, Dist);
		return true;
	}
	// huyes y te tiene a tiro: se planta donde este y dispara, haya llegado o no a cubrirse
	if (D->bFleeing && Dist < ArmedRange)
	{
		if (AI && AI->GetMoveStatus() != EPathFollowingStatus::Idle) AI->StopMovement();
		FaceTowards(PL, DeltaSeconds);
		AimT += DeltaSeconds;
		D->ReportAim(this, Dist);
		if (AimT > 0.5f && ShotT <= 0.0f) FireAt(Player, Dist, V, D);
		return true;
	}
	// la cobertura se eligio para donde estabas: si te has movido mucho, ya no vale
	if (bHasCover && FVector::Dist2D(CoverThreat, PL) > 400.0f) { bHasCover = false; CoverT = FMath::Min(CoverT, 0.5f); }
	if (!bHasCover && CoverT <= 0.0f)
	{
		bHasCover = FindCover(PL, CoverLoc);
		CoverThreat = PL;
		CoverT = 3.0f;
		if (bHasCover) ++D->ArmedCovers;
	}
	// si desde su cobertura ya no te ve o te has acercado demasiado, buscara otra
	if (bHasCover && Near2D(CoverLoc, 80.0f) && Dist < 350.0f) { bHasCover = false; CoverT = 1.0f; }
	if (bHasCover && !Near2D(CoverLoc, 70.0f))
	{
		Walk(CoverLoc, RunSpeed);
		if (Dist < ArmedRange) D->ReportAim(this, Dist);   // va a cubrirse sin quitarte ojo: el alto vale igual
		AimT = 0.0f;
		return true;
	}
	if (!bHasCover && Dist > ArmedRange)
	{
		Walk(PL, RunSpeed);   // lejos y sin donde cubrirse: se acerca hasta tenerte a tiro, no mas
		return true;
	}
	// en su sitio: quieto, te encara y te apunta (UpdateAnim pone la pose de apuntar al estar parado en alerta)
	if (AI && AI->GetMoveStatus() != EPathFollowingStatus::Idle) AI->StopMovement();
	FaceTowards(PL, DeltaSeconds);
	AimT += DeltaSeconds;
	D->ReportAim(this, Dist);
	if (D->bFleeing && AimT > 0.5f && ShotT <= 0.0f) FireAt(Player, Dist, V, D);
	return true;
}

void ATarsisGuard::FireAt(APawn* Player, float Dist, float V, ATarsisDirector* D)
{
	ShotT = D->ShotInterval * FMath::FRandRange(0.8f, 1.3f);
	const ACharacter* C = Cast<ACharacter>(Player);
	float Chance = FMath::Clamp(1.05f - Dist / 2200.0f, 0.15f, 0.9f) * FMath::Lerp(0.5f, 1.0f, FMath::Clamp(V, 0.0f, 1.0f));
	if (C && C->bIsCrouched) Chance *= 0.7f;
	if (Player->GetVelocity().Size2D() > 400.0f) Chance *= 0.7f;
	D->ShotFired(this, FMath::FRand() < Chance * D->ArmedAim);
}

// ---------------------------------------------------------------- el director: el alto, las heridas y los refuerzos

void ATarsisDirector::ReportAim(ATarsisGuard* G, float Dist)
{
	if (!G || Dist > 2600.0f) return;
	AimHoldT = 0.35f;
	if (!Aimer || Dist < AimerDist || Aimer->State != ETarsisGuardState::Alert) { Aimer = G; AimerDist = Dist; }
	else if (Aimer == G) AimerDist = Dist;
}

void ATarsisDirector::ArmedTick(float DeltaSeconds)
{
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!bArmedRule || !Pl) return;
	if (HitFlashT > 0.0f) HitFlashT -= DeltaSeconds;
	if (AimHoldT > 0.0f) AimHoldT -= DeltaSeconds;
	const bool bAimed = AimHoldT > 0.0f && !bCapturing && !bDone && !bCine;
	const float Speed = PlayerSpeedOverride >= 0.0f ? PlayerSpeedOverride : Pl->GetVelocity().Size2D();
	if (bAimed)
	{
		UnaimedT = 0.0f;
		if (!bHalt)
		{
			bHalt = true;
			HaltT = StillT = 0.0f;
			++Halts;
			if (Aimer) GuardSay(Aimer, TEXT("alto"));
			Teach(TEXT("ensena_alto"), TEXT("TE APUNTAN\nQuieto, se acercan y te detienen. Si te mueves, disparan: rompe la linea de vision o cubrete."), {}, 6.0f);
			if (BackupT <= 0.0f && !bBackupSent) BackupT = BackupDelay;
		}
		HaltT += DeltaSeconds;
		if (Speed < 40.0f) StillT += DeltaSeconds;
		else { StillT = 0.0f; if (Speed > 120.0f) ArrestGuard = nullptr; }
		bFleeing = HaltT > HaltGrace && Speed > 120.0f;
		if (StillT > SurrenderSeconds && !ArrestGuard && Aimer)
		{
			ArrestGuard = Aimer;
			++Surrenders;
			ShowMessage(Tx(TEXT("alto_quieto"), TEXT("NO TE MUEVES\nUno de ellos se acerca a detenerte. Aun puedes echar a correr.")), 4.0f);
		}
	}
	else
	{
		bFleeing = false;
		if (bHalt)
		{
			UnaimedT += DeltaSeconds;
			if (UnaimedT > 2.5f) { bHalt = false; ArrestGuard = nullptr; Aimer = nullptr; }
		}
	}
	// refuerzos: los pide por radio el que te apunta; con la emisora muda no hay a quien pedirlos
	if (BackupT > 0.0f)
	{
		BackupT -= DeltaSeconds;
		if (BackupT <= 0.0f && !bBackupSent)
		{
			bBackupSent = true;
			if (RadioDead()) { if (Aimer) GuardSay(Aimer, TEXT("sinradio")); }
			else
			{
				const FVector Where = Pl->GetActorLocation();
				TArray<ATarsisGuard*> Free;
				for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
				{
					if (It->bTowerSentry || It->bAlly || It->HoldT > 0.0f) continue;
					if (It->State == ETarsisGuardState::Down || It->State == ETarsisGuardState::Alert) continue;
					Free.Add(*It);
				}
				Free.Sort([&Where](const ATarsisGuard& A, const ATarsisGuard& B) { return FVector::DistSquared(A.GetActorLocation(), Where) < FVector::DistSquared(B.GetActorLocation(), Where); });
				for (int32 i = 0; i < Free.Num() && i < BackupCount; ++i) { Free[i]->Alarm(Where); Free[i]->bRadioCall = true; ++ArmedBackups; }
				TensionT = FMath::Max(TensionT, 120.0f);
				CentralSay(TEXT("refuerzos"), Tx(TEXT("radio_refuerzos"), TEXT("Intruso a la vista. Las unidades mas cercanas, a apoyar. El resto, cada uno en su puesto.")));
			}
		}
	}
	// sin nadie en alerta, la proxima vez pueden volver a pedirlos
	if (bBackupSent && !bHalt && BaseState() < 2) bBackupSent = false;
	// las heridas se pasan si te dejan en paz
	if (Wounds > 0 && !bHalt)
	{
		WoundT += DeltaSeconds;
		if (WoundT > WoundHealSeconds) { --Wounds; WoundT = 0.0f; }
	}
}

void ATarsisDirector::ShotFired(ATarsisGuard* G, bool bHit)
{
	if (!G || bCapturing || bDone) return;
	++Shots;
	const FVector Muzzle = G->GetActorLocation() + G->GetActorForwardVector() * 60.0f + FVector(0.0f, 0.0f, 50.0f);
	PlaySfx(TEXT("disparo"), Muzzle, 1.0f);
	ShotFlashT = 0.08f;
	ShotFlashAt = Muzzle;
	TensionT = FMath::Max(TensionT, 120.0f);
	// el tiro se oye: los que esten cerca y libres acuden
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (*It == G || It->bTowerSentry || It->bAlly || It->HoldT > 0.0f || It->State == ETarsisGuardState::Down || It->State == ETarsisGuardState::Alert) continue;
		if (FVector::Dist(It->GetActorLocation(), Muzzle) < ShotHeard) It->HearNoise(Muzzle);
	}
	if (!bHit || !Pl) return;
	++Hits;
	++Wounds;
	WoundT = 0.0f;
	HitFlashT = 0.6f;
	PlaySfx(TEXT("golpe"), Pl->GetActorLocation(), 0.9f, false);
	if (Wounds >= MaxWounds)
	{
		Wounds = 0;
		bHalt = false;
		ArrestGuard = nullptr;
		ShowMessage(Tx(TEXT("herido_cae"), TEXT("CAES\nEl tercer tiro te tumba. Vienen a por ti.")), 3.0f);
		BeginCapture(G);
		return;
	}
	ShowMessage(Tx(TEXT("herido"), TEXT("HERIDO {0}/{1}\nCubrete o quedate quieto."), { Wounds, MaxWounds }), 3.0f);
}

// ---------------------------------------------------------------- las escaleras de las torres

int32 ATarsisDirector::LadderNear(bool& bTop) const
{
	const APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	bTop = false;
	if (!Pl || bClimbing || bRiding) return INDEX_NONE;
	const FVector P = Pl->GetActorLocation();
	for (int32 i = 0; i < Ladders.Num() && i < LadderTops.Num(); ++i)
	{
		if (FVector::Dist2D(P, Ladders[i]) < 150.0f && P.Z < Ladders[i].Z + 250.0f) return i;
		if (FVector::Dist2D(P, LadderTops[i]) < 90.0f && FMath::Abs(P.Z - LadderTops[i].Z) < 200.0f) { bTop = true; return i; }
	}
	return INDEX_NONE;
}

FString ATarsisDirector::LadderPrompt() const
{
	bool bTop = false;
	if (LadderNear(bTop) == INDEX_NONE) return FString();
	return bTop ? Tx(TEXT("p_bajar_torre"), TEXT("E   BAJAR POR LA ESCALERA")) : Tx(TEXT("p_subir_torre"), TEXT("E   SUBIR A LA TORRE"));
}

bool ATarsisDirector::LadderInteract()
{
	bool bTop = false;
	const int32 i = LadderNear(bTop);
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (i == INDEX_NONE || !C) return false;
	if (C->bIsCrouched) C->UnCrouch();
	StopDrag();
	const float HalfH = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	bClimbing = true;
	bClimbUp = !bTop;
	ClimbT = 0.0f;
	ClimbBase = Ladders[i] + FVector(0.0f, 0.0f, HalfH + 5.0f);
	ClimbTop = LadderTops[i] + FVector(0.0f, 0.0f, HalfH + 5.0f);
	C->GetCharacterMovement()->SetMovementMode(MOVE_None);
	++Climbs;
	return true;
}

// Subir es lento y a la vista: primero la vertical pegado a la escalera, y arriba un paso hasta la plataforma
void ATarsisDirector::ClimbTick(float DeltaSeconds)
{
	if (!bClimbing) return;
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || bCapturing) { bClimbing = false; if (C) C->GetCharacterMovement()->SetMovementMode(MOVE_Walking); return; }
	ClimbT += DeltaSeconds;
	const float A = FMath::Clamp(ClimbT / FMath::Max(ClimbSeconds, 0.1f), 0.0f, 1.0f);
	const float U = bClimbUp ? A : 1.0f - A;   // 0 abajo, 1 arriba
	const FVector Rail(ClimbBase.X, ClimbBase.Y, ClimbTop.Z);
	const FVector P = U < 0.8f ? FMath::Lerp(ClimbBase, Rail, U / 0.8f) : FMath::Lerp(Rail, ClimbTop, (U - 0.8f) / 0.2f);
	C->SetActorLocation(P, false, nullptr, ETeleportType::TeleportPhysics);
	if (FMath::Fmod(ClimbT, 0.55f) < DeltaSeconds) PlaySfx(FString::Printf(TEXT("paso_metal_%d"), FMath::RandRange(1, 3)), P - FVector(0.0f, 0.0f, 80.0f), 0.5f);
	if (A >= 1.0f)
	{
		bClimbing = false;
		C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	}
}
