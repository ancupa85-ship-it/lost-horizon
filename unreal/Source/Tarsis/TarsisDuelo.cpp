// Lost Horizon: De Profundis - tanda N, segunda parte (2026-11-26): el cuerpo a cuerpo de ida y vuelta y los guardias
// que se coordinan.
//
// El duelo (antes una sola E en una ventana: aciertas y ganas, fallas y pierdes):
// - GOLPEAR (H) a un guardia en alerta o mosqueado que te encara, a menos de 1,8 m, empieza el duelo con el. Mientras
//   dura, ese guardia no te detiene al tocarte ni dispara: pelea. Los demas siguen con lo suyo (apuntan, rodean).
// - El guardia: CUBIERTO (tus golpes los para con el fusil) -> AMAGO (levanta la culata, despacio, y suena el roce de la
//   correa: se lee tambien de noche) -> CULATAZO (o AGARRE, a veces) -> otra vez CUBIERTO. Tus golpes durante el amago
//   entran; con los suficientes (por dificultad) se tambalea. Parar el culatazo en la ventana (BLOQUEAR, Alt, pulsado
//   justo antes del golpe) o esquivarlo (BLOQUEAR moviendote) lo deja TAMBALEANDOSE: la E lo remata (la pareja de
//   derribo del GASP de la N1). Parar antes de tiempo con el brazo aguanta el golpe pero gasta aguante; sin aguante
//   entra. Los culatazos que aguantas dependen de la dificultad; al ultimo caes (la detencion a golpes).
// - El agarre: forcejeo; la E a tiempo te suelta (y el guardia se tambalea); si no, te detienen (la de siempre, sin
//   golpes: captura, no muerte).
// - Aguante: golpear, parar y esquivar gastan; se recupera sin pelear. La barra se ve en el duelo o si no esta llena.
// - Ruido: cada golpe y culatazo se oye (MeleeHeard): acuden los que esten cerca y libres. El sigilo sigue siendo lo
//   mejor: uno se gana con oficio, dos muy dificil, tres perdido.
// Coordinacion en la alerta (cada 0,5 s): el guardia armado mas cercano que te ve FIJA (se cubre y te apunta, como
// siempre); hasta dos mas FLANQUEAN, a 60-110 grados a cada lado, a FlankDistance de ti (o de donde te perdieron), sin
// cruzarse delante del que fija. Un punto de flanqueo a oscuras (luz < FlankDarkLight) no se usa: se acerca al borde
// iluminado (regla de la tanda 28, nadie entra solo a oscuras).
// Ideas tomadas (sin codigo): las «fichas de ataque» de los devlogs (aqui, un solo guardia pelea de cerca a la vez).
// Textos solo en ASCII.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "AIController.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "HAL/PlatformTime.h"
#include "Kismet/GameplayStatics.h"
#include "NavigationSystem.h"

namespace
{
	enum EDuel : int32 { DuelNone = 0, DuelGuardUp = 1, DuelFeint = 2, DuelStrikeN = 3, DuelGrab = 4, DuelStagger = 5 };
	const TCHAR* MeleeAnimPath = TEXT("/Game/Tarsis/Armas/Anims/MM_Rifle_Melee.MM_Rifle_Melee");
}

bool ATarsisDirector::MeleeEngageTarget(ATarsisGuard*& Out) const
{
	Out = nullptr;
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || !bMeleeRule || bCapturing || bCine || bDone || bHiding || bRiding) return false;
	float Best = 180.0f;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		if (G->bTowerSentry || G->bAlly || G->State == ETarsisGuardState::Down || G->IsStunned()) continue;
		if (G->State != ETarsisGuardState::Alert && G->State != ETarsisGuardState::Suspicious) continue;
		const FVector D = P->GetActorLocation() - G->GetActorLocation();
		const float Dist = D.Size2D();
		if (Dist > Best || FMath::Abs(D.Z) > 120.0f) continue;
		if (FVector::DotProduct(G->GetActorForwardVector(), D.GetSafeNormal2D()) < 0.2f) continue;   // te encara
		Best = Dist;
		Out = G;
	}
	return Out != nullptr;
}

