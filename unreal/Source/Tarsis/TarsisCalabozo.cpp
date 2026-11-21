// Lost Horizon: De Profundis — el calabozo (tanda 35). Parte de ATarsisDirector: ver el bloque «tanda 35» de
// TarsisDirector.h. Es el puzle de la version web: tras la reja, el cabo Vidal reza. Se sale convenciendole en tres
// pasos (no con amenazas ni sobornos: con lo que hayas averiguado de lo que hay debajo, o rezando con el si has leido
// el salmo), o con la llave que su hermano dejo bajo la losa suelta del rincon. Tres errores y Vidal deja de escuchar.
// Cambios respecto a la web, por coherencia: Halloran no esta en esta celda (sus pistas las da Control por el codec,
// control_celda); nadie ensena papeles (te han registrado: lo que vale es lo que has leido u oido); lo que dices saber
// depende de como lo supiste; en vez de los perros, el viento; el hermano consta como desertor; y salir con la llave
// tiene precio: Vidal no lo ha visto, asi que a los CellAlertSeconds alguien encuentra la celda vacia y la base queda
// en guardia. Si le convences, calla (bandera vidal_calla).
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "Components/PointLightComponent.h"
#include "Kismet/GameplayStatics.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

// Al calabozo: lo llama la primera captura (y las pruebas, para encerrar otra vez)
void ATarsisDirector::LockInCell(APawn* Player)
{
	if (!Player || CellSpot.IsZero()) return;
	AController* Ctl = Player->GetController();
	const FRotator R(0.0f, CellYaw, 0.0f);
	Player->TeleportTo(CellSpot, R);
	if (Ctl) Ctl->SetControlRotation(R);
	CalmBase();
	CloseCell();
	PlaySfx(TEXT("reja"), CellDoor + FVector(0.0f, 0.0f, 100.0f));
	CellT = bCellPuzzle ? 0.0f : CellTime;
	CellReset();
	if (bCellPuzzle) { SpawnVidal(); FaceVidal(VidalYaw); }
	if (bCellPuzzle) TakeGear();   // te han registrado: lo que llevabas esta en la sala de guardia
	// lo que estuviera sonando en la radio ya no importa: llama Control, que es quien sabe con quien hablas ahi dentro
	if (bCellPuzzle && !bCodec) { CodecPending = NAME_None; CodecRingT = 0.0f; CellCallT = 9.0f; }
	ShowMessage(Tx(TEXT("calabozo"), TEXT("CALABOZO\nDespiertas tras la reja. Al otro lado, a un paso de la reja, el cabo Vidal hace guardia y reza en voz baja.\nHabla con el por la reja. Vidal no es como los demas.")), 8.0f);
}

// Te han cogido: nadie sigue en alerta por alguien que ya esta preso (los de la torre te veian en la escena de la
// captura y volvian a dar la voz; los mandados por radio seguian corriendo al sitio)
void ATarsisDirector::CalmBase()
{
	TensionT = 0.0f;
	LastKnownT = 0.0f;
	// lo que quedaba en marcha de la persecucion: el alto, los refuerzos pedidos y la pregunta de la central
	bHalt = bFleeing = false;
	HaltT = StillT = UnaimedT = AimHoldT = 0.0f;
	BackupT = 0.0f;
	bBackupSent = false;
	Aimer = nullptr;
	ArrestGuard = nullptr;
	if (bRadioAsk) { bRadioAsk = false; MessageT = FMath::Min(MessageT, 0.3f); }
	RadioAskGuard = nullptr;
	RadioAskT = 0.0f;
	// los tumbados y los aturdidos tambien: a los suyos los han levantado, y nadie se despierta buscandote
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->bAlly) continue;
		It->Recover();
	}
	DogReset();
	++Calms;
}

bool ATarsisDirector::InCell() const
{
	return Bars.Num() > 0 && NearPlayer(CellSpot, 480.0f);
}

