// Lost Horizon: De Profundis - tanda I. Parte de ATarsisDirector: ver el bloque «tanda I» de TarsisDirector.h.
// (0) La mira: apuntando, la boca de la pistola se lleva al centro de la pantalla, que es por donde va el dardo.
// (1) El selector: rueda del raton o 1-6 cambian el objeto en mano; el clic izquierdo lo usa (con el dardo, dispara).
// (2) Objetos: tabaco (el guardia se para a fumar), somnifero (olla de la cocina o cantimplora), cizalla (corte en la
//     malla de una valla), walkie (la red desde cualquier sitio y una orden falsa), espejo (vista por la esquina) y el
//     plano de la jefatura (rondas y relevos en el mapa mental).
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

namespace
{
	const TCHAR* ItemNames[] = { TEXT("DARDOS"), TEXT("PIEDRAS"), TEXT("LATAS"), TEXT("CABLE"), TEXT("TABACO"), TEXT("SOMNIFERO"), TEXT("CIZALLA"), TEXT("WALKIE"), TEXT("ESPEJO"), TEXT("FUSIL") };
	const TCHAR* ZoneNames[] = { TEXT("la capilla"), TEXT("el hangar"), TEXT("la plaza de armas"), TEXT("el barracon oeste"), TEXT("el anillo oeste") };

	struct FZone { const TCHAR* Name; float X, Y; };
	const FZone PlanZones[] = {
		{ TEXT("patio central"), 4300.0f, 3950.0f }, { TEXT("barracon oeste"), 1500.0f, 2600.0f }, { TEXT("jefatura"), 700.0f, 3500.0f },
		{ TEXT("hangar"), 4900.0f, 6800.0f }, { TEXT("cocina"), 6200.0f, 3500.0f }, { TEXT("enfermeria"), 7900.0f, 3100.0f },
		{ TEXT("plaza de armas"), 7900.0f, 4200.0f }, { TEXT("porton de entrada"), -1900.0f, 5700.0f }, { TEXT("anillo norte"), 3000.0f, -1100.0f },
		{ TEXT("anillo oeste"), -1000.0f, 2500.0f }, { TEXT("anillo este"), 8500.0f, 1500.0f }, { TEXT("capilla"), 6400.0f, -1250.0f },
		{ TEXT("transmisiones"), 6275.0f, 2000.0f }, { TEXT("camino del sur"), 3600.0f, 5770.0f } };

	const TCHAR* ZoneOf(const FVector& P)
	{
		const FZone* Best = &PlanZones[0];
		float BestD = TNumericLimits<float>::Max();
		for (const FZone& Z : PlanZones)
		{
			const float D = FVector2D::Distance(FVector2D(P), FVector2D(Z.X, Z.Y));
			if (D < BestD) { BestD = D; Best = &Z; }
		}
		return Best->Name;
	}

	bool IsFence(const AActor* A)
	{
		if (!A) return false;
		TInlineComponentArray<UStaticMeshComponent*> Ms(A);
		for (const UStaticMeshComponent* M : Ms)
		{
			if (M && M->GetStaticMesh() && M->GetStaticMesh()->GetName().StartsWith(TEXT("valla"))) return true;
		}
		return false;
	}
}

// ---------------------------------------------------------------- la mira

FVector2D ATarsisDirector::AimMuzzleOffset() const
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC || !Pistol) return FVector2D(9.0f, 9.0f);
	const FVector M = Pistol->DoesSocketExist(TEXT("Muzzle")) ? Pistol->GetSocketLocation(TEXT("Muzzle")) : Pistol->Bounds.Origin;
	// sobre la linea de vista (la pistola se dibuja con el campo de vision de primera persona: lo que esta en el eje de la
	// camara sale en el centro con cualquier campo de vision)
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	const FVector L = Rot.UnrotateVector(M - Loc);
	if (L.X <= 1.0f) return FVector2D(9.0f, 9.0f);
	return FVector2D(L.Y / L.X, -L.Z / L.X);   // tangentes: 0,0 = en el centro
}

