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
	SetupPlayer();
	SetWeather(Weather);
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
	ShowMessage(FString::Printf(TEXT("TARSIS, DE NOCHE\nBusca la sombra. Agachado (%s) te ven menos y por los huecos de las vallas se pasa agachado.\nEl expediente LH-07 esta en el archivo de la jefatura. La llave la lleva el sargento Ibarra.\n%s lanza una piedra para distraer. %s prismaticos: marca a los guardias que mires.\nTus pasos se oyen: corriendo (%s) y sobre la gravilla mas que dentro. Agachado, nada.\nP: pausa, opciones, controles y cargar el ultimo punto de control."),
		*K(0), *K(2), *K(3), *K(4)), 11.0f);
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
		const FRotator R(0.0f, CellYaw, 0.0f);
		Player->TeleportTo(CellSpot, R);
		if (Ctl) Ctl->SetControlRotation(R);
		CloseCell();
		CellT = CellTime;
		ShowMessage(TEXT("CALABOZO\nDespiertas tras la reja. Al otro lado, el cabo Vidal hace guardia y reza en voz baja.\nEspera. Vidal no es como los demas."), 8.0f);
		return;
	}
	if (bHasCheck && Difficulty < 2)
	{
		// al último punto de control, no a la entrada: la segunda mitad de la misión no se repite entera
		Player->TeleportTo(CheckLoc, CheckRot);
		if (Ctl) Ctl->SetControlRotation(CheckRot);
		Darts = FMath::Max(Darts, CheckDarts);
		ShowMessage(FString::Printf(TEXT("TE HAN COGIDO\nVuelves al ultimo punto de control: %s."), *CheckpointName), 4.0f);
		return;
	}
	if (AActor* Start = UGameplayStatics::GetActorOfClass(this, APlayerStart::StaticClass()))
	{
		Player->TeleportTo(Start->GetActorLocation(), Start->GetActorRotation());
		if (Ctl) Ctl->SetControlRotation(Start->GetActorRotation());
	}
	ShowMessage(TEXT("TE HAN COGIDO\nVuelves a la entrada de la base."), 4.0f);
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
		if (Cyl) Add(Cyl, CellDoor + FVector(i * 20.0f, 0.0f, 110.0f), FVector(0.05f, 0.05f, 2.2f));
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
	ShowMessage(TEXT("CELDA ABIERTA\nVidal abre, se aparta al rincon y se queda rezando de cara a la pared. No dara la alarma.\nTus cosas las tiene Peris en la sala de guardia."), 8.0f);
}

