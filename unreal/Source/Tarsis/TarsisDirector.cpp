#include "TarsisDirector.h"
#include "TarsisGuard.h"
#include "TarsisHUD.h"

#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/PlayerStart.h"
#include "Components/InputComponent.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputCoreTypes.h"
#include "Kismet/GameplayStatics.h"
#include "Components/CapsuleComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Sound/SoundBase.h"
#include "Sound/SoundWave.h"
#include "Sound/SoundAttenuation.h"
#include "Components/AudioComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/Light.h"
#include "Engine/SpotLight.h"
#include "Components/SpotLightComponent.h"
#include "Components/PointLightComponent.h"
#include "HAL/IConsoleManager.h"
#include "Algo/Sort.h"
#include "LevelSequence.h"
#include "LevelSequencePlayer.h"
#include "LevelSequenceActor.h"
#include "Components/MeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "TarsisSave.h"
#include "GameFramework/GameUserSettings.h"
#include "GameFramework/InputSettings.h"
#include "Kismet/KismetSystemLibrary.h"
#include "AudioDevice.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Animation/AnimationAsset.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "InputKeyEventArgs.h"
#include "TimerManager.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/DecalComponent.h"
#include "Materials/MaterialParameterCollection.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Engine/TextureLightProfile.h"

ATarsisDirector::ATarsisDirector()
{
	PrimaryActorTick.bCanEverTick = true;
}

void ATarsisDirector::BeginPlay()
{
	Super::BeginPlay();
	SetupMission();
	SetupBarrier();
	SetupSound();
	SetupTruck();
	SetupBeamLenses();
	SetupPlayer();
	SetWeather(Weather);
	SetupZones();
	ApplyRenderCVars();
}

void ATarsisDirector::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
	// las variables de consola del presupuesto de render, como estaban (en el editor siguen puestas al salir del PIE)
	for (int32 i = RenderSaved.Num() - 1; i >= 0; --i)
	{
		if (IConsoleVariable* CV = IConsoleManager::Get().FindConsoleVariable(*RenderSaved[i].Key)) CV->Set(*RenderSaved[i].Value, ECVF_SetByCode);
	}
	RenderSaved.Reset();
	// y la base seca para el editor
	if (WetMPC) UKismetMaterialLibrary::SetScalarParameterValue(this, WetMPC, TEXT("Mojado"), 0.0f);
	if (WetMPC) UKismetMaterialLibrary::SetScalarParameterValue(this, WetMPC, TEXT("Nublado"), 0.0f);   // y el cielo raso
	Super::EndPlay(EndPlayReason);
}

void ATarsisDirector::ApplyRenderCVars()
{
	RenderApplied.Reset();
	for (const FString& Line : RenderCVars)
	{
		FString Name, Value;
		if (!Line.Split(TEXT("="), &Name, &Value)) continue;
		Name.TrimStartAndEndInline();
		Value.TrimStartAndEndInline();
		IConsoleVariable* CV = IConsoleManager::Get().FindConsoleVariable(*Name);
		if (!CV)
		{
			UE_LOG(LogTemp, Warning, TEXT("Tarsis: presupuesto de render: no existe la variable %s"), *Name);
			continue;
		}
		const FString Before = CV->GetString();
		if (Before == Value) continue;
		RenderSaved.Emplace(Name, Before);
		CV->Set(*Value, ECVF_SetByCode);
		RenderApplied.Add(FString::Printf(TEXT("%s=%s->%s"), *Name, *Before, *CV->GetString()));
	}
	if (RenderApplied.Num() > 0) UE_LOG(LogTemp, Display, TEXT("Tarsis: presupuesto de render: %s"), *FString::Join(RenderApplied, TEXT(", ")));
}

void ATarsisDirector::SetupPlayer()
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!PC || !C) return;
	// el personaje de la plantilla no se agacha: se le permite y se enlaza la C (y Ctrl izquierdo)
	C->GetCharacterMovement()->GetNavAgentPropertiesRef().bCanCrouch = true;
	C->GetCharacterMovement()->MaxWalkSpeedCrouched = 200.0f;
	BaseWalk = C->GetCharacterMovement()->MaxWalkSpeed;
	SetupArms(C);
	// ajuste 26e: tu sombra en tu propia vista. El cuerpo de la plantilla va como «representación en el mundo» de la
	// primera persona, y así el motor no dibuja su sombra para su dueño (medido en el PC: ni con CastHiddenShadow). Con
	// el truco de siempre sí: sin tipo de primera persona, oculto para ti y con sombra aunque esté oculto
	if (bPlayerShadow)
	{
		if (USkeletalMeshComponent* Body = C->GetMesh())
		{
			Body->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::None);
			Body->SetOwnerNoSee(true);
			Body->SetCastShadow(true);
			Body->SetCastHiddenShadow(true);
		}
	}
	PC->ClientSetHUD(ATarsisHUD::StaticClass());
	EnableInput(PC);
	DefaultKeys();
	LoadOptions();
	BindAll();
	bPlayerReady = true;
	bHasSave = UGameplayStatics::DoesSaveGameExist(TEXT("TarsisPartida"), 0);
	// entrada: sobrevuelo de la base; al acabar (o al saltarla) salen las instrucciones
	if (!(bPlayIntro && PlayCine(TEXT("LS_Entrada"), true))) IntroText();
}

void ATarsisDirector::IntroText()
{
	auto K = [this](int32 I) { return ActionKeys[I].GetDisplayName().ToString(); };
	ShowMessage(Tx(TEXT("intro"), TEXT("TARSIS, DE NOCHE\nBusca la sombra. Agachado ({0}) te ven menos y por los huecos de las vallas se pasa agachado.\nEl expediente LH-07 esta en el archivo de la jefatura. La llave la lleva el sargento Ibarra.\n{1} lanza una piedra para distraer. {2} prismaticos: marca a los guardias que mires.\nTus pasos se oyen: corriendo ({3}) y sobre la gravilla mas que dentro. Agachado, nada.\nP: pausa, opciones, controles y cargar el ultimo punto de control."),
		{ K(0), K(2), K(3), K(4) }), 11.0f);
	// Control llama al empezar (no al cargar un punto de control). No para el juego: se coge con la R
	if (bCodecCalls && MissionTime < 5.0f && !CodecTaken.Contains(TEXT("inicio")))
	{
		FTimerHandle H;
		GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateWeakLambda(this, [this]() { if (bCodecCalls && !CodecTaken.Contains(TEXT("inicio"))) CodecRing(TEXT("inicio")); }), 6.0f, false);
	}
}

void ATarsisDirector::ShowMessage(const FString& Text, float Seconds)
{
	if (Text.StartsWith(TEXT("RADIO")))
	{
		Radio = Text;
		RadioT = Seconds;
		return;
	}
	Message = Text;
	MessageT = Seconds;
}

void ATarsisDirector::Captured(APawn* Player)
{
	if (!Player) return;
	if (bRiding) LeaveTruck(true);
	SetTorch(false);
	ExitHide();
	StopDrag();
	bKeypad = false;
	if (bBinoculars) ToggleBinoculars();
	++Captures;
	ACharacter* C = Cast<ACharacter>(Player);
	if (C && C->bIsCrouched) C->UnCrouch();
	AController* Ctl = Player->GetController();
	bChoice = false;
	if (Captures == 1 && !CellSpot.IsZero())
	{
		LockInCell(Player);
		return;
	}
	if (bHasCheck && Difficulty < 2)
	{
		// al último punto de control, no a la entrada: la segunda mitad de la misión no se repite entera
		Player->TeleportTo(CheckLoc, CheckRot);
		if (Ctl) Ctl->SetControlRotation(CheckRot);
		Darts = FMath::Max(Darts, CheckDarts);
		ShowMessage(Tx(TEXT("cogido_punto"), TEXT("TE HAN COGIDO\nVuelves al ultimo punto de control: {0}."), { CheckpointName }), 4.0f);
		return;
	}
	if (AActor* Start = UGameplayStatics::GetActorOfClass(this, APlayerStart::StaticClass()))
	{
		Player->TeleportTo(Start->GetActorLocation(), Start->GetActorRotation());
		if (Ctl) Ctl->SetControlRotation(Start->GetActorRotation());
	}
	ShowMessage(Tx(TEXT("cogido_entrada"), TEXT("TE HAN COGIDO\nVuelves a la entrada de la base.")), 4.0f);
}

void ATarsisDirector::CloseCell()
{
	if (Bars.Num() > 0 || CellDoor.IsZero()) return;
	UStaticMesh* Cyl = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	auto Add = [this](UStaticMesh* Mesh, const FVector& Loc, const FVector& Scale)
	{
		UStaticMeshComponent* B = NewObject<UStaticMeshComponent>(this);
		B->SetStaticMesh(Mesh);
		B->SetMobility(EComponentMobility::Movable);
		B->SetWorldLocation(Loc);
		B->SetWorldScale3D(Scale);
		B->SetCollisionProfileName(TEXT("BlockAll"));
		B->RegisterComponent();
		Bars.Add(B);
	};
	// reja de 2 m: barrotes cada 20 cm y dos travesaños (el hueco de la puerta va a lo largo de X)
	for (int32 i = -4; i <= 4; ++i)
	{
		if (Cyl) Add(Cyl, CellDoor + FVector(i * 20.0f, 0.0f, 110.0f), FVector(0.03f, 0.03f, 2.2f));   // tanda 40: de 5 a 3 cm (de cerca tapaban a Vidal)
	}
	if (Cube)
	{
		Add(Cube, CellDoor + FVector(0.0f, 0.0f, 30.0f), FVector(1.9f, 0.06f, 0.06f));
		Add(Cube, CellDoor + FVector(0.0f, 0.0f, 200.0f), FVector(1.9f, 0.06f, 0.06f));
	}
}

void ATarsisDirector::OpenCell()
{
	for (UStaticMeshComponent* B : Bars)
	{
		if (B) B->DestroyComponent();
	}
	Bars.Empty();
	PlaySfx(TEXT("reja"), CellDoor + FVector(0.0f, 0.0f, 100.0f));
	ShowMessage(Tx(TEXT("celda_abierta"), TEXT("CELDA ABIERTA\nVidal abre, se aparta al rincon y se queda rezando de cara a la pared. No dara la alarma.\nTus cosas las tiene Peris en la sala de guardia.")), 8.0f);
}

ATarsisGuard* ATarsisDirector::TakedownTarget() const
{
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || bRiding) return nullptr;   // desde la caja del camión no se llega a nadie
	ATarsisGuard* Best = nullptr;
	float BestD = TNumericLimits<float>::Max();
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (!It->CanBeTakenDown(P)) continue;
		const float D = FVector::DistSquared(It->GetActorLocation(), P->GetActorLocation());
		if (D < BestD) { BestD = D; Best = *It; }
	}
	return Best;
}

void ATarsisDirector::Takedown()
{
	ATarsisGuard* G = TakedownTarget();
	if (!G) return;
	G->KnockOut();
	++Takedowns;
	HintStep = 3;
	Teach(TEXT("ensena_derribo"), TEXT("{0} DERRIBADO\nDespertara en un rato. Si otro guardia lo ve en el suelo, dara la alarma."), { G->GuardName.ToUpper() }, 4.0f);
}

void ATarsisDirector::ToggleCrouch()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || bRiding || bBoxOn) return;   // en la caja del camión ya vas encogido; y con la de cartón puesta, agachado
	if (C->bIsCrouched) C->UnCrouch(); else C->Crouch();
}

void ATarsisDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (!bPlayerReady) { SetupPlayer(); return; }
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C) return;

	// agachado: la cámara de la plantilla cuelga del brazo en primera persona, que el motor mantiene a la misma altura
	// al encoger la cápsula, así que se baja a mano. La etiqueta de la cámara recuerda si ya está bajada.
	if (UCameraComponent* Cam = C->FindComponentByClass<UCameraComponent>())
	{
		static const FName Tag(TEXT("LH_agachado"));
		const bool bLowered = Cam->ComponentHasTag(Tag);
		if (C->bIsCrouched != bLowered)
		{
			const float Drop = 55.0f;
			Cam->AddWorldOffset(FVector(0.0f, 0.0f, C->bIsCrouched ? -Drop : Drop));
			if (C->bIsCrouched) Cam->ComponentTags.Add(Tag); else Cam->ComponentTags.Remove(Tag);
		}
	}

	// la luz se mide unas 8 veces por segundo y se suaviza
	LightT -= DeltaSeconds;
	if (LightT <= 0.0f)
	{
		LightT = 0.12f;
		const float L = ATarsisGuard::LightAt(this, C->GetActorLocation() + FVector(0.0f, 0.0f, 40.0f));
		PlayerLight = FMath::Lerp(PlayerLight, bTorch ? FMath::Max(L, 0.85f) : L, 0.5f);   // con tu linterna encendida eres tu la luz
	}

	if (MessageT > 0.0f) MessageT -= DeltaSeconds;
	if (RadioT > 0.0f) RadioT -= DeltaSeconds;
	if (CheckT > 0.0f) CheckT -= DeltaSeconds;
	if (SubtitleT > 0.0f) SubtitleT -= DeltaSeconds;
	if (ReportWait > 0.0f) { ReportWait -= DeltaSeconds; if (ReportWait <= 0.0f) { bReport = true; MessageT = 0.0f; } }
	DetectTick();
	HintTick();
	HideTick();
	RideTick();
	RideFeelTick(DeltaSeconds);
	CaptureTick(DeltaSeconds);
	ChangesTick(DeltaSeconds);
	if (FrontMsgT > 0.0f) FrontMsgT -= DeltaSeconds;
	if (KeypadErrT > 0.0f) KeypadErrT -= DeltaSeconds;
	if (StoneT > 0.0f) StoneT -= DeltaSeconds;
	BinocularTick();
	TorchTick(DeltaSeconds);
	if (!bDone && !bCine) MissionTime += DeltaSeconds;
	DragTick();
	if (bKeypad && !NearPlayer(Cell(6, 17), 260.0f)) { bKeypad = false; KeypadInput.Reset(); }
	// salida con el expediente; sin él, un aviso (con enfriamiento para no repetirlo en cada fotograma)
	if (ExitMsgT > 0.0f) ExitMsgT -= DeltaSeconds;
	if (!bDone && NearPlayer(ExitLoc, ExitRadius))
	{
		if (bFile) Finish(false);
		else if (ExitMsgT <= 0.0f)
		{
			ExitMsgT = 6.0f;
			ShowMessage(Tx(TEXT("salida_sin_expediente"), TEXT("NO PUEDES IRTE TODAVIA\nFalta el expediente de la jefatura.")), 3.0f);
		}
	}
	if (DartT > 0.0f) DartT -= DeltaSeconds;
	NoiseTick(C, DeltaSeconds);
	ShadowTick(C, DeltaSeconds);
	BobTick(C, DeltaSeconds);
	ArmsTick(C, DeltaSeconds);
	SoundTick(C, DeltaSeconds);
	RainTick(DeltaSeconds);
	ZonesTick(DeltaSeconds);
	RadioTick(DeltaSeconds);
	PowerTick(DeltaSeconds);
	BarrierTick(DeltaSeconds);
	TruckTick(DeltaSeconds);
	MusicTick(DeltaSeconds);
	CodecTick(DeltaSeconds);
	// el que fue a mirar el farol roto encuentra los cristales y avisa: la base se pone en guardia un rato
	LampsTick();
	if (CheckLamp && CheckLamp.Get() == GateLamp.Get() && !bLampReported && LampChecker && LampChecker->State != ETarsisGuardState::Down
		&& FVector::Dist2D(LampChecker->GetActorLocation(), CheckSpot) < 350.0f)
	{
		bLampReported = true;
		// lo dice por radio (voz y subtítulo); que la base se pone en guardia lo dice el indicador del HUD
		GuardSay(LampChecker, TEXT("farol"), true);
		TensionT = FMath::Max(TensionT, 60.0f);
	}
	// el camino hasta la garita es largo (rodea): a los 25 s de investigar lo deja a medio camino y vuelve a su ronda.
	// Si no ha llegado a verlo, se le vuelve a mandar (sale ya más cerca)
	else if (CheckLamp && !bLampReported && LampChecker
		&& (LampChecker->State == ETarsisGuardState::Return || LampChecker->State == ETarsisGuardState::Patrol))
	{
		LampChecker->HearNoise(CheckSpot);
	}
	if (HeardT > 0.0f) HeardT -= DeltaSeconds;
	// Ramos: la charla se corta si te alejas; con el expediente, si va contigo, se va al portillo
	if (ATarsisGuard* R = FindGuard(TEXT("Ramos")))
	{
		if (bChoice && FVector::Dist2D(R->GetActorLocation(), C->GetActorLocation()) > 300.0f) { bChoice = false; R->Hold(0.1f); MessageT = FMath::Min(MessageT, 1.0f); }
		if (bRamosAlly && bFile && !bRamosSent && R->State != ETarsisGuardState::Down)
		{
			bRamosSent = true;
			R->GoTo(FVector(WicketLoc.X, WicketLoc.Y, R->GetActorLocation().Z));
			ShowMessage(Tx(TEXT("ramos_radio"), TEXT("RAMOS, POR RADIO\n\"Ya lo tiene? Le espero en el portillo de la marisma, en el muro sur, junto al agua.\"")), 6.0f);
		}
	}
	if (CellT > 0.0f)
	{
		CellT -= DeltaSeconds;
		if (CellT <= 0.0f) OpenCell();
	}
	CellTick(DeltaSeconds);
	GearTick(DeltaSeconds);
	BoxTick(DeltaSeconds);
	TalkTick(DeltaSeconds);
	ArmedTick(DeltaSeconds);
	ClimbTick(DeltaSeconds);
}

// ---------------------------------------------------------------- misión 1

FVector ATarsisDirector::Cell(int32 C, int32 R, float Z)
{
	return FVector((C + 0.5f) * 200.0f, (R + 0.5f) * 200.0f, Z);
}

bool ATarsisDirector::NearPlayer(const FVector& P, float Radius) const
{
	const APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	return Pl && FVector::Dist2D(Pl->GetActorLocation(), P) < Radius;
}

UStaticMeshComponent* ATarsisDirector::AddBlock(const FVector& Loc, const FVector& Scale, const FLinearColor& Color, bool bCollide)
{
	UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube"));
	if (!Cube) return nullptr;
	UStaticMeshComponent* B = NewObject<UStaticMeshComponent>(this);
	B->SetStaticMesh(Cube);
	B->SetMobility(EComponentMobility::Movable);
	B->SetWorldLocation(Loc);
	B->SetWorldScale3D(Scale);
	B->SetCanEverAffectNavigation(false);
	// el cubo del motor trae WorldGridMaterial (cuadros, sin parámetro Color): se usa el material de formas básicas
	if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"))) B->SetMaterial(0, Base);
	B->SetCollisionProfileName(bCollide ? TEXT("BlockAll") : TEXT("NoCollision"));
	B->RegisterComponent();
	if (UMaterialInstanceDynamic* M = B->CreateDynamicMaterialInstance(0)) M->SetVectorParameterValue(TEXT("Color"), Color);
	return B;
}

void ATarsisDirector::SetupMission()
{
	// puertas cerradas: L (4,15) en el muro de la fila 15, que va a lo largo de X; V (6,17) en el muro de la columna 6
	const FLinearColor Wood(0.09f, 0.06f, 0.04f);
	DoorL = AddBlock(Cell(4, 15, 110.0f), FVector(2.0f, 0.12f, 2.2f), Wood, true);
	DoorV = AddBlock(Cell(6, 17, 110.0f), FVector(0.12f, 2.0f, 2.2f), FLinearColor(0.12f, 0.13f, 0.14f), true);
	// la nota en la mesa de Alarcón y el expediente en el archivo: se apoyan en lo que haya debajo (mesa o suelo)
	auto Rest = [this](const FVector& P) -> FVector
	{
		FHitResult Hit;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisApoyo), true, this);
		if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
		if (GetWorld()->LineTraceSingleByChannel(Hit, P + FVector(0.0f, 0.0f, 200.0f), P - FVector(0.0f, 0.0f, 50.0f), ECC_Visibility, Q))
		{
			return Hit.ImpactPoint;
		}
		return P;
	};
	// tanda 35: la losa suelta del calabozo, un dedo levantada y algo torcida
	SlabProp = AddBlock(CellSlab + FVector(0.0f, 0.0f, 1.5f), FVector(0.42f, 0.42f, 0.03f), FLinearColor(0.11f, 0.105f, 0.095f), false);
	if (SlabProp) SlabProp->SetRelativeRotation(FRotator(0.0f, 7.0f, 2.0f));
	NoteProp = AddBlock(Rest(Cell(3, 17)) + FVector(0.0f, 0.0f, 1.0f), FVector(0.21f, 0.30f, 0.01f), FLinearColor(0.9f, 0.88f, 0.8f), false);
	// carta en la litera de Ramos (barracón oeste) y botiquín del veterinario en el muro norte del patio este
	LetterProp = AddBlock(Rest(FVector(1130.0f, 2850.0f, 0.0f)) + FVector(0.0f, 0.0f, 1.0f), FVector(0.21f, 0.15f, 0.01f), FLinearColor(0.85f, 0.82f, 0.72f), false);
	AddBlock(FVector(4660.0f, 150.0f, 145.0f), FVector(0.62f, 0.1f, 0.78f), FLinearColor(0.45f, 0.44f, 0.36f), true);
	VetDoor = AddBlock(FVector(4660.0f, 156.5f, 145.0f), FVector(0.6f, 0.03f, 0.76f), FLinearColor(0.75f, 0.78f, 0.7f), true);
	// en el archivo no hay mesa: se pone una (1,2 x 0,6 m, 75 cm de alto) y el expediente encima
	const FVector Floor = Rest(Cell(9, 17));
	AddBlock(Floor + FVector(0.0f, 0.0f, 37.5f), FVector(1.2f, 0.6f, 0.75f), FLinearColor(0.16f, 0.11f, 0.07f), true);
	FileProp = AddBlock(Floor + FVector(0.0f, 0.0f, 77.0f), FVector(0.24f, 0.32f, 0.04f), FLinearColor(0.55f, 0.42f, 0.2f), false);
	// los puntos de la misión (mision1.json) los quitan por su nombre
	Blocks.Add(TEXT("puerta_jefatura"), DoorL);
	Blocks.Add(TEXT("puerta_archivo"), DoorV);
	Blocks.Add(TEXT("puerta_botiquin"), VetDoor);
	Blocks.Add(TEXT("nota"), NoteProp);
	Blocks.Add(TEXT("carta"), LetterProp);
	Blocks.Add(TEXT("expediente"), FileProp);
	SetupHiding();
	DefaultMission();
}

ATarsisGuard* ATarsisDirector::DownedNear(float Radius) const
{
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P) return nullptr;
	ATarsisGuard* Best = nullptr;
	float BestD = Radius;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State != ETarsisGuardState::Down || *It == Dragged) continue;
		const float D = FVector::Dist2D(It->GetActorLocation(), P->GetActorLocation());
		if (D < BestD && FMath::Abs(It->GetActorLocation().Z - P->GetActorLocation().Z) < 150.0f) { BestD = D; Best = *It; }
	}
	return Best;
}

static bool IsIbarra(const ATarsisGuard* G)
{
	return G && G->GuardName.Equals(TEXT("Ibarra"), ESearchCase::IgnoreCase);
}

FString ATarsisDirector::InteractPrompt() const
{
	if (bCapturing) return FString();
	if (bHiding) return Tx(TEXT("p_taquilla_salir"), TEXT("E   SALIR DE LA TAQUILLA"));
	if (bRiding) return bDone ? FString() : Tx(TEXT("p_camion_bajar"), TEXT("E   BAJAR DEL CAMION"));
	if (Dragged) return Tx(TEXT("p_soltar"), TEXT("E   SOLTAR EL CUERPO"));
	if (bChoice) return Tx(TEXT("p_ramos_eleccion"), TEXT("1   VENTE CONMIGO        2   DERRIBARLO"));
	// tanda 37: la escalera manda sobre lo demas (arriba, el centinela queda a un paso)
	if (bClimbing) return FString();
	{ const FString L = LadderPrompt(); if (!L.IsEmpty()) return L; }
	if (ATarsisGuard* T = TakedownTarget())
	{
		return (T->GuardName.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase) && !bRamosTalked) ? Tx(TEXT("p_ramos_agarrar"), TEXT("E   AGARRAR A RAMOS")) : Tx(TEXT("p_derribar"), TEXT("E   DERRIBAR"));
	}
	if (ShoveTarget()) return Tx(TEXT("p_empujar"), TEXT("E   EMPUJAR (queda aturdido 2 s; hace ruido)"));
	if (FacingAlertGuard()) return Tx(TEXT("p_te_ve"), TEXT("TE VE: huye, rodealo o distraelo ({0})"), { ActionKeys[2].GetDisplayName().ToString().ToUpper() });
	if (ATarsisGuard* G = DownedNear(170.0f))
	{
		if (IsIbarra(G) && !bKey) return Tx(TEXT("p_llave_ibarra"), TEXT("E   QUITARLE LA LLAVE"));
		if (G->GuardName.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase) && !bVetKey && !bVetOpen) return Tx(TEXT("p_llave_ramos"), TEXT("E   QUITARLE LA LLAVE DEL BOTIQUIN"));
		if (G->bDarted) return Tx(TEXT("p_dardo"), TEXT("E   RECUPERAR EL DARDO"));
		return Tx(TEXT("p_arrastrar"), TEXT("E   ARRASTRAR (escondelo en la sombra)"));
	}
	{ const FString GP = GearPrompt(); if (!GP.IsEmpty()) return GP; }
	if (CanBoardTruck()) return Tx(TEXT("p_camion_subir"), TEXT("E   SUBIR A LA CAJA DEL CAMION"));
	if (bCellPuzzle && InCell()) return CellPrompt();
	// puertas, notas y objetos de la misión (mision1.json)
	if (const FTarsisPoint* Pt = PointNear())
	{
		const FName K = (Pt->Need.IsNone() || HasFlag(Pt->Need)) ? Pt->Prompt : Pt->PromptLocked;
		return K.IsNone() ? FString() : Tx(K, *K.ToString());
	}
	if (!bVaultOpen && NearPlayer(Cell(6, 17), 190.0f)) return bKeypad ? FString() : Tx(TEXT("p_teclado"), TEXT("E   TECLADO DEL ARCHIVO"));
	if (NearPlayer(WicketLoc, 220.0f)) return Tx(TEXT("p_portillo"), TEXT("E   PORTILLO DE LA MARISMA"));
	if (NearPlayer(GeneratorLoc, 230.0f)) return bPowerOff ? Tx(TEXT("p_generador_parado"), TEXT("GENERADOR: PARADO")) : Tx(TEXT("p_generador"), TEXT("E   CORTAR EL GENERADOR (apaga las luces)"));
	if (HideSpotNear() >= 0) return Tx(TEXT("p_taquilla"), TEXT("E   ESCONDERTE EN LA TAQUILLA"));
	return FString();
}

FString ATarsisDirector::Objective() const
{
	if (bDone) return Tx(TEXT("obj_fin"), TEXT("MISION CUMPLIDA"));
	// el primero de la lista (mision1.json, «objetivos») cuya bandera esté puesta
	for (const FTarsisObjective& O : Objectives)
	{
		if (O.If.IsNone() || HasFlag(O.If)) return Tx(O.Text, *O.Text.ToString());
	}
	return FString();
}