FString ATarsisDirector::CellPrompt() const
{
	if (!bCellPuzzle || !InCell() || bCellAsk) return FString();
	if (!HasFlag(FName(TEXT("llave_celda"))) && NearPlayer(CellSlab, 110.0f)) return Tx(TEXT("p_losa"), TEXT("E   LOSA SUELTA"));
	if (NearPlayer(CellDoor, 170.0f))
	{
		if (!bVidalGone) return Tx(TEXT("p_vidal"), TEXT("E   HABLAR CON EL CABO VIDAL"));
		return HasFlag(FName(TEXT("llave_celda"))) ? Tx(TEXT("p_reja_llave"), TEXT("E   ABRIR LA REJA CON LA LLAVE")) : Tx(TEXT("p_vidal_ido"), TEXT("VIDAL YA NO ESCUCHA"));
	}
	return FString();
}

bool ATarsisDirector::CellInteract()
{
	if (!bCellPuzzle || !InCell()) return false;
	if (bCellAsk) return true;
	const bool bKeyNow = HasFlag(FName(TEXT("llave_celda")));
	if (!bKeyNow && NearPlayer(CellSlab, 110.0f))
	{
		SetFlag(FName(TEXT("llave_celda")));
		PlaySfx(TEXT("recoger"), CellSlab + FVector(0.0f, 0.0f, 20.0f));
		if (SlabProp) SlabProp->SetRelativeRotation(FRotator(0.0f, 24.0f, 9.0f));
		ShowMessage(Tx(TEXT("losa"), TEXT("LOSA SUELTA\nBajo la losa, en un trapo, una llave de hierro y una medalla con un nombre rayado a navaja: VIDAL, J.\nLa llave encaja en la reja. La medalla, a Vidal, le dira mas que tu.")), 8.0f);
		return true;
	}
	if (!NearPlayer(CellDoor, 170.0f)) return false;
	if (bVidalGone)
	{
		if (bKeyNow) { OpenCellWith(true); return true; }
		ShowMessage(Tx(TEXT("vidal_ido"), TEXT("CABO VIDAL\nReza de cara a la pared y no se vuelve.\nEn el rincon, a la derecha de la reja, una losa baila bajo el pie.")), 5.0f);
		return true;
	}
	CellAsk();
	return true;
}

// Las tres preguntas (revisadas en la tanda 37: antes, si te cogian pronto, no habia respuesta buena y nada lo decia).
// Todo lo que hace falta se puede conseguir sin salir de la celda: lo de abajo te lo cuenta Control por la radio
// (control_celda) y lo que a Vidal le importa esta bajo la losa (la medalla de su hermano). Lo que hayas averiguado
// fuera (la voz sin nombre, el expediente, el salmo) tambien vale. Contestar sin saber no cuenta como error: Vidal
// dice que no basta y el juego dice que te falta. Solo cuentan amenazar, sobornar y mentir. Con la llave en la mano
// hay una cuarta respuesta: callar y abrir.
// Tanda 38: la conversacion se podia perder (tres errores y Vidal callaba para siempre) y pedia saber cosas que no
// tenias delante, asi que probando respuestas no avanzaba nunca. Ahora es una conversacion: ninguna respuesta la
// cierra, Vidal contesta y vuelve a preguntar el solo, y en cada paso hay una respuesta buena que no pide nada
// (escucharle, decir lo que se oye, rezar con el). Lo que hayas averiguado solo cambia como lo dices. La buena no
// esta siempre en el mismo sitio: en pantalla, el hueco i ensena la respuesta CellOrder[paso][i].
static const int32 CellOrder[3][3] = { { 0, 1, 2 }, { 2, 0, 1 }, { 1, 2, 0 } };