FVector2D ATarsisDirector::DartScreenOffset() const
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC) return FVector2D(9.0f, 9.0f);
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	FVector2D S;
	int32 W = 0, H = 0;
	PC->GetViewportSize(W, H);
	if (W <= 0 || H <= 0 || !PC->ProjectWorldLocationToScreen(Loc + Rot.Vector() * 1000.0f, S, false)) return FVector2D(9.0f, 9.0f);
	return FVector2D(S.X / W - 0.5f, S.Y / H - 0.5f);
}

void ATarsisDirector::AimAlignTick(float DeltaSeconds)
{
	// apuntando del todo, la boca de la pistola va al eje de la camara (un poco por debajo, como unas miras): asi la cruz
	// del HUD, la pistola y el dardo coinciden. Lo corrido se queda para la proxima vez
	if (!Pistol || !Arms || AimAlpha < 0.97f || !Arms->IsVisible()) return;
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC) return;
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	const FVector M = Pistol->DoesSocketExist(TEXT("Muzzle")) ? Pistol->GetSocketLocation(TEXT("Muzzle")) : Pistol->Bounds.Origin;
	const FVector L = Rot.UnrotateVector(M - Loc);
	const float K = FMath::Min(1.0f, DeltaSeconds * 8.0f);
	AimAutoShift.Y = FMath::Clamp(AimAutoShift.Y - L.Y * K, -20.0f, 20.0f);
	AimAutoShift.Z = FMath::Clamp(AimAutoShift.Z + (AimSightDrop - L.Z) * K, -20.0f, 20.0f);
}

// ---------------------------------------------------------------- el selector

int32 ATarsisDirector::ItemCount(int32 Item) const
{
	switch (Item)
	{
	case 0: return Darts;
	case 1: return -1;
	case 2: return TrapCans;
	case 3: return TrapWires;
	case 4: return Cigs;
	case 5: return SleepDoses;
	case 6: return HasFlag(FName(TEXT("obj_cizalla"))) ? -1 : 0;
	case 7: return HasWalkie() ? -1 : 0;
	case 8: return HasFlag(FName(TEXT("obj_espejo"))) ? -1 : 0;
	case 9: return PlayerRifleAmmo;   // tanda K: el fusil que le quitaste a un guardia
	default: return 0;
	}
}

FString ATarsisDirector::ItemName(int32 Item) const
{
	return (Item >= 0 && Item < NumItems) ? Tx(FName(*FString::Printf(TEXT("obj_nombre_%d"), Item)), ItemNames[Item]) : FString();
}

bool ATarsisDirector::HasWalkie() const
{
	return HasFlag(FName(TEXT("obj_walkie")));
}

bool ATarsisDirector::ItemKeyAllowed() const
{
	// con una eleccion abierta (dialogo, central, calabozo, teclado, codec, menu) las cifras son de esa eleccion
	return !bChoice && !bKeypad && !bCellAsk && !bRadioAsk && !bCodec && !bMenu && !bMindMap && !bCine && !bDone;
}

bool ATarsisDirector::SelectItem(int32 Item)
{
	if (Item < 0 || Item >= NumItems || ItemCount(Item) == 0) return false;
	if (ItemSel == 8 && Item != 8) UseItemRelease();
	ItemSel = Item;
	return true;
}

void ATarsisDirector::CycleItem(int32 Dir)
{
	if (!ItemKeyAllowed()) return;
	for (int32 k = 1; k <= NumItems; ++k)
	{
		const int32 I = ((ItemSel + Dir * k) % NumItems + NumItems) % NumItems;
		if (SelectItem(I)) return;
	}
}

