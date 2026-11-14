#include "TarsisHUD.h"
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"

// Textos del HUD solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

float ATarsisHUD::UiScale() const
{
	// todo a escala de 1080 p, por el tamaño del texto del menú (accesibilidad)
	float K = 1.0f;
	for (TActorIterator<ATarsisDirector> It(GetWorld()); It; ++It) { K = It->OptTextScale; break; }
	return Canvas ? Canvas->ClipY / 1080.0f * K : 1.0f;
}

void ATarsisHUD::Panel(float X, float Y, float W, float H, const FLinearColor& C)
{
	DrawRect(C, X, Y, W, H);
}

void ATarsisHUD::Text(const FString& S, float X, float Y, const FLinearColor& C, float Scale, bool bCenter)
{
	UFont* F = GEngine ? GEngine->GetMediumFont() : nullptr;
	if (!F || !Canvas) return;
	float W = 0.0f, H = 0.0f;
	GetTextSize(S, W, H, F, Scale);
	DrawText(S, FLinearColor(0.0f, 0.0f, 0.0f, 0.7f * C.A), (bCenter ? X - W / 2.0f : X) + 1.5f, Y + 1.5f, F, Scale);
	DrawText(S, C, bCenter ? X - W / 2.0f : X, Y, F, Scale);
}

void ATarsisHUD::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas) return;
	ATarsisDirector* D = nullptr;
	for (TActorIterator<ATarsisDirector> It(GetWorld()); It; ++It) { D = *It; break; }
	const ACharacter* C = Cast<ACharacter>(GetOwningPawn());
	if (D && D->bCine)
	{
		// cinemática: franjas de cine y solo el texto
		const float H = Canvas->ClipY * 0.11f;
		Panel(0.0f, 0.0f, Canvas->ClipX, H, FLinearColor::Black);
		Panel(0.0f, Canvas->ClipY - H, Canvas->ClipX, H, FLinearColor::Black);
		DrawMessage(D);
		// el final se queda en la cinemática (bPauseAtEnd): el parte y el menú se dibujan también aquí
		DrawReport(D);
		DrawMenu(D);
		return;
	}
	DrawHiding(D);
	DrawBinoculars(D);
	DrawMarked();
	DrawHeard(D);
	DrawLight(D, C && C->bIsCrouched);
	DrawAlert();
	DrawGuardMarks();
	DrawMessage(D);
	DrawObjective(D);
	DrawHint(D);
	DrawPrompt(D);
	DrawKeypad(D);
	DrawExtras(D);
	DrawReport(D);
	DrawMenu(D);
}

void ATarsisHUD::DrawReport(ATarsisDirector* D)
{
	if (!D || !D->bReport || D->bMenu || D->ReportLines.Num() == 0) return;
	++D->ReportFrames;   // para las pruebas: el parte se ha dibujado de verdad (no solo tiene datos)
	const float S = Canvas->ClipY / 1080.0f;   // como el menú: tiene que caber entero
	const float W = FMath::Min(1100.0f * S, Canvas->ClipX - 40.0f * S), LH = 38.0f * S;
	UFont* F = GEngine ? GEngine->GetMediumFont() : nullptr;
	if (!F) return;
	// las líneas largas («LA PROXIMA NOCHE: ...», la lista de dormidos) se parten por palabras al ancho de la hoja
	struct FRow { FString T; float Scale; FLinearColor Col; bool bHead; };
	TArray<FRow> Rows;
	// colores lineales: 0,12 se veía gris claro sobre el papel; tinta casi negra y papel beige, no blanco
	const FLinearColor Ink(0.012f, 0.01f, 0.008f, 1.0f), Red(0.32f, 0.025f, 0.015f, 1.0f);
	const float MaxW = W - 80.0f * S;
	for (int32 i = 0; i < D->ReportLines.Num(); ++i)
	{
		const FString& T = D->ReportLines[i];
		const bool bHead = i == 0;
		const bool bKeyLine = T.StartsWith(TEXT("LA PROXIMA NOCHE")) || T.StartsWith(TEXT("SIGILO"));
		const float Sc = (bHead ? 1.3f : (bKeyLine ? 1.0f : 0.95f)) * S;   // antes 0,78: pequeño para leer un parte entero
		const FLinearColor Col = bKeyLine ? Red : Ink;
		TArray<FString> Words;
		T.ParseIntoArray(Words, TEXT(" "));
		if (bHead || Words.Num() == 0) { Rows.Add({ T, Sc, Col, bHead }); continue; }
		FString Cur;
		for (const FString& Wd : Words)
		{
			const FString Try = Cur.IsEmpty() ? Wd : Cur + TEXT(" ") + Wd;
			float TW = 0.0f, TH = 0.0f;
			GetTextSize(Try, TW, TH, F, Sc);
			if (TW > MaxW && !Cur.IsEmpty()) { Rows.Add({ Cur, Sc, Col, false }); Cur = TEXT("   ") + Wd; }
			else Cur = Try;
		}
		Rows.Add({ Cur, Sc, Col, false });
	}
	const float H = Rows.Num() * LH + 60.0f * S;
	const float X = (Canvas->ClipX - W) / 2.0f, Y = FMath::Max((Canvas->ClipY - H) / 2.0f, 10.0f * S);
	Panel(0.0f, 0.0f, Canvas->ClipX, Canvas->ClipY, FLinearColor(0.0f, 0.0f, 0.0f, 0.55f));
	// hoja de papel: un parte mecanografiado
	Panel(X, Y, W, H, FLinearColor(0.6f, 0.54f, 0.42f, 0.97f));
	Panel(X, Y, W, 6.0f * S, FLinearColor(0.55f, 0.12f, 0.1f, 1.0f));
	for (int32 i = 0; i < Rows.Num(); ++i)
	{
		// tinta sin la sombra negra de Text(): sobre el papel la emborronaba
		float TW = 0.0f, TH = 0.0f;
		GetTextSize(Rows[i].T, TW, TH, F, Rows[i].Scale);
		const float TX = Rows[i].bHead ? Canvas->ClipX / 2.0f - TW / 2.0f : X + 40.0f * S;
		DrawText(Rows[i].T, Rows[i].Col, TX, Y + 26.0f * S + i * LH, F, Rows[i].Scale);
	}
}