ATarsisGuard* ATarsisDirector::TakedownTarget() const
{
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P) return nullptr;
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
	ShowMessage(FString::Printf(TEXT("%s DERRIBADO\nDespertara en un rato. Si otro guardia lo ve en el suelo, dara la alarma."), *G->GuardName.ToUpper()), 4.0f);
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
		PlayerLight = FMath::Lerp(PlayerLight, L, 0.5f);
	}

	if (MessageT > 0.0f) MessageT -= DeltaSeconds;
	if (RadioT > 0.0f) RadioT -= DeltaSeconds;
	if (CheckT > 0.0f) CheckT -= DeltaSeconds;
	if (SubtitleT > 0.0f) SubtitleT -= DeltaSeconds;
	if (ReportWait > 0.0f) { ReportWait -= DeltaSeconds; if (ReportWait <= 0.0f) { bReport = true; MessageT = 0.0f; } }
	DetectTick();
	if (KeypadErrT > 0.0f) KeypadErrT -= DeltaSeconds;
	if (StoneT > 0.0f) StoneT -= DeltaSeconds;
	BinocularTick();
	if (!bDone && !bCine) MissionTime += DeltaSeconds;
	DragTick();
	if (bKeypad && !NearPlayer(Cell(6, 17), 260.0f)) { bKeypad = false; KeypadInput.Reset(); }
	// salida con el expediente
	if (bFile && !bDone && NearPlayer(Cell(34, 26), 260.0f)) Finish(false);
	if (DartT > 0.0f) DartT -= DeltaSeconds;
	NoiseTick(C, DeltaSeconds);
	BobTick(C, DeltaSeconds);
	SoundTick(C, DeltaSeconds);
	RainTick(DeltaSeconds);
	RadioTick(DeltaSeconds);
	PowerTick(DeltaSeconds);
	BarrierTick(DeltaSeconds);
	MusicTick(DeltaSeconds);
	// el que fue a mirar el farol roto encuentra los cristales y avisa: la base se pone en guardia un rato
	if (bLampBroken && !bLampReported && LampChecker && LampChecker->State != ETarsisGuardState::Down
		&& GateLamp && FVector::Dist2D(LampChecker->GetActorLocation(), GateLamp->GetActorLocation()) < 350.0f)
	{
		bLampReported = true;
		TensionT = FMath::Max(TensionT, 60.0f);
		if (RadioSnd) UGameplayStatics::PlaySoundAtLocation(this, RadioSnd, LampChecker->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 1.0f, 1.0f, 0.0f, Atten);
		ShowMessage(FString::Printf(TEXT("RADIO, %s: \"Farol roto en el control. Cristales por el suelo... esto no es el viento.\"\nLA BASE SE PONE EN GUARDIA."), *LampChecker->GuardName.ToUpper()), 4.5f);
	}
	// el camino hasta la garita es largo (rodea): a los 25 s de investigar lo deja a medio camino y vuelve a su ronda.
	// Si no ha llegado a verlo, se le vuelve a mandar (sale ya más cerca)
	else if (bLampBroken && !bLampReported && LampChecker && GateLamp
		&& (LampChecker->State == ETarsisGuardState::Return || LampChecker->State == ETarsisGuardState::Patrol))
	{
		const FVector P = GateLamp->GetActorLocation();
		LampChecker->HearNoise(FVector(P.X, P.Y, ExitBarrierLoc.Z));
	}
	if (HeardT > 0.0f) HeardT -= DeltaSeconds;
	// Ramos: la charla se corta si te alejas; con el expediente, si va contigo, se va al portillo
	if (ATarsisGuard* R = FindGuard(TEXT("Ramos")))
	{
		if (bChoice && FVector::Dist2D(R->GetActorLocation(), C->GetActorLocation()) > 300.0f) { bChoice = false; R->Hold(0.1f); MessageT = FMath::Min(MessageT, 1.0f); }
		if (bRamosAlly && bFile && !bRamosSent && R->State != ETarsisGuardState::Down)
		{
			bRamosSent = true;
			R->GoTo(FVector(310.0f, 4900.0f, R->GetActorLocation().Z));
			ShowMessage(TEXT("RAMOS, POR RADIO\n\"Ya lo tiene? Le espero en el portillo de la marisma, muro oeste del patio suroeste.\""), 6.0f);
		}
	}
	if (CellT > 0.0f)
	{
		CellT -= DeltaSeconds;
		if (CellT <= 0.0f) OpenCell();
	}
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
	NoteProp = AddBlock(Rest(Cell(3, 17)) + FVector(0.0f, 0.0f, 1.0f), FVector(0.21f, 0.30f, 0.01f), FLinearColor(0.9f, 0.88f, 0.8f), false);
	// carta en la litera de Ramos (barracón oeste) y botiquín del veterinario en el muro norte del patio este
	LetterProp = AddBlock(Rest(FVector(1130.0f, 2850.0f, 0.0f)) + FVector(0.0f, 0.0f, 1.0f), FVector(0.21f, 0.15f, 0.01f), FLinearColor(0.85f, 0.82f, 0.72f), false);
	AddBlock(FVector(4660.0f, 150.0f, 145.0f), FVector(0.62f, 0.1f, 0.78f), FLinearColor(0.45f, 0.44f, 0.36f), true);
	VetDoor = AddBlock(FVector(4660.0f, 156.5f, 145.0f), FVector(0.6f, 0.03f, 0.76f), FLinearColor(0.75f, 0.78f, 0.7f), true);
	// en el archivo no hay mesa: se pone una (1,2 x 0,6 m, 75 cm de alto) y el expediente encima
	const FVector Floor = Rest(Cell(9, 17));
	AddBlock(Floor + FVector(0.0f, 0.0f, 37.5f), FVector(1.2f, 0.6f, 0.75f), FLinearColor(0.16f, 0.11f, 0.07f), true);
	FileProp = AddBlock(Floor + FVector(0.0f, 0.0f, 77.0f), FVector(0.24f, 0.32f, 0.04f), FLinearColor(0.55f, 0.42f, 0.2f), false);
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
	if (Dragged) return TEXT("E   SOLTAR EL CUERPO");
	if (bChoice) return TEXT("1   VENTE CONMIGO        2   DERRIBARLO");
	if (ATarsisGuard* T = TakedownTarget())
	{
		return (T->GuardName.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase) && !bRamosTalked) ? TEXT("E   AGARRAR A RAMOS") : TEXT("E   DERRIBAR");
	}
	if (ATarsisGuard* G = DownedNear(170.0f))
	{
		if (IsIbarra(G) && !bKey) return TEXT("E   QUITARLE LA LLAVE");
		if (G->GuardName.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase) && !bVetKey && !bVetOpen) return TEXT("E   QUITARLE LA LLAVE DEL BOTIQUIN");
		if (G->bDarted) return TEXT("E   RECUPERAR EL DARDO");
		return TEXT("E   ARRASTRAR (escondelo en la sombra)");
	}
	if (!bJefOpen && NearPlayer(Cell(4, 15), 190.0f)) return bKey ? TEXT("E   ABRIR LA JEFATURA") : TEXT("JEFATURA: CERRADA CON LLAVE");
	if (!bVaultOpen && NearPlayer(Cell(6, 17), 190.0f)) return bKeypad ? TEXT("") : TEXT("E   TECLADO DEL ARCHIVO");
	if (bJefOpen && NearPlayer(Cell(3, 17), 150.0f)) return TEXT("E   LEER LA NOTA");
	if (bVaultOpen && !bFile && NearPlayer(Cell(9, 17), 160.0f)) return TEXT("E   COGER EL EXPEDIENTE LH-07");
	if (!bLetter && NearPlayer(FVector(1130.0f, 2850.0f, 0.0f), 150.0f)) return TEXT("E   LEER LA CARTA");
	if (!bVetOpen && NearPlayer(FVector(4660.0f, 300.0f, 0.0f), 170.0f)) return bVetKey ? TEXT("E   ABRIR EL BOTIQUIN") : TEXT("E   BOTIQUIN DEL VETERINARIO");
	if (NearPlayer(FVector(310.0f, 4900.0f, 0.0f), 220.0f)) return TEXT("E   PORTILLO DE LA MARISMA");
	if (NearPlayer(GeneratorLoc, 230.0f)) return bPowerOff ? TEXT("GENERADOR: PARADO") : TEXT("E   CORTAR EL GENERADOR (apaga las luces)");
	return FString();
}

