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
#include "Animation/AnimInstance.h"
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
}

bool ATarsisDirector::MeleeEngageTarget(ATarsisGuard*& Out) const
{
	Out = nullptr;
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || !bMeleeRule || bCapturing || bCine || bDone || bHiding || bRiding) return false;
	float Best = bThirdShown ? MeleeEngageRange : MeleeEngageRangeFP;   // tanda P: en primera, mas permisivo
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		if (G->bTowerSentry || G->bAlly || G->State == ETarsisGuardState::Down || G->IsStunned()) continue;
		if (G->State != ETarsisGuardState::Alert && G->State != ETarsisGuardState::Suspicious) continue;
		const FVector D = P->GetActorLocation() - G->GetActorLocation();
		const float Dist = D.Size2D();
		if (Dist > Best || FMath::Abs(D.Z) > 120.0f) continue;
		if (FVector::DotProduct(G->GetActorForwardVector(), D.GetSafeNormal2D()) < (bThirdShown ? 0.2f : 0.0f)) continue;   // te encara
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
	HeroStrikeAnim();   // tanda Q: sin sacudida por tu propio golpe   // tanda O: en tercera, el puñetazo se ve
	const FVector At = G->GetActorLocation() + FVector(0.0f, 0.0f, 110.0f);
	// tanda O: lo que se ve y se oye del golpe va en el contacto del puño (HeroContactLead), no al pulsar (ContactTick)
	if (DuelPhaseN == DuelGuardUp || DuelPhaseN == DuelStrikeN)
	{
		// cubierto (o ya lanzado): lo para con el fusil
		++MeleeBlocked;
		DuelContactT = HeroContactLead; DuelContactKind = 2; bDuelSounded = false;
		DuelNoise(At);
	}
	else if (DuelPhaseN == DuelFeint)
	{
		// en el amago esta abierto: el golpe entra y le corta el ataque
		++MeleeLanded;
		++DuelHits;
		DuelContactT = HeroContactLead; DuelContactKind = 1; bDuelSounded = false;
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
	if (GSGuard.IsValid()) GrabSceneEnd(false);   // tanda O
	if (ATarsisGuard* G = DuelGuard.Get())
	{
		if (G->bSceneLock && !G->bSceneFallPending && !TSGuard.IsValid() && !DSGuard.IsValid()) { G->SceneEnd(); G->bSceneLock = false; }
	}
	bDuelRecovering = false;
	bRemateQueued = false;
	bGrabReactPending = false;
	bDuelStepping = false;
	if (DuelGuard.IsValid()) FlankFrozenUntil = FPlatformTime::Seconds() + FlankFreezeAfterDuel;   // tanda S
	if (ATarsisGuard* G = DuelGuard.Get()) if (G->GetCharacterMovement()) G->GetCharacterMovement()->bOrientRotationToMovement = true;   // tanda R
	DuelGuard = nullptr;
	DuelPhaseN = DuelNone;
}