void ATarsisHUD::DrawExtras(ATarsisDirector* D)
{
	if (!D) return;
	const float S = UiScale();
	// contador de fps (opción del menú), suavizado
	const float Dt = GetWorld() ? GetWorld()->GetDeltaSeconds() : 0.0f;
	if (Dt > 0.0f) FpsSmooth = FpsSmooth <= 0.0f ? 1.0f / Dt : FMath::Lerp(FpsSmooth, 1.0f / Dt, 0.05f);
	if (D->bShowFps)
	{
		Text(FString::Printf(TEXT("%d FPS"), FMath::RoundToInt(FpsSmooth)), Canvas->ClipX - 20.0f * S - 90.0f * S, 12.0f * S,
			FpsSmooth >= 55.0f ? FLinearColor(0.6f, 1.0f, 0.6f) : (FpsSmooth >= 30.0f ? FLinearColor(1.0f, 0.85f, 0.4f) : FLinearColor(1.0f, 0.4f, 0.3f)), 0.8f * S, false);
	}
	// ayuda de teclas, abajo del todo (opción del menú)
	if (D->bShowHelp && !D->bKeypad && !D->bMenu)
	{
		Text(D->HelpLine(), Canvas->ClipX / 2.0f, Canvas->ClipY - 26.0f * S, FLinearColor(0.85f, 0.85f, 0.85f, 0.6f), 0.7f * S, true);
	}
	// subtítulos de sonidos (opción del menú), encima del panel de mensajes
	if (D->bSubtitles && D->SubtitleT > 0.0f && !D->Subtitle.IsEmpty() && !D->bMenu)
	{
		const float A = FMath::Clamp(D->SubtitleT * 2.0f, 0.0f, 1.0f);
		// a 0,75 del alto: entre la caja de radio (que al 140 % baja hasta ~0,67) y los paneles de abajo
		Text(D->Subtitle, Canvas->ClipX / 2.0f, Canvas->ClipY * 0.75f, FLinearColor(0.95f, 0.95f, 0.75f, A), 0.8f * S, true);
	}
	// aviso de punto de control, arriba a la derecha
	if (D->CheckT > 0.0f && !D->CheckpointName.IsEmpty())
	{
		const float A = FMath::Clamp(D->CheckT, 0.0f, 1.0f);
		const float W = 430.0f * S, X = Canvas->ClipX - W - 20.0f * S, Y = 48.0f * S;
		Panel(X, Y, W, 58.0f * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.5f * A));
		Text(TEXT("PUNTO DE CONTROL GUARDADO"), X + 14.0f * S, Y + 6.0f * S, FLinearColor(1.0f, 0.85f, 0.55f, A), 0.72f * S, false);
		Text(D->CheckpointName, X + 14.0f * S, Y + 30.0f * S, FLinearColor(1.0f, 0.95f, 0.85f, A), 0.72f * S, false);
	}
}