FString ATarsisDirector::Objective() const
{
	if (bDone) return TEXT("MISION CUMPLIDA");
	if (bFile) return TEXT("Sal por el control de salida (esquina sureste)");
	if (bVaultOpen) return TEXT("Coge el expediente LH-07 del archivo");
	if (bNoteRead) return TEXT("Abre el archivo con la clave de la nota");
	if (bJefOpen) return TEXT("Registra la mesa de Alarcon en la jefatura");
	if (bKey) return TEXT("Abre la jefatura (se entra por el barracon oeste)");
	return TEXT("Consigue la llave de la jefatura: la lleva Ibarra (patio norte)");
}

void ATarsisDirector::Interact()
{
	if (bCine) { SkipCine(); return; }
	if (bDone) return;
	if (Dragged) { StopDrag(); ShowMessage(TEXT("CUERPO ESCONDIDO\nEn la sombra, los guardias no lo ven si no pasan muy cerca."), 3.0f); return; }
	if (bChoice) { bChoice = false; if (ATarsisGuard* R = FindGuard(TEXT("Ramos"))) R->Hold(0.1f); MessageT = 0.0f; return; }
	if (ATarsisGuard* T = TakedownTarget())
	{
		if (T->GuardName.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase) && !bRamosTalked)
		{
			bRamosTalked = true;
			bRamosKnown = true;
			bChoice = true;
			T->Hold(25.0f);
			ShowMessage(TEXT("RAMOS, EL CUARTELERO\n\"No me haga nada. El jueves bajo con los partes y no pienso volver.\"\n\"Llevo la llave del botiquin del veterinario: dentro hay una pistola de dardos. Si me saca de aqui, es suya.\"\n1   \"Vente conmigo\"          2   Derribarlo"), 25.0f);
			return;
		}
		Takedown();
		return;
	}
	if (ATarsisGuard* G = DownedNear(170.0f))
	{
		if (G->GuardName.Equals(TEXT("Ramos"), ESearchCase::IgnoreCase) && !bVetKey && !bVetOpen)
		{
			bVetKey = true;
			bRamosKnown = true;
			ShowMessage(TEXT("LLAVE DE RAMOS\n\"Botiquin - veterinario\". Esta en el muro norte del patio este."), 4.0f);
			return;
		}
		if (IsIbarra(G) && !bKey)
		{
			bKey = true;
			ShowMessage(TEXT("LLAVE DE LA JEFATURA\nSe la quitas a Ibarra del cinturon. Ahora puedes arrastrarlo a la sombra (E)."), 5.0f);
			Checkpoint(TEXT("LA LLAVE DE IBARRA"));
			return;
		}
		if (G->bDarted)
		{
			G->bDarted = false;
			++Darts;
			ShowMessage(FString::Printf(TEXT("DARDO RECUPERADO\nSe lo sacas del cuello a %s. Tienes %d."), *G->GuardName, Darts), 3.0f);
			return;
		}
		StartDrag(G);
		return;
	}
	if (!bJefOpen && NearPlayer(Cell(4, 15), 190.0f))
	{
		if (!bKey) { ShowMessage(TEXT("JEFATURA CERRADA\nHace falta la llave. La lleva el sargento Ibarra."), 3.5f); return; }
		bJefOpen = true;
		if (DoorL) { DoorL->DestroyComponent(); DoorL = nullptr; }
		ShowMessage(TEXT("JEFATURA ABIERTA\nEl despacho de Alarcon. Al fondo, la puerta blindada del archivo."), 4.0f);
		Checkpoint(TEXT("LA JEFATURA"));
		return;
	}
	if (!bVaultOpen && NearPlayer(Cell(6, 17), 190.0f))
	{
		bKeypad = !bKeypad;
		KeypadInput.Reset();
		return;
	}
	if (bJefOpen && NearPlayer(Cell(3, 17), 150.0f))
	{
		bNoteRead = true;
		ShowMessage(TEXT("MESA DE ALARCON\nUna Vulgata abierta por el salmo CXXIX: \"De profundis clamavi ad te, Domine\".\nEn el margen, a lapiz: \"Ella tambien clama. Nadie la oye. - A.\"\nUna nota: \"Clave: la de siempre. No apuntar.\""), 12.0f);
		return;
	}
	if (!bLetter && NearPlayer(FVector(1130.0f, 2850.0f, 0.0f), 150.0f))
	{
		bLetter = true;
		bRamosKnown = true;
		if (LetterProp) { LetterProp->DestroyComponent(); LetterProp = nullptr; }
		ShowMessage(TEXT("LITERA DE RAMOS - CARTA SIN TERMINAR\n\"Padre: el jueves me toca bajar con los partes. No se lo diga a madre.\"\n\"El veterinario se dejo la pistola de dardos en el botiquin y la llave la llevo encima.\"\n\"A veces pienso en dormirlos a todos y salir andando por la marisma.\"\nEn el sobre: Julian Ramos, Trebujena."), 12.0f);
		return;
	}
	if (!bVetOpen && NearPlayer(FVector(4660.0f, 300.0f, 0.0f), 170.0f))
	{
		if (!bVetKey) { bRamosKnown = true; ShowMessage(TEXT("BOTIQUIN DEL VETERINARIO\nCandado. La llave la lleva Ramos, el cuartelero del barracon oeste."), 3.5f); return; }
		bVetOpen = true;
		Darts = 5;
		if (VetDoor) { VetDoor->DestroyComponent(); VetDoor = nullptr; }
		ShowMessage(TEXT("PISTOLA DE DARDOS\n5 dardos. Clic izquierdo: duerme sin ruido al guardia que apuntes, tambien a los de las torres."), 5.0f);
		Checkpoint(TEXT("EL BOTIQUIN"));
		return;
	}
	if (NearPlayer(FVector(310.0f, 4900.0f, 0.0f), 220.0f))
	{
		ATarsisGuard* R = FindGuard(TEXT("Ramos"));
		if (!bRamosAlly) { ShowMessage(TEXT("PORTILLO DE LA MARISMA\nCerrado. La llave la guarda el cuartelero del barracon oeste."), 3.5f); return; }
		if (!bFile) { ShowMessage(TEXT("PORTILLO DE LA MARISMA\nRamos lo abrira cuando tengas el expediente."), 3.0f); return; }
		if (!R || R->State == ETarsisGuardState::Down || FVector::Dist2D(R->GetActorLocation(), FVector(310.0f, 4900.0f, 0.0f)) > 700.0f) { ShowMessage(TEXT("ESPERA A RAMOS\nEl trae la llave del portillo."), 2.5f); return; }
		Finish(true);
		return;
	}
	if (!bPowerOff && NearPlayer(GeneratorLoc, 230.0f))
	{
		CutPower();
		return;
	}
	if (bVaultOpen && !bFile && NearPlayer(Cell(9, 17), 160.0f))
	{
		bFile = true;
		if (FileProp) { FileProp->DestroyComponent(); FileProp = nullptr; }
		ShowMessage(TEXT("EXPEDIENTE LH-07\nLo tienes. Ahora sal de la base por el control de salida, al sureste."), 5.0f);
		Checkpoint(TEXT("EL EXPEDIENTE"));
	}
}

