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

#include "Components/StaticMeshComponent.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
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
	CloseCell();
	PlaySfx(TEXT("reja"), CellDoor + FVector(0.0f, 0.0f, 100.0f));
	CellT = bCellPuzzle ? 0.0f : CellTime;
	CellReset();
	ShowMessage(Tx(TEXT("calabozo"), TEXT("CALABOZO\nDespiertas tras la reja. Al otro lado, pegado a la pared donde no le ves, el cabo Vidal hace guardia y reza en voz baja.\nHabla con el por la reja. Vidal no es como los demas.")), 8.0f);
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
		if (HasFlag(FName(TEXT("llave_celda")))) return Tx(TEXT("p_reja_llave"), TEXT("E   ABRIR LA REJA CON LA LLAVE"));
		return bVidalGone ? Tx(TEXT("p_vidal_ido"), TEXT("VIDAL YA NO ESCUCHA")) : Tx(TEXT("p_vidal"), TEXT("E   HABLAR CON EL CABO VIDAL"));
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
		ShowMessage(Tx(TEXT("losa"), TEXT("LOSA SUELTA\nBajo la losa, en un trapo, una llave de hierro y una medalla con un nombre rayado a navaja: VIDAL, J.\nLa llave encaja en la reja. Vidal no tiene por que verlo.")), 8.0f);
		return true;
	}
	if (!NearPlayer(CellDoor, 170.0f)) return false;
	if (bKeyNow) { OpenCellWith(true); return true; }
	if (bVidalGone)
	{
		ShowMessage(Tx(TEXT("vidal_ido"), TEXT("CABO VIDAL\nReza mas alto y ya no contesta.\nEn el rincon, a la derecha de la reja, una losa baila bajo el pie.")), 5.0f);
		return true;
	}
	CellAsk();
	return true;
}

// Las tres preguntas. Cada una tiene una respuesta que vale; en la segunda y la tercera solo vale si sabes algo:
// la voz sin nombre del codec o el expediente (que lo de abajo esta vivo), la mesa de Alarcon o la pista de Roig (el salmo)
void ATarsisDirector::CellAsk()
{
	const bool bKnows = bCodecVoiceHeard || bFile;
	const bool bPsalm = bNoteRead || CodecTaken.Contains(TEXT("roig_salmo"));
	CellOptions.Init(FString(), 3);
	FString Q;
	if (CellStage == 0)
	{
		Q = Tx(TEXT("vidal_q1"), TEXT("Vidal no contesta. Al otro lado de la reja se le oye rezar."));
		CellOptions[0] = Tx(TEXT("vidal_1a"), TEXT("\"Abre, o cuando salga te busco a ti primero.\""));
		CellOptions[1] = Tx(TEXT("vidal_1b"), TEXT("\"Lo oyes por las noches? Lo de abajo.\""));
		CellOptions[2] = Tx(TEXT("vidal_1c"), TEXT("\"Alarcon te ascendera si me sueltas. Yo se lo dire.\""));
		CellRight = 2;
	}
	else if (CellStage == 1)
	{
		Q = Tx(TEXT("vidal_q2"), TEXT("\"Y usted que sabe de lo de abajo?\""));
		CellOptions[0] = Tx(TEXT("vidal_2a"), TEXT("\"Es combustible. Un deposito. Me lo dijo Ibarra.\""));
		CellOptions[1] = bKnows ? (bCodecVoiceHeard ? Tx(TEXT("vidal_2b_voz"), TEXT("\"Que esta vivo y sufre. Lo he oido en una frecuencia que no existe.\""))
			: Tx(TEXT("vidal_2b_sabe"), TEXT("\"Que esta vivo y sufre. Halloran lo firmo y le tacharon la firma.\""))) : Tx(TEXT("vidal_2b"), TEXT("\"Que grita.\""));
		CellOptions[2] = Tx(TEXT("vidal_2c"), TEXT("\"Que es el viento en la marisma. Nada mas.\""));
		CellRight = bKnows ? 2 : 0;
	}
	else
	{
		Q = Tx(TEXT("vidal_q3"), TEXT("\"Aunque le creyera. Por que iba a abrir?\""));
		CellOptions[0] = bFile ? Tx(TEXT("vidal_3a_sabe"), TEXT("\"He leido el expediente. Alarcon firma los traslados abajo, y el proximo lleva tu apellido.\"")) : Tx(TEXT("vidal_3a"), TEXT("\"Hay bajas por voces. A vosotros no os lo cuentan.\""));
		CellOptions[1] = bPsalm ? Tx(TEXT("vidal_3b_sabe"), TEXT("\"Reza conmigo. De profundis clamavi ad te, Domine.\"")) : Tx(TEXT("vidal_3b"), TEXT("\"Reza conmigo.\""));
		CellOptions[2] = Tx(TEXT("vidal_3c"), TEXT("\"Te dare el expediente. Vendelo.\""));
		CellRight = bFile ? 1 : (bPsalm ? 2 : 0);
		bCellAlso = bFile && bPsalm;   // valen las dos
	}
	bCellAsk = true;
	ShowMessage(Tx(TEXT("vidal_pregunta"), TEXT("CABO VIDAL  {0}/3\n{1}\n1   {2}\n2   {3}\n3   {4}"),
		{ CellStage + 1, Q, CellOptions[0], CellOptions[1], CellOptions[2] }), 60.0f);
}

