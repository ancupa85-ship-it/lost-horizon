// Lost Horizon: De Profundis - tanda D (2026-11-22): el relevo de los puestos fijos.
//
// Cada centinela de torre se releva cada ReliefEvery segundos, escalonado por puesto. Del barracon sale el relevo (un
// guardia nuevo, copia del centinela: misma persona, fusil y ajustes), anda hasta el pie de la escalera; el saliente
// baja, se dicen el santo y sena (se oye de cerca: TalkHearDist) y, tras un rato, el relevo sube y el saliente se va
// al barracon. Desde que el saliente deja la plataforma hasta que sube el relevo el puesto esta vacio (unos 20-40 s):
// la ventana del jugador. Si el relevo no encuentra a nadie (dormido, escondido, arrastrado), busca por la zona, avisa
// por radio a Control y, si en ReliefMissingSeconds no aparece, la base pasa a tension (alerta de nivel 1): la base
// echa de menos a los suyos.
// El santo y sena oido se apunta en el mapa mental (ficha «Relevos»), y el cuadrante del barracon (punto que se lee
// con la E) apunta la hora del proximo relevo de cada torre (se actualiza sola en la ficha).
// Enfoque: un horario por puesto (proximo relevo, fase) como las franjas de las rutinas de PNJ, y una regla de «uno por
// puesto»: el saliente no se va hasta que ha llegado el relevo.
// Textos solo en ASCII.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "AIController.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/UnrealType.h"

namespace
{
	// santo y sena del dia: el centinela pide uno y el relevo contesta (cambian con la noche de la mision)
	const TCHAR* GPassA[] = { TEXT("Ceniza"), TEXT("Nevero"), TEXT("Alcotan"), TEXT("Tolva"), TEXT("Brezo") };
	const TCHAR* GPassB[] = { TEXT("Invierno"), TEXT("Candil"), TEXT("Sierra"), TEXT("Ancla"), TEXT("Pizarra") };
}

// ---- en el guardia: dejar el puesto y tomarlo

void ATarsisGuard::LeaveTowerPost(const FVector& Ground)
{
	// baja por la escalera: queda al pie, como un guardia de suelo, y puede andar
	bTowerSentry = false;
	TowerLight = nullptr;
	SetActorLocation(Ground + FVector(0.0f, 0.0f, GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 5.0f), false, nullptr, ETeleportType::TeleportPhysics);
	if (UCharacterMovementComponent* M = GetCharacterMovement()) M->SetMovementMode(MOVE_Walking);
	PatrolPoints.Reset();
	PatrolPoints.Add(Ground);
	PointIndex = 0;
	Home = Ground;
	MoveDest = FVector(1e9f);
}

void ATarsisGuard::TakeTowerPost(ATarsisGuard* From, const FVector& Post, const FRotator& Rot, AActor* Light)
{
	// sube: en el sitio del saliente, con su foco, sin caer ni andar
	if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
	if (bErrand) EndErrand();
	SetActorLocationAndRotation(Post, Rot, false, nullptr, ETeleportType::TeleportPhysics);
	bTowerSentry = true;
	TowerLight = Light;
	if (From)
	{
		TowerYaw = From->TowerYaw;
		TowerT = From->TowerT;
		LightPitch = From->LightPitch;
		SweepAim = From->SweepAim;
		BeamLumens = From->BeamLumens;
		BeamPaint = From->BeamPaint;
	}
	if (UCharacterMovementComponent* M = GetCharacterMovement()) M->DisableMovement();
	PatrolPoints.Reset();
	PatrolPoints.Add(Post);
	PointIndex = 0;
	Home = Post;
	if (State != ETarsisGuardState::Patrol) SetState(ETarsisGuardState::Patrol);
}

// ---- en el director: el horario de relevos