void ATarsisDirector::KeypadKey(FKey Key)
{
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
	if (Digit < 0) { KeypadInput.LeftChopInline(1); return; }
	if (KeypadInput.Len() >= 4) KeypadInput.Reset();
	KeypadInput.AppendInt(FMath::Clamp(Digit, 0, 9));
	if (KeypadInput.Len() < 4) return;
	if (KeypadInput == VaultCode)
	{
		bVaultOpen = true;
		bKeypad = false;
		if (DoorV) { DoorV->DestroyComponent(); DoorV = nullptr; }
		ShowMessage(TEXT("ARCHIVO ABIERTO\nLa puerta blindada se abre con un chasquido."), 4.0f);
	}
	else
	{
		KeypadErrT = 1.2f;
		KeypadInput.Reset();
		ShowMessage(TEXT("CLAVE INCORRECTA"), 1.5f);
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
	ShowMessage(FString::Printf(TEXT("ARRASTRAS A %s\nLlevalo a la sombra y sueltalo con E. Si un guardia te ve con el, dara la alarma."), *G->GuardName.ToUpper()), 4.0f);
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
	if (Heard == 0) ShowMessage(TEXT("CLAC\nNadie lo ha oido."), 1.5f);
}

void ATarsisDirector::ToggleBinoculars()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	UCameraComponent* Cam = C ? C->FindComponentByClass<UCameraComponent>() : nullptr;
	if (!Cam) return;
	if (!bBinoculars && (bKeypad || Dragged)) return;
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
		ShowMessage(FString::Printf(TEXT("%s MARCADO\nLo veras aunque haya paredes por medio."), *It->GuardName.ToUpper()), 2.5f);
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
		ShowMessage(TEXT("RAMOS ESTA CONTIGO\nTe da la llave del botiquin del veterinario (muro norte del patio este).\nSigue su ronda para que no le echen en falta, y ya no te delatara."), 7.0f);
	}
	else
	{
		R->Hold(0.0f);
		R->KnockOut();
		++Takedowns;
		bRamosDowned = true;
		ShowMessage(TEXT("RAMOS DERRIBADO\nLleva encima la llave del botiquin."), 3.5f);
	}
}

FString ATarsisDirector::SideObjective() const
{
	if (bDone || !bRamosKnown) return FString();
	if (bRamosAlly && bFile) return TEXT("Otra salida: Ramos te espera en el portillo de la marisma (muro oeste, patio suroeste)");
	if (bVetOpen) return bRamosAlly ? TEXT("Ramos esta contigo: con el expediente, saldra por la marisma") : FString();
	if (bVetKey) return TEXT("Abre el botiquin del veterinario: muro norte del patio este");
	return TEXT("Ramos, el cuartelero del barracon oeste, lleva la llave del botiquin: agarralo por la espalda");
}

