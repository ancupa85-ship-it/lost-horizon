// Lost Horizon: De Profundis - tanda 43: interrogar, asomarse y el ultimo sitio donde te vieron.
// Interrogar (T, por la espalda): el guardia levanta las manos, suelta un dato para el mapa mental y se queda quieto unos
// segundos. Hay que derribarlo (E) antes de que se rehaga, o va a por ti. Cada guardia habla una sola vez.
// Asomarse (Z a la izquierda, V a la derecha, mantenidas): la camara sale de lado sin mover el cuerpo. Los guardias miran
// al pecho, que sigue tras la esquina: ves sin que te vean.
// Ultimo avistamiento: cuando el que te persigue te pierde, queda marcado el sitio donde te vio por ultima vez y llama
// al companero mas cercano para registrarlo entre los dos. Mientras miran alli, tu ya no estas.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Camera/CameraComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

bool ATarsisDirector::CanInterrogate(const ATarsisGuard* G) const
{
	return bInterrogation && G && !G->bTowerSentry && !G->bAlly && G->StunT <= 0.0f && !Interrogated.Contains(G->GuardName);
}

void ATarsisDirector::Interrogate()
{
	if (!bInterrogation || bCine || bDone || bMenu || bCodec || bChoice || bKeypad || Dragged || bRiding || bHiding || bBoxOn || bCapturing) return;
	ATarsisGuard* G = TakedownTarget();
	if (!G || G->bTowerSentry) return;
	if (G->GuardName.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase) && !bRamosTalked) { Interact(); return; }   // Ramos tiene su propia conversacion
	if (!CanInterrogate(G))
	{
		if (Interrogated.Contains(G->GuardName)) ShowMessage(Tx(TEXT("int_ya"), TEXT("YA HA HABLADO\n{0} no sabe mas. Derribalo o dejalo pasar."), { G->GuardName.ToUpper() }), 2.5f);
		return;
	}
	Interrogated.Add(G->GuardName);
	++Interrogations;
	G->Stun(InterrogateSeconds);
	// lo que sabe: primero lo que le une a otro (un dato de la ficha de un companero que lo nombra a el); si no, uno de la suya.
	// Nunca datos que no le tocan: el mapa mental no se llena interrogando a cualquiera.
	FName Got;
	for (const FTarsisFact& F : Facts) { if (F.Link.Equals(G->GuardName, ESearchCase::IgnoreCase) && !FactKnown(F.Id)) { Got = F.Id; break; } }
	if (Got.IsNone()) { for (const FTarsisFact& F : Facts) { if (F.Card.Equals(G->GuardName, ESearchCase::IgnoreCase) && !FactKnown(F.Id)) { Got = F.Id; break; } } }
	PlaySfx(TEXT("empujon"), G->GetActorLocation() + FVector(0.0f, 0.0f, 100.0f), 0.3f);
	G->PlayGesture(FName(TEXT("manos")), InterrogateSeconds);   // manos arriba mientras habla
	// antes del dato: el cartel de APUNTADO es el que debe quedar a la vista
	Teach(TEXT("ensena_interrogar"), TEXT("INTERROGADO\n{0} habla y se queda quieto unos segundos. Derribalo (E) antes de que se rehaga, o ira a por ti."), { G->GuardName.ToUpper() }, 4.5f);
	if (Got.IsNone())
	{
		SaySubtitle(G->GuardName.ToUpper(), Tx(TEXT("int_nada"), TEXT("No se nada mas. Se lo juro.")), 3.0f);
	}
	else
	{
		SaySubtitle(G->GuardName.ToUpper(), Tx(TEXT("int_habla"), TEXT("No dispare. Le digo lo que se.")), 3.0f);
		LearnFact(Got);
		++InterrogationFacts;
	}
}

// ---------------------------------------------------------------- asomarse

