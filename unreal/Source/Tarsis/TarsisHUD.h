// Lost Horizon: De Profundis — HUD del sigilo en el nivel Tarsis (dibujado con el Canvas del motor, sin assets).
// Indicador de luz y postura, aviso de alerta con la sospecha, marcas «?» y «!» de los guardias en el borde
// de la pantalla cuando no se ven, mensajes del director (captura, celda...), objetivo de la misión, aviso de la E
// y el teclado del archivo. Lo instala ATarsisDirector.
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "TarsisHUD.generated.h"

UCLASS()
class ATarsisHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void DrawHUD() override;

private:
	void DrawLight(class ATarsisDirector* D, bool bCrouched);
	void DrawAlert();
	void DrawGuardMarks();
	void DrawMessage(class ATarsisDirector* D);
	void DrawObjective(class ATarsisDirector* D);
	void DrawPrompt(class ATarsisDirector* D);
	void DrawKeypad(class ATarsisDirector* D);
	void Panel(float X, float Y, float W, float H, const FLinearColor& C);
	void Text(const FString& S, float X, float Y, const FLinearColor& C, float Scale, bool bCenter = false);
};