void ATarsisDirector::Interact()
{
	if (bCine) { SkipCine(); return; }
	if (bDone || bCapturing) return;
	if (bHiding) { ExitHide(); return; }
	if (bRiding) { LeaveTruck(false); return; }
	if (Dragged) { StopDrag(); Teach(TEXT("ensena_cuerpo"), TEXT("CUERPO ESCONDIDO\nEn la sombra, los guardias no lo ven si no pasan muy cerca."), {}, 3.0f); return; }
	if (bChoice) { bChoice = false; if (ATarsisGuard* R = FindGuard(TEXT("Ramos"))) R->Hold(0.1f); MessageT = 0.0f; return; }
	if (bClimbing) return;
	if (LadderInteract()) return;
	if (ATarsisGuard* T = TakedownTarget())
	{
		if (T->GuardName.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase) && !bRamosTalked)
		{
			bRamosTalked = true;
			bRamosKnown = true;
			bChoice = true;
			T->Hold(25.0f);
			ShowMessage(Tx(TEXT("ramos_dialogo"), TEXT("RAMOS, EL CUARTELERO\n\"No me haga nada. El jueves bajo con los partes y no pienso volver.\"\n\"Llevo la llave del botiquin del veterinario: dentro hay una pistola de dardos. Si me saca de aqui, es suya.\"\n1   \"Vente conmigo\"          2   Derribarlo")), 25.0f);
			return;
		}
		Takedown();
		return;
	}
	// de frente: si aún no te ha visto en alerta, lo empujas; si ya está en alerta, la E no sirve y se dice por qué
	if (ATarsisGuard* S = ShoveTarget()) { Shove(S); return; }
	if (ATarsisGuard* A = FacingAlertGuard())
	{
		if (FrontMsgT <= 0.0f)
		{
			FrontMsgT = 2.0f;
			PlaySfx(TEXT("empujon"), A->GetActorLocation() + FVector(0.0f, 0.0f, 100.0f), 0.4f);
			Teach(TEXT("ensena_de_frente"), TEXT("DE FRENTE TE VE\n{0} esta en alerta: no se deja. Huye, rodealo o distraelo con una piedra ({1})."), { A->GuardName.ToUpper(), ActionKeys[2].GetDisplayName().ToString().ToUpper() }, 2.5f);
		}
		return;
	}
	if (ATarsisGuard* G = DownedNear(170.0f))
	{
		if (G->GuardName.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase) && !bVetKey && !bVetOpen)
		{
			bVetKey = true;
			bRamosKnown = true;
			PlaySfx(TEXT("llaves"), G->GetActorLocation(), 0.8f);
			ShowMessage(Tx(TEXT("llave_ramos"), TEXT("LLAVE DE RAMOS\n\"Botiquin - veterinario\". Esta en el muro norte del patio este.")), 4.0f);
			return;
		}
		if (IsIbarra(G) && !bKey)
		{
			bKey = true;
			PlaySfx(TEXT("llaves"), G->GetActorLocation(), 0.8f);
			ShowMessage(Tx(TEXT("llave_ibarra"), TEXT("LLAVE DE LA JEFATURA\nSe la quitas a Ibarra del cinturon. Ahora puedes arrastrarlo a la sombra (E).")), 5.0f);
			Checkpoint(Tx(TEXT("cp_llave"), TEXT("LA LLAVE DE IBARRA")));
			return;
		}
		if (G->bDarted)
		{
			G->bDarted = false;
			++Darts;
			PlaySfx(TEXT("recoger"), G->GetActorLocation(), 0.6f);
			Teach(TEXT("ensena_dardo_recuperado"), TEXT("DARDO RECUPERADO\nSe lo sacas del cuello a {0}. Los que llevas, abajo a la derecha."), { G->GuardName }, 3.0f);
			return;
		}
		StartDrag(G);
		return;
	}
	if (GearInteract()) return;
	if (CanBoardTruck()) { BoardTruck(); return; }
	if (CellInteract()) return;
	// puertas, notas y objetos de la misión (mision1.json)
	if (const FTarsisPoint* Pt = PointNear()) { UsePoint(*Pt); return; }
	if (!bVaultOpen && NearPlayer(Cell(6, 17), 190.0f))
	{
		bKeypad = !bKeypad;
		KeypadInput.Reset();
		PlaySfx(TEXT("tecla"), Cell(6, 17, 120.0f), 0.6f);
		return;
	}
	if (NearPlayer(WicketLoc, 220.0f))
	{
		ATarsisGuard* R = FindGuard(TEXT("Ramos"));
		if (!bRamosAlly) { ShowMessage(Tx(TEXT("portillo_cerrado"), TEXT("PORTILLO DE LA MARISMA\nCerrado. La llave la guarda el cuartelero del barracon oeste.")), 3.5f); return; }
		if (!bFile) { ShowMessage(Tx(TEXT("portillo_sin_expediente"), TEXT("PORTILLO DE LA MARISMA\nRamos lo abrira cuando tengas el expediente.")), 3.0f); return; }
		if (!R || R->State == ETarsisGuardState::Down || FVector::Dist2D(R->GetActorLocation(), WicketLoc) > 700.0f) { ShowMessage(Tx(TEXT("portillo_espera"), TEXT("ESPERA A RAMOS\nEl trae la llave del portillo.")), 2.5f); return; }
		PlaySfx(TEXT("reja"), WicketLoc + FVector(0.0f, 0.0f, 100.0f), 0.8f);
		Finish(true);
		return;
	}
	if (!bPowerOff && NearPlayer(GeneratorLoc, 230.0f))
	{
		CutPower();
		return;
	}
	if (const int32 H = HideSpotNear(); H >= 0)
	{
		EnterHide(H);
		return;
	}
}

void ATarsisDirector::KeypadKey(FKey Key)
{
	if (bCellAsk)
	{
		if (Key == EKeys::One || Key == EKeys::NumPadOne) AnswerCell(1);
		else if (Key == EKeys::Two || Key == EKeys::NumPadTwo) AnswerCell(2);
		else if (Key == EKeys::Three || Key == EKeys::NumPadThree) AnswerCell(3);
		else if (Key == EKeys::Four || Key == EKeys::NumPadFour) AnswerCell(4);
		return;
	}
	if (bRadioAsk)
	{
		if (Key == EKeys::One || Key == EKeys::NumPadOne) AnswerRadio(1);
		else if (Key == EKeys::Two || Key == EKeys::NumPadTwo) AnswerRadio(2);
		else if (Key == EKeys::Three || Key == EKeys::NumPadThree) AnswerRadio(3);
		return;
	}
	if (bCodecMenu && !bChoice && !bKeypad)
	{
		if (Key == EKeys::One || Key == EKeys::NumPadOne) CodecCall(1);
		else if (Key == EKeys::Two || Key == EKeys::NumPadTwo) CodecCall(2);
		else if (Key == EKeys::Three || Key == EKeys::NumPadThree) CodecCall(3);
		return;
	}
	if (bChoice)
	{
		if (Key == EKeys::One || Key == EKeys::NumPadOne) Choose(1);
		else if (Key == EKeys::Two || Key == EKeys::NumPadTwo) Choose(2);
		return;
	}
	if (!bKeypad) return;
	if (Key == EKeys::BackSpace) { KeypadDigit(-1); return; }
	const FString N = Key.GetFName().ToString();   // "Zero"... o "NumPadZero"...
	static const TCHAR* Names[] = { TEXT("Zero"), TEXT("One"), TEXT("Two"), TEXT("Three"), TEXT("Four"), TEXT("Five"), TEXT("Six"), TEXT("Seven"), TEXT("Eight"), TEXT("Nine") };
	for (int32 i = 0; i < 10; ++i)
	{
		if (N.EndsWith(Names[i])) { KeypadDigit(i); return; }
	}
}

void ATarsisDirector::KeypadDigit(int32 Digit)
{
	if (!bKeypad || bVaultOpen) return;
	if (Digit < 0) { KeypadInput.LeftChopInline(1); PlaySfx(TEXT("tecla"), Cell(6, 17, 120.0f), 0.4f); return; }
	if (KeypadInput.Len() >= 4) KeypadInput.Reset();
	KeypadInput.AppendInt(FMath::Clamp(Digit, 0, 9));
	PlaySfx(TEXT("tecla"), Cell(6, 17, 120.0f), 0.6f);
	if (KeypadInput.Len() < 4) return;
	if (KeypadInput == VaultCode)
	{
		bVaultOpen = true;
		bKeypad = false;
		if (DoorV) { DoorV->DestroyComponent(); DoorV = nullptr; }
		AddChange(Cell(6, 17, 110.0f), TEXT("puerta"));
		PlaySfx(TEXT("clave_ok"), Cell(6, 17, 120.0f), 0.8f);
		PlaySfx(TEXT("puerta_blindada"), Cell(6, 17, 110.0f));
		ShowMessage(Tx(TEXT("archivo_abierto"), TEXT("ARCHIVO ABIERTO\nLa puerta blindada se abre con un chasquido.")), 4.0f);
	}
	else
	{
		KeypadErrT = 1.2f;
		PlaySfx(TEXT("clave_mal"), Cell(6, 17, 120.0f), 0.8f);
		KeypadInput.Reset();   // el teclado se pone en rojo (KeypadErrT): no hace falta cartel
		// tanda 35: como en la web, a ciegas no se prueba. Cada dos errores el teclado avisa a la central
		++KeypadFails;
		if (KeypadMaxFails > 0 && KeypadFails % KeypadMaxFails == 0)
		{
			++KeypadAlerts;
			bKeypad = false;
			TensionT = FMath::Max(TensionT, 90.0f);
			ShowMessage(Tx(TEXT("clave_alarma"), TEXT("TECLADO DEL ARCHIVO\nDos claves malas seguidas: el teclado se bloquea un momento y avisa a la central.")), 5.0f);
			CentralSay(TEXT("teclado"), Tx(TEXT("radio_teclado"), TEXT("Clave erronea en el archivo, dos veces. Todas las unidades: ojo, y parte uno por uno.")), 1.5f);
		}
	}
}

void ATarsisDirector::StartDrag(ATarsisGuard* G)
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || !G) return;
	Dragged = G;
	UCharacterMovementComponent* M = C->GetCharacterMovement();
	SavedWalk = BaseWalk > 0.0f ? BaseWalk : M->MaxWalkSpeed;
	SavedCrouch = M->MaxWalkSpeedCrouched;
	bSprint = false;
	M->MaxWalkSpeed = 180.0f;
	M->MaxWalkSpeedCrouched = 140.0f;
	Teach(TEXT("ensena_arrastrar"), TEXT("ARRASTRAS A {0}\nLlevalo a la sombra y sueltalo con E. Si un guardia te ve con el, dara la alarma."), { G->GuardName.ToUpper() }, 4.0f);
}

void ATarsisDirector::StopDrag()
{
	if (!Dragged) return;
	Dragged = nullptr;
	if (ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0)))
	{
		UCharacterMovementComponent* M = C->GetCharacterMovement();
		if (SavedWalk > 0.0f) M->MaxWalkSpeed = SavedWalk;
		if (SavedCrouch > 0.0f) M->MaxWalkSpeedCrouched = SavedCrouch;
	}
}

void ATarsisDirector::DragTick()
{
	if (!Dragged) return;
	// se ha despertado (o lo han encontrado y se levanta): se suelta
	if (Dragged->State != ETarsisGuardState::Down) { StopDrag(); return; }
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C) return;
	// el cuerpo va detrás del jugador, a la altura a la que está (choca con muros y cajas, no con personas)
	const FVector Back = C->GetActorForwardVector().GetSafeNormal2D();
	FVector Want = C->GetActorLocation() - Back * 110.0f;
	Want.Z = Dragged->GetActorLocation().Z;
	if (FVector::Dist2D(Want, Dragged->GetActorLocation()) > 400.0f) { StopDrag(); return; }   // se ha quedado enganchado
	Dragged->SetActorLocation(Want, true);
	Dragged->SetActorRotation(FRotator(0.0f, Back.Rotation().Yaw, 0.0f));
}

// ---------------------------------------------------------------- piedras y prismáticos

void ATarsisDirector::ThrowStone()
{
	if (StoneT > 0.0f || bKeypad || bDone || Dragged) return;
	if (BoxBlocks()) return;
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!PC || !Pl) return;
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	// tiro parabólico a unos 11 m/s hacia donde miras, por tramos de 50 ms hasta que choca con algo
	FVector P = Loc + Rot.Vector() * 40.0f;
	FVector Vel = Rot.Vector() * 1100.0f + FVector(0.0f, 0.0f, 250.0f);
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisPiedra), true, this);
	Q.AddIgnoredActor(Pl);
	bool bHit = false;
	for (int32 i = 0; i < 80 && !bHit; ++i)
	{
		const FVector N = P + Vel * 0.05f;
		Vel.Z -= 980.0f * 0.05f;
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, P, N, ECC_Visibility, Q))
		{
			bHit = true;
			P = Hit.ImpactPoint;
			// si da en una pared (o el canto de algo), rebota un poco hacia fuera y cae al suelo: no se queda pegada en el aire
			if (Hit.ImpactNormal.Z < 0.7f)
			{
				const FVector Out = P + Hit.ImpactNormal.GetSafeNormal2D() * 12.0f;
				FHitResult Down;
				P = GetWorld()->LineTraceSingleByChannel(Down, Out, Out - FVector(0.0f, 0.0f, 3000.0f), ECC_Visibility, Q) ? Down.ImpactPoint : Out;
			}
		}
		else P = N;
	}
	StoneT = 1.2f;
	LastStone = P;
	if (HintStep < 2) HintStep = 2;
	if (StoneSnd) UGameplayStatics::PlaySoundAtLocation(this, StoneSnd, P, 1.0f, FMath::FRandRange(0.9f, 1.1f), 0.0f, Atten);
	if (UStaticMeshComponent* S = AddBlock(P + FVector(0.0f, 0.0f, 3.0f), FVector(0.06f, 0.05f, 0.05f), FLinearColor(0.3f, 0.29f, 0.27f), false))
	{
		Stones.Add(S);
		if (Stones.Num() > 6) { if (Stones[0]) Stones[0]->DestroyComponent(); Stones.RemoveAt(0); }
	}
	int32 Heard = 0;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (FVector::Dist(It->GetActorLocation(), P) < NoiseRadius && It->State != ETarsisGuardState::Alert && It->State != ETarsisGuardState::Down && !It->bTowerSentry)
		{
			It->HearNoise(P);
			++Heard;
		}
	}
	if (Heard == 0) Teach(TEXT("ensena_piedra"), TEXT("CLAC\nNadie lo ha oido: la piedra solo atrae a los que estan cerca."), {}, 2.5f);
}

void ATarsisDirector::ToggleBinoculars()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	UCameraComponent* Cam = C ? C->FindComponentByClass<UCameraComponent>() : nullptr;
	if (!Cam) return;
	if (!bBinoculars && (bKeypad || Dragged)) return;
	if (!bBinoculars && bGearTaken) { GearNag(); return; }
	if (!bBinoculars && BoxBlocks()) return;
	bBinoculars = !bBinoculars;
	if (bBinoculars) { SavedFov = Cam->FieldOfView; Cam->SetFieldOfView(18.0f); }
	else Cam->SetFieldOfView(SavedFov > 0.0f ? SavedFov : 90.0f);
}

void ATarsisDirector::BinocularTick()
{
	if (!bBinoculars) return;
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC) return;
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	const FVector Fwd = Rot.Vector();
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisPrismaticos), true, this);
	if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->bMarked) continue;
		const FVector Head = It->GetActorLocation() + FVector(0.0f, 0.0f, 60.0f);
		const FVector D = Head - Loc;
		if (D.Size() > 6000.0f || FVector::DotProduct(Fwd, D.GetSafeNormal()) < FMath::Cos(FMath::DegreesToRadians(7.0f))) continue;
		FCollisionQueryParams Q2 = Q;
		Q2.AddIgnoredActor(*It);
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, Loc, Head, ECC_Visibility, Q2)) continue;
		It->bMarked = true;
		Teach(TEXT("ensena_marcado"), TEXT("{0} MARCADO\nLo veras aunque haya paredes por medio."), { It->GuardName.ToUpper() }, 2.5f);
	}
}

// ---------------------------------------------------------------- Ramos y dardos

ATarsisGuard* ATarsisDirector::FindGuard(const TCHAR* Name) const
{
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->GuardName.Equals(Name, ESearchCase::IgnoreCase)) return *It;
	}
	return nullptr;
}

void ATarsisDirector::Choose(int32 Option)
{
	if (!bChoice) return;
	bChoice = false;
	ATarsisGuard* R = FindGuard(TEXT("Ramos"));
	if (!R) return;
	if (Option == 1)
	{
		bRamosAlly = true;
		bVetKey = true;
		R->bAlly = true;
		R->Hold(1.5f);
		ShowMessage(Tx(TEXT("ramos_contigo"), TEXT("RAMOS ESTA CONTIGO\nTe da la llave del botiquin del veterinario (muro norte del patio este).\nSigue su ronda para que no le echen en falta, y ya no te delatara.")), 7.0f);
	}
	else
	{
		R->Hold(0.0f);
		R->KnockOut();
		++Takedowns;
		bRamosDowned = true;
		ShowMessage(Tx(TEXT("ramos_derribado"), TEXT("RAMOS DERRIBADO\nLleva encima la llave del botiquin.")), 3.5f);
	}
}

FString ATarsisDirector::SideObjective() const
{
	if (bGearTaken) return Tx(TEXT("sec_equipo"), TEXT("Sin equipo: tus cosas estan en el cajon de Peris, en la sala de guardia"));
	if (bDone || !bRamosKnown) return FString();
	if (bRamosAlly && bFile) return Tx(TEXT("sec_portillo"), TEXT("Otra salida: Ramos te espera en el portillo de la marisma (muro oeste, patio suroeste)"));
	if (bVetOpen) return bRamosAlly ? Tx(TEXT("sec_ramos_contigo"), TEXT("Ramos esta contigo: con el expediente, saldra por la marisma")) : FString();
	if (bVetKey) return Tx(TEXT("sec_botiquin"), TEXT("Abre el botiquin del veterinario: muro norte del patio este"));
	return Tx(TEXT("sec_ramos"), TEXT("Ramos, el cuartelero del barracon oeste, lleva la llave del botiquin: agarralo por la espalda"));
}

void ATarsisDirector::ShootDart()
{
	if (bGearTaken && Darts <= 0 && !bKeypad && !bMenu && !bCodec && !bCellAsk) { GearNag(); return; }
	if (Darts <= 0 || DartT > 0.0f || bKeypad || bChoice || bDone || Dragged || bRiding) return;
	if (!bMenu && !bCodec && !bCellAsk && BoxBlocks()) return;
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!PC || !Pl) return;
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	const FVector Fwd = Rot.Vector();
	--Darts;
	DartT = 0.8f;
	if (DartSnd) UGameplayStatics::PlaySound2D(this, DartSnd, 0.7f);
	// retroceso: la pistola salta hacia arriba y atrás, y la vista sube un poco
	RecoilT = 1.0f;
	PC->SetControlRotation(PC->GetControlRotation() + FRotator(0.7f, 0.0f, 0.0f));
	// el guardia más cercano cuyo cuerpo cruza la línea de tiro (a menos de 35 m), sin nada en medio
	ATarsisGuard* Best = nullptr;
	float BestT = 3500.0f;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisDardo), true, this);
	Q.AddIgnoredActor(Pl);
	const float Heights[] = { -50.0f, 0.0f, 50.0f };
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Down) continue;
		const FVector Base = It->GetActorLocation();
		for (const float Hz : Heights)
		{
			const FVector P = Base + FVector(0.0f, 0.0f, Hz);
			const float T = FVector::DotProduct(P - Loc, Fwd);
			if (T < 0.0f || T > BestT) continue;
			if (FVector::Dist(Loc + Fwd * T, P) > 32.0f) continue;
			FCollisionQueryParams Q2 = Q;
			Q2.AddIgnoredActor(*It);
			FHitResult Hit;
			if (GetWorld()->LineTraceSingleByChannel(Hit, Loc, P, ECC_Visibility, Q2)) continue;
			Best = *It;
			BestT = T;
			break;
		}
	}
	if (ShootLamp(Loc, Fwd, Best ? BestT : 3500.0f)) return;
	if (!Best) return;   // fallado: el contador de dardos del HUD ya lo dice
	Best->KnockOut();
	Best->bDarted = true;
	++Takedowns;
	Teach(TEXT("ensena_dormido"), TEXT("{0} DORMIDO\nEl dardo se recupera: acercate al cuerpo y pulsa E."), { Best->GuardName.ToUpper() }, 3.0f);
}

void ATarsisDirector::Finish(bool bByMarsh)
{
	if (bDone) return;
	bDone = true;
	bMarsh = bByMarsh;
	bLeftByTruck = bRiding && !bByMarsh;   // sales en la caja del camión: sigue contigo dentro hasta el final del terraplén
	StopDrag();
	if (bBinoculars) ToggleBinoculars();
	FString GateLine;
	if (!bByMarsh)
	{
		// en el control, el de la garita levanta la barrera y mira hacia otro lado (sale en el plano de LS_Salida)
		if (BarrierTarget < 1.0f) PlaySfx(TEXT("barrera"), ExitBarrierLoc + FVector(0.0f, 0.0f, 100.0f));
		BarrierTarget = 1.0f;
		if (GateLamp && GateLamp->GetLightComponent())
		{
			// que el plano final se vea aunque cortaras la luz; si rompiste el farol, solo la bombilla de dentro de la garita
			if (bLampBroken) GateLamp->GetLightComponent()->SetIntensity(70.0f);   // 700 de sigilo (luz fuerte: se pinta la décima parte)
			GateLamp->GetLightComponent()->SetVisibility(true);
		}
		ATarsisGuard* Best = nullptr;
		float BestD = TNumericLimits<float>::Max();
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (It->State == ETarsisGuardState::Down || It->bTowerSentry || It->bAlly) continue;
			const float D = FVector::Dist(It->GetActorLocation(), ExitBarrierLoc);
			if (D < BestD) { BestD = D; Best = *It; }
		}
		if (Best)
		{
			const FRotator R(0.0f, ExitBarrierYaw, 0.0f);
			const FVector Spot = ExitBarrierLoc + R.RotateVector(FVector(-60.0f, -110.0f, 0.0f));
			Best->SetActorLocationAndRotation(FVector(Spot.X, Spot.Y, Best->GetActorLocation().Z), FRotator(0.0f, ExitBarrierYaw + 150.0f, 0.0f), false, nullptr, ETeleportType::TeleportPhysics);
			Best->SetFlashlight(false);
			Best->Hold(3600.0f);
			GateLine = TEXT("\n") + Tx(TEXT("final_garita"), TEXT("En la garita, {0} levanta la barrera y mira hacia la marisma."), { Best->GuardName });
		}
	}
	PlayCine(bByMarsh ? TEXT("LS_Marisma") : TEXT("LS_Salida"), false);
	const int32 Secs = FMath::FloorToInt(MissionTime);
	// puntuación de sigilo: te ven, te cogen y derribas, menos; tardar mucho, algo menos. En fácil cuenta menos y en difícil más
	static const float DiffMul[] = { 0.8f, 1.0f, 1.2f };
	static const TCHAR* Df[] = { TEXT("FACIL"), TEXT("NORMAL"), TEXT("DIFICIL") };
	const float Raw = 1000.0f - 120.0f * Detections - 200.0f * Captures - 30.0f * Takedowns - FMath::Max(0.0f, MissionTime - 600.0f) * 0.5f;
	Score = FMath::Clamp(FMath::RoundToInt(Raw * DiffMul[FMath::Clamp(Difficulty, 0, 2)]), 0, 1200);
	Rank = (Detections == 0 && Captures == 0 && Takedowns == 0) ? TEXT("FANTASMA")
		: (Detections == 0 && Captures == 0) ? TEXT("SOMBRA")
		: Score >= 600 ? TEXT("INFILTRADO") : TEXT("RUIDOSO");
	const FString Stats = Tx(TEXT("final_datos"), TEXT("Tiempo {0}:{1}   Te vieron {2}   Capturas {3}   Derribos {4}\nSIGILO: {5} puntos - {6} ({7})"),
		{ Secs / 60, FString::Printf(TEXT("%02d"), Secs % 60), Detections, Captures, Takedowns, Score, Rank, FString(Df[FMath::Clamp(Difficulty, 0, 2)]) });
	if (bByMarsh)
	{
		ShowMessage(Tx(TEXT("final_marisma"), TEXT("EL QUE NO ENTREGO\nRamos abre el portillo y rema sin encender la linterna. El expediente sigue en tu chaqueta.\nControl pierde tu rastro en la marisma.")) + TEXT("\n") + Stats, 20.0f);
	}
	else
	{
		FString T = (bLeftByTruck ? Tx(TEXT("final_salida_camion"), TEXT("MISION CUMPLIDA\nSales de Tarsis bajo la lona del camion de suministros, con el expediente LH-07 en la chaqueta."))
			: Tx(TEXT("final_salida"), TEXT("MISION CUMPLIDA\nSales de Tarsis con el expediente LH-07."))) + GateLine + TEXT("\n") + Stats;
		if (bRamosAlly) T += TEXT("\n") + Tx(TEXT("final_ramos"), TEXT("Ramos sale solo por la marisma y os espera en el camino de Trebujena."));
		ShowMessage(T, 15.0f);
	}
	BuildReport();
	ReportWait = bByMarsh ? 20.0f : 15.0f;
}

// ---------------------------------------------------------------- pasos, carrera y balanceo

void ATarsisDirector::SprintOn()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || Dragged || bDone || bRiding || bBoxOn) return;
	if (BaseWalk <= 0.0f) BaseWalk = C->GetCharacterMovement()->MaxWalkSpeed;
	bSprint = true;
	C->GetCharacterMovement()->MaxWalkSpeed = BaseWalk * 1.5f;
}

void ATarsisDirector::SprintOff()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || !bSprint) return;
	bSprint = false;
	if (!Dragged && BaseWalk > 0.0f) C->GetCharacterMovement()->MaxWalkSpeed = BaseWalk;
}

void ATarsisDirector::NoiseTick(ACharacter* C, float DeltaSeconds)
{
	const float Speed = C->GetVelocity().Size2D();
	const bool bAir = C->GetCharacterMovement()->IsFalling();
	// suelo: dentro (cemento, base_suelo_int) suena menos que fuera (gravilla y tierra)
	StepT -= DeltaSeconds;
	if (StepT <= 0.0f)
	{
		StepT = 0.35f;
		FHitResult Hit;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisSuelo), true, this);
		Q.AddIgnoredActor(C);
		const FVector P = C->GetActorLocation();
		bIndoor = IndoorAt(P, C);
		PlayerSurface = SurfaceIndex(P, C);
		// según lo que pisas: la chapa y la madera se oyen de lejos, el cemento menos que la grava, la hierba casi nada;
		// con lluvia, el agua tapa los pasos de fuera
		static const float SurfNoise[] = { 1.0f, 0.6f, 1.3f, 1.1f, 0.55f };
		const float Surf = SurfNoise[FMath::Clamp(PlayerSurface, 0, 4)] * (Weather == 1 && !bIndoor ? 0.6f : 1.0f);
		static const float DiffHear[] = { 0.75f, 1.0f, 1.25f };
		PlayerNoise = (C->bIsCrouched || bAir || Speed < 60.0f) ? 0.0f : Speed * 1.15f * Surf * DiffHear[FMath::Clamp(Difficulty, 0, 2)];
		if (PlayerNoise > 0.0f)
		{
			for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
			{
				if (FVector::Dist(It->GetActorLocation(), P) > PlayerNoise) continue;
				if (It->Visibility(C) > 0.0f) continue;   // si ya te ve, manda la vista
				if (It->State == ETarsisGuardState::Patrol || It->State == ETarsisGuardState::Return) { HeardT = 2.5f; HeardFrom = It->GetActorLocation(); }
				It->HearNoise(P);
			}
		}
	}
	if (C->bIsCrouched || Speed < 60.0f) PlayerNoise = 0.0f;   // al pararte o agacharte, el HUD lo ve enseguida
}

// ---------------------------------------------------------------- empezar sin armas: consejos y empujón de frente

// ---------------------------------------------------------------- tu sombra te delata (tanda 26)
// Bajo una luz que dibuja sombras, la tuya se alarga por el suelo o sube por la pared. Un guardia que no te ve a ti
// (estás tras una esquina, o a su espalda no: tiene que caerle en el cono) pero sí ve esa sombra se mosquea: «?» malva,
// va a mirar la punta y se vuelve hacia donde venía. Nunca da la alarma por sí sola. Agachado es más corta; quieto,
// llama mucho menos.
int32 ATarsisDirector::MeasureShadows()
{
	ShadowTips.Reset();
	ShadowContrasts.Reset();
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || bDone || bCine || bCapturing || bHiding || bRiding || C->IsHidden() || BoxCloaked()) return 0;
	TArray<float> Heights;
	if (C->bIsCrouched) Heights = { 110.0f, 70.0f, 35.0f };
	else Heights = { 170.0f, 110.0f, 45.0f };
	TArray<FVector> Tips;
	TArray<float> Con;
	ATarsisGuard::ShadowsOf(this, C, Heights, ShadowMinLight, Tips, Con);
	for (int32 i = 0; i < Tips.Num(); ++i)
	{
		if (Con[i] >= ShadowMinContrast) { ShadowTips.Add(Tips[i]); ShadowContrasts.Add(Con[i]); }
	}
	return ShadowTips.Num();
}

void ATarsisDirector::ShadowTick(ACharacter* C, float DeltaSeconds)
{
	if (!bShadowTells)
	{
		if (ShadowTips.Num() > 0) { ShadowTips.Reset(); ShadowContrasts.Reset(); }
		return;
	}
	ShadowT -= DeltaSeconds;
	if (ShadowT > 0.0f) return;
	const float Step = 0.2f;   // cinco veces por segundo sobra: una sombra no es un disparo
	ShadowT = Step;
	if (MeasureShadows() == 0) return;
	const bool bStill = C->GetVelocity().Size2D() < 20.0f;
	const FVector From = C->GetActorLocation();
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		if (G->bTowerSentry || G->bAlly || G->State == ETarsisGuardState::Down || G->State == ETarsisGuardState::Alert || G->IsStunned()) continue;
		if (G->Visibility(C) > 0.0f) continue;   // te ve a ti: eso ya lo lleva su vista
		const FVector Eye = G->GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
		const float CosView = FMath::Cos(FMath::DegreesToRadians(G->ViewHalfAngle));
		float Best = 0.0f;
		FVector BestTip = FVector::ZeroVector;
		for (int32 i = 0; i < ShadowTips.Num(); ++i)
		{
			const FVector To = ShadowTips[i] - Eye;
			const float D = To.Size();
			if (D >= ShadowRange) continue;
			if (FVector::DotProduct(G->GetActorForwardVector(), To.GetSafeNormal2D()) < CosView) continue;
			const float A = ShadowRate * ShadowContrasts[i] * (1.0f - D / ShadowRange);
			if (A <= Best) continue;
			FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisSombraVista), true, G);
			Q.AddIgnoredActor(C);
			FHitResult Hit;
			if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, ShadowTips[i], ECC_Visibility, Q) && FVector::Dist(Hit.ImpactPoint, ShadowTips[i]) > 40.0f) continue;
			Best = A;
			BestTip = ShadowTips[i];
		}
		if (Best <= 0.0f) continue;
		if (bStill) Best *= ShadowStillFactor;
		const bool bWas = G->IsShadowCurious();
		if (G->NoticeShadow(BestTip, From, Best * Step, ShadowCap) && !bWas)
		{
			++ShadowNoticed;
			ShadowWatcher = G->GuardName;
			Teach(TEXT("ensena_sombra"), TEXT("TU SOMBRA TE DELATA\nBajo una luz, tu sombra llega antes que tu. Agachate, quedate quieto o rodea la luz."), {}, 4.5f);
		}
	}
}

