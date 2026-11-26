// Lost Horizon: De Profundis - tanda K. Parte de ATarsisDirector (y de ATarsisGuard): ver el bloque «tanda K».
// Revolverse: cuando van a detenerte (el que llega a por ti, el culatazo, el que te toca), un instante para la E: le
// quitas el fusil de un golpe, el arma sale despedida al suelo y el guardia queda aturdido (la E otra vez lo derriba).
// Si no, va a por su fusil y pide refuerzos por radio; sin fusil ni apunta ni dispara: viene a por ti con las manos, y
// si te toca, otra ventana (y esta vez acaba en el suelo). Desarmar: al que te apunta en el alto, si llegas a menos de
// DisarmDist, la E le golpea el arma. El fusil del suelo lo recoges con la E (el selector: FUSIL, letal y muy ruidoso)
// o lo recoge el primer guardia que pase. La idea de la ventana (la abre el que ataca, en un instante de su accion, y
// quien la aprovecha deja al otro aturdido) es comun en los juegos de cuerpo a cuerpo; el codigo es propio.
#include "TarsisDirector.h"
#include "TarsisGuard.h"
#include "TarsisSave.h"

#include "AIController.h"
#include "Animation/AnimationAsset.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

namespace
{
	ATarsisDirector* CuerpoDirector(const UObject* Ctx)
	{
		for (TActorIterator<ATarsisDirector> It(Ctx->GetWorld()); It; ++It) return *It;
		return nullptr;
	}
	const TCHAR* RiflePath = TEXT("/Game/Tarsis/Armas/M14/SM_M14.SM_M14");
}

// ---------------------------------------------------------------- el guardia sin fusil

void ATarsisGuard::SetDisarmed(bool bOn)
{
	bDisarmed = bOn;
	if (bOn) RifleW = 0.0f;   // tanda L: los brazos sueltos ya, sin pasar por la pose de fusil
	if (Rifle) Rifle->SetVisibility(!bOn, true);
}

void ATarsisGuard::GoForRifle(const FVector& Where)
{
	if (State == ETarsisGuardState::Down || bAlly) return;
	LastSeen = Where;
	UnseenT = 0.0f;
	Meter = 1.0f;
	if (State != ETarsisGuardState::Alert) SetState(ETarsisGuardState::Alert);
}

bool ATarsisGuard::DisarmedTick(float DeltaSeconds, APawn* Player, float V)
{
	ATarsisDirector* D = CuerpoDirector(this);
	if (!D) return false;
	FVector RL;
	if (D->FloorRifleOf(this, RL))
	{
		// a por su fusil, corriendo, sin hacerte caso
		Walk(RL, RunSpeed);
		if (Near2D(RL, 110.0f)) D->RifleRecovered(this);
		return true;
	}
	// el fusil se lo has quitado tu (o lo tiene otro): viene a por ti con las manos
	if (!Player) return true;
	const float Dist = FVector::Dist2D(GetActorLocation(), Player->GetActorLocation());
	if (V > 0.0f && Dist < CatchDistance) { Caught(Player); return true; }
	Walk(V > 0.0f ? Player->GetActorLocation() : LastSeen, RunSpeed);
	if (V <= 0.0f && (Near2D(LastSeen, 120.0f) || UnseenT > 20.0f)) SetState(ETarsisGuardState::Search);
	return true;
}

// ---------------------------------------------------------------- consultas

float ATarsisDirector::CounterWindowNow(const ATarsisGuard* G) const
{
	float W = CounterWindow * (Difficulty <= 0 ? CounterEasyMul : (Difficulty >= 2 ? CounterHardMul : 1.0f));
	if (Wounds > 0) W *= 0.8f;
	// con otro encima (en alerta y a menos de 7 m), mas corta
	if (G)
	{
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (*It == G || It->bTowerSentry || It->bAlly || It->State != ETarsisGuardState::Alert) continue;
			if (FVector::Dist2D(It->GetActorLocation(), G->GetActorLocation()) < 700.0f) { W *= 0.7f; break; }
		}
	}
	return W;
}