void ATarsisDirector::ShootDart()
{
	if (Darts <= 0 || DartT > 0.0f || bKeypad || bChoice || bDone || Dragged) return;
	APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0);
	APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!PC || !Pl) return;
	FVector Loc; FRotator Rot;
	PC->GetPlayerViewPoint(Loc, Rot);
	const FVector Fwd = Rot.Vector();
	--Darts;
	DartT = 0.8f;
	if (DartSnd) UGameplayStatics::PlaySound2D(this, DartSnd, 0.7f);
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
	if (!Best)
	{
		ShowMessage(FString::Printf(TEXT("FALLASTE\nTe quedan %d dardos."), Darts), 1.8f);
		return;
	}
	Best->KnockOut();
	Best->bDarted = true;
	++Takedowns;
	ShowMessage(FString::Printf(TEXT("%s DORMIDO\nTe quedan %d dardos."), *Best->GuardName.ToUpper(), Darts), 2.5f);
}

void ATarsisDirector::Finish(bool bByMarsh)
{
	if (bDone) return;
	bDone = true;
	bMarsh = bByMarsh;
	StopDrag();
	if (bBinoculars) ToggleBinoculars();
	FString GateLine;
	if (!bByMarsh)
	{
		// en el control, el de la garita levanta la barrera y mira hacia otro lado (sale en el plano de LS_Salida)
		BarrierT = 0.001f;
		if (GateLamp && GateLamp->GetLightComponent())
		{
			// que el plano final se vea aunque cortaras la luz; si rompiste el farol, solo la bombilla de dentro de la garita
			if (bLampBroken) GateLamp->GetLightComponent()->SetIntensity(700.0f);
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
			GateLine = FString::Printf(TEXT("\nEn la garita, %s levanta la barrera y mira hacia la marisma."), *Best->GuardName);
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
	const FString Stats = FString::Printf(TEXT("Tiempo %d:%02d   Te vieron %d   Capturas %d   Derribos %d\nSIGILO: %d puntos - %s (%s)"),
		Secs / 60, Secs % 60, Detections, Captures, Takedowns, Score, *Rank, Df[FMath::Clamp(Difficulty, 0, 2)]);
	if (bByMarsh)
	{
		ShowMessage(FString(TEXT("EL QUE NO ENTREGO\nRamos abre el portillo y rema sin encender la linterna. El expediente sigue en tu chaqueta.\nControl pierde tu rastro en la marisma.\n")) + Stats, 20.0f);
	}
	else
	{
		FString T = FString(TEXT("MISION CUMPLIDA\nSales de Tarsis con el expediente LH-07.")) + GateLine + TEXT("\n") + Stats;
		if (bRamosAlly) T += TEXT("\nRamos sale solo por la marisma y os espera en el camino de Trebujena.");
		ShowMessage(T, 15.0f);
	}
	BuildReport();
	ReportWait = bByMarsh ? 20.0f : 15.0f;
}

// ---------------------------------------------------------------- pasos, carrera y balanceo

void ATarsisDirector::SprintOn()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || Dragged || bDone) return;
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
		// dentro suena menos; con lluvia, el agua tapa los pasos
		const float Surf = (bIndoor ? 0.6f : 1.0f) * (Weather == 1 && !bIndoor ? 0.6f : 1.0f);
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
	for (int32 i = 1; i <= 3; ++i)
	{
		if (USoundBase* S = LoadSnd(*FString::Printf(TEXT("paso_grava_%d"), i))) StepGravel.Add(S);
		if (USoundBase* S = LoadSnd(*FString::Printf(TEXT("paso_cemento_%d"), i))) StepConcrete.Add(S);
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
			if (L->IsA<USpotLightComponent>()) L->SetVolumetricScatteringIntensity(4.0f);
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

void ATarsisDirector::StepSound(const FVector& Where, bool bIndoorStep, float Volume, bool b3D)
{
	const TArray<TObjectPtr<USoundBase>>& Set = bIndoorStep ? StepConcrete : StepGravel;
	if (Set.Num() == 0) return;
	USoundBase* S = Set[FMath::RandRange(0, Set.Num() - 1)];
	const float Pitch = FMath::FRandRange(0.9f, 1.1f);
	if (b3D) UGameplayStatics::PlaySoundAtLocation(this, S, Where, Volume, Pitch, 0.0f, Atten);
	else UGameplayStatics::PlaySound2D(this, S, Volume, Pitch);
}

void ATarsisDirector::SoundTick(ACharacter* C, float DeltaSeconds)
{
	// tus pasos: uno cada ~1,4 m (agachado, flojito)
	const float Speed = C->GetCharacterMovement()->IsFalling() ? 0.0f : C->GetVelocity().Size2D();
	if (Speed > 40.0f)
	{
		PlayerStride += Speed * DeltaSeconds;
		const float Stride = C->bIsCrouched ? 90.0f : (bSprint ? 190.0f : 140.0f);
		if (PlayerStride >= Stride)
		{
			PlayerStride = 0.0f;
			StepSound(C->GetActorLocation(), bIndoor, C->bIsCrouched ? 0.15f : (bSprint ? 0.8f : 0.45f), false);
		}
	}
	// pasos de los guardias, en 3D: los oyes acercarse aunque haya una pared
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Down || It->bTowerSentry) continue;
		const float GS = It->GetVelocity().Size2D();
		if (GS < 40.0f) continue;
		const TObjectPtr<ATarsisGuard> K(*It);
		float& D = GuardStride.FindOrAdd(K);
		D += GS * DeltaSeconds;
		if (D < (GS > 300.0f ? 170.0f : 120.0f)) continue;
		D = 0.0f;
		if (FVector::Dist(It->GetActorLocation(), C->GetActorLocation()) > 1600.0f) continue;
		StepSound(It->GetActorLocation(), IndoorAt(It->GetActorLocation(), *It), GS > 300.0f ? 1.0f : 0.75f, true);
		if (bSubtitles)
		{
			const float Dm = FVector::Dist2D(It->GetActorLocation(), C->GetActorLocation()) / 100.0f;
			if (SubtitleT <= 0.0f || Dm < SubtitleDist)
			{
				SubtitleDist = Dm;
				Subtitle = FString::Printf(TEXT("[%s - %s, %s, %d m]"), GS > 300.0f ? TEXT("CORRE") : TEXT("PASOS"), *It->GuardName.ToUpper(), *Direction(It->GetActorLocation()), FMath::RoundToInt(Dm));
				SubtitleT = 1.2f;
			}
		}
	}
	// viento y lluvia: más bajos bajo techo
	if (WindComp) WindComp->SetVolumeMultiplier(bIndoor ? 0.12f : (Weather == 1 ? 0.2f : 0.3f));
	if (RainComp) RainComp->SetVolumeMultiplier(bIndoor ? 0.15f : 0.45f);
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
	static const TCHAR* Texts[] = {
		TEXT("DESPEJADO\nLa vista y el oido de los guardias, normales."),
		TEXT("LLUVIA\nLos guardias ven menos de lejos y el agua tapa tus pasos fuera."),
		TEXT("NIEBLA\nLos guardias ven mucho menos de lejos; tus pasos se oyen igual.") };
	ShowMessage(Texts[Weather], 3.5f);
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
		F->SetFogDensity(FMath::Min(0.2f, BaseFog * (Weather == 2 ? 4.0f : (Weather == 1 ? 1.8f : 1.0f))));
		// niebla volumétrica: las farolas y los focos dibujan haces; de noche, sin ella, la niebla casi no se ve
		F->SetVolumetricFog(Weather != 0);
		F->SetVolumetricFogScatteringDistribution(Weather == 2 ? 0.6f : 0.4f);
		F->SetVolumetricFogExtinctionScale(Weather == 2 ? 2.0f : 1.0f);
		F->SetFogInscatteringColor(Weather == 2 ? FLinearColor(0.10f, 0.11f, 0.13f) : (Weather == 1 ? FLinearColor(0.05f, 0.06f, 0.07f) : BaseFogColor));
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
		Best->HearNoise(G->KnockLoc);
		if (RadioSnd) UGameplayStatics::PlaySoundAtLocation(this, RadioSnd, Best->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 1.0f, 1.0f, 0.0f, Atten);
		ShowMessage(FString::Printf(TEXT("RADIO: \"%s, responde.\" ... Nada.\n%s va a ver que pasa donde le toca la ronda."),
			*G->GuardName, *Best->GuardName), 4.5f);
	}
}