void ATarsisDirector::HintTick()
{
	// consejos del principio, uno tras otro hasta que los usas (o pasados 3 min): agacharse, la piedra y la E
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (HintStep == 0 && C && C->bIsCrouched) HintStep = 1;
	if (HintStep >= 3 || MissionTime > 180.0f || bDone) { Hint.Reset(); return; }
	auto K = [this](int32 I) { return ActionKeys[I].GetDisplayName().ToString().ToUpper(); };
	if (HintStep == 0) Hint = FString::Printf(TEXT("CONSEJO: agachate (%s) y busca la sombra: asi te ven mucho menos."), *K(0));
	else if (HintStep == 1) Hint = FString::Printf(TEXT("CONSEJO: %s lanza una piedra: el guardia se para, se gira y va a mirar. Pasa por detras."), *K(2));
	else Hint = FString::Printf(TEXT("CONSEJO: por la espalda, %s derriba. De frente, si aun no te ha visto, %s le empuja y queda aturdido 2 s."), *K(1), *K(1));
}

ATarsisGuard* ATarsisDirector::ShoveTarget() const
{
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || bHiding || bRiding) return nullptr;
	ATarsisGuard* Best = nullptr;
	float BestD = 170.0f;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		if (G->bTowerSentry || G->bAlly || G->State == ETarsisGuardState::Down || G->State == ETarsisGuardState::Alert || G->IsStunned()) continue;
		if (G->CanBeTakenDown(P)) continue;   // por la espalda: eso es derribar
		const FVector D = G->GetActorLocation() - P->GetActorLocation();
		if (FMath::Abs(D.Z) > 120.0f) continue;
		if (D.Size2D() < BestD) { BestD = D.Size2D(); Best = G; }
	}
	return Best;
}

ATarsisGuard* ATarsisDirector::FacingAlertGuard() const
{
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P) return nullptr;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State != ETarsisGuardState::Alert || It->bTowerSentry || It->bAlly) continue;
		if (FVector::Dist2D(It->GetActorLocation(), P->GetActorLocation()) < 260.0f) return *It;
	}
	return nullptr;
}

void ATarsisDirector::Shove(ATarsisGuard* G)
{
	if (!G) return;
	// de frente y sin que esté en alerta: lo empujas y queda aturdido 2,5 s (no ve). Da tiempo a rodearlo y derribarlo
	// o a irte, pero hace ruido: los que estén cerca vienen a mirar. Si no lo derribas, al rehacerse va a por ti
	G->Stun(2.5f);
	++Shoves;
	HintStep = 3;
	PlaySfx(TEXT("empujon"), G->GetActorLocation() + FVector(0.0f, 0.0f, 100.0f));
	GuardSay(G, TEXT("eh"));
	int32 Heard = 0;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (*It == G || It->bTowerSentry || It->State == ETarsisGuardState::Down || It->State == ETarsisGuardState::Alert) continue;
		if (FVector::Dist(It->GetActorLocation(), G->GetActorLocation()) > NoiseRadius) continue;
		It->HearNoise(G->GetActorLocation());
		++Heard;
	}
	Teach(TEXT("ensena_empujon"), TEXT("EMPUJAS A {0}\nAturdido 2 s: rodealo y derribalo (E) o vete. El golpe se oye: los que esten cerca vienen."), { G->GuardName.ToUpper() }, 3.5f);
}

// ---------------------------------------------------------------- escondites: taquillas del barracón y de la sala de guardia

void ATarsisDirector::SetupHiding()
{
	for (int32 i = 0; i < HideSpots.Num(); ++i)
	{
		FVector P = HideSpots[i];
		const float Yaw = HideYaws.IsValidIndex(i) ? HideYaws[i] : 0.0f;
		FHitResult Hit;
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisTaquilla), true, this);
		if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
		if (GetWorld()->LineTraceSingleByChannel(Hit, P + FVector(0.0f, 0.0f, 250.0f), P - FVector(0.0f, 0.0f, 100.0f), ECC_Visibility, Q)) P.Z = Hit.ImpactPoint.Z;
		HideSpots[i] = P;
		// taquilla metálica de 60 x 50 x 190 cm con la puerta (más clara) hacia donde abre
		const FRotator R(0.0f, Yaw - 90.0f, 0.0f);
		const FVector Dir = FRotator(0.0f, Yaw, 0.0f).Vector();
		// malla de verdad (chapa pintada y gastada, cantos biselados, rendijas abiertas); la puerta mira hacia Dir (+Y de la malla)
		if (UStaticMesh* LM = LockerMesh.LoadSynchronous())
		{
			UStaticMeshComponent* L = NewObject<UStaticMeshComponent>(this);
			L->SetStaticMesh(LM);
			L->SetMobility(EComponentMobility::Movable);
			L->SetWorldLocationAndRotation(P, FRotator(0.0f, Yaw - 90.0f, 0.0f));
			L->SetCanEverAffectNavigation(false);
			L->SetCollisionProfileName(TEXT("BlockAll"));
			L->RegisterComponent();
			Lockers.Add(L);
			continue;
		}
		if (UStaticMeshComponent* L = AddBlock(P + FVector(0.0f, 0.0f, 95.0f), FVector(0.6f, 0.5f, 1.9f), FLinearColor(0.09f, 0.11f, 0.08f), true))
		{
			L->SetWorldRotation(R);
			Lockers.Add(L);
		}
		if (UStaticMeshComponent* Door = AddBlock(P + Dir * 26.0f + FVector(0.0f, 0.0f, 95.0f), FVector(0.56f, 0.02f, 1.84f), FLinearColor(0.14f, 0.16f, 0.12f), false))
		{
			Door->SetWorldRotation(R);
			Lockers.Add(Door);
		}
		// rendijas de ventilación en la puerta, a la altura de los ojos
		for (int32 s = 0; s < 4; ++s)
		{
			if (UStaticMeshComponent* Slit = AddBlock(P + Dir * 27.5f + FVector(0.0f, 0.0f, 150.0f + s * 6.0f), FVector(0.36f, 0.01f, 0.015f), FLinearColor(0.01f, 0.01f, 0.01f), false))
			{
				Slit->SetWorldRotation(R);
				Lockers.Add(Slit);
			}
		}
	}
}

int32 ATarsisDirector::HideSpotNear() const
{
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || bHiding) return -1;
	for (int32 i = 0; i < HideSpots.Num(); ++i)
	{
		const FVector Front = HideSpots[i] + FRotator(0.0f, HideYaws.IsValidIndex(i) ? HideYaws[i] : 0.0f, 0.0f).Vector() * 75.0f;
		if (FVector::Dist2D(P->GetActorLocation(), Front) < 120.0f && FMath::Abs(P->GetActorLocation().Z - HideSpots[i].Z) < 200.0f) return i;
	}
	return -1;
}

void ATarsisDirector::EnterHide(int32 Index)
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!C || !PC || !HideSpots.IsValidIndex(Index)) return;
	StopDrag();
	if (bBinoculars) ToggleBinoculars();
	bKeypad = false;
	// ¿te ha visto meterte? Un guardia en alerta que te tiene a la vista o te acaba de perder te saca de un tirón
	bHideSeen = false;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Alert && !It->bTowerSentry && It->UnseenT < 1.5f) bHideSeen = true;
	}
	HideIdx = Index;
	bHiding = true;
	const float Yaw = HideYaws.IsValidIndex(Index) ? HideYaws[Index] : 0.0f;
	const FVector Dir = FRotator(0.0f, Yaw, 0.0f).Vector();
	if (C->bIsCrouched) C->UnCrouch();
	C->SetActorEnableCollision(false);
	C->GetCharacterMovement()->StopMovementImmediately();
	C->GetCharacterMovement()->DisableMovement();
	C->SetActorLocation(HideSpots[Index] - Dir * 5.0f + FVector(0.0f, 0.0f, C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), false, nullptr, ETeleportType::TeleportPhysics);
	C->SetActorHiddenInGame(true);   // los guardias no ven a un actor oculto (ATarsisGuard::Visibility)
	PC->SetControlRotation(FRotator(0.0f, Yaw, 0.0f));
	if (FAudioDeviceHandle Dev = GEngine->GetMainAudioDevice()) Dev->SetTransientPrimaryVolume(OptVolume * 0.45f);   // se oye amortiguado
	PlaySfx(TEXT("taquilla"), HideSpots[Index] + FVector(0.0f, 0.0f, 100.0f), 0.8f);
	Teach(TEXT("ensena_taquilla"), TEXT("EN LA TAQUILLA\nNo te ven ni te oyen, salvo que te hayan visto meterte. E para salir."), {}, 3.5f);
}

void ATarsisDirector::ExitHide()
{
	if (!bHiding) return;
	bHiding = false;
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (FAudioDeviceHandle Dev = GEngine->GetMainAudioDevice()) Dev->SetTransientPrimaryVolume(OptVolume);
	if (!C || !HideSpots.IsValidIndex(HideIdx)) return;
	const FVector Dir = FRotator(0.0f, HideYaws.IsValidIndex(HideIdx) ? HideYaws[HideIdx] : 0.0f, 0.0f).Vector();
	C->SetActorLocation(HideSpots[HideIdx] + Dir * 85.0f + FVector(0.0f, 0.0f, C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight() + 2.0f), false, nullptr, ETeleportType::TeleportPhysics);
	C->SetActorHiddenInGame(false);
	C->SetActorEnableCollision(true);
	C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	PlaySfx(TEXT("taquilla"), HideSpots[HideIdx] + FVector(0.0f, 0.0f, 100.0f), 0.8f);
}

void ATarsisDirector::HideTick()
{
	if (!bHiding || !bHideSeen) return;
	// te vio meterte: el que te persigue abre la taquilla al llegar
	bool bAny = false;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State != ETarsisGuardState::Alert || It->bTowerSentry) continue;
		bAny = true;
		if (FVector::Dist2D(It->GetActorLocation(), HideSpots[HideIdx]) < 190.0f)
		{
			// la abre de un tirón: la misma escena que cualquier captura (BeginCapture), con su aviso al final
			BeginCapture(*It);
			bCaptureLocker = true;
			return;
		}
	}
	if (!bAny) bHideSeen = false;   // ya no te persigue nadie: estás a salvo ahí dentro
}

// ---------------------------------------------------------------- los guardias notan cambios (puertas que estaban cerradas)

void ATarsisDirector::AddChange(const FVector& Where, const TCHAR* Key)
{
	ChangeLocs.Add(Where);
	ChangeKeys.Add(Key);
	ChangeSeen.Add(false);
}

void ATarsisDirector::ChangesTick(float DeltaSeconds)
{
	ChangeT -= DeltaSeconds;
	if (ChangeT > 0.0f || ChangeLocs.Num() == 0) return;
	ChangeT = 0.25f;
	for (int32 i = 0; i < ChangeLocs.Num(); ++i)
	{
		if (ChangeSeen[i]) continue;
		const FVector P = ChangeLocs[i];
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			ATarsisGuard* G = *It;
			if (G->State == ETarsisGuardState::Down || G->State == ETarsisGuardState::Alert || G->bAlly || G->bTowerSentry
				|| G->IsInvestigating() || G->IsCheckingBody() || G->IsStunned()) continue;
			const FVector Eye = G->GetActorLocation() + FVector(0.0f, 0.0f, 70.0f);
			const float D = FVector::Dist(Eye, P);
			if (D > 1200.0f) continue;
			if (FVector::DotProduct(G->GetActorForwardVector(), (P - Eye).GetSafeNormal2D()) < 0.5f) continue;   // ±60 grados
			if (D > 600.0f && ATarsisGuard::LightAt(this, P) < 0.2f) continue;   // a oscuras solo lo nota de cerca
			FHitResult Hit;
			FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisCambio), true, this);
			Q.AddIgnoredActor(G);
			if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
			if (GetWorld()->LineTraceSingleByChannel(Hit, Eye, P, ECC_Visibility, Q) && FVector::Dist(Hit.ImpactPoint, P) > 60.0f) continue;
			ChangeSeen[i] = true;
			++ChangesNoticed;
			GuardSay(G, ChangeKeys[i]);   // antes que HearNoise: así no dice además «¿qué ha sido eso?»
			G->HearNoise(P);   // lo dice él («esta puerta estaba cerrada»), con subtítulo
			break;
		}
	}
}

void ATarsisDirector::SimulateKey(FName Key, bool bPress, bool bRelease)
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC) return;
	const FKey K(Key);
	if (bPress) PC->InputKey(FInputKeyEventArgs::CreateSimulated(K, IE_Pressed, 1.0f));
	if (bRelease) PC->InputKey(FInputKeyEventArgs::CreateSimulated(K, IE_Released, 0.0f));
}

// ---------------------------------------------------------------- tus brazos con la pistola de dardos

void ATarsisDirector::SetupArms(ACharacter* C)
{
	if (Arms || !C) return;
	// la cámara de la plantilla cuelga de la cabeza del cuerpo en primera persona, que sin arma lleva los brazos
	// caídos (fuera de la vista). Para la pistola se pone otro maniquí pegado a la cámara, con la cabeza en ella,
	// solo para ti y con el campo de visión de primera persona (no se mete en las paredes)
	UCameraComponent* Cam = C->FindComponentByClass<UCameraComponent>();
	USkeletalMesh* SK = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple"));
	if (!Cam || !SK) return;
	Arms = NewObject<USkeletalMeshComponent>(C, TEXT("BrazosTarsis"));
	Arms->SetSkeletalMeshAsset(SK);
	Arms->SetupAttachment(Cam);
	Arms->SetOnlyOwnerSee(true);
	Arms->SetCastShadow(false);
	Arms->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Arms->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
	Arms->VisibilityBasedAnimTickOption = EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
	Arms->SetRelativeRotation(FRotator(0.0f, -90.0f, 0.0f));   // el maniquí mira hacia +Y
	Arms->RegisterComponent();
	// sin cabeza ni piernas: solo se ven los brazos (y algo del pecho si miras abajo)
	for (const TCHAR* B : { TEXT("neck_01"), TEXT("thigh_l"), TEXT("thigh_r") }) Arms->HideBoneByName(FName(B), PBO_None);
	if (UAnimationAsset* A = LoadObject<UAnimationAsset>(nullptr, *ArmsAnimPath))
	{
		Arms->SetAnimationMode(EAnimationMode::AnimationSingleNode);
		Arms->PlayAnimation(A, true);
	}
	if (UStaticMesh* PM = LoadObject<UStaticMesh>(nullptr, *PistolMeshPath))
	{
		Pistol = NewObject<UStaticMeshComponent>(C, TEXT("PistolaDardos"));
		Pistol->SetStaticMesh(PM);
		Pistol->SetupAttachment(Arms, TEXT("HandGrip_R"));
		Pistol->SetRelativeTransform(PistolGrip);
		Pistol->SetOnlyOwnerSee(true);
		Pistol->SetCastShadow(false);
		Pistol->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		Pistol->SetFirstPersonPrimitiveType(EFirstPersonPrimitiveType::FirstPerson);
		Pistol->RegisterComponent();
	}
	Arms->SetVisibility(false, true);
}

void ATarsisDirector::ArmsTick(ACharacter* C, float DeltaSeconds)
{
	if (!Arms) return;
	// con dardos y las manos libres, la pistola sube a la vista; si no, baja y se oculta
	const bool bWant = Darts > 0 && !bCine && !bDone && !bBinoculars && !bKeypad && !Dragged && !bMenu && !bReport && !bChoice && !bHiding && !bRiding;
	ArmsShow = FMath::FInterpConstantTo(ArmsShow, bWant ? 1.0f : 0.0f, DeltaSeconds, 3.5f);
	const bool bVis = ArmsShow > 0.01f;
	if (Arms->IsVisible() != bVis) Arms->SetVisibility(bVis, true);
	bArmsVisible = ArmsShow > 0.99f;
	if (!bVis) return;
	// balanceo: al girar la vista, los brazos se quedan un poco atrás y vuelven
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	const FRotator VR = PC ? PC->GetControlRotation() : FRotator::ZeroRotator;
	const float DYaw = FMath::FindDeltaAngleDegrees(LastViewRot.Yaw, VR.Yaw);
	const float DPitch = FMath::FindDeltaAngleDegrees(LastViewRot.Pitch, VR.Pitch);
	LastViewRot = VR;
	const FVector SwayWant(0.0f, FMath::Clamp(-DYaw * 0.5f, -3.0f, 3.0f), FMath::Clamp(-DPitch * 0.5f, -2.5f, 2.5f));
	Sway = FMath::VInterpTo(Sway, SwayWant, DeltaSeconds, 6.0f);
	// al andar suben y bajan a compás del paso (más suave agachado, más corriendo); y el retroceso del disparo
	const float Speed = C->GetCharacterMovement()->IsFalling() ? 0.0f : C->GetVelocity().Size2D();
	const float Amp = Speed > 40.0f ? (C->bIsCrouched ? 0.35f : (bSprint ? 1.3f : 0.7f)) : 0.0f;
	const FVector Bob(0.0f, FMath::Sin(BobPhase * 0.5f) * Amp * 0.8f, -FMath::Abs(FMath::Sin(BobPhase)) * Amp);
	RecoilT = FMath::Max(0.0f, RecoilT - DeltaSeconds * 5.0f);
	const FQuat Rel = FRotator(7.0f * RecoilT, 0.0f, 0.0f).Quaternion() * FRotator(0.0f, -90.0f, 0.0f).Quaternion();
	// la cabeza del maniquí, en la cámara: así la pistola queda donde la llevaría alguien de tu altura
	const FVector Head = Arms->GetBoneLocation(TEXT("head"), EBoneSpaces::ComponentSpace);
	const FVector Loc = -Rel.RotateVector(Head) + ArmsOffset + Bob + Sway + FVector(-5.0f * RecoilT, 0.0f, -30.0f * (1.0f - ArmsShow));
	Arms->SetRelativeLocationAndRotation(Loc, Rel);
}

void ATarsisDirector::BobTick(ACharacter* C, float DeltaSeconds)
{
	UCameraComponent* Cam = C->FindComponentByClass<UCameraComponent>();
	if (!Cam) return;
	const float Speed = C->GetCharacterMovement()->IsFalling() ? 0.0f : C->GetVelocity().Size2D();
	FVector Want = FVector::ZeroVector;
	if (Speed > 40.0f && !bBinoculars)
	{
		// un paso cada ~0,55 s andando; corriendo más rápido y más marcado, agachado más suave
		BobPhase += DeltaSeconds * Speed / 45.0f;
		const float Amp = C->bIsCrouched ? 0.6f : (bSprint ? 2.0f : 1.1f);
		Want = FVector(0.0f, FMath::Sin(BobPhase * 0.5f) * Amp * 0.6f, -FMath::Abs(FMath::Sin(BobPhase)) * Amp);
	}
	const FVector Next = FMath::VInterpTo(BobApplied, Want, DeltaSeconds, 10.0f);
	Cam->AddRelativeLocation(Next - BobApplied);
	BobApplied = Next;
}

// ---------------------------------------------------------------- sonido y clima

static USoundBase* LoadSnd(const TCHAR* Name)
{
	return LoadObject<USoundBase>(nullptr, *FString::Printf(TEXT("/Game/Tarsis/Sonidos/%s.%s"), Name, Name));
}

void ATarsisDirector::SetupSound()
{
	// pasos: 5 superficies x 3 variantes; si falta alguna (sonidos sin regenerar), se usa la grava o el cemento
	static const TCHAR* Surf[] = { TEXT("grava"), TEXT("cemento"), TEXT("metal"), TEXT("madera"), TEXT("hierba") };
	StepSnds.SetNum(15);
	for (int32 s = 0; s < 5; ++s)
	{
		for (int32 i = 0; i < 3; ++i)
		{
			USoundBase* S = LoadSnd(*FString::Printf(TEXT("paso_%s_%d"), Surf[s], i + 1));
			if (!S && s >= 2) S = StepSnds[(s == 3 ? 1 : 0) * 3 + i];
			StepSnds[s * 3 + i] = S;
		}
	}
	StoneSnd = LoadSnd(TEXT("piedra"));
	DartSnd = LoadSnd(TEXT("dardo"));
	WindSnd = LoadSnd(TEXT("viento"));
	RainSnd = LoadSnd(TEXT("lluvia"));
	RadioSnd = LoadSnd(TEXT("radio"));
	HumSnd = LoadSnd(TEXT("generador"));
	// haces de luz con niebla o lluvia: las farolas y los focos dispersan más en la niebla volumétrica
	for (TActorIterator<ALight> It(GetWorld()); It; ++It)
	{
		if (ULightComponent* L = It->GetLightComponent())
		{
			// tanda 25: las luces fuertes se pintan diez veces más flojas (ATarsisGuard::LightAt): dispersan algo más para
			// que el haz se siga viendo con lluvia (StrongSpotScattering; con 16 era un cono blanco macizo); el resplandor
			// de relleno («decorado») no hace halo en la niebla
			if (It->ActorHasTag(FName(TEXT("decorado")))) L->SetVolumetricScatteringIntensity(0.0f);
			else if (L->IsA<USpotLightComponent>()) L->SetVolumetricScatteringIntensity(It->ActorHasTag(FName(TEXT("luz_fuerte"))) ? StrongSpotScattering : 4.0f);
			else if (L->IsA<UPointLightComponent>()) L->SetVolumetricScatteringIntensity(1.0f);   // una puntual no hace haz: solo un halo suave
		}
	}
	// atenuación: se oye en 3D y se apaga hacia los 15 m (los pasos de un guardia tras una pared, la piedra al caer)
	Atten = NewObject<USoundAttenuation>(this);
	Atten->Attenuation.bAttenuate = true;
	Atten->Attenuation.bSpatialize = true;
	Atten->Attenuation.AttenuationShape = EAttenuationShape::Sphere;
	Atten->Attenuation.AttenuationShapeExtents = FVector(150.0f, 0.0f, 0.0f);
	Atten->Attenuation.FalloffDistance = 1500.0f;
	for (USoundBase* L : { WindSnd.Get(), RainSnd.Get(), HumSnd.Get() })
	{
		if (USoundWave* W = Cast<USoundWave>(L)) W->bLooping = true;
	}
	if (WindSnd)
	{
		WindComp = UGameplayStatics::SpawnSound2D(this, WindSnd, 0.3f, 1.0f, 0.0f, nullptr, false, false);
	}
	// noche: grillos y un rumor lejano, en bucle; su volumen va con el clima y con estar dentro (SoundTick)
	for (const TCHAR* N : { TEXT("grillos"), TEXT("rumor") })
	{
		USoundBase* S = LoadSnd(N);
		if (!S) continue;
		if (USoundWave* W = Cast<USoundWave>(S)) W->bLooping = true;
		UAudioComponent* A = UGameplayStatics::SpawnSound2D(this, S, 0.01f, 1.0f, 0.0f, nullptr, false, false);
		if (FCString::Strcmp(N, TEXT("grillos")) == 0) CricketComp = A; else RumbleComp = A;
	}
	SetupMusic();
	// zumbido del generador, en 3D: te guía hasta él y se calla cuando lo cortas
	if (HumSnd)
	{
		HumComp = UGameplayStatics::SpawnSoundAtLocation(this, HumSnd, GeneratorLoc + FVector(0.0f, 0.0f, 100.0f), FRotator::ZeroRotator, 0.8f, 1.0f, 0.0f, Atten, nullptr, false);
	}
	// gotas de lluvia: rayas finas alrededor del jugador (se ocultan bajo techo)
	UStaticMesh* Cyl = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder"));
	if (Cyl)
	{
		RainISM = NewObject<UInstancedStaticMeshComponent>(this);
		RainISM->SetStaticMesh(Cyl);
		RainISM->SetMobility(EComponentMobility::Movable);
		RainISM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		RainISM->SetCastShadow(false);
		RainISM->SetCanEverAffectNavigation(false);
		if (UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"))) RainISM->SetMaterial(0, Base);
		RainISM->RegisterComponent();
		if (UMaterialInstanceDynamic* M = RainISM->CreateDynamicMaterialInstance(0)) M->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.62f, 0.66f, 0.72f));
		TArray<FTransform> T;
		for (int32 i = 0; i < 450; ++i)
		{
			Drops.Add(FVector(FMath::FRandRange(-1200.0f, 1200.0f), FMath::FRandRange(-1200.0f, 1200.0f), FMath::FRandRange(-200.0f, 900.0f)));
			T.Add(FTransform(FRotator::ZeroRotator, FVector::ZeroVector, FVector(0.008f, 0.008f, 0.45f)));
		}
		RainISM->AddInstances(T, false, true);
		RainISM->SetVisibility(false);
	}
}

bool ATarsisDirector::IndoorAt(const FVector& P, const AActor* Ignore) const
{
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisSuelo), true, this);
	if (Ignore) Q.AddIgnoredActor(Ignore);
	if (GetWorld()->LineTraceSingleByChannel(Hit, P, P - FVector(0.0f, 0.0f, 250.0f), ECC_Visibility, Q))
	{
		if (const UStaticMeshComponent* SM = Cast<UStaticMeshComponent>(Hit.GetComponent()))
		{
			return SM->GetStaticMesh() && SM->GetStaticMesh()->GetName().Contains(TEXT("suelo_int"));
		}
	}
	return false;
}

static const TCHAR* SurfaceNames[] = { TEXT("grava"), TEXT("cemento"), TEXT("metal"), TEXT("madera"), TEXT("hierba") };

// superficie por un nombre (material físico PM_*, malla o material): -1 si no dice nada
static int32 SurfaceFromName(FString N)
{
	N.ToLowerInline();
	if (N.StartsWith(TEXT("pm_")))
	{
		for (int32 i = 0; i < 5; ++i) { if (N.Contains(SurfaceNames[i])) return i; }
		return -1;
	}
	if (N.Contains(TEXT("madera")) || N.Contains(TEXT("veta")) || N.Contains(TEXT("wood"))) return 3;
	if (N.Contains(TEXT("hierro")) || N.Contains(TEXT("metal")) || N.Contains(TEXT("tejado")) || N.Contains(TEXT("contenedor")) || N.Contains(TEXT("oliva")) || N.Contains(TEXT("chapa"))) return 2;
	if (N.Contains(TEXT("hierba")) || N.Contains(TEXT("cesped")) || N.Contains(TEXT("marisma")) || N.Contains(TEXT("grass"))) return 4;
	if (N.Contains(TEXT("suelo_int")) || N.Contains(TEXT("hormigon")) || N.Contains(TEXT("cemento")) || N.Contains(TEXT("muro")) || N.Contains(TEXT("pared"))) return 1;
	if (N.Contains(TEXT("suelo")) || N.Contains(TEXT("grava")) || N.Contains(TEXT("tierra"))) return 0;
	return -1;
}

int32 ATarsisDirector::SurfaceIndex(const FVector& P, const AActor* Ignore) const
{
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisPisada), true, this);
	Q.bReturnPhysicalMaterial = true;
	if (Ignore) Q.AddIgnoredActor(Ignore);
	if (!GetWorld()->LineTraceSingleByChannel(Hit, P + FVector(0.0f, 0.0f, 30.0f), P - FVector(0.0f, 0.0f, 250.0f), ECC_Visibility, Q)) return 0;
	// 1) material físico del triángulo pisado (tools/unreal/superficies.py los pone en los materiales)
	if (Hit.PhysMaterial.IsValid())
	{
		const int32 S = SurfaceFromName(Hit.PhysMaterial->GetName());
		if (S >= 0) return S;
	}
	// 2) la malla (las de la base van una por material: base_suelo, torre1_madera...) y luego sus materiales
	if (const UStaticMeshComponent* SM = Cast<UStaticMeshComponent>(Hit.GetComponent()))
	{
		if (SM->GetStaticMesh())
		{
			const int32 S = SurfaceFromName(SM->GetStaticMesh()->GetName());
			if (S >= 0) return S;
		}
		for (int32 i = 0; i < SM->GetNumMaterials(); ++i)
		{
			if (const UMaterialInterface* M = SM->GetMaterial(i))
			{
				const int32 S = SurfaceFromName(M->GetName());
				if (S >= 0) return S;
			}
		}
	}
	return 0;
}

FString ATarsisDirector::SurfaceAt(FVector Where) const
{
	return SurfaceNames[FMath::Clamp(SurfaceIndex(Where, UGameplayStatics::GetPlayerPawn(this, 0)), 0, 4)];
}

void ATarsisDirector::StepSound(const FVector& Where, int32 Surface, float Volume, bool b3D)
{
	if (StepSnds.Num() < 15) return;
	USoundBase* S = StepSnds[FMath::Clamp(Surface, 0, 4) * 3 + FMath::RandRange(0, 2)];
	if (!S) return;
	// la chapa y la madera suenan más; la hierba, menos
	static const float Loud[] = { 1.0f, 0.85f, 1.25f, 1.1f, 0.6f };
	const float Pitch = FMath::FRandRange(0.9f, 1.1f);
	Volume *= Loud[FMath::Clamp(Surface, 0, 4)];
	if (b3D) UGameplayStatics::PlaySoundAtLocation(this, S, Where, Volume, Pitch, 0.0f, Atten);
	else UGameplayStatics::PlaySound2D(this, S, Volume, Pitch);
}

USoundBase* ATarsisDirector::Sfx(const FString& Name)
{
	const FName K(*Name);
	if (TObjectPtr<USoundBase>* Found = SfxCache.Find(K)) return *Found;
	USoundBase* S = LoadSnd(*Name);
	SfxCache.Add(K, S);   // también si falta: no se vuelve a buscar
	return S;
}

void ATarsisDirector::PlaySfx(const FString& Name, const FVector& Where, float Volume, bool b3D)
{
	USoundBase* S = Sfx(Name);
	if (!S) return;
	if (b3D) UGameplayStatics::PlaySoundAtLocation(this, S, Where, Volume, 1.0f, 0.0f, Atten);
	else UGameplayStatics::PlaySound2D(this, S, Volume);
}

