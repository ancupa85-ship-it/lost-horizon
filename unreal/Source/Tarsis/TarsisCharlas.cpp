// Lost Horizon: De Profundis - tanda 41: charlas que se oyen de cerca y mapa mental.
// Dos guardias dejan la ronda, se juntan en un sitio y hablan. De lejos solo se ve que hablan (un murmullo); a menos
// de TalkHearDist se oye cada frase. Algunas frases llevan un dato: al oirlas, el dato se apunta en la ficha del
// soldado al que se refiere (una bandera dato_<id>, que se guarda con el punto de control) y puede poner otra
// bandera que abra una opcion. Una charla se repite cada cierto tiempo mientras te falte alguno de sus datos.
// El mapa mental (tecla M) ensena una ficha por soldado con lo que sabes y lineas entre los que se relacionan.
// Todo sale de mision1.json (charlas, datos): el codigo no nombra a nadie.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

namespace
{
	ATarsisGuard* TalkGuard(UWorld* W, const FString& Name)
	{
		for (TActorIterator<ATarsisGuard> It(W); It; ++It)
		{
			if (!It->bTowerSentry && It->GuardName.Equals(Name, ESearchCase::IgnoreCase)) return *It;
		}
		return nullptr;
	}
}

bool ATarsisDirector::FactKnown(FName Id) const
{
	return HasFlag(FName(*(FString(TEXT("dato_")) + Id.ToString())));
}

int32 ATarsisDirector::FactsKnown() const
{
	int32 N = 0;
	for (const FTarsisFact& F : Facts) { if (FactKnown(F.Id)) ++N; }
	return N;
}

bool ATarsisDirector::LearnFact(FName Id)
{
	if (Id.IsNone() || FactKnown(Id)) return false;
	for (const FTarsisFact& F : Facts)
	{
		if (F.Id != Id) continue;
		SetFlag(FName(*(FString(TEXT("dato_")) + Id.ToString())));
		if (!F.Sets.IsNone()) SetFlag(F.Sets);
		++FactsLearned;
		LastFact = Id;
		PlaySfx(TEXT("tecla"), FVector::ZeroVector, 0.5f, false);
		ShowMessage(Tx(TEXT("mapa_nuevo"), TEXT("APUNTADO: {0}\n{1}\nM abre el mapa."), { F.Card.ToUpper(), Tx(F.Text, TEXT("")) }), 5.0f);
		return true;
	}
	return false;
}

bool ATarsisDirector::TalkPending(int32 Index) const
{
	// le queda algo que contarte: alguna de sus frases lleva un dato que aun no tienes
	if (!Talks.IsValidIndex(Index)) return false;
	for (const FName& F : Talks[Index].Facts) { if (!F.IsNone() && !FactKnown(F)) return true; }
	return false;
}

void ATarsisDirector::ToggleMindMap()
{
	if (bCodec || bMenu || bCine || bDone || bKeypad || bChoice || bCellAsk) return;
	bMindMap = !bMindMap;
	PlaySfx(TEXT("tecla"), FVector::ZeroVector, 0.4f, false);
}

void ATarsisDirector::EndTalk(bool bCut)
{
	if (TalkIdx < 0) return;
	if (TalkA) TalkA->EndErrandIn(bCut ? 0.0f : 1.5f);
	if (TalkB) TalkB->EndErrandIn(bCut ? 0.0f : 1.5f);
	if (bCut && TalkPhase == 1 && bTalkHeardAny) ShowMessage(Tx(TEXT("charla_cortada"), TEXT("SE CALLAN\nLa charla se corta. Volveran a hablar mas tarde.")), 3.5f);
	if (bCut) ++TalkCuts;
	TalkIdx = -1;
	TalkPhase = 0;
	TalkA = nullptr;
	TalkB = nullptr;
	TalkWait = TalkRetry;
}