// ---------------------------------------------------------------- generador

void ATarsisDirector::CutPower()
{
	bPowerOff = true;
	bPowerCutOnce = true;
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
		// el aviso va aparte, a la caja de radio (ShowMessage lo manda allí si empieza por RADIO)
		ShowMessage(TEXT("GENERADOR CORTADO\nSe apagan farolas y focos: la oscuridad te esconde. La base se pone en guardia."), 5.0f);
		ShowMessage(FString::Printf(TEXT("RADIO: \"Se ha ido la luz en toda la base! %s, mira el generador.\""), *Repairer->GuardName), 5.0f);
	}
	else
	{
		ShowMessage(TEXT("GENERADOR CORTADO\nSe apagan farolas y focos: la oscuridad te esconde. La base se pone en guardia."), 4.5f);
	}
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
	ShowMessage(bByGuard && Repairer
		? FString::Printf(TEXT("VUELVE LA LUZ\n%s ha arrancado el generador."), *Repairer->GuardName)
		: FString(TEXT("VUELVE LA LUZ (A MEDIAS)\nEl generador de reserva no da para todo: la mitad de las farolas se quedan apagadas.")), 4.0f);
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
			ShowMessage(FString::Printf(TEXT("RADIO: \"%s, como va eso?\" - \"Ya casi.\""), *Repairer->GuardName), 2.5f);
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
			ShowMessage(FString::Printf(TEXT("RADIO: \"%s, como va eso?\" ... Nada.\nEntra el generador de reserva (solo la mitad de las luces) y mandan gente corriendo al generador. LA BASE ESTA EN ALERTA."), *Name), 5.0f);
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
		ShowMessage(TEXT("LOST HORIZON: DE PROFUNDIS\nMision 1 - Tarsis\nUna base en la marisma. Esta noche, el expediente LH-07 sale de ahi contigo.\n\n(E o Espacio para saltar)"), 30.0f);
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
		if (USpotLightComponent* L = Cast<USpotLightComponent>(GateLamp->GetLightComponent()))
		{
			L->SetIntensityUnits(ELightUnits::Lumens);
			L->SetIntensity(3000.0f);
			L->SetAttenuationRadius(1500.0f);
			L->SetOuterConeAngle(55.0f);
			L->SetInnerConeAngle(35.0f);
			L->SetLightColor(FLinearColor(1.0f, 0.78f, 0.5f));
			L->SetCastShadows(false);
			L->SetVolumetricScatteringIntensity(1.5f);
		}
	}
}