void ATarsisDirector::UseItem()
{
	if (bCine || bDone || bMenu || bCodec || bKeypad || bChoice || bHiding || bRiding || bCapturing) return;
	if (ItemCount(ItemSel) == 0) { if (ItemSel != 0) CycleItem(1); if (ItemSel != 0 && ItemCount(ItemSel) == 0) return; }
	switch (ItemSel)
	{
	case 0: ShootDart(); break;
	case 9: FireRifle(); break;   // tanda K
	case 1: ThrowStone(); break;
	case 2:
	{
		// las latas aunque estes en un paso estrecho
		const int32 W = TrapWires;
		TrapWires = 0;
		PlaceTrap();
		TrapWires = W;
		break;
	}
	case 3:
	{
		const ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
		FVector A, B;
		if (C && NarrowAt(C->GetActorLocation() + C->GetActorForwardVector() * 70.0f, C->GetActorForwardVector(), A, B))
		{
			const int32 N = TrapCans;
			TrapCans = 0;
			PlaceTrap();
			TrapCans = N;
		}
		else ShowMessage(Tx(TEXT("obj_cable_estrecho"), TEXT("EL CABLE, EN UN PASO ESTRECHO\nTiene que ir de pared a pared.")), 2.5f);
		break;
	}
	case 4: DropCig(); break;
	case 5: DrugPot(); break;
	case 6: CutFence(); break;
	case 7: FakeOrder(); break;
	case 8:
		bMirrorOn = true;
		Teach(TEXT("ensena_espejo"), TEXT("EL ESPEJO\nCon el clic mantenido miras por la esquina hacia el lado al que te asomas (Z / V).\nAgachado, por debajo de una puerta."), {}, 4.0f);
		break;
	default: break;
	}
}

void ATarsisDirector::UseItemRelease()
{
	bMirrorOn = false;
	if (MirrorCap) MirrorCap->bCaptureEveryFrame = false;
}

// ---------------------------------------------------------------- tabaco

void ATarsisDirector::DropCig()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || Cigs <= 0) return;
	FVector P = C->GetActorLocation() + C->GetActorForwardVector().GetSafeNormal2D() * 60.0f;
	FHitResult H;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisTabaco), false, C);
	if (GetWorld()->LineTraceSingleByChannel(H, P + FVector(0.0f, 0.0f, 50.0f), P - FVector(0.0f, 0.0f, 250.0f), ECC_Visibility, Q)) P = H.ImpactPoint;
	FTarsisCig K;
	K.Loc = P;
	if (UStaticMeshComponent* M = AddBlock(P + FVector(0.0f, 0.0f, 1.5f), FVector(0.085f, 0.055f, 0.022f), FLinearColor(0.75f, 0.68f, 0.5f), false))
	{
		M->SetWorldRotation(FRotator(0.0f, C->GetActorRotation().Yaw + 25.0f, 0.0f));
		ItemMeshes.Add(M);
		K.Mesh = M;
	}
	CigPacks.Add(K);
	--Cigs;
	PlaySfx(TEXT("recoger"), P, 0.25f);
	Teach(TEXT("ensena_tabaco"), TEXT("TABACO EN EL SUELO\nEl primero que pase la vera, se parara a cogerla y se fumara un pitillo.\nDe noche se le ve el ascua."), {}, 4.0f);
}

bool ATarsisDirector::IsSmoking(const ATarsisGuard* G) const
{
	for (const TPair<TWeakObjectPtr<ATarsisGuard>, float>& S : Smokers) if (S.Key.Get() == G) return true;
	return false;
}

void ATarsisDirector::StopSmoking(ATarsisGuard* G)
{
	Smokers.Remove(G);
	if (TObjectPtr<UPointLightComponent>* L = Embers.Find(G))
	{
		if (*L) (*L)->DestroyComponent();
		Embers.Remove(G);
	}
}

// ---------------------------------------------------------------- somnifero