void ATarsisDirector::DuelTick(float DeltaSeconds)
{
	ContactTick(DeltaSeconds);   // tanda O
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
	// tanda R: al colocarse andando no se gira hacia donde anda (daba media vuelta a 420 grados/s al retroceder)
	if (G->GetCharacterMovement()) G->GetCharacterMovement()->bOrientRotationToMovement = false;
	if (DuelPhaseN != DuelStagger)
	{
		const FRotator Want(0.0f, (C->GetActorLocation() - G->GetActorLocation()).Rotation().Yaw, 0.0f);
		// tanda R: con tope (antes, exponencial: al abrir el duelo giraba a 400-500 grados/s)
		G->SetActorRotation(FMath::RInterpConstantTo(G->GetActorRotation(), Want, DeltaSeconds, DuelTurnMaxSpeed));
	}
	const FVector At = G->GetActorLocation() + FVector(0.0f, 0.0f, 110.0f);
	// tanda Q: la distancia del duelo sin saltos: el guardia se coloca a DuelDistance andando (como mucho
	// DuelSpacingSpeed) y en el culatazo se acerca a MeleeContactDistance a lo largo de todo el golpe
	// tanda R: andando (entrada de movimiento: el GASP le pone pasos), no moviendo el actor; el acercamiento a
	// MeleeContactDistance va al final de la guardia y en el amago y el culatazo ya no se mueve (patinaba 25 cm)
	// tanda S: mientras Cuttlas da su paso, el guardia no se recoloca (retrocedia a la vez, sin pasos)
	if (DuelPhaseN == DuelGuardUp && !GSGuard.IsValid() && !bDuelRecovering && HeroStepPending.IsNearlyZero())
	{
		const float Want = (DuelT >= DuelPhaseLen - DuelApproachSeconds) ? MeleeContactDistance : DuelDistance;
		const FVector Away = (G->GetActorLocation() - C->GetActorLocation()).GetSafeNormal2D();
		const float Now2 = FVector::Dist2D(G->GetActorLocation(), C->GetActorLocation());
		const float Speed = FMath::Clamp((Want - Now2) * 6.0f, -DuelSpacingSpeed, DuelSpacingSpeed);
		const float Max = G->GetCharacterMovement() ? FMath::Max(G->GetCharacterMovement()->MaxWalkSpeed, 1.0f) : 1.0f;
		// tanda S: solo si le faltan DuelStepDeadband o mas, y entonces hasta llegar (un paso entero, no pasitos)
		if (FMath::Abs(Want - Now2) >= DuelStepDeadband) bDuelStepping = true;
		else if (FMath::Abs(Want - Now2) <= 3.0f) bDuelStepping = false;
		if (bDuelStepping && !Away.IsNearlyZero()) G->AddMovementInput(Away * FMath::Sign(Speed), FMath::Min(FMath::Abs(Speed) / Max, 1.0f), true);
	}
	// tanda Q: la pose final del culatazo (el seguimiento entero) antes de volver a la guardia
	if (bDuelRecovering && DuelT >= MeleeRecoverSeconds)
	{
		bDuelRecovering = false;
		G->SceneEnd();
		G->bSceneLock = false;
	}
	// tanda Q: el remate pedido al principio del tambaleo sale cuando ya ha pasado la contra
	if (bRemateQueued && (DuelPhaseN != DuelStagger || DuelT >= StaggerRemateDelay))
	{
		bRemateQueued = false;
		if (DuelPhaseN == DuelStagger) { Takedown(); if (!DuelGuard.IsValid()) return; }
	}
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
				GrabSceneBegin(G);   // tanda O: las manos encima, de verdad
			}
			else
			{
				// el amago: levanta la culata despacio; suena el roce de la correa (se lee tambien a oscuras)
				// tanda O: sube justo hasta arriba del todo (MeleeWindupAt) en lo que dura el amago y ahi se queda
				DuelPhaseN = DuelFeint; DuelT = 0.0f; DuelPhaseLen = MeleeFeintSeconds;
				if (UAnimSequenceBase* A = LoadObject<UAnimSequenceBase>(nullptr, *MeleeStrikeAnimPath))
				{
					G->ScenePlay(A);
					G->GetMesh()->SetPlayRate(MeleeWindupAt / FMath::Max(MeleeFeintSeconds, 0.05f));
				}
				if (USoundBase* S = Sfx(TEXT("llaves"))) UGameplayStatics::PlaySoundAtLocation(this, S, At, 0.9f, 0.62f, 0.0f, Atten);
			}
		}
		break;
	case DuelFeint:
		if (DuelT >= DuelPhaseLen)
		{
			DuelPhaseN = DuelStrikeN; DuelT = 0.0f; DuelPhaseLen = MeleeStrikeSeconds;
			// tanda O: la culata se queda arriba (la silueta del amago, quieta) y baja de golpe justo para el contacto
			G->GetMesh()->SetPlayRate(0.0f);
			G->GetMesh()->SetPosition(MeleeWindupAt, false);
			bDuelSwing = false;
			// tanda P: el aviso con voz (gesto, sonido y voz a la vez: Sekiro, The Last of Us Part II)
			{
				const FString Who = G->bTowerSentry ? TEXT("centinela") : G->GuardName.ToLower();
				USoundBase* V = Sfx(FString::Printf(TEXT("voz_%s_toma"), *Who));
				if (!V) V = Sfx(TEXT("voz_moya_toma"));
				if (V) UGameplayStatics::PlaySoundAtLocation(this, V, G->GetActorLocation() + FVector(0.0f, 0.0f, 150.0f), 1.2f, 1.0f, 0.0f, Atten);
				++MeleeWarnings;
			}
		}
		break;
	case DuelStrikeN:
		if (!bDuelSwing && DuelT >= DuelPhaseLen - (MeleeContactAt - MeleeWindupAt))
		{
			bDuelSwing = true;
			G->GetMesh()->SetPlayRate(1.0f);
			DuelSwingAt = DuelT;   // tanda Q: el acercamiento va repartido en todo el culatazo (arriba, sin saltos)
		}
		if (DuelT >= DuelPhaseLen)
		{
			// el golpe llega: contra a tiempo (pulsado dentro de la ventana), parada con el brazo o te da
			const double Now = FPlatformTime::Seconds();
			const float Win = MeleeCounterWindow[DiffIdx()];
			const bool bInWindow = BlockPressAt > 0.0 && Now - BlockPressAt <= Win + DeltaSeconds;
			const bool bMoving = C->GetVelocity().Size2D() > 150.0f;
			// tanda Q: la animacion del culatazo sigue (pose final, MeleeRecoverSeconds) salvo en la contra
			bDuelRecovering = !(bInWindow && StaminaNow >= (bMoving ? StaminaDodgeCost : StaminaBlockCost) * 0.5f);
			if (!bDuelRecovering) { G->SceneEnd(); G->bSceneLock = false; }
			else G->GetMesh()->SetPlayRate(1.0f);
			if (bInWindow && StaminaNow >= (bMoving ? StaminaDodgeCost : StaminaBlockCost) * 0.5f)
			{
				StaminaNow = FMath::Max(0.0f, StaminaNow - (bMoving ? StaminaDodgeCost : StaminaBlockCost));
				++MeleeParries;
				++MeleeStaggers;
				PlayImpact(At, 2, false, 0, true);   // tanda P: en capas
				HeroStrikeAnim(0.0f);   // tanda O: la contra se ve: tu puño llega con la parada
				StrikeT = StrikeLen;
				ContactHitStop(G, 1.6f);
				// reaccion ligera: se tambalea sin salirse del alcance del remate
				G->HitReact(G->GetActorLocation() - C->GetActorLocation(), false, TEXT("spine_03"));   // tanda P: al pecho
				G->Stun(MeleeStaggerSeconds);
				G->StaggerSway(MeleeStaggerSeconds);   // tanda O: se tambalea de verdad
				// tanda O: a tiro del remate (a veces quedaba a 225 cm, fuera del alcance de la E)
				{
					const FVector Away = (G->GetActorLocation() - C->GetActorLocation()).GetSafeNormal2D();
					if (FVector::Dist2D(G->GetActorLocation(), C->GetActorLocation()) > MeleeContactDistance + 45.0f && !Away.IsNearlyZero())
						G->SetActorLocation(FVector(C->GetActorLocation().X, C->GetActorLocation().Y, G->GetActorLocation().Z) + Away * (MeleeContactDistance + 25.0f), true);
				}
				DuelPhaseN = DuelStagger; DuelT = 0.0f; DuelPhaseLen = MeleeStaggerSeconds;
				DuelNoise(At);
				ExchangeHappened(true);   // tanda Q: sin camara lenta en la contra (una por encuentro, en el remate)
			}
			else if (bBlockHeld && StaminaNow >= StaminaBlockCost)
			{
				StaminaNow -= StaminaBlockCost;
				++MeleeBlocked;
				PlayImpact(C->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 0, false, 1, false);
				ContactHitStop(G, 0.7f, false);
				ExchangeHappened(false);
				DuelNoise(At);
				DuelPhaseN = DuelGuardUp; DuelT = 0.0f; DuelPhaseLen = FMath::FRandRange(MeleeGuardUpSeconds.X, MeleeGuardUpSeconds.Y);
			}
			else
			{
				++MeleeTaken;
				++DuelStrikes;
				PlayImpact(C->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 2, false, 1, true);
				KickT = FMath::Max(KickT, 0.2f);
				HeroReactAnim();
				ContactHitStop(G, 1.3f, false);
				ExchangeHappened(false);
				SuppressT = FMath::Max(SuppressT, 1.2f);
				// tanda S: retrocede andando (antes LaunchCharacter: la capsula salia y los pies patinaban)
				if (bHeroStepRule) HeroStepPending += (C->GetActorLocation() - G->GetActorLocation()).GetSafeNormal2D() * HeroHitPushCm;
				else C->LaunchCharacter((C->GetActorLocation() - G->GetActorLocation()).GetSafeNormal2D() * HeroHitPushSpeed, true, false);   // tanda R
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
		GrabSceneTick(DeltaSeconds);
		if (bGrabFreed)
		{
			GrabSceneEnd(true);
			++MeleeGrabEscapes;
			PlayImpact(At, 1, false, 0, true);
			// tanda R: sin parada de golpe al soltarte, y la reaccion (con su fisica) un fotograma despues: en el mismo, la
			// malla aun tenia la pose de la pareja (la raiz 86 cm adelante) y los cuerpos fisicos su sitio en la escena: la
			// pelvis se metia en Cuttlas. Ver bGrabReactPending
			bGrabReactPending = true;
			G->Stun(MeleeStaggerSeconds * 0.8f);
			DuelPhaseN = DuelStagger; DuelT = 0.0f; DuelPhaseLen = MeleeStaggerSeconds * 0.8f;
		}
		else if (DuelT >= DuelPhaseLen)
		{
			// no te soltaste: te detienen (en calma, sin golpes)
			GrabSceneEnd(false);
			DuelEnd();
			bCaptureWounded = false;
			BeginCapture(G);
			return;
		}
		break;
	case DuelStagger:
		if (bGrabReactPending && DuelT > 0.0f)
		{
			bGrabReactPending = false;
			G->HitReact(G->GetActorLocation() - C->GetActorLocation(), true, TEXT("spine_02"));
			G->PoseBridge(SceneAlignSeconds);
			G->StaggerSway(FMath::Max(DuelPhaseLen - DuelT, 0.3f));   // tanda O
		}
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
	// tanda S: justo despues de un duelo, todo como estaba (al caer el del duelo el flanqueador se recolocaba)
	if (FPlatformTime::Seconds() < FlankFrozenUntil) return;
	Roles.Reset();
	// tanda Q: los puntos de flanqueo se conservan (recalcular cada 0,5 s los hacia corregir el rumbo sin parar)
	TMap<TWeakObjectPtr<ATarsisGuard>, FVector> OldPoints = FlankPoints;
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
	if (Alert.Num() < 2) { FlankAngles.Reset(); LastFixer = nullptr; return; }
	// donde esta el objetivo: tu sitio si alguno te ve; si no, donde te perdieron
	const ATarsisGuard* Seer = nullptr;
	for (ATarsisGuard* G : Alert) if (G->UnseenT < 0.5f) { Seer = G; break; }
	const FVector Target = Seer ? P->GetActorLocation() : (Alert[0]->LastSeen.IsZero() ? P->GetActorLocation() : Alert[0]->LastSeen);
	Alert.Sort([&Target](const ATarsisGuard& A, const ATarsisGuard& B) { return FVector::DistSquared(A.GetActorLocation(), Target) < FVector::DistSquared(B.GetActorLocation(), Target); });
	// tanda R: el que fija sigue fijando salvo que otro quede FixerSwapMargin mas cerca (antes, siempre el mas cercano:
	// al moverse se cambiaban los papeles y cada cambio era un punto nuevo, una vuelta mas)
	ATarsisGuard* Fixer = Alert[0];
	if (ATarsisGuard* Old = LastFixer.Get())
	{
		const int32 OldIdx = Alert.Find(Old);
		if (OldIdx > 0 && FVector::Dist2D(Old->GetActorLocation(), Target) < FVector::Dist2D(Fixer->GetActorLocation(), Target) + FixerSwapMargin)
		{
			Alert.Swap(0, OldIdx);
			Fixer = Old;
		}
	}
	if (LastFixer.Get() != Fixer) { if (LastFixer.IsValid()) ++FixerSwaps; LastFixer = Fixer; }
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
		// tanda R: el angulo de cada uno se sortea una vez por alerta, no en cada vuelta
		if (!FlankAngles.Contains(G)) FlankAngles.Add(G, FMath::FRandRange(60.0f, 110.0f));
		const float Ang = FMath::DegreesToRadians(FlankAngles[G]) * Side;
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
		// tanda Q: el punto de antes sigue si es reciente y el nuevo no se aleja mucho de el
		{
			const double NowS = FPlatformTime::Seconds();
			const FVector* Old = OldPoints.Find(G);
			const double* OldAt = FlankPointAt.Find(G);
			if (Old && OldAt && NowS - *OldAt < FlankRefreshSeconds && FVector::Dist2D(*Old, Pt) < FlankRefreshDistance * 2.0f) Pt = *Old;
			else if (Old && FVector::Dist2D(*Old, Pt) < FlankRefreshDistance) Pt = *Old;
			else { FlankPointAt.Add(G, NowS); ++FlankOrders; }
		}
		FlankPoints.Add(G, Pt);
		++Made;
	}
}

