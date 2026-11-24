// Lost Horizon: De Profundis - tanda I. La tira del objeto en mano (abajo a la derecha) y la vista del espejo.
#include "TarsisHUD.h"
#include "TarsisDirector.h"
#include "Engine/Canvas.h"
#include "Engine/TextureRenderTarget2D.h"
#include "EngineUtils.h"
#include "TarsisGuard.h"

void ATarsisHUD::DrawItems(ATarsisDirector* D)
{
	if (!D || D->bMenu || D->bCodec || D->bCine || D->bDone || D->bMindMap || D->bBinoculars) return;
	const float S = UiScale();
	const float X = Canvas->ClipX, Y = Canvas->ClipY;
	// el espejo, en un recuadro
	if (D->bMirrorOn && D->MirrorRT)
	{
		const float W = 384.0f * S, H = 256.0f * S, Mx = X - W - 30.0f * S, My = Y - H - 150.0f * S;
		Panel(Mx - 4.0f * S, My - 4.0f * S, W + 8.0f * S, H + 8.0f * S, FLinearColor(0.05f, 0.05f, 0.05f, 0.9f));
		DrawTexture(D->MirrorRT, Mx, My, W, H, 0.0f, 0.0f, 1.0f, 1.0f, FLinearColor::White, BLEND_Opaque);
	}
	// cuantos tipos llevas: con uno solo (los dardos) no hace falta la tira
	int32 Owned = 0;
	for (int32 i = 0; i < ATarsisDirector::NumItems; ++i) if (D->ItemCount(i) != 0) ++Owned;
	if (Owned == 0) return;
	const int32 I = D->ItemSel;
	const int32 N = D->ItemCount(I);
	const FString Count = N > 0 ? FString::Printf(TEXT("  x%d"), N) : FString();
	const FString Line = FString::Printf(TEXT("%s%s"), *D->ItemName(I), *Count);
	const float W = 260.0f * S, H = 40.0f * S, Px = X - W - 30.0f * S, Py = Y - H - 96.0f * S;
	Panel(Px, Py, W, H, FLinearColor(0.02f, 0.025f, 0.02f, 0.72f));
	Panel(Px, Py, 3.0f * S, H, FLinearColor(0.6f, 0.9f, 0.7f, 0.9f));
	Text(Line, Px + 14.0f * S, Py + 6.0f * S, FLinearColor::White, 0.95f * S);
	if (Owned > 1) Text(D->Tx(TEXT("obj_ayuda"), TEXT("rueda / 1-6   clic: usar")), Px + 14.0f * S, Py + 26.0f * S, FLinearColor(0.6f, 0.65f, 0.6f), 0.55f * S);
}

// ---------------------------------------------------------------- tanda J: el plano de la jefatura en el mapa mental