int32 ATarsisDirector::FloorRifleCount() const
{
	int32 N = 0;
	for (const FTarsisFloorRifle& R : FloorRifles) if (R.Actor.IsValid()) ++N;
	return N;
}

FVector ATarsisDirector::FloorRifleLoc(int32 Index) const
{
	int32 N = 0;
	for (const FTarsisFloorRifle& R : FloorRifles)
	{
		if (!R.Actor.IsValid()) continue;
		if (N++ == Index) return R.Actor->GetActorLocation();
	}
	return FVector::ZeroVector;
}

bool ATarsisDirector::FloorRifleOf(const ATarsisGuard* G, FVector& OutLoc) const
{
	for (const FTarsisFloorRifle& R : FloorRifles)
	{
		if (R.Actor.IsValid() && R.Owner.Get() == G) { OutLoc = R.Actor->GetActorLocation(); return true; }
	}
	return false;
}

ATarsisGuard* ATarsisDirector::DisarmTarget() const
{
	if (!bHalt || bCapturing || bCounterOpen) return nullptr;
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P) return nullptr;
	ATarsisGuard* Best = nullptr;
	float BestD = DisarmDist;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		if (G->bTowerSentry || G->bAlly || G->bDisarmed || !G->HasRifle() || G->State != ETarsisGuardState::Alert || G->IsStunned()) continue;
		const float Dd = FVector::Dist2D(G->GetActorLocation(), P->GetActorLocation());
		if (Dd < BestD && FMath::Abs(G->GetActorLocation().Z - P->GetActorLocation().Z) < 150.0f) { BestD = Dd; Best = G; }
	}
	return Best;
}

int32 ATarsisDirector::FloorRifleNear() const
{
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P) return -1;
	for (int32 i = 0; i < FloorRifles.Num(); ++i)
	{
		const AStaticMeshActor* A = FloorRifles[i].Actor.Get();
		if (A && FVector::Dist2D(A->GetActorLocation(), P->GetActorLocation()) < 140.0f && FMath::Abs(A->GetActorLocation().Z - P->GetActorLocation().Z) < 160.0f) return i;
	}
	return -1;
}

// ---------------------------------------------------------------- la ventana

void ATarsisDirector::CounterOrCapture(ATarsisGuard* G)
{
	if (!G) return;
	if (bCounterOpen)
	{
		// otro mas encima mientras te revuelves: la ventana se acorta (una vez)
		if (G != CounterGuard && !bCounterSqueezed) { CounterLeft *= 0.6f; bCounterSqueezed = true; }
		return;
	}
	if (!bCounterRule || bCapturing || bCine || bDone || bRiding || bHiding || G->bTowerSentry || G->bAlly || G->State == ETarsisGuardState::Down)
	{
		BeginCapture(G);
		return;
	}
	bCounterOpen = true;
	bCounterSqueezed = false;
	CounterGuard = G;
	CounterLen = CounterLeft = CounterWindowNow(G);
	G->Hold(CounterLen + 0.25f);
	if (AAIController* AI = Cast<AAIController>(G->GetController())) AI->StopMovement();
	if (APawn* P = UGameplayStatics::GetPlayerPawn(this, 0)) PlaySfx(TEXT("empujon"), P->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 0.3f);
}