// ---------------------------------------------------------------- tanda O: contacto (tanda P: con temblor, escala, capas de sonido)
void ATarsisDirector::ContactHitStop(ATarsisGuard* G, float Scale, bool bGuardVictim)
{
	// tanda P (Sakurai): mas fuerte, mas parada (con tope); el que recibe se congela y tiembla, el que pega sigue despacio
	if (!bHitStopRule || HitStopSeconds <= 0.0f) return;
	const float S = FMath::Min(HitStopSeconds * Scale, HitStopMax);
	if (G) G->HitStop(S, bGuardVictim, G->HitStopShake * FMath::Clamp(Scale, 0.5f, 2.0f));
	if (HeroDriver)
	{
		if (bGuardVictim) HeroDriver->GlobalAnimRateScale = G ? G->HitStopAttackerRate : 0.05f;   // tu golpe sigue, muy despacio
		else { HeroDriver->bPauseAnims = true; if (Scale >= 1.0f) KickT = FMath::Max(KickT, 0.15f * Scale); }   // te dan: congelado y sacudida (tanda Q: no en lo parado)
		HeroHitStopUntil = FPlatformTime::Seconds() + S;
	}
	if (Arms && bGuardVictim) Arms->GlobalAnimRateScale = 0.05f;
	++HitStopsDone;
}