void ATarsisHUD::DrawMenu(ATarsisDirector* D)
{
	if (!D || !D->bMenu) return;
	const float S = Canvas->ClipY / 1080.0f;   // el menú no crece con el tamaño del texto: tiene que caber entero
	Panel(0.0f, 0.0f, Canvas->ClipX, Canvas->ClipY, FLinearColor(0.0f, 0.0f, 0.0f, 0.6f));
	const TArray<FString> L = D->MenuLines();
	const float CX = Canvas->ClipX / 2.0f, LH = 40.0f * S;
	const float W = 720.0f * S, Y0 = Canvas->ClipY / 2.0f - (L.Num() * LH) / 2.0f;
	Text(D->MenuPage == 1 ? TEXT("CONTROLES") : TEXT("PAUSA"), CX, Y0 - 90.0f * S, FLinearColor(1.0f, 0.85f, 0.55f), 1.6f * S, true);
	for (int32 i = 0; i < L.Num(); ++i)
	{
		const bool bSel = i == D->MenuSel;
		if (bSel) Panel(CX - W / 2.0f, Y0 + i * LH - 6.0f * S, W, LH - 6.0f * S, FLinearColor(1.0f, 0.85f, 0.55f, 0.18f));
		Text(L[i], CX, Y0 + i * LH, bSel ? FLinearColor(1.0f, 0.95f, 0.8f) : FLinearColor(0.75f, 0.75f, 0.75f), (bSel ? 0.95f : 0.85f) * S, true);
	}
	Text(D->MenuPage == 1 ? TEXT("Intro: cambiar la tecla (si ya la usa otra accion, se intercambian)    Esc: volver")
		: TEXT("W/S o flechas: elegir    A/D: cambiar    Intro: aceptar    P: volver al juego"), CX, Y0 + L.Num() * LH + 30.0f * S,
		FLinearColor(0.7f, 0.7f, 0.7f), 0.7f * S, true);
}

void ATarsisHUD::DrawBinoculars(ATarsisDirector* D)
{
	if (!D || !D->bBinoculars) return;
	const float S = UiScale();
	const float W = Canvas->ClipX, H = Canvas->ClipY;
	// dos círculos de los prismáticos, aproximados con franjas negras arriba, abajo y a los lados
	const FLinearColor K(0.0f, 0.0f, 0.0f, 0.92f);
	Panel(0.0f, 0.0f, W, H * 0.12f, K);
	Panel(0.0f, H * 0.88f, W, H * 0.12f, K);
	Panel(0.0f, 0.0f, W * 0.1f, H, K);
	Panel(W * 0.9f, 0.0f, W * 0.1f, H, K);
	Panel(W / 2.0f - 1.0f * S, H * 0.12f, 2.0f * S, H * 0.76f, FLinearColor(0.0f, 0.0f, 0.0f, 0.5f));
	Panel(W / 2.0f - 30.0f * S, H / 2.0f - 1.0f * S, 60.0f * S, 2.0f * S, FLinearColor(1.0f, 1.0f, 1.0f, 0.35f));
	Text(TEXT("PRISMATICOS  x5   -   mira a un guardia para marcarlo   -   B para bajar"), W / 2.0f, H * 0.9f, FLinearColor(0.8f, 0.8f, 0.8f), 0.85f * S, true);
}

void ATarsisHUD::DrawMarked()
{
	APlayerController* PC = GetOwningPlayerController();
	const APawn* Pl = GetOwningPawn();
	if (!PC || !Pl) return;
	const float S = UiScale();
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (!It->bMarked) continue;
		FVector2D Scr;
		if (!PC->ProjectWorldLocationToScreen(It->GetActorLocation() + FVector(0.0f, 0.0f, 135.0f), Scr, true)) continue;
		if (Scr.X < 0.0f || Scr.Y < 0.0f || Scr.X > Canvas->ClipX || Scr.Y > Canvas->ClipY) continue;
		const ETarsisGuardState St = It->State;
		FLinearColor Col(0.85f, 0.9f, 1.0f, 0.85f);
		if (St == ETarsisGuardState::Alert) Col = FLinearColor(1.0f, 0.23f, 0.18f);
		else if (St == ETarsisGuardState::Suspicious || St == ETarsisGuardState::Search) Col = FLinearColor(1.0f, 0.82f, 0.23f);
		else if (St == ETarsisGuardState::Down) Col = FLinearColor(0.55f, 0.55f, 0.55f, 0.8f);
		const int32 M = FMath::RoundToInt(FVector::Dist(It->GetActorLocation(), Pl->GetActorLocation()) / 100.0f);
		const FString L = FString::Printf(TEXT("%s  %dm%s"), *It->GuardName.ToUpper(), M, St == ETarsisGuardState::Down ? TEXT("  (KO)") : TEXT(""));
		Panel(Scr.X - 3.0f * S, Scr.Y + 4.0f * S, 6.0f * S, 6.0f * S, Col);
		Text(L, Scr.X, Scr.Y - 20.0f * S, Col, 0.7f * S, true);
	}
}

