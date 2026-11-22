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
	if (!bCrossRule || bTowerSentry || State == ETarsisGuardState::Down) { YieldT = 0.0f; return; }
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
		if (YieldSideT > 0.0f)
		{
			YieldSideT -= DeltaSeconds;
			AddMovementInput(YieldSide, 0.7f);
		}
		else if (!bYieldGesture)
		{
			bYieldGesture = true;
			PlayGesture(TEXT("pase"), FMath::Max(0.4f, YieldT), YieldToward);
		}
		if (YieldT <= 0.0f) MoveDest = FVector(1e9f);   // que vuelva a pedir el camino
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
		++Yields;
		if (AAIController* AI = Cast<AAIController>(GetController())) AI->StopMovement();
		break;
	}
}