void ATarsisDirector::PlayImpact(const FVector& At, int32 Force, bool bWall, int32 Attacker, bool bVictimVoice)
{
	// tanda P: el golpe en capas (Bourne Conspiracy, God of War): grave de fuerza, medio de carne y tela, chasquido agudo;
	// pared si es contra el entorno; el esfuerzo del que pega y el dolor del que recibe. Variantes al azar
	Force = FMath::Clamp(Force, 0, 2);
	auto Capa = [&](const TCHAR* Base, int32 N, float Vol)
	{
		if (USoundBase* S = Sfx(FString::Printf(TEXT("%s_%d"), Base, FMath::RandRange(1, N))))
		{
			UGameplayStatics::PlaySoundAtLocation(this, S, At, Vol, FMath::FRandRange(0.94f, 1.06f), 0.0f, Atten);
			++ImpactLayersPlayed;
			return true;
		}
		return false;
	};
	static const float Vol[3] = { 0.55f, 0.8f, 1.0f };
	// tanda Q: prioridad (HDR de DICE): ligero 2 capas, medio 3, fuerte 5 con voces; lo que suena 0,3 s despues de algo
	// de mas rango baja 6 dB (la mitad)
	const double NowI = FPlatformTime::Seconds();
	const float Duck = (NowI - LastImpactAt < 0.3 && Force < LastImpactRank) ? 0.5f : 1.0f;
	if (Force >= LastImpactRank || NowI - LastImpactAt >= 0.3) { LastImpactRank = Force; LastImpactAt = NowI; }
	bool bAny = false;
	if (bLayeredImpactRule)
	{
		if (Force >= 1) bAny |= Capa(TEXT("golpe_grave"), 3, Vol[Force] * Duck);
		bAny |= Capa(TEXT("golpe_medio"), 3, (0.7f * Vol[Force] + 0.2f) * Duck);
		bAny |= Capa(TEXT("golpe_chasquido"), 3, (0.45f + 0.25f * Force) * Duck);
		if (bWall) Capa(TEXT("golpe_pared"), 3, 1.0f);
		if (Force >= 2)
		{
			Capa(Attacker == 0 ? TEXT("esfuerzo_cuttlas") : TEXT("esfuerzo_guardia"), 3, 0.75f);
			if (bVictimVoice) Capa(Attacker == 0 ? TEXT("dolor_guardia") : TEXT("dolor_cuttlas"), Attacker == 0 ? 3 : 2, 0.85f);
		}
	}
	if (!bAny)
	{
		if (USoundBase* S = Sfx(FString::Printf(TEXT("golpe_seco_%d"), FMath::RandRange(1, 2)))) UGameplayStatics::PlaySoundAtLocation(this, S, At, 0.8f, 1.0f, 0.0f, Atten);
		else PlaySfx(TEXT("golpe"), At, 0.8f);
	}
}

