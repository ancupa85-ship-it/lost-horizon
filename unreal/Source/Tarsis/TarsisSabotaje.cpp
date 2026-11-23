// Lost Horizon: De Profundis - tanda F. Parte de ATarsisDirector: ver el bloque «tanda F» de TarsisDirector.h.
// (1) Cuerpos que se echan de menos: entre 60 y 120 s despues de caer, su compañero (el de la ronda que se cruza con la
//     suya, o el de la garita) sale a buscarlo por su ronda, punto por punto. Si lo ve, el aviso de siempre; si no,
//     «ni rastro» por radio y la base queda en guardia. Sin red lo echa de menos igual, mas tarde y sin central.
// (2) Sabotaje con la E y tiempo de manipulacion: cortar el cable de la antena (sin red hasta que la empalmen) y abrir
//     la llave del gasoil (el chorro se oye de lejos y deja un charco donde se mojan las botas). Los dos dejan rastro.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

namespace
{
	const FName FlagAntena(TEXT("antena_cortada"));
	const FName FlagAntenaOk(TEXT("antena_reparada"));
	const FName FlagGasoil(TEXT("gasoil_abierto"));
	const FName FlagGasoilOk(TEXT("gasoil_cerrado"));

	bool Free(const ATarsisGuard* O)
	{
		return O && !O->bTowerSentry && !O->bAlly && !O->IsHeld() && !O->IsBusy() && !O->IsOnErrand()
			&& (O->State == ETarsisGuardState::Patrol || O->State == ETarsisGuardState::Return);
	}
}

// ---------------------------------------------------------------- ausencias

float ATarsisDirector::MissDelayOf(const ATarsisGuard* G) const
{
	if (!G) return MissMax;
	const float F = float(GetTypeHash(G->GuardName) % 1000) * 0.001f;   // fijo por guardia: unos tardan mas en faltar
	return FMath::Lerp(MissMin, FMath::Max(MissMin, MissMax), F);
}

ATarsisGuard* ATarsisDirector::BuddyOf(const ATarsisGuard* G) const
{
	if (!G) return nullptr;
	TArray<FVector> Mine = G->PatrolPoints;
	if (Mine.Num() == 0) Mine.Add(G->KnockLoc);
	ATarsisGuard* Best = nullptr;
	float BestS = TNumericLimits<float>::Max();
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* O = *It;
		if (O == G || !Free(O) || O == EmisoraFixer.Get() || O == ValveCloser.Get()) continue;
		// el que se cruza con el en su ronda (la parte de las dos rondas que mas se acerca) o, si nadie, el mas cercano
		float Cross = TNumericLimits<float>::Max();
		const TArray<FVector>& Theirs = O->PatrolPoints;
		for (const FVector& A : Mine)
		{
			if (Theirs.Num() == 0) Cross = FMath::Min(Cross, FVector::Dist2D(A, O->GetActorLocation()));
			for (const FVector& B : Theirs) Cross = FMath::Min(Cross, FVector::Dist2D(A, B));
		}
		float Near = TNumericLimits<float>::Max();
		for (const FVector& A : Mine) Near = FMath::Min(Near, FVector::Dist2D(A, O->GetActorLocation()));
		const float S = FMath::Min(Cross, 2500.0f) + 0.25f * Near;
		if (S < BestS) { BestS = S; Best = O; }
	}
	return Best;
}

ATarsisGuard* ATarsisDirector::MissSearcherOf(const ATarsisGuard* G) const
{
	for (const FTarsisMiss& M : Misses) if (M.Fallen.Get() == G) return M.Searcher.Get();
	return nullptr;
}

int32 ATarsisDirector::MissStepsOf(const ATarsisGuard* G) const
{
	for (const FTarsisMiss& M : Misses) if (M.Fallen.Get() == G) return M.Steps;
	return -1;
}

bool ATarsisDirector::StartMissSearch(ATarsisGuard* G, bool bRadio)
{
	if (!G || G->bTowerSentry || G->PatrolPoints.Num() == 0) return false;   // las torres: el relevo (TarsisRelevo.cpp)
	ATarsisGuard* S = BuddyOf(G);
	if (!S) return false;
	Missed.Add(G);
	FTarsisMiss M;
	M.Fallen = G;
	M.Searcher = S;
	M.bRadio = bRadio;
	if (const FVector* First = MissFirst.Find(G)) { M.Extra = *First; M.bExtra = true; }   // tanda G: iba de recado
	// empieza por el punto de su ronda que le queda mas cerca y la sigue en su orden
	float BestD = TNumericLimits<float>::Max();
	for (int32 i = 0; i < G->PatrolPoints.Num(); ++i)
	{
		const float D = FVector::Dist2D(G->PatrolPoints[i], S->GetActorLocation());
		if (D < BestD) { BestD = D; M.Start = i; }
	}
	Misses.Add(M);
	++MissSearches;
	if (bRadio)
	{
		// la central se lo dice por radio: «¿donde se ha metido?»
		if (RadioSnd) UGameplayStatics::PlaySoundAtLocation(this, RadioSnd, S->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 1.0f, 1.0f, 0.0f, Atten);
		TWeakObjectPtr<ATarsisGuard> W(S);
		FTimerHandle H;
		GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateWeakLambda(this, [this, W]() { if (W.IsValid()) GuardSay(W.Get(), TEXT("donde")); }), 2.2f, false);
	}
	else GuardSay(S, TEXT("falta"));   // sin red: cae en la cuenta el solo
	return true;
}

