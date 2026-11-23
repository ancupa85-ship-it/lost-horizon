// Lost Horizon: De Profundis — dos puzles de radio (tanda 32). Parte de ATarsisDirector: ver el bloque «tanda 32» de
// TarsisDirector.h. (1) La charla: Lobato, el nuevo, pregunta por la red que decir si le apuntan, y Carmona se lo
// explica; si andas cerca de uno de los dos te enteras de cual es la frase de coaccion antes de caer en ella.
// (2) La emisora: en transmisiones puedes dejar muda la red de la base. Sin red, la central no echa de menos a nadie
// ni da voces; al rato mandan a uno a arreglarla y, cuando vuelve, la base queda en guardia.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

namespace
{
	ATarsisGuard* GuardNamed(UWorld* W, const TCHAR* Name)
	{
		for (TActorIterator<ATarsisGuard> It(W); It; ++It)
		{
			if (!It->bTowerSentry && It->GuardName.Equals(Name, ESearchCase::IgnoreCase)) return *It;
		}
		return nullptr;
	}
}

bool ATarsisDirector::RadioDead() const
{
	// tanda F: o con el cable de la antena cortado
	return (HasFlag(FName(TEXT("emisora_muda"))) && !HasFlag(FName(TEXT("emisora_reparada")))) || AntennaCut();
}

void ATarsisDirector::RadioChatTick()
{
	if (!bRadioChat || bRadioChatOn || HasFlag(FName(TEXT("sabe_coaccion"))) || MissionTime < RadioChatAfter || RadioDead() || bRadioAsk) return;
	StartRadioChat(false);
}

bool ATarsisDirector::StartRadioChat(bool bForce)
{
	ATarsisGuard* L = GuardNamed(GetWorld(), TEXT("Lobato"));
	ATarsisGuard* C = GuardNamed(GetWorld(), TEXT("Carmona"));
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!L || !C || !Pl || bRadioChatOn) return false;
	if (!bForce)
	{
		// los dos de ronda y tu cerca de uno: si no, la charla espera (no se pierde por estar lejos)
		if (L->State != ETarsisGuardState::Patrol || C->State != ETarsisGuardState::Patrol || L->IsHeld() || C->IsHeld()) return false;
		const float D = FMath::Min(FVector::Dist(Pl->GetActorLocation(), L->GetActorLocation()), FVector::Dist(Pl->GetActorLocation(), C->GetActorLocation()));
		if (D > ParteHearDist) return false;
	}
	bRadioChatOn = true;
	++RadioChats;
	struct FLine { const TCHAR* Who; const TCHAR* Key; const TCHAR* Text; float At; };
	static const FLine Lines[] = {
		{ TEXT("Lobato"), TEXT("charla_1"), TEXT("Carmona, una cosa. Si me apuntan y no puedo hablar claro, que digo?"), 0.0f },
		{ TEXT("Carmona"), TEXT("charla_2"), TEXT("Todo tranquilo. Asi, tal cual. Aqui eso no lo dice nadie de verdad."), 4.5f },
		{ TEXT("Lobato"), TEXT("charla_3"), TEXT("Y entonces?"), 9.0f },
		{ TEXT("Carmona"), TEXT("charla_4"), TEXT("Entonces la central manda a los dos que tenga mas cerca. Y corta, que nos oye el sargento."), 11.5f },
	};
	for (const FLine& Ln : Lines)
	{
		const FString Who = Ln.Who, Key = Ln.Key, Text = Ln.Text;
		auto Say = [this, Who, Key, Text]()
		{
			if (bCine || bDone || RadioDead()) return;
			if (RadioSnd) UGameplayStatics::PlaySound2D(this, RadioSnd, 0.3f);
			SaySubtitle(FString::Printf(TEXT("%s (RADIO)"), *Who.ToUpper()), Tx(FName(*Key), *Text), 4.2f);
			LastVoice = Who.ToLower() + TEXT("_") + Key;
			VoiceLog.Add(LastVoice);
			if (VoiceLog.Num() > 30) VoiceLog.RemoveAt(0);
			if (Key == TEXT("charla_2")) SetFlag(FName(TEXT("sabe_coaccion")));   // ya lo sabes: se guarda con el punto de control
		};
		if (Ln.At <= 0.0f) { Say(); continue; }
		FTimerHandle H;
		GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateWeakLambda(this, Say), Ln.At, false);
	}
	CentralSay(TEXT("charla"), Tx(TEXT("charla_central"), TEXT("Lobato, Carmona: esta red no es para charlar.")), 17.0f);
	FTimerHandle End;
	GetWorldTimerManager().SetTimer(End, FTimerDelegate::CreateWeakLambda(this, [this]() { bRadioChatOn = false; }), 20.0f, false);
	return true;
}