ATarsisGuard* ATarsisDirector::SpawnRelief(ATarsisGuard* Src, const FVector& At)
{
	if (!Src || !GetWorld()) return nullptr;
	const FTransform Xf(FRotator::ZeroRotator, At + FVector(0.0f, 0.0f, 100.0f));
	ATarsisGuard* R = GetWorld()->SpawnActorDeferred<ATarsisGuard>(Src->GetClass(), Xf, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn);
	if (!R) return nullptr;
	// la misma persona, el mismo fusil y los mismos ajustes que el centinela: todo lo editable del guardia (no lo de
	// Actor ni Character, ni componentes)
	for (TFieldIterator<FProperty> P(Src->GetClass()); P; ++P)
	{
		FProperty* Prop = *P;
		if (!Prop->HasAnyPropertyFlags(CPF_Edit) || Prop->HasAnyPropertyFlags(CPF_Transient | CPF_InstancedReference | CPF_ContainsInstancedReference)) continue;
		const UClass* PropOwner = Prop->GetOwnerClass();
		if (!PropOwner || !PropOwner->IsChildOf(ATarsisGuard::StaticClass())) continue;
		if (const FObjectPropertyBase* OP = CastField<FObjectPropertyBase>(Prop)) { if (OP->PropertyClass && OP->PropertyClass->IsChildOf(UActorComponent::StaticClass())) continue; }
		Prop->CopyCompleteValue_InContainer(R, Src);
	}
	R->bTowerSentry = false;
	R->TowerLight = nullptr;
	R->PatrolPoints.Reset();
	R->PatrolPoints.Add(At);
	R->GuardName = Src->GuardName;   // el puesto se llama igual con quien lo tenga
	UGameplayStatics::FinishSpawningActor(R, Xf);
	++ReliefsSpawned;
	return R;
}

void ATarsisDirector::SetupRelief()
{
	bReliefReady = true;
	ReliefPosts.Reset();
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (!It->bTowerSentry || It->bAlly) continue;
		FTarsisPost P;
		P.Sentry = *It;
		P.Name = It->GuardName;
		P.Loc = It->GetActorLocation();
		P.Rot = It->GetActorRotation();
		P.Light = It->TowerLight;
		// la escalera de su torre: la mas cercana
		float Best = 1e12f;
		for (int32 k = 0; k < Ladders.Num(); ++k)
		{
			const float D = FVector::DistSquared2D(Ladders[k], P.Loc);
			if (D < Best) { Best = D; P.Ladder = Ladders[k]; }
		}
		if (Best > FMath::Square(2500.0f)) P.Ladder = FVector(P.Loc.X, P.Loc.Y, 0.0f);
		ReliefPosts.Add(P);
	}
	// orden fijo (por nombre) y escalonados: el primero a los ReliefFirst segundos, luego repartidos en ReliefEvery
	ReliefPosts.Sort([](const FTarsisPost& A, const FTarsisPost& B) { return A.Name < B.Name; });
	for (int32 i = 0; i < ReliefPosts.Num(); ++i)
	{
		ReliefPosts[i].NextAt = MissionTime + ReliefFirst + ReliefEvery * i / FMath::Max(1, ReliefPosts.Num());
	}
	// santo y sena de esta noche
	PasswordA = GPassA[ReliefNight % UE_ARRAY_COUNT(GPassA)];
	PasswordB = GPassB[ReliefNight % UE_ARRAY_COUNT(GPassB)];
	// los datos del mapa mental y los textos, si no vienen ya en mision1.json
	auto AddFact = [this](FName Id, FName Text, FName Kind)
	{
		for (const FTarsisFact& F : Facts) { if (F.Id == Id) return; }
		FTarsisFact F;
		F.Id = Id;
		F.Card = TEXT("Relevos");
		F.Text = Text;
		F.Kind = Kind;
		Facts.Add(F);
	};
	AddFact(TEXT("relevo_santo"), TEXT("dt_relevo_santo"), TEXT("costumbre"));
	AddFact(TEXT("relevo_cuadrante"), TEXT("dt_relevo_cuadrante"), TEXT("horario"));
	if (!Texts.Contains(TEXT("p_cuadrante"))) Texts.Add(TEXT("p_cuadrante"), TEXT("E   LEER EL CUADRANTE DE RELEVOS"));
	// el cuadrante: un papel en la pared del barracon, en la mas cercana a BarracksLoc
	FVector Wall = BarracksLoc;
	FVector Normal = FVector(0.0f, 1.0f, 0.0f);
	float Near = 1e9f;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisCuadrante), false, this);
	if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
	for (int32 k = 0; k < 8; ++k)
	{
		const FVector Dir = FRotator(0.0f, k * 45.0f, 0.0f).Vector();
		FHitResult Hit;
		const FVector From = BarracksLoc + FVector(0.0f, 0.0f, 150.0f);
		if (GetWorld()->LineTraceSingleByChannel(Hit, From, From + Dir * 700.0f, ECC_Visibility, Q) && Hit.Distance < Near && FMath::Abs(Hit.ImpactNormal.Z) < 0.3f)
		{
			Near = Hit.Distance;
			Wall = Hit.ImpactPoint;
			Normal = Hit.ImpactNormal;
		}
	}
	RosterLoc = Wall + Normal * 2.0f;
	if (UStaticMeshComponent* Paper = AddBlock(RosterLoc, FVector(0.02f, 0.32f, 0.42f), FLinearColor(0.82f, 0.8f, 0.7f), false))
	{
		Paper->SetWorldRotation(Normal.Rotation());
	}
	bool bHas = false;
	for (const FTarsisPoint& Pt : Points) { if (Pt.Id == TEXT("cuadrante_relevos")) bHas = true; }
	if (!bHas)
	{
		FTarsisPoint Pt;
		Pt.Id = TEXT("cuadrante_relevos");
		Pt.Pos = FVector(RosterLoc.X, RosterLoc.Y, 0.0f) + Normal * 60.0f;
		Pt.Radius = 170.0f;
		Pt.Prompt = TEXT("p_cuadrante");
		Pt.Sets = TEXT("cuadrante_leido");
		Pt.bRepeat = true;
		Pt.Sound = TEXT("papel");
		Pt.Text = TEXT("nota_cuadrante");
		Pt.TextSeconds = 8.0f;
		Points.Add(Pt);
	}
	ReliefTexts();
	UE_LOG(LogTemp, Log, TEXT("Tarsis: relevo: %d puestos, santo y sena %s / %s, cuadrante en %s"), ReliefPosts.Num(), *PasswordA, *PasswordB, *RosterLoc.ToString());
}