void ATarsisHUD::DrawHeard(ATarsisDirector* D)
{
	if (!D || D->HeardT <= 0.0f) return;
	APlayerController* PC = GetOwningPlayerController();
	if (!PC) return;
	const float S = UiScale();
	const float A = FMath::Min(1.0f, D->HeardT);
	const FLinearColor Col(0.47f, 0.78f, 1.0f, A);   // azul, como el «?» del guardia que te oye
	const float CX = Canvas->ClipX / 2.0f, Y = Canvas->ClipY * 0.2f;
	// de qué lado está el guardia que te ha oído
	FVector CamLoc; FRotator CamRot;
	PC->GetPlayerViewPoint(CamLoc, CamRot);
	const FVector Local = CamRot.UnrotateVector(D->HeardFrom - CamLoc);
	FString Side = TEXT("DELANTE");
	if (Local.X < 0.0f && FMath::Abs(Local.Y) < -Local.X) Side = TEXT("DETRAS");
	else if (Local.Y > FMath::Abs(Local.X) * 0.4f) Side = TEXT("A LA DERECHA  >>");
	else if (Local.Y < -FMath::Abs(Local.X) * 0.4f) Side = TEXT("<<  A LA IZQUIERDA");
	Panel(CX - 230.0f * S, Y, 460.0f * S, 74.0f * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.5f * A));
	Text(TEXT("TE HAN OIDO"), CX, Y + 6.0f * S, Col, 1.35f * S, true);
	Text(Side, CX, Y + 44.0f * S, Col, 0.85f * S, true);
}

void ATarsisHUD::DrawObjective(ATarsisDirector* D)
{
	if (!D) return;
	const FString O = D->Objective();
	if (O.IsEmpty()) return;
	const float S = UiScale();
	const float X = 32.0f * S, Y = 28.0f * S;
	UFont* F = GEngine ? GEngine->GetMediumFont() : nullptr;
	const FString Side = D->SideObjective();
	const FString SideT = Side.IsEmpty() ? FString() : TEXT("SECUNDARIA: ") + Side;
	float W = 0.0f, H = 0.0f, W2 = 0.0f;
	if (F) GetTextSize(O, W, H, F, 0.9f * S);
	if (F && !SideT.IsEmpty()) GetTextSize(SideT, W2, H, F, 0.75f * S);
	Panel(X, Y, FMath::Max(FMath::Max(W, W2), 140.0f * S) + 28.0f * S, (SideT.IsEmpty() ? 62.0f : 88.0f) * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.45f));
	Text(D->bDone ? TEXT("FIN") : TEXT("OBJETIVO"), X + 14.0f * S, Y + 6.0f * S, FLinearColor(0.95f, 0.8f, 0.4f), 0.8f * S);
	Text(O, X + 14.0f * S, Y + 30.0f * S, FLinearColor(1.0f, 1.0f, 1.0f), 0.9f * S);
	if (!SideT.IsEmpty()) Text(SideT, X + 14.0f * S, Y + 60.0f * S, FLinearColor(0.7f, 0.85f, 1.0f), 0.75f * S);
	// pistola de dardos, abajo a la derecha
	if (D->bVetOpen)
	{
		const FString A = FString::Printf(TEXT("DARDOS  %d   (clic izquierdo)"), D->Darts);
		const float AX = Canvas->ClipX - 332.0f * S, AY = Canvas->ClipY - 76.0f * S;
		Panel(AX, AY, 300.0f * S, 44.0f * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.45f));
		Text(A, AX + 14.0f * S, AY + 10.0f * S, D->Darts > 0 ? FLinearColor(0.85f, 0.95f, 0.75f) : FLinearColor(0.6f, 0.6f, 0.6f), 0.9f * S);
	}
}

void ATarsisHUD::DrawPrompt(ATarsisDirector* D)
{
	if (!D) return;
	const FString P = D->InteractPrompt();
	if (P.IsEmpty()) return;
	const float S = UiScale();
	UFont* F = GEngine ? GEngine->GetMediumFont() : nullptr;
	float W = 200.0f * S, H = 0.0f;
	if (F) GetTextSize(P, W, H, F, 1.05f * S);
	W += 40.0f * S;
	Panel(Canvas->ClipX / 2.0f - W / 2.0f, Canvas->ClipY * 0.56f, W, 40.0f * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.55f));
	Text(P, Canvas->ClipX / 2.0f, Canvas->ClipY * 0.56f + 6.0f * S, FLinearColor(1.0f, 1.0f, 1.0f), 1.05f * S, true);
}

