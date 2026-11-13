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
#include "Components/SpotLightComponent.h"
#include "Components/PointLightComponent.h"
#include "HAL/IConsoleManager.h"
#include "Components/MeshComponent.h"
#include "Materials/MaterialInterface.h"

ATarsisDirector::ATarsisDirector()
{
	PrimaryActorTick.bCanEverTick = true;
}

void ATarsisDirector::BeginPlay()
{
	Super::BeginPlay();
	SetupMission();
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
	if (InputComponent)
	{
		InputComponent->BindKey(EKeys::C, IE_Pressed, this, &ATarsisDirector::ToggleCrouch);
		InputComponent->BindKey(EKeys::LeftControl, IE_Pressed, this, &ATarsisDirector::ToggleCrouch);
		InputComponent->BindKey(EKeys::E, IE_Pressed, this, &ATarsisDirector::Interact);
		InputComponent->BindKey(EKeys::Q, IE_Pressed, this, &ATarsisDirector::ThrowStone);
		InputComponent->BindKey(EKeys::B, IE_Pressed, this, &ATarsisDirector::ToggleBinoculars);
		InputComponent->BindKey(EKeys::Y, IE_Pressed, this, &ATarsisDirector::CycleWeather);
		InputComponent->BindKey(EKeys::LeftShift, IE_Pressed, this, &ATarsisDirector::SprintOn);
		InputComponent->BindKey(EKeys::LeftShift, IE_Released, this, &ATarsisDirector::SprintOff);
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
	}
	bPlayerReady = true;
	ShowMessage(TEXT("TARSIS, DE NOCHE\nBusca la sombra. Agachado (C) te ven menos y por los huecos de las vallas se pasa agachado.\nEl expediente LH-07 esta en el archivo de la jefatura. La llave la lleva el sargento Ibarra.\nQ lanza una piedra para distraer. B prismaticos: marca a los guardias que mires.\nTus pasos se oyen: corriendo (Shift) y sobre la gravilla mas que dentro. Agachado, nada."), 11.0f);
}

void ATarsisDirector::ShowMessage(const FString& Text, float Seconds)
{
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
	if (KeypadErrT > 0.0f) KeypadErrT -= DeltaSeconds;
	if (StoneT > 0.0f) StoneT -= DeltaSeconds;
	BinocularTick();
	if (!bDone) MissionTime += DeltaSeconds;
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
	if (!Best)
	{
		ShowMessage(FString::Printf(TEXT("FALLASTE\nTe quedan %d dardos."), Darts), 1.8f);
		return;
	}
	Best->KnockOut();
	++Takedowns;
	ShowMessage(FString::Printf(TEXT("%s DORMIDO\nTe quedan %d dardos."), *Best->GuardName.ToUpper(), Darts), 2.5f);
}

void ATarsisDirector::Finish(bool bByMarsh)
{
	if (bDone) return;
	bDone = true;
	bMarsh = bByMarsh;
	const int32 Secs = FMath::FloorToInt(MissionTime);
	const FString Stats = FString::Printf(TEXT("Tiempo %d:%02d   Capturas %d   Derribos %d"), Secs / 60, Secs % 60, Captures, Takedowns);
	if (bByMarsh)
	{
		ShowMessage(FString(TEXT("EL QUE NO ENTREGO\nRamos abre el portillo y rema sin encender la linterna. El expediente sigue en tu chaqueta.\nControl pierde tu rastro en la marisma.\n")) + Stats, 20.0f);
	}
	else
	{
		FString T = FString(TEXT("MISION CUMPLIDA\nSales de Tarsis con el expediente LH-07.\n")) + Stats;
		if (bRamosAlly) T += TEXT("\nRamos sale solo por la marisma y os espera en el camino de Trebujena.");
		ShowMessage(T, 15.0f);
	}
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
		PlayerNoise = (C->bIsCrouched || bAir || Speed < 60.0f) ? 0.0f : Speed * 1.15f * Surf;
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
		It->AlertBoost = TensionT > 0.0f ? 1.5f : 1.0f;
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
	PowerT = 60.0f;
	RepairT = 0.0f;
	OffLights.Reset();
	// se apagan farolas, focos de las torres y luces de dentro (el cielo y la luna siguen)
	for (TActorIterator<ALight> It(GetWorld()); It; ++It)
	{
		ULocalLightComponent* L = Cast<ULocalLightComponent>(It->GetLightComponent());
		if (!L || !L->IsVisible()) continue;
		L->SetVisibility(false);
		OffLights.Add(L);
	}
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
		Repairer->HearNoise(GeneratorLoc);
		if (RadioSnd) UGameplayStatics::PlaySoundAtLocation(this, RadioSnd, Repairer->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f), 1.0f, 1.0f, 0.0f, Atten);
		ShowMessage(FString::Printf(TEXT("GENERADOR CORTADO\nSe apagan farolas y focos: la oscuridad te esconde. La base se pone en guardia.\nRADIO: \"%s, mira el generador.\""), *Repairer->GuardName), 5.0f);
	}
	else
	{
		ShowMessage(TEXT("GENERADOR CORTADO\nSe apagan farolas y focos: la oscuridad te esconde. La base se pone en guardia."), 4.5f);
	}
}

void ATarsisDirector::RestorePower(bool bByGuard)
{
	bPowerOff = false;
	PowerT = 0.0f;
	for (ULightComponent* L : OffLights)
	{
		if (L) L->SetVisibility(true);
	}
	OffLights.Reset();
	WindowsDark(false);
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It) It->SetFlashlight(false);
	if (HumComp) HumComp->Play();
	ShowMessage(bByGuard && Repairer
		? FString::Printf(TEXT("VUELVE LA LUZ\n%s ha arrancado el generador."), *Repairer->GuardName)
		: FString(TEXT("VUELVE LA LUZ\nEl generador de reserva ha entrado solo.")), 3.5f);
	Repairer = nullptr;
}

void ATarsisDirector::PowerTick(float DeltaSeconds)
{
	if (!bPowerOff) return;
	// sin luz, los guardias de suelo sacan la linterna (también el que se despierta)
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It) It->SetFlashlight(true);
	PowerT -= DeltaSeconds;
	if (PowerT <= 0.0f) { RestorePower(false); return; }
	// el enviado lo arregla tras RepairSeconds junto al generador; si lo derribas antes, la luz tarda lo que le quede
	if (Repairer && Repairer->State != ETarsisGuardState::Down && Repairer->State != ETarsisGuardState::Alert)
	{
		if (FVector::Dist2D(Repairer->GetActorLocation(), GeneratorLoc) < 320.0f)
		{
			RepairT += DeltaSeconds;
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