void ATarsisDirector::GuardStep(ATarsisGuard* G, bool bRun)
{
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!G || !P || bCine) return;
	const float Dm = FVector::Dist(G->GetActorLocation(), P->GetActorLocation());
	if (Dm > 1600.0f) return;
	++GuardStepsPlayed;
	StepSound(G->GetActorLocation(), SurfaceIndex(G->GetActorLocation(), G), bRun ? 1.0f : (G->bTurnStepping ? 0.4f : 0.75f), true);
	if (bSubtitles && VoiceSubT <= 0.0f)
	{
		const float D2 = FVector::Dist2D(G->GetActorLocation(), P->GetActorLocation()) / 100.0f;
		if (SubtitleT <= 0.0f || D2 < SubtitleDist)
		{
			SubtitleDist = D2;
			Subtitle = FString::Printf(TEXT("[%s - %s, %s, %d m]"), bRun ? TEXT("CORRE") : TEXT("PASOS"), *G->GuardName.ToUpper(), *Direction(G->GetActorLocation()), FMath::RoundToInt(D2));
			SubtitleT = 1.2f;
		}
	}
}

void ATarsisDirector::GuardSay(ATarsisGuard* G, const FString& Key, bool bRadio)
{
	if (!G || bCine || bDone || G->bAlly) return;
	const float Now = GetWorld()->GetTimeSeconds();
	const TObjectPtr<ATarsisGuard> K(G);
	float& Next = VoiceNext.FindOrAdd(K, 0.0f);
	// no repite frase enseguida (al cambiar de estado varias veces seguidas), salvo las que importan: el empujón,
	// el «¡alto!» y el aviso por radio del cuerpo no pueden quedarse callados por un «¿quién anda ahí?» de antes
	const bool bUrgent = Key == TEXT("eh") || Key == TEXT("alto") || Key == TEXT("suelo") || Key == TEXT("puerta") || Key == TEXT("luz") || Key == TEXT("donde")
		|| Key == TEXT("tengo") || Key == TEXT("cuerpo") || Key == TEXT("farol") || Key == TEXT("farola") || Key == TEXT("apoyo") || Key == TEXT("voy") || Key == TEXT("perdido") || Key == TEXT("despierta")
		|| Key == TEXT("sinradio") || Key == TEXT("emisora") || Key == TEXT("papeles") || Key == TEXT("pase") || Key == TEXT("registro");
	FString& Prev = VoicePrev.FindOrAdd(K);
	// tras avisar por radio del cuerpo, la alarma que sigue no lo pisa con un «¡alto!»
	if (Now < Next && (!bUrgent || Prev == TEXT("suelo"))) return;
	Prev = Key;
	Next = Now + 3.5f;
	FString Who = G->bTowerSentry ? TEXT("centinela") : G->GuardName.ToLower();
	USoundBase* S = Sfx(FString::Printf(TEXT("voz_%s_%s"), *Who, *Key));
	if (!S) { Who = TEXT("moya"); S = Sfx(FString::Printf(TEXT("voz_moya_%s"), *Key)); }
	if (S) UGameplayStatics::PlaySoundAtLocation(this, S, G->GetActorLocation() + FVector(0.0f, 0.0f, 150.0f), bRadio ? 1.0f : 1.2f, 1.0f, 0.0f, Atten);
	if (bRadio && RadioSnd) UGameplayStatics::PlaySound2D(this, RadioSnd, 0.35f);   // la radio la oyes tú también, lejos o no
	LastVoice = Who + TEXT("_") + Key;
	++VoicesPlayed;
	VoiceLog.Add(LastVoice);
	if (VoiceLog.Num() > 30) VoiceLog.RemoveAt(0);
	// las voces llevan siempre subtítulo (los de pasos y ruidos, solo con la opción). Texto en ASCII (la fuente del HUD no lleva tildes)
	FString T;
	if (Key == TEXT("quien")) T = TEXT("Quien anda ahi?");
	else if (Key == TEXT("ruido")) T = TEXT("Que ha sido eso?");
	else if (Key == TEXT("viento")) T = TEXT("Bah. Habra sido el viento.");
	else if (Key == TEXT("alto")) T = TEXT("Alto! Quieto ahi!");
	else if (Key == TEXT("nadie")) T = TEXT("Aqui no hay nadie.");
	else if (Key == TEXT("suelo")) T = TEXT("Central, aqui patio. He encontrado a uno en el suelo.");
	else if (Key == TEXT("puerta")) T = TEXT("Esta puerta estaba cerrada.");
	else if (Key == TEXT("luz")) T = TEXT("Y la luz?");
	else if (Key == TEXT("donde")) T = TEXT("Donde se ha metido? No contesta.");
	else if (Key == TEXT("eh")) T = TEXT("Eh! Pero que...?");
	else if (Key == TEXT("farol")) T = TEXT("Central, el farol del control esta roto. Cristales por el suelo... esto no es el viento.");
	else if (Key == TEXT("farola")) T = TEXT("Central, aqui hay una farola rota. Cristales por el suelo... esto no es el viento.");
	else if (Key == TEXT("apoyo")) T = TEXT("Central, ahi no hay luz. Yo solo no entro: mandadme a alguien.");
	else if (Key == TEXT("voy")) T = TEXT("Voy para alla. No te muevas.");
	else if (Key == TEXT("cuerpo")) T = TEXT("Eh... ese de ahi esta en el suelo?");
	else if (Key == TEXT("despierta")) T = TEXT("Ay, mi cabeza... Quien ha sido?");
	else if (Key == TEXT("tengo")) T = TEXT("Te tengo!");
	else if (Key == TEXT("perdido")) T = TEXT("Lo he perdido.");
	else if (Key == TEXT("yacasi")) T = TEXT("Ya casi esta.");
	else if (Key == TEXT("papeles")) T = TEXT("Para ahi. Los papeles del porte.");
	else if (Key == TEXT("pase")) T = TEXT("Todo en orden. Tira.");
	else if (Key == TEXT("sinradio")) T = TEXT("Central? ... Central? Esto no da senal.");
	else if (Key == TEXT("emisora")) T = TEXT("Quien ha tocado esto? Una valvula floja... Ya casi.");
	else if (Key == TEXT("registro")) T = TEXT("Hay orden de mirar la carga. Abre atras.");
	else T = Key;
	T = Tx(FName(*(TEXT("voz_") + Key)), *T);
	const FString Name = G->bTowerSentry ? Tx(TEXT("nombre_centinela"), TEXT("CENTINELA")) : G->GuardName.ToUpper();
	SaySubtitle(bRadio ? FString::Printf(TEXT("%s (RADIO)"), *Name) : FString::Printf(TEXT("%s (%s)"), *Name, *Direction(G->GetActorLocation())), T);
}

void ATarsisDirector::SoundTick(ACharacter* C, float DeltaSeconds)
{
	if (VoiceSubT > 0.0f) VoiceSubT -= DeltaSeconds;
	// subtítulos en cola: si hablan dos seguidos, el segundo sale al acabar el primero
	if (VoiceSubT <= 0.0f && PendingSubs.Num() > 0)
	{
		const FString Next = PendingSubs[0];
		PendingSubs.RemoveAt(0);
		ShowSubtitleLine(Next);
	}
	// tus pasos: uno cada ~1,4 m (agachado, flojito; corriendo, fuerte), con el sonido de lo que pisas
	const float Speed = C->GetCharacterMovement()->IsFalling() ? 0.0f : C->GetVelocity().Size2D();
	if (Speed > 40.0f)
	{
		PlayerStride += Speed * DeltaSeconds;
		const float Stride = C->bIsCrouched ? 90.0f : (bSprint ? 190.0f : 140.0f);
		if (PlayerStride >= Stride)
		{
			PlayerStride = 0.0f;
			++PlayerSteps;
			LastStepSurface = SurfaceNames[FMath::Clamp(PlayerSurface, 0, 4)];
			StepSound(C->GetActorLocation(), PlayerSurface, C->bIsCrouched ? 0.15f : (bSprint ? 0.8f : 0.45f), false);
		}
	}
	// pasos de los guardias, en 3D: los oyes acercarse aunque haya una pared. Los que tienen cuerpo animado los
	// mandan ellos al apoyar cada pie (GuardStep); los demás (cilindro provisional), por distancia recorrida
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Down || It->bTowerSentry || It->HasFootSync()) continue;
		const float GS = It->GetVelocity().Size2D();
		if (GS < 40.0f) continue;
		const TObjectPtr<ATarsisGuard> K(*It);
		float& D = GuardStride.FindOrAdd(K);
		D += GS * DeltaSeconds;
		if (D < (GS > 300.0f ? 170.0f : 120.0f)) continue;
		D = 0.0f;
		GuardStep(*It, GS > 300.0f);
	}
	// viento y lluvia: más bajos bajo techo. Grillos con buen tiempo (con lluvia callan, con niebla pocos); el rumor
	// lejano sube con la lluvia (tormenta a lo lejos)
	// bajo la lona del camión (tanda 23) todo lo de fuera llega a la mitad; la lluvia, menos: repica en la lona
	const float Box = 1.0f - 0.5f * RideMuffleK;
	if (WindComp) WindComp->SetVolumeMultiplier((bIndoor ? 0.12f : (Weather == 1 ? 0.2f : (Weather == 2 ? 0.16f : 0.3f))) * Box);
	if (RainComp) RainComp->SetVolumeMultiplier((bIndoor ? 0.15f : 0.45f) * (1.0f - 0.2f * RideMuffleK));
	const float In = (bIndoor ? 0.3f : 1.0f) * Box;
	if (CricketComp) CricketComp->SetVolumeMultiplier(FMath::Max(0.001f, In * (Weather == 1 ? 0.0f : (Weather == 2 ? 0.07f : 0.2f))));
	if (RumbleComp) RumbleComp->SetVolumeMultiplier(FMath::Max(0.001f, In * (Weather == 1 ? 0.3f : 0.14f)));
}

void ATarsisDirector::RainTick(float DeltaSeconds)
{
	if (!RainISM) return;
	const bool bShow = Weather == 1 && !bIndoor;
	if (RainISM->IsVisible() != bShow) RainISM->SetVisibility(bShow);
	if (!bShow) return;
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC) return;
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	TArray<FTransform> T;
	T.Reserve(Drops.Num());
	for (FVector& D : Drops)
	{
		D.Z -= 1300.0f * DeltaSeconds;
		if (D.Z < -250.0f) D = FVector(FMath::FRandRange(-1200.0f, 1200.0f), FMath::FRandRange(-1200.0f, 1200.0f), 900.0f);
		T.Add(FTransform(FRotator(0.0f, 0.0f, 8.0f), Loc + D, FVector(0.008f, 0.008f, 0.45f)));   // algo inclinadas por el viento
	}
	RainISM->BatchUpdateInstancesTransforms(0, T, true, true, true);
}

void ATarsisDirector::CycleWeather()
{
	SetWeather((Weather + 1) % 3);
	static const TCHAR* Def[] = {
		TEXT("DESPEJADO\nLa vista y el oido de los guardias, normales."),
		TEXT("LLUVIA\nLos guardias ven menos de lejos y el agua tapa tus pasos fuera."),
		TEXT("NIEBLA\nLos guardias ven mucho menos de lejos; tus pasos se oyen igual.") };
	static const TCHAR* Keys[] = { TEXT("clima_despejado"), TEXT("clima_lluvia"), TEXT("clima_niebla") };
	ShowMessage(Tx(Keys[Weather], Def[Weather]), 3.5f);
}

void ATarsisDirector::SetWeather(int32 NewWeather)
{
	Weather = FMath::Clamp(NewWeather, 0, 2);
	const float ViewMul = Weather == 1 ? 0.75f : (Weather == 2 ? 0.55f : 1.0f);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		const TObjectPtr<ATarsisGuard> K(*It);
		float& B = BaseView.FindOrAdd(K, It->ViewDistance);
		It->ViewDistance = B * ViewMul;
	}
	// niebla de la escena (ExponentialHeightFog del nivel): más espesa con lluvia y mucho más con niebla
	for (TActorIterator<AExponentialHeightFog> It(GetWorld()); It; ++It)
	{
		UExponentialHeightFogComponent* F = It->GetComponent();
		if (!F) continue;
		if (BaseFog < 0.0f) { BaseFog = F->FogDensity; BaseFogColor = F->FogInscatteringLuminance; }
		// tanda 25: con lluvia, RainFogMul (1,25; antes 1,8 y luego 1,5) y el color de la niebla más oscuro (RainFogColor):
		// el velo gris aclaraba toda la base y tapaba lo mojado; ahora la lluvia se lee en el suelo y en el cielo cubierto
		F->SetFogDensity(FMath::Min(0.2f, BaseFog * (Weather == 2 ? 4.0f : (Weather == 1 ? RainFogMul : 1.0f))));
		// niebla volumétrica: las farolas y los focos dibujan haces; de noche, sin ella, la niebla casi no se ve
		F->SetVolumetricFog(Weather != 0);
		F->SetVolumetricFogScatteringDistribution(Weather == 2 ? 0.6f : 0.4f);
		F->SetVolumetricFogExtinctionScale(Weather == 2 ? 2.0f : 1.0f);
		F->SetFogInscatteringColor(Weather == 2 ? FLinearColor(0.10f, 0.11f, 0.13f) : (Weather == 1 ? RainFogColor : BaseFogColor));
		break;
	}
	// con escalabilidad Baja el motor desactiva la niebla volumétrica (r.VolumetricFog 0) y no hay haces:
	// con lluvia o niebla se activa desde el juego y al despejar se deja como estaba
	if (IConsoleVariable* CV = IConsoleManager::Get().FindConsoleVariable(TEXT("r.VolumetricFog")))
	{
		if (SavedVolFog < 0) SavedVolFog = CV->GetInt();
		CV->Set(Weather != 0 ? 1 : SavedVolFog, ECVF_SetByCode);
	}
	if (Weather == 1 && !RainComp && RainSnd) RainComp = UGameplayStatics::SpawnSound2D(this, RainSnd, 0.45f, 1.0f, 0.0f, nullptr, false, false);
	if (Weather != 1 && RainComp) { RainComp->Stop(); RainComp->DestroyComponent(); RainComp = nullptr; }
}

// ---------------------------------------------------------------- radio y base en guardia

void ATarsisDirector::RadioTick(float DeltaSeconds)
{
	// tras una alarma, la base queda en guardia 90 s: la sospecha sube más deprisa
	bool bAlarm = false;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Alert && !It->bTowerSentry) bAlarm = true;
	}
	if (bAlarm) TensionT = 90.0f;
	else if (TensionT > 0.0f) TensionT -= DeltaSeconds;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		static const float DiffSight[] = { 0.65f, 1.0f, 1.4f };   // fácil, normal, difícil
		It->AlertBoost = (TensionT > 0.0f ? 1.5f : 1.0f) * DiffSight[FMath::Clamp(Difficulty, 0, 2)];
		// en guardia, la ronda se hace a paso ligero (se ve en el mundo, no solo en el HUD)
		const TObjectPtr<ATarsisGuard> K(*It);
		const float& B = BaseWalkSpeed.FindOrAdd(K, It->WalkSpeed);
		It->WalkSpeed = TensionT > 0.0f ? B * 1.7f : B;
	}
	// radio: a los 40 s de caer un guardia, no contesta y mandan al más cercano a donde cayó.
	// Si lo has arrastrado y escondido, el que va a mirar no lo encuentra.
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		const TObjectPtr<ATarsisGuard> K(G);
		if (G->State != ETarsisGuardState::Down) { Called.Remove(K); continue; }
		if (G->bFound || G->bAlly || Called.Contains(K) || G->DownTime() < 40.0f) continue;
		if (RadioDead()) continue;   // tanda 32: sin red nadie le echa de menos; cuando vuelva, llamaran
		Called.Add(K);
		ATarsisGuard* Best = nullptr;
		float BestD = TNumericLimits<float>::Max();
		for (TActorIterator<ATarsisGuard> O(GetWorld()); O; ++O)
		{
			if (*O == G || O->State == ETarsisGuardState::Down || O->State == ETarsisGuardState::Alert || O->bTowerSentry || O->bAlly) continue;
			const float D = FVector::Dist(O->GetActorLocation(), G->KnockLoc);
			if (D < BestD) { BestD = D; Best = *O; }
		}
		if (!Best) continue;
		// la central llama al caído. Tanda 28: si estás junto a él, su radio la tienes tú y puedes contestar
		CentralSay(TEXT("responde"), Tx(TEXT("radio_responde"), TEXT("{0}, responde. {0}?"), { G->GuardName }));
		APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
		if (bRadioAnswer && !bRadioAsk && Pl && !bChoice && !bKeypad && !bRiding && !bCine
			&& FVector::Dist(Pl->GetActorLocation(), G->GetActorLocation()) < RadioReach)
		{
			StartRadioAsk(G);
			continue;
		}
		RadioSend(G, 1);
	}
	// la pregunta de la central no espera: sin respuesta (o si te alejas del cuerpo), mandan a alguien como siempre
	if (bRadioAsk)
	{
		RadioAskT -= DeltaSeconds;
		ATarsisGuard* G = RadioAskGuard;
		APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
		const bool bGone = !G || G->State != ETarsisGuardState::Down || !Pl || FVector::Dist(Pl->GetActorLocation(), G->GetActorLocation()) > RadioReach * 1.6f;
		if (RadioAskT <= 0.0f || bGone)
		{
			bRadioAsk = false;
			RadioAskGuard = nullptr;
			MessageT = FMath::Min(MessageT, 0.3f);
			if (G && G->State == ETarsisGuardState::Down) RadioSend(G, 1);
		}
	}
	EmisoraTick(DeltaSeconds);
	PartesTick();
}

// El guardia (o los dos) más cercano va a mirar dónde cayó el que no contesta
void ATarsisDirector::RadioSend(ATarsisGuard* Fallen, int32 HowMany)
{
	if (!Fallen) return;
	TArray<ATarsisGuard*> Sent;
	for (int32 n = 0; n < HowMany; ++n)
	{
		ATarsisGuard* Best = nullptr;
		float BestD = TNumericLimits<float>::Max();
		for (TActorIterator<ATarsisGuard> O(GetWorld()); O; ++O)
		{
			if (*O == Fallen || Sent.Contains(*O) || O->State == ETarsisGuardState::Down || O->State == ETarsisGuardState::Alert || O->bTowerSentry || O->bAlly) continue;
			const float D = FVector::Dist(O->GetActorLocation(), Fallen->KnockLoc);
			if (D < BestD) { BestD = D; Best = *O; }
		}
		if (!Best) break;
		Sent.Add(Best);
		Best->HearNoise(Fallen->KnockLoc);
		if (RadioSnd) UGameplayStatics::PlaySoundAtLocation(this, RadioSnd, Best->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 1.0f, 1.0f, 0.0f, Atten);
	}
	if (Sent.Num() > 0)
	{
		// al rato, el que va a mirar: «¿dónde se ha metido?»
		TWeakObjectPtr<ATarsisGuard> W(Sent[0]);
		FTimerHandle H;
		GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateWeakLambda(this, [this, W]() { if (W.IsValid()) GuardSay(W.Get(), TEXT("donde")); }), 2.2f, false);
	}
}

// ---------------------------------------------------------------- «Responde, Carmona»: contestar por la radio de otro

// Cada centinela da su parte a su manera (textos «parte_<nombre>» de mision1.json): lo que dice después de «Aquí Fulano»
FString ATarsisDirector::ParteOf(const FString& Name) const
{
	const FString* F = Texts.Find(FName(*(TEXT("parte_") + Name.ToLower())));
	return F ? *F : FString(TEXT("Sin novedad."));
}

// De vez en cuando, cada guardia en su ronda da el parte por radio. Si estás cerca lo oyes (subtítulo siempre: es
// una pista, no ambiente) y te lo quedas; es lo que tendrás que decir si la central lo llama cuando esté en el suelo
void ATarsisDirector::PartesTick()
{
	if (!bRadioAnswer || bCine || bDone || bPowerOff || TensionT > 0.0f || RadioDead()) return;
	RadioChatTick();
	const float Now = GetWorld()->GetTimeSeconds();
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->bTowerSentry || It->bAlly || It->State != ETarsisGuardState::Patrol || It->IsHeld()) continue;
		const TObjectPtr<ATarsisGuard> K(*It);
		float* Next = ParteNext.Find(K);
		if (!Next) { ParteNext.Add(K, Now + 12.0f + float(GetTypeHash(It->GuardName) % 1000) * 0.001f * ParteEvery); continue; }
		if (Now < *Next) continue;
		*Next = Now + ParteEvery;
		SayParte(*It);
	}
}

void ATarsisDirector::SayParte(ATarsisGuard* G)
{
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!G || !Pl || FVector::Dist(Pl->GetActorLocation(), G->GetActorLocation()) > ParteHearDist) return;
	const FString Line = Tx(TEXT("parte_aqui"), TEXT("Aqui {0}. {1}"), { G->GuardName, ParteOf(G->GuardName) });
	if (RadioSnd) UGameplayStatics::PlaySoundAtLocation(this, RadioSnd, G->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 1.0f, 1.0f, 0.0f, Atten);
	SaySubtitle(FString::Printf(TEXT("%s (%s)"), *G->GuardName.ToUpper(), *Direction(G->GetActorLocation())), Line);
	LastVoice = G->GuardName.ToLower() + TEXT("_parte");
	VoiceLog.Add(LastVoice);
	if (VoiceLog.Num() > 30) VoiceLog.RemoveAt(0);
	if (!HeardPartes.Contains(G->GuardName))
	{
		HeardPartes.Add(G->GuardName);
		Teach(TEXT("ensena_parte"), TEXT("PARTE OIDO\nCada centinela da el parte a su manera. Si la central llama a uno que has dejado en el suelo, contesta como el."), {}, 4.5f);
	}
}

void ATarsisDirector::StartRadioAsk(ATarsisGuard* G)
{
	const FString Name = G->GuardName;
	const FString Own = ParteOf(Name);
	// la de otro: la del primer compañero que la dé distinta (empezando por uno al azar)
	TArray<FString> Others;
	for (TActorIterator<ATarsisGuard> O(GetWorld()); O; ++O)
	{
		if (*O == G || O->bTowerSentry) continue;
		const FString P = ParteOf(O->GuardName);
		if (P != Own) Others.AddUnique(P);
	}
	const FString Other = Others.Num() > 0 ? Others[FMath::RandHelper(Others.Num())] : FString(TEXT("Sin novedad en el puesto."));
	const FString Duress = Tx(TEXT("parte_coaccion"), TEXT("Todo tranquilo."));
	RadioRight = 1 + FMath::RandHelper(3);
	RadioDuress = 1 + (RadioRight % 3);
	RadioOptions.Init(FString(), 3);
	for (int32 i = 1; i <= 3; ++i)
	{
		RadioOptions[i - 1] = Tx(TEXT("parte_aqui"), TEXT("Aqui {0}. {1}"), { Name, i == RadioRight ? Own : (i == RadioDuress ? Duress : Other) });
	}
	RadioAskGuard = G;
	RadioAskT = RadioAnswerSeconds;
	bRadioAsk = true;
	ShowMessage(Tx(TEXT("radio_contesta"), TEXT("LA CENTRAL LLAMA A {0}. SU RADIO LA TIENES TU:\n1   {1}\n2   {2}\n3   {3}"),
		{ Name.ToUpper(), RadioOptions[0], RadioOptions[1], RadioOptions[2] }), RadioAnswerSeconds);
}

void ATarsisDirector::AnswerRadio(int32 Option)
{
	if (!bRadioAsk || Option < 1 || Option > 3) return;
	ATarsisGuard* G = RadioAskGuard;
	bRadioAsk = false;
	RadioAskGuard = nullptr;
	MessageT = FMath::Min(MessageT, 0.2f);
	if (!G) return;
	SaySubtitle(Tx(TEXT("radio_tu"), TEXT("TU (RADIO)")), RadioOptions.IsValidIndex(Option - 1) ? RadioOptions[Option - 1] : FString());
	if (Option == RadioRight)
	{
		// cuela: nadie va a mirar. Si lo encuentran o se despierta, ya es otra historia
		++RadioFooled;
		CentralSay(TEXT("recibido"), Tx(TEXT("radio_recibido"), TEXT("Recibido, {0}."), { G->GuardName }), 1.6f);
	}
	else if (Option == RadioDuress)
	{
		// la frase de coacción: la central contesta como si nada y manda a dos, con la base en guardia
		CentralSay(TEXT("coaccion"), Tx(TEXT("radio_coaccion"), TEXT("Recibido, {0}. Aguanta ahi."), { G->GuardName }), 1.6f);
		TensionT = FMath::Max(TensionT, 90.0f);
		RadioSend(G, 2);
		FTimerHandle H;
		GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateWeakLambda(this, [this]()
		{
			Teach(TEXT("ensena_coaccion"), TEXT("TODO TRANQUILO\nEs lo que dice un centinela cuando le estan apuntando. La central ha mandado gente."), {}, 5.0f);
		}), 3.5f, false);
	}
	else
	{
		CentralSay(TEXT("repite"), Tx(TEXT("radio_repite"), TEXT("{0}? Ese parte no es el tuyo. Voy a mandar a alguien."), { G->GuardName }), 1.6f);
		RadioSend(G, 1);
	}
}

// ---------------------------------------------------------------- generador

void ATarsisDirector::CutPower()
{
	bPowerOff = true;
	bPowerCutOnce = true;
	// el guardia de suelo más cercano se queja: «¿y la luz?»
	{
		ATarsisGuard* Near = nullptr;
		float ND = TNumericLimits<float>::Max();
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (It->bTowerSentry || It->bAlly || It->State == ETarsisGuardState::Down) continue;
			const float Dd = FVector::Dist(It->GetActorLocation(), GeneratorLoc);
			if (Dd < ND) { ND = Dd; Near = *It; }
		}
		if (Near) GuardSay(Near, TEXT("luz"));
	}
	PowerT = 60.0f;
	RepairT = 0.0f;
	OffLights.Reset();
	PendingOff.Reset();
	OffClock = 0.0f;
	RepairCallT = 0.0f;
	// se apagan farolas, focos de las torres y luces de dentro (el cielo y la luna siguen), en cadena desde el
	// generador hacia fuera en unos 2,5 s, cada una con su chasquido: ves venir la oscuridad
	for (TActorIterator<ALight> It(GetWorld()); It; ++It)
	{
		ULocalLightComponent* L = Cast<ULocalLightComponent>(It->GetLightComponent());
		if (!L || !L->IsVisible()) continue;
		if (It->ActorHasTag(FName(TEXT("camion")))) continue;   // los faros del camión van con su batería
		if (It->ActorHasTag(FName(TEXT("decorado")))) continue; // el resplandor de relleno sigue a su farola (ZonesTick)
		PendingOff.Add(L);
	}
	const FVector G = GeneratorLoc;
	Algo::Sort(PendingOff, [G](const TObjectPtr<ULightComponent>& A, const TObjectPtr<ULightComponent>& B) { return FVector::DistSquared(A->GetComponentLocation(), G) < FVector::DistSquared(B->GetComponentLocation(), G); });
	if (HumComp) HumComp->Stop();
	if (StoneSnd) UGameplayStatics::PlaySoundAtLocation(this, StoneSnd, GeneratorLoc + FVector(0.0f, 0.0f, 80.0f), 1.0f, 0.6f, 0.0f, Atten);
	TensionT = FMath::Max(TensionT, 60.0f);
	// mandan a arreglarlo a uno que esté lejos (el más cercano de los que quedan a más de 20 m; si no, el más lejano),
	// para que el apagón dé tiempo a cruzar a oscuras
	Repairer = nullptr;
	ATarsisGuard* Far = nullptr;
	float BestD = TNumericLimits<float>::Max(), FarD = -1.0f;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Down || It->State == ETarsisGuardState::Alert || It->bTowerSentry || It->bAlly) continue;
		const float D = FVector::Dist(It->GetActorLocation(), GeneratorLoc);
		if (D >= 2000.0f && D < BestD) { BestD = D; Repairer = *It; }
		if (D > FarD) { FarD = D; Far = *It; }
	}
	if (!Repairer) Repairer = Far;
	WindowsDark(true);
	if (Repairer)
	{
		Repairer->SetFlashlight(true);
		Repairer->SetFlashlightShadows(true);   // su cono recorta cajas y muros: te puedes esconder detrás
		Repairer->HearNoise(RepairSpot());
		if (RadioSnd) UGameplayStatics::PlaySoundAtLocation(this, RadioSnd, Repairer->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 1.0f, 1.0f, 0.0f, Atten);
		const FString RName = Repairer->GuardName;
		FTimerHandle H;
		GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateWeakLambda(this, [this, RName]()
		{
			CentralSay(TEXT("luz"), Tx(TEXT("radio_luz"), TEXT("Se ha ido la luz en toda la base! {0}, mira el generador."), { RName }));
		}), 1.6f, false);
	}
	Teach(TEXT("ensena_generador"), TEXT("GENERADOR CORTADO\nSe apagan farolas y focos: la oscuridad te esconde. La base se pone en guardia."), {}, 4.5f);
}

