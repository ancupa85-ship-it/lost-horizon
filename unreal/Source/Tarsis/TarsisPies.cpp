// Lost Horizon: De Profundis - tanda T: bloqueo de pies propio. Ver TarsisPies.h.
#include "TarsisPies.h"
#include "Components/PoseableMeshComponent.h"

static void TarsisLegIK(UPoseableMeshComponent* P, FName UpN, FName LoN, FName FtN, const FVector& TargetCS)
{
	// IK de dos huesos (ley del coseno) en espacio de la malla; la rodilla se queda del lado en que estaba y el pie
	// conserva su giro
	const FTransform Up = P->GetBoneTransformByName(UpN, EBoneSpaces::ComponentSpace);
	const FTransform Lo = P->GetBoneTransformByName(LoN, EBoneSpaces::ComponentSpace);
	const FTransform Ft = P->GetBoneTransformByName(FtN, EBoneSpaces::ComponentSpace);
	const FVector A = Up.GetLocation(), B = Lo.GetLocation(), C = Ft.GetLocation();
	const float L1 = FVector::Dist(A, B), L2 = FVector::Dist(B, C);
	FVector Dir = TargetCS - A;
	const float D = FMath::Clamp(Dir.Size(), 1.0f, (L1 + L2) * 0.999f);
	if (L1 < 1.0f || L2 < 1.0f || !Dir.Normalize()) return;
	FVector Pole = (B - A) - Dir * FVector::DotProduct(B - A, Dir);
	if (!Pole.Normalize()) return;
	const float Along = (L1 * L1 - L2 * L2 + D * D) / (2.0f * D);
	const float H = FMath::Sqrt(FMath::Max(L1 * L1 - Along * Along, 0.0f));
	const FVector NB = A + Dir * Along + Pole * H;
	const FVector NC = A + Dir * D;
	const FQuat Q1 = FQuat::FindBetweenNormals((B - A).GetSafeNormal(), (NB - A).GetSafeNormal());
	const FQuat Q2 = FQuat::FindBetweenNormals(Q1.RotateVector(C - B).GetSafeNormal(), (NC - NB).GetSafeNormal());
	FTransform NUp = Up, NLo = Lo, NFt = Ft;
	NUp.SetRotation((Q1 * Up.GetRotation()).GetNormalized());
	NLo.SetRotation((Q2 * Q1 * Lo.GetRotation()).GetNormalized());
	NLo.SetLocation(NB);
	NFt.SetLocation(NC);   // el giro del pie, el de la animacion
	P->SetBoneTransformByName(UpN, NUp, EBoneSpaces::ComponentSpace);
	P->SetBoneTransformByName(LoN, NLo, EBoneSpaces::ComponentSpace);
	P->SetBoneTransformByName(FtN, NFt, EBoneSpaces::ComponentSpace);
}

void TarsisFootLockApply(UPoseableMeshComponent* P, FTarsisFootLock (&Locks)[2], float DeltaSeconds, float GroundZ, bool bActive,
	const FTarsisFootLockSettings& S)
{
	if (!P || DeltaSeconds <= 0.0f) return;
	static const FName Up[2] = { TEXT("thigh_l"), TEXT("thigh_r") };
	static const FName Lo[2] = { TEXT("calf_l"), TEXT("calf_r") };
	static const FName Ft[2] = { TEXT("foot_l"), TEXT("foot_r") };
	const FTransform CompXf = P->GetComponentTransform();
	for (int32 i = 0; i < 2; ++i)
	{
		FTarsisFootLock& L = Locks[i];
		if (P->GetBoneIndex(Ft[i]) == INDEX_NONE || P->GetBoneIndex(Lo[i]) == INDEX_NONE || P->GetBoneIndex(Up[i]) == INDEX_NONE) continue;
		const FVector Fc = P->GetBoneTransformByName(Ft[i], EBoneSpaces::ComponentSpace).GetLocation();
		const FVector Fw = CompXf.TransformPosition(Fc);
		const float AnimSpeed = L.bHasPrev ? FVector::Dist(Fc, L.PrevCS) / DeltaSeconds : 0.0f;
		L.PrevCS = Fc;
		L.bHasPrev = true;
		const bool bLow = bActive && (Fw.Z - GroundZ) < S.PlantHeight;
		const bool bPlanted = bLow && AnimSpeed < S.PlantSpeed;
		if (L.bLocked)
		{
			// clavado: aunque la animacion arrastre el pie (los pasitos del GASP apenas lo levantan), se queda hasta que
			// se aleje ReleaseDistance o la animacion lo levante de verdad
			if (!bLow || FVector::Dist2D(L.LockW, Fw) > S.ReleaseDistance) { L.bLocked = false; L.ReleaseFrom = L.LockW; }
		}
		else if (bPlanted && L.Alpha <= 0.0f)
		{
			L.bLocked = true;
			L.LockW = Fw;
		}
		const float Rate = L.bLocked ? 1.0f / FMath::Max(S.BlendIn, 0.01f) : -1.0f / FMath::Max(S.BlendOut, 0.01f);
		L.Alpha = FMath::Clamp(L.Alpha + Rate * DeltaSeconds, 0.0f, 1.0f);
		if (L.Alpha <= 0.0f) continue;
		const FVector Want(L.LockW.X, L.LockW.Y, Fw.Z);   // la altura, la de la animacion (el suelo ya lo pone el GASP)
		FVector TargetW = FMath::Lerp(Fw, Want, FMath::SmoothStep(0.0f, 1.0f, L.Alpha));
		// al soltarlo, el pie va a su sitio nuevo con un arco (paso), no arrastrado
		if (!L.bLocked) TargetW.Z += S.StepLift * FMath::Sin(PI * L.Alpha);
		TarsisLegIK(P, Up[i], Lo[i], Ft[i], CompXf.InverseTransformPosition(TargetW));
		if (L.bLocked) L.Drift = FVector::Dist2D(CompXf.TransformPosition(P->GetBoneTransformByName(Ft[i], EBoneSpaces::ComponentSpace).GetLocation()), L.LockW);
	}
}