void ATarsisDirector::DisarmGuard(ATarsisGuard* G)
{
	if (!G || G->State == ETarsisGuardState::Down) return;
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	const FVector Away = P ? (G->GetActorLocation() - P->GetActorLocation()).GetSafeNormal2D() : G->GetActorForwardVector() * -1.0f;
	if (!G->bDisarmed)
	{
		// el fusil sale despedido: un actor con fisica, de lado y hacia arriba
		UStaticMesh* Mesh = nullptr;
		FTransform T(G->GetActorRotation(), G->GetActorLocation() + FVector(0.0f, 0.0f, 40.0f));
		for (UActorComponent* C : G->GetComponents())
		{
			UStaticMeshComponent* S = Cast<UStaticMeshComponent>(C);
			if (S && S->GetStaticMesh() && S->GetStaticMesh()->GetName().Contains(TEXT("M14"))) { Mesh = S->GetStaticMesh(); T = S->GetComponentTransform(); break; }
		}
		if (!Mesh) Mesh = LoadObject<UStaticMesh>(nullptr, RiflePath);
		// tanda M: arrancado hacia un lado (antes caia detras del guardia, en la linea de la vista: la E dudaba entre los dos),
		// hacia el lado con sitio libre: contra una pared o un contenedor se quedaba encima o donde el guardia no llega
		const FVector R = FVector::CrossProduct(FVector::UpVector, Away);
		const FVector From = G->GetActorLocation() + FVector(0.0f, 0.0f, 30.0f);
		FCollisionQueryParams Q(SCENE_QUERY_STAT(FusilLado), false, G);
		if (P) Q.AddIgnoredActor(P);
		auto Libre = [&](const FVector& Dir) { FHitResult H; return !GetWorld()->LineTraceSingleByChannel(H, From, From + Dir * 420.0f, ECC_Visibility, Q); };
		float Sign = FMath::RandBool() ? 1.0f : -1.0f;
		if (!Libre(R * Sign)) Sign = -Sign;
		const bool bSide = Libre(R * Sign);
		const FVector Side = R * Sign * FMath::FRandRange(0.6f, 0.8f);
		SpawnFloorRifle(Mesh, T, G, bSide ? Away * 230.0f + Side * 320.0f + FVector(0.0f, 0.0f, 260.0f) : Away * 340.0f + FVector(0.0f, 0.0f, 260.0f));   // tanda N: mas lejos (en sitios estrechos lo recuperaba al instante)
		G->SetDisarmed(true);
		++Disarms;
		GuardSay(G, TEXT("desarmado"), true);
		if (BackupT <= 0.0f && !bBackupSent) BackupT = 1.5f;   // pide refuerzos por radio enseguida
		Teach(TEXT("ensena_desarme"), TEXT("DESARMADO\nLe has quitado el fusil. Aturdido, la E lo derriba; si no, ira a por el arma.\nEl fusil del suelo se recoge con la E."), {}, 5.0f);
	}
	G->Stun(DisarmStun);
	// tanda M: con el GASP, el empujon de verdad (la pareja de la detencion al reves); si no, el traspie de antes
	if (!DisarmSceneBegin(G)) G->LaunchCharacter(Away * 140.0f + FVector(0.0f, 0.0f, 40.0f), true, false);   // un traspie: sigue a mano para la E
	if (ArrestGuard == G) ArrestGuard = nullptr;
	if (Aimer == G) Aimer = nullptr;
	KickT = 0.25f;
	StrikeT = StrikeLen;   // tanda L: se ve el golpe de Cuttlas
	++Strikes;
	if (P) PlaySfx(TEXT("golpe"), G->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 0.8f);
}

void ATarsisDirector::SpawnFloorRifle(UStaticMesh* Mesh, const FTransform& T, ATarsisGuard* RifleOwner, const FVector& Impulse)
{
	if (!Mesh) return;
	FActorSpawnParameters Sp;
	Sp.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	AStaticMeshActor* A = GetWorld()->SpawnActor<AStaticMeshActor>(T.GetLocation(), T.Rotator(), Sp);
	if (!A) return;
	UStaticMeshComponent* C = A->GetStaticMeshComponent();
	C->SetMobility(EComponentMobility::Movable);
	C->SetStaticMesh(Mesh);
	C->SetWorldScale3D(T.GetScale3D());
	C->SetCollisionProfileName(TEXT("PhysicsActor"));
	C->SetCollisionResponseToChannel(ECC_Pawn, ECR_Ignore);   // no empuja ni hace tropezar a nadie
	C->SetSimulatePhysics(true);
	if (!Impulse.IsNearlyZero())
	{
		C->AddImpulse(Impulse, NAME_None, true);
		C->AddAngularImpulseInDegrees(FMath::VRand() * 400.0f, NAME_None, true);
	}
	A->Tags.Add(FName(TEXT("fusil_suelo")));
	FTarsisFloorRifle R;
	R.Actor = A;
	R.Owner = RifleOwner;
	FloorRifles.Add(R);
}