void ATarsisDirector::RestorePower(bool bByGuard)
{
	bPowerOff = false;
	bReserveHalf = !bByGuard;
	PowerT = 0.0f;
	// arreglado por el guardia, vuelven todas; con el generador de reserva, solo una de cada dos (las otras se quedan
	// apagadas el resto de la partida): después del apagón la base queda distinta, con zonas nuevas de sombra
	int32 Idx = 0;
	for (ULightComponent* L : OffLights)
	{
		if (!L || (bLampBroken && GateLamp && L == GateLamp->GetLightComponent())) continue;
		const AActor* Own = L->GetOwner();
		// los focos de las torres tienen su propio circuito. GetName() da el nombre del objeto (SpotLight_N), no la
		// etiqueta del editor (foco_torreta_*), así que se reconocen por ser el TowerLight de un centinela.
		// El farol de la garita (si no está roto) va con ellos: el control siempre está iluminado
		bool bTowerLamp = GateLamp && Own == GateLamp.Get();
		for (TActorIterator<ATarsisGuard> G(GetWorld()); G && !bTowerLamp; ++G) bTowerLamp = Own && G->TowerLight == Own;
		const bool bOn = bByGuard || bTowerLamp || (Idx++ % 2 == 0);
		if (bOn) L->SetVisibility(true);
	}
	OffLights.Reset();
	PendingOff.Reset();
	WindowsDark(false);
	if (Repairer) Repairer->StopRepair();
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It) { It->SetFlashlightShadows(false); It->SetFlashlight(false); }
	if (HumComp) HumComp->Play();
	if (bByGuard && Repairer) Teach(TEXT("ensena_luz_vuelve"), TEXT("VUELVE LA LUZ\n{0} ha arrancado el generador."), { Repairer->GuardName }, 3.5f);
	else Teach(TEXT("ensena_reserva"), TEXT("VUELVE LA LUZ (A MEDIAS)\nEl generador de reserva no da para todo: la mitad de las farolas se quedan apagadas."), {}, 4.0f);
	Repairer = nullptr;
}

void ATarsisDirector::PowerTick(float DeltaSeconds)
{
	if (!bPowerOff) return;
	// apagado en cadena
	if (PendingOff.Num() > 0)
	{
		OffClock += DeltaSeconds;
		const float Step = 2.5f / FMath::Max(1, PendingOff.Num() + OffLights.Num());
		while (PendingOff.Num() > 0 && OffClock >= 0.2f + OffLights.Num() * Step)
		{
			ULightComponent* L = PendingOff[0];
			PendingOff.RemoveAt(0);
			if (!L) continue;
			L->SetVisibility(false);
			OffLights.Add(L);
			if (StoneSnd) UGameplayStatics::PlaySoundAtLocation(this, StoneSnd, L->GetComponentLocation(), 0.45f, 0.45f, 0.0f, Atten);
		}
	}
	// sin luz, los guardias de suelo sacan la linterna (también el que se despierta)
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It) It->SetFlashlight(true);
	PowerT -= DeltaSeconds;
	if (PowerT <= 0.0f) { RestorePower(false); return; }
	// cada 15 s la radio pregunta al reparador; si lo has derribado y no contesta, entra la reserva y la base se alarma
	RepairCallT += DeltaSeconds;
	if (Repairer && RepairCallT >= 15.0f)
	{
		RepairCallT = 0.0f;
		if (RadioSnd) UGameplayStatics::PlaySoundAtLocation(this, RadioSnd, Repairer->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 1.0f, 1.0f, 0.0f, Atten);
		if (Repairer->State != ETarsisGuardState::Down)
		{
			CentralSay(TEXT("comova"), Tx(TEXT("radio_comova"), TEXT("{0}, como va eso?"), { Repairer->GuardName }));
			TWeakObjectPtr<ATarsisGuard> W(Repairer.Get());
			FTimerHandle H;
			GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateWeakLambda(this, [this, W]() { if (W.IsValid() && W->State != ETarsisGuardState::Down) GuardSay(W.Get(), TEXT("yacasi"), true); }), 2.0f, false);
		}
		else
		{
			const FString Name = Repairer->GuardName;
			RestorePower(false);
			TensionT = 90.0f;
			// los dos de suelo más cercanos van corriendo al generador
			TArray<ATarsisGuard*> Near;
			for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
			{
				if (It->State == ETarsisGuardState::Down || It->bTowerSentry || It->bAlly) continue;
				Near.Add(*It);
			}
			const FVector G = GeneratorLoc;
			Near.Sort([G](const ATarsisGuard& A, const ATarsisGuard& B) { return FVector::DistSquared(A.GetActorLocation(), G) < FVector::DistSquared(B.GetActorLocation(), G); });
			for (int32 i = 0; i < Near.Num() && i < 2; ++i) { Near[i]->Alarm(GeneratorLoc); Near[i]->bRadioCall = true; }
			CentralSay(TEXT("reserva"), Tx(TEXT("radio_reserva"), TEXT("{0}, como va eso? ... {0}? Entra la reserva. Todos al generador, ya!"), { Name }));
			return;
		}
	}
	// el enviado lo arregla tras RepairSeconds junto al generador; si lo derribas antes, la luz tarda lo que le quede
	if (Repairer && Repairer->State != ETarsisGuardState::Down && Repairer->State != ETarsisGuardState::Alert)
	{
		// tras buscar un rato junto al generador pasaría a volver a su ronda: se le vuelve a mandar (también tras una captura)
		if (!Repairer->IsRepairing() && (Repairer->State == ETarsisGuardState::Return || Repairer->State == ETarsisGuardState::Patrol)) Repairer->HearNoise(RepairSpot());
		// el guardia da por llegado a menos de 150 de su destino: se mide desde el sitio de reparación
		if (FVector::Dist2D(Repairer->GetActorLocation(), RepairSpot()) < 250.0f)
		{
			if (!Repairer->IsRepairing()) Repairer->StartRepair(GeneratorLoc);   // se queda y barre el patio con la linterna
			if (Repairer->IsRepairing()) RepairT += DeltaSeconds;
			if (RepairT >= RepairSeconds) RestorePower(true);
		}
	}
}

void ATarsisDirector::WindowsDark(bool bDark)
{
	if (!bDark)
	{
		for (int32 i = 0; i < WinComps.Num(); ++i)
		{
			if (WinComps[i]) WinComps[i]->SetMaterial(WinSlots[i], WinMats[i]);
		}
		WinComps.Reset(); WinSlots.Reset(); WinMats.Reset();
		return;
	}
	if (!DarkWindow)
	{
		UMaterialInterface* Base = LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
		if (!Base) return;
		DarkWindow = UMaterialInstanceDynamic::Create(Base, this);
		DarkWindow->SetVectorParameterValue(TEXT("Color"), FLinearColor(0.015f, 0.017f, 0.02f));
	}
	// las ventanas con material emisivo se quedan a oscuras (se cambia el material de esa ranura y se guarda el original)
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		TArray<UMeshComponent*> Meshes;
		It->GetComponents<UMeshComponent>(Meshes);
		for (UMeshComponent* M : Meshes)
		{
			for (int32 Slot = 0; Slot < M->GetNumMaterials(); ++Slot)
			{
				UMaterialInterface* Mat = M->GetMaterial(Slot);
				if (!Mat) continue;
				const FString N = Mat->GetName().ToLower();
				bool bHit = false;
				for (const FString& K : WindowMaterialKeys) if (!K.IsEmpty() && N.Contains(K.ToLower())) { bHit = true; break; }
				if (!bHit) continue;
				WinComps.Add(M); WinSlots.Add(Slot); WinMats.Add(Mat);
				M->SetMaterial(Slot, DarkWindow);
			}
		}
	}
}

// ---------------------------------------------------------------- cinemáticas (Sequencer)

bool ATarsisDirector::PlayCine(const TCHAR* Name, bool bIntro)
{
	ULevelSequence* Seq = LoadObject<ULevelSequence>(nullptr, *FString::Printf(TEXT("/Game/Tarsis/Cine/%s.%s"), Name, Name));
	if (!Seq) return false;
	if (CinePlayer) { CinePlayer->Stop(); CinePlayer = nullptr; }
	FMovieSceneSequencePlaybackSettings S;
	S.bDisableMovementInput = true;
	S.bDisableLookAtInput = true;
	S.bHidePlayer = true;              // oculto, los guardias no lo ven (ATarsisGuard::Visibility)
	S.bPauseAtEnd = !bIntro;           // en los finales la cámara se queda en el último plano con el texto
	ALevelSequenceActor* Actor = nullptr;
	CinePlayer = ULevelSequencePlayer::CreateLevelSequencePlayer(GetWorld(), Seq, S, Actor);
	if (!CinePlayer) return false;
	CinePlayer->OnFinished.AddDynamic(this, &ATarsisDirector::OnCineFinished);
	bCine = true;
	bCineIntro = bIntro;
	CinePlayer->Play();
	if (bIntro)
	{
		ShowMessage(Tx(TEXT("titulo"), TEXT("LOST HORIZON: DE PROFUNDIS\nMision 1 - Tarsis\nUna base en la marisma. Esta noche, el expediente LH-07 sale de ahi contigo.\n\n(E o Espacio para saltar)")), 30.0f);
	}
	return true;
}

void ATarsisDirector::SkipCine()
{
	if (!bCine || !CinePlayer) return;
	if (!bCineIntro) return;   // los finales no se saltan: es la pantalla final
	CinePlayer->Stop();        // Stop no lanza OnFinished: se cierra a mano
	OnCineFinished();
}

void ATarsisDirector::OnCineFinished()
{
	if (!bCine) return;
	if (!bCineIntro) return;   // final: se queda en el último plano (bPauseAtEnd)
	bCine = false;
	if (CinePlayer) { CinePlayer->Stop(); CinePlayer = nullptr; }
	MessageT = 0.0f;
	IntroText();
}

// ---------------------------------------------------------------- barrera del control de salida

void ATarsisDirector::SetupBarrier()
{
	const FRotator R(0.0f, ExitBarrierYaw, 0.0f);
	BarrierPost = AddBlock(ExitBarrierLoc + FVector(0.0f, 0.0f, 55.0f), FVector(0.18f, 0.18f, 1.1f), FLinearColor(0.15f, 0.15f, 0.15f), false);
	BarrierArm = AddBlock(ExitBarrierLoc, FVector(ExitBarrierLength / 100.0f, 0.08f, 0.08f), FLinearColor(0.75f, 0.08f, 0.06f), false);   // sin colisión: no corta la salida
	BarrierTick(0.0f);
	// farol de la garita: el control es un sitio iluminado y vigilado (se cruza por la sombra) y se ve en el final.
	// Es un ALight del nivel, así que cuenta para LightAt y se apaga con el generador.
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	const FVector LampLoc = ExitBarrierLoc + R.RotateVector(FVector(ExitBarrierLength * 0.4f, -60.0f, 0.0f)) + FVector(0.0f, 0.0f, 380.0f);
	GateLamp = GetWorld()->SpawnActor<ASpotLight>(LampLoc, FRotator(-90.0f, 0.0f, 0.0f), P);
	if (GateLamp)
	{
		if (USceneComponent* Root = GateLamp->GetRootComponent()) Root->SetMobility(EComponentMobility::Movable);
		GateLamp->SetActorRotation(FRotator(-90.0f, 0.0f, 0.0f));   // el giro del SpawnActor no se aplica sobre la luz estática: se fija ya móvil
		GateLamp->Tags.Add(FName(TEXT("luz_fuerte")));               // para el sigilo cuenta 3000 lm; se pinta con 300 (tanda 25)
		if (USpotLightComponent* L = Cast<USpotLightComponent>(GateLamp->GetLightComponent()))
		{
			L->SetIntensityUnits(ELightUnits::Lumens);
			L->SetIntensity(300.0f);
			L->SetAttenuationRadius(1500.0f);
			L->SetOuterConeAngle(55.0f);
			L->SetInnerConeAngle(18.0f);                             // del centro al borde, sin escalón
			L->SetLightColor(FLinearColor(1.0f, 0.78f, 0.5f));
			L->SetCastShadows(false);
			L->SetVolumetricScatteringIntensity(1.5f);
		}
	}
}

void ATarsisDirector::BarrierTick(float DeltaSeconds)
{
	if (!BarrierArm) return;
	// sube en el final por la salida y cuando pasa el camión; detrás del camión vuelve a bajar
	BarrierT = FMath::FInterpConstantTo(BarrierT, BarrierTarget, DeltaSeconds, 1.0f / 2.5f);
	const float Pitch = 80.0f * FMath::SmoothStep(0.0f, 1.0f, BarrierT);
	const FRotator R(Pitch, ExitBarrierYaw, 0.0f);
	const FVector Pivot = ExitBarrierLoc + FVector(0.0f, 0.0f, 100.0f);
	BarrierArm->SetWorldLocationAndRotation(Pivot + R.RotateVector(FVector(ExitBarrierLength * 0.5f, 0.0f, 0.0f)), R);
}

// ---------------------------------------------------------------- camión de suministros y portón de entrada (tanda 21)
// El camión es un decorado que se mueve (sin física): sus piezas se colocan cada fotograma a lo largo del eje del camino.
// Lo que da al juego: sus faros alumbran lo que tiene delante (cuentan para LightAt como cualquier luz del nivel), su caja
// tapa la vista de los guardias, el portón de entrada y la barrera se abren a su paso, y si el conductor te ve en el haz o
// le cortas el paso toca el claxon y los guardias de cerca vienen a mirar.

void ATarsisDirector::SetupTruck()
{
	TArray<AActor*> Found;
	UGameplayStatics::GetAllActorsWithTag(this, FName(TEXT("hoja_entrada")), Found);
	for (AActor* A : Found) { if (A) EntryLeaf.Add(A); }
	Found.Reset();
	UGameplayStatics::GetAllActorsWithTag(this, FName(TEXT("camion")), Found);
	for (AActor* A : Found) { if (A && !A->IsA<ALight>()) TruckParts.Add(A); }
	if (TruckParts.Num() == 0) return;
	FActorSpawnParameters P;
	P.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	// tanda 26: dos faros con el haz de cruce de un camión de los 80 (perfil IES propio), cristal encendido y destello.
	// Entre los dos pintan TruckLampLumens y cuentan para el sigilo lo que contaba la luz única; solo uno da sombra
	UTextureLightProfile* Profile = TruckIESPath.IsEmpty() ? nullptr : LoadObject<UTextureLightProfile>(nullptr, *TruckIESPath, nullptr, LOAD_NoWarn | LOAD_Quiet);
	UStaticMesh* Sphere = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	UMaterialInterface* LensMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Tarsis/Materiales/MI_Faro_Cristal.MI_Faro_Cristal"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	UMaterialInterface* GlowMat = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/Tarsis/Materiales/MI_Halo_Faro.MI_Halo_Faro"), nullptr, LOAD_NoWarn | LOAD_Quiet);
	for (int32 i = 0; i < 2; ++i)
	{
		ASpotLight* Lamp = GetWorld()->SpawnActor<ASpotLight>(TruckStart, FRotator(TruckLampPitch, 0.0f, TruckLampRoll), P);
		(i == 0 ? TruckLamp : TruckLamp2) = Lamp;
		if (!Lamp) continue;
		Lamp->Tags.Add(FName(TEXT("camion")));
		Lamp->Tags.Add(FName(TEXT("luz_fuerte")));   // lo que se pinta; para el sigilo, diez veces más
		if (USceneComponent* Root = Lamp->GetRootComponent()) Root->SetMobility(EComponentMobility::Movable);
		if (USpotLightComponent* L = Cast<USpotLightComponent>(Lamp->GetLightComponent()))
		{
			L->SetIntensityUnits(ELightUnits::Lumens);
			// ajuste 26b: lo que se pinta (TruckLampPaint) va aparte de lo que cuenta para el sigilo, que es lo de siempre
			L->SetIntensity(TruckLampLumens * 0.5f * TruckLampPaint);
			ATarsisGuard::SetStealthLumens(Lamp, TruckLampLumens * 0.5f);
			L->SetAttenuationRadius(3800.0f);
			L->SetOuterConeAngle(30.0f);
			L->SetInnerConeAngle(14.0f);
			L->SetLightColor(FLinearColor(1.0f, 0.88f, 0.66f));
			L->SetCastShadows(bTruckShadows && i == 0);
			L->SetVolumetricScatteringIntensity(5.0f);   // dos haces en la lluvia: cada uno la mitad que el único de antes
			L->SetSourceRadius(8.0f);
			if (Profile) { L->SetIESTexture(Profile); L->SetUseIESBrightness(false); ++TruckProfiles; }
		}
		// cristal (una lenteja encendida, pegada a la calandra) y destello (esfera aditiva, como los de las farolas)
		struct FGlow { UMaterialInterface* Mat; float Size; float Flat; float Back; };
		const FGlow Glows[2] = { { LensMat, TruckLensSize, 0.35f, -13.0f }, { GlowMat, TruckGlowSize, 1.0f, -8.0f } };
		for (const FGlow& G : Glows)
		{
			if (!Sphere || !G.Mat || G.Size <= 0.0f) continue;
			UStaticMeshComponent* M = NewObject<UStaticMeshComponent>(Lamp);
			M->SetMobility(EComponentMobility::Movable);
			M->SetStaticMesh(Sphere);
			M->SetMaterial(0, G.Mat);
			M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
			M->SetCastShadow(false);
			M->bAffectDynamicIndirectLighting = false;
			M->bAffectDistanceFieldLighting = false;
			M->SetupAttachment(Lamp->GetRootComponent());
			M->SetRelativeLocation(FVector(G.Back, 0.0f, 0.0f));
			M->SetRelativeScale3D(FVector(G.Size * G.Flat, G.Size, G.Size) / 100.0f);
			M->RegisterComponent();
			TruckGlows.Add(M);
		}
	}
	if (USoundBase* S = Sfx(TEXT("camion_motor")))
	{
		if (USoundWave* W = Cast<USoundWave>(S)) W->bLooping = true;
		// se le oye venir desde lejos (unos 50 m), no como los pasos
		TruckAtten = NewObject<USoundAttenuation>(this);
		TruckAtten->Attenuation.bAttenuate = true;
		TruckAtten->Attenuation.bSpatialize = true;
		TruckAtten->Attenuation.AttenuationShape = EAttenuationShape::Sphere;
		TruckAtten->Attenuation.AttenuationShapeExtents = FVector(350.0f, 0.0f, 0.0f);
		TruckAtten->Attenuation.FalloffDistance = 5000.0f;
		TruckAudio = UGameplayStatics::SpawnSoundAtLocation(this, S, TruckStart, FRotator::ZeroRotator, 0.9f, 1.0f, 0.0f, TruckAtten, nullptr, false);
		if (TruckAudio) TruckAudio->Stop();
	}
	TruckReset(TruckFirstDelay);
}

FIntVector ATarsisDirector::TruckLampCounts() const
{
	return FIntVector((TruckLamp ? 1 : 0) + (TruckLamp2 ? 1 : 0), TruckProfiles, TruckGlows.Num());
}

void ATarsisDirector::TruckShow(bool bShow)
{
	for (AActor* A : TruckParts)
	{
		if (!A) continue;
		A->SetActorHiddenInGame(!bShow);
		A->SetActorEnableCollision(bShow);
	}
	for (ASpotLight* Lamp : { TruckLamp.Get(), TruckLamp2.Get() })
	{
		if (Lamp && Lamp->GetLightComponent()) Lamp->GetLightComponent()->SetVisibility(bShow);
	}
	for (UStaticMeshComponent* M : TruckGlows) { if (M) M->SetVisibility(bShow); }
	if (TruckAudio)
	{
		if (bShow && !TruckAudio->IsPlaying()) TruckAudio->Play();
		else if (!bShow && TruckAudio->IsPlaying()) TruckAudio->Stop();
	}
}

void ATarsisDirector::TruckPlace()
{
	const FVector L(TruckX, TruckStart.Y, TruckStart.Z);
	for (AActor* A : TruckParts)
	{
		if (A) A->SetActorLocation(L, false, nullptr, ETeleportType::TeleportPhysics);
	}
	// los dos faros, delante de la calandra (la malla no les hace sombra) y algo hacia el suelo
	const FRotator LampRot(TruckLampPitch, 0.0f, TruckLampRoll);
	if (TruckLamp) TruckLamp->SetActorLocationAndRotation(L + FVector(212.0f, TruckLampSpread, 122.0f), LampRot, false, nullptr, ETeleportType::TeleportPhysics);
	if (TruckLamp2) TruckLamp2->SetActorLocationAndRotation(L + FVector(212.0f, -TruckLampSpread, 122.0f), LampRot, false, nullptr, ETeleportType::TeleportPhysics);
	if (TruckAudio)
	{
		TruckAudio->SetWorldLocation(L + FVector(120.0f, 0.0f, 130.0f));
		TruckAudio->SetPitchMultiplier(0.82f + 0.45f * FMath::Clamp(TruckV / FMath::Max(1.0f, TruckSpeedOut), 0.0f, 1.0f));
	}
	RidePlace();
}

void ATarsisDirector::TruckReset(float Wait)
{
	// si ibas dentro, te deja donde esté (acabada la misión no: sigues en la caja hasta que cargues la partida)
	if (bRiding && !bDone) LeaveTruck(true);
	if (TruckInspector) TruckInspector->EndErrand();
	TruckInspector = nullptr;
	TruckCheck = 0;
	TruckCheckT = 0.0f;
	bTruckCalled = false;
	TruckState = 0;
	TruckT = Wait;
	TruckX = TruckStart.X;
	TruckV = 0.0f;
	TruckWaitT = TruckSeenT = TruckBlockT = 0.0f;
	bTruckStayed = false;
	bEntryOpened = bEntryAsked = false;
	TruckStayT = 0.0f;
	EntryGateTarget = 0.0f;
	bEntryGateShut = false;
	if (!bDone) BarrierTarget = 0.0f;
	TruckShow(false);
	TruckPlace();
}

void ATarsisDirector::TruckHorn(const FVector& Where, int32 Why)
{
	TruckHornT = 14.0f;
	++TruckHorns;
	const FVector L(TruckX, TruckStart.Y, TruckStart.Z + 150.0f);
	if (USoundBase* S = Sfx(TEXT("claxon"))) UGameplayStatics::PlaySoundAtLocation(this, S, L, 1.0f, 1.0f, 0.0f, TruckAtten ? TruckAtten.Get() : Atten.Get());
	// el claxon se oye en media base: los guardias de a pie que estén a menos de 45 m van a ver qué pasa
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->bTowerSentry || It->bAlly || It->State == ETarsisGuardState::Down) continue;
		if (FVector::Dist2D(It->GetActorLocation(), L) < 4500.0f) It->HearNoise(Where);
	}
	if (Why == 0) ShowMessage(Tx(TEXT("camion_visto"), TEXT("TE HA VISTO EL CAMION\nEstabas en la luz de sus faros. El conductor toca el claxon y los guardias de cerca vienen a mirar.")), 4.0f);
	else if (Why == 1) ShowMessage(Tx(TEXT("camion_paso"), TEXT("ESTAS EN MEDIO DEL CAMINO\nEl camion frena y toca el claxon. Los guardias de cerca vienen a mirar.")), 4.0f);
}