void ATarsisDirector::MeleeStrike()
{
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || bMenu || bCodec || bCapturing || bCine || bDone) return;
	if (StaminaNow < StaminaHitCost * 0.5f) { ShowMessage(Tx(TEXT("duelo_sin_aguante"), TEXT("SIN ALIENTO\nNo te quedan fuerzas para golpear: para o aparta.")), 1.5f); return; }
	ATarsisGuard* G = DuelGuard.Get();
	if (!G)
	{
		if (!MeleeEngageTarget(G)) return;
		// empieza el duelo: el guardia se planta y se cubre
		DuelGuard = G;
		DuelPhaseN = DuelGuardUp;
		DuelT = 0.0f;
		DuelPhaseLen = FMath::FRandRange(MeleeGuardUpSeconds.X, MeleeGuardUpSeconds.Y);
		DuelHits = DuelStrikes = 0;
		bGrabFreed = false;
		++Duels;
		if (AAIController* AI = Cast<AAIController>(G->GetController())) AI->StopMovement();
		Teach(TEXT("ensena_duelo"), TEXT("CUERPO A CUERPO\n{0} golpea cuando amaga, {1} para el culatazo justo antes. A tiempo, se tambalea: E para rematar."), { KeyLabel(14), KeyLabel(15) }, 6.0f);
	}
	StaminaNow = FMath::Max(0.0f, StaminaNow - StaminaHitCost);
	StrikeT = StrikeLen;   // el golpe que se ve (primera persona)
	++Strikes;
	KickT = FMath::Max(KickT, 0.1f);
	const FVector At = G->GetActorLocation() + FVector(0.0f, 0.0f, 110.0f);
	if (DuelPhaseN == DuelGuardUp || DuelPhaseN == DuelStrikeN)
	{
		// cubierto (o ya lanzado): lo para con el fusil
		++MeleeBlocked;
		PlaySfx(TEXT("golpe"), At, 0.45f);
		DuelNoise(At);
	}
	else if (DuelPhaseN == DuelFeint)
	{
		// en el amago esta abierto: el golpe entra y le corta el ataque
		++MeleeLanded;
		++DuelHits;
		G->SceneEnd();
		G->bSceneLock = false;
		G->HitReact(G->GetActorLocation() - P->GetActorLocation(), false);
		if (USoundBase* S = Sfx(FString::Printf(TEXT("golpe_seco_%d"), FMath::RandRange(1, 2)))) UGameplayStatics::PlaySoundAtLocation(this, S, At, 0.8f, 1.1f, 0.0f, Atten);
		DuelNoise(At);
		if (DuelHits >= MeleeHitsToStagger[DiffIdx()])
		{
			DuelPhaseN = DuelStagger; DuelT = 0.0f; DuelPhaseLen = MeleeStaggerSeconds;
			G->Stun(MeleeStaggerSeconds);
			++MeleeStaggers;
		}
		else { DuelPhaseN = DuelGuardUp; DuelT = 0.0f; DuelPhaseLen = FMath::FRandRange(MeleeGuardUpSeconds.X, MeleeGuardUpSeconds.Y); }
	}
}

void ATarsisDirector::BlockOn()
{
	bBlockHeld = true;
	BlockPressAt = FPlatformTime::Seconds();
}

void ATarsisDirector::BlockOff()
{
	bBlockHeld = false;
}

void ATarsisDirector::DuelNoise(const FVector& Where)
{
	++MeleeNoises;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (*It == DuelGuard.Get() || It->bTowerSentry || It->bAlly || It->HoldT > 0.0f || It->State == ETarsisGuardState::Down || It->State == ETarsisGuardState::Alert) continue;
		if (FVector::Dist(It->GetActorLocation(), Where) < MeleeHeard) It->HearNoise(Where);
	}
}