void ATarsisDirector::HeroStrikeAnim(float Lead, bool bAlways)
{
	// en tercera, Cuttlas da el puñetazo por encima del ABP del GASP (su ranura DefaultSlot, mezclado); empieza avanzado
	// para que el puño llegue Lead (HeroContactLead) despues de la tecla. Lead 0 con HeroCounterAnimPath: la contra propia
	if (Lead < 0.0f) Lead = HeroContactLead;
	if (!bThirdShown) ArmsPunch(Lead);   // en primera, tus brazos
	if (!bHeroStrikeAnimRule || (!bThirdShown && !bAlways) || !HeroDriver || bSceneHero) return;
	if (HeroDriver->GetAnimationMode() != EAnimationMode::AnimationBlueprint) return;
	UAnimInstance* AI = HeroDriver->GetAnimInstance();
	if (!AI || HeroPunchAnimPaths.Num() == 0) return;
	UAnimSequenceBase* A = nullptr;
	float Contact = 0.4f;
	if (Lead <= 0.0f && !HeroCounterAnimPath.IsEmpty()) { A = LoadObject<UAnimSequenceBase>(nullptr, *HeroCounterAnimPath); Contact = HeroCounterContact; }
	if (!A)
	{
		HeroStrikeIdx = (HeroStrikeIdx + 1) % HeroPunchAnimPaths.Num();
		A = LoadObject<UAnimSequenceBase>(nullptr, *HeroPunchAnimPaths[HeroStrikeIdx]);
		Contact = HeroPunchContact.IsValidIndex(HeroStrikeIdx) ? HeroPunchContact[HeroStrikeIdx] : 0.4f;
	}
	if (!A) return;
	const float Start = FMath::Max(0.0f, Contact - Lead);
	if (AI->PlaySlotAnimationAsDynamicMontage(A, TEXT("DefaultSlot"), HeroStrikeBlendIn, 0.25f, 1.0f, 1, -1.0f, Start)) ++HeroStrikeAnims;   // tanda R: entrada 0,15
}