void ATarsisDirector::EmisoraTick(float DeltaSeconds)
{
	if (!RadioDead())
	{
		RadioDeadT = 0.0f;
		EmisoraFixT = 0.0f;
		EmisoraFixer = nullptr;
		bEmisoraNoticed = false;
		return;
	}
	if (bCine || bDone) return;
	RadioDeadT += DeltaSeconds;
	// la pregunta de la central se queda sin central
	if (bRadioAsk) { bRadioAsk = false; RadioAskGuard = nullptr; MessageT = FMath::Min(MessageT, 0.3f); }
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	// a los 20 s, el que tengas mas cerca prueba la radio y no le da nada: se oye que ha funcionado
	if (!bEmisoraNoticed && RadioDeadT > 20.0f && Pl)
	{
		bEmisoraNoticed = true;
		ATarsisGuard* Near = nullptr;
		float NearD = TNumericLimits<float>::Max();
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (It->bTowerSentry || It->bAlly || It->State != ETarsisGuardState::Patrol) continue;
			const float D = FVector::Dist(It->GetActorLocation(), Pl->GetActorLocation());
			if (D < NearD) { NearD = D; Near = *It; }
		}
		if (Near) GuardSay(Near, TEXT("sinradio"), true);
	}
	if (RadioDeadT < RadioDeadSeconds) return;
	// mandan a uno a transmisiones (a pie: no hay red para avisarle, sale el que esta mas cerca)
	ATarsisGuard* F = EmisoraFixer.Get();
	if (F && (F->State == ETarsisGuardState::Down || F->bAlly))
	{
		// lo has tumbado: tardan en echarlo de menos y sale otro. Tanda G: el que lo busque empieza por la antena o la
		// emisora (adonde iba), y luego su ronda
		MissFirst.Add(F, F->ErrandLoc);
		EmisoraFixer = nullptr;
		EmisoraFixT = 0.0f;
		RadioDeadT = RadioDeadSeconds * 0.4f;
		return;
	}
	EmisoraSendT -= DeltaSeconds;
	// tanda F: si la emisora esta bien, lo que falla es la antena: el cable se empalma al pie del mastil
	const bool bAntenna = !(HasFlag(FName(TEXT("emisora_muda"))) && !HasFlag(FName(TEXT("emisora_reparada"))));
	const FVector Fix = bAntenna ? AntennaLoc : EmisoraLoc;
	const FVector Stand = bAntenna ? AntennaLoc + FVector(0.0f, EmisoraStand, 0.0f) : EmisoraLoc + FVector(EmisoraStand, 0.0f, 0.0f);
	if (!F)
	{
		if (EmisoraSendT > 0.0f) return;
		EmisoraSendT = 3.0f;
		float BestD = TNumericLimits<float>::Max();
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (It->bTowerSentry || It->bAlly || It->IsHeld() || It->IsBusy() || It->IsOnErrand()) continue;
			if (It->State != ETarsisGuardState::Patrol && It->State != ETarsisGuardState::Return) continue;
			const float D = FVector::Dist(It->GetActorLocation(), Fix);
			if (D < BestD) { BestD = D; F = *It; }
		}
		if (!F || !F->Errand(Stand, Fix, 600.0f)) return;
		EmisoraFixer = F;
		EmisoraFixT = 0.0f;
		++RadioRepairsSent;
		return;
	}
	if (!F->IsOnErrand())
	{
		// algo le ha distraido por el camino (un ruido, tu): cuando vuelva a su ronda, sigue hacia la emisora
		EmisoraFixT = 0.0f;
		if (EmisoraSendT <= 0.0f) { EmisoraSendT = 3.0f; F->Errand(Stand, Fix, 600.0f); }
		return;
	}
	if (!F->AtErrand()) return;
	if (EmisoraFixT <= 0.0f) GuardSay(F, bAntenna ? TEXT("antena") : TEXT("emisora"));
	EmisoraFixT += DeltaSeconds;
	if (EmisoraFixT < RadioFixSeconds) return;
	F->EndErrand();
	++RadioRepairs;
	EmisoraFixer = nullptr;
	EmisoraFixT = 0.0f;
	if (bAntenna)
	{
		// un cable cortado no es una valvula floja: hay alguien dentro
		SetFlag(FName(TEXT("antena_reparada")));
		TensionT = FMath::Max(TensionT, MissTension);
		CentralSay(TEXT("red"), Tx(TEXT("radio_red_antena"), TEXT("Vuelve la red. Han cortado el cable de la antena: hay alguien dentro. Todas las unidades, en guardia.")), 0.5f);
		return;
	}
	SetFlag(FName(TEXT("emisora_reparada")));
	TensionT = 90.0f;   // alguien la ha tocado: la base queda en guardia
	CentralSay(TEXT("red"), Tx(TEXT("radio_red"), TEXT("Vuelve la red. Alguien ha tocado la emisora. Todas las unidades: ojo, y parte uno por uno.")), 0.5f);
}