void ATarsisDirector::LeanTick(float DeltaSeconds)
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	UCameraComponent* Cam = C ? C->FindComponentByClass<UCameraComponent>() : nullptr;
	if (!Cam) return;
	float Want = 0.0f;
	if (bLeanRule && !bCine && !bDone && !bMenu && !bCodec && !bRiding && !bHiding && !bBoxOn && !bClimbing && !bBinoculars && !Dragged)
	{
		Want = (bLeanRight ? 1.0f : 0.0f) - (bLeanLeft ? 1.0f : 0.0f);
	}
	const FVector Right = C->GetActorRightVector();
	if (Want != 0.0f)
	{
		// que la cabeza no atraviese la pared: lo que haya a ese lado acorta el paso
		const FVector Base = Cam->GetComponentLocation() - Right * LeanNow;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisAsomarse), false, this);
		Q.AddIgnoredActor(C);
		FHitResult Hit;
		float Room = LeanDist;
		if (GetWorld()->SweepSingleByChannel(Hit, Base, Base + Right * Want * (LeanDist + 18.0f), FQuat::Identity, ECC_Visibility, FCollisionShape::MakeSphere(12.0f), Q))
		{
			// pegado a una pared el barrido sale ya tocandola (distancia 0) y no dejaba asomarse a ningun lado: solo cuenta
			// si es hacia la pared
			if (!Hit.bStartPenetrating) Room = FMath::Max(0.0f, Hit.Distance - 6.0f);
			else if (FVector::DotProduct(Hit.Normal, Right * Want) < 0.0f) Room = 0.0f;
		}
		Want *= Room;
	}
	const float Next = FMath::FInterpTo(LeanNow, Want, DeltaSeconds, 9.0f);
	if (!FMath::IsNearlyEqual(Next, LeanNow, 0.01f))
	{
		Cam->AddWorldOffset(Right * (Next - LeanNow));
		LeanNow = Next;
	}
	if (FMath::Abs(LeanNow) > LeanDist * 0.5f && !bLeanTaught)
	{
		bLeanTaught = true;
		++Leans;
		Teach(TEXT("ensena_asomarse"), TEXT("ASOMADO\nSolo sacas la cabeza: desde la esquina ves sin que te vean. Suelta la tecla para volver."), {}, 4.0f);
	}
	if (FMath::Abs(LeanNow) < 1.0f) bLeanTaught = false;
}

// ---------------------------------------------------------------- ultimo avistamiento

void ATarsisDirector::LostPlayer(ATarsisGuard* G, const FVector& Where)
{
	if (!bLastSeenRule || !G || bCine || bDone || bCapturing) return;
	LastKnown = Where;
	LastKnownT = LastKnownSeconds;
	++LastKnownMarks;
	// el companero mas cercano que este libre viene a registrar el sitio con el (uno cada cierto tiempo, no toda la base)
	if (PartnerCoolT > 0.0f) return;
	ATarsisGuard* Best = nullptr;
	float BestD = FMath::Square(PartnerDist);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (*It == G || It->bTowerSentry || It->bAlly || It->IsOnErrand()) continue;
		if (It->State != ETarsisGuardState::Patrol && It->State != ETarsisGuardState::Return) continue;
		const float D = FVector::DistSquared2D(It->GetActorLocation(), Where);
		if (D < BestD) { BestD = D; Best = *It; }
	}
	if (!Best) return;
	PartnerCoolT = 20.0f;
	++PartnerSearches;
	const FVector Side = (Best->GetActorLocation() - Where).GetSafeNormal2D();
	Best->HearNoise(Where + Side * 250.0f);
	SaySubtitle(G->GuardName.ToUpper(), Tx(TEXT("busca_pareja"), TEXT("Lo he perdido por aqui. {0}, cubre ese lado."), { Best->GuardName }), 3.5f);
	Teach(TEXT("ensena_ultimo"), TEXT("TE BUSCAN DONDE TE VIERON\nLa silueta es el ultimo sitio donde te vieron: van a registrarlo entre dos. Alejate de ella."), {}, 5.0f);
}

void ATarsisDirector::TacticsTick(float DeltaSeconds)
{
	LeanTick(DeltaSeconds);
	if (PartnerCoolT > 0.0f) PartnerCoolT -= DeltaSeconds;
	if (LastKnownT > 0.0f)
	{
		LastKnownT -= DeltaSeconds;
		// si te vuelven a ver, la marca sobra
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (!It->bTowerSentry && It->State == ETarsisGuardState::Alert && !It->bRadioCall && It->StateT > 0.5f && It->UnseenT < 0.5f) { LastKnownT = 0.0f; break; }
		}
	}
}
