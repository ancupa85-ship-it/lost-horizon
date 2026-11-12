#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Components/InputComponent.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"

ATarsisDirector::ATarsisDirector()
{
	PrimaryActorTick.bCanEverTick = true;
}

void ATarsisDirector::BeginPlay()
{
	Super::BeginPlay();
	SetupPlayer();
}

void ATarsisDirector::SetupPlayer()
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!PC || !C) return;
	// el personaje de la plantilla no se agacha: se le permite y se enlaza la C (y Ctrl izquierdo)
	C->GetCharacterMovement()->GetNavAgentPropertiesRef().bCanCrouch = true;
	C->GetCharacterMovement()->MaxWalkSpeedCrouched = 200.0f;
	EnableInput(PC);
	if (InputComponent)
	{
		InputComponent->BindKey(EKeys::C, IE_Pressed, this, &ATarsisDirector::ToggleCrouch);
		InputComponent->BindKey(EKeys::LeftControl, IE_Pressed, this, &ATarsisDirector::ToggleCrouch);
	}
	bPlayerReady = true;
}

void ATarsisDirector::ToggleCrouch()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C) return;
	if (C->bIsCrouched) C->UnCrouch(); else C->Crouch();
}

void ATarsisDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bPlayerReady) { SetupPlayer(); return; }
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || !GEngine) return;

	// la luz se mide unas 8 veces por segundo y se suaviza
	LightT -= DeltaSeconds;
	if (LightT <= 0.0f)
	{
		LightT = 0.12f;
		const float L = ATarsisGuard::LightAt(this, C->GetActorLocation() + FVector(0.0f, 0.0f, 40.0f));
		PlayerLight = FMath::Lerp(PlayerLight, L, 0.5f);
	}

	// barra de luz: 10 tramos
	const int32 N = FMath::Clamp(FMath::RoundToInt(PlayerLight * 10.0f), 0, 10);
	FString Bar = TEXT("LUZ  [");
	for (int32 i = 0; i < 10; ++i) Bar += (i < N) ? TEXT("#") : TEXT("-");
	Bar += TEXT("]  ");
	Bar += PlayerLight < 0.3f ? TEXT("EN SOMBRA") : (PlayerLight < 0.6f ? TEXT("PENUMBRA") : TEXT("ILUMINADO"));
	if (C->bIsCrouched) Bar += TEXT("   ·   AGACHADO");
	const FColor BarColor = PlayerLight < 0.3f ? FColor(120, 200, 140) : (PlayerLight < 0.6f ? FColor(230, 200, 90) : FColor(255, 140, 70));
	GEngine->AddOnScreenDebugMessage(9101, 0.5f, BarColor, Bar, false, FVector2D(1.4f, 1.4f));

	// estado de los guardias: el peor manda
	ETarsisGuardState Worst = ETarsisGuardState::Patrol;
	float MaxMeter = 0.0f;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		MaxMeter = FMath::Max(MaxMeter, It->Meter);
		if (It->State == ETarsisGuardState::Alert) Worst = ETarsisGuardState::Alert;
		else if (Worst != ETarsisGuardState::Alert && (It->State == ETarsisGuardState::Suspicious || It->State == ETarsisGuardState::Search))
			Worst = It->State;
	}
	FString Msg;
	FColor MsgColor = FColor::White;
	if (Worst == ETarsisGuardState::Alert) { Msg = TEXT("¡TE HAN VISTO! Rompe la línea de vista y escóndete"); MsgColor = FColor(255, 59, 47); }
	else if (Worst == ETarsisGuardState::Search) { Msg = TEXT("TE BUSCAN"); MsgColor = FColor(255, 160, 60); }
	else if (Worst == ETarsisGuardState::Suspicious) { Msg = TEXT("?  Un guardia sospecha"); MsgColor = FColor(255, 210, 58); }
	GEngine->AddOnScreenDebugMessage(9102, 0.5f, MsgColor, Msg.IsEmpty() ? FString(TEXT(" ")) : Msg, false, FVector2D(1.6f, 1.6f));
	bWasAlert = Worst == ETarsisGuardState::Alert;
}