void ATarsisDirector::DrugPot()
{
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || SleepDoses <= 0) return;
	if (!bPotDrugged && FVector::Dist2D(P->GetActorLocation(), SleepPotLoc) < 230.0f)
	{
		bPotDrugged = true;
		--SleepDoses;
		EatNextT = 3.0f;
		PlaySfx(TEXT("recoger"), SleepPotLoc + FVector(0.0f, 0.0f, 90.0f), 0.4f);
		ShowMessage(Tx(TEXT("obj_olla"), TEXT("SOMNIFERO EN LA OLLA\nLos dos primeros que vengan a comer se dormiran al rato.")), 4.0f);
		return;
	}
	if (ATarsisGuard* G = TakedownTarget())
	{
		// por la espalda, en su cantimplora
		if (!G->bTowerSentry && !G->bAlly && !Sleepers.Contains(G))
		{
			--SleepDoses;
			Sleepers.Add(G, GetWorld()->GetTimeSeconds() + SleepDelay);
			PlaySfx(TEXT("recoger"), G->GetActorLocation() + FVector(0.0f, 0.0f, 90.0f), 0.2f);
			ShowMessage(Tx(TEXT("obj_cantimplora"), TEXT("SOMNIFERO EN SU CANTIMPLORA\n{0} se dormira cuando beba, dentro de un rato."), { G->GuardName }), 3.5f);
			return;
		}
	}
	ShowMessage(Tx(TEXT("obj_somnifero_donde"), TEXT("AQUI NO\nEn la olla de la cocina, o en la cantimplora de un guardia (por la espalda, sin que te vea).")), 3.0f);
}

// ---------------------------------------------------------------- cizalla

void ATarsisDirector::CutFence()
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!PC || !Pl) return;
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	FHitResult H;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisCizalla), true, Pl);
	if (!GetWorld()->LineTraceSingleByChannel(H, Loc, Loc + Rot.Vector() * 160.0f, ECC_Visibility, Q) || !IsFence(H.GetActor()))
	{
		ShowMessage(Tx(TEXT("obj_cizalla_donde"), TEXT("CIZALLA\nAcercate a la malla de una valla y mirala.")), 2.0f);
		return;
	}
	for (const FTarsisCut& K : FenceCuts) if (FVector::Dist2D(K.Loc, H.ImpactPoint) < 120.0f) return;
	// tanda J: un agujero de verdad en la malla (material) y la solapa de alambre doblada hacia fuera
	const FVector CutLoc(H.ImpactPoint.X, H.ImpactPoint.Y, Pl->GetActorLocation().Z - 80.0f);
	FVector N = H.ImpactNormal.GetSafeNormal2D();
	if (FVector::DotProduct(N, Pl->GetActorLocation() - CutLoc) < 0.0f) N = -N;   // la solapa, hacia tu lado
	MakeCut(CutLoc, N);
	++FenceCutsMade;
	PlaySfx(TEXT("candado"), CutLoc + FVector(0.0f, 0.0f, 90.0f), 0.6f);
	ShowMessage(Tx(TEXT("obj_corte"), TEXT("MALLA CORTADA\nPor aqui se pasa. Si un guardia ve el corte con luz, dara la alarma.")), 3.5f);
}

// ---------------------------------------------------------------- walkie

bool ATarsisDirector::WalkieLoot()
{
	if (HasWalkie()) return false;
	ATarsisGuard* G = DownedNear(170.0f);
	if (!G || G->bStashed) return false;
	SetFlag(FName(TEXT("obj_walkie")));
	if (RadioSnd) UGameplayStatics::PlaySound2D(this, RadioSnd, 0.3f);
	ShowMessage(Tx(TEXT("obj_walkie"), TEXT("WALKIE DE {0}\nOyes la red de la base desde cualquier sitio.\nUna vez, con el walkie en la mano (clic), puedes dar una orden falsa a la central."), { G->GuardName.ToUpper() }), 5.0f);
	return true;
}

