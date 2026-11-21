// Tanda A (2026-11-21): los guardias se mueven con el Animation Blueprint del Game Animation Sample de Epic
// (Motion Matching, inercialización, giros en el sitio, arranques y paradas, IK de pies), en vez de una mezcla de
// quieto-andar-trotar con saltos entre animaciones sueltas. Ver docs/animacion-tanda-a.md.
//
// Montaje (sin editar grafos, que Python no alcanza):
//  - BP_GuardiaGASP es una copia de SandboxCharacter_CMC reparentada a ATarsisGuard, sin cámara, sin traversal y sin
//    AC_PreCMCTick (que fijaría la velocidad por su cuenta). Conserva su implementación de
//    BPI_SandboxCharacter_Pawn::Get_PropertiesForAnimation, que lee el CharacterMovementComponent y sus variables Gait y
//    CharacterInputState: el ABP le pide los datos por esa interfaz, sin cast.
//  - GetMesh() pasa a ser el maniquí UEFN, oculto, que corre SandboxCharacter_CMC_ABP.
//  - GaspBody, hijo de GetMesh(), es la persona (MakeHuman) con ABP_GenericRetarget: copia la pose del padre con el
//    IK Retargeter RTG_UEFN_<persona>. De GaspBody copian el cuerpo visible (Pose), los pasos y los gestos, como antes.
//  - Caer y apuntar siguen siendo animaciones sueltas de la persona (las del GASP no traen armas: tanda B).
#include "TarsisGuard.h"

#include "Animation/AnimInstance.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "UObject/UnrealType.h"

static const TCHAR* GaspMeshPath = TEXT("/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin.SKM_UEFN_Mannequin");
static const TCHAR* GaspAbpPath = TEXT("/Game/Blueprints/SandboxCharacter_CMC_ABP.SandboxCharacter_CMC_ABP_C");
static const TCHAR* GaspRetargetPath = TEXT("/Game/Blueprints/RetargetedCharacters/ABP_GenericRetarget.ABP_GenericRetarget_C");
static const TCHAR* GaspPawnBpiPath = TEXT("/Game/Blueprints/BPI_SandboxCharacter_Pawn.BPI_SandboxCharacter_Pawn_C");

// posición de un hueso en la pose de referencia, en espacio de la malla (como RefBonePos de TarsisGuard.cpp)
static FVector GaspRefBone(const USkeletalMesh* Mesh, FName Bone)
{
	const FReferenceSkeleton& Ref = Mesh->GetRefSkeleton();
	int32 I = Ref.FindBoneIndex(Bone);
	if (I == INDEX_NONE) return FVector::ZeroVector;
	FTransform T = FTransform::Identity;
	while (I != INDEX_NONE)
	{
		T = T * Ref.GetRefBonePose()[I];
		I = Ref.GetParentIndex(I);
	}
	return T.GetLocation();
}

// hacia dónde mira la malla en reposo (del tobillo a la punta del pie) y a qué altura queda la punta del pie
static void GaspFacing(const USkeletalMesh* Mesh, float& OutYaw, float& OutBallZ)
{
	const FVector Foot = GaspRefBone(Mesh, TEXT("foot_l")), Ball = GaspRefBone(Mesh, TEXT("ball_l"));
	const FVector FootR = GaspRefBone(Mesh, TEXT("foot_r")), BallR = GaspRefBone(Mesh, TEXT("ball_r"));
	FVector Fwd = (Ball - Foot) + (BallR - FootR);
	Fwd.Z = 0.0f;
	OutYaw = Fwd.IsNearlyZero() ? 0.0f : -FMath::RadiansToDegrees(FMath::Atan2(Fwd.Y, Fwd.X));
	OutBallZ = FMath::Min(Ball.Z, BallR.Z);
}

USkeletalMeshComponent* ATarsisGuard::AnimBody() const
{
	return GaspBody ? GaspBody.Get() : GetMesh();
}

bool ATarsisGuard::SetupGasp()
{
	if (GaspBody) return true;
	USkeletalMeshComponent* M = GetMesh();
	if (!bGaspAnim || !BodyMesh || !M || !GetWorld() || !GetWorld()->IsGameWorld()) return false;
	UClass* Bpi = LoadObject<UClass>(nullptr, GaspPawnBpiPath);
	if (!Bpi || !GetClass()->ImplementsInterface(Bpi)) return false;   // guardia C++ a secas: el sistema de siempre
	USkeletalMesh* Uefn = LoadObject<USkeletalMesh>(nullptr, GaspMeshPath);
	UClass* Abp = LoadObject<UClass>(nullptr, GaspAbpPath);
	GaspRetargetClass = LoadObject<UClass>(nullptr, GaspRetargetPath);
	if (!Uefn || !Abp || !GaspRetargetClass)
	{
		UE_LOG(LogTemp, Warning, TEXT("Tarsis: %s implementa la interfaz del GASP pero faltan sus assets; animación de siempre"), *GetName());
		return false;
	}
	const float HalfH = GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	// el que conduce: maniquí UEFN oculto con el ABP de Epic (se evalúa aunque no se dibuje)
	float UYaw = 0.0f, UBall = 0.0f;
	GaspFacing(Uefn, UYaw, UBall);
	M->SetSkeletalMesh(Uefn);
	M->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	M->SetAnimInstanceClass(Abp);
	M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	M->SetCastShadow(false);
	M->SetHiddenInGame(true);
	M->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	const float UZ = -HalfH - UBall + 3.0f;
	M->SetRelativeLocationAndRotation(FVector(0.0f, 0.0f, UZ), FRotator(0.0f, UYaw, 0.0f));
	// la persona, pegada al que conduce (ABP_GenericRetarget toma la pose de la malla a la que va pegada)
	float PYaw = 0.0f, PBall = 0.0f;
	GaspFacing(BodyMesh, PYaw, PBall);
	GaspBody = NewObject<USkeletalMeshComponent>(this, TEXT("CuerpoPersona"));
	GaspBody->SetSkeletalMesh(BodyMesh);
	GaspBody->SetupAttachment(M);
	GaspBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	GaspBody->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	GaspBody->SetRelativeLocationAndRotation(FVector(0.0f, 0.0f, (-HalfH - PBall + 3.0f) - UZ), FRotator(0.0f, PYaw - UYaw + GaspBodyYaw, 0.0f));
	GaspBody->RegisterComponent();
	GaspBody->AddTickPrerequisiteComponent(M);   // primero la pose de Epic, luego la copia
	GaspRestore();
	// el CMC con los valores con que se grabaron las bases de Motion Matching: aceleración y frenada suaves, sin girar
	// de golpe (lo demás, velocidades y giros, lo sigue poniendo el guardia)
	if (UCharacterMovementComponent* Move = GetCharacterMovement())
	{
		Move->MaxAcceleration = GaspMaxAcceleration;
		Move->BrakingDecelerationWalking = GaspBrakingDeceleration;
	}
	UE_LOG(LogTemp, Log, TEXT("Tarsis: %s anima con el GASP (retarget %s)"), *GetName(), GaspRetargeter ? *GaspRetargeter->GetName() : TEXT("NINGUNO"));
	return true;
}