void ATarsisDirector::BarrierTick(float DeltaSeconds)
{
	if (!BarrierArm) return;
	if (BarrierT > 0.0f && BarrierT < 1.0f) BarrierT = FMath::Min(1.0f, BarrierT + DeltaSeconds / 2.5f);
	const float Pitch = 80.0f * FMath::SmoothStep(0.0f, 1.0f, BarrierT);
	const FRotator R(Pitch, ExitBarrierYaw, 0.0f);
	const FVector Pivot = ExitBarrierLoc + FVector(0.0f, 0.0f, 100.0f);
	BarrierArm->SetWorldLocationAndRotation(Pivot + R.RotateVector(FVector(ExitBarrierLength * 0.5f, 0.0f, 0.0f)), R);
}

// ---------------------------------------------------------------- farol de la garita: se rompe de un disparo

bool ATarsisDirector::ShootLamp(const FVector& From, const FVector& Fwd, float MaxT)
{
	if (!GateLamp || bLampBroken) return false;
	ULightComponent* L = GateLamp->GetLightComponent();
	if (!L) return false;
	const FVector P = GateLamp->GetActorLocation();
	const float T = FVector::DotProduct(P - From, Fwd);
	if (T < 0.0f || T > MaxT || FVector::Dist(From + Fwd * T, P) > 40.0f) return false;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisFarol), true, this);
	if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Q.AddIgnoredActor(Pl);
	Q.AddIgnoredActor(GateLamp);
	FHitResult Hit;
	if (GetWorld()->LineTraceSingleByChannel(Hit, From, P, ECC_Visibility, Q) && FVector::Dist(Hit.ImpactPoint, P) > 60.0f) return false;
	bLampBroken = true;
	L->SetVisibility(false);
	OffLights.Remove(L);   // si hay apagón, al volver la luz sigue roto
	if (StoneSnd) UGameplayStatics::PlaySoundAtLocation(this, StoneSnd, P, 1.0f, 1.6f, 0.0f, Atten);
	// el ruido de cristales llama al guardia más cercano, que viene a mirar
	ATarsisGuard* Best = nullptr;
	float BestD = 2500.0f;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Down || It->bTowerSentry || It->bAlly) continue;
		const float D = FVector::Dist(It->GetActorLocation(), P);
		if (D < BestD) { BestD = D; Best = *It; }
	}
	if (Best) Best->HearNoise(FVector(P.X, P.Y, ExitBarrierLoc.Z));
	LampChecker = Best;
	ShowMessage(FString::Printf(TEXT("FAROL ROTO\nEl control queda a oscuras.%s Te quedan %d dardos."),
		Best ? *FString::Printf(TEXT(" %s ha oido los cristales y viene a mirar."), *Best->GuardName) : TEXT(""), Darts), 4.0f);
	return true;
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
	S->Weather = Weather;
	bHasSave = UGameplayStatics::SaveGameToSlot(S, TEXT("TarsisPartida"), 0) || bHasSave;
}