void ATarsisDirector::AnswerCell(int32 Option)
{
	if (!bCellAsk || Option < 1 || Option > 3) return;
	bCellAsk = false;
	const bool bOk = Option == CellRight || (CellStage == 2 && bCellAlso && Option == 2);
	bCellAlso = false;
	// lo que contesta Vidal a cada respuesta: vidal_r<paso><a|b|c>, y vidal_r<paso>b_no / 3a_no si la buena aun no la sabes
	static const TCHAR* Def[3][3] = {
		{ TEXT("\"Amenace. Aqui dentro no cuesta nada.\" Se aleja un paso."), TEXT("Deja de rezar. \"Todos lo oimos. Nadie lo dice.\""), TEXT("\"Alarcon no asciende. Alarcon baja gente.\" Vuelve al rezo.") },
		{ TEXT("\"Ibarra dice lo que le mandan.\" Pierde interes."), TEXT("\"Mi hermano bajo en octubre. Volvio sordo. Luego dijeron que habia desertado.\""), TEXT("Casi se rie. \"El viento no llama a nadie por su nombre.\"") },
		{ TEXT("Se queda callado. \"Vidal, J. Octubre. Y ahora yo.\" La llave le tiembla en la cerradura."), TEXT("Se le quiebra la voz en el segundo verso. \"Desde lo profundo...\" Abre sin mirarte. \"Ella tambien clama, verdad?\""), TEXT("\"Y que hago yo con eso?\" Se va.") } };
	static const TCHAR* DefNo[3] = { TEXT(""), TEXT("\"Eso lo sabe cualquiera que haya dormido aqui.\" No basta."), TEXT("\"Palabras.\" Vuelve la espalda.") };
	static const TCHAR* DefNoPray = TEXT("\"Usted no reza.\" Vuelve la espalda.");
	const TCHAR Letter = TCHAR('a' + Option - 1);
	FString Key = FString::Printf(TEXT("vidal_r%d%c"), CellStage + 1, Letter);
	const TCHAR* D = Def[CellStage][Option - 1];
	if (!bOk && CellStage > 0 && Option != 3 && !(CellStage == 1 && Option == 1)) { Key += TEXT("_no"); D = (CellStage == 2 && Option == 2) ? DefNoPray : DefNo[CellStage]; }
	const FString Reply = Tx(FName(*Key), D);
	if (bOk)
	{
		++CellStage;
		if (CellStage >= 3) { ShowMessage(Tx(TEXT("vidal_cede"), TEXT("CABO VIDAL\n{0}"), { Reply }), 4.0f); CellOpenT = 3.0f; return; }
		ShowMessage(Tx(TEXT("vidal_sigue"), TEXT("CABO VIDAL\n{0}\nSigue ahi. Habla otra vez con el."), { Reply }), 6.0f);
		return;
	}
	++CellFails;
	if (CellFails >= 3)
	{
		bVidalGone = true;
		ShowMessage(Tx(TEXT("vidal_se_va"), TEXT("CABO VIDAL\n{0}\nVidal no volvera a escucharte. Tiene que haber otra manera: mira el suelo."), { Reply }), 7.0f);
		return;
	}
	ShowMessage(Tx(TEXT("vidal_falla"), TEXT("CABO VIDAL\n{0}\nVuelve al rezo, pero sigue ahi. Fallos: {1}/3"), { Reply, CellFails }), 6.0f);
}

void ATarsisDirector::OpenCellWith(bool bKeyUsed)
{
	bCellAsk = false;
	CellOpenT = 0.0f;
	if (Bars.Num() == 0) return;
	++(bKeyUsed ? CellByKey : CellByVidal);
	OpenCell();
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
	// si te apartas de la reja, la pregunta se queda sin contestar (no cuenta como fallo)
	if (bCellAsk && (!InCell() || !NearPlayer(CellDoor, 260.0f)))
	{
		bCellAsk = false;
		MessageT = FMath::Min(MessageT, 0.3f);
	}
}

void ATarsisDirector::CellReset()
{
	bCellAsk = false;
	bVidalGone = false;
	bCellAlso = false;
	CellStage = CellFails = 0;
	CellOpenT = CellAlertT = 0.0f;
}
