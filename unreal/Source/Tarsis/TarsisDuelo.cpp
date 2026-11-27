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
	HeroStrikeAnim();   // tanda O: en tercera, el puñetazo se ve
	const FVector At = G->GetActorLocation() + FVector(0.0f, 0.0f, 110.0f);
	// tanda O: lo que se ve y se oye del golpe va en el contacto del puño (HeroContactLead), no al pulsar (ContactTick)
	if (DuelPhaseN == DuelGuardUp || DuelPhaseN == DuelStrikeN)
	{
		// cubierto (o ya lanzado): lo para con el fusil
		++MeleeBlocked;
		DuelContactT = HeroContactLead; DuelContactKind = 2;
		DuelNoise(At);
	}
	else if (DuelPhaseN == DuelFeint)
	{
		// en el amago esta abierto: el golpe entra y le corta el ataque
		++MeleeLanded;
		++DuelHits;
		DuelContactT = HeroContactLead; DuelContactKind = 1;
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
				GrabSceneBegin(G);   // tanda O: las manos encima, de verdad
			}
			else
			{
				// el amago: levanta la culata despacio; suena el roce de la correa (se lee tambien a oscuras)
				// tanda O: sube justo hasta arriba del todo (MeleeWindupAt) en lo que dura el amago y ahi se queda
				DuelPhaseN = DuelFeint; DuelT = 0.0f; DuelPhaseLen = MeleeFeintSeconds;
				if (UAnimSequenceBase* A = LoadObject<UAnimSequenceBase>(nullptr, MeleeAnimPath))
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
		}
		break;
	case DuelStrikeN:
		if (!bDuelSwing && DuelT >= DuelPhaseLen - (MeleeContactAt - MeleeWindupAt))
		{
			bDuelSwing = true;
			G->GetMesh()->SetPlayRate(1.0f);
			// se echa encima: al contacto, a MeleeContactDistance de ti (la culata llega)
			DuelSwingAt = DuelT;
			DuelStepFrom = G->GetActorLocation();
			const FVector Away = (G->GetActorLocation() - C->GetActorLocation()).GetSafeNormal2D();
			DuelStepTo = FVector(C->GetActorLocation().X, C->GetActorLocation().Y, DuelStepFrom.Z) + Away * MeleeContactDistance;
			if (FVector::Dist2D(DuelStepFrom, DuelStepTo) > 120.0f || FVector::Dist2D(DuelStepFrom, C->GetActorLocation()) < MeleeContactDistance) DuelStepTo = DuelStepFrom;
		}
		if (bDuelSwing)
		{
			const float S = FMath::Clamp((DuelT - DuelSwingAt) / FMath::Max(DuelPhaseLen - DuelSwingAt, 0.01f), 0.0f, 1.0f);
			G->SetActorLocation(FMath::Lerp(DuelStepFrom, DuelStepTo, FMath::SmoothStep(0.0f, 1.0f, S)), true);
		}
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
				HeroStrikeAnim(0.0f);   // tanda O: la contra se ve: tu puño llega con la parada
				StrikeT = StrikeLen;
				ContactHitStop(G, 1.4f);
				// reaccion ligera: se tambalea sin salirse del alcance del remate
				G->HitReact(G->GetActorLocation() - C->GetActorLocation(), false);
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
				SlowMo();
			}
			else if (bBlockHeld && StaminaNow >= StaminaBlockCost)
			{
				StaminaNow -= StaminaBlockCost;
				++MeleeBlocked;
				PlaySfx(TEXT("golpe"), At, 0.6f);
				ContactHitStop(G, 0.7f);
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
				HeroReactAnim();
				ContactHitStop(G, 1.0f);
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
		GrabSceneTick(DeltaSeconds);
		if (bGrabFreed)
		{
			GrabSceneEnd(true);
			++MeleeGrabEscapes;
			PlaySfx(TEXT("empujon"), At, 0.8f);
			G->HitReact(G->GetActorLocation() - C->GetActorLocation(), true);
			G->Stun(MeleeStaggerSeconds * 0.8f);
			G->StaggerSway(MeleeStaggerSeconds * 0.8f);   // tanda O
			ContactHitStop(G, 1.0f);
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

// ---------------------------------------------------------------- tanda O: contacto
void ATarsisDirector::ContactHitStop(ATarsisGuard* G, float Scale)
{
	if (!bHitStopRule || HitStopSeconds <= 0.0f) return;
	const float S = HitStopSeconds * Scale;
	if (G) G->HitStop(S);
	if (HeroDriver)
	{
		HeroDriver->bPauseAnims = true;
		HeroHitStopUntil = FPlatformTime::Seconds() + S;
	}
	++HitStopsDone;
}

void ATarsisDirector::HeroStrikeAnim(float Lead, bool bAlways)
{
	// en tercera, Cuttlas da el puñetazo (Lyra, sin armas) por encima del ABP del GASP (su ranura DefaultSlot, mezclado);
	// empieza avanzado para que el puño llegue Lead (HeroContactLead) despues de la tecla
	if (Lead < 0.0f) Lead = HeroContactLead;
	if (!bThirdShown) ArmsPunch(Lead);   // en primera, tus brazos
	if (!bHeroStrikeAnimRule || (!bThirdShown && !bAlways) || !HeroDriver || bSceneHero) return;
	if (HeroDriver->GetAnimationMode() != EAnimationMode::AnimationBlueprint) return;
	UAnimInstance* AI = HeroDriver->GetAnimInstance();
	if (!AI) return;
	static const TCHAR* Paths[] = {
		TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_01.MM_Attack_01"),
		TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_02.MM_Attack_02") };
	static const float Contact[] = { 0.42f, 0.40f };
	HeroStrikeIdx = (HeroStrikeIdx + 1) % 2;
	UAnimSequenceBase* A = LoadObject<UAnimSequenceBase>(nullptr, Paths[HeroStrikeIdx]);
	if (!A) return;
	const float Start = FMath::Max(0.0f, Contact[HeroStrikeIdx] - Lead);
	if (AI->PlaySlotAnimationAsDynamicMontage(A, TEXT("DefaultSlot"), 0.08f, 0.25f, 1.0f, 1, -1.0f, Start)) ++HeroStrikeAnims;
}

void ATarsisDirector::HeroReactAnim()
{
	// el culatazo te da: la reaccion fuerte de Lyra en el maniqui de Cuttlas (en tercera se ve; en primera, la sacudida)
	if (!bHeroStrikeAnimRule || !HeroDriver || bSceneHero || HeroDriver->GetAnimationMode() != EAnimationMode::AnimationBlueprint) return;
	UAnimInstance* AI = HeroDriver->GetAnimInstance();
	UAnimSequenceBase* A = LoadObject<UAnimSequenceBase>(nullptr, TEXT("/Game/Characters/Mannequins/Anims/Rifle/HitReact/MM_HitReact_Front_Med_01.MM_HitReact_Front_Med_01"));
	if (AI && A && AI->PlaySlotAnimationAsDynamicMontage(A, TEXT("DefaultSlot"), 0.05f, 0.3f, 1.0f, 1, -1.0f, 0.0f)) ++HeroReactAnims;
}

void ATarsisDirector::ContactTick(float DeltaSeconds)
{
	if (HeroHitStopUntil > 0.0 && FPlatformTime::Seconds() >= HeroHitStopUntil)
	{
		HeroHitStopUntil = 0.0;
		if (HeroDriver) HeroDriver->bPauseAnims = false;
	}
	if (DuelContactT < 0.0f) return;
	DuelContactT -= DeltaSeconds;
	if (DuelContactT > 0.0f) return;
	DuelContactT = -1.0f;
	ATarsisGuard* G = DuelGuard.Get();
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!G || !P) return;
	const FVector At = G->GetActorLocation() + FVector(0.0f, 0.0f, 110.0f);
	++ContactEvents;
	if (DuelContactKind == 1)
	{
		G->SceneEnd();
		G->bSceneLock = false;
		G->HitReact(G->GetActorLocation() - P->GetActorLocation(), false);
		if (DuelPhaseN == DuelStagger) G->StaggerSway(FMath::Max(DuelPhaseLen - DuelT, 0.3f));   // tanda O
		if (USoundBase* S = Sfx(FString::Printf(TEXT("golpe_seco_%d"), FMath::RandRange(1, 2)))) UGameplayStatics::PlaySoundAtLocation(this, S, At, 0.8f, 1.1f, 0.0f, Atten);
		ContactHitStop(G, 1.0f);
	}
	else
	{
		PlaySfx(TEXT("golpe"), At, 0.45f);
		ContactHitStop(G, 0.6f);
	}
}

void ATarsisDirector::ArmsPunch(float Lead)
{
	// en primera, el puñetazo de Lyra en los brazos de la vista (manos libres): el puño entra en el centro de la imagen
	if (!bHeroStrikeAnimRule || !Arms || bThirdShown || bFPRifle) return;
	static const TCHAR* Paths[] = {
		TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_01.MM_Attack_01"),
		TEXT("/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_02.MM_Attack_02") };
	static const float Contact[] = { 0.42f, 0.40f };
	const int32 I = HeroStrikeIdx % 2;
	UAnimSequenceBase* A = LoadObject<UAnimSequenceBase>(nullptr, Paths[I]);
	if (!A) return;
	Arms->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	Arms->PlayAnimation(A, false);
	const float Start = FMath::Max(0.0f, Contact[I] - Lead);
	Arms->SetPosition(Start, false);
	ArmsPunchT = FMath::Min(A->GetPlayLength() - Start, Lead + 0.3f);
	++ArmsPunches;
}