void ATarsisDirector::CellAsk()
{
	CellNextT = 0.0f;
	const bool bHasKey = HasFlag(FName(TEXT("llave_celda")));
	const bool bTold = CodecTaken.Contains(TEXT("control_celda"));
	const bool bKnows = bCodecVoiceHeard || bFile || bTold;
	const bool bPsalm = bNoteRead || bCellHeardPrayer || CodecTaken.Contains(TEXT("roig_salmo"));
	CellOptions.Init(FString(), 3);
	CellOkMask = CellLackMask = 0;
	FString Q;
	if (CellStage == 0)
	{
		Q = Tx(TEXT("vidal_q1"), TEXT("Vidal no te mira. Mueve los labios: reza."));
		CellOptions[0] = Tx(TEXT("vidal_1a"), TEXT("\"Abre, o cuando salga te busco a ti primero.\""));
		CellOptions[1] = Tx(TEXT("vidal_1b"), TEXT("\"Lo oyes por las noches? Lo de abajo.\""));
		CellOptions[2] = Tx(TEXT("vidal_1c"), TEXT("\"Alarcon te ascendera si me sueltas. Yo se lo dire.\""));
		CellOkMask = 2;
	}
	else if (CellStage == 1)
	{
		Q = Tx(TEXT("vidal_q2"), TEXT("\"Y usted que sabe de lo de abajo?\""));
		CellOptions[0] = Tx(TEXT("vidal_2a"), TEXT("\"Es combustible. Un deposito. Me lo dijo Ibarra.\""));
		CellOptions[1] = !bKnows ? Tx(TEXT("vidal_2b"), TEXT("\"Que grita.\""))
			: bCodecVoiceHeard ? Tx(TEXT("vidal_2b_voz"), TEXT("\"Que esta vivo y sufre. Lo he oido en una frecuencia que no existe.\""))
			: bFile ? Tx(TEXT("vidal_2b_sabe"), TEXT("\"Que esta vivo y sufre. Halloran lo firmo y le tacharon la firma.\""))
			: Tx(TEXT("vidal_2b_control"), TEXT("\"Que esta vivo y sufre. Una doctora lo escribio y ya no firma nada.\""));
		CellOptions[2] = Tx(TEXT("vidal_2c"), TEXT("\"Que es el viento en la marisma. Nada mas.\""));
		CellOkMask = 2;
	}
	else
	{
		Q = Tx(TEXT("vidal_q3"), TEXT("\"Aunque le creyera. Por que iba a abrir?\""));
		CellOptions[0] = bFile ? Tx(TEXT("vidal_3a_sabe"), TEXT("\"He leido el expediente. Alarcon firma los traslados abajo, y el proximo lleva tu apellido.\""))
			: bHasKey ? Tx(TEXT("vidal_3a_medalla"), TEXT("(Le das la medalla entre los barrotes.) \"Tu hermano durmio en este catre.\""))
			: Tx(TEXT("vidal_3a"), TEXT("\"Hay bajas por voces. A vosotros no os lo cuentan.\""));
		CellOptions[1] = bPsalm ? Tx(TEXT("vidal_3b_sabe"), TEXT("\"Reza conmigo. De profundis clamavi ad te, Domine.\"")) : Tx(TEXT("vidal_3b"), TEXT("\"Reza conmigo.\""));
		CellOptions[2] = Tx(TEXT("vidal_3c"), TEXT("\"Te dare el expediente. Vendelo.\""));
		if (bFile || bHasKey) CellOkMask |= 1; else CellLackMask |= 1;
		CellOkMask |= 2;
		bCellMedal = !bFile && bHasKey;
	}
	{
		// del orden de escritura (a, b, c) al orden en pantalla de este paso
		const TArray<FString> Canon = CellOptions;
		const int32 Ok = CellOkMask, Lack = CellLackMask;
		CellOkMask = CellLackMask = 0;
		for (int32 i = 0; i < 3; ++i)
		{
			const int32 c = CellOrder[FMath::Clamp(CellStage, 0, 2)][i];
			CellOptions[i] = Canon[c];
			if (Ok & (1 << c)) CellOkMask |= 1 << i;
			if (Lack & (1 << c)) CellLackMask |= 1 << i;
		}
	}
	if (bHasKey) CellOptions.Add(Tx(TEXT("vidal_4"), TEXT("(Callar y abrir con la llave del hermano)")));
	CellRight = (CellOkMask & 1) ? 1 : (CellOkMask & 2) ? 2 : (CellOkMask & 4) ? 3 : 0;
	bCellAsk = true;
	CellQuestion = Q;
	FString M = FString::Printf(TEXT("%s  %d/3\n%s"), *Tx(TEXT("vidal_nombre"), TEXT("CABO VIDAL")), CellStage + 1, *Q);
	for (int32 i = 0; i < CellOptions.Num(); ++i) M += FString::Printf(TEXT("\n%d   %s"), i + 1, *CellOptions[i]);
	ShowMessage(M, 60.0f);
}

