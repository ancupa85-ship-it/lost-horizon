// Lost Horizon: De Profundis - tanda J. Parte de ATarsisDirector: ver el bloque «tanda J» de TarsisDirector.h.
// Pulido de lo que ya habia:
// (1) La cizalla deja un agujero de verdad en la malla: el material de la tela (M_TelaMalla, tools/unreal/visual_j.py)
//     recorta alrededor de los cuatro primeros cortes (MPC_Cortes, CorteN = x, y, z, radio) y la solapa de alambre,
//     doblada hacia fuera, lleva la misma malla (MI_TelaSolapa, sin recorte).
// (2) El ascua del que fuma: una brasa que se ve (M_Ascua), que se aviva en cada calada, y el humo al soltarla (M_Humo).
// (3) El cable de una trampa brilla un poco cuando le da tu linterna (M_AlambreBrillo).
// (4) Los objetos, las trampas puestas y los cortes se guardan en el punto de control.
// (5) Rendimiento: los guardias lejos animan a menos pasos por segundo y los muy lejos no hacen sombra.
#include "TarsisDirector.h"
#include "TarsisGuard.h"
#include "TarsisSave.h"

#include "Components/PointLightComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialParameterCollection.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

namespace
{
	const TCHAR* CutMPCPath = TEXT("/Game/Tarsis/Materiales/MPC_Cortes.MPC_Cortes");
	const TCHAR* FlapMatPath = TEXT("/Game/Tarsis/Materiales/MI_TelaSolapa.MI_TelaSolapa");
	const TCHAR* EmberMatPath = TEXT("/Game/Tarsis/Materiales/M_Ascua.M_Ascua");
	const TCHAR* SmokeMatPath = TEXT("/Game/Tarsis/Materiales/M_Humo.M_Humo");
	const TCHAR* WireMatPath = TEXT("/Game/Tarsis/Materiales/M_AlambreBrillo.M_AlambreBrillo");
	constexpr int32 MaxHoles = 4;
	constexpr float HoleRadius = 42.0f;
	constexpr float PuffLife = 3.5f;

	FName CutParam(int32 Slot) { return FName(*FString::Printf(TEXT("Corte%d"), Slot)); }
	UStaticMesh* ShapeMesh(const TCHAR* Name) { return LoadObject<UStaticMesh>(nullptr, *FString::Printf(TEXT("/Engine/BasicShapes/%s.%s"), Name, Name)); }
}

// ---------------------------------------------------------------- consultas

FVector ATarsisDirector::ReliefPostLoc(int32 Index) const
{
	return ReliefPosts.IsValidIndex(Index) ? ReliefPosts[Index].Loc : FVector::ZeroVector;
}

FString ATarsisDirector::ReliefPostName(int32 Index) const
{
	return ReliefPosts.IsValidIndex(Index) ? ReliefPosts[Index].Name : FString();
}

bool ATarsisDirector::PlanKnown() const
{
	return FactKnown(FName(TEXT("plano_rondas")));
}

float ATarsisDirector::EmberGlow(const ATarsisGuard* G) const
{
	const float* V = EmberGlows.Find(const_cast<ATarsisGuard*>(G));
	return V ? *V : 0.0f;
}

bool ATarsisDirector::EmberVisible(const ATarsisGuard* G) const
{
	const TObjectPtr<UStaticMeshComponent>* M = EmberMeshes.Find(const_cast<ATarsisGuard*>(G));
	return M && *M && (*M)->IsVisible();
}

int32 ATarsisDirector::FenceHolesOpen() const
{
	return FMath::Min(FenceCuts.Num(), MaxHoles);
}

bool ATarsisDirector::FenceFlapIsMesh(int32 Index) const
{
	if (!FenceCuts.IsValidIndex(Index)) return false;
	const UStaticMeshComponent* M = FenceCuts[Index].Mesh.Get();
	const UMaterialInterface* Mat = M ? M->GetMaterial(0) : nullptr;
	return Mat && Mat->GetPathName() == FlapMatPath;
}

int32 ATarsisDirector::AnimLodLevel(const ATarsisGuard* G) const
{
	const int32* L = AnimLods.Find(const_cast<ATarsisGuard*>(G));
	return L ? *L : 0;
}