bool ATarsisDirector::AtEmisora() const
{
	return bRadioTap && !bHiding && !RadioDead() && BaseState() == 0 && NearPlayer(EmisoraLoc, RadioTapDist);
}

bool ATarsisDirector::StartTalk(int32 Index)
{
	return Talks.IsValidIndex(Index) && StartTalkAt(Index, Talks[Index].Spot);
}

bool ATarsisDirector::StartTalkAt(int32 Index, const FVector& Spot)
{
	if (TalkIdx >= 0 || !Talks.IsValidIndex(Index)) return false;
	const FTarsisTalk& T = Talks[Index];
	ATarsisGuard* GA = TalkGuard(GetWorld(), T.A);
	ATarsisGuard* GB = TalkGuard(GetWorld(), T.B);
	if (!GA || !GB) return false;
	// cada uno a un lado del sitio, a un paso largo, mirandose
	const FVector Side = (GB->GetActorLocation() - GA->GetActorLocation()).GetSafeNormal2D();
	const FVector Dir = Side.IsNearlyZero() ? FVector(1.0f, 0.0f, 0.0f) : Side;
	const FVector PA = Spot - Dir * 65.0f, PB = Spot + Dir * 65.0f;
	if (!GA->Errand(PA, PB, TalkGather + T.Lines.Num() * (TalkLineSeconds + 3.0f) + 10.0f)) return false;
	if (!GB->Errand(PB, PA, TalkGather + T.Lines.Num() * (TalkLineSeconds + 3.0f) + 10.0f)) { GA->EndErrand(); return false; }
	TalkSpotNow = Spot;
	TalkIdx = Index;
	TalkPhase = 0;
	TalkLine = 0;
	TalkT = 0.0f;
	TalkA = GA;
	TalkB = GB;
	bTalkHeardAny = false;
	bTalkMurmur = false;
	++TalksStarted;
	return true;
}