void ATarsisDirector::AnswerCell(int32 Option)
{
	if (!bCellAsk || Option < 1 || Option > CellOptions.Num()) return;
	if (Option == 4) { OpenCellWith(true); return; }
	bCellAsk = false;
	const int32 Bit = 1 << (Option - 1);
	const bool bOk = (CellOkMask & Bit) != 0, bLack = (CellLackMask & Bit) != 0;
	// lo que contesta Vidal: vidal_r<paso><a|b|c>; con _no si la respuesta era la buena pero aun no sabes bastante
	static const TCHAR* Def[3][3] = {
		{ TEXT("\"Amenace. Aqui dentro no cuesta nada.\" Se aleja un paso."), TEXT("Deja de rezar. \"Todos lo oimos. Nadie lo dice.\""), TEXT("\"Alarcon no asciende. Alarcon baja gente.\" Vuelve al rezo.") },
		{ TEXT("\"Ibarra dice lo que le mandan.\" Pierde interes."), TEXT("\"Mi hermano bajo en octubre. Volvio sordo. Luego dijeron que habia desertado.\""), TEXT("Casi se rie. \"El viento no llama a nadie por su nombre.\"") },
		{ TEXT("Se queda callado. \"Vidal, J. Octubre. Y ahora yo.\" La llave le tiembla en la cerradura."), TEXT("Se le quiebra la voz en el segundo verso. \"Desde lo profundo...\" Abre sin mirarte. \"Ella tambien clama, verdad?\""), TEXT("\"Y que hago yo con eso?\" Se va.") } };
	const int32 Canon = CellOrder[FMath::Clamp(CellStage, 0, 2)][Option - 1];   // a, b o c
	const TCHAR Letter = TCHAR('a' + Canon);
	FString Key = FString::Printf(TEXT("vidal_r%d%c"), CellStage + 1, Letter);
	const TCHAR* D = Def[CellStage][Canon];
	if (bLack)
	{
		Key += TEXT("_no");
		D = TEXT("\"Palabras.\" Vuelve la espalda.");
	}
	else if (bOk && CellStage == 2 && Canon == 0 && bCellMedal)
	{
		Key = TEXT("vidal_r3a_medalla");
		D = TEXT("Coge la medalla por entre los barrotes y la aprieta en el puno. No dice nada. Abre.");
	}
	const FString Reply = Tx(FName(*Key), D);
	if (bOk)
	{
		++CellStage;
		if (CellStage >= 3) { ShowMessage(Tx(TEXT("vidal_cede"), TEXT("CABO VIDAL\n{0}"), { Reply }), 4.0f); CellOpenT = 3.0f; return; }
		ShowMessage(Tx(TEXT("vidal_sigue"), TEXT("CABO VIDAL\n{0}"), { Reply }), 6.0f);
		CellNextT = CellAutoAsk;
		return;
	}
	if (bLack)
	{
		// no es un error: te falta saber algo, y se dice donde buscarlo
		++CellLacks;
		ShowMessage(Tx(TEXT("vidal_falta"), TEXT("CABO VIDAL\n{0}\n{1}"), { Reply, Tx(TEXT("vidal_pista3"), TEXT("Sin pruebas no te cree. Prueba otra cosa, o registra la celda.")) }), 8.0f);
		CellNextT = CellAutoAsk + 1.5f;
		return;
	}
	// una mala respuesta no cierra nada: Vidal contesta, vuelve al rezo y te deja probar otra vez
	++CellFails;
	ShowMessage(Tx(TEXT("vidal_falla"), TEXT("CABO VIDAL\n{0}\nAsi no. Prueba otra cosa."), { Reply }), 6.0f);
	CellNextT = CellAutoAsk;
}

