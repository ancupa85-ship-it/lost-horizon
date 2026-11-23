// Lost Horizon: De Profundis - tanda I. La tira del objeto en mano (abajo a la derecha) y la vista del espejo.
#include "TarsisHUD.h"
#include "TarsisDirector.h"
#include "Engine/Canvas.h"
#include "Engine/TextureRenderTarget2D.h"

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
