// Lost Horizon: De Profundis - tanda E2: al cruzarse, los guardias no se atraviesan.
// La cápsula del personaje del GASP (copia de SandboxCharacter_CMC) venía con la respuesta a Pawn en «Ignore»: dos
// guardias que se cruzaban se metían uno dentro del otro, y el jugador también. Ahora:
//  - la cápsula bloquea a las personas, salvo tumbado (dormido, derribado, arrastrado), en ragdoll o en una escena
//    (la captura): esos siguen ignorando, como antes;
//  - el RVO del CharacterMovement los aparta con suavidad en sitios anchos (el que corre o persigue pesa más);
//  - en un sitio estrecho, de frente, el de menos prisa se arrima a un lado, se para y da paso con el brazo.
#include "TarsisGuard.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "AIController.h"
#include "EngineUtils.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

bool ATarsisGuard::AvoidanceOn() const
{
	const UCharacterMovementComponent* M = GetCharacterMovement();
	return M && M->bUseRVOAvoidance;
}

void ATarsisGuard::CrossSetup()
{
	UCharacterMovementComponent* M = GetCharacterMovement();
	if (!M || !bCrossRule || bTowerSentry) return;
	M->AvoidanceConsiderationRadius = AvoidRadius;
	M->AvoidanceWeight = 0.5f;
	M->SetAvoidanceEnabled(true);
}

bool ATarsisGuard::ShouldYieldTo(const ATarsisGuard* Other) const
{
	// cede el que va de ronda (o de vuelta) frente al que busca o persigue; entre iguales, el de menor id
	auto Prisa = [](const ATarsisGuard* G)
	{
		switch (G->State)
		{
		case ETarsisGuardState::Alert: return 3;
		case ETarsisGuardState::Search: return 2;
		case ETarsisGuardState::Suspicious: return 1;
		default: return G->IsOnErrand() ? 1 : 0;
		}
	};
	const int32 A = Prisa(this), B = Prisa(Other);
	if (A != B) return A < B;
	return GetUniqueID() < Other->GetUniqueID();
}