void ATarsisGuard::GaspPointRetargeter()
{
	if (!GaspBody || !BodyMesh) return;
	if (!GaspRetargeter)
	{
		// RTG_UEFN_<persona>: la persona es la carpeta de la malla (/Game/Tarsis/Personas/<persona>_<huella>/...)
		FString Folder = FPackageName::GetLongPackagePath(BodyMesh->GetOutermost()->GetName());
		Folder = FPaths::GetCleanFilename(Folder).ToLower();
		FString Persona = Folder;
		Folder.Split(TEXT("_"), &Persona, nullptr);
		TArray<FAssetData> List;
		IAssetRegistry::GetChecked().GetAssetsByPath(FName(TEXT("/Game/Tarsis/Anim")), List, true);
		for (const FAssetData& A : List)
		{
			const FString N = A.AssetName.ToString().ToLower();
			if (A.AssetClassPath.GetAssetName() == FName(TEXT("IKRetargeter")) && (N == TEXT("rtg_uefn_") + Persona || N == TEXT("rtg_uefn_") + Folder))
			{
				GaspRetargeter = A.GetAsset();
				break;
			}
		}
	}
	UAnimInstance* AI = GaspBody->GetAnimInstance();
	if (!AI || !GaspRetargeter) return;
	if (FObjectProperty* P = CastField<FObjectProperty>(AI->GetClass()->FindPropertyByName(TEXT("IKRetargeter"))))
	{
		P->SetObjectPropertyValue_InContainer(AI, GaspRetargeter);
	}
}

void ATarsisGuard::GaspSingle(UAnimationAsset* A, bool bLoop)
{
	if (!GaspBody || !A) return;
	if (bGaspSingle && CurrentAnim == A) return;
	GaspBody->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	GaspBody->PlayAnimation(A, bLoop);
	GaspBody->SetPlayRate(1.0f);
	CurrentAnim = A;
	bGaspSingle = true;
}

void ATarsisGuard::GaspRestore()
{
	if (!GaspBody || !GaspRetargetClass) return;
	GaspBody->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	GaspBody->SetAnimInstanceClass(GaspRetargetClass);
	GaspPointRetargeter();
	CurrentAnim = nullptr;
	bGaspSingle = false;
}

bool ATarsisGuard::GaspSetEnum(FName Prop, const FString& Value)
{
	FProperty* P = GetClass()->FindPropertyByName(Prop);
	UEnum* E = nullptr;
	if (FByteProperty* BP = CastField<FByteProperty>(P)) E = BP->Enum;
	else if (FEnumProperty* EP = CastField<FEnumProperty>(P)) E = EP->GetEnum();
	if (!E) return false;
	// los enums de Blueprint guardan NewEnumeratorN por dentro: se busca por el nombre que se ve
	int64 V = INDEX_NONE;
	for (int32 i = 0; i < E->NumEnums(); ++i)
	{
		if (E->GetDisplayNameTextByIndex(i).ToString() == Value || E->GetNameStringByIndex(i) == Value) { V = E->GetValueByIndex(i); break; }
	}
	if (V == INDEX_NONE) return false;
	if (FByteProperty* BP = CastField<FByteProperty>(P)) BP->SetPropertyValue_InContainer(this, (uint8)V);
	else if (FEnumProperty* EP = CastField<FEnumProperty>(P)) EP->GetUnderlyingProperty()->SetIntPropertyValue(EP->ContainerPtrToValuePtr<void>(this), V);
	return true;
}

bool ATarsisGuard::GaspTick()
{
	if (!GaspBody) return false;
	const float Speed = GetVelocity().Size2D();
	bTurnStepping = false;   // los giros en el sitio los pone el ABP
	// apuntar (en alerta y parado) y caer siguen siendo animaciones sueltas de la persona
	if (State == ETarsisGuardState::Alert && Speed <= 15.0f && AimAnim) { GaspSingle(AimAnim, true); return true; }
	if (bGaspSingle) GaspRestore();
	const UCharacterMovementComponent* Move = GetCharacterMovement();
	const FString Gait = (Move && Move->MaxWalkSpeed >= GaspRunFrom) ? TEXT("Run") : TEXT("Walk");
	if (Gait != GaspGaitNow && GaspSetEnum(TEXT("Gait"), Gait)) GaspGaitNow = Gait;
	return true;
}