bool ATarsisDirector::LoadCheckpoint()
{
	UTarsisSave* S = Cast<UTarsisSave>(UGameplayStatics::LoadGameFromSlot(TEXT("TarsisPartida"), 0));
	APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!S || !P) return false;
	StopDrag();
	bKeypad = false;
	if (bBinoculars) ToggleBinoculars();
	// la misión como estaba: puertas abiertas, objetos cogidos
	bKey = S->bKey;
	bJefOpen = S->bJefOpen;
	bNoteRead = S->bNoteRead;
	bVaultOpen = S->bVaultOpen;
	bFile = S->bFile;
	bLetter = S->bLetter;
	bVetKey = S->bVetKey;
	bVetOpen = S->bVetOpen;
	bRamosKnown = S->bRamosKnown || bLetter || bVetKey;
	Darts = S->Darts;
	MissionTime = S->MissionTime;
	Captures = FMath::Max(Captures, S->Captures);
	if (bJefOpen && DoorL) { DoorL->DestroyComponent(); DoorL = nullptr; }
	if (bVaultOpen && DoorV) { DoorV->DestroyComponent(); DoorV = nullptr; }
	if (bFile && FileProp) { FileProp->DestroyComponent(); FileProp = nullptr; }
	if (bLetter && LetterProp) { LetterProp->DestroyComponent(); LetterProp = nullptr; }
	if (bVetOpen && VetDoor) { VetDoor->DestroyComponent(); VetDoor = nullptr; }
	if (S->bLampBroken && GateLamp && GateLamp->GetLightComponent() && !bLampBroken)
	{
		bLampBroken = true;
		GateLamp->GetLightComponent()->SetVisibility(false);
		OffLights.Remove(GateLamp->GetLightComponent());
	}
	if (S->Weather != Weather) SetWeather(S->Weather);
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
	ShowMessage(FString::Printf(TEXT("PARTIDA CARGADA\nUltimo punto de control: %s."), *CheckpointName), 3.5f);
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
	if (bMenu && MenuPage == 1 && Key == EKeys::Escape) { MenuPage = 0; MenuSel = 0; return; }
	if (Key == EKeys::P || Key == EKeys::Escape)
	{
		if (bKeypad && Key == EKeys::Escape) { bKeypad = false; KeypadInput.Reset(); return; }   // Esc cierra antes el teclado del archivo (y borra lo tecleado)
		if (!bCine || bMenu) TogglePause();
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
			ShowMessage(FString::Printf(TEXT("CALIDAD GRAFICA\nElegida segun tu PC: %s. Se cambia en Pausa (P)."),
				OptQuality == 0 ? TEXT("BAJA") : OptQuality == 1 ? TEXT("MEDIA") : OptQuality == 2 ? TEXT("ALTA") : TEXT("EPICA")), 5.0f);
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
	static const TCHAR* N[NumActions] = { TEXT("AGACHARSE"), TEXT("USAR / DERRIBAR (E)"), TEXT("LANZAR PIEDRA"), TEXT("PRISMATICOS"), TEXT("CORRER"), TEXT("CAMBIAR CLIMA") };
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
	if (bPowerOff) S += TEXT("   sin luz: busca la sombra de las linternas");
	S += TEXT("   P pausa");
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
	if (MusicBase) MusicBase->SetVolumeMultiplier(FMath::Max(0.001f, Base * OptMusic));
	if (MusicTen) MusicTen->SetVolumeMultiplier(FMath::Max(0.001f, 0.5f * MusicTension * (1.0f - 0.5f * MusicAlert) * OptMusic));
	if (MusicAlr) MusicAlr->SetVolumeMultiplier(FMath::Max(0.001f, 0.55f * MusicAlert * OptMusic));
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
		if (Now != Prev && It->State == ETarsisGuardState::Alert && !It->bRadioCall && !It->bAlly) ++Detections;
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
	L.Add(TEXT("Base de Tarsis - Del capitan Alarcon al Mando de la Zona Sur"));
	L.Add(TEXT(""));
	L.Add(bMarsh ? TEXT("Anoche un intruso huyo por la marisma con el expediente LH-07. Se le perdio el rastro en los canales.")
		: TEXT("Anoche un intruso salio por el control de salida con el expediente LH-07. El de la garita no vio nada."));
	if (Detections == 0) L.Add(TEXT("Nadie llego a verlo. Hay quien duda de que existiera."));
	else L.Add(FString::Printf(TEXT("Fue visto %d %s, pero las descripciones no coinciden."), Detections, Detections == 1 ? TEXT("vez") : TEXT("veces")));
	if (Captures > 0) L.Add(TEXT("Estuvo en el calabozo y salio de el. Se abre expediente al cabo Vidal."));
	if (Downed.Num() > 0) L.Add(FString::Printf(TEXT("Amanecieron en el suelo, aturdidos o dormidos: %s."), *FString::Join(Downed, TEXT(", "))));
	if (bVetOpen) L.Add(TEXT("El botiquin del veterinario esta abierto y falta la pistola de dardos."));
	if (bKey) L.Add(TEXT("Al sargento Ibarra le falta la llave de la jefatura. Se cambiara la cerradura."));
	if (bLampBroken) L.Add(TEXT("El farol del control aparecio roto de un disparo. Se ha pedido otro a Sevilla."));
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
	if (bRamosAlly) Cons.Add(TEXT("Ramos te espera fuera"));
	else if (bRamosDowned) Cons.Add(TEXT("Ramos desconfia de todos"));
	if (bKey) Cons.Add(TEXT("cerradura nueva en la jefatura"));
	L.Add(Cons.Num() > 0 ? FString::Printf(TEXT("LA PROXIMA NOCHE: %s."), *FString::Join(Cons, TEXT(", "))) : FString(TEXT("LA PROXIMA NOCHE: todo sigue igual. Nadie sabe que estuviste.")));
	L.Add(FString::Printf(TEXT("SIGILO: %d puntos - %s"), Score, *Rank));
	L.Add(TEXT(""));
	L.Add(TEXT("P: menu (salir o cargar el ultimo punto de control)"));
	// se guarda para la misión 2
	UTarsisSave* S = Cast<UTarsisSave>(UGameplayStatics::CreateSaveGameObject(UTarsisSave::StaticClass()));
	if (!S) return;
	S->bByMarsh = bMarsh;
	S->Detections = Detections;
	S->Takedowns = Takedowns;
	S->Captures = Captures;
	S->MissionTime = MissionTime;
	S->bPowerCut = bPowerCutOnce;
	S->bReserveHalf = bReserveHalf;
	S->bLampBroken = bLampBroken;
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