void ATarsisDirector::HeroReactAnim()
{
	// el culatazo te da: la reaccion fuerte de Lyra en el maniqui de Cuttlas (en tercera se ve; en primera, la sacudida).
	// tanda P: sin fundido de entrada, como las de los guardias
	if (!bHeroStrikeAnimRule || !HeroDriver || bSceneHero || HeroDriver->GetAnimationMode() != EAnimationMode::AnimationBlueprint) return;
	UAnimInstance* AI = HeroDriver->GetAnimInstance();
	UAnimSequenceBase* A = LoadObject<UAnimSequenceBase>(nullptr, TEXT("/Game/Characters/Mannequins/Anims/Rifle/HitReact/MM_HitReact_Front_Med_01.MM_HitReact_Front_Med_01"));
	if (AI && A && AI->PlaySlotAnimationAsDynamicMontage(A, TEXT("DefaultSlot"), 0.0f, 0.3f, 1.0f, 1, -1.0f, 0.14f)) ++HeroReactAnims;
}

void ATarsisDirector::HeroRootMotionTick()
{
	// tanda R: el root motion del golpe de Cuttlas (la acometida que queda, 25 cm) se le da a la capsula: el cuerpo no se
	// separa de ella ni vuelve de golpe, y los pies apoyados no patinan
	if (!HeroDriver || bSceneHero) return;
	UAnimInstance* AI = HeroDriver->GetAnimInstance();
	if (!AI) return;
	FRootMotionMovementParams RM = AI->ConsumeExtractedRootMotion(1.0f);
	if (!bHeroRootMotionRule || !RM.bHasRootMotion) return;
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P) return;
	FVector D = HeroDriver->ConvertLocalRootMotionToWorld(RM.GetRootMotionTransform()).GetTranslation();
	D.Z = 0.0f;
	if (D.IsNearlyZero()) return;
	if (ATarsisGuard* G = DuelGuard.Get())
	{
		// sin meterse en el guardia
		const float Now = FVector::Dist2D(P->GetActorLocation(), G->GetActorLocation());
		const float After = FVector::Dist2D(P->GetActorLocation() + D, G->GetActorLocation());
		const float Floor = MeleeContactDistance - 15.0f;
		if (After < Now && After < Floor) D *= FMath::Clamp((Now - Floor) / FMath::Max(Now - After, 0.01f), 0.0f, 1.0f);
	}
	HeroRootMotionCm += D.Size();
	// tanda S: andando (el GASP pone pasos); si no, como en la R
	if (bHeroStepRule) HeroStepPending += D;
	else P->AddActorWorldOffset(D, true);
}