void ATarsisDirector::TruckTick(float DeltaSeconds)
{
	// hoja del portón de entrada: corre por su carril hacia el sur y vuelve
	if (EntryLeaf.Num() > 0 && !FMath::IsNearlyEqual(EntryGateT, EntryGateTarget))
	{
		EntryGateT = FMath::FInterpConstantTo(EntryGateT, EntryGateTarget, DeltaSeconds, 1.0f / 5.0f);
		const FVector Off = EntryGateSlide * FMath::SmoothStep(0.0f, 1.0f, EntryGateT);
		for (AActor* A : EntryLeaf)
		{
			if (A) A->SetActorLocation(Off, false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
	if (TruckParts.Num() == 0) return;
	if (!bTruck)
	{
		// apagado a media pasada (las pruebas y la medida): desaparece y vuelve a esperar fuera
		if (TruckState != 0) TruckReset(TruckInterval);
		return;
	}
	if (TruckHornT > 0.0f) TruckHornT -= DeltaSeconds;
	if (TruckState == 0)
	{
		if (bCine || bDone) return;
		TruckT -= DeltaSeconds;
		if (TruckT > 0.0f) return;
		TruckState = 1;
		TruckX = TruckStart.X;
		TruckV = TruckSpeedOut;
		TruckShow(true);
		Teach(TEXT("ensena_camion"), TEXT("VIENE UN CAMION\nEntra por el porton del oeste y cruza la base por el camino. Sus faros alumbran lo que tiene delante; detras de el, todo queda a oscuras."), {}, 5.0f);
	}
	const FVector Loc(TruckX, TruckStart.Y, TruckStart.Z);
	float Want = 0.0f;
	float StopX = TruckEndX;
	switch (TruckState)
	{
	case 1:
		Want = TruckSpeedOut;
		StopX = TruckGateStopX;
		break;
	case 2:
		TruckWaitT += DeltaSeconds;
		StopX = TruckGateStopX;
		// al pasar a 3 la parada es la del control: con la del portón (Left ~ 0) saltaba enseguida a 4 y levantaba la barrera
		// del control con el camión aún en el portón de entrada
		// tanda 40: control tambien al entrar. El centinela de la garita pide los papeles y hasta que no pasan
		// TruckEntryPapers segundos la hoja no corre
		if (!bEntryOpened)
		{
			ATarsisGuard* Gate = nullptr;
			float GateD = 2500.0f;
			for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
			{
				if (It->bTowerSentry || It->bAlly || It->State == ETarsisGuardState::Down || It->IsStunned()) continue;
				const float Dg = FVector::Dist2D(It->GetActorLocation(), EntryGateLoc);
				if (Dg < GateD) { GateD = Dg; Gate = *It; }
			}
			if (!bEntryAsked && TruckWaitT > 1.0f && TruckEntryPapers > 0.0f)
			{
				bEntryAsked = true;
				++TruckEntryChecks;
				if (Gate) GuardSay(Gate, TEXT("papeles"));
			}
			if (TruckWaitT > TruckEntryPapers)
			{
				bEntryOpened = true;
				TruckWaitT = 0.0f;
				EntryGateTarget = 1.0f;
				bEntryGateShut = false;
				PlaySfx(TEXT("porton"), EntryGateLoc, 1.0f);
				if (Gate && bEntryAsked) GuardSay(Gate, TEXT("pase"));
			}
			break;
		}
		if (EntryGateT > 0.98f && TruckWaitT > 1.5f) { TruckState = 3; TruckWaitT = 0.0f; StopX = TruckStopX(); }
		break;
	case 3:
		Want = TruckSpeed;
		StopX = TruckStopX();
		// con la trasera ya dentro, la hoja se cierra detrás
		if (!bEntryGateShut && TruckX > EntryGateLoc.X + 520.0f)
		{
			bEntryGateShut = true;
			EntryGateTarget = 0.0f;
			PlaySfx(TEXT("porton"), EntryGateLoc, 1.0f);
		}
		break;
	case 6:
		StopX = TruckStayX;
		TruckStayT += DeltaSeconds;
		if (TruckStayT > TruckStaySeconds)
		{
			bTruckStayed = true;
			TruckState = 3;
			StopX = TruckBarrierStopX;
		}
		break;
	case 4:
		TruckWaitT += DeltaSeconds;
		StopX = TruckBarrierStopX;
		// en el control alguien viene a la cabina a mirar los papeles y levanta la barrera
		TruckControlTick(DeltaSeconds);
		break;
	default:
		Want = TruckX < ExitLoc.X + 300.0f ? TruckSpeed : TruckSpeedOut;
		if (!bDone && BarrierTarget > 0.0f && TruckX > ExitBarrierLoc.X + 700.0f)
		{
			BarrierTarget = 0.0f;
			PlaySfx(TEXT("barrera"), ExitBarrierLoc + FVector(0.0f, 0.0f, 100.0f));
		}
		break;
	}
	// alguien delante (tú, un guardia o un cuerpo en el suelo): frena en seco y, si no se aparta, claxon
	bool bBlocked = false, bBlockedByPlayer = false;
	FVector BlockLoc = Loc;
	APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
	if (Want > 0.0f)
	{
		const float Ahead = 230.0f + 260.0f + TruckV * 0.7f;
		for (TActorIterator<ACharacter> It(GetWorld()); It; ++It)
		{
			const FVector R = It->GetActorLocation() - Loc;
			if (R.X > 150.0f && R.X < Ahead && FMath::Abs(R.Y) < 175.0f && FMath::Abs(R.Z) < 320.0f)
			{
				bBlocked = true;
				BlockLoc = It->GetActorLocation();
				if (*It == Player) bBlockedByPlayer = true;
			}
		}
	}
	if (bBlocked)
	{
		Want = 0.0f;
		TruckBlockT += DeltaSeconds;
		if (TruckBlockT > (bBlockedByPlayer ? 1.2f : 3.5f) && TruckHornT <= 0.0f && !bDone && !bCine) TruckHorn(BlockLoc, bBlockedByPlayer ? 1 : 2);
	}
	else TruckBlockT = 0.0f;
	// frena a tiempo para parar justo en su sitio
	const float Left = StopX - TruckX;
	if (TruckState != 5 && Want > 0.0f) Want = FMath::Min(Want, FMath::Sqrt(2.0f * 240.0f * FMath::Max(0.0f, Left)) + 25.0f);
	const float PrevX = TruckX, PrevV = TruckV;
	TruckV = FMath::FInterpConstantTo(TruckV, Want, DeltaSeconds, Want > TruckV ? 170.0f : (bBlocked ? 900.0f : 420.0f));
	TruckX += TruckV * DeltaSeconds;
	TruckFeel(PrevX, PrevV, DeltaSeconds);
	if (TruckState == 1 && Left < 10.0f)
	{
		// ante el portón: se para, la hoja empieza a correr
		TruckState = 2;
		TruckV = 0.0f;
		TruckWaitT = 0.0f;
		bEntryOpened = false;
		bEntryAsked = false;
	}
	else if (TruckState == 3 && Left < 10.0f && !bTruckStayed && TruckStaySeconds > 0.0f)
	{
		// tanda 40: para ante el hangar a descargar; al rato arranca y sigue hasta el control de salida
		TruckState = 6;
		TruckV = 0.0f;
		TruckStayT = 0.0f;
		++TruckStays;
		Teach(TEXT("ensena_camion_hangar"), TEXT("EL CAMION PARA EN EL HANGAR\nSe queda un rato descargando y luego sigue hasta el control de salida. Parado, se sube a la caja por detras."), {}, 5.0f);
	}
	else if (TruckState == 3 && Left < 10.0f)
	{
		TruckState = 4;
		TruckV = 0.0f;
		TruckWaitT = 0.0f;
		TruckCheck = 0;
		TruckCheckT = 0.0f;
		bTruckCalled = false;
		TruckInspector = nullptr;
	}
	else if (TruckState == 5 && TruckX >= TruckEndX)
	{
		if (bRiding && bDone)
		{
			// final en la caja del camión: se queda al fondo del terraplén, con la base a lo lejos, hasta que cargues la partida
			TruckX = TruckEndX;
			TruckV = 0.0f;
			TruckPlace();
			return;
		}
		++TruckPasses;
		TruckReset(TruckInterval);
		return;
	}
	TruckPlace();
	// el conductor: ve a quien esté de pie en el haz de los faros, sin nada por medio (agachado, solo a la mitad de distancia)
	if (TruckSeenT > 0.0f && TruckHornT > 0.0f) TruckSeenT = 0.0f;
	ACharacter* PC = Cast<ACharacter>(Player);
	bool bSeen = false;
	if (PC && !bDone && !bCine && !bCapturing && !bHiding && !bRiding && !PC->IsHidden() && !BoxCloaked() && !bUniformNow && TruckHornT <= 0.0f)
	{
		const FVector Eye = FVector(TruckX + 235.0f, TruckStart.Y, TruckStart.Z + 165.0f);
		const FVector To = PC->GetActorLocation() - Eye;
		const float Reach = PC->bIsCrouched ? TruckSight * 0.5f : TruckSight;
		if (To.X > 120.0f && To.Size2D() < Reach && FMath::Abs(To.Y) < To.X * 0.34f)
		{
			FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisCamion), true);
			Q.AddIgnoredActor(PC);
			for (AActor* A : TruckParts) { if (A) Q.AddIgnoredActor(A); }
			FHitResult Hit;
			bSeen = !GetWorld()->LineTraceSingleByChannel(Hit, Eye, PC->GetActorLocation() + FVector(0.0f, 0.0f, 30.0f), ECC_Visibility, Q);
		}
	}
	TruckSeenT = bSeen ? TruckSeenT + DeltaSeconds : FMath::Max(0.0f, TruckSeenT - DeltaSeconds * 0.5f);
	if (bSeen && TruckSeenT > 0.8f && !bBlockedByPlayer) TruckHorn(PC->GetActorLocation(), 0);
}

// ---------------------------------------------------------------- control de salida y viaje en la caja del camión (tanda 22)

FString ATarsisDirector::TruckInspectorName() const
{
	return TruckInspector ? TruckInspector->GuardName : FString();
}

void ATarsisDirector::TruckControlTick(float DeltaSeconds)
{
	// En el control nadie abre desde lejos: el guardia de ronda más cercano va hasta la puerta del conductor (lado norte),
	// mira los papeles y levanta la barrera. Con la base en guardia, además rodea el camión y mira la caja: si vas dentro,
	// te saca. Si no hay nadie que pueda ir (dormido, lejos, ocupado), el conductor toca el claxon (y los que lo oyen se
	// acercan) y, si ni así, se baja y levanta la barrera él.
	TruckCheckT += DeltaSeconds;
	const FVector Cab(TruckX + 62.0f, TruckStart.Y - 185.0f, TruckStart.Z);
	const FVector CabFace(TruckX + 62.0f, TruckStart.Y, TruckStart.Z);
	const FVector Tail(TruckX - 320.0f, TruckStart.Y - 140.0f, TruckStart.Z);
	const FVector TailFace(TruckX - 150.0f, TruckStart.Y, TruckStart.Z);
	// Keep: segundos que el guardia se queda todavía en su sitio (acabando el gesto) antes de volver a la ronda
	auto Lift = [this](float Keep = 0.0f)
	{
		if (TruckInspector)
		{
			if (Keep > 0.0f) TruckInspector->EndErrandIn(Keep);
			else TruckInspector->EndErrand();
		}
		TruckCheck = 5;
		TruckCheckT = 0.0f;
		if (BarrierTarget < 1.0f)
		{
			BarrierTarget = 1.0f;
			PlaySfx(TEXT("barrera"), ExitBarrierLoc + FVector(0.0f, 0.0f, 100.0f));
		}
	};
	ATarsisGuard* G = TruckInspector;
	// el que venía ha dejado el recado (te ha visto, ha oído algo, lo han tumbado): se espera a otro
	if (TruckCheck >= 1 && TruckCheck <= 4 && (!G || !G->IsOnErrand()))
	{
		TruckInspector = nullptr;
		G = nullptr;
		TruckCheck = 0;
		TruckCheckT = 0.0f;
	}
	// mientras dura el control lleva el bastón encendido (tanda 25); al dar paso hace la señal con él y lo guarda
	if (G && TruckCheck >= 1 && TruckCheck <= 4) G->HoldBaton(0.6f);
	switch (TruckCheck)
	{
	case 0:
	{
		ATarsisGuard* Best = nullptr;
		float BestD = 3000.0f;
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (It->bTowerSentry || It->bAlly || It->HoldT > 0.0f || It->IsStunned() || It->IsRepairing() || It->IsCheckingBody()) continue;
			if (It->State != ETarsisGuardState::Patrol && It->State != ETarsisGuardState::Return) continue;
			const float D = FVector::Dist2D(It->GetActorLocation(), Cab);
			if (D < BestD) { BestD = D; Best = *It; }
		}
		if (Best && Best->Errand(Cab, CabFace, 45.0f))
		{
			Best->PlayGesture(TEXT("alto"), 3.2f);   // va hacia la cabina con el bastón luminoso en alto
			Best->HoldBaton(4.0f);
			TruckInspector = Best;
			TruckCheck = 1;
			TruckCheckT = 0.0f;
			break;
		}
		if (TruckWaitT > TruckHornWait && !bTruckCalled && !bDone && !bCine)
		{
			bTruckCalled = true;
			TruckHorn(Cab, 3);
			Teach(TEXT("camion_nadie_abre"), TEXT("NADIE ABRE AL CAMION\nEn el control no hay quien mire los papeles. El conductor toca el claxon: los guardias de cerca vienen a ver."), {}, 4.5f);
		}
		if (TruckWaitT > TruckSelfWait) Lift();
		break;
	}
	case 1:
		if (G->AtErrand())
		{
			TruckCheck = 2;
			TruckCheckT = 0.0f;
			++TruckChecks;
			GuardSay(G, TEXT("papeles"));
		}
		else if (TruckCheckT > 20.0f) Lift();   // no llega (algo le corta el paso): da paso desde donde está
		break;
	case 2:
		// tiende la mano, coge los papeles y los mira (el gesto se renueva cada tick: si deja el recado, se deshace solo)
		G->PlayGesture(TruckCheckT < 1.3f ? TEXT("papeles") : TEXT("leer"), 0.4f);
		if (TruckCheckT < TruckPapersTime) break;
		if (BaseState() >= 1 && G->Errand(Tail, TailFace, 30.0f))
		{
			TruckCheck = 3;
			TruckCheckT = 0.0f;
			++TruckSearches;
			GuardSay(G, TEXT("registro"));
		}
		else
		{
			// da paso con el brazo hacia el portón y se queda un momento viendo arrancar el camión
			GuardSay(G, TEXT("pase"));
			G->PlayGesture(TEXT("pase"), 2.4f, ExitLoc);
			G->HoldBaton(2.6f);
			Lift(2.2f);
		}
		break;
	case 3:
		if (G->AtErrand()) { TruckCheck = 4; TruckCheckT = 0.0f; G->PlayGesture(TEXT("lona"), 1.5f); }
		else if (TruckCheckT > 14.0f) Lift();
		break;
	case 4:
		if (TruckCheckT < 1.3f) break;
		if (bRiding && bBoxOn && !bCapturing && !bDone)
		{
			// tanda 40: levanta la lona y ve una caja de carton entre las demas
			++TruckBoxPasses;
			GuardSay(G, TEXT("nadie"));
			G->PlayGesture(TEXT("pase"), 2.2f, ExitLoc);
			G->HoldBaton(2.4f);
			ShowMessage(Tx(TEXT("caja_registro"), TEXT("LEVANTA LA LONA\nCajas. Una mas no le dice nada.")), 4.0f);
			Lift(2.0f);
			break;
		}
		if (bRiding && !bCapturing && !bDone)
		{
			BeginCapture(G);       // te baja de la caja (LeaveTruck) y la escena de siempre
			bCaptureTruck = true;
		}
		else
		{
			GuardSay(G, TEXT("nadie"));
			G->PlayGesture(TEXT("pase"), 2.2f, ExitLoc);
			G->HoldBaton(2.4f);
			Lift(2.0f);
			break;
		}
		Lift();
		break;
	default:
		if (BarrierT > 0.95f)
		{
			if (bRiding && !bFile && !bCapturing)
			{
				// sin el expediente no te vas: te bajas antes de que arranque
				LeaveTruck(true);
				ShowMessage(Tx(TEXT("camion_sin_expediente"), TEXT("TE BAJAS DEL CAMION\nSin el expediente no puedes irte de Tarsis. El camion arranca: apartate de la luz del control.")), 5.0f);
			}
			TruckState = 5;
			TruckWaitT = 0.0f;
		}
		break;
	}
}

bool ATarsisDirector::CanBoardTruck() const
{
	if (!bTruck || bRiding || bHiding || bCapturing || bDone || bCine || bChoice || bKeypad || Dragged) return false;
	if (TruckParts.Num() == 0 || TruckState < 3 || TruckState > 6) return false;
	if (TruckState == 5 && !bFile) return false;        // sin el expediente no te vas
	if (TruckV > TruckSpeed + 30.0f) return false;      // ya va lanzado
	// la trasera, dentro de la base: pasado el portón de entrada y antes del punto de salida
	const float TailX = TruckX - 200.0f;
	if (TailX < EntryGateLoc.X + 60.0f || TailX > ExitLoc.X) return false;
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P) return false;
	const FVector R = P->GetActorLocation() - FVector(TailX, TruckStart.Y, TruckStart.Z);
	return R.X > -200.0f && R.X < 50.0f && FMath::Abs(R.Y) < 140.0f && R.Z > -50.0f && R.Z < 260.0f;
}

void ATarsisDirector::BoardTruck()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!C || !PC || !CanBoardTruck()) return;
	if (bBinoculars) ToggleBinoculars();
	SprintOff();
	bKeypad = false;
	// ¿te han visto subir? Como en las taquillas: un guardia en alerta que te tiene a la vista o te acaba de perder
	bRideSeen = false;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Alert && !It->bTowerSentry && It->UnseenT < 1.5f) bRideSeen = true;
	}
	bRiding = true;
	++TruckRides;
	if (C->bIsCrouched) C->UnCrouch();
	C->SetActorEnableCollision(false);
	C->GetCharacterMovement()->StopMovementImmediately();
	C->GetCharacterMovement()->DisableMovement();
	C->SetActorHiddenInGame(true);   // los guardias no ven a un actor oculto (ATarsisGuard::Visibility)
	PC->SetControlRotation(FRotator(-4.0f, 180.0f, 0.0f));   // sentado al fondo, mirando por la trasera abierta
	RidePlace();
	PlaySfx(TEXT("camion_subir"), TruckLocation() + FVector(-190.0f, 0.0f, 120.0f), 0.8f);
	if (bRideSeen) ShowMessage(Tx(TEXT("camion_caja_vista"), TEXT("TE HAN VISTO SUBIR\nEl que te persigue sabe donde estas: si llega a la trasera, te saca. E para bajar.")), 4.0f);
	else if (!bFile) Teach(TEXT("ensena_camion_caja"), TEXT("EN LA CAJA DEL CAMION\nBajo la lona no te ven. En el control miran los papeles del conductor; con la base en guardia registran tambien la caja.\nSin el expediente no puedes irte: bajate (E) antes de que salga."), {}, 7.0f);
	else Teach(TEXT("ensena_camion_salir"), TEXT("EN LA CAJA DEL CAMION\nCon el expediente, el camion te saca de la base. En el control miran los papeles del conductor; con la base en guardia registran tambien la caja."), {}, 7.0f);
}

void ATarsisDirector::RidePlace()
{
	if (!bRiding) return;
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C) return;
	// los ojos, a 82 cm del suelo de la caja (que queda a 113 cm del camino) y a 75 cm del portalón, en el eje del camión.
	// Se coloca el actor de modo que su cámara caiga ahí, esté donde esté respecto a la cápsula
	float CamUp = 64.0f;
	if (const UCameraComponent* Cam = C->FindComponentByClass<UCameraComponent>()) CamUp = Cam->GetComponentLocation().Z - C->GetActorLocation().Z;
	// el traqueteo: con el camión en marcha la vista tiembla un poco. Desde la tanda 23 se le suman el temblor del motor
	// al ralentí (parado en el control también se nota que el camión está vivo), el golpe de cada junta de la losa y la
	// inercia del cuerpo al frenar y al arrancar (TruckFeel)
	const float K = FMath::Clamp(TruckV / FMath::Max(1.0f, TruckSpeed), 0.0f, 1.6f);
	const float T = GetWorld()->GetTimeSeconds();
	RideShake = FVector(RideLurch, FMath::Sin(T * 9.1f) * 0.5f * K, (FMath::Sin(T * 13.7f) * 0.9f + FMath::Sin(T * 23.3f) * 0.4f) * K + FMath::Sin(T * 61.0f) * 0.1f + RideKick);
	const FVector Eye = FVector(TruckX - 125.0f, TruckStart.Y, TruckStart.Z + 113.0f + 82.0f) + RideShake;
	C->SetActorLocation(Eye - FVector(0.0f, 0.0f, CamUp), false, nullptr, ETeleportType::TeleportPhysics);
	if (RideLight) RideLight->SetWorldLocation(Eye + FVector(0.0f, 0.0f, 6.0f));
}

// ---------------------------------------------------------------- la caja del camión por dentro (tanda 23)
// Lo que nota quien viaja en la caja. Cada eje que pisa una junta de la losa da un golpe: se oye también desde fuera (es
// el «ta-tac» del camión por el camino, que avisa de por dónde va) y dentro sacude la vista. El cuerpo se va hacia la
// cabina al frenar y hacia el portalón al arrancar. El mundo de fuera suena apagado por la lona, y dentro crujen las
// tablas y bate la lona. Una luz de relleno muy tenue deja ver la caja sin alumbrar nada de fuera.

void ATarsisDirector::TruckFeel(float PrevX, float PrevV, float DeltaSeconds)
{
	const float K = FMath::Clamp(TruckV / FMath::Max(1.0f, TruckSpeed), 0.0f, 1.5f);
	if (TruckJointPitch > 1.0f && TruckV > 40.0f)
	{
		// primero el eje de delante (x + 112) y luego el de atrás (x - 118), sobre el que vas sentado
		static const float Axles[2] = { 112.0f, -118.0f };
		for (int32 i = 0; i < 2; ++i)
		{
			const int32 A = FMath::FloorToInt((PrevX + Axles[i] - TruckJointPhase) / TruckJointPitch);
			const int32 B = FMath::FloorToInt((TruckX + Axles[i] - TruckJointPhase) / TruckJointPitch);
			if (A == B) continue;
			++TruckJoints;
			if (USoundBase* S = Sfx(TEXT("camion_junta")))
			{
				UGameplayStatics::PlaySoundAtLocation(this, S, FVector(TruckX + Axles[i], TruckStart.Y, TruckStart.Z + 50.0f), (bRiding ? 0.8f : 0.5f) * FMath::Max(0.35f, K),
					FMath::FRandRange(0.93f, 1.07f), 0.0f, TruckAtten ? TruckAtten.Get() : Atten.Get());
			}
			if (bRiding) RideKickV += (i == 1 ? 34.0f : 14.0f) * FMath::Max(0.35f, K);
		}
	}
	// el golpe es un muelle amortiguado (5 Hz); el paso se acota para que un tirón de fotogramas no lo dispare
	const float Dt = FMath::Min(DeltaSeconds, 0.033f);
	const float W = 34.0f, Z = 0.32f;
	RideKickV += (-W * W * RideKick - 2.0f * Z * W * RideKickV) * Dt;
	RideKickV = FMath::Clamp(RideKickV, -120.0f, 120.0f);
	RideKick = FMath::Clamp(RideKick + RideKickV * Dt, -3.0f, 3.0f);
	// inercia: frenar (aceleración negativa) te echa hacia la cabina (+X); arrancar, hacia el portalón
	const float Acc = DeltaSeconds > KINDA_SMALL_NUMBER ? (TruckV - PrevV) / DeltaSeconds : 0.0f;
	RideLurch = FMath::FInterpTo(RideLurch, FMath::Clamp(-Acc * 0.012f, -3.0f, 7.0f), DeltaSeconds, 5.0f);
}

bool ATarsisDirector::RideLightOn() const
{
	return RideLight && RideLight->IsVisible();
}

void ATarsisDirector::RideFeelTick(float DeltaSeconds)
{
	RideMuffleK = FMath::FInterpTo(RideMuffleK, bRiding ? 1.0f : 0.0f, DeltaSeconds, 3.0f);
	if (!bRiding) { RideKick = RideKickV = RideLurch = 0.0f; RideShake = FVector::ZeroVector; }
	// luz de relleno: se crea la primera vez que subes; pertenece al director (no es un ALight: no cuenta para LightAt)
	const bool bLight = bRiding && RideFillLumens > 0.0f;
	if (bLight && !RideLight)
	{
		RideLight = NewObject<UPointLightComponent>(this);
		RideLight->SetMobility(EComponentMobility::Movable);
		RideLight->SetWorldLocation(TruckLocation() + FVector(-125.0f, 0.0f, 201.0f));
		RideLight->SetIntensityUnits(ELightUnits::Lumens);
		RideLight->SetAttenuationRadius(300.0f);
		RideLight->SetSourceRadius(12.0f);
		RideLight->SetLightColor(FLinearColor(0.7f, 0.82f, 1.0f));
		RideLight->SetCastShadows(false);
		RideLight->SetVolumetricScatteringIntensity(0.0f);
		RideLight->RegisterComponent();
	}
	if (RideLight)
	{
		if (bLight) RideLight->SetIntensity(RideFillLumens);
		if (RideLight->IsVisible() != bLight) RideLight->SetVisibility(bLight);
	}
	// el ambiente pierde los agudos bajo la lona (la música no: no es de este mundo); el motor se oye a través de la cabina
	const bool bLow = RideMuffleK > 0.02f;
	const float Cut = FMath::Lerp(16000.0f, 1300.0f, RideMuffleK);
	for (UAudioComponent* A : { WindComp.Get(), RainComp.Get(), CricketComp.Get(), RumbleComp.Get(), HumComp.Get() })
	{
		if (!A) continue;
		A->SetLowPassFilterEnabled(bLow);
		if (bLow) A->SetLowPassFilterFrequency(Cut);
	}
	if (TruckAudio)
	{
		TruckAudio->SetLowPassFilterEnabled(bLow);
		if (bLow) TruckAudio->SetLowPassFilterFrequency(FMath::Lerp(16000.0f, 2400.0f, RideMuffleK));
	}
	// lo de dentro: tablas, lona y hebillas, más fuerte cuanto más corre el camión
	if (bLow && !RideAudio)
	{
		if (USoundBase* S = Sfx(TEXT("camion_caja")))
		{
			if (USoundWave* Wv = Cast<USoundWave>(S)) Wv->bLooping = true;
			RideAudio = UGameplayStatics::SpawnSound2D(this, S, 0.001f, 1.0f, 0.0f, nullptr, false, false);
		}
	}
	if (RideAudio)
	{
		const float V = RideMuffleK * FMath::Clamp(TruckV / FMath::Max(1.0f, TruckSpeed), 0.0f, 1.4f) * 0.5f;
		RideAudio->SetVolumeMultiplier(FMath::Max(0.001f, V));
		if (bLow && !RideAudio->IsPlaying()) RideAudio->Play();
		else if (!bLow && RideAudio->IsPlaying()) RideAudio->Stop();
	}
}

bool ATarsisDirector::LeaveTruck(bool bForced)
{
	if (!bRiding) return false;
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C)
	{
		bRiding = false;
		return false;
	}
	const float Half = C->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const float Rad = C->GetCapsuleComponent()->GetScaledCapsuleRadius();
	// al suelo, un paso por detrás del portalón
	FVector Spot(TruckX - 295.0f, TruckStart.Y, TruckStart.Z);
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisBajar), false);
	Q.AddIgnoredActor(C);
	for (AActor* A : TruckParts) { if (A) Q.AddIgnoredActor(A); }
	FHitResult Hit;
	if (GetWorld()->LineTraceSingleByChannel(Hit, Spot + FVector(0.0f, 0.0f, 150.0f), Spot - FVector(0.0f, 0.0f, 200.0f), ECC_Visibility, Q)) Spot.Z = Hit.ImpactPoint.Z;
	Spot.Z += Half + 2.0f;
	if (!bForced && GetWorld()->OverlapBlockingTestByChannel(Spot + FVector(0.0f, 0.0f, 6.0f), FQuat::Identity, ECC_Pawn, FCollisionShape::MakeCapsule(Rad, Half), Q))
	{
		ShowMessage(Tx(TEXT("camion_no_bajar"), TEXT("NO PUEDES BAJAR AQUI\nHay algo justo detras del camion.")), 2.0f);
		return false;
	}
	bRiding = false;
	bRideSeen = false;
	C->SetActorLocation(Spot, false, nullptr, ETeleportType::TeleportPhysics);
	C->SetActorHiddenInGame(false);
	C->SetActorEnableCollision(true);
	C->GetCharacterMovement()->SetMovementMode(MOVE_Walking);
	if (!bDone && !bCapturing)
	{
		PlaySfx(TEXT("camion_subir"), Spot, 0.7f);
		// saltar en marcha hace ruido: los que estén a menos de 10 m se vuelven a mirar
		if (TruckV > 120.0f)
		{
			for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
			{
				if (FVector::Dist(It->GetActorLocation(), Spot) < 1000.0f) It->HearNoise(Spot);
			}
		}
	}
	return true;
}

void ATarsisDirector::RideTick()
{
	if (!bRiding || !bRideSeen || bCapturing || bDone) return;
	// te vieron subir: el que te persigue llega a la trasera y te saca de la caja
	bool bAny = false;
	const FVector Tail(TruckX - 230.0f, TruckStart.Y, TruckStart.Z);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State != ETarsisGuardState::Alert || It->bTowerSentry) continue;
		bAny = true;
		if (FVector::Dist2D(It->GetActorLocation(), Tail) < 260.0f)
		{
			BeginCapture(*It);
			bCaptureTruck = true;
			return;
		}
	}
	if (!bAny) bRideSeen = false;   // ya no te persigue nadie
}

// ---------------------------------------------------------------- farol de la garita y farolas: se rompen de un disparo

// tanda 27: además del farol de la garita, cualquier farola (luz fuerte de la base) se apaga de un dardo. No vale para
// los focos de las torres (los lleva su centinela), los faros del camión ni los rellenos; «irrompible» la excluye a mano
bool ATarsisDirector::BreakableLamp(const ALight* A) const
{
	static const FName Strong(TEXT("luz_fuerte")), Truck(TEXT("camion")), Decor(TEXT("decorado")), Hard(TEXT("irrompible"));
	if (!A || A == GateLamp.Get() || !A->ActorHasTag(Strong) || A->ActorHasTag(Truck) || A->ActorHasTag(Decor) || A->ActorHasTag(Hard)) return false;
	for (TActorIterator<ATarsisGuard> G(GetWorld()); G; ++G) if (G->TowerLight.Get() == A) return false;
	return true;
}

bool ATarsisDirector::ShootLamp(const FVector& From, const FVector& Fwd, float MaxT)
{
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisFarol), true, this);
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (Pl) Q.AddIgnoredActor(Pl);
	// la luminaria más cercana que cruza la línea de tiro, sin nada en medio
	ALight* Lamp = nullptr;
	float BestT = MaxT;
	for (TActorIterator<ALight> It(GetWorld()); It; ++It)
	{
		ALight* A = *It;
		ULightComponent* L = A->GetLightComponent();
		if (!L) continue;
		const bool bGate = A == GateLamp.Get();
		if (bGate ? bLampBroken : (BrokenLights.Contains(L) || !BreakableLamp(A))) continue;
		const FVector P = A->GetActorLocation();
		const float T = FVector::DotProduct(P - From, Fwd);
		if (T < 0.0f || T > BestT || FVector::Dist(From + Fwd * T, P) > 40.0f) continue;
		FCollisionQueryParams Q2 = Q;
		Q2.AddIgnoredActor(A);
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, From, P, ECC_Visibility, Q2) && FVector::Dist(Hit.ImpactPoint, P) > 60.0f) continue;
		Lamp = A;
		BestT = T;
	}
	if (!Lamp) return false;
	ULightComponent* L = Lamp->GetLightComponent();
	const bool bGate = Lamp == GateLamp.Get();
	const FVector P = Lamp->GetActorLocation();
	if (bGate) bLampBroken = true;
	else BrokenLights.Add(L);
	L->SetVisibility(false);
	const int32 SpotIdx = bGate ? INDEX_NONE : BrokenLights.Num() - 1;
	if (!bGate) CoverLamp(Lamp);
	OffLights.Remove(L);   // si hay apagón, al volver la luz sigue roto
	PendingOff.Remove(L);
	if (StoneSnd) UGameplayStatics::PlaySoundAtLocation(this, StoneSnd, P, 1.0f, 1.6f, 0.0f, Atten);
	// dónde caen los cristales: el suelo bajo la luminaria (la de la garita, a la altura de la barrera)
	FVector Ground(P.X, P.Y, ExitBarrierLoc.Z);
	if (!bGate)
	{
		FCollisionQueryParams Q3 = Q;
		Q3.AddIgnoredActor(Lamp);
		FHitResult Floor;
		if (GetWorld()->LineTraceSingleByChannel(Floor, P, P - FVector(0.0f, 0.0f, 1500.0f), ECC_Visibility, Q3)) Ground = Floor.ImpactPoint;
		else Ground.Z = Pl ? Pl->GetActorLocation().Z : P.Z - 500.0f;
	}
	// el ruido de cristales llama al guardia más cercano, que viene a mirar
	ATarsisGuard* Best = nullptr;
	float BestD = 2500.0f;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Down || It->bTowerSentry || It->bAlly) continue;
		const float D = FVector::Dist(It->GetActorLocation(), P);
		if (D < BestD) { BestD = D; Best = *It; }
	}
	if (Best) Best->HearNoise(Ground);
	LampChecker = Best;
	CheckLamp = Lamp;
	CheckSpot = Ground;
	bLampReported = false;
	if (SpotIdx != INDEX_NONE)
	{
		BrokenSpots.SetNum(BrokenLights.Num());
		BrokenSeen.SetNum(BrokenLights.Num());
		BrokenSpots[SpotIdx] = Ground;
		BrokenSeen[SpotIdx] = false;
	}
	const FString Comes = Best ? TEXT(" ") + Tx(TEXT("farol_viene"), TEXT("{0} ha oido los cristales y viene a mirar."), { Best->GuardName }) : FString();
	if (bGate) ShowMessage(Tx(TEXT("farol_roto"), TEXT("FAROL ROTO\nEl control queda a oscuras.{0}"), { Comes }), 4.0f);
	else ShowMessage(Tx(TEXT("farola_rota"), TEXT("FAROLA ROTA\nEsta zona queda a oscuras.{0}"), { Comes }), 4.0f);
	return true;
}

// Una farola rota no pasa desapercibida: el primer guardia que pisa su charco de sombra (el que oyó los cristales u
// otro en su ronda) lo dice por radio, la base se pone en guardia un rato y él ya no guarda la linterna
void ATarsisDirector::LampsTick()
{
	for (int32 i = 0; i < BrokenLights.Num(); ++i)
	{
		if (!BrokenSeen.IsValidIndex(i) || BrokenSeen[i]) continue;
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (It->State == ETarsisGuardState::Down || It->bTowerSentry || It->bAlly) continue;
			const FVector G = It->GetActorLocation();
			if (FVector::Dist2D(G, BrokenSpots[i]) > 350.0f || FMath::Abs(G.Z - BrokenSpots[i].Z) > 300.0f) continue;
			BrokenSeen[i] = true;
			if (CheckLamp && CheckLamp->GetLightComponent() == BrokenLights[i].Get()) bLampReported = true;
			GuardSay(*It, TEXT("farola"), true);
			TensionT = FMath::Max(TensionT, 60.0f);
			It->KeepFlashlight();
			break;
		}
	}
	// tanda 28: nadie entra solo a mirar un ruido donde falta la farola. Se planta, pide apoyo y espera al más cercano
	// que esté libre; si ya tiene a alguien al lado, o hay apagón (todos llevan linterna), entra sin más
	if (BrokenLights.Num() == 0 || bPowerOff || !bBuddyRule) return;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		if (G->bTowerSentry || G->bAlly || !G->WantsDarkCheck()) continue;
		const FVector Spot = G->NoiseSpot();
		bool bDark = false;
		for (const FVector& B : BrokenSpots) if (FVector::Dist2D(B, Spot) < DarkZoneRadius) { bDark = true; break; }
		// ya está dentro de la sombra (pasaba por allí): no se queda plantado en medio
		for (const FVector& B : BrokenSpots) if (FVector::Dist2D(B, G->GetActorLocation()) < 400.0f) bDark = false;
		G->DarkChecked();
		if (!bDark) continue;
		ATarsisGuard* Best = nullptr;
		float BestD = BuddyCallRadius;
		bool bCompany = false;
		for (TActorIterator<ATarsisGuard> O(GetWorld()); O; ++O)
		{
			if (*O == G || O->State == ETarsisGuardState::Down || O->State == ETarsisGuardState::Alert || O->bTowerSentry || O->bAlly || O->IsHeld() || O->IsBusy()) continue;
			const float D = FVector::Dist(O->GetActorLocation(), G->GetActorLocation());
			if (D < 600.0f) bCompany = true;
			if (D < BestD) { BestD = D; Best = *O; }
		}
		if (bCompany) continue;
		G->WaitForBuddy(Best, Best ? BuddyWaitSeconds : BuddyWaitSeconds * 0.4f);
		++BuddyCalls;
		GuardSay(G, TEXT("apoyo"), true);
		if (Best)
		{
			TWeakObjectPtr<ATarsisGuard> W(Best);
			FTimerHandle H;
			GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateWeakLambda(this, [this, W]() { if (W.IsValid()) GuardSay(W.Get(), TEXT("voy"), true); }), 2.4f, false);
		}
	}
}