// ---------------------------------------------------------------- la malla cortada

void ATarsisDirector::MakeCut(const FVector& Loc, const FVector& Normal)
{
	if (!CutMPC) CutMPC = LoadObject<UMaterialParameterCollection>(nullptr, CutMPCPath);
	FTarsisCut K;
	K.Loc = Loc;
	K.Normal = Normal.GetSafeNormal2D();
	const int32 Slot = FenceCuts.Num();
	// la solapa: el trozo de malla cortado por tres lados, doblado hacia fuera sobre el que queda (la bisagra)
	const FVector T(-K.Normal.Y, K.Normal.X, 0.0f);
	const float Open = FMath::DegreesToRadians(62.0f);
	const FVector Hinge = Loc + T * HoleRadius;
	const FVector Dir = (-T * FMath::Cos(Open) + K.Normal * FMath::Sin(Open)).GetSafeNormal();
	const FVector Center = Hinge + Dir * HoleRadius + FVector(0.0f, 0.0f, 48.0f);
	if (UStaticMeshComponent* M = AddBlock(Center, FVector(0.004f, HoleRadius * 2.0f / 100.0f, 1.08f), FLinearColor(0.2f, 0.2f, 0.19f), false))
	{
		M->SetWorldRotation(FRotator(0.0f, Dir.Rotation().Yaw - 90.0f, 0.0f));
		if (UMaterialInterface* Flap = LoadObject<UMaterialInterface>(nullptr, FlapMatPath)) M->SetMaterial(0, Flap);
		M->SetCastShadow(true);
		ItemMeshes.Add(M);
		K.Mesh = M;
	}
	FenceCuts.Add(K);
	if (CutMPC && Slot < MaxHoles)
	{
		UKismetMaterialLibrary::SetVectorParameterValue(this, CutMPC, CutParam(Slot), FLinearColor(Loc.X, Loc.Y, Loc.Z, HoleRadius));
	}
}

void ATarsisDirector::ClearCuts()
{
	for (const FTarsisCut& K : FenceCuts)
	{
		if (UStaticMeshComponent* M = K.Mesh.Get()) { ItemMeshes.Remove(M); M->DestroyComponent(); }
	}
	FenceCuts.Reset();
	if (!CutMPC) CutMPC = LoadObject<UMaterialParameterCollection>(nullptr, CutMPCPath);
	if (CutMPC)
	{
		for (int32 i = 0; i < MaxHoles; ++i) UKismetMaterialLibrary::SetVectorParameterValue(this, CutMPC, CutParam(i), FLinearColor(0.0f, 0.0f, 0.0f, 0.0f));
	}
}

// ---------------------------------------------------------------- las trampas (piezas)

void ATarsisDirector::BuildTrapParts(FTarsisTrap& T)
{
	const FLinearColor Wire(0.05f, 0.05f, 0.045f), Tin(0.38f, 0.37f, 0.33f);
	if (T.Kind == 1)
	{
		const FVector Mid = (T.A + T.B) * 0.5f;
		if (UStaticMeshComponent* M = AddBlock(Mid, FVector(FVector::Dist(T.A, T.B) / 100.0f, 0.008f, 0.008f), Wire, false))
		{
			M->SetWorldRotation((T.B - T.A).Rotation());
			// alambre galvanizado: con la linterna se le ve un hilo de brillo (Brillo, PulidoTick)
			if (UMaterialInterface* WM = LoadObject<UMaterialInterface>(nullptr, WireMatPath))
			{
				M->SetMaterial(0, WM);
				M->CreateDynamicMaterialInstance(0);
			}
			TrapMeshes.Add(M);
			T.Parts.Add(M);
		}
		return;
	}
	const FVector Ahead = T.Loc;
	FVector R = (T.B - T.A).GetSafeNormal2D();
	if (R.IsNearlyZero()) R = FVector(0.0f, 1.0f, 0.0f);
	if (UStaticMeshComponent* M = AddBlock(Ahead + FVector(0.0f, 0.0f, 22.0f), FVector(0.9f, 0.005f, 0.005f), Wire, false))
	{
		M->SetWorldRotation(R.Rotation());
		TrapMeshes.Add(M);
		T.Parts.Add(M);
	}
	for (const float s : { -1.0f, 1.0f })
	{
		if (UStaticMeshComponent* Post = AddBlock(Ahead + R * (45.0f * s) + FVector(0.0f, 0.0f, 12.0f), FVector(0.025f, 0.025f, 0.24f), FLinearColor(0.12f, 0.08f, 0.05f), false))
		{
			TrapMeshes.Add(Post);
			T.Parts.Add(Post);
		}
		if (UStaticMeshComponent* Can = AddBlock(Ahead + R * (14.0f * s) + FVector(0.0f, 0.0f, 13.0f), FVector(0.07f, 0.07f, 0.11f), Tin, false))
		{
			if (UStaticMesh* Cyl = ShapeMesh(TEXT("Cylinder"))) Can->SetStaticMesh(Cyl);
			TrapMeshes.Add(Can);
			T.Parts.Add(Can);
		}
	}
}