void ATarsisHUD::DrawKeypad(ATarsisDirector* D)
{
	if (!D || !D->bKeypad) return;
	const float S = UiScale();
	const float W = 380.0f * S, H = 150.0f * S;
	const float X = Canvas->ClipX / 2.0f - W / 2.0f, Y = Canvas->ClipY * 0.36f;
	Panel(X, Y, W, H, FLinearColor(0.02f, 0.03f, 0.03f, 0.8f));
	Text(TEXT("ARCHIVO - CLAVE"), Canvas->ClipX / 2.0f, Y + 10.0f * S, FLinearColor(0.6f, 0.9f, 0.7f), 0.9f * S, true);
	FString Code;
	for (int32 i = 0; i < 4; ++i)
	{
		Code += i < D->KeypadInput.Len() ? D->KeypadInput.Mid(i, 1) : TEXT("_");
		if (i < 3) Code += TEXT("  ");
	}
	Text(Code, Canvas->ClipX / 2.0f, Y + 44.0f * S, FLinearColor(0.45f, 1.0f, 0.55f), 1.8f * S, true);
	Text(TEXT("Teclea 4 cifras   Retroceso borra   E cierra"), Canvas->ClipX / 2.0f, Y + 112.0f * S, FLinearColor(0.75f, 0.75f, 0.75f), 0.75f * S, true);
}

void ATarsisHUD::DrawLight(ATarsisDirector* D, bool bCrouched)
{
	const float L = D ? D->PlayerLight : 0.0f;
	const float S = UiScale();   // todo a escala de 1080 p
	const float X = 32.0f * S, Y = Canvas->ClipY - 118.0f * S, W = 300.0f * S, H = 86.0f * S;
	Panel(X, Y, W, H, FLinearColor(0.0f, 0.0f, 0.0f, 0.45f));
	// daltonismo: azul, blanco y naranja (no verde, amarillo y naranja, que se confunden)
	const bool bCB = D && D->bColorblind;
	const FLinearColor Col = L < 0.3f ? (bCB ? FLinearColor(0.35f, 0.6f, 1.0f) : FLinearColor(0.45f, 0.85f, 0.55f))
		: (L < 0.6f ? (bCB ? FLinearColor(0.95f, 0.95f, 0.95f) : FLinearColor(0.95f, 0.8f, 0.3f)) : FLinearColor(1.0f, 0.5f, 0.25f));
	Text(TEXT("LUZ"), X + 14.0f * S, Y + 10.0f * S, FLinearColor(0.8f, 0.8f, 0.8f), 1.0f * S);
	Text(L < 0.3f ? TEXT("EN SOMBRA") : (L < 0.6f ? TEXT("PENUMBRA") : TEXT("ILUMINADO")), X + 70.0f * S, Y + 10.0f * S, Col, 1.0f * S);
	const int32 N = FMath::Clamp(FMath::RoundToInt(L * 10.0f), 0, 10);
	const float SegW = (W - 28.0f * S - 9.0f * 4.0f * S) / 10.0f;
	for (int32 i = 0; i < 10; ++i)
	{
		const FLinearColor SC = i < N ? Col : FLinearColor(1.0f, 1.0f, 1.0f, 0.12f);
		Panel(X + 14.0f * S + i * (SegW + 4.0f * S), Y + 38.0f * S, SegW, 12.0f * S, SC);
	}
	// postura y ruido de los pasos
	const float Nz = D ? D->PlayerNoise : 0.0f;
	// con las teclas configuradas (Controles): antes decía siempre C y Shift aunque las hubieras cambiado
	FString Post = bCrouched ? FString(TEXT("AGACHADO - SILENCIOSO")) : (D
		? FString::Printf(TEXT("DE PIE  (%s agacharte, %s correr)"), *D->ActionKeys[0].GetDisplayName().ToString(), *D->ActionKeys[4].GetDisplayName().ToString())
		: FString(TEXT("DE PIE  (C agacharte, Shift correr)")));
	FLinearColor PC = bCrouched ? FLinearColor(0.6f, 0.85f, 1.0f) : FLinearColor(0.7f, 0.7f, 0.7f);
	if (!bCrouched && Nz > 0.0f)
	{
		Post = FString::Printf(TEXT("%s - TE OYEN A %d m"), (D && D->bSprint) ? TEXT("CORRIENDO") : TEXT("PASOS"), FMath::RoundToInt(Nz / 100.0f));
		PC = Nz > 700.0f ? FLinearColor(1.0f, 0.5f, 0.25f) : FLinearColor(0.95f, 0.8f, 0.3f);
	}
	Text(Post, X + 14.0f * S, Y + 58.0f * S, PC, 0.85f * S);
	if (D)
	{
		static const TCHAR* Wx[] = { TEXT("DESPEJADO"), TEXT("LLUVIA"), TEXT("NIEBLA") };
		Text(FString::Printf(TEXT("%s (Y)"), Wx[FMath::Clamp(D->Weather, 0, 2)]), X + W - 120.0f * S, Y + 10.0f * S, FLinearColor(0.6f, 0.7f, 0.8f), 0.7f * S);
		if (D->TensionT > 0.0f)
		{
			Panel(X, Y - 36.0f * S, 240.0f * S, 30.0f * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.5f));
			Text(FString::Printf(TEXT("BASE EN GUARDIA  %d s"), FMath::CeilToInt(D->TensionT)), X + 14.0f * S, Y - 32.0f * S, FLinearColor(1.0f, 0.45f, 0.3f), 0.85f * S);
		}
		if (D->bPowerOff)
		{
			Panel(X + 250.0f * S, Y - 36.0f * S, 190.0f * S, 30.0f * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.5f));
			Text(FString::Printf(TEXT("SIN LUZ  %d s"), FMath::CeilToInt(D->PowerT)), X + 264.0f * S, Y - 32.0f * S, FLinearColor(0.55f, 0.75f, 1.0f), 0.85f * S);
		}
	}
}