// La pantalla de la luminaria es parte de una malla fundida con brillo propio: no se puede apagar una sola. Al
// romperla se le pone delante una tapa negra sin sombra (tamaño y sitio en LampCoverScale y LampCoverOffset)
void ATarsisDirector::CoverLamp(const ALight* Lamp)
{
	if (!Lamp) return;
	const bool bPatio = Lamp->GetActorLocation().Z < LampCoverPatioZ;   // el farol del patio cuelga más bajo que la farola del camino
	UStaticMeshComponent* C = AddBlock(Lamp->GetActorLocation() + (bPatio ? LampCoverPatioOffset : LampCoverOffset), bPatio ? LampCoverPatioScale : LampCoverScale, FLinearColor(0.004f, 0.004f, 0.004f), false);
	if (C) C->SetCastShadow(false);
	LampCovers.Add(C);
}

void ATarsisDirector::RepairLamps()
{
	for (ULightComponent* L : BrokenLights)
	{
		if (!L) continue;
		if (bPowerOff) OffLights.AddUnique(L);
		else L->SetVisibility(true);
	}
	BrokenLights.Reset();
	for (UStaticMeshComponent* C : LampCovers) if (C) C->DestroyComponent();
	LampCovers.Reset();
	BrokenSpots.Reset();
	BrokenSeen.Reset();
	if (CheckLamp && CheckLamp.Get() != GateLamp.Get()) { CheckLamp = nullptr; LampChecker = nullptr; }
}

// ---------------------------------------------------------------- puntos de control y guardado

void ATarsisDirector::Checkpoint(const FString& Name)
{
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || bDone) return;
	bHasCheck = true;
	CheckLoc = P->GetActorLocation();
	CheckRot = FRotator(0.0f, P->GetControlRotation().Yaw, 0.0f);
	CheckDarts = Darts;
	CheckpointName = Name;
	CheckT = 3.0f;
	UTarsisSave* S = Cast<UTarsisSave>(UGameplayStatics::CreateSaveGameObject(UTarsisSave::StaticClass()));
	if (!S) return;
	S->Checkpoint = Name;
	S->Loc = CheckLoc;
	S->Rot = CheckRot;
	S->MissionTime = MissionTime;
	S->Captures = Captures;
	S->Darts = Darts;
	S->bKey = bKey;
	S->bJefOpen = bJefOpen;
	S->bNoteRead = bNoteRead;
	S->bVaultOpen = bVaultOpen;
	S->bFile = bFile;
	S->bLetter = bLetter;
	S->bVetKey = bVetKey;
	S->bVetOpen = bVetOpen;
	S->bRamosKnown = bRamosKnown;
	S->bLampBroken = bLampBroken;
	S->BrokenLamps.Reset();
	for (const ULightComponent* BL : BrokenLights) if (BL && BL->GetOwner()) S->BrokenLamps.Add(BL->GetOwner()->GetActorLocation());
	S->CodecTaken = CodecTaken;
	S->Weather = Weather;
	S->Flags = FlagList();
	bHasSave = UGameplayStatics::SaveGameToSlot(S, TEXT("TarsisPartida"), 0) || bHasSave;
}

bool ATarsisDirector::LoadCheckpoint()
{
	UTarsisSave* S = Cast<UTarsisSave>(UGameplayStatics::LoadGameFromSlot(TEXT("TarsisPartida"), 0));
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!S || !P) return false;
	if (bRiding) LeaveTruck(true);
	SetTorch(false);
	ExitHide();
	StopDrag();
	bKeypad = false;
	if (bBinoculars) ToggleBinoculars();
	// la misión como estaba: puertas abiertas, objetos cogidos
	if (S->Flags.Num() > 0)
	{
		// banderas (desde la tanda 17): se quitan todas y se ponen las guardadas
		for (const FName& F : FlagList()) { if (bool* B = FlagBool(F)) *B = false; }
		Flags.Reset();
		for (const FName& F : S->Flags) SetFlag(F);
	}
	else
	{
		// partida guardada antes de las banderas
		bKey = S->bKey;
		bJefOpen = S->bJefOpen;
		bNoteRead = S->bNoteRead;
		bVaultOpen = S->bVaultOpen;
		bFile = S->bFile;
		bLetter = S->bLetter;
		bVetKey = S->bVetKey;
		bVetOpen = S->bVetOpen;
	}
	bRamosKnown = bRamosKnown || bLetter || bVetKey;
	Darts = S->Darts;
	MissionTime = S->MissionTime;
	Captures = FMath::Max(Captures, S->Captures);
	// lo que quitaron los puntos ya usados (puertas abiertas, carta y expediente cogidos) y la puerta del archivo
	for (const FTarsisPoint& Pt : Points)
	{
		if (!Pt.RemoveBlock.IsNone() && !Pt.Sets.IsNone() && HasFlag(Pt.Sets)) RemoveBlockNamed(Pt.RemoveBlock);
	}
	if (bVaultOpen) RemoveBlockNamed(TEXT("puerta_archivo"));
	if (S->bLampBroken && GateLamp && GateLamp->GetLightComponent() && !bLampBroken)
	{
		bLampBroken = true;
		GateLamp->GetLightComponent()->SetVisibility(false);
		OffLights.Remove(GateLamp->GetLightComponent());
	}
	// tanda 27: las farolas rotas son las del punto de control, ni más ni menos
	RepairLamps();
	for (const FVector& BP : S->BrokenLamps)
	{
		for (TActorIterator<ALight> It(GetWorld()); It; ++It)
		{
			ULightComponent* BL = It->GetLightComponent();
			if (!BL || FVector::DistSquared(It->GetActorLocation(), BP) > 2500.0f || !BreakableLamp(*It) || BrokenLights.Contains(BL)) continue;
			BrokenLights.Add(BL);
			BrokenSpots.Add(It->GetActorLocation());
			CoverLamp(*It);
			BrokenSeen.Add(true);   // ya se dio parte antes del punto de control (o da igual: no se repite)
			BL->SetVisibility(false);
			OffLights.Remove(BL);
			PendingOff.Remove(BL);
		}
	}
	// tanda 32: las llamadas ya cogidas son las del punto de control (antes, al cargar, Control repetia las suyas)
	CloseCodec();
	CodecPending = NAME_None;
	CodecRingT = 0.0f;
	bCodecMenu = false;
	CodecTaken = S->CodecTaken;
	if (S->Weather != Weather) SetWeather(S->Weather);
	bWetInit = false;   // el mojado, de golpe al que toque con el clima cargado
	bCloudInit = false; // y el cielo
	bHasCheck = true;
	CheckLoc = S->Loc;
	CheckRot = S->Rot;
	CheckDarts = S->Darts;
	CheckpointName = S->Checkpoint;
	P->TeleportTo(CheckLoc, CheckRot);
	if (AController* Ctl = P->GetController()) Ctl->SetControlRotation(CheckRot);
	// los guardias vuelven a su ronda (los que estaban dormidos o alerta no se guardan)
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->bAlly) continue;
		if (It->State == ETarsisGuardState::Alert || It->State == ETarsisGuardState::Suspicious || It->State == ETarsisGuardState::Search)
		{
			It->Meter = 0.0f;
			It->SetState(ETarsisGuardState::Return);
		}
	}
	TensionT = 0.0f;
	if (TruckParts.Num() > 0) TruckReset(FMath::Min(TruckInterval, 45.0f));   // el camión no se guarda: vuelve a esperar fuera
	ShowMessage(Tx(TEXT("partida_cargada"), TEXT("PARTIDA CARGADA\nUltimo punto de control: {0}."), { CheckpointName }), 3.5f);
	return true;
}

// ---------------------------------------------------------------- menú de pausa y opciones

void ATarsisDirector::BindMenuKeys()
{
	if (!InputComponent) return;
	const FKey Keys[] = { EKeys::P, EKeys::Escape, EKeys::Up, EKeys::Down, EKeys::Left, EKeys::Right, EKeys::W, EKeys::S,
		EKeys::A, EKeys::D, EKeys::Enter, EKeys::SpaceBar };   // la E no: ya la usa Interact
	for (const FKey& K : Keys)
	{
		FInputKeyBinding& B = InputComponent->BindKey(K, IE_Pressed, this, &ATarsisDirector::MenuKey);
		B.bConsumeInput = false;
		B.bExecuteWhenPaused = true;
	}
}

void ATarsisDirector::TogglePause()
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	if (!PC) return;
	bMenu = !bMenu;
	MenuSel = 0;
	MenuPage = 0;
	WaitKeyFor = -1;
	if (bMenu) bHasSave = UGameplayStatics::DoesSaveGameExist(TEXT("TarsisPartida"), 0);
	UGameplayStatics::SetGamePaused(this, bMenu);
}

TArray<FString> ATarsisDirector::MenuLines() const
{
	static const TCHAR* Q[] = { TEXT("BAJA"), TEXT("MEDIA"), TEXT("ALTA"), TEXT("EPICA") };
	TArray<FString> L;
	if (MenuPage == 1)
	{
		for (int32 i = 0; i < NumActions; ++i)
		{
			L.Add(WaitKeyFor == i ? FString::Printf(TEXT("%s   ... PULSA UNA TECLA (Esc cancela)"), ActionName(i))
				: FString::Printf(TEXT("%s   [ %s ]"), ActionName(i), *ActionKeys[i].GetDisplayName().ToString().ToUpper()));
		}
		L.Add(TEXT("TECLAS POR DEFECTO"));
		L.Add(TEXT("VOLVER"));
		return L;
	}
	L.Add(TEXT("REANUDAR"));
	L.Add(bHasSave ? FString::Printf(TEXT("CARGAR PUNTO DE CONTROL%s"), CheckpointName.IsEmpty() ? TEXT("") : *FString::Printf(TEXT(" (%s)"), *CheckpointName))
		: FString(TEXT("CARGAR PUNTO DE CONTROL (no hay)")));
	L.Add(FString::Printf(TEXT("SENSIBILIDAD DEL RATON   < %.1f >"), OptSensitivity));
	L.Add(FString::Printf(TEXT("INVERTIR EJE Y   < %s >"), bOptInvertY ? TEXT("SI") : TEXT("NO")));
	L.Add(FString::Printf(TEXT("VOLUMEN   < %d %% >"), FMath::RoundToInt(OptVolume * 100.0f)));
	L.Add(FString::Printf(TEXT("CALIDAD GRAFICA   < %s >"), Q[FMath::Clamp(OptQuality, 0, 3)]));
	L.Add(FString::Printf(TEXT("CONTADOR DE FPS   < %s >"), bShowFps ? TEXT("SI") : TEXT("NO")));
	static const TCHAR* Df[] = { TEXT("FACIL"), TEXT("NORMAL"), TEXT("DIFICIL") };
	L.Add(FString::Printf(TEXT("MUSICA   < %d %% >"), FMath::RoundToInt(OptMusic * 100.0f)));
	L.Add(FString::Printf(TEXT("AYUDA DE TECLAS EN PANTALLA   < %s >"), bShowHelp ? TEXT("SI") : TEXT("NO")));
	L.Add(TEXT("CONTROLES..."));
	L.Add(FString::Printf(TEXT("DIFICULTAD   < %s >"), Df[FMath::Clamp(Difficulty, 0, 2)]));
	L.Add(FString::Printf(TEXT("TAMANO DEL TEXTO   < %d %% >"), FMath::RoundToInt(OptTextScale * 100.0f)));
	L.Add(FString::Printf(TEXT("COLORES PARA DALTONISMO   < %s >"), bColorblind ? TEXT("SI") : TEXT("NO")));
	L.Add(FString::Printf(TEXT("SUBTITULOS DE SONIDOS   < %s >"), bSubtitles ? TEXT("SI") : TEXT("NO")));
	L.Add(TEXT("SALIR DEL JUEGO"));
	return L;
}

void ATarsisDirector::MenuKey(FKey Key)
{
	if (KeyFrame == GFrameCounter) return;   // esta pulsación ya se ha usado para asignar una tecla
	if (WaitKeyFor >= 0) return;               // esperando la tecla nueva: la recoge AnyKey
	if (bCodec)
	{
		// códec abierto (juego en pausa, sin menú): Intro o Espacio pasan de frase y Esc cuelga
		if (Key == EKeys::Escape) CloseCodec();
		else if (Key == EKeys::Enter || Key == EKeys::SpaceBar) CodecNext();
		return;
	}
	if (bMenu && MenuPage == 1 && Key == EKeys::Escape) { MenuPage = 0; MenuSel = 0; return; }
	if (Key == EKeys::P || Key == EKeys::Escape)
	{
		if (bKeypad && Key == EKeys::Escape) { bKeypad = false; KeypadInput.Reset(); return; }   // Esc cierra antes el teclado del archivo (y borra lo tecleado)
		if (!bCine || bMenu || bDone) TogglePause();   // en el final (cinemática parada en su último plano) el parte ofrece P
		return;
	}
	if (!bMenu) return;
	const int32 N = MenuLines().Num();
	if (Key == EKeys::Up || Key == EKeys::W) MenuSel = (MenuSel + N - 1) % N;
	else if (Key == EKeys::Down || Key == EKeys::S) MenuSel = (MenuSel + 1) % N;
	else if (Key == EKeys::Left || Key == EKeys::A) MenuActivate(-1);
	else if (Key == EKeys::Right || Key == EKeys::D) MenuActivate(1);
	else MenuActivate(0);   // Intro o Espacio
}

void ATarsisDirector::MenuActivate(int32 Dir)
{
	const int32 Step = Dir == 0 ? 1 : Dir;
	if (MenuPage == 1)
	{
		if (Dir != 0) return;
		if (MenuSel < NumActions) { WaitKeyFor = MenuSel; KeyFrame = GFrameCounter; return; }
		if (MenuSel == NumActions) { DefaultKeys(); BindAll(); SaveOptions(); return; }
		MenuPage = 0;
		MenuSel = 9;
		return;
	}
	switch (MenuSel)
	{
	case 0: if (Dir == 0) TogglePause(); return;
	case 1:
		if (Dir == 0 && bHasSave) { TogglePause(); LoadCheckpoint(); }
		return;
	case 2: OptSensitivity = FMath::Clamp(FMath::RoundToFloat((OptSensitivity + 0.1f * Step) * 10.0f) / 10.0f, 0.2f, 3.0f); break;
	case 3: bOptInvertY = !bOptInvertY; break;
	case 4: OptVolume = FMath::Clamp(FMath::RoundToFloat((OptVolume + 0.1f * Step) * 10.0f) / 10.0f, 0.0f, 1.0f); break;
	case 5: OptQuality = (OptQuality + Step + 4) % 4; break;
	case 6: bShowFps = !bShowFps; break;
	case 7: OptMusic = FMath::Clamp(FMath::RoundToFloat((OptMusic + 0.1f * Step) * 10.0f) / 10.0f, 0.0f, 1.0f); break;
	case 8: bShowHelp = !bShowHelp; break;
	case 9:
		if (Dir == 0) { MenuPage = 1; MenuSel = 0; }
		return;
	case 10: Difficulty = (Difficulty + Step + 3) % 3; break;
	case 11: OptTextScale = FMath::Clamp(FMath::RoundToFloat((OptTextScale + 0.1f * Step) * 10.0f) / 10.0f, 0.8f, 1.4f); break;
	case 12: bColorblind = !bColorblind; break;
	case 13: bSubtitles = !bSubtitles; break;
	case 14:
		if (Dir == 0) UKismetSystemLibrary::QuitGame(this, UGameplayStatics::GetPlayerController(this, 0), EQuitPreference::Quit, false);
		return;
	default: return;
	}
	ApplyOptions();
	SaveOptions();
}

void ATarsisDirector::ApplyOptions()
{
	// ratón: las escalas «legacy» del PlayerController multiplican lo que llega por AddYawInput/AddPitchInput
	// (la plantilla mueve la cámara con esas funciones). Si estaban desactivadas, la base es 1.
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
	{
		UInputSettings* IS = GetMutableDefault<UInputSettings>();
		if (!bScalesRead)
		{
			bScalesRead = true;
			if (IS && IS->bEnableLegacyInputScales)
			{
				BaseYawScale = PC->InputYawScale_DEPRECATED;
				BasePitchScale = PC->InputPitchScale_DEPRECATED;
			}
			else
			{
				BaseYawScale = 1.0f;
				BasePitchScale = 1.0f;
			}
		}
		if (IS) IS->bEnableLegacyInputScales = true;
		PC->InputYawScale_DEPRECATED = BaseYawScale * OptSensitivity;
		PC->InputPitchScale_DEPRECATED = BasePitchScale * OptSensitivity * (bOptInvertY ? -1.0f : 1.0f);
	}
	MusicTick(0.0f);   // en pausa MusicTick no corre: que el volumen de la música cambie ya, con el menú abierto
	if (GEngine)
	{
		if (FAudioDeviceHandle Dev = GEngine->GetMainAudioDevice()) Dev->SetTransientPrimaryVolume(OptVolume);
	}
	if (UGameUserSettings* G = UGameUserSettings::GetGameUserSettings())
	{
		if (G->GetOverallScalabilityLevel() != OptQuality)
		{
			G->SetOverallScalabilityLevel(OptQuality);
			G->ApplySettings(false);
			// SetWeather fija r.VolumetricFog por código (pisa a la escalabilidad): con despejado, que siga a la calidad
			// (Alta o Épica con niebla volumétrica, Baja y Media sin ella)
			if (IConsoleVariable* CV = IConsoleManager::Get().FindConsoleVariable(TEXT("r.VolumetricFog")))
			{
				SavedVolFog = OptQuality >= 2 ? 1 : 0;
				if (Weather == 0) CV->Set(SavedVolFog, ECVF_SetByCode);
			}
		}
	}
}

void ATarsisDirector::SaveOptions() const
{
	UTarsisSave* S = Cast<UTarsisSave>(UGameplayStatics::CreateSaveGameObject(UTarsisSave::StaticClass()));
	if (!S) return;
	S->Sensitivity = OptSensitivity;
	S->bInvertY = bOptInvertY;
	S->Volume = OptVolume;
	S->Quality = OptQuality;
	S->bShowFps = bShowFps;
	S->Music = OptMusic;
	S->bShowHelp = bShowHelp;
	S->TextScale = OptTextScale;
	S->bColorblind = bColorblind;
	S->bSubtitles = bSubtitles;
	S->Difficulty = Difficulty;
	for (int32 i = 0; i < NumActions; ++i) S->Keys.Add(ActionKeys[i].GetFName());
	UGameplayStatics::SaveGameToSlot(S, TEXT("TarsisOpciones"), 0);
}

void ATarsisDirector::LoadOptions()
{
	if (UGameUserSettings* G = UGameUserSettings::GetGameUserSettings())
	{
		const int32 Cur = G->GetOverallScalabilityLevel();   // -1 si los grupos van mezclados
		OptQuality = Cur >= 0 ? FMath::Clamp(Cur, 0, 3) : 1;
	}
	if (!GIsEditor && !UGameplayStatics::DoesSaveGameExist(TEXT("TarsisOpciones"), 0))
	{
		// primera vez que se arranca el juego: el motor mide el PC y elige la calidad (luego se cambia en Pausa)
		if (UGameUserSettings* G = UGameUserSettings::GetGameUserSettings())
		{
			G->RunHardwareBenchmark();
			G->ApplyHardwareBenchmarkResults();
			const int32 Cur = G->GetOverallScalabilityLevel();
			OptQuality = Cur >= 0 ? FMath::Clamp(Cur, 0, 3) : 1;
			SaveOptions();
			ShowMessage(Tx(TEXT("calidad"), TEXT("CALIDAD GRAFICA\nElegida segun tu PC: {0}. Se cambia en Pausa (P)."),
				{ FString(OptQuality == 0 ? TEXT("BAJA") : OptQuality == 1 ? TEXT("MEDIA") : OptQuality == 2 ? TEXT("ALTA") : TEXT("EPICA")) }), 5.0f);
		}
	}
	if (UTarsisSave* S = Cast<UTarsisSave>(UGameplayStatics::LoadGameFromSlot(TEXT("TarsisOpciones"), 0)))
	{
		OptSensitivity = FMath::Clamp(S->Sensitivity, 0.2f, 3.0f);
		bOptInvertY = S->bInvertY;
		OptVolume = FMath::Clamp(S->Volume, 0.0f, 1.0f);
		if (S->Quality >= 0) OptQuality = FMath::Clamp(S->Quality, 0, 3);
		bShowFps = S->bShowFps;
		OptMusic = FMath::Clamp(S->Music, 0.0f, 1.0f);
		bShowHelp = S->bShowHelp;
		OptTextScale = FMath::Clamp(S->TextScale, 0.8f, 1.4f);
		bColorblind = S->bColorblind;
		bSubtitles = S->bSubtitles;
		Difficulty = FMath::Clamp(S->Difficulty, 0, 2);
		for (int32 i = 0; i < NumActions && i < S->Keys.Num(); ++i)
		{
			const FKey K(S->Keys[i]);
			if (K.IsValid()) ActionKeys[i] = K;
		}
		ApplyOptions();
	}
}

// ---------------------------------------------------------------- teclas configurables

const TCHAR* ATarsisDirector::ActionName(int32 I)
{
	static const TCHAR* N[NumActions] = { TEXT("AGACHARSE"), TEXT("USAR / DERRIBAR (E)"), TEXT("LANZAR PIEDRA"), TEXT("PRISMATICOS"), TEXT("CORRER"), TEXT("CAMBIAR CLIMA"), TEXT("LINTERNA"), TEXT("RADIO") };
	return (I >= 0 && I < NumActions) ? N[I] : TEXT("");
}

void ATarsisDirector::DefaultKeys()
{
	ActionKeys[0] = EKeys::C;
	ActionKeys[1] = EKeys::E;
	ActionKeys[2] = EKeys::Q;
	ActionKeys[3] = EKeys::B;
	ActionKeys[4] = EKeys::LeftShift;
	ActionKeys[5] = EKeys::Y;
	ActionKeys[6] = EKeys::F;
	ActionKeys[7] = EKeys::R;
}

void ATarsisDirector::BindAll()
{
	if (!InputComponent) return;
	InputComponent->KeyBindings.Reset();
	InputComponent->BindKey(ActionKeys[0], IE_Pressed, this, &ATarsisDirector::ToggleCrouch);
	if (ActionKeys[0] != EKeys::LeftControl) InputComponent->BindKey(EKeys::LeftControl, IE_Pressed, this, &ATarsisDirector::ToggleCrouch);
	InputComponent->BindKey(ActionKeys[1], IE_Pressed, this, &ATarsisDirector::Interact);
	InputComponent->BindKey(ActionKeys[2], IE_Pressed, this, &ATarsisDirector::ThrowStone);
	InputComponent->BindKey(ActionKeys[3], IE_Pressed, this, &ATarsisDirector::ToggleBinoculars);
	InputComponent->BindKey(ActionKeys[5], IE_Pressed, this, &ATarsisDirector::CycleWeather);
	InputComponent->BindKey(ActionKeys[6], IE_Pressed, this, &ATarsisDirector::ToggleTorch);
	InputComponent->BindKey(EKeys::M, IE_Pressed, this, &ATarsisDirector::ToggleMindMap);   // tanda 41: el mapa mental (tecla fija)
	InputComponent->BindKey(EKeys::X, IE_Pressed, this, &ATarsisDirector::ToggleBox);   // tanda 40: la caja de cartón (tecla fija)
	InputComponent->BindKey(ActionKeys[4], IE_Pressed, this, &ATarsisDirector::SprintOn);
	InputComponent->BindKey(ActionKeys[4], IE_Released, this, &ATarsisDirector::SprintOff);
	{
		FInputKeyBinding& B = InputComponent->BindKey(EKeys::LeftMouseButton, IE_Pressed, this, &ATarsisDirector::ShootDart);
		B.bConsumeInput = false;
	}
	// teclado del archivo: cifras de arriba y del teclado numérico, y Retroceso para borrar
	const FKey Keys[] = { EKeys::Zero, EKeys::One, EKeys::Two, EKeys::Three, EKeys::Four, EKeys::Five, EKeys::Six,
		EKeys::Seven, EKeys::Eight, EKeys::Nine, EKeys::NumPadZero, EKeys::NumPadOne, EKeys::NumPadTwo,
		EKeys::NumPadThree, EKeys::NumPadFour, EKeys::NumPadFive, EKeys::NumPadSix, EKeys::NumPadSeven,
		EKeys::NumPadEight, EKeys::NumPadNine, EKeys::BackSpace };
	for (const FKey& K : Keys)
	{
		FInputKeyBinding& B = InputComponent->BindKey(K, IE_Pressed, this, &ATarsisDirector::KeypadKey);
		B.bConsumeInput = false;
	}
	{
		FInputKeyBinding& B = InputComponent->BindKey(EKeys::SpaceBar, IE_Pressed, this, &ATarsisDirector::SkipCine);
		B.bConsumeInput = false;
	}
	BindMenuKeys();
	// códec: la tecla de la radio (R; llamar o coger la llamada) y, con la conversación abierta y el juego en pausa, la E y el clic para seguir
	for (const FKey& K : { ActionKeys[7], ActionKeys[1], EKeys::LeftMouseButton })
	{
		FInputKeyBinding& B = InputComponent->BindKey(K, IE_Pressed, this, &ATarsisDirector::CodecInput);
		B.bConsumeInput = false;
		B.bExecuteWhenPaused = true;
	}
	{
		FInputKeyBinding& B = InputComponent->BindKey(EKeys::AnyKey, IE_Pressed, this, &ATarsisDirector::AnyKey);
		B.bConsumeInput = false;
		B.bExecuteWhenPaused = true;
	}
}

void ATarsisDirector::AnyKey(FKey Key)
{
	if (WaitKeyFor < 0 || KeyFrame == GFrameCounter) return;
	if (Key.IsMouseButton() || Key.IsAnalog() || Key == EKeys::Enter || Key == EKeys::P) return;   // no valen
	const int32 I = WaitKeyFor;
	WaitKeyFor = -1;
	KeyFrame = GFrameCounter;
	if (Key == EKeys::Escape) return;   // cancelar
	// si la tecla ya era de otra acción, se intercambian
	for (int32 j = 0; j < NumActions; ++j)
	{
		if (j != I && ActionKeys[j] == Key) ActionKeys[j] = ActionKeys[I];
	}
	ActionKeys[I] = Key;
	BindAll();
	SaveOptions();
}

FString ATarsisDirector::HelpLine() const
{
	auto K = [this](int32 I) { return ActionKeys[I].GetDisplayName().ToString().ToUpper(); };
	FString S = FString::Printf(TEXT("%s agacharse   %s correr   %s piedra   %s prismaticos"), *K(0), *K(4), *K(2), *K(3));
	if (Darts > 0) S += FString::Printf(TEXT("   CLIC dardo (%d)"), Darts);
	if (bHasTorch) S += FString::Printf(TEXT("   %s linterna"), *K(6));
	if (HasFlag(FName(TEXT("caja")))) S += TEXT("   X caja");
	if (FactsLearned > 0 || FactsKnown() > 0) S += TEXT("   M mapa");
	if (bPowerOff) S += TEXT("   sin luz: busca la sombra de las linternas");
	S += FString::Printf(TEXT("   %s radio   P pausa"), *K(7));
	return S;
}

// ---------------------------------------------------------------- música por capas

void ATarsisDirector::SetupMusic()
{
	auto Layer = [this](const TCHAR* Name, float Vol) -> UAudioComponent*
	{
		USoundBase* S = LoadSnd(Name);
		if (!S) return nullptr;
		if (USoundWave* W = Cast<USoundWave>(S)) W->bLooping = true;
		UAudioComponent* A = UGameplayStatics::CreateSound2D(this, S, 1.0f, 1.0f, 0.0f, nullptr, true, false);
		if (A) A->SetVolumeMultiplier(FMath::Max(Vol, 0.001f));
		return A;
	};
	MusicBase = Layer(TEXT("musica_base"), 0.35f * OptMusic);
	MusicTen = Layer(TEXT("musica_tension"), 0.001f);
	MusicAlr = Layer(TEXT("musica_alerta"), 0.001f);
	// las tres a la vez: duran lo mismo y así van a compás
	for (UAudioComponent* A : { MusicBase.Get(), MusicTen.Get(), MusicAlr.Get() }) if (A) A->Play();
}