void ATarsisDirector::OpenCellWith(bool bKeyUsed)
{
	bCellAsk = false;
	CellOpenT = 0.0f;
	if (Bars.Num() == 0) return;
	++(bKeyUsed ? CellByKey : CellByVidal);
	OpenCell();
	FaceVidal(VidalWallYaw);
	if (bKeyUsed)
	{
		CellAlertT = CellAlertSeconds;
		ShowMessage(Tx(TEXT("celda_llave"), TEXT("CELDA ABIERTA\nLa llave del hermano gira sin ruido. Vidal reza de espaldas y no lo ve.\nNo tardaran en encontrar la celda vacia. Tus cosas las tiene Peris en la sala de guardia.")), 8.0f);
		return;
	}
	SetFlag(FName(TEXT("vidal_calla")));
	ShowMessage(Tx(TEXT("celda_vidal"), TEXT("CELDA ABIERTA\nVidal abre y se queda rezando de cara a la pared. \"Yo no le he visto.\"\nNadie dara la alarma. Tus cosas las tiene Peris en la sala de guardia.")), 8.0f);
}

void ATarsisDirector::CellTick(float DeltaSeconds)
{
	if (CellOpenT > 0.0f)
	{
		CellOpenT -= DeltaSeconds;
		if (CellOpenT <= 0.0f) OpenCellWith(false);
	}
	// saliste con la llave: alguien acaba pasando por delante de la celda vacia
	if (CellAlertT > 0.0f)
	{
		CellAlertT -= DeltaSeconds;
		if (CellAlertT <= 0.0f)
		{
			++CellAlerts;
			TensionT = FMath::Max(TensionT, 90.0f);
			CentralSay(TEXT("fuga"), Tx(TEXT("celda_fuga"), TEXT("El calabozo esta vacio. Todas las unidades: ojo, y parte uno por uno.")));
		}
	}
	if (CellCallT > 0.0f && Bars.Num() > 0)
	{
		CellCallT -= DeltaSeconds;
		if (CellCallT <= 0.0f && !CodecTaken.Contains(TEXT("control_celda"))) CodecRing(TEXT("control_celda"));
	}
	// Vidal reza en voz alta: si te quedas unos segundos junto a la reja, oyes que salmo es (vale para rezar con el)
	if (bCellPuzzle && !bCellHeardPrayer && !bCellAsk && !bVidalGone && Bars.Num() > 0 && InCell() && NearPlayer(CellDoor, 200.0f))
	{
		CellPrayT += DeltaSeconds;
		if (CellPrayT >= CellPraySeconds)
		{
			bCellHeardPrayer = true;
			SaySubtitle(Tx(TEXT("vidal_nombre"), TEXT("CABO VIDAL")), Tx(TEXT("vidal_rezo"), TEXT("De profundis clamavi ad te, Domine... Domine, exaudi vocem meam...")), 5.0f);
		}
	}
	// la conversacion sigue sola: tras lo que contesta Vidal, vuelve la pregunta (la siguiente o la misma)
	if (CellNextT > 0.0f)
	{
		CellNextT -= DeltaSeconds;
		if (CellNextT <= 0.0f && bCellPuzzle && !bCellAsk && !bVidalGone && !bCodec && CellStage < 3 && InCell() && NearPlayer(CellDoor, 260.0f)) CellAsk();
	}
	// si te apartas de la reja, la pregunta se queda sin contestar (no cuenta como fallo)
	if (bCellAsk && (!InCell() || !NearPlayer(CellDoor, 260.0f)))
	{
		bCellAsk = false;
		MessageT = FMath::Min(MessageT, 0.3f);
	}
}