FString ATarsisDirector::ClockText(float Seconds) const
{
	// la hora de la noche: la mision empieza a las ClockStartHour (horas y minutos)
	const int32 Total = FMath::FloorToInt(ClockStartHour * 3600.0f + Seconds);
	return FString::Printf(TEXT("%02d:%02d"), (Total / 3600) % 24, (Total / 60) % 60);
}

void ATarsisDirector::ReliefTexts()
{
	// lo que dicen la ficha y el cuadrante: siempre al dia (el HUD lo lee cada vez)
	Texts.Add(TEXT("dt_relevo_santo"), FString::Printf(TEXT("Santo y sena de esta noche: piden \"%s\", se contesta \"%s\"."), *PasswordA, *PasswordB));
	FString Rows;
	for (const FTarsisPost& P : ReliefPosts)
	{
		Rows += FString::Printf(TEXT("%s: %s. "), *P.Name.ToUpper(), *ClockText(P.NextAt));
	}
	Texts.Add(TEXT("dt_relevo_cuadrante"), FString::Printf(TEXT("Proximos relevos (cada %d min): %s"), FMath::RoundToInt(ReliefEvery / 60.0f), *Rows));
	Texts.Add(TEXT("nota_cuadrante"), FString::Printf(TEXT("CUADRANTE DE RELEVOS\nCada torre, cada %d minutos. Ahora son las %s.\n%s"), FMath::RoundToInt(ReliefEvery / 60.0f), *ClockText(MissionTime), *Rows));
}

void ATarsisDirector::ReliefSay(FTarsisPost& P, ATarsisGuard* G, const FString& Line)
{
	// como las charlas: de cerca se oye cada frase; de mas lejos, un murmullo
	if (!G) return;
	const APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	const float D = Pl ? FVector::Dist(Pl->GetActorLocation(), G->GetActorLocation()) : 1e9f;
	if (D < TalkHearDist)
	{
		SaySubtitle(G->GuardName.ToUpper(), Line, 3.2f);
		++ReliefLinesHeard;
		P.bHeard = true;
	}
	else if (D < TalkSeeDist && !P.bMurmur)
	{
		P.bMurmur = true;
		ShowSubtitleLine(Tx(TEXT("relevo_murmullo"), TEXT("(Al pie de la torre hablan en voz baja: el relevo.)")), 3.0f);
	}
}

void ATarsisDirector::ForceRelief(int32 Index)
{
	if (!bReliefReady) SetupRelief();
	if (ReliefPosts.IsValidIndex(Index) && ReliefPosts[Index].Phase == 0) ReliefPosts[Index].NextAt = MissionTime;
}

int32 ATarsisDirector::ReliefPhase(int32 Index) const
{
	return ReliefPosts.IsValidIndex(Index) ? ReliefPosts[Index].Phase : -1;
}