// tanda S: Cuttlas recorre andando lo pendiente (root motion de su golpe y el empujon del culatazo)
void ATarsisDirector::HeroStepTick(float DeltaSeconds)
{
	if (!bHeroStepRule || HeroStepPending.IsNearlyZero()) return;
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || !C->GetCharacterMovement()) { HeroStepPending = FVector::ZeroVector; return; }
	const float Left = HeroStepPending.Size2D();
	if (Left < 2.0f) { HeroStepPending = FVector::ZeroVector; return; }
	// sin meterse en el guardia del duelo: hacia el, nunca por debajo de MeleeContactDistance (la contra le llevaba a
	// 22-25 cm de pelvis)
	if (const ATarsisGuard* G = DuelGuard.Get())
	{
		const FVector ToG = (G->GetActorLocation() - C->GetActorLocation()).GetSafeNormal2D();
		if (FVector::DotProduct(HeroStepPending.GetSafeNormal2D(), ToG) > 0.0f && FVector::Dist2D(G->GetActorLocation(), C->GetActorLocation()) <= MeleeContactDistance)
		{
			HeroStepPending = FVector::ZeroVector;
			return;
		}
	}
	const float Max = FMath::Max(C->GetCharacterMovement()->GetMaxSpeed(), 1.0f);
	const float Speed = FMath::Min(HeroStepSpeed, Left / 0.15f);
	C->AddMovementInput(HeroStepPending.GetSafeNormal2D(), FMath::Min(Speed / Max, 1.0f), true);
	// lo que la capsula ya ha recorrido en esa direccion se descuenta
	const FVector V = C->GetVelocity();
	const float Done = FMath::Max(0.0f, FVector::DotProduct(V, HeroStepPending.GetSafeNormal2D())) * DeltaSeconds;
	HeroStepPending -= HeroStepPending.GetSafeNormal2D() * FMath::Min(Done, Left);
	HeroStepCm += FMath::Min(Done, Left);
}