void ATarsisHUD::DrawAlert()
{
	ETarsisGuardState Worst = ETarsisGuardState::Patrol;
	float MaxMeter = 0.0f;
	bool bSeen = false;   // alguno en alerta por haberte visto (no solo mandado por radio)
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		MaxMeter = FMath::Max(MaxMeter, It->Meter);
		if (It->State == ETarsisGuardState::Alert && !It->bRadioCall) bSeen = true;
		if (It->State == ETarsisGuardState::Alert) Worst = ETarsisGuardState::Alert;
		else if (Worst != ETarsisGuardState::Alert && It->State == ETarsisGuardState::Search) Worst = ETarsisGuardState::Search;
		else if (Worst == ETarsisGuardState::Patrol && It->State == ETarsisGuardState::Suspicious) Worst = ETarsisGuardState::Suspicious;
	}
	if (Worst == ETarsisGuardState::Patrol && MaxMeter < 0.05f) return;
	const float S = UiScale();
	float CX = Canvas->ClipX / 2.0f, Y = 28.0f * S;
	const float W = 460.0f * S;
	// no pisar el panel del objetivo (arriba a la izquierda): con texto grande o en 4:3 se metía debajo de esta barra.
	// Se aparta a la derecha si cabe y, si no, baja por debajo del objetivo (mismas medidas que DrawObjective)
	{
		ATarsisDirector* D = nullptr;
		for (TActorIterator<ATarsisDirector> It(GetWorld()); It; ++It) { D = *It; break; }
		UFont* F = GEngine ? GEngine->GetMediumFont() : nullptr;
		if (D && F && !D->Objective().IsEmpty())
		{
			float OW = 0.0f, OH = 0.0f, OW2 = 0.0f;
			GetTextSize(D->Objective(), OW, OH, F, 0.9f * S);
			const FString Side = D->SideObjective();
			if (!Side.IsEmpty()) GetTextSize(TEXT("SECUNDARIA: ") + Side, OW2, OH, F, 0.75f * S);
			const float ObjRight = 32.0f * S + FMath::Max(FMath::Max(OW, OW2), 140.0f * S) + 28.0f * S;
			const float ObjBottom = 28.0f * S + (Side.IsEmpty() ? 62.0f : 88.0f) * S;
			if (CX - W / 2.0f < ObjRight + 12.0f * S)
			{
				if (ObjRight + 12.0f * S + W <= Canvas->ClipX - 12.0f * S) CX = ObjRight + 12.0f * S + W / 2.0f;
				else Y = ObjBottom + 10.0f * S;
			}
		}
	}
	FString T = TEXT("TODO TRANQUILO");
	FLinearColor Col(0.8f, 0.8f, 0.8f);
	if (Worst == ETarsisGuardState::Alert && bSeen) { T = TEXT("!  TE HAN VISTO: ROMPE LA LINEA DE VISTA"); Col = FLinearColor(1.0f, 0.23f, 0.18f); }
	else if (Worst == ETarsisGuardState::Alert) { T = TEXT("!  ALERTA POR RADIO: VAN CORRIENDO AL GENERADOR"); Col = FLinearColor(1.0f, 0.45f, 0.2f); }
	else if (Worst == ETarsisGuardState::Search) { T = TEXT("TE BUSCAN: NO TE MUEVAS DE LA SOMBRA"); Col = FLinearColor(1.0f, 0.6f, 0.2f); }
	else if (Worst == ETarsisGuardState::Suspicious) { T = TEXT("?  UN GUARDIA SOSPECHA"); Col = FLinearColor(1.0f, 0.82f, 0.23f); }
	Panel(CX - W / 2.0f, Y, W, 52.0f * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.5f));
	Text(T, CX, Y + 6.0f * S, Col, 1.05f * S, true);
	// sospecha del guardia más mosqueado
	Panel(CX - W / 2.0f + 12.0f * S, Y + 38.0f * S, W - 24.0f * S, 6.0f * S, FLinearColor(1.0f, 1.0f, 1.0f, 0.12f));
	Panel(CX - W / 2.0f + 12.0f * S, Y + 38.0f * S, (W - 24.0f * S) * FMath::Clamp(MaxMeter, 0.0f, 1.0f), 6.0f * S, Col);
}