bool ATarsisDirector::ReliefPostEmpty(int32 Index) const
{
	if (!ReliefPosts.IsValidIndex(Index)) return false;
	const ATarsisGuard* S = ReliefPosts[Index].Sentry.Get();
	return !S || !S->bTowerSentry || S->State == ETarsisGuardState::Down || FVector::Dist(S->GetActorLocation(), ReliefPosts[Index].Loc) > 300.0f;
}

float ATarsisDirector::ReliefNextIn(int32 Index) const
{
	return ReliefPosts.IsValidIndex(Index) ? ReliefPosts[Index].NextAt - MissionTime : -1.0f;
}

ATarsisGuard* ATarsisDirector::ReliefSentry(int32 Index) const
{
	return ReliefPosts.IsValidIndex(Index) ? ReliefPosts[Index].Sentry.Get() : nullptr;
}

ATarsisGuard* ATarsisDirector::ReliefGuard(int32 Index) const
{
	return ReliefPosts.IsValidIndex(Index) ? ReliefPosts[Index].Relief.Get() : nullptr;
}

void ATarsisDirector::ReliefTick(float DeltaSeconds)
{
	if (!bReliefRule) return;
	if (!bReliefReady) { if (MissionTime > 1.0f) SetupRelief(); return; }
	// el cuadrante leido: al mapa mental
	if (HasFlag(TEXT("cuadrante_leido")) && !FactKnown(TEXT("relevo_cuadrante"))) LearnFact(TEXT("relevo_cuadrante"));
	ReliefTextT -= DeltaSeconds;
	if (ReliefTextT <= 0.0f) { ReliefTextT = 1.0f; ReliefTexts(); }
	if (bCine || bDone) return;
	for (int32 i = 0; i < ReliefPosts.Num(); ++i)
	{
		FTarsisPost& P = ReliefPosts[i];
		P.T += DeltaSeconds;
		ATarsisGuard* S = P.Sentry.Get();
		ATarsisGuard* R = P.Relief.Get();
		switch (P.Phase)
		{
		case 0:
			// esperando su hora (con la base en alerta no se releva nadie: se aplaza un poco)
			if (MissionTime < P.NextAt) break;
			if (BaseState() == 2 || bCapturing) { P.NextAt = MissionTime + 30.0f; break; }
			if (!S) { P.NextAt = MissionTime + ReliefEvery; break; }
			R = SpawnRelief(S, BarracksLoc);
			if (!R) { P.NextAt = MissionTime + ReliefEvery; break; }
			P.Relief = R;
			P.Phase = 1;
			P.T = 0.0f;
			P.bHeard = P.bMurmur = false;
			break;
		case 1:
			// el relevo va del barracon al pie de la escalera
			if (!R || R->State == ETarsisGuardState::Down) { P.Phase = 0; P.NextAt = MissionTime + ReliefEvery; break; }
			if (!R->IsOnErrand() && R->State == ETarsisGuardState::Patrol && !R->Errand(P.Ladder, P.Loc, 240.0f)) break;
			if (R->State != ETarsisGuardState::Patrol) { if (P.T > 240.0f) { P.Phase = 0; P.NextAt = MissionTime + ReliefEvery; } break; }
			if (!R->AtErrand() && P.T < 240.0f) break;
			// ha llegado: ¿esta el centinela en su sitio?
			if (!S || S->State == ETarsisGuardState::Down || !S->bTowerSentry || FVector::Dist(S->GetActorLocation(), P.Loc) > 300.0f)
			{
				P.Phase = 10;
				P.T = 0.0f;
				GuardSay(R, TEXT("relevo_vacio"));
				break;
			}
			// baja el saliente: desde ahora el puesto esta vacio
			S->LeaveTowerPost(P.Ladder + FRotator(0.0f, FMath::FRandRange(0.0f, 360.0f), 0.0f).Vector() * 110.0f);
			S->Errand(S->GetActorLocation(), R->GetActorLocation(), 60.0f);
			P.EmptySince = MissionTime;
			P.Phase = 2;
			P.T = 0.0f;
			P.Line = 0;
			break;
		case 2:
		{
			// la charla al pie de la torre, con el santo y sena
			if (!S || !R) { P.Phase = 4; P.T = 0.0f; break; }
			const float Every = 3.4f;
			if (P.T > Every * P.Line && P.Line < 4)
			{
				switch (P.Line)
				{
				case 0: ReliefSay(P, S, Tx(TEXT("relevo_l0"), TEXT("Alto. Santo y sena."))); break;
				case 1: ReliefSay(P, S, FString::Printf(TEXT("%s."), *PasswordA)); break;
				case 2: ReliefSay(P, R, FString::Printf(TEXT("%s. Te relevo."), *PasswordB)); break;
				default: ReliefSay(P, S, Tx(TEXT("relevo_l3"), TEXT("Todo tranquilo. El foco tira a la izquierda. Ahi lo tienes."))); break;
				}
				++P.Line;
				if (P.Line == 3 && P.bHeard && !FactKnown(TEXT("relevo_santo"))) LearnFact(TEXT("relevo_santo"));
			}
			if (P.Line >= 4 && P.T > Every * 4.0f) { P.Phase = 3; P.T = 0.0f; P.Wait = FMath::FRandRange(ReliefWaitMin, ReliefWaitMax); }
			break;
		}
		case 3:
			// el saliente se va al barracon; el relevo se lia un cigarro y luego sube (la ventana sigue abierta)
			if (S && S->IsOnErrand() && !P.bGone) { S->EndErrand(); }
			if (S && !P.bGone) { P.bGone = true; S->Errand(BarracksLoc, BarracksLoc + FVector(100.0f, 0.0f, 0.0f), 180.0f); }
			if (P.T < P.Wait + ReliefClimbSeconds) break;
			if (R && R->State != ETarsisGuardState::Down)
			{
				R->TakeTowerPost(S, P.Loc, P.Rot, P.Light.Get());
				P.Sentry = R;
				P.Relief = nullptr;
				++ReliefsDone;
				LastReliefWindow = MissionTime - P.EmptySince;
			}
			P.Leaving = S;
			P.Phase = 4;
			P.T = 0.0f;
			break;
		case 4:
		{
			// el saliente llega al barracon (o se cansa de andar) y desaparece dentro
			ATarsisGuard* L = P.Leaving.Get();
			if (L && L->State == ETarsisGuardState::Patrol && (L->AtErrand() || P.T > 180.0f)) { L->Destroy(); L = nullptr; }
			if (!L || L->State == ETarsisGuardState::Down || P.T > 240.0f)
			{
				P.Leaving = nullptr;
				P.bGone = false;
				P.Phase = 0;
				P.NextAt = MissionTime + ReliefEvery;
			}
			break;
		}
		case 10:
			// el puesto vacio: busca por la zona y avisa a Control; si en ReliefMissingSeconds no aparece, tension
			if (!R || R->State == ETarsisGuardState::Down) { P.Phase = 0; P.NextAt = MissionTime + ReliefEvery; break; }
			if (P.T > 2.5f && !P.bRadioed)
			{
				P.bRadioed = true;
				GuardSay(R, TEXT("relevo_control"), true);
				CentralSay(TEXT("relevo"), Tx(TEXT("radio_relevo"), TEXT("Recibido, relevo. Busca a {0} por la zona. Si no aparece, avisa."), { P.Name }), 3.5f);
				++ReliefRadioCalls;
				if (R->IsOnErrand()) R->EndErrand();
				R->HearNoise(P.Ladder + FVector(250.0f, 0.0f, 0.0f));   // a buscar por alrededor
			}
			// ha aparecido (lo han despertado o ha vuelto): todo en orden, sube
			if (S && S->State != ETarsisGuardState::Down && S->bTowerSentry && FVector::Dist(S->GetActorLocation(), P.Loc) < 300.0f)
			{
				P.Phase = 0;
				if (R) R->Destroy();
				P.Relief = nullptr;
				P.NextAt = MissionTime + ReliefEvery;
				break;
			}
			if (P.T > ReliefMissingSeconds && !P.bMissing)
			{
				P.bMissing = true;
				++ReliefMissingAlerts;
				TensionT = FMath::Max(TensionT, 150.0f);   // alerta de nivel 1: se echa de menos a uno
				CentralSay(TEXT("falta"), Tx(TEXT("radio_falta"), TEXT("A todas las unidades: falta {0}. Puede haber alguien dentro. Ojos abiertos."), { P.Name }), 0.5f);
				// el relevo se queda con el puesto
				if (R) R->TakeTowerPost(S, P.Loc, P.Rot, P.Light.Get());
				if (S && S->TowerLight == P.Light.Get()) S->TowerLight = nullptr;
				P.Sentry = R;
				P.Relief = nullptr;
				P.Phase = 0;
				P.bMissing = false;
				P.bRadioed = false;
				P.NextAt = MissionTime + ReliefEvery;
			}
			break;
		default:
			break;
		}
	}
}