void ATarsisDirector::FakeOrder()
{
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Pl || !HasWalkie()) return;
	if (bFakeOrderUsed)
	{
		ShowMessage(Tx(TEXT("obj_orden_usada"), TEXT("WALKIE\nOtra orden falsa no colaria: la central ya sospecha.")), 2.5f);
		return;
	}
	if (RadioDead())
	{
		ShowMessage(Tx(TEXT("obj_orden_sinred"), TEXT("WALKIE\nNo hay red: nadie te oiria.")), 2.5f);
		return;
	}
	// la zona mas lejana de donde estas, y los dos que tengas mas cerca, alli
	int32 Zi = 0;
	float Far = -1.0f;
	for (int32 i = 0; i < FakeOrderZones.Num(); ++i)
	{
		const float D = FVector::Dist2D(FakeOrderZones[i], Pl->GetActorLocation());
		if (D > Far) { Far = D; Zi = i; }
	}
	if (!FakeOrderZones.IsValidIndex(Zi)) return;
	TArray<ATarsisGuard*> Sent;
	for (int32 n = 0; n < 2; ++n)
	{
		ATarsisGuard* Best = nullptr;
		float BestD = TNumericLimits<float>::Max();   // por radio lo oye toda la base
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			ATarsisGuard* G = *It;
			if (Sent.Contains(G) || G->bTowerSentry || G->bAlly || G->IsHeld() || G->IsBusy() || G->IsOnErrand()) continue;
			if (G->State != ETarsisGuardState::Patrol && G->State != ETarsisGuardState::Return) continue;
			const float D = FVector::Dist2D(G->GetActorLocation(), Pl->GetActorLocation());
			if (D < BestD) { BestD = D; Best = G; }
		}
		if (!Best) break;
		const FVector Z = FakeOrderZones[Zi] + FVector(n * 150.0f, n * 120.0f, 0.0f);
		if (Best->Errand(Z, Z + FVector(300.0f, 0.0f, 0.0f), 90.0f)) Sent.Add(Best);
	}
	bFakeOrderUsed = true;
	FakeOrderDetections = Detections;
	if (RadioSnd) UGameplayStatics::PlaySound2D(this, RadioSnd, 0.35f);
	const FString A = Sent.Num() > 0 ? Sent[0]->GuardName : FString(TEXT("patrulla"));
	const FString B = Sent.Num() > 1 ? Sent[1]->GuardName : FString(TEXT("quien este cerca"));
	SaySubtitle(TEXT("CUTTLAS (WALKIE)"), Tx(TEXT("obj_orden"), TEXT("Central a {0} y {1}: acudid a {2}, han visto a alguien. Corto."), { A, B, Zi < 5 ? FString(ZoneNames[Zi]) : FString(TEXT("esa zona")) }), 4.0f);
	Teach(TEXT("ensena_orden"), TEXT("ORDEN FALSA\nVan a mirar. Si te pillan despues, la central sabra que la orden era tuya y la base se pondra en guardia."), {}, 4.0f);
}

// ---------------------------------------------------------------- el espejo y el plano

FVector ATarsisDirector::MirrorViewLoc() const
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	const ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!PC || !C) return FVector::ZeroVector;
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	const FRotator Y(0.0f, Rot.Yaw, 0.0f);
	if (C->bIsCrouched)
	{
		// por debajo de la puerta: a ras de suelo, delante
		const float Feet = C->GetActorLocation().Z - C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
		const FVector P = Loc + Y.Vector() * 45.0f;
		return FVector(P.X, P.Y, Feet + 10.0f);
	}
	const float Side = bLeanLeft ? -1.0f : 1.0f;
	return Loc + Y.Vector() * 45.0f + FRotationMatrix(Y).GetUnitAxis(EAxis::Y) * (Side * 28.0f);
}

void ATarsisDirector::ComposePlan()
{
	// las rondas, de cada uno donde empieza y hasta donde llega; y los relevos de las torres
	FString R;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		const ATarsisGuard* G = *It;
		if (G->bTowerSentry || G->bAlly || G->PatrolPoints.Num() == 0 || G->GuardName.IsEmpty()) continue;
		const FVector A = G->PatrolPoints[0];
		FVector Far = A;
		for (const FVector& P : G->PatrolPoints) if (FVector::Dist2D(P, A) > FVector::Dist2D(Far, A)) Far = P;
		const FString Za = ZoneOf(A), Zb = ZoneOf(Far);
		R += FString::Printf(TEXT("%s: %s%s. "), *G->GuardName.ToUpper(), *Za, Za == Zb ? TEXT("") : *(TEXT(" - ") + Zb));
	}
	Texts.Add(FName(TEXT("dt_plano_rondas")), R.IsEmpty() ? FString(TEXT("Sin rondas apuntadas.")) : R.TrimEnd());
	Texts.Add(FName(TEXT("dt_plano_relevos")), FString::Printf(TEXT("Las torres se relevan cada %d minutos: el relevo sale del barracon, espera al pie y sube; el saliente baja y vuelve. %d puestos."),
		FMath::Max(1, FMath::RoundToInt(ReliefEvery / 60.0f)), FMath::Max(0, ReliefPostCount())));
}