void ATarsisHUD::DrawGuardMarks()
{
	APlayerController* PC = GetOwningPlayerController();
	if (!PC) return;
	FVector CamLoc; FRotator CamRot;
	PC->GetPlayerViewPoint(CamLoc, CamRot);
	const float S = UiScale();
	const float CX = Canvas->ClipX / 2.0f, CY = Canvas->ClipY / 2.0f, M = 60.0f * S;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		const ETarsisGuardState St = It->State;
		if (St == ETarsisGuardState::Down || It->bAlly) continue;
		const bool bCalm = St == ETarsisGuardState::Patrol || St == ETarsisGuardState::Return;
		const float Mt = FMath::Clamp(It->Meter, 0.0f, 1.0f);
		if (bCalm && Mt < 0.05f) continue;
		const bool bAlert = St == ETarsisGuardState::Alert;
		// la sospecha va del amarillo al rojo según se llena
		const FLinearColor Col = bAlert ? FLinearColor(1.0f, 0.23f, 0.18f) : FLinearColor(1.0f, FMath::Lerp(0.82f, 0.35f, Mt), FMath::Lerp(0.23f, 0.15f, Mt), bCalm ? 0.4f + 0.6f * Mt : 1.0f);
		const FVector P = It->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f);
		FVector2D Scr;
		const bool bIn = PC->ProjectWorldLocationToScreen(P, Scr, true) && Scr.X > M && Scr.X < Canvas->ClipX - M && Scr.Y > M && Scr.Y < Canvas->ClipY - M;
		if (bIn)
		{
			// a la vista: barra de sospecha sobre la cabeza, que avisa antes del «!»
			if (!bAlert)
			{
				FVector2D Top;
				if (PC->ProjectWorldLocationToScreen(It->GetActorLocation() + FVector(0.0f, 0.0f, 150.0f), Top, true))
				{
					const float BW = 64.0f * S, BH = 7.0f * S;
					Panel(Top.X - BW / 2.0f - 2.0f * S, Top.Y - 2.0f * S, BW + 4.0f * S, BH + 4.0f * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.55f));
					Panel(Top.X - BW / 2.0f, Top.Y, BW * Mt, BH, Col);
				}
			}
			continue;
		}
		// fuera de la pantalla: marca en el borde, en la dirección del guardia
		const FVector Local = CamRot.UnrotateVector(P - CamLoc);
		FVector2D Dir(Local.Y, -Local.X);   // vista desde arriba: derecha = +Y, delante = arriba
		if (Dir.IsNearlyZero()) continue;
		Dir.Normalize();
		const float R = FMath::Min(CX, CY) - M;
		const float X = CX + Dir.X * R, Y = CY + Dir.Y * R;
		Panel(X - 20.0f * S, Y - 20.0f * S, 40.0f * S, 40.0f * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.5f));
		Text(bAlert ? TEXT("!") : TEXT("?"), X, Y - 16.0f * S, Col, 1.4f * S, true);
	}
}