void ATarsisHUD::DrawPlan(ATarsisDirector* D, float Bx, float By, float Bw, float Bh)
{
	if (!D) return;
	const float S = UiScale();
	Panel(Bx, By, Bw, Bh, FLinearColor(0.11f, 0.105f, 0.085f, 0.97f));   // papel viejo, a oscuras
	Panel(Bx, By, Bw, 3.0f * S, FLinearColor(0.85f, 0.7f, 0.3f));
	Text(TEXT("PLANO DE LA JEFATURA"), Bx + 12.0f * S, By + 10.0f * S, FLinearColor(0.95f, 0.88f, 0.7f), 0.95f * S);
	Text(TEXT("Rondas a lapiz; torres con su proximo relevo."), Bx + 12.0f * S, By + 34.0f * S, FLinearColor(0.7f, 0.66f, 0.55f), 0.66f * S);
	const float Cell = FMath::Max(D->PlanCell, 1.0f);
	const int32 Rows = D->PlanRows.Num();
	const int32 Cols = Rows > 0 ? D->PlanRows[0].Len() : 0;
	// lo que cabe: la planta y todas las rondas y torres
	FBox2D Bnd(FVector2D(0.0f, 0.0f), FVector2D(FMath::Max(Cols, 1) * Cell, FMath::Max(Rows, 1) * Cell));
	TArray<class ATarsisGuard*> Gs;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		if (G->bTowerSentry || G->bAlly || G->PatrolPoints.Num() < 2) continue;
		Gs.Add(G);
		for (const FVector& P : G->PatrolPoints) Bnd += FVector2D(P.X, P.Y);
	}
	for (int32 i = 0; i < D->ReliefPostCount(); ++i) { const FVector P = D->ReliefPostLoc(i); Bnd += FVector2D(P.X, P.Y); }
	Bnd = Bnd.ExpandBy(300.0f);
	const float Mx = Bx + 16.0f * S, My = By + 60.0f * S, Mw = Bw - 32.0f * S, Mh = Bh - 76.0f * S;
	const FVector2D Size = Bnd.GetSize();
	const float K = FMath::Min(Mw / FMath::Max(Size.X, 1.0f), Mh / FMath::Max(Size.Y, 1.0f));
	const float Ox = Mx + (Mw - Size.X * K) * 0.5f, Oy = My + (Mh - Size.Y * K) * 0.5f;
	auto Px = [&](float Wx) { return Ox + (Wx - Bnd.Min.X) * K; };
	auto Py = [&](float Wy) { return Oy + (Wy - Bnd.Min.Y) * K; };
	// la planta: muros y paredes en tinta, el suelo de dentro sombreado
	const float Cw = Cell * K + 0.5f;
	for (int32 r = 0; r < Rows; ++r)
	{
		const FString& Row = D->PlanRows[r];
		for (int32 c = 0; c < Row.Len(); ++c)
		{
			const TCHAR Ch = Row[c];
			if (Ch == TEXT('#') || Ch == TEXT('W')) Panel(Px(c * Cell), Py(r * Cell), Cw, Cw, FLinearColor(0.42f, 0.38f, 0.3f, 1.0f));
			else if (Ch == TEXT('_') || Ch == TEXT('z')) Panel(Px(c * Cell), Py(r * Cell), Cw, Cw, FLinearColor(0.16f, 0.15f, 0.12f, 1.0f));
			else if (Ch == TEXT('D') || Ch == TEXT('L') || Ch == TEXT('V')) Panel(Px(c * Cell), Py(r * Cell), Cw, Cw, FLinearColor(0.55f, 0.36f, 0.18f, 1.0f));
		}
	}
	// las rondas: cada guardia con su color, su recorrido cerrado y su nombre al empezar
	const FLinearColor Ink[] = { FLinearColor(0.85f, 0.25f, 0.2f), FLinearColor(0.25f, 0.55f, 0.85f), FLinearColor(0.35f, 0.75f, 0.35f), FLinearColor(0.85f, 0.65f, 0.2f),
		FLinearColor(0.7f, 0.4f, 0.8f), FLinearColor(0.3f, 0.8f, 0.8f), FLinearColor(0.9f, 0.5f, 0.6f), FLinearColor(0.75f, 0.75f, 0.7f) };
	for (int32 g = 0; g < Gs.Num(); ++g)
	{
		const TArray<FVector>& Pts = Gs[g]->PatrolPoints;
		const FLinearColor C = Ink[g % UE_ARRAY_COUNT(Ink)];
		for (int32 i = 0; i < Pts.Num(); ++i)
		{
			const FVector& A = Pts[i];
			const FVector& B = Pts[(i + 1) % Pts.Num()];
			DrawLine(Px(A.X), Py(A.Y), Px(B.X), Py(B.Y), C, 2.0f * S);
		}
		Panel(Px(Pts[0].X) - 3.0f * S, Py(Pts[0].Y) - 3.0f * S, 6.0f * S, 6.0f * S, C);
		Text(Gs[g]->GuardName.ToUpper(), Px(Pts[0].X) + 5.0f * S, Py(Pts[0].Y) - 8.0f * S, C, 0.55f * S);
	}
	// las torres y su relevo
	for (int32 i = 0; i < D->ReliefPostCount(); ++i)
	{
		const FVector P = D->ReliefPostLoc(i);
		const float Next = D->ReliefNextIn(i);
		Panel(Px(P.X) - 5.0f * S, Py(P.Y) - 5.0f * S, 10.0f * S, 10.0f * S, FLinearColor(0.95f, 0.88f, 0.7f));
		const FString Line = Next > 0.0f ? FString::Printf(TEXT("%s  relevo %d:%02d"), *D->ReliefPostName(i).ToUpper(), FMath::FloorToInt(Next / 60.0f), FMath::FloorToInt(Next) % 60)
			: FString::Printf(TEXT("%s  relevandose"), *D->ReliefPostName(i).ToUpper());
		// junto al borde derecho, la etiqueta a la izquierda de la torre
		const float Tx0 = Px(P.X) + 8.0f * S + 190.0f * S > Bx + Bw ? Px(P.X) - 198.0f * S : Px(P.X) + 8.0f * S;
		Text(Line, Tx0, Py(P.Y) - 7.0f * S, FLinearColor(0.95f, 0.88f, 0.7f), 0.58f * S);
	}
	// tu, un punto
	if (APawn* Pl = GetOwningPawn())
	{
		const FVector P = Pl->GetActorLocation();
		if (Bnd.IsInside(FVector2D(P.X, P.Y))) Panel(Px(P.X) - 4.0f * S, Py(P.Y) - 4.0f * S, 8.0f * S, 8.0f * S, FLinearColor(0.4f, 1.0f, 0.5f));
	}
}