void ATarsisDirector::ContactTick(float DeltaSeconds)
{
	HeroRootMotionTick();
	HeroStepTick(DeltaSeconds);   // tanda S
	if (HeroHitStopUntil > 0.0 && FPlatformTime::Seconds() >= HeroHitStopUntil)
	{
		HeroHitStopUntil = 0.0;
		if (HeroDriver) { HeroDriver->bPauseAnims = false; HeroDriver->GlobalAnimRateScale = 1.0f; }
		if (Arms) Arms->GlobalAnimRateScale = 1.0f;
	}
	if (DuelContactT < 0.0f) return;
	DuelContactT -= DeltaSeconds;
	ATarsisGuard* G = DuelGuard.Get();
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	// tanda P: el sonido, una pizca antes del fotograma de contacto
	if (!bDuelSounded && DuelContactT <= ImpactSoundLead && G)
	{
		bDuelSounded = true;
		PlayImpact(G->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), DuelContactKind == 1 ? 1 : 0, false, 0, DuelContactKind == 1);
	}
	if (DuelContactT > 0.0f) return;
	DuelContactT = -1.0f;
	if (!G || !P) return;
	++ContactEvents;
	if (DuelContactKind == 1)
	{
		G->SceneEnd();
		G->bSceneLock = false;
		G->HitReact(G->GetActorLocation() - P->GetActorLocation(), false, TEXT("head"));   // tanda P: el punetazo, a la cara
		if (DuelPhaseN == DuelStagger) G->StaggerSway(FMath::Max(DuelPhaseLen - DuelT, 0.3f));   // tanda O
		ContactHitStop(G, 1.0f);
		ExchangeHappened(false);
	}
	else { ContactHitStop(G, 0.6f); ExchangeHappened(false); }
}

void ATarsisDirector::ArmsPunch(float Lead)
{
	// en primera, el puñetazo en los brazos de la vista (manos libres); tanda P: exagerado hacia el centro (ArmsTick)
	if (!bHeroStrikeAnimRule || !Arms || bThirdShown || bFPRifle || HeroPunchAnimPaths.Num() == 0) return;
	const int32 I = HeroStrikeIdx % HeroPunchAnimPaths.Num();
	UAnimSequenceBase* A = LoadObject<UAnimSequenceBase>(nullptr, *HeroPunchAnimPaths[I]);
	if (!A) return;
	const float Contact = HeroPunchContact.IsValidIndex(I) ? HeroPunchContact[I] : 0.4f;
	Arms->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	Arms->PlayAnimation(A, false);
	const float Start = FMath::Max(0.0f, Contact - Lead);
	Arms->SetPosition(Start, false);
	ArmsPunchT = FMath::Min(A->GetPlayLength() - Start, Lead + 0.3f);
	ArmsPunchAge = 0.0f;
	ArmsPunchContact = Lead;
	++ArmsPunches;
}

// ---------------------------------------------------------------- tanda Q: turnos y silencio
bool ATarsisDirector::MayFire(const ATarsisGuard* G)
{
	if (!bTurnRule || !G) return true;
	const double Now = FPlatformTime::Seconds();
	// en el duelo (y justo despues de cada intercambio) nadie mas dispara: un solo protagonista
	if (G != DuelGuard.Get() && (DuelGuard.IsValid() || Now < TurnQuietUntil)) { ++ShotsHeld; return false; }
	// fuera del duelo, un tirador a la vez: la ficha es de quien disparo hace menos de ShooterTokenSeconds
	ATarsisGuard* T = ShooterToken.Get();
	if (T && T != G && T->State == ETarsisGuardState::Alert && Now - ShooterTokenAt < ShooterTokenSeconds) { ++ShotsHeld; return false; }
	ShooterToken = const_cast<ATarsisGuard*>(G);
	ShooterTokenAt = Now;
	return true;
}

void ATarsisDirector::ExchangeHappened(bool bBig)
{
	const double Now = FPlatformTime::Seconds();
	TurnQuietUntil = FMath::Max(TurnQuietUntil, Now + TurnQuietSeconds);
	if (bBig) VoicesQuietUntil = FMath::Max(VoicesQuietUntil, Now + BigHitQuietSeconds);
}