// Vidal con cuerpo (tanda 36): no es un guardia (ni ve ni oye ni patrulla), solo la malla y la postura de reposo de
// uno de ellos, con su misma ropa. No cuesta memoria: la malla ya esta cargada. Aparece cuando te encierran.
void ATarsisDirector::SpawnVidal()
{
	if (VidalBody || CellDoor.IsZero()) return;
	ATarsisGuard* Src = nullptr;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (!It->BodyMesh) continue;
		if (!Src) Src = *It;
		if (It->GuardName == VidalLooksLike) { Src = *It; break; }
	}
	USkeletalMeshComponent* From = Src ? Src->AnimBody() : nullptr;   // con el GASP, el cuerpo de la persona (GetMesh es el maniquí que conduce)
	if (!From) return;
	FVector At = CellDoor + VidalOffset;
	FHitResult Hit;
	FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisVidal), false, this);
	if (GetWorld()->LineTraceSingleByObjectType(Hit, FVector(At.X, At.Y, 160.0f), FVector(At.X, At.Y, -50.0f), FCollisionObjectQueryParams(ECC_WorldStatic), Q)) At.Z = Hit.ImpactPoint.Z;
	const float HalfH = Src->GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
	const FTransform Rel = From->GetComponentTransform().GetRelativeTransform(Src->GetActorTransform());   // respecto al guardia, cuelgue de donde cuelgue
	USkeletalMeshComponent* M = NewObject<USkeletalMeshComponent>(this);
	M->SetSkeletalMesh(Src->BodyMesh);
	M->SetMobility(EComponentMobility::Movable);
	M->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	M->SetAnimationMode(EAnimationMode::AnimationSingleNode);
	M->SetWorldScale3D(From->GetComponentScale());
	M->SetWorldLocation(At + FVector(0.0f, 0.0f, HalfH + Rel.GetLocation().Z));
	M->RegisterComponent();
	for (int32 i = 0; i < From->GetNumMaterials(); ++i) M->SetMaterial(i, From->GetMaterial(i));
	if (Src->IdleAnim) M->PlayAnimation(Src->IdleAnim, true);
	VidalMeshYaw = Rel.Rotator().Yaw;
	VidalBody = M;
	// tanda 38: una luz calida y floja entre el y la reja, a la altura de la cara. La del vestibulo le daba por
	// detras y desde la celda era una silueta. Sin sombras y de corto alcance: no cuesta memoria ni cuenta para el sigilo
	if (VidalLightLm > 0.0f)
	{
		UPointLightComponent* L = NewObject<UPointLightComponent>(this);
		L->SetMobility(EComponentMobility::Movable);
		L->SetIntensityUnits(ELightUnits::Lumens);
		L->SetIntensity(VidalLightLm);
		L->SetAttenuationRadius(260.0f);
		L->SetCastShadows(false);
		L->SetLightColor(FLinearColor(1.0f, 0.62f, 0.34f));
		L->ComponentTags.Add(FName(TEXT("decorado")));
		L->SetWorldLocation(FVector(At.X, At.Y, At.Z + 175.0f) + (CellDoor - At).GetSafeNormal2D() * 75.0f);
		L->RegisterComponent();
	}
}

void ATarsisDirector::FaceVidal(float Yaw)
{
	if (!VidalBody) return;
	VidalFace = Yaw;
	VidalBody->SetWorldRotation(FRotator(0.0f, Yaw + VidalMeshYaw, 0.0f));
}

void ATarsisDirector::CellReset()
{
	bCellAsk = false;
	bVidalGone = false;
	bCellMedal = false;
	bCellHeardPrayer = false;
	CellCallT = 0.0f;
	CellNextT = 0.0f;
	CellPrayT = 0.0f;
	CellOkMask = CellLackMask = 0;
	CellStage = CellFails = 0;
	CellOpenT = CellAlertT = 0.0f;
}