// ---------------------------------------------------------------- el punto de control

void ATarsisDirector::SaveItems(UTarsisSave* S) const
{
	if (!S) return;
	S->ItemCigs = Cigs;
	S->ItemDoses = SleepDoses;
	S->ItemCans = TrapCans;
	S->ItemWires = TrapWires;
	S->ItemSel = ItemSel;
	S->bItemFakeOrder = bFakeOrderUsed;
	S->bItemPot = bPotDrugged;
	S->ItemsCounted = ItemsCounted.Array();
	for (const FTarsisTrap& T : Traps)
	{
		if (T.bDead) continue;
		S->TrapKinds.Add(T.Kind);
		S->TrapLocs.Add(T.Loc);
		S->TrapAs.Add(T.A);
		S->TrapBs.Add(T.B);
	}
	for (const FTarsisCut& K : FenceCuts)
	{
		S->CutLocs.Add(K.Loc);
		S->CutNormals.Add(K.Normal);
	}
}

void ATarsisDirector::LoadItems(const UTarsisSave* S)
{
	if (!S || S->ItemCigs < 0) return;   // guardada antes de la tanda J: los objetos se quedan como estan
	// lo recogido ya esta contado (si no, la bandera volveria a sumar las cajetillas y las dosis)
	ItemsCounted.Reset();
	for (const FName& N : S->ItemsCounted) ItemsCounted.Add(N);
	Cigs = S->ItemCigs;
	SleepDoses = S->ItemDoses;
	TrapCans = S->ItemCans;
	TrapWires = S->ItemWires;
	bFakeOrderUsed = S->bItemFakeOrder;
	bPotDrugged = S->bItemPot;
	for (int32 i = Traps.Num() - 1; i >= 0; --i) RemoveTrap(i);
	for (int32 i = 0; i < S->TrapKinds.Num(); ++i)
	{
		FTarsisTrap T;
		T.Kind = S->TrapKinds[i];
		T.Loc = S->TrapLocs.IsValidIndex(i) ? S->TrapLocs[i] : FVector::ZeroVector;
		T.A = S->TrapAs.IsValidIndex(i) ? S->TrapAs[i] : T.Loc;
		T.B = S->TrapBs.IsValidIndex(i) ? S->TrapBs[i] : T.Loc;
		BuildTrapParts(T);
		Traps.Add(T);
	}
	ClearCuts();
	for (int32 i = 0; i < S->CutLocs.Num(); ++i) MakeCut(S->CutLocs[i], S->CutNormals.IsValidIndex(i) ? S->CutNormals[i] : FVector(1.0f, 0.0f, 0.0f));
	if (!SelectItem(S->ItemSel)) CycleItem(1);
}

// ---------------------------------------------------------------- el tick