void ATarsisDirector::RifleRecovered(ATarsisGuard* G)
{
	for (int32 i = FloorRifles.Num() - 1; i >= 0; --i)
	{
		if (FloorRifles[i].Owner.Get() != G) continue;
		if (AStaticMeshActor* A = FloorRifles[i].Actor.Get()) A->Destroy();
		FloorRifles.RemoveAt(i);
	}
	if (G)
	{
		G->SetDisarmed(false);
		GuardSay(G, TEXT("mifusil"));
		++RiflesRecovered;
	}
}

// ---------------------------------------------------------------- la E

FString ATarsisDirector::CuerpoPrompt() const
{
	if (bCounterOpen) return Tx(TEXT("p_revolverse"), TEXT("E   REVOLVERSE"));
	if (DisarmTarget()) return Tx(TEXT("p_golpear_fusil"), TEXT("E   GOLPEAR EL FUSIL"));
	if ((!TakedownTarget() || RiflePickFirst()) && FloorRifleNear() >= 0) return Tx(TEXT("p_recoger_fusil"), TEXT("E   RECOGER EL FUSIL"));
	return FString();
}

bool ATarsisDirector::CuerpoInteract()
{
	if (bCounterOpen)
	{
		ATarsisGuard* G = CounterGuard;
		bCounterOpen = false;
		CounterGuard = nullptr;
		if (!G) return true;
		G->Hold(0.0f);
		++Counters;
		if (G->bDisarmed)
		{
			// ya sin fusil, a las manos: esta vez acaba en el suelo (tanda N: con la pareja de derribo)
			TakedownSceneBegin(G);
			G->KnockOut();
			++Takedowns;
			KickT = 0.25f;
			StrikeT = StrikeLen;
			++Strikes;
			PlaySfx(TEXT("golpe"), G->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 0.8f);
			Teach(TEXT("ensena_revolverse_suelo"), TEXT("{0} AL SUELO\nSin fusil no ha podido contigo."), { G->GuardName.ToUpper() }, 3.5f);
		}
		else DisarmGuard(G);
		return true;
	}
	if (ATarsisGuard* G = DisarmTarget())
	{
		DisarmGuard(G);
		return true;
	}
	if (TakedownTarget() && !RiflePickFirst()) return false;   // tanda L: manda lo que miras
	const int32 R = FloorRifleNear();
	if (R >= 0)
	{
		if (AStaticMeshActor* A = FloorRifles[R].Actor.Get()) A->Destroy();
		FloorRifles.RemoveAt(R);
		PlayerRifleAmmo += RifleAmmoPick;
		SelectItem(9);
		if (APawn* P = UGameplayStatics::GetPlayerPawn(this, 0)) PlaySfx(TEXT("llaves"), P->GetActorLocation(), 0.3f);
		Teach(TEXT("ensena_fusil"), TEXT("EL FUSIL\nEn el selector (FUSIL). Disparar es matar, y se oye en media base."), {}, 4.5f);
		return true;
	}
	return false;
}

// ---------------------------------------------------------------- tu disparo con el fusil

