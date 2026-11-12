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
	DrawLight(D, C && C->bIsCrouched);
	DrawAlert();
	DrawGuardMarks();
	DrawMessage(D);
}

void ATarsisHUD::DrawLight(ATarsisDirector* D, bool bCrouched)
{
	const float L = D ? D->PlayerLight : 0.0f;
	const float S = Canvas->ClipY / 1080.0f;   // todo a escala de 1080 p
	const float X = 32.0f * S, Y = Canvas->ClipY - 118.0f * S, W = 300.0f * S, H = 86.0f * S;
	Panel(X, Y, W, H, FLinearColor(0.0f, 0.0f, 0.0f, 0.45f));
	const FLinearColor Col = L < 0.3f ? FLinearColor(0.45f, 0.85f, 0.55f) : (L < 0.6f ? FLinearColor(0.95f, 0.8f, 0.3f) : FLinearColor(1.0f, 0.5f, 0.25f));
	Text(TEXT("LUZ"), X + 14.0f * S, Y + 10.0f * S, FLinearColor(0.8f, 0.8f, 0.8f), 1.0f * S);
	Text(L < 0.3f ? TEXT("EN SOMBRA") : (L < 0.6f ? TEXT("PENUMBRA") : TEXT("ILUMINADO")), X + 70.0f * S, Y + 10.0f * S, Col, 1.0f * S);
	const int32 N = FMath::Clamp(FMath::RoundToInt(L * 10.0f), 0, 10);
	const float SegW = (W - 28.0f * S - 9.0f * 4.0f * S) / 10.0f;
	for (int32 i = 0; i < 10; ++i)
	{
		const FLinearColor SC = i < N ? Col : FLinearColor(1.0f, 1.0f, 1.0f, 0.12f);
		Panel(X + 14.0f * S + i * (SegW + 4.0f * S), Y + 38.0f * S, SegW, 12.0f * S, SC);
	}
	Text(bCrouched ? TEXT("AGACHADO  (C)") : TEXT("DE PIE  (C para agacharte)"), X + 14.0f * S, Y + 58.0f * S,
		bCrouched ? FLinearColor(0.6f, 0.85f, 1.0f) : FLinearColor(0.7f, 0.7f, 0.7f), 0.85f * S);
}

void ATarsisHUD::DrawAlert()
{
	ETarsisGuardState Worst = ETarsisGuardState::Patrol;
	float MaxMeter = 0.0f;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		MaxMeter = FMath::Max(MaxMeter, It->Meter);
		if (It->State == ETarsisGuardState::Alert) Worst = ETarsisGuardState::Alert;
		else if (Worst != ETarsisGuardState::Alert && It->State == ETarsisGuardState::Search) Worst = ETarsisGuardState::Search;
		else if (Worst == ETarsisGuardState::Patrol && It->State == ETarsisGuardState::Suspicious) Worst = ETarsisGuardState::Suspicious;
	}
	if (Worst == ETarsisGuardState::Patrol && MaxMeter < 0.05f) return;
	const float S = Canvas->ClipY / 1080.0f;
	const float CX = Canvas->ClipX / 2.0f, Y = 28.0f * S, W = 460.0f * S;
	FString T = TEXT("TODO TRANQUILO");
	FLinearColor Col(0.8f, 0.8f, 0.8f);
	if (Worst == ETarsisGuardState::Alert) { T = TEXT("!  TE HAN VISTO: ROMPE LA LINEA DE VISTA"); Col = FLinearColor(1.0f, 0.23f, 0.18f); }
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
	const float S = Canvas->ClipY / 1080.0f;
	const float CX = Canvas->ClipX / 2.0f, CY = Canvas->ClipY / 2.0f, M = 60.0f * S;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		const ETarsisGuardState St = It->State;
		if (St == ETarsisGuardState::Patrol || St == ETarsisGuardState::Return) continue;
		const bool bAlert = St == ETarsisGuardState::Alert;
		const FLinearColor Col = bAlert ? FLinearColor(1.0f, 0.23f, 0.18f) : FLinearColor(1.0f, 0.82f, 0.23f);
		const FVector P = It->GetActorLocation() + FVector(0.0f, 0.0f, 120.0f);
		FVector2D Scr;
		const bool bIn = PC->ProjectWorldLocationToScreen(P, Scr, true) && Scr.X > M && Scr.X < Canvas->ClipX - M && Scr.Y > M && Scr.Y < Canvas->ClipY - M;
		if (bIn) continue;   // si se le ve, ya lleva su marca encima de la cabeza
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
	if (!D || D->MessageT <= 0.0f || D->Message.IsEmpty()) return;
	const float S = Canvas->ClipY / 1080.0f;
	const float A = FMath::Clamp(D->MessageT, 0.0f, 1.0f);
	TArray<FString> Lines;
	D->Message.ParseIntoArray(Lines, TEXT("\n"));
	const float Y0 = Canvas->ClipY * 0.62f;
	Panel(Canvas->ClipX * 0.2f, Y0 - 12.0f * S, Canvas->ClipX * 0.6f, (Lines.Num() * 34.0f + 24.0f) * S, FLinearColor(0.0f, 0.0f, 0.0f, 0.55f * A));
	for (int32 i = 0; i < Lines.Num(); ++i)
	{
		Text(Lines[i], Canvas->ClipX / 2.0f, Y0 + i * 34.0f * S, FLinearColor(1.0f, 0.95f, 0.85f, A), (i == 0 ? 1.15f : 0.95f) * S, true);
	}
}