void ATarsisDirector::DuelEnd()
{
	if (ATarsisGuard* G = DuelGuard.Get())
	{
		if (G->bSceneLock && !G->bSceneFallPending && !TSGuard.IsValid() && !DSGuard.IsValid()) { G->SceneEnd(); G->bSceneLock = false; }
	}
	DuelGuard = nullptr;
	DuelPhaseN = DuelNone;
}

void ATarsisDirector::DuelTick(float DeltaSeconds)
{
	// el aguante se recupera sin pelear
	if (!DuelGuard.IsValid()) StaminaNow = FMath::Min(StaminaMax, StaminaNow + StaminaRegen * DeltaSeconds);
	ATarsisGuard* G = DuelGuard.Get();
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!G) { if (DuelPhaseN != DuelNone) DuelEnd(); return; }
	if (!C || bCapturing || G->State == ETarsisGuardState::Down || TSGuard.Get() == G || FVector::Dist2D(G->GetActorLocation(), C->GetActorLocation()) > 350.0f || G->bDead)
	{
		DuelEnd();
		return;
	}
	DuelT += DeltaSeconds;
	// el guardia del duelo pelea: no anda, no detiene ni dispara (Hold); te encara
	G->Hold(0.3f);
	if (DuelPhaseN != DuelStagger)
	{
		const FRotator Want(0.0f, (C->GetActorLocation() - G->GetActorLocation()).Rotation().Yaw, 0.0f);
		G->SetActorRotation(FMath::RInterpTo(G->GetActorRotation(), Want, DeltaSeconds, 8.0f));
	}
	const FVector At = G->GetActorLocation() + FVector(0.0f, 0.0f, 110.0f);
	switch (DuelPhaseN)
	{
	case DuelGuardUp:
		if (DuelT >= DuelPhaseLen)
		{
			const bool bGrab = TestNextMelee == 2 || (TestNextMelee == 0 && FMath::FRand() < MeleeGrabChance);
			TestNextMelee = 0;
			if (bGrab)
			{
				// el agarre: te coge del brazo; la E a tiempo te suelta
				DuelPhaseN = DuelGrab; DuelT = 0.0f; DuelPhaseLen = MeleeGrabWindow[DiffIdx()];
				bGrabFreed = false;
				++MeleeGrabs;
				PlaySfx(TEXT("empujon"), At, 0.7f);
				GuardSay(G, TEXT("alto"));
				ShowMessage(Tx(TEXT("duelo_agarre"), TEXT("TE AGARRA\nE para soltarte, ya.")), MeleeGrabWindow[DiffIdx()]);
			}
			else
			{
				// el amago: levanta la culata despacio; suena el roce de la correa (se lee tambien a oscuras)
				DuelPhaseN = DuelFeint; DuelT = 0.0f; DuelPhaseLen = MeleeFeintSeconds;
				if (UAnimSequenceBase* A = LoadObject<UAnimSequenceBase>(nullptr, MeleeAnimPath))
				{
					G->ScenePlay(A);
					G->GetMesh()->SetPlayRate(0.45f);
				}
				if (USoundBase* S = Sfx(TEXT("llaves"))) UGameplayStatics::PlaySoundAtLocation(this, S, At, 0.9f, 0.62f, 0.0f, Atten);
			}
		}
		break;
	case DuelFeint:
		if (DuelT >= DuelPhaseLen)
		{
			DuelPhaseN = DuelStrikeN; DuelT = 0.0f; DuelPhaseLen = MeleeStrikeSeconds;
			G->GetMesh()->SetPlayRate(1.5f);
		}
		break;
	case DuelStrikeN:
		if (DuelT >= DuelPhaseLen)
		{
			// el golpe llega: contra a tiempo (pulsado dentro de la ventana), parada con el brazo o te da
			const double Now = FPlatformTime::Seconds();
			const float Win = MeleeCounterWindow[DiffIdx()];
			const bool bInWindow = BlockPressAt > 0.0 && Now - BlockPressAt <= Win + DeltaSeconds;
			const bool bMoving = C->GetVelocity().Size2D() > 150.0f;
			G->SceneEnd();
			G->bSceneLock = false;
			if (bInWindow && StaminaNow >= (bMoving ? StaminaDodgeCost : StaminaBlockCost) * 0.5f)
			{
				StaminaNow = FMath::Max(0.0f, StaminaNow - (bMoving ? StaminaDodgeCost : StaminaBlockCost));
				++MeleeParries;
				++MeleeStaggers;
				PlaySfx(TEXT("golpe"), At, 0.7f);
				// reaccion ligera: se tambalea sin salirse del alcance del remate
				G->HitReact(G->GetActorLocation() - C->GetActorLocation(), false);
				G->Stun(MeleeStaggerSeconds);
				DuelPhaseN = DuelStagger; DuelT = 0.0f; DuelPhaseLen = MeleeStaggerSeconds;
				DuelNoise(At);
				SlowMo();
			}
			else if (bBlockHeld && StaminaNow >= StaminaBlockCost)
			{
				StaminaNow -= StaminaBlockCost;
				++MeleeBlocked;
				PlaySfx(TEXT("golpe"), At, 0.6f);
				KickT = FMath::Max(KickT, 0.12f);
				DuelNoise(At);
				DuelPhaseN = DuelGuardUp; DuelT = 0.0f; DuelPhaseLen = FMath::FRandRange(MeleeGuardUpSeconds.X, MeleeGuardUpSeconds.Y);
			}
			else
			{
				++MeleeTaken;
				++DuelStrikes;
				if (USoundBase* S = Sfx(FString::Printf(TEXT("golpe_seco_%d"), FMath::RandRange(1, 2)))) UGameplayStatics::PlaySound2D(this, S, 1.0f);
				KickT = FMath::Max(KickT, 0.3f);
				SuppressT = FMath::Max(SuppressT, 1.2f);
				C->LaunchCharacter((C->GetActorLocation() - G->GetActorLocation()).GetSafeNormal2D() * 220.0f, true, false);
				DuelNoise(At);
				if (DuelStrikes >= MeleeStrikesToDown[DiffIdx()])
				{
					// al ultimo culatazo caes: la detencion a golpes
					DuelEnd();
					bCaptureWounded = true;
					BeginCapture(G);
					return;
				}
				DuelPhaseN = DuelGuardUp; DuelT = 0.0f; DuelPhaseLen = FMath::FRandRange(MeleeGuardUpSeconds.X, MeleeGuardUpSeconds.Y);
			}
			BlockPressAt = -1.0;
		}
		break;
	case DuelGrab:
		if (bGrabFreed)
		{
			++MeleeGrabEscapes;
			PlaySfx(TEXT("empujon"), At, 0.8f);
			G->HitReact(G->GetActorLocation() - C->GetActorLocation(), true);
			G->Stun(MeleeStaggerSeconds * 0.8f);
			DuelPhaseN = DuelStagger; DuelT = 0.0f; DuelPhaseLen = MeleeStaggerSeconds * 0.8f;
		}
		else if (DuelT >= DuelPhaseLen)
		{
			// no te soltaste: te detienen (en calma, sin golpes)
			DuelEnd();
			bCaptureWounded = false;
			BeginCapture(G);
			return;
		}
		break;
	case DuelStagger:
		if (DuelT >= DuelPhaseLen) { DuelPhaseN = DuelGuardUp; DuelT = 0.0f; DuelPhaseLen = FMath::FRandRange(MeleeGuardUpSeconds.X, MeleeGuardUpSeconds.Y); }
		break;
	default:
		break;
	}
}