void ATarsisGuard::CrossTick(float DeltaSeconds)
{
	// 1) la cápsula: bloquea de pie; ignora tumbado, en ragdoll o en una escena
	const bool bWant = bCrossRule && State != ETarsisGuardState::Down && !bRagdoll && !bSceneLock;
	if (bWant != bPawnBlock)
	{
		bPawnBlock = bWant;
		GetCapsuleComponent()->SetCollisionResponseToChannel(ECC_Pawn, bWant ? ECR_Block : ECR_Ignore);
	}
	// tanda F: con alguien de pie al lado (otro guardia o tú), el fusil con el cañón abajo: no se rozan al cruzarse
	{
		float Want = 0.0f;
		if (bCrossRule && State != ETarsisGuardState::Down && !bRifleAim && !bSceneLock)
		{
			const FVector Me = GetActorLocation();
			for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
			{
				if (*It == this || It->State == ETarsisGuardState::Down) continue;
				const FVector To = It->GetActorLocation() - Me;
				if (To.Size2D() < RifleTuckDist && FMath::Abs(To.Z) < 150.0f) { Want = 1.0f; break; }
			}
			const APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
			if (Want <= 0.0f && Pl && FVector::Dist2D(Pl->GetActorLocation(), Me) < RifleTuckDist && FMath::Abs(Pl->GetActorLocation().Z - Me.Z) < 150.0f) Want = 1.0f;
		}
		RifleTuckW = FMath::FInterpConstantTo(RifleTuckW, Want, DeltaSeconds, 3.0f);
	}
	if (!bCrossRule || bTowerSentry || State == ETarsisGuardState::Down) { YieldT = 0.0f; YieldBackT = 0.0f; return; }
	UCharacterMovementComponent* M = GetCharacterMovement();
	// el que corre o persigue pesa más en el RVO (los demás se apartan de él)
	if (M && M->bUseRVOAvoidance)
	{
		const float W = (State == ETarsisGuardState::Alert || State == ETarsisGuardState::Search) ? 0.9f : 0.5f;
		if (!FMath::IsNearlyEqual(M->AvoidanceWeight, W)) M->AvoidanceWeight = W;
	}
	if (YieldCoolT > 0.0f) YieldCoolT -= DeltaSeconds;
	// 2) cediendo el paso: primero se arrima, luego espera dando paso con el brazo
	if (YieldT > 0.0f)
	{
		YieldT -= DeltaSeconds;
		// tanda F: en un pasillo, primero atras hasta salir de entre las dos paredes
		if (YieldBackT > 0.0f)
		{
			YieldBackT -= DeltaSeconds;
			AddMovementInput(YieldBackDir, 1.0f);
			const FVector Right = FVector::CrossProduct(FVector::UpVector, YieldBackDir);
			FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisCruceAtras), false, this);
			if (ATarsisGuard* O = YieldOther.Get()) Q.AddIgnoredActor(O);
			FHitResult HR, HL;
			const FVector Eye = GetActorLocation() + FVector(0.0f, 0.0f, 20.0f);
			const bool bR = GetWorld()->LineTraceSingleByChannel(HR, Eye, Eye + Right * NarrowDist, ECC_Visibility, Q);
			const bool bL = GetWorld()->LineTraceSingleByChannel(HL, Eye, Eye - Right * NarrowDist, ECC_Visibility, Q);
			if (!(bR && bL) || YieldBackT <= 0.0f)
			{
				// fuera: un paso al lado con más sitio y a esperar
				YieldBackT = 0.0f;
				const FVector Eye2 = Eye + YieldBackDir * 60.0f;
				const bool bR2 = GetWorld()->LineTraceSingleByChannel(HR, Eye2, Eye2 + Right * 200.0f, ECC_Visibility, Q);
				const bool bL2 = GetWorld()->LineTraceSingleByChannel(HL, Eye2, Eye2 - Right * 200.0f, ECC_Visibility, Q);
				const float dR = bR2 ? HR.Distance : 200.0f, dL = bL2 ? HL.Distance : 200.0f;
				YieldSide = ((dR >= dL) ? Right : -Right) + YieldBackDir * 0.5f;
				YieldSide.Normalize();
				YieldSideT = 0.8f;
			}
			return;
		}
		// esperando a que pase el del pasillo: en cuanto ha salido y se aleja (o tarda demasiado), se sigue
		if (ATarsisGuard* O = YieldOther.Get())
		{
			const FVector To = O->GetActorLocation() - GetActorLocation();
			const bool bStill = O->GetVelocity().Size2D() < 20.0f;
			const bool bAway = FVector::DotProduct(O->GetVelocity(), To) > 0.0f || bStill;
			// o ya ha salido del pasillo y se ha parado (ha llegado a donde iba, al lado de la boca): el paso esta libre
			bool bOut = false;
			if (bStill)
			{
				const FVector R = FVector::CrossProduct(FVector::UpVector, YieldBackDir);
				FCollisionQueryParams QO(SCENE_QUERY_STAT(TarsisCruceSale), false, O);
				QO.AddIgnoredActor(this);
				FHitResult H1, H2;
				const FVector E = O->GetActorLocation() + FVector(0.0f, 0.0f, 20.0f);
				bOut = !(GetWorld()->LineTraceSingleByChannel(H1, E, E + R * NarrowDist, ECC_Visibility, QO) && GetWorld()->LineTraceSingleByChannel(H2, E, E - R * NarrowDist, ECC_Visibility, QO));
			}
			if (YieldSideT <= 0.0f && (O->State == ETarsisGuardState::Down || (To.Size2D() > YieldDist + 60.0f && bAway) || bOut)) YieldT = FMath::Min(YieldT, 0.3f);
		}
		if (YieldSideT > 0.0f)
		{
			YieldSideT -= DeltaSeconds;
			AddMovementInput(YieldSide, 0.7f);
		}
		else if (!bYieldGesture)
		{
			bYieldGesture = true;
			PlayGesture(TEXT("pase"), FMath::Clamp(YieldT, 0.4f, 2.5f), YieldToward);
		}
		if (YieldT <= 0.0f) { MoveDest = FVector(1e9f); YieldOther = nullptr; }   // que vuelva a pedir el camino
		return;
	}
	if (YieldCoolT > 0.0f || !M || M->Velocity.Size2D() < 40.0f || bPetting || bSceneLock || bAlly) return;
	const FVector Me = GetActorLocation();
	const FVector Dir = M->Velocity.GetSafeNormal2D();
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* O = *It;
		if (O == this || O->bTowerSentry || O->State == ETarsisGuardState::Down || O->bSceneLock) continue;
		const FVector To = O->GetActorLocation() - Me;
		if (To.Size2D() > YieldDist || FMath::Abs(To.Z) > 150.0f) continue;
		const FVector ToN = To.GetSafeNormal2D();
		if (FVector::DotProduct(Dir, ToN) < 0.6f) continue;                   // no lo tengo delante
		const FVector OV = O->GetVelocity();
		const bool bOMoving = OV.Size2D() > 30.0f;
		if (bOMoving && FVector::DotProduct(OV.GetSafeNormal2D(), -ToN) < 0.3f) continue;   // no viene hacia mí
		if (!ShouldYieldTo(O) && (bOMoving || O->IsYielding())) continue;      // cede el otro (o ya está cediendo)
		// ¿estrecho? pared cerca a un lado o al otro
		const FVector Right = FVector::CrossProduct(FVector::UpVector, Dir);
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisCruce), false, this);
		Q.AddIgnoredActor(O);
		FHitResult HR, HL;
		const FVector Eye = Me + FVector(0.0f, 0.0f, 20.0f);
		const bool bR = GetWorld()->LineTraceSingleByChannel(HR, Eye, Eye + Right * NarrowDist, ECC_Visibility, Q);
		const bool bL = GetWorld()->LineTraceSingleByChannel(HL, Eye, Eye - Right * NarrowDist, ECC_Visibility, Q);
		if (!bR && !bL) continue;   // en ancho se apartan solos (RVO)
		// a un lado: hacia donde haya más sitio
		const float dR = bR ? HR.Distance : NarrowDist, dL = bL ? HL.Distance : NarrowDist;
		YieldSide = (dR >= dL) ? Right : -Right;
		YieldT = 1.6f;
		YieldSideT = 0.55f;
		YieldCoolT = 4.0f;
		YieldToward = O->GetActorLocation();
		bYieldGesture = false;
		YieldOther = nullptr;
		YieldBackT = 0.0f;
		if (bR && bL && dR + dL < 2.0f * NarrowDist * 0.85f)
		{
			// tanda F: pared a los dos lados (pasillo): no cabe arrimarse; atrás hasta salir y esperar
			YieldBackDir = -Dir;
			YieldBackT = 5.0f;
			YieldSideT = 0.0f;
			YieldT = 14.0f;
			YieldOther = O;
			YieldCoolT = 16.0f;
			++BackOuts;
		}
		++Yields;
		if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
		break;
	}
}