void ATarsisDirector::FireRifle()
{
	if (PlayerRifleAmmo <= 0) return;
	if (!bLethal)
	{
		ShowMessage(Tx(TEXT("fusil_sinletal"), TEXT("EL FUSIL\nCon la via letal apagada no se dispara.")), 2.5f);
		return;
	}
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!PC || !P) return;
	--PlayerRifleAmmo;
	++RifleShots;
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	// el guardia cuyo cuerpo cruza la linea de tiro, sin nada en medio (como el dardo, pero a 80 m)
	float BestT = 8000.0f;
	if (ATarsisGuard* G = DartLine(Loc, Rot.Vector(), BestT))
	{
		if (G->State != ETarsisGuardState::Down && !G->bAlly)
		{
			G->Kill();
			++Kills;
			Killed.AddUnique(G->GuardName);
		}
	}
	// 7,62: se oye en media base
	USoundBase* S = Sfx(FString::Printf(TEXT("disparo_cerca_%d"), FMath::RandRange(1, 4)));
	if (S) UGameplayStatics::PlaySound2D(this, S, 1.0f);
	else PlaySfx(TEXT("disparo"), Loc, 1.0f);
	TensionT = FMath::Max(TensionT, 150.0f);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->bTowerSentry || It->bAlly || It->State == ETarsisGuardState::Down || It->State == ETarsisGuardState::Alert) continue;
		if (FVector::Dist(It->GetActorLocation(), Loc) < RifleHeard) It->HearNoise(Loc);
	}
	KickT = 0.18f;
	RecoilT = 1.0f;
	PC->SetControlRotation(PC->GetControlRotation() + FRotator(1.6f, FMath::FRandRange(-0.4f, 0.4f), 0.0f));   // el 7,62 patea
	if (PlayerRifleAmmo == 0) { ShowMessage(Tx(TEXT("fusil_vacio"), TEXT("SIN CARTUCHOS\nEl cargador esta vacio.")), 2.5f); CycleItem(1); }
}

// ---------------------------------------------------------------- el tick

void ATarsisDirector::CuerpoTick(float DeltaSeconds)
{
	UWorld* W = GetWorld();
	if (!W) return;
	WeaponTick(DeltaSeconds);   // tanda L
	DisarmSceneTick(DeltaSeconds);   // tanda M
	TakedownSceneTick(DeltaSeconds);   // tanda N
	PeligroTick(DeltaSeconds);
	HeroSlingTick();
	// la ventana: se cierra sola y te detienen como siempre
	if (bCounterOpen)
	{
		CounterLeft -= DeltaSeconds;
		ATarsisGuard* G = CounterGuard;
		if (!G || G->State == ETarsisGuardState::Down || bCapturing) { bCounterOpen = false; CounterGuard = nullptr; }
		else if (CounterLeft <= 0.0f)
		{
			bCounterOpen = false;
			CounterGuard = nullptr;
			++CounterFails;
			G->Hold(0.0f);
			BeginCapture(G);
		}
	}
	// la sacudida del golpe: unos tirones cortos de la vista
	if (KickT > 0.0f)
	{
		KickT -= DeltaSeconds;
		if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
		{
			PC->AddPitchInput(FMath::FRandRange(-0.6f, 0.6f));
			PC->AddYawInput(FMath::FRandRange(-0.6f, 0.6f));
		}
	}
	// los fusiles del suelo
	for (int32 i = FloorRifles.Num() - 1; i >= 0; --i)
	{
		FTarsisFloorRifle& R = FloorRifles[i];
		AStaticMeshActor* A = R.Actor.Get();
		if (!A) { FloorRifles.RemoveAt(i); continue; }
		// el dueno, al rehacerse, va a por el (sin el queda en alerta)
		ATarsisGuard* O = R.Owner.Get();
		if (O && O->bDisarmed && !O->IsStunned() && O->State != ETarsisGuardState::Down && O->State != ETarsisGuardState::Alert) O->GoForRifle(A->GetActorLocation());
		// otro guardia que pase y lo vea, lo recoge
		ATarsisGuard* K = R.Picker.Get();
		if (K)
		{
			if (K->State == ETarsisGuardState::Down || K->State == ETarsisGuardState::Alert || !K->IsOnErrand()) { R.Picker = nullptr; continue; }
			if (FVector::Dist2D(K->GetActorLocation(), A->GetActorLocation()) < 130.0f)
			{
				K->EndErrand();
				GuardSay(K, TEXT("fusil"));
				++RiflesRecovered;
				A->Destroy();
				FloorRifles.RemoveAt(i);
			}
			continue;
		}
		if (O && O->bDisarmed && O->State != ETarsisGuardState::Down) continue;   // es suyo y va a por el
		for (TActorIterator<ATarsisGuard> It(W); It; ++It)
		{
			ATarsisGuard* G = *It;
			if (G == O || G->bDisarmed || G->bTowerSentry || G->bAlly || G->IsHeld() || G->IsBusy() || G->IsOnErrand()) continue;
			if (G->State != ETarsisGuardState::Patrol && G->State != ETarsisGuardState::Return && G->State != ETarsisGuardState::Search) continue;
			const FVector Eye = G->GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
			if (FVector::Dist(Eye, A->GetActorLocation()) > 700.0f) continue;
			FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisVeFusil), false, G);
			Q.AddIgnoredActor(A);
			FHitResult H;
			if (W->LineTraceSingleByChannel(H, Eye, A->GetActorLocation() + FVector(0.0f, 0.0f, 10.0f), ECC_Visibility, Q)) continue;
			if (G->Errand(A->GetActorLocation(), A->GetActorLocation(), 2.0f)) { R.Picker = G; break; }
		}
	}
}