// ---------------------------------------------------------------- el tick

void ATarsisDirector::ItemsTick(float DeltaSeconds)
{
	AimAlignTick(DeltaSeconds);
	const float Now = GetWorld()->GetTimeSeconds();
	// lo recogido en su sitio (puntos de mision1.json, que ponen una bandera): se cuenta una vez
	auto Once = [this](const TCHAR* F) { const FName N(F); if (!HasFlag(N) || ItemsCounted.Contains(N)) return false; ItemsCounted.Add(N); return true; };
	if (Once(TEXT("obj_tabaco"))) { Cigs += 3; SelectItem(4); }
	if (Once(TEXT("obj_somnifero"))) { SleepDoses += 2; SelectItem(5); }
	if (Once(TEXT("obj_cizalla"))) SelectItem(6);
	if (Once(TEXT("obj_espejo"))) SelectItem(8);
	if (Once(TEXT("obj_walkie"))) SelectItem(7);
	if (Once(TEXT("dato_plano_rondas"))) { ComposePlan(); LearnFact(FName(TEXT("plano_relevos"))); }
	if (ItemCount(ItemSel) == 0) CycleItem(1);
	// lo que ya has cogido desaparece de su mueble (etiqueta «recoger_<bandera>», tools/unreal/relleno.py)
	if (!bPickupsScanned)
	{
		bPickupsScanned = true;
		for (TActorIterator<AActor> It(GetWorld()); It; ++It)
		{
			for (const FName& T : It->Tags) if (T.ToString().StartsWith(TEXT("recoger_"))) { Pickups.Add(*It, FName(*T.ToString().RightChop(8))); break; }
		}
	}
	for (const TPair<TWeakObjectPtr<AActor>, FName>& P : Pickups)
	{
		AActor* A = P.Key.Get();
		if (A && !A->IsHidden() && HasFlag(P.Value)) { A->SetActorHiddenInGame(true); A->SetActorEnableCollision(false); }
	}
	if (bCine || bDone) return;
	// tabaco: el que pasa y la ve va a por ella, la coge y se fuma un pitillo (el ascua se ve de noche)
	for (int32 i = CigPacks.Num() - 1; i >= 0; --i)
	{
		FTarsisCig& K = CigPacks[i];
		ATarsisGuard* T = K.Taker.Get();
		if (T)
		{
			if (T->State == ETarsisGuardState::Down || T->State == ETarsisGuardState::Alert || T->bAlly) { K.Taker = nullptr; continue; }
			if (T->AtErrand() && FVector::Dist2D(T->GetActorLocation(), K.Loc) < 140.0f)
			{
				if (UStaticMeshComponent* M = K.Mesh.Get()) { ItemMeshes.Remove(M); M->DestroyComponent(); }
				T->EndErrand();
				T->Hold(SmokeSeconds);
				T->PlayGesture(TEXT("leer"), 2.5f);
				Smokers.Add(T, SmokeSeconds);
				GuardSay(T, TEXT("tabaco"));
				UPointLightComponent* L = NewObject<UPointLightComponent>(T);
				L->SetupAttachment(T->GetMesh(), TEXT("head"));
				L->SetRelativeLocation(FVector(0.0f, 14.0f, -4.0f));
				L->SetIntensity(4.0f);
				L->SetAttenuationRadius(70.0f);
				L->SetLightColor(FLinearColor(1.0f, 0.35f, 0.08f));
				L->SetCastShadows(false);
				L->RegisterComponent();
				Embers.Add(T, L);
				++CigsSmoked;
				CigPacks.RemoveAt(i);
				continue;
			}
			if (!T->IsOnErrand()) K.Taker = nullptr;   // algo le ha distraido: la deja para otro
			continue;
		}
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			ATarsisGuard* G = *It;
			if (G->bTowerSentry || G->bAlly || G->IsHeld() || G->IsBusy() || G->IsOnErrand() || IsSmoking(G)) continue;
			if (G->State != ETarsisGuardState::Patrol && G->State != ETarsisGuardState::Return) continue;
			const FVector Eye = G->GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
			if (FVector::Dist(Eye, K.Loc) > CigSeeDist) continue;
			FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisVeTabaco), false, G);
			FHitResult H;
			if (GetWorld()->LineTraceSingleByChannel(H, Eye, K.Loc + FVector(0.0f, 0.0f, 10.0f), ECC_Visibility, Q)) continue;
			const FVector Stand = K.Loc + (G->GetActorLocation() - K.Loc).GetSafeNormal2D() * 60.0f;
			if (G->Errand(Stand, K.Loc, 30.0f)) { K.Taker = G; break; }
		}
	}
	TArray<ATarsisGuard*> Done;
	for (TPair<TWeakObjectPtr<ATarsisGuard>, float>& S : Smokers)
	{
		ATarsisGuard* G = S.Key.Get();
		S.Value -= DeltaSeconds;
		if (!G || S.Value <= 0.0f || G->State == ETarsisGuardState::Down || G->State == ETarsisGuardState::Alert || G->State == ETarsisGuardState::Suspicious) { if (G) Done.Add(G); continue; }
		// la calada (el ascua, el humo): PulidoTick, tanda J
	}
	for (ATarsisGuard* G : Done) { if (G->IsHeld() && G->State != ETarsisGuardState::Down) G->Hold(0.0f); StopSmoking(G); }
	for (auto It = Smokers.CreateIterator(); It; ++It) if (!It->Key.IsValid()) It.RemoveCurrent();
	// somnifero: a la olla van a comer de uno en uno; y el que ha comido o bebido se duerme al rato
	if (bPotDrugged && Eaters.Num() < 2)
	{
		EatNextT -= DeltaSeconds;
		if (EatNextT <= 0.0f)
		{
			EatNextT = SleepEveryS;
			ATarsisGuard* Best = nullptr;
			float BestD = 6000.0f;
			for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
			{
				ATarsisGuard* G = *It;
				if (Eaters.Contains(G) || G->bTowerSentry || G->bAlly || G->IsHeld() || G->IsBusy() || G->IsOnErrand()) continue;
				if (G->State != ETarsisGuardState::Patrol && G->State != ETarsisGuardState::Return) continue;
				const float D = FVector::Dist2D(G->GetActorLocation(), SleepPotLoc);
				if (D < BestD) { BestD = D; Best = G; }
			}
			if (Best && Best->Errand(SleepPotLoc + FVector(75.0f, 0.0f, 0.0f), SleepPotLoc, 60.0f)) Eaters.Add(Best);
		}
	}
	for (const TWeakObjectPtr<ATarsisGuard>& W : Eaters)
	{
		ATarsisGuard* G = W.Get();
		if (!G || Sleepers.Contains(G) || G->State == ETarsisGuardState::Down || !G->AtErrand()) continue;
		G->PlayGesture(TEXT("leer"), 4.0f);
		G->EndErrandIn(4.5f);
		GuardSay(G, TEXT("rancho"));
		Sleepers.Add(G, Now + SleepDelay);
	}
	for (auto It = Sleepers.CreateIterator(); It; ++It)
	{
		ATarsisGuard* G = It->Key.Get();
		if (!G) { It.RemoveCurrent(); continue; }
		if (Now < It->Value) continue;
		if (G->State != ETarsisGuardState::Down && !G->bAlly)
		{
			GuardSay(G, TEXT("sueno"));
			G->KnockOutTime = SleepTime;
			G->KnockOut();
			++SleptByDrug;
		}
		It.RemoveCurrent();
	}
	// cizalla: por el corte pasa tu capsula (solo junto a el); y el guardia que lo ve con luz da la alarma
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (C && FenceCuts.Num() > 0)
	{
		bool bNear = false;
		for (const FTarsisCut& K : FenceCuts) if (FVector::Dist2D(C->GetActorLocation(), K.Loc) < 75.0f && FMath::Abs(C->GetActorLocation().Z - K.Loc.Z) < 200.0f) bNear = true;
		if (bNear != bFenceIgnoring)
		{
			bFenceIgnoring = bNear;
			for (TActorIterator<AActor> It(GetWorld()); It; ++It)
			{
				if (!IsFence(*It)) continue;
				if (bNear) C->GetCapsuleComponent()->IgnoreActorWhenMoving(*It, true);
				else C->GetCapsuleComponent()->IgnoreActorWhenMoving(*It, false);
			}
		}
		for (FTarsisCut& K : FenceCuts)
		{
			if (K.bFound) continue;
			for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
			{
				ATarsisGuard* G = *It;
				if (G->bTowerSentry || G->bAlly || G->State == ETarsisGuardState::Down || G->State == ETarsisGuardState::Alert) continue;
				const FVector Eye = G->GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
				const FVector P = K.Loc + FVector(0.0f, 0.0f, 80.0f);
				if (FVector::Dist(Eye, P) > FenceSeeDist) continue;
				if (FVector::DotProduct(G->GetActorForwardVector(), (P - Eye).GetSafeNormal2D()) < 0.5f) continue;
				if (ATarsisGuard::LightAt(this, P) < 0.3f) continue;
				FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisVeCorte), false, G);
				Q.AddIgnoredActor(C);
				FHitResult H;
				if (GetWorld()->LineTraceSingleByChannel(H, Eye, P + K.Normal * 30.0f, ECC_Visibility, Q) && !IsFence(H.GetActor())) continue;
				K.bFound = true;
				++FenceCutsFound;
				GuardSay(G, TEXT("valla"), true);
				if (!RadioDead()) TensionT = FMath::Max(TensionT, 150.0f);
				G->HearNoise(K.Loc);
				break;
			}
		}
	}
	// la orden falsa: si te pillan despues, la central ata cabos
	if (bFakeOrderUsed && !bFakeOrderBlown && Detections > FakeOrderDetections)
	{
		bFakeOrderBlown = true;
		TensionT = FMath::Max(TensionT, 150.0f);
		CentralSay(TEXT("falsa"), Tx(TEXT("radio_falsa"), TEXT("Esa orden no salio de aqui: hay alguien en la red. Todas las unidades, en guardia.")), 0.5f);
	}
	// el espejo: una vista pequena desde la mano, mientras se mantiene el clic
	if (bMirrorOn && ItemSel == 8 && C)
	{
		if (!MirrorRT)
		{
			MirrorRT = NewObject<UTextureRenderTarget2D>(this);
			MirrorRT->InitAutoFormat(384, 256);
		}
		if (!MirrorCap)
		{
			MirrorCap = NewObject<USceneCaptureComponent2D>(this, TEXT("Espejo"));
			MirrorCap->RegisterComponent();
			MirrorCap->TextureTarget = MirrorRT;
			MirrorCap->CaptureSource = ESceneCaptureSource::SCS_FinalColorLDR;
			MirrorCap->FOVAngle = 75.0f;
			MirrorCap->HiddenActors.Add(C);
		}
		APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
		FVector Loc = FVector::ZeroVector; FRotator Rot = FRotator::ZeroRotator;
		if (PC) PC->GetPlayerViewPoint(Loc, Rot);
		const float Side = bLeanLeft ? -1.0f : 1.0f;
		const FRotator R = C->bIsCrouched ? FRotator(0.0f, Rot.Yaw, 0.0f) : FRotator(0.0f, Rot.Yaw + Side * 75.0f, 0.0f);
		MirrorCap->SetWorldLocationAndRotation(MirrorViewLoc(), R);
		MirrorCap->bCaptureEveryFrame = true;
	}
	else if (bMirrorOn && ItemSel != 8) UseItemRelease();
}