// ---------------------------------------------------------------- la coordinacion: fijar y flanquear

int32 ATarsisDirector::CombatRole(const ATarsisGuard* G) const
{
	for (const auto& KV : Roles) if (KV.Key.Get() == G) return KV.Value;
	return 0;
}

FVector ATarsisDirector::FlankPointOf(const ATarsisGuard* G) const
{
	for (const auto& KV : FlankPoints) if (KV.Key.Get() == G) return KV.Value;
	return FVector::ZeroVector;
}

int32 ATarsisDirector::AwakeRagdolls() const
{
	int32 N = 0;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It) if (It->bRagdoll && !It->bRagdollSlept) ++N;
	return N;
}

void ATarsisDirector::CombatRolesTick(float DeltaSeconds)
{
	RolesT -= DeltaSeconds;
	if (RolesT > 0.0f) return;
	RolesT = 0.5f;
	Roles.Reset();
	FlankPoints.Reset();
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!bFlankRule || !bArmedRule || !P || bCapturing) return;
	TArray<ATarsisGuard*> Alert;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		if (G->State != ETarsisGuardState::Alert || G->bTowerSentry || G->bAlly || G->bDisarmed || !G->HasRifle() || G->HoldT > 0.0f || G == DuelGuard.Get() || G == ArrestGuard) continue;
		Alert.Add(G);
	}
	if (Alert.Num() < 2) return;
	// donde esta el objetivo: tu sitio si alguno te ve; si no, donde te perdieron
	const ATarsisGuard* Seer = nullptr;
	for (ATarsisGuard* G : Alert) if (G->UnseenT < 0.5f) { Seer = G; break; }
	const FVector Target = Seer ? P->GetActorLocation() : (Alert[0]->LastSeen.IsZero() ? P->GetActorLocation() : Alert[0]->LastSeen);
	Alert.Sort([&Target](const ATarsisGuard& A, const ATarsisGuard& B) { return FVector::DistSquared(A.GetActorLocation(), Target) < FVector::DistSquared(B.GetActorLocation(), Target); });
	ATarsisGuard* Fixer = Alert[0];
	Roles.Add(Fixer, 1);
	const FVector FixDir = (Fixer->GetActorLocation() - Target).GetSafeNormal2D();
	UNavigationSystemV1* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
	int32 Made = 0;
	float FirstSide = 1.0f;
	for (int32 i = 1; i < Alert.Num() && Made < 2; ++i)
	{
		ATarsisGuard* G = Alert[i];
		// a cada lado del que fija (el primero por el lado en que ya esta, el segundo por el otro): ninguno cruza por
		// delante de su tiro
		const float Side = (Made == 0) ? (FVector::CrossProduct(FixDir, G->GetActorLocation() - Target).Z >= 0.0f ? 1.0f : -1.0f) : -FirstSide;
		if (Made == 0) FirstSide = Side;
		const float Ang = FMath::DegreesToRadians(FMath::FRandRange(60.0f, 110.0f)) * Side;
		const FVector Dir = FixDir.RotateAngleAxis(FMath::RadiansToDegrees(Ang), FVector::UpVector);
		FVector Pt = Target + Dir * FlankDistance;
		FNavLocation NL;
		if (Nav && Nav->ProjectPointToNavigation(Pt, NL, FVector(250.0f, 250.0f, 300.0f))) Pt = NL.Location;
		// regla de la tanda 28: nadie entra solo a oscuras; el punto se acerca al borde iluminado (hacia el guardia)
		if (ATarsisGuard::LightAt(this, Pt + FVector(0.0f, 0.0f, 60.0f)) < FlankDarkLight)
		{
			++FlankDarkAvoided;
			bool bLit = false;
			for (int32 k = 1; k <= 6 && !bLit; ++k)
			{
				const FVector Q = FMath::Lerp(Pt, G->GetActorLocation(), k / 6.0f);
				if (ATarsisGuard::LightAt(this, Q + FVector(0.0f, 0.0f, 60.0f)) >= FlankDarkLight) { Pt = Q; bLit = true; }
			}
			if (!bLit) continue;   // todo oscuro: no flanquea (se queda con los demas)
		}
		Roles.Add(G, 2);
		FlankPoints.Add(G, Pt);
		++FlankOrders;
		++Made;
	}
}