void ATarsisDirector::MissTick(float DeltaSeconds)
{
	for (int32 i = Misses.Num() - 1; i >= 0; --i)
	{
		FTarsisMiss& M = Misses[i];
		ATarsisGuard* G = M.Fallen.Get();
		ATarsisGuard* S = M.Searcher.Get();
		// encontrado (el aviso lo da LookForBodies/BodyTick, como siempre), despierto o lo has tumbado al que buscaba
		if (!G || G->State != ETarsisGuardState::Down || G->bFound)
		{
			if (S && S->IsOnErrand() && (!G || G->State != ETarsisGuardState::Down)) S->EndErrand();
			Misses.RemoveAt(i);
			continue;
		}
		if (!S || S->State == ETarsisGuardState::Down || S->bAlly || S->State == ETarsisGuardState::Alert)
		{
			Missed.Remove(G);   // saldra otro (ya ha pasado su tiempo: enseguida)
			Misses.RemoveAt(i);
			continue;
		}
		if (S->AtErrand())
		{
			// tanda G: abre las taquillas y cajones que tiene a mano en cada punto (solo asi se encuentra a uno escondido)
			if (!M.bOpened)
			{
				M.bOpened = true;
				OpenStashesNear(S, S->ErrandLoc, StashSearchDist);
				// tanda G: buscando a proposito mira alrededor (no solo hacia delante): un caido a la vista cerca, lo ve
				if (!S->BodyTarget) LookAroundFor(S, MissLookDist);
			}
			S->EndErrandIn(1.5f);
			continue;
		}
		if (S->IsOnErrand() || S->IsHeld() || S->IsBusy()) continue;
		if (S->State != ETarsisGuardState::Patrol && S->State != ETarsisGuardState::Return) continue;   // algo le ha distraido
		const int32 NR = G->PatrolPoints.Num();
		const int32 N = NR + (M.bExtra ? 1 : 0);
		if (M.Steps >= N)
		{
			// toda su ronda y ni rastro: lo dice por radio y la base queda en guardia; sin red se lo guarda
			const bool bNet = !RadioDead();
			GuardSay(S, bNet ? TEXT("nirastro") : TEXT("nirastro_solo"), bNet);
			if (bNet) TensionT = FMath::Max(TensionT, MissTension);
			++MissNotFound;
			Misses.RemoveAt(i);
			continue;
		}
		auto Pt = [&](int32 K) { return (M.bExtra && K == 0) ? M.Extra : G->PatrolPoints[(M.Start + K - (M.bExtra ? 1 : 0)) % NR]; };
		const FVector P = Pt(M.Steps);
		const FVector Q = Pt((M.Steps + 1) % N);
		const FVector Face = FVector::Dist2D(P, Q) > 10.0f ? Q : P + S->GetActorForwardVector() * 200.0f;
		// el tiempo del recado, segun lo lejos que este (a paso de ronda, con margen): si no, lo dejaba a medio camino
		const float Secs = 25.0f + FVector::Dist2D(S->GetActorLocation(), P) / 90.0f;
		if (S->Errand(P, Face, Secs)) { ++M.Steps; M.bOpened = false; }
	}
}

// ---------------------------------------------------------------- sabotaje

bool ATarsisDirector::AntennaCut() const
{
	return HasFlag(FlagAntena) && !HasFlag(FlagAntenaOk);
}

bool ATarsisDirector::ValveOpen() const
{
	return HasFlag(FlagGasoil) && !HasFlag(FlagGasoilOk);
}

float ATarsisDirector::SabotageProgress() const
{
	if (SabWork == 0) return 0.0f;
	return FMath::Clamp(SabT / FMath::Max(SabWork == 1 ? AntennaCutSeconds : ValveOpenSeconds, 0.1f), 0.0f, 1.0f);
}

void ATarsisDirector::SabotageSetup()
{
	bSabReady = true;
	SabTraces.Reset();
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		for (const FName& T : It->Tags)
		{
			if (T.ToString().StartsWith(TEXT("sabotaje_"))) { SabTraces.Add(*It); break; }
		}
	}
	UE_LOG(LogTemp, Log, TEXT("Tarsis: sabotaje: %d piezas de rastro"), SabTraces.Num());
}

void ATarsisDirector::ShowTrace(FName Tag, bool bShow)
{
	for (const TWeakObjectPtr<AActor>& W : SabTraces)
	{
		AActor* A = W.Get();
		if (!A || !A->ActorHasTag(Tag) || !A->GetRootComponent()) continue;
		if (A->GetRootComponent()->IsVisible() == bShow && A->IsHidden() == !bShow) continue;
		A->GetRootComponent()->SetVisibility(bShow, true);   // la calcomania del charco cuenta para las huellas solo visible
		A->SetActorHiddenInGame(!bShow);
	}
}

bool ATarsisDirector::SabotageTraceShown(FName Tag) const
{
	for (const TWeakObjectPtr<AActor>& W : SabTraces)
	{
		const AActor* A = W.Get();
		if (A && A->ActorHasTag(Tag)) return !A->IsHidden() && A->GetRootComponent() && A->GetRootComponent()->IsVisible();
	}
	return false;
}

FString ATarsisDirector::SabotagePrompt() const
{
	if (SabWork != 0)
	{
		const FString Pct = FString::FromInt(FMath::RoundToInt(SabotageProgress() * 100.0f));
		return SabWork == 1 ? Tx(TEXT("p_antena_cortando"), TEXT("CORTANDO EL CABLE... {0}%      E   DEJARLO"), { Pct })
			: Tx(TEXT("p_gasoil_abriendo"), TEXT("ABRIENDO LA LLAVE... {0}%      E   DEJARLO"), { Pct });
	}
	if (!HasFlag(FlagAntena) && NearPlayer(AntennaLoc, SabotageReach)) return Tx(TEXT("p_antena"), TEXT("E   CORTAR EL CABLE DE LA ANTENA (la base se queda sin radio)"));
	if (!HasFlag(FlagGasoil) && NearPlayer(ValveLoc, SabotageReach)) return Tx(TEXT("p_gasoil"), TEXT("E   ABRIR LA LLAVE DEL GASOIL (ruido y un charco)"));
	return FString();
}

bool ATarsisDirector::SabotageInteract()
{
	if (SabWork != 0)
	{
		SabWork = 0;
		SabT = 0.0f;
		ShowMessage(Tx(TEXT("sabotaje_dejado"), TEXT("LO DEJAS A MEDIAS")), 1.5f);
		return true;
	}
	if (!HasFlag(FlagAntena) && NearPlayer(AntennaLoc, SabotageReach))
	{
		SabWork = 1;
		SabT = 0.0f;
		PlaySfx(TEXT("llaves"), AntennaLoc + FVector(0.0f, 0.0f, 120.0f), 0.35f);
		return true;
	}
	if (!HasFlag(FlagGasoil) && NearPlayer(ValveLoc, SabotageReach))
	{
		SabWork = 2;
		SabT = 0.0f;
		PlaySfx(TEXT("candado"), ValveLoc + FVector(0.0f, 0.0f, 60.0f), 0.35f);
		return true;
	}
	return false;
}

void ATarsisDirector::SabotageDone(int32 Which)
{
	if (Which == 1)
	{
		SetFlag(FlagAntena);
		bAntennaSeen = false;
		PlaySfx(TEXT("candado"), AntennaLoc + FVector(0.0f, 0.0f, 120.0f), 0.6f);
		ShowMessage(Tx(TEXT("antena_cortada"), TEXT("CABLE DE LA ANTENA CORTADO\nLa base se queda sin radio: nadie puede avisar a la central ni pedir refuerzos.\nCuando lo noten, mandaran a uno a empalmarlo. Y sabran que hay alguien dentro.")), 6.0f);
		return;
	}
	SetFlag(FlagGasoil);
	bValveFirst = true;
	ValveNoiseT = 0.0f;
	ValveCloseT = 0.0f;
	ValveCloser = nullptr;
	PlaySfx(TEXT("candado"), ValveLoc + FVector(0.0f, 0.0f, 60.0f), 0.7f);
	ShowMessage(Tx(TEXT("gasoil_abierto"), TEXT("LLAVE DEL GASOIL ABIERTA\nEl chorro se oye de lejos: vendran a mirar.\nEl charco moja las botas: si lo pisas, dejaras huellas.")), 5.0f);
}

void ATarsisDirector::ValveFound(ATarsisGuard* G)
{
	ValveCloser = G;
	ValveCloseT = 0.0f;
	++SabotageFound;
	if (G->State != ETarsisGuardState::Alert) G->Hold(4.5f);   // persiguiendote no se para
	const bool bNet = !RadioDead();
	GuardSay(G, TEXT("gasoil"), bNet);
	if (bNet) TensionT = FMath::Max(TensionT, MissTension);   // nadie abre eso sin querer: la base queda en guardia
}

void ATarsisDirector::SabotageTick(float DeltaSeconds)
{
	if (!bSabReady) SabotageSetup();
	// los rastros siguen a las banderas (tambien al volver a un punto de control)
	const bool bCut = AntennaCut();
	ShowTrace(FName(TEXT("sabotaje_antena")), bCut);
	ShowTrace(FName(TEXT("sabotaje_antena_sano")), !bCut);
	ShowTrace(FName(TEXT("sabotaje_gasoil")), HasFlag(FlagGasoil));
	ShowTrace(FName(TEXT("sabotaje_chorro")), ValveOpen());
	// manipulando: quieto a su lado el tiempo que haga falta
	if (SabWork != 0)
	{
		const FVector At = SabWork == 1 ? AntennaLoc : ValveLoc;
		if (bCine || bDone || bCapturing || bHiding || !NearPlayer(At, SabotageReach + 40.0f))
		{
			SabWork = 0;
			SabT = 0.0f;
		}
		else
		{
			SabT += DeltaSeconds;
			if (SabT >= (SabWork == 1 ? AntennaCutSeconds : ValveOpenSeconds))
			{
				const int32 W = SabWork;
				SabWork = 0;
				SabT = 0.0f;
				SabotageDone(W);
			}
		}
	}
	if (bCine || bDone) return;
	// la antena: el que pasa de ronda junto a ella ve el cable colgando; ya no esperan: sale uno a empalmarlo
	if (bCut && !bAntennaSeen)
	{
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (It->bTowerSentry || It->bAlly || It->State == ETarsisGuardState::Down || It->State == ETarsisGuardState::Alert || *It == EmisoraFixer.Get()) continue;
			if (FVector::Dist2D(It->GetActorLocation(), AntennaLoc) > SabotageSeeDist) continue;
			bAntennaSeen = true;
			GuardSay(*It, TEXT("antena_ve"));
			RadioDeadT = FMath::Max(RadioDeadT, RadioDeadSeconds);
			break;
		}
	}
	// el gasoil: el chorro suena y atrae; el primero que llega lo ve, lo cierra y avisa
	const bool bOpen = ValveOpen();
	if (!bOpen)
	{
		if (ValveAudio) { ValveAudio->Stop(); ValveAudio = nullptr; }
		return;
	}
	if (!ValveAudio || !ValveAudio->IsPlaying())
	{
		if (USoundBase* S = Sfx(TEXT("lluvia"))) ValveAudio = UGameplayStatics::SpawnSoundAtLocation(this, S, ValveLoc + FVector(0.0f, 0.0f, 40.0f), FRotator::ZeroRotator, 0.9f, 1.25f, 0.0f, Atten);
	}
	ATarsisGuard* C = ValveCloser.Get();
	// el que la ha visto la cierra (un giro de volante) aunque luego eche a andar o la base entre en alerta; si no lo tumbas
	if (C && (C->State == ETarsisGuardState::Down || C->bAlly)) { ValveCloser = nullptr; C = nullptr; }
	if (C)
	{
		ValveCloseT += DeltaSeconds;
		if (ValveCloseT >= 3.5f)
		{
			SetFlag(FlagGasoilOk);
			PlaySfx(TEXT("candado"), ValveLoc + FVector(0.0f, 0.0f, 60.0f), 0.6f);
			ValveCloser = nullptr;
		}
		return;
	}
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->bTowerSentry || It->bAlly || It->State == ETarsisGuardState::Down) continue;
		if (FVector::Dist2D(It->GetActorLocation(), ValveLoc) > 330.0f) continue;
		ValveFound(*It);
		return;
	}
	ValveNoiseT -= DeltaSeconds;
	if (ValveNoiseT > 0.0f) return;
	ValveNoiseT = ValveNoiseEvery;
	// los mas cercanos que lo oyen van a mirar: dos la primera vez, luego uno
	TArray<ATarsisGuard*> Sent;
	const int32 Want = bValveFirst ? 2 : 1;
	for (int32 n = 0; n < Want; ++n)
	{
		ATarsisGuard* Best = nullptr;
		float BestD = ValveNoiseRadius;
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			ATarsisGuard* O = *It;
			if (Sent.Contains(O) || O->bTowerSentry || O->bAlly || O->IsHeld() || O->State == ETarsisGuardState::Down || O->State == ETarsisGuardState::Alert) continue;
			const float D = FVector::Dist2D(O->GetActorLocation(), ValveLoc);
			if (D < BestD) { BestD = D; Best = O; }
		}
		if (!Best) break;
		Sent.Add(Best);
		Best->HearNoise(ValveLoc);
	}
	if (Sent.Num() > 0) bValveFirst = false;
	else ValveNoiseT = 1.0f;   // nadie a tiro ahora: se vuelve a mirar enseguida
}