void ATarsisDirector::TalkTick(float DeltaSeconds)
{
	if (!bTalkRule || Talks.Num() == 0) { if (TalkIdx >= 0) EndTalk(true); return; }
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Pl || bCine || bDone) return;
	if (TalkIdx < 0)
	{
		TalkWait -= DeltaSeconds;
		if (TalkWait > 0.0f) return;
		TalkWait = 2.0f;   // se vuelve a mirar cada dos segundos
		const bool bTap = AtEmisora();
		if (bTap) Teach(TEXT("ensena_escucha"), TEXT("A LA ESCUCHA\nCon la base tranquila, la emisora deja oir lo que hablan los soldados cuando se cruzan en sus rondas.\nQuedate junto a ella y espera."), {}, 7.0f);
		// la primera charla que tenga algo que contarte, con sus dos guardias de ronda y contigo por la zona
		for (int32 i = 0; i < Talks.Num(); ++i)
		{
			const int32 k = (TalkNext + i) % Talks.Num();
			const FTarsisTalk& T = Talks[k];
			if (MissionTime < T.After || !TalkPending(k)) continue;
			if (bTalkCross)
			{
				// tanda 47: se cruzan en sus rondas y tu andas cerca: se paran alli mismo
				ATarsisGuard* GA = TalkGuard(GetWorld(), T.A);
				ATarsisGuard* GB = TalkGuard(GetWorld(), T.B);
				if (GA && GB && GA->State == ETarsisGuardState::Patrol && GB->State == ETarsisGuardState::Patrol && !GA->IsOnErrand() && !GB->IsOnErrand())
				{
					const FVector Mid = (GA->GetActorLocation() + GB->GetActorLocation()) * 0.5f;
					if (FVector::Dist2D(GA->GetActorLocation(), GB->GetActorLocation()) < TalkCrossDist && (bTap || FVector::Dist2D(Pl->GetActorLocation(), Mid) < TalkNearDist)
						&& FMath::Abs(GA->GetActorLocation().Z - GB->GetActorLocation().Z) < 150.0f && StartTalkAt(k, FVector(Mid.X, Mid.Y, T.Spot.Z)))
					{
						++TalksCrossed;
						TalkCrossT = 0.0f;
						TalkNext = k + 1;
						break;
					}
				}
				// no se cruzan y llevas un rato por su zona: quedan donde siempre
				if (!bTap && FVector::Dist2D(Pl->GetActorLocation(), T.Spot) > TalkNearDist) continue;
				TalkCrossT += 2.0f;
				if (TalkCrossT < TalkCrossWait) continue;
				if (StartTalk(k)) { TalkCrossT = 0.0f; TalkNext = k + 1; break; }
				continue;
			}
			if (FVector::Dist2D(Pl->GetActorLocation(), T.Spot) > TalkStartDist) continue;
			if (StartTalk(k)) { TalkNext = k + 1; break; }
		}
		return;
	}
	const FTarsisTalk& T = Talks[TalkIdx];
	// uno de los dos ha dejado el recado (te ha visto, ha oido algo, lo han tumbado): se acabo
	if (!TalkA || !TalkB || !TalkA->IsOnErrand() || !TalkB->IsOnErrand()) { EndTalk(true); return; }
	TalkT += DeltaSeconds;
	if (TalkPhase == 0)
	{
		if (TalkA->AtErrand() && TalkB->AtErrand()) { TalkPhase = 1; TalkT = TalkLineSeconds - 1.0f; TalkLineWait = TalkLineSeconds; TalkLine = 0; }
		else if (TalkT > TalkGather) EndTalk(true);
		return;
	}
	if (TalkT < TalkLineWait) return;
	TalkT = 0.0f;
	TalkLineWait = TalkLineSeconds;
	if (TalkLine >= T.Lines.Num())
	{
		++TalksEnded;
		EndTalk(false);
		return;
	}
	const float D = FVector::Dist2D(Pl->GetActorLocation(), TalkSpotNow);
	const FString Who = T.Who.IsValidIndex(TalkLine) ? T.Who[TalkLine] : T.A;
	if (ATarsisGuard* Sp = Who.Equals(T.B, ESearchCase::IgnoreCase) ? TalkB.Get() : TalkA.Get()) Sp->PlayGesture(TEXT("pase"), 1.2f, (Sp == TalkA ? TalkB : TalkA)->GetActorLocation());
	const bool bTapNow = AtEmisora();
	if ((D < TalkHearDist && !bHiding) || bTapNow)
	{
		if (bTapNow && D >= TalkHearDist) ++TapLinesHeard;
		bTalkHeardAny = true;
		++TalkLinesHeard;
		PlaySfx(TEXT("rumor"), TalkSpotNow + FVector(0.0f, 0.0f, 150.0f), 0.5f);
		// tanda 42: las frases largas duran lo que se tarda en leerlas (16 letras por segundo), no 4 s justos
		const FString Said = Tx(T.Lines[TalkLine], TEXT("..."));
		TalkLineWait = FMath::Max(TalkLineSeconds, Said.Len() / 16.0f);
		SaySubtitle((bTapNow && D >= TalkHearDist) ? Tx(TEXT("escucha_quien"), TEXT("EMISORA - {0}"), { Who.ToUpper() }) : Who.ToUpper(), Said, TalkLineWait);
		if (T.Facts.IsValidIndex(TalkLine)) LearnFact(T.Facts[TalkLine]);
	}
	else if (D < TalkSeeDist)
	{
		PlaySfx(TEXT("rumor"), TalkSpotNow + FVector(0.0f, 0.0f, 150.0f), 0.35f);
		if (!bTalkMurmur)
		{
			bTalkMurmur = true;
			ShowSubtitleLine(Tx(TEXT("charla_murmullo"), TEXT("(Hablan en voz baja. Desde aqui no se entiende: acercate.)")), 4.0f);
		}
	}
	++TalkLine;
}