// ---------------------------------------------------------------- el punto de control

void ATarsisDirector::SaveCuerpo(UTarsisSave* S) const
{
	if (!S) return;
	S->ItemRifleAmmo = PlayerRifleAmmo;
	for (const FTarsisFloorRifle& R : FloorRifles)
	{
		if (!R.Actor.IsValid()) continue;
		S->FloorRifleLocs.Add(R.Actor->GetActorLocation());
		S->FloorRifleOwners.Add(R.Owner.IsValid() ? R.Owner->GuardName : FString());
	}
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It) if (It->bDisarmed) S->DisarmedNames.Add(It->GuardName);
}

void ATarsisDirector::LoadCuerpo(const UTarsisSave* S)
{
	if (!S) return;
	PlayerRifleAmmo = S->ItemRifleAmmo;
	for (const FTarsisFloorRifle& R : FloorRifles) if (AStaticMeshActor* A = R.Actor.Get()) A->Destroy();
	FloorRifles.Reset();
	bCounterOpen = false;
	CounterGuard = nullptr;
	UStaticMesh* Mesh = LoadObject<UStaticMesh>(nullptr, RiflePath);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		It->SetDisarmed(S->DisarmedNames.Contains(It->GuardName));
		if (!Mesh)
		{
			for (UActorComponent* C : It->GetComponents())
			{
				const UStaticMeshComponent* M = Cast<UStaticMeshComponent>(C);
				if (M && M->GetStaticMesh() && M->GetStaticMesh()->GetName().Contains(TEXT("M14"))) { Mesh = M->GetStaticMesh(); break; }
			}
		}
	}
	for (int32 i = 0; i < S->FloorRifleLocs.Num(); ++i)
	{
		ATarsisGuard* RifleOwner = S->FloorRifleOwners.IsValidIndex(i) && !S->FloorRifleOwners[i].IsEmpty() ? FindGuard(*S->FloorRifleOwners[i]) : nullptr;
		SpawnFloorRifle(Mesh, FTransform(FRotator(0.0f, 0.0f, 90.0f), S->FloorRifleLocs[i] + FVector(0.0f, 0.0f, 5.0f)), RifleOwner, FVector::ZeroVector);
	}
}