void ATarsisHUD::DrawMessage(ATarsisDirector* D)
{
	if (!D) return;
	const float S = UiScale();
	if (D->MessageT > 0.0f && !D->Message.IsEmpty())
	{
		// más abajo y más pequeño que antes: no tapa a los guardias del centro de la pantalla
		const float A = FMath::Clamp(D->MessageT, 0.0f, 1.0f);
		TArray<FString> Lines;
		D->Message.ParseIntoArray(Lines, TEXT("\n"));
		const float LH = 27.0f * S;
		const float Y0 = Canvas->ClipY * 0.93f - Lines.Num() * LH;
		// a la derecha de los paneles de abajo a la izquierda (LUZ, BASE EN GUARDIA, SIN LUZ acaban en 472*S): en 16:10 o 4:3
		// el 25 % del ancho se metía encima de ellos
		// El panel se ajusta al texto: centrado si cabe a la derecha de los paneles de la izquierda; si no (texto grande o
		// 4:3), empieza justo a su derecha. Antes, con 2*490*S de margen, al 140 % en 4:3 se quedaba en ~60 px de ancho.
		const float Left = 490.0f * S;
		float TW = 0.0f;
		if (UFont* F = GEngine ? GEngine->GetMediumFont() : nullptr)
		{
			for (int32 i = 0; i < Lines.Num(); ++i) { float LW = 0.0f, LHt = 0.0f; GetTextSize(Lines[i], LW, LHt, F, (i == 0 ? 0.95f : 0.78f) * S); TW = FMath::Max(TW, LW); }
		}
		const float PW = FMath::Min(FMath::Max(TW + 40.0f * S, Canvas->ClipX * 0.3f), Canvas->ClipX - Left - 12.0f * S);
		const float PX = FMath::Max(Canvas->ClipX / 2.0f - PW / 2.0f, Left);
		const float TX = PX + PW / 2.0f;
		Panel(PX, Y0 - 10.0f * S, PW, Lines.Num() * LH + 18.0f * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.45f * A));
		for (int32 i = 0; i < Lines.Num(); ++i)
		{
			Text(Lines[i], TX, Y0 + i * LH, i == 0 ? FLinearColor(1.0f, 0.85f, 0.55f, A) : FLinearColor(1.0f, 0.95f, 0.85f, 0.9f * A), (i == 0 ? 0.95f : 0.78f) * S, true);
		}
	}
	if (D->RadioT > 0.0f && !D->Radio.IsEmpty())
	{
		// radio: caja verde a la izquierda, con su cabecera, como una transmisión interceptada
		const float A = FMath::Clamp(D->RadioT, 0.0f, 1.0f);
		FString Body = D->Radio;
		Body.RemoveFromStart(TEXT("RADIO"));
		Body.RemoveFromStart(TEXT(":"));
		Body.RemoveFromStart(TEXT(","));
		Body.TrimStartInline();
		TArray<FString> Lines;
		Body.ParseIntoArray(Lines, TEXT("\n"));
		const float LH = 25.0f * S;
		// mínimo 560*S: la línea más larga («Entra el generador de reserva...») mide ~510*S y en 4:3 el 32 % se quedaba corto
		const float X0 = 30.0f * S, W = FMath::Max(Canvas->ClipX * 0.32f, 560.0f * S);
		const float Y0 = Canvas->ClipY * 0.55f;
		const float H = (Lines.Num() + 1) * LH + 18.0f * S;
		Panel(X0, Y0, W, H, FLinearColor(0.0f, 0.06f, 0.02f, 0.6f * A));
		Panel(X0, Y0, 4.0f * S, H, FLinearColor(0.35f, 1.0f, 0.45f, 0.9f * A));
		// parpadeo del piloto mientras dura la transmisión
		const bool bOn = FMath::Fmod(D->RadioT, 0.8f) > 0.3f;
		Text(bOn ? TEXT("((o)) RADIO") : TEXT("( o ) RADIO"), X0 + 14.0f * S, Y0 + 8.0f * S, FLinearColor(0.45f, 1.0f, 0.55f, A), 0.72f * S, false);
		for (int32 i = 0; i < Lines.Num(); ++i)
		{
			Text(Lines[i], X0 + 14.0f * S, Y0 + 8.0f * S + (i + 1) * LH, FLinearColor(0.75f, 1.0f, 0.8f, A), 0.72f * S, false);
		}
	}
}

void ATarsisHUD::DrawHint(ATarsisDirector* D)
{
	// consejo del principio, bajo el objetivo (ATarsisDirector::HintTick)
	if (!D || D->Hint.IsEmpty() || D->bMenu) return;
	const float S = UiScale();
	UFont* F = GEngine ? GEngine->GetMediumFont() : nullptr;
	float W = 300.0f * S, H = 0.0f;
	if (F) GetTextSize(D->Hint, W, H, F, 0.8f * S);
	const float X = 32.0f * S, Y = (D->SideObjective().IsEmpty() ? 98.0f : 124.0f) * S;
	Panel(X, Y, W + 28.0f * S, 34.0f * S, FLinearColor(0.05f, 0.08f, 0.02f, 0.55f));
	Text(D->Hint, X + 14.0f * S, Y + 7.0f * S, FLinearColor(0.85f, 1.0f, 0.6f), 0.8f * S);
}

void ATarsisHUD::DrawHiding(ATarsisDirector* D)
{
	// dentro de la taquilla: todo a oscuras salvo las rendijas de la puerta, a la altura de los ojos
	if (!D || !D->bHiding) return;
	const float X = Canvas->ClipX, Y = Canvas->ClipY;
	const FLinearColor Dark(0.0f, 0.0f, 0.0f, 0.97f);
	const float Top = Y * 0.36f, SlitH = Y * 0.035f, Gap = Y * 0.03f, L = X * 0.18f, R = X * 0.82f;
	Panel(0.0f, 0.0f, X, Top, Dark);
	float Yc = Top;
	for (int32 i = 0; i < 4; ++i)
	{
		Panel(0.0f, Yc, L, SlitH, Dark);
		Panel(R, Yc, X - R, SlitH, Dark);
		Yc += SlitH;
		Panel(0.0f, Yc, X, Gap, Dark);
		Yc += Gap;
	}
	Panel(0.0f, Yc, X, Y - Yc, Dark);
}