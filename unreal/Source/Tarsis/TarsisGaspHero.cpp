// Lost Horizon: De Profundis - tanda A (2026-11-21): Cuttlas en tercera persona con el Animation Blueprint del Game
// Animation Sample de Epic (Motion Matching), como los guardias (TarsisGasp.cpp). Ver docs/animacion-tanda-a.md.
//
// Montaje (tools/unreal/gasp_cuttlas.py, modo montar):
//  - BP_CuttlasGASP es la copia entera de SandboxCharacter_CMC reparentada a BP_FirstPersonCharacter (no a la clase C++):
//    hereda tal cual sus acciones de entrada, su malla y su camara de primera persona. Su CDO lleva copiados los valores
//    del peon de antes (malla, capsula, CMC, giro con el control), asi que la primera persona no cambia: la camara cuelga
//    de la cabeza de la malla de primera persona, que copia la pose de GetMesh(), y GetMesh() sigue siendo la de siempre.
//  - El GASP no va en GetMesh(): aqui se crea un maniqui UEFN oculto (HeroDriver) con SandboxCharacter_CMC_ABP. El ABP
//    pide los datos al peon dueno por la interfaz BPI_SandboxCharacter_Pawn, que la copia implementa leyendo el CMC.
//  - HeroBody (la persona de Cuttlas) cuelga del que conduce con ABP_GenericRetarget y RTG_UEFN_cuttlas.
//  - Lo que la copia trae y no queremos se apaga al empezar (SetupGaspPlayer): AC_PreCMCTick (fijaria velocidad, giro y
//    Gait cada fotograma), traversal, smart objects, foley, VisualOverride; sus camaras y el brazo de muelle se destruyen
//    (FindComponentByClass<UCameraComponent> debe dar la de siempre); su IMC_Sandbox se quita (sus acciones duplicarian
//    la vista con el raton y la C de agacharse) y sus eventos de rueda y cruceta (cambian el estilo de camara del GASP).
// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.
#include "TarsisDirector.h"

#include "Animation/AnimInstance.h"
#include "AssetRegistry/AssetData.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/ChildActorComponent.h"
#include "Components/InputComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/LocalPlayer.h"
#include "Engine/SkeletalMesh.h"
#include "EnhancedInputSubsystems.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputMappingContext.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/UnrealType.h"

namespace
{
	const TCHAR* HeroUefnPath = TEXT("/Game/Characters/UEFN_Mannequin/Meshes/SKM_UEFN_Mannequin.SKM_UEFN_Mannequin");
	const TCHAR* HeroAbpPath = TEXT("/Game/Blueprints/SandboxCharacter_CMC_ABP.SandboxCharacter_CMC_ABP_C");
	const TCHAR* HeroRetargetPath = TEXT("/Game/Blueprints/RetargetedCharacters/ABP_GenericRetarget.ABP_GenericRetarget_C");
	const TCHAR* HeroBpiPath = TEXT("/Game/Blueprints/BPI_SandboxCharacter_Pawn.BPI_SandboxCharacter_Pawn_C");
	const TCHAR* HeroImcPath = TEXT("/Game/Input/IMC_Sandbox.IMC_Sandbox");

	FVector HeroRefBone(const USkeletalMesh* Mesh, FName Bone)
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

	// hacia donde mira la malla en reposo (del tobillo a la punta del pie) y a que altura queda la punta del pie
	void HeroFacing(const USkeletalMesh* Mesh, float& OutYaw, float& OutBallZ)
	{
		FVector Fwd = (HeroRefBone(Mesh, TEXT("ball_l")) - HeroRefBone(Mesh, TEXT("foot_l"))) + (HeroRefBone(Mesh, TEXT("ball_r")) - HeroRefBone(Mesh, TEXT("foot_r")));
		Fwd.Z = 0.0f;
		OutYaw = Fwd.IsNearlyZero() ? 0.0f : -FMath::RadiansToDegrees(FMath::Atan2(Fwd.Y, Fwd.X));
		OutBallZ = FMath::Min(HeroRefBone(Mesh, TEXT("ball_l")).Z, HeroRefBone(Mesh, TEXT("ball_r")).Z);
	}

	// los enums de Blueprint guardan NewEnumeratorN por dentro: se busca por el nombre que se ve ("Walk", "Run"...)
	bool HeroSetEnum(UObject* Obj, FName Prop, const FString& Value)
	{
		FProperty* P = Obj ? Obj->GetClass()->FindPropertyByName(Prop) : nullptr;
		UEnum* E = nullptr;
		if (FByteProperty* BP = CastField<FByteProperty>(P)) E = BP->Enum;
		else if (FEnumProperty* EP = CastField<FEnumProperty>(P)) E = EP->GetEnum();
		if (!E) return false;
		int64 V = INDEX_NONE;
		for (int32 i = 0; i < E->NumEnums(); ++i)
		{
			if (E->GetDisplayNameTextByIndex(i).ToString() == Value || E->GetNameStringByIndex(i) == Value) { V = E->GetValueByIndex(i); break; }
		}
		if (V == INDEX_NONE) return false;
		if (FByteProperty* BP = CastField<FByteProperty>(P)) BP->SetPropertyValue_InContainer(Obj, (uint8)V);
		else if (FEnumProperty* EP = CastField<FEnumProperty>(P)) EP->GetUnderlyingProperty()->SetIntPropertyValue(EP->ContainerPtrToValuePtr<void>(Obj), V);
		return true;
	}

	void HeroDropImc(APlayerController* PC, UInputMappingContext* Imc)
	{
		if (!PC || !Imc) return;
		if (ULocalPlayer* LP = PC->GetLocalPlayer())
		{
			if (UEnhancedInputLocalPlayerSubsystem* S = LP->GetSubsystem<UEnhancedInputLocalPlayerSubsystem>())
			{
				if (S->HasMappingContext(Imc)) S->RemoveMappingContext(Imc);
			}
		}
	}
}

void ATarsisDirector::SetupGaspPlayer(ACharacter* C)
{
	bHeroGaspPawn = false;
	if (!C) return;
	UClass* Bpi = LoadObject<UClass>(nullptr, HeroBpiPath);
	if (!Bpi || !C->GetClass()->ImplementsInterface(Bpi)) return;   // el peon de siempre: nada que limpiar
	bHeroGaspPawn = true;
	APlayerController* PC = Cast<APlayerController>(C->GetController());
	// componentes de juego del GASP: apagados (no se pueden quitar del BP sin dejar nodos huerfanos)
	TArray<UActorComponent*> Comps;
	C->GetComponents(Comps);
	UCameraComponent* Keep = nullptr;
	for (UActorComponent* X : Comps)
	{
		// la camara de la plantilla es la que cuelga de la malla de primera persona; las del GASP, del brazo de muelle o de la raiz
		if (UCameraComponent* Cam = Cast<UCameraComponent>(X))
		{
			const USceneComponent* Parent = Cam->GetAttachParent();
			if (!Keep && Parent && Parent->IsA<USkeletalMeshComponent>()) Keep = Cam;
		}
	}
	for (UActorComponent* X : Comps)
	{
		const FString N = X->GetClass()->GetName();
		if (N.Contains(TEXT("PreCMCTick")) || N.Contains(TEXT("TraversalLogic")) || N.Contains(TEXT("SmartObjectAnimation"))
			|| N.Contains(TEXT("FoleyEvents")) || N.Contains(TEXT("VisualOverride")))
		{
			X->SetComponentTickEnabled(false);
			X->Deactivate();
		}
		const bool bCamera = X->IsA<UCameraComponent>() && X != Keep;
		const bool bGameplayCam = N.Contains(TEXT("GameplayCamera"));
		if (bCamera || bGameplayCam || X->IsA<USpringArmComponent>() || X->IsA<UChildActorComponent>())
		{
			X->DestroyComponent();
		}
	}
	// su IMC (y los eventos sueltos de rueda y cruceta que cambian el estilo de camara del GASP)
	HeroGaspImc = LoadObject<UInputMappingContext>(nullptr, HeroImcPath);
	HeroDropImc(PC, HeroGaspImc);
	if (UInputComponent* IC = C->InputComponent)
	{
		IC->KeyBindings.RemoveAll([](const FInputKeyBinding& B)
		{
			const FKey K = B.Chord.Key;
			return K == EKeys::MouseScrollUp || K == EKeys::MouseScrollDown || K == EKeys::Gamepad_DPad_Up || K == EKeys::Gamepad_DPad_Down;
		});
	}
	// SetupCamera del GASP pone de vista su GameplayCamera al poseer: vuelve la del peon
	if (PC) PC->SetViewTarget(C);
	// como el peon de antes: el cuerpo gira con el control (vista estrafe del GASP), no hacia donde anda
	C->bUseControllerRotationYaw = true;
	if (UCharacterMovementComponent* M = C->GetCharacterMovement())
	{
		M->bOrientRotationToMovement = false;
		M->bUseControllerDesiredRotation = false;
	}
	UE_LOG(LogTemp, Log, TEXT("Tarsis: el jugador es %s (GASP): camara %s, IMC del GASP quitado"), *C->GetClass()->GetName(), Keep ? *Keep->GetName() : TEXT("NINGUNA"));
}

bool ATarsisDirector::SetupGaspHero(ACharacter* C, USkeletalMesh* SK)
{
	USkeletalMesh* Uefn = LoadObject<USkeletalMesh>(nullptr, HeroUefnPath);
	UClass* Abp = LoadObject<UClass>(nullptr, HeroAbpPath);
	UClass* Rt = LoadObject<UClass>(nullptr, HeroRetargetPath);
	if (!C || !SK || !Uefn || !Abp || !Rt)
	{
		UE_LOG(LogTemp, Warning, TEXT("Tarsis: faltan assets del GASP para Cuttlas; animaciones de siempre"));
		return false;
	}
	// RTG_UEFN_cuttlas (gasp_guardia.py, parte B7)
	TArray<FAssetData> List;
	IAssetRegistry::GetChecked().GetAssetsByPath(FName(TEXT("/Game/Tarsis/Anim")), List, true);
	for (const FAssetData& A : List)
	{
		if (A.AssetClassPath.GetAssetName() == FName(TEXT("IKRetargeter")) && A.AssetName.ToString().ToLower() == TEXT("rtg_uefn_cuttlas"))
		{
			HeroRetargeter = A.GetAsset();
			break;
		}
	}
	if (!HeroRetargeter)
	{
		UE_LOG(LogTemp, Warning, TEXT("Tarsis: no hay RTG_UEFN_cuttlas en /Game/Tarsis/Anim; animaciones de siempre"));
		return false;
	}
	HeroFacing(Uefn, HeroDriverYaw, HeroDriverBallZ);
	HeroFacing(SK, HeroBodyYawGasp, HeroBodyBallZ);
	// el que conduce: maniqui UEFN oculto con el ABP de Epic (se evalua aunque no se dibuje)
	HeroDriver = NewObject<USkeletalMeshComponent>(C, TEXT("ConductorGASP"));
	HeroDriver->SetSkeletalMesh(Uefn);
	HeroDriver->SetupAttachment(C->GetCapsuleComponent());
	HeroDriver->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	HeroDriver->SetCastShadow(false);
	HeroDriver->SetHiddenInGame(true);
	HeroDriver->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	HeroDriver->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	HeroDriver->SetAnimInstanceClass(Abp);
	HeroDriver->RegisterComponent();
	// la persona, pegada al que conduce (ABP_GenericRetarget toma la pose del padre)
	HeroBody = NewObject<USkeletalMeshComponent>(C, TEXT("CuerpoCuttlas"));
	HeroBody->SetSkeletalMesh(SK);
	HeroBody->SetupAttachment(HeroDriver);
	HeroBody->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	HeroBody->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	HeroBody->SetOwnerNoSee(false);
	HeroBody->ComponentTags.Add(HeroRetargeter->GetFName());   // sin entrada en IKRetargeter_Map: no pisa la variable
	HeroBody->RegisterComponent();
	HeroBody->AddTickPrerequisiteComponent(HeroDriver);   // primero la pose de Epic, luego la copia
	HeroBody->SetAnimationMode(EAnimationMode::AnimationBlueprint);
	HeroBody->SetAnimInstanceClass(Rt);
	bHeroRetargetSet = false;
	HeroBody->SetVisibility(false);
	HeroAnimNow = -1;
	GaspHeroTick(C, false);
	UE_LOG(LogTemp, Log, TEXT("Tarsis: Cuttlas anima con el GASP (retarget %s)"), *HeroRetargeter->GetName());
	return true;
}

void ATarsisDirector::GaspHeroTick(ACharacter* C, bool bOut)
{
	if (!C || !HeroDriver || !HeroBody) return;
	// el IK Retargeter, en la variable del ABP de la persona (una vez creada su instancia)
	if (!bHeroRetargetSet)
	{
		if (UAnimInstance* AI = HeroBody->GetAnimInstance())
		{
			if (FObjectProperty* P = CastField<FObjectProperty>(AI->GetClass()->FindPropertyByName(TEXT("IKRetargeter"))))
			{
				P->SetObjectPropertyValue_InContainer(AI, HeroRetargeter);
				bHeroRetargetSet = true;
			}
		}
	}
	// si algo vuelve a poner el IMC del GASP (otra posesion), se quita otra vez
	HeroDropImc(Cast<APlayerController>(C->GetController()), HeroGaspImc);
	// pies en el suelo: la capsula cambia de altura al agacharse
	const float HalfH = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const float UZ = -HalfH - HeroDriverBallZ + 2.0f;
	HeroDriver->SetRelativeLocationAndRotation(FVector(0.0f, 0.0f, UZ), FRotator(0.0f, HeroDriverYaw, 0.0f));
	HeroBody->SetRelativeLocationAndRotation(FVector(0.0f, 0.0f, (-HalfH - HeroBodyBallZ + 2.0f) - UZ), FRotator(0.0f, HeroBodyYawGasp - HeroDriverYaw + HeroGaspYaw, 0.0f));
	// en primera persona no se ve: el ABP sigue (la historia de poses y la trayectoria no dan saltos al salir a tercera)
	// Gait del GASP segun la velocidad que pone el juego (andar 600, correr x1,5, arrastrar 180); agachado sale de IsCrouching
	const float Max = C->GetCharacterMovement() ? C->GetCharacterMovement()->MaxWalkSpeed : 0.0f;
	const FString Gait = Max >= HeroGaspSprintFrom ? TEXT("Sprint") : (Max >= HeroGaspRunFrom ? TEXT("Run") : TEXT("Walk"));
	if (Gait != HeroGaitNow && HeroSetEnum(C, TEXT("Gait"), Gait)) HeroGaitNow = Gait;
	// parado y girando la camara: el ABP solo gira en el sitio si quiere apuntar (TarsisGaspTurn.h)
	HeroGaspTurn.Tick(C, HeroDriver, C->GetVelocity().Size2D(), C->GetWorld() ? C->GetWorld()->GetDeltaSeconds() : 0.0f,
		HeroGaspTurnFrom, HeroGaspTurnRelease, HeroGaspTurnMaxSeconds);
	HeroAnimNow = C->bIsCrouched ? 2 : (C->GetVelocity().Size2D() > 20.0f ? 1 : 0);
}