void ATarsisDirector::MusicTick(float DeltaSeconds)
{
	if (!MusicBase && !MusicTen && !MusicAlr) return;
	float MaxMeter = 0.0f;
	bool bAlert = false;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Down || It->bAlly) continue;
		MaxMeter = FMath::Max(MaxMeter, It->Meter);
		if (It->State == ETarsisGuardState::Alert) bAlert = true;
	}
	// tensión: sube con el guardia más mosqueado y se queda a medias mientras la base está en guardia o sin luz
	float TenT = FMath::Clamp(MaxMeter * 1.4f, 0.0f, 1.0f);
	if (TensionT > 0.0f || bPowerOff) TenT = FMath::Max(TenT, 0.45f);
	const float AlrT = bAlert ? 1.0f : 0.0f;
	const bool bQuiet = bCine || bDone;   // en las cinemáticas y el final, solo el ambiente
	MusicTension = FMath::FInterpTo(MusicTension, bQuiet ? 0.0f : TenT, DeltaSeconds, TenT > MusicTension ? 2.0f : 0.4f);
	MusicAlert = FMath::FInterpTo(MusicAlert, bQuiet ? 0.0f : AlrT, DeltaSeconds, AlrT > MusicAlert ? 4.0f : 0.3f);
	const float Base = 0.35f * (1.0f - 0.4f * MusicAlert);
	const float Duck = bCodec ? 0.3f : 1.0f;   // con el códec abierto la música se aparta
	if (MusicBase) MusicBase->SetVolumeMultiplier(FMath::Max(0.001f, Base * OptMusic * Duck));
	if (MusicTen) MusicTen->SetVolumeMultiplier(FMath::Max(0.001f, 0.5f * MusicTension * (1.0f - 0.5f * MusicAlert) * OptMusic * Duck));
	if (MusicAlr) MusicAlr->SetVolumeMultiplier(FMath::Max(0.001f, 0.55f * MusicAlert * OptMusic * Duck));
}

// ---------------------------------------------------------------- detecciones (para la puntuación) y dirección de un sonido

void ATarsisDirector::DetectTick()
{
	if (bDone || bCine) return;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		const TObjectPtr<ATarsisGuard> K(*It);
		uint8& Prev = PrevState.FindOrAdd(K, (uint8)It->State);
		const uint8 Now = (uint8)It->State;
		if (Now != Prev)
		{
			const ETarsisGuardState Before = (ETarsisGuardState)Prev;
			if (It->State == ETarsisGuardState::Alert && !It->bRadioCall && !It->bAlly) ++Detections;
			// lo que dicen: «¡alto!» al verte, «¿quién anda ahí?» o «¿qué ha sido eso?» al mosquearse, y al dejarlo
			// «aquí no hay nadie» o, si fue por un ruido, «habrá sido el viento»
			if (It->State == ETarsisGuardState::Alert && !It->bRadioCall) GuardSay(*It, TEXT("alto"));
			else if (It->State == ETarsisGuardState::Suspicious && Before != ETarsisGuardState::Alert) GuardSay(*It, It->bInvestigate ? TEXT("ruido") : TEXT("quien"));
			else if (It->State == ETarsisGuardState::Return && Before == ETarsisGuardState::Search) GuardSay(*It, It->bNoiseSearch ? TEXT("viento") : TEXT("nadie"));
			else if (It->State == ETarsisGuardState::Search && Before == ETarsisGuardState::Alert && !It->bRadioCall) GuardSay(*It, TEXT("perdido"));
		}
		Prev = Now;
	}
}

FString ATarsisDirector::Direction(const FVector& Where) const
{
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!PC || !P) return TEXT("CERCA");
	const FRotator R(0.0f, PC->GetControlRotation().Yaw, 0.0f);
	const FVector L = R.UnrotateVector(Where - P->GetActorLocation());
	const float A = FMath::RadiansToDegrees(FMath::Atan2(L.Y, L.X));   // 0 delante, 90 derecha
	if (FMath::Abs(A) < 30.0f) return TEXT("DELANTE");
	if (FMath::Abs(A) > 150.0f) return TEXT("DETRAS");
	const TCHAR* Side = A > 0.0f ? TEXT("DERECHA") : TEXT("IZQUIERDA");
	if (FMath::Abs(A) < 75.0f) return FString::Printf(TEXT("DELANTE A LA %s"), Side);
	if (FMath::Abs(A) > 105.0f) return FString::Printf(TEXT("DETRAS A LA %s"), Side);
	return FString::Printf(TEXT("A LA %s"), Side);
}

// ---------------------------------------------------------------- parte del día siguiente

void ATarsisDirector::BuildReport()
{
	TArray<FString> Downed;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Down) Downed.Add(It->GuardName);
		if (It->State == ETarsisGuardState::Down && It->GuardName.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase) && !bRamosAlly) bRamosDowned = true;
	}
	TArray<FString>& L = ReportLines;
	L.Reset();
	L.Add(TEXT("PARTE DEL DIA SIGUIENTE"));
	L.Add(TEXT("Base de Tarsis - Del teniente coronel Alarcon al Mando de la Zona Sur"));
	L.Add(TEXT(""));
	L.Add(bMarsh ? TEXT("Anoche un intruso huyo por la marisma con el expediente LH-07. Se le perdio el rastro en los canales.")
		: bLeftByTruck ? TEXT("Anoche un intruso salio de la base en la caja del camion de suministros, con el expediente LH-07. En el control miraron los papeles del conductor y nada mas.")
		: TEXT("Anoche un intruso salio por el control de salida con el expediente LH-07. El de la garita no vio nada."));
	if (Detections == 0) L.Add(TEXT("Nadie llego a verlo. Hay quien duda de que existiera."));
	else L.Add(FString::Printf(TEXT("Fue visto %d %s, pero las descripciones no coinciden."), Detections, Detections == 1 ? TEXT("vez") : TEXT("veces")));
	if (Captures > 0) L.Add(TEXT("Estuvo en el calabozo y salio de el. Se abre expediente al cabo Vidal."));
	TArray<FString> DownedList = Downed;
	if (bRamosDowned) DownedList.RemoveAll([](const FString& N) { return N.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase); });   // ya tiene su línea
	if (DownedList.Num() > 0) L.Add(FString::Printf(TEXT("Amanecieron en el suelo, aturdidos o dormidos: %s."), *FString::Join(DownedList, TEXT(", "))));
	if (bVetOpen) L.Add(TEXT("El botiquin del veterinario esta abierto y falta la pistola de dardos."));
	if (bKey) L.Add(TEXT("Al sargento Ibarra le falta la llave de la jefatura. Se cambiara la cerradura."));
	if (bLampBroken) L.Add(TEXT("El farol del control aparecio roto de un disparo. Se ha pedido otro a Sevilla."));
	if (BrokenLights.Num() == 1) L.Add(TEXT("Una farola aparecio rota de un disparo. No hay repuesto hasta el lunes."));
	else if (BrokenLights.Num() > 1) L.Add(FString::Printf(TEXT("%d farolas aparecieron rotas a tiros. No hay repuesto hasta el lunes."), BrokenLights.Num()));
	if (bReserveHalf) L.Add(TEXT("El generador sigue averiado: con la reserva, media base pasara la noche a oscuras."));
	else if (bPowerCutOnce) L.Add(TEXT("Alguien corto el generador; se arranco de nuevo antes del alba."));
	if (bRamosAlly) L.Add(bMarsh ? TEXT("El soldado Ramos no se presento a la diana. Se le da por desertor.")
		: TEXT("El soldado Ramos no se presento a la diana. Se le busca en Trebujena."));
	else if (bRamosDowned) L.Add(TEXT("A Ramos lo encontraron sin sentido. No recuerda nada, o eso dice."));
	L.Add(TEXT(""));
	// consecuencias para la siguiente noche (las leerá la misión 2)
	TArray<FString> Cons;
	if (Detections >= 3 || Captures > 0) Cons.Add(TEXT("se doblan las rondas"));
	if (bReserveHalf) Cons.Add(TEXT("la zona norte queda a oscuras"));
	if (bLampBroken) Cons.Add(TEXT("el control sigue sin farol"));
	if (BrokenLights.Num() > 0) Cons.Add(TEXT("hay farolas sin reponer"));
	if (bRamosAlly) Cons.Add(TEXT("Ramos te espera fuera"));
	else if (bRamosDowned) Cons.Add(TEXT("Ramos desconfia de todos"));
	if (bKey) Cons.Add(TEXT("cerradura nueva en la jefatura"));
	if (bLeftByTruck) Cons.Add(TEXT("en el control registran todos los camiones"));
	L.Add(Cons.Num() > 0 ? FString::Printf(TEXT("LA PROXIMA NOCHE: %s."), *FString::Join(Cons, TEXT(", "))) : FString(TEXT("LA PROXIMA NOCHE: todo sigue igual. Nadie sabe que estuviste.")));
	L.Add(FString::Printf(TEXT("SIGILO: %d puntos - %s"), Score, *Rank));
	L.Add(TEXT(""));
	L.Add(TEXT("P: menu (salir o cargar el ultimo punto de control)"));
	// se guarda para la misión 2
	UTarsisSave* S = Cast<UTarsisSave>(UGameplayStatics::CreateSaveGameObject(UTarsisSave::StaticClass()));
	if (!S) return;
	S->bByMarsh = bMarsh;
	S->bByTruck = bLeftByTruck;
	S->Detections = Detections;
	S->Takedowns = Takedowns;
	S->Captures = Captures;
	S->MissionTime = MissionTime;
	S->bPowerCut = bPowerCutOnce;
	S->bReserveHalf = bReserveHalf;
	S->bLampBroken = bLampBroken;
	S->LampsBroken = BrokenLights.Num();
	S->bRamosAlly = bRamosAlly;
	S->bRamosDowned = bRamosDowned;
	S->bKey = bKey;
	S->bVetOpen = bVetOpen;
	S->Score = Score;
	S->Rank = Rank;
	S->Downed = Downed;
	S->Report = L;
	S->Difficulty = Difficulty;
	UGameplayStatics::SaveGameToSlot(S, TEXT("TarsisParte"), 0);
}

// ---------------------------------------------------------------- misión en datos: textos, banderas, puntos y objetivos
// assets/unreal/mision1.json lo vuelca tools/unreal/mision.py en este actor y se guarda con el nivel (vale empaquetado).

FString ATarsisDirector::Tx(FName Key, const TCHAR* Default, const FStringFormatOrderedArguments& Args) const
{
	const FString* Found = Texts.Find(Key);
	if (!Found) const_cast<ATarsisDirector*>(this)->MissingTexts.AddUnique(Key.ToString());
	const FString Raw = Found ? *Found : FString(Default);
	return Args.Num() > 0 ? FString::Format(*Raw, Args) : Raw;
}

void ATarsisDirector::Teach(FName Key, const TCHAR* Default, const FStringFormatOrderedArguments& Args, float Seconds)
{
	const FString T = Tx(Key, Default, Args);
	if (Taught.Contains(Key)) return;   // ya lo sabes: la segunda vez no sale
	Taught.Add(Key);
	ShowMessage(T, Seconds);
}

// las banderas de siempre siguen siendo booleanos del C++ (los usa media clase); el resto, en el conjunto Flags
static const TCHAR* const MappedFlags[] = {
	TEXT("llave_jefatura"), TEXT("jefatura_abierta"), TEXT("nota_leida"), TEXT("archivo_abierto"), TEXT("expediente"),
	TEXT("carta_leida"), TEXT("llave_botiquin"), TEXT("botiquin_abierto"), TEXT("sabe_de_ramos") };

bool* ATarsisDirector::FlagBool(FName F)
{
	bool* const Ptrs[] = { &bKey, &bJefOpen, &bNoteRead, &bVaultOpen, &bFile, &bLetter, &bVetKey, &bVetOpen, &bRamosKnown };
	static_assert(UE_ARRAY_COUNT(MappedFlags) == 9, "una bandera por booleano");
	for (int32 i = 0; i < UE_ARRAY_COUNT(MappedFlags); ++i)
	{
		if (F == FName(MappedFlags[i])) return Ptrs[i];
	}
	return nullptr;
}

bool ATarsisDirector::HasFlag(FName F) const
{
	if (F.IsNone()) return true;
	if (const bool* B = const_cast<ATarsisDirector*>(this)->FlagBool(F)) return *B;
	return Flags.Contains(F);
}

void ATarsisDirector::SetFlag(FName F)
{
	if (F.IsNone()) return;
	if (bool* B = FlagBool(F)) *B = true;
	Flags.Add(F);
}

TArray<FName> ATarsisDirector::FlagList() const
{
	TArray<FName> L;
	for (const TCHAR* N : MappedFlags) { if (HasFlag(FName(N))) L.Add(FName(N)); }
	for (const FName& F : Flags) L.AddUnique(F);
	return L;
}

int32 ATarsisDirector::BaseState() const
{
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Alert && !It->bAlly) return 2;
	}
	return TensionT > 0.0f ? 1 : 0;
}

void ATarsisDirector::DefaultMission()
{
	// sin datos (no se ha pasado tools/unreal/mision.py por el nivel) no hay puertas, notas ni objetivos: se avisa
	if (Points.Num() == 0 || Objectives.Num() == 0)
	{
		UE_LOG(LogTemp, Error, TEXT("Tarsis: el director no tiene los datos de la mision; ejecuta tools/unreal/mision.py en el editor"));
		ShowMessage(TEXT("FALTAN LOS DATOS DE LA MISION\nEn el editor: tools/unreal/mision.py (assets/unreal/mision1.json)."), 30.0f);
	}
}

const FTarsisPoint* ATarsisDirector::PointNear() const
{
	for (const FTarsisPoint& Pt : Points)
	{
		if (!Pt.bRepeat && !Pt.Sets.IsNone() && HasFlag(Pt.Sets)) continue;   // ya usado
		const bool bHave = HasFlag(Pt.Need);
		if (!bHave && Pt.PromptLocked.IsNone() && Pt.NeedText.IsNone()) continue;   // aún no existe para ti (la nota, con la jefatura cerrada)
		if (NearPlayer(Pt.Pos, Pt.Radius)) return &Pt;
	}
	return nullptr;
}

void ATarsisDirector::RemoveBlockNamed(FName Name)
{
	TObjectPtr<UStaticMeshComponent>* Found = Blocks.Find(Name);
	if (!Found) return;
	UStaticMeshComponent* B = *Found;
	Blocks.Remove(Name);
	if (!B) return;
	if (B == DoorL) DoorL = nullptr;
	if (B == DoorV) DoorV = nullptr;
	if (B == VetDoor) VetDoor = nullptr;
	if (B == NoteProp) NoteProp = nullptr;
	if (B == LetterProp) LetterProp = nullptr;
	if (B == FileProp) FileProp = nullptr;
	B->DestroyComponent();
}

void ATarsisDirector::UsePoint(const FTarsisPoint& PtRef)
{
	const FTarsisPoint Pt = PtRef;   // copia: lo que sigue no debe depender de la lista
	// dónde suena y dónde lo notan los guardias: en el bloque que quita (la puerta), o en el punto
	FVector Where = Pt.Pos + FVector(0.0f, 0.0f, 100.0f);
	if (const TObjectPtr<UStaticMeshComponent>* B = Blocks.Find(Pt.RemoveBlock)) { if (*B) Where = (*B)->GetComponentLocation(); }
	if (!HasFlag(Pt.Need))
	{
		SetFlag(Pt.NeedSets);
		if (!Pt.NeedSound.IsNone()) PlaySfx(Pt.NeedSound.ToString(), Where, 0.5f);
		if (!Pt.NeedText.IsNone()) ShowMessage(Tx(Pt.NeedText, *Pt.NeedText.ToString()), 3.5f);
		return;
	}
	SetFlag(Pt.Sets);
	SetFlag(Pt.AlsoSets);
	if (Pt.Darts > 0) Darts = FMath::Max(Darts, Pt.Darts);
	if (!Pt.RemoveBlock.IsNone()) RemoveBlockNamed(Pt.RemoveBlock);
	if (Pt.bChange) AddChange(Where, TEXT("puerta"));
	if (!Pt.Sound.IsNone()) PlaySfx(Pt.Sound.ToString(), Where, 0.8f);
	if (!Pt.Text.IsNone()) ShowMessage(Tx(Pt.Text, *Pt.Text.ToString()), Pt.TextSeconds);
	if (!Pt.Checkpoint.IsNone()) Checkpoint(Tx(Pt.Checkpoint, *Pt.Checkpoint.ToString()));
}

// ---------------------------------------------------------------- subtítulos de voz y la central por radio

void ATarsisDirector::ShowSubtitleLine(const FString& Line, float Seconds)
{
	Subtitle = Line;
	SubtitleT = Seconds;
	VoiceSubT = Seconds;
	SubtitleDist = 0.0f;
	SubtitleLog.Add(Line);
	if (SubtitleLog.Num() > 30) SubtitleLog.RemoveAt(0);
}

void ATarsisDirector::SaySubtitle(const FString& Who, const FString& Text, float Seconds)
{
	const FString Line = FString::Printf(TEXT("%s: \"%s\""), *Who, *Text);
	// si aún se lee el anterior, este espera su turno (como mucho tres en cola; si hay más, el más viejo sobra)
	if (VoiceSubT > 0.8f)
	{
		PendingSubs.Add(Line);
		if (PendingSubs.Num() > 3) PendingSubs.RemoveAt(0);
		return;
	}
	ShowSubtitleLine(Line, Seconds);
}

void ATarsisDirector::CentralSay(const FString& Key, const FString& Text, float Delay)
{
	if (Delay > 0.0f)
	{
		FTimerHandle H;
		GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateWeakLambda(this, [this, Key, Text]() { CentralSay(Key, Text, 0.0f); }), Delay, false);
		return;
	}
	if (bCine || bDone || RadioDead()) return;   // tanda 32: con la emisora muda la central no se oye
	if (USoundBase* S = Sfx(TEXT("voz_central_") + Key)) UGameplayStatics::PlaySound2D(this, S, 0.8f);
	else if (RadioSnd) UGameplayStatics::PlaySound2D(this, RadioSnd, 0.35f);
	LastVoice = TEXT("central_") + Key;
	++VoicesPlayed;
	VoiceLog.Add(LastVoice);
	if (VoiceLog.Num() > 30) VoiceLog.RemoveAt(0);
	SaySubtitle(Tx(TEXT("nombre_central"), TEXT("CENTRAL (RADIO)")), Text);
}

// ---------------------------------------------------------------- te cogen: escena en vez de teletransporte en seco

void ATarsisDirector::BeginCapture(ATarsisGuard* G)
{
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || bCapturing || bDone) return;
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	bCapturing = true;
	bCaptureHit = false;
	bCaptureDone = false;
	bCaptureLocker = false;
	bCaptureTruck = false;
	Captor = G;
	CaptureT = 0.0f;
	StopDrag();
	bKeypad = false;
	if (bBinoculars) ToggleBinoculars();
	ExitHide();   // de la taquilla te saca de un tirón: sales y lo tienes delante
	if (bRiding) LeaveTruck(true);   // y de la caja del camión, lo mismo
	if (ACharacter* C = Cast<ACharacter>(P)) C->GetCharacterMovement()->StopMovementImmediately();
	if (PC)
	{
		PC->SetIgnoreMoveInput(true);
		PC->SetIgnoreLookInput(true);
		CaptureFrom = PC->GetControlRotation();
	}
	if (G) GuardSay(G, TEXT("tengo"));
}

void ATarsisDirector::CaptureTick(float DeltaSeconds)
{
	if (!bCapturing) return;
	CaptureT += DeltaSeconds;
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!bCaptureHit)
	{
		// la cámara se vuelve hacia él (0,75 s); luego el golpe y negro
		if (PC && P && Captor)
		{
			FVector Eye; FRotator R;
			PC->GetPlayerViewPoint(Eye, R);
			const FRotator Want = (Captor->GetActorLocation() + FVector(0.0f, 0.0f, 60.0f) - Eye).Rotation();
			PC->SetControlRotation(FMath::RInterpTo(PC->GetControlRotation(), Want, DeltaSeconds, 7.0f));
		}
		if (CaptureT >= 0.75f)
		{
			bCaptureHit = true;
			PlaySfx(TEXT("empujon"), FVector::ZeroVector, 1.0f, false);
			if (PC && PC->PlayerCameraManager) PC->PlayerCameraManager->StartCameraFade(0.0f, 1.0f, 0.15f, FLinearColor::Black, false, true);
		}
		return;
	}
	if (!bCaptureDone)
	{
		if (CaptureT < 1.15f) return;
		bCaptureDone = true;
		const FString Who = Captor ? Captor->GuardName.ToUpper() : FString();
		const bool bLocker = bCaptureLocker;
		const bool bFromTruck = bCaptureTruck;
		bCaptureLocker = false;
		bCaptureTruck = false;
		if (P) Captured(P);   // en negro: al calabozo, al punto de control o a la entrada
		if (bLocker)
		{
			ShowMessage(Tx(TEXT("taquilla_pillado"), TEXT("{0} TE VIO METERTE EN LA TAQUILLA\nLa abre de un tiron. {1}"), { Who, Message.Mid(Message.Find(TEXT("\n")) + 1) }), 6.0f);
		}
		else if (bFromTruck)
		{
			ShowMessage(Tx(TEXT("camion_pillado"), TEXT("{0} LEVANTA LA LONA\nTe saca de la caja del camion. {1}"), { Who, Message.Mid(Message.Find(TEXT("\n")) + 1) }), 6.0f);
		}
		if (PC)
		{
			PC->SetIgnoreMoveInput(false);
			PC->SetIgnoreLookInput(false);
			if (PC->PlayerCameraManager) PC->PlayerCameraManager->StartCameraFade(1.0f, 0.0f, 0.9f, FLinearColor::Black, false, false);
		}
		return;
	}
	if (CaptureT >= 2.1f) { bCapturing = false; Captor = nullptr; }
}


// ---------------------------------------------------------------- ambiente de las zonas

void ATarsisDirector::SetupZones()
{
	static const FName Flicker(TEXT("parpadeo")), Power(TEXT("electrico")), Rain(TEXT("lluvia")), Halo(TEXT("halo")), Decor(TEXT("decorado"));
	for (TActorIterator<AActor> It(GetWorld()); It; ++It)
	{
		if (It->ActorHasTag(Flicker))
		{
			TInlineComponentArray<ULightComponent*> Ls(*It);
			for (ULightComponent* L : Ls) { FlickerLights.Add(L); FlickerBase.Add(L->Intensity); FlickerT.Add(FMath::FRandRange(2.0f, 9.0f)); }
		}
		const bool bHalo = It->ActorHasTag(Halo), bDecor = It->ActorHasTag(Decor);
		if (bHalo || bDecor)
		{
			// tanda 25: el halo de una luminaria y su resplandor de relleno (tools/unreal/cielo.py) van con su luz, la
			// más cercana: se apagan con el generador, con el farol roto y cuando falla
			ULightComponent* Best = nullptr;
			float BestD = FMath::Square(260.0f);
			for (TActorIterator<ALight> Lt(GetWorld()); Lt; ++Lt)
			{
				if (Lt->ActorHasTag(Decor) || !Lt->GetLightComponent()) continue;
				const float D = FVector::DistSquared(Lt->GetActorLocation(), It->GetActorLocation());
				if (D < BestD) { BestD = D; Best = Lt->GetLightComponent(); }
			}
			if (bHalo) { Halos.Add(*It); HaloLights.Add(Best); }
			else if (ALight* DL = Cast<ALight>(*It)) { DecorLights.Add(DL->GetLightComponent()); DecorOf.Add(Best); }
		}
		const bool bPower = It->ActorHasTag(Power), bRain = It->ActorHasTag(Rain);
		if (!bPower && !bRain) continue;
		if (bRain)
		{
			TInlineComponentArray<UDecalComponent*> Ds(*It);
			for (UDecalComponent* D : Ds) RainDecals.Add(D);
		}
		TInlineComponentArray<UAudioComponent*> As(*It);
		for (UAudioComponent* A : As) (bRain ? RainSounds : PowerSounds).Add(A);
	}
}

void ATarsisDirector::ZonesTick(float DeltaSeconds)
{
	// fluorescente viejo: casi siempre fijo; de vez en cuando titila unas décimas (sin luz no hace nada: está apagado)
	for (int32 i = 0; i < FlickerLights.Num(); ++i)
	{
		ULightComponent* L = FlickerLights[i];
		if (!L || !L->IsVisible()) continue;
		FlickerT[i] -= DeltaSeconds;
		float K = 1.0f;
		if (FlickerT[i] < 0.0f)
		{
			K = FMath::FRand() < 0.5f ? 0.15f : 0.7f;
			if (FlickerT[i] < -0.35f) FlickerT[i] = FMath::FRandRange(3.0f, 12.0f);
		}
		L->SetIntensity(FlickerBase[i] * K);
	}
	// el zumbido del fluorescente calla con el apagón; la gotera solo suena si llueve
	for (UAudioComponent* A : PowerSounds)
	{
		if (!A) continue;
		if (bPowerOff && A->IsPlaying()) A->Stop();
		else if (!bPowerOff && !A->IsPlaying()) A->Play();
	}
	for (UDecalComponent* D : RainDecals)
	{
		if (D && D->IsVisible() != (Weather == 1)) D->SetVisibility(Weather == 1);
	}
	for (UAudioComponent* A : RainSounds)
	{
		if (!A) continue;
		if (Weather != 1 && A->IsPlaying()) A->Stop();
		else if (Weather == 1 && !A->IsPlaying()) A->Play();
	}
	// los halos y los resplandores de relleno, con su luz (uno sin luz cerca se queda encendido)
	for (int32 i = 0; i < Halos.Num(); ++i)
	{
		AActor* H = Halos[i];
		if (!H) continue;
		const ULightComponent* L = HaloLights.IsValidIndex(i) ? HaloLights[i].Get() : nullptr;
		const bool bOff = L && (!L->IsVisible() || L->Intensity <= 0.0f);
		if (H->IsHidden() != bOff) H->SetActorHiddenInGame(bOff);
	}
	for (int32 i = 0; i < DecorLights.Num(); ++i)
	{
		ULightComponent* D = DecorLights[i];
		if (!D) continue;
		const ULightComponent* L = DecorOf.IsValidIndex(i) ? DecorOf[i].Get() : nullptr;
		const bool bOn = !L || (L->IsVisible() && L->Intensity > 0.0f);
		if (D->IsVisible() != bOn) D->SetVisibility(bOn);
	}
	WetTick(DeltaSeconds);
}

int32 ATarsisDirector::HalosLit() const
{
	int32 N = 0;
	for (const TObjectPtr<AActor>& H : Halos) if (H && !H->IsHidden()) ++N;
	return N;
}

void ATarsisDirector::WetTick(float DeltaSeconds)
{
	CloudTick(DeltaSeconds);
	// tanda 24: con lluvia la base entera se moja poco a poco y al escampar se seca despacio
	const float Target = Weather == 1 ? 1.0f : 0.0f;
	const float Prev = Wetness;
	if (!bWetInit)
	{
		bWetInit = true;
		if (!WetMPC) WetMPC = WetCollection.LoadSynchronous();
		if (!WetMPC) UE_LOG(LogTemp, Warning, TEXT("Tarsis: falta MPC_Tarsis (tools/unreal/materiales.py): la lluvia no moja el suelo"));
		Wetness = Target;
		if (WetMPC) UKismetMaterialLibrary::SetScalarParameterValue(this, WetMPC, TEXT("Mojado"), Wetness);
		return;
	}
	Wetness = FMath::FInterpConstantTo(Wetness, Target, DeltaSeconds, 1.0f / FMath::Max(1.0f, Target > Wetness ? WetSeconds : DrySeconds));
	if (WetMPC && Wetness != Prev) UKismetMaterialLibrary::SetScalarParameterValue(this, WetMPC, TEXT("Mojado"), Wetness);
}

void ATarsisDirector::CloudTick(float DeltaSeconds)
{
	// tanda 25: con lluvia o niebla el cielo se cubre (parámetro «Nublado» de MPC_Tarsis: lo leen el cielo y los halos
	// de las farolas, tools/unreal/cielo.py). Se cubre en CloudSeconds y se abre algo más despacio
	const float Target = Weather != 0 ? 1.0f : 0.0f;
	if (!bCloudInit)
	{
		bCloudInit = true;
		if (!WetMPC) WetMPC = WetCollection.LoadSynchronous();
		Cloudiness = Target;
		if (WetMPC) UKismetMaterialLibrary::SetScalarParameterValue(this, WetMPC, TEXT("Nublado"), Cloudiness);
		return;
	}
	const float Prev = Cloudiness;
	Cloudiness = FMath::FInterpConstantTo(Cloudiness, Target, DeltaSeconds, 1.0f / FMath::Max(1.0f, Target > Cloudiness ? CloudSeconds : CloudSeconds * 1.5f));
	if (WetMPC && Cloudiness != Prev) UKismetMaterialLibrary::SetScalarParameterValue(this, WetMPC, TEXT("Nublado"), Cloudiness);
}

void ATarsisDirector::SetCloudinessNow(float Value)
{
	if (!WetMPC) WetMPC = WetCollection.LoadSynchronous();
	bCloudInit = true;
	Cloudiness = FMath::Clamp(Value, 0.0f, 1.0f);
	if (WetMPC) UKismetMaterialLibrary::SetScalarParameterValue(this, WetMPC, TEXT("Nublado"), Cloudiness);
}

float ATarsisDirector::CloudinessInCollection() const
{
	return WetMPC ? UKismetMaterialLibrary::GetScalarParameterValue(const_cast<ATarsisDirector*>(this), WetMPC, TEXT("Nublado")) : -1.0f;
}

void ATarsisDirector::SetWetnessNow(float Value)
{
	if (!WetMPC) WetMPC = WetCollection.LoadSynchronous();
	bWetInit = true;
	Wetness = FMath::Clamp(Value, 0.0f, 1.0f);
	if (WetMPC) UKismetMaterialLibrary::SetScalarParameterValue(this, WetMPC, TEXT("Mojado"), Wetness);
}

float ATarsisDirector::WetnessInCollection() const
{
	return WetMPC ? UKismetMaterialLibrary::GetScalarParameterValue(const_cast<ATarsisDirector*>(this), WetMPC, TEXT("Mojado")) : -1.0f;
}