void ATarsisDirector::PulidoTick(float DeltaSeconds)
{
	UWorld* W = GetWorld();
	if (!W) return;
	const float Now = W->GetTimeSeconds();
	if (!bCutsReset)
	{
		// los agujeros del material son de la partida: al empezar, ninguno
		bCutsReset = true;
		if (FenceCuts.Num() == 0) ClearCuts();
	}
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	FVector Cam = FVector::ZeroVector;
	FRotator CamRot = FRotator::ZeroRotator;
	if (PC) PC->GetPlayerViewPoint(Cam, CamRot);

	// (2) el ascua y el humo
	UStaticMesh* Sphere = ShapeMesh(TEXT("Sphere"));
	for (const TPair<TObjectPtr<ATarsisGuard>, TObjectPtr<UPointLightComponent>>& E : Embers)
	{
		ATarsisGuard* G = E.Key;
		UPointLightComponent* L = E.Value;
		if (!G || !L) continue;
		float& Clk = DragClock.FindOrAdd(G);
		const float Prev = Clk;
		Clk += DeltaSeconds;
		const float Every = FMath::Max(DragEvery, 2.5f);
		const float Ph = FMath::Fmod(Clk, Every), PrevPh = FMath::Fmod(Prev, Every);
		// la calada: sube en medio segundo, aguanta y se apaga; entre caladas, la brasa casi muerta que tiembla
		float Glow = FMath::SmoothStep(0.0f, 0.5f, Ph) * (1.0f - FMath::SmoothStep(1.1f, 1.7f, Ph));
		Glow = FMath::Max(Glow, 0.14f + 0.05f * FMath::Sin(Now * 7.3f + G->GetUniqueID()));
		EmberGlows.Add(G, Glow);
		L->SetIntensity(3.0f + 34.0f * Glow);
		L->SetAttenuationRadius(60.0f + 90.0f * Glow);
		TObjectPtr<UStaticMeshComponent>& EM = EmberMeshes.FindOrAdd(G);
		if (!EM && Sphere)
		{
			EM = NewObject<UStaticMeshComponent>(G);
			EM->SetStaticMesh(Sphere);
			EM->SetupAttachment(L);
			EM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			EM->SetCastShadow(false);
			EM->SetCanEverAffectNavigation(false);
			if (UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, EmberMatPath)) EM->SetMaterial(0, M);
			EM->RegisterComponent();
			EM->CreateDynamicMaterialInstance(0);
		}
		if (EM)
		{
			EM->SetRelativeScale3D(FVector(0.011f + 0.006f * Glow));
			if (UMaterialInstanceDynamic* D = Cast<UMaterialInstanceDynamic>(EM->GetMaterial(0))) D->SetScalarParameterValue(TEXT("Brillo"), 15.0f + 160.0f * Glow);
		}
		// al soltar la calada, el humo (tres bocanadas que suben, crecen y se deshacen)
		if (PrevPh < 2.1f && Ph >= 2.1f && Sphere && Puffs.Num() < 30)
		{
			const FVector From = L->GetComponentLocation() + G->GetActorForwardVector() * 6.0f;
			for (int32 i = 0; i < 3; ++i)
			{
				UStaticMeshComponent* P = NewObject<UStaticMeshComponent>(this);
				P->SetStaticMesh(Sphere);
				P->SetMobility(EComponentMobility::Movable);
				P->SetCollisionEnabled(ECollisionEnabled::NoCollision);
				P->SetCastShadow(false);
				P->SetCanEverAffectNavigation(false);
				P->SetWorldLocation(From + FMath::VRand() * 2.0f);
				P->SetWorldScale3D(FVector(0.03f));
				if (UMaterialInterface* M = LoadObject<UMaterialInterface>(nullptr, SmokeMatPath)) P->SetMaterial(0, M);
				P->RegisterComponent();
				P->CreateDynamicMaterialInstance(0);
				Puffs.Add(P);
				PuffAge.Add(-0.18f * i);
				PuffVel.Add(G->GetActorForwardVector() * (14.0f - 3.0f * i) + FVector(0.0f, 0.0f, 10.0f + 4.0f * i) + FMath::VRand() * 3.0f);
				++SmokePuffs;
			}
		}
	}
	for (auto It = EmberMeshes.CreateIterator(); It; ++It)
	{
		if (It->Key && Embers.Contains(It->Key)) continue;
		if (It->Value) It->Value->DestroyComponent();
		if (It->Key) { EmberGlows.Remove(It->Key.Get()); DragClock.Remove(It->Key.Get()); }
		It.RemoveCurrent();
	}
	for (int32 i = Puffs.Num() - 1; i >= 0; --i)
	{
		UStaticMeshComponent* P = Puffs[i];
		PuffAge[i] += DeltaSeconds;
		const float A = PuffAge[i];
		if (!P || A > PuffLife)
		{
			if (P) P->DestroyComponent();
			Puffs.RemoveAt(i); PuffAge.RemoveAt(i); PuffVel.RemoveAt(i);
			continue;
		}
		if (A < 0.0f) { P->SetVisibility(false); continue; }
		P->SetVisibility(true);
		P->AddWorldOffset(PuffVel[i] * DeltaSeconds);
		PuffVel[i] = PuffVel[i] * FMath::Pow(0.55f, DeltaSeconds) + FVector(0.0f, 0.0f, 6.0f * DeltaSeconds);
		P->SetWorldScale3D(FVector(0.03f + 0.11f * A));
		if (UMaterialInstanceDynamic* D = Cast<UMaterialInstanceDynamic>(P->GetMaterial(0)))
		{
			D->SetScalarParameterValue(TEXT("Opacidad"), 0.32f * FMath::Min(1.0f, A * 5.0f) * (1.0f - A / PuffLife));
		}
	}

	// (3) el cable con la linterna
	WireGlint = 0.0f;
	for (const FTarsisTrap& T : Traps)
	{
		if (T.Kind != 1 || T.bDead || T.Parts.Num() == 0) continue;
		UStaticMeshComponent* M = T.Parts[0].Get();
		UMaterialInstanceDynamic* D = M ? Cast<UMaterialInstanceDynamic>(M->GetMaterial(0)) : nullptr;
		if (!D) continue;
		float G = 0.0f;
		if (bTorch && PC)
		{
			const FVector Fwd = CamRot.Vector();
			for (int32 k = 0; k <= 6; ++k)
			{
				const FVector P = FMath::Lerp(T.A, T.B, k / 6.0f);
				const FVector To = P - Cam;
				const float Dist = To.Size();
				if (Dist < 1.0f || Dist > 1100.0f) continue;
				const float Ang = FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(To / Dist, Fwd), -1.0f, 1.0f)));
				G = FMath::Max(G, FMath::Clamp(1.0f - Ang / 20.0f, 0.0f, 1.0f) * FMath::Clamp(1.0f - Dist / 1100.0f, 0.0f, 1.0f));
			}
		}
		D->SetScalarParameterValue(TEXT("Brillo"), G);
		WireGlint = FMath::Max(WireGlint, G);
	}

	// (5) animacion y sombra por distancia (cuatro veces por segundo basta)
	AnimLodT -= DeltaSeconds;
	if (AnimLodT > 0.0f) return;
	AnimLodT = 0.25f;
	for (TActorIterator<ATarsisGuard> It(W); It; ++It)
	{
		ATarsisGuard* G = *It;
		const float D = FVector::Dist(G->GetActorLocation(), Cam);
		int32 L = 0;
		if (bAnimLod && G->State != ETarsisGuardState::Down && !G->bAlly)
		{
			L = D > AnimLodFar ? 2 : (D > AnimLodNear ? 1 : 0);
			if (L < 2 && D > 800.0f && !G->WasRecentlyRendered(0.5f)) L = 2;
		}
		int32& Old = AnimLods.FindOrAdd(G, -1);
		if (Old != L)
		{
			Old = L;
			const float Interval = L == 0 ? 0.0f : (L == 1 ? 1.0f / 30.0f : 1.0f / 12.0f);
			TInlineComponentArray<USkeletalMeshComponent*> Sk(G);
			for (USkeletalMeshComponent* S : Sk) S->SetComponentTickInterval(Interval);
		}
		if (UPoseableMeshComponent* Pose = G->FindComponentByClass<UPoseableMeshComponent>())
		{
			const bool bShadow = !bAnimLod || D < ShadowCullDist;
			if (Pose->CastShadow != bShadow) Pose->SetCastShadow(bShadow);
		}
	}
}