// ---------------------------------------------------------------- tanda L: el fusil en tus manos y la E por mirada

bool ATarsisDirector::RiflePickFirst() const
{
	const int32 R = FloorRifleNear();
	const ATarsisGuard* G = TakedownTarget();
	if (R < 0) return false;
	if (!G) return true;
	const AStaticMeshActor* A = FloorRifles[R].Actor.Get();
	const APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!A || !PC) return false;
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	const FVector F = Rot.Vector();
	const float ToRifle = FVector::DotProduct(F, (A->GetActorLocation() - Loc).GetSafeNormal());
	const float ToGuard = FVector::DotProduct(F, (G->GetActorLocation() + FVector(0.0f, 0.0f, 20.0f) - Loc).GetSafeNormal());
	return ToRifle > ToGuard;   // el que esta mas cerca del centro de la vista
}

void ATarsisDirector::WeaponTick(float DeltaSeconds)
{
	if (StrikeT > 0.0f) StrikeT = FMath::Max(0.0f, StrikeT - DeltaSeconds);
	if (!Pistol) return;
	const bool bWant = ItemSel == 9 && PlayerRifleAmmo > 0;
	if (bWant && !FPRifleMesh)
	{
		// el M14 de los guardias (el mismo modelo)
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It && !FPRifleMesh; ++It)
		{
			for (UActorComponent* C : It->GetComponents())
			{
				const UStaticMeshComponent* M = Cast<UStaticMeshComponent>(C);
				if (M && M->GetStaticMesh() && M->GetStaticMesh()->GetName().Contains(TEXT("M14"))) { FPRifleMesh = M->GetStaticMesh(); break; }
			}
		}
	}
	if (bWant && FPRifleMesh)
	{
		if (!bFPRifle)
		{
			PistolMeshKeep = Pistol->GetStaticMesh();
			PistolGripKeep = Pistol->GetRelativeTransform();
			Pistol->SetStaticMesh(FPRifleMesh);
			bFPRifle = true;
			// tanda M: los brazos con la pose de fusil de Lyra (dos manos), no la de la pistola
			if (Arms)
				if (UAnimationAsset* RA = LoadObject<UAnimationAsset>(nullptr, *FPRifleArmsAnimPath)) Arms->PlayAnimation(RA, true);
		}
		Pistol->SetRelativeTransform(FPRifleGrip);   // cada fotograma: se puede afinar en el director en marcha
	}
	else if (bFPRifle)
	{
		if (PistolMeshKeep) Pistol->SetStaticMesh(PistolMeshKeep);
		Pistol->SetRelativeTransform(PistolGripKeep);
		bFPRifle = false;
		if (Arms)
			if (UAnimationAsset* PA = LoadObject<UAnimationAsset>(nullptr, *ArmsAnimPath)) Arms->PlayAnimation(PA, true);
	}
}

bool ATarsisDirector::HeroSlingShown() const
{
	return HeroSling && HeroSling->IsVisible();
}

void ATarsisDirector::HeroSlingTick()
{
	// tanda M: en tercera persona, el fusil recogido va a la espalda de Cuttlas (en primera lo llevas en las manos)
	const bool bWant = HeroBody && bThirdShown && ItemCount(9) > 0 && !bCapturing;
	if (bWant && !HeroSling && FPRifleMesh)
	{
		HeroSling = NewObject<UStaticMeshComponent>(this, TEXT("FusilEspalda"));
		HeroSling->SetStaticMesh(FPRifleMesh);
		HeroSling->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		HeroSling->SetupAttachment(HeroBody, TEXT("spine_03"));
		HeroSling->RegisterComponent();
	}
	if (!HeroSling) return;
	if (HeroSling->IsVisible() != bWant) HeroSling->SetVisibility(bWant);
	if (bWant) HeroSling->SetRelativeTransform(HeroSlingXf);   // se puede afinar en el director en marcha
}
