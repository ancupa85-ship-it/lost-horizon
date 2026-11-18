// Lost Horizon: De Profundis — tanda 39: «tus cosas las tiene Peris».
// Al encerrarte en el calabozo te registran: sales sin linterna, sin prismaticos y sin dardos. Estan en el cajon de la
// mesa de Peris, en la sala de guardia. Peris hace su ronda de siempre (mesa, puerta a fumar, mesa): hay que entrar
// cuando sale, o tumbarlo, o sacarlo con una piedra, y registrar el cajon. Registrar lleva unos segundos, hace ruido
// (quien este cerca lo oye) y se corta si te apartas. No es obligatorio: la mision se puede acabar sin equipo.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

void ATarsisDirector::TakeGear()
{
	if (!bGearRule || bGearTaken || bGearBack) return;
	bGearTaken = true;
	GearDarts = Darts;
	Darts = 0;
	bGearHadTorch = bHasTorch;
	SetTorch(false);
	bHasTorch = false;
	if (bBinoculars) ToggleBinoculars();
	GearT = 0.0f;
	bGearSearching = false;
}

// Lo que sale al usar algo que ya no llevas (con pausa entre avisos: el clic del dardo se pulsa mucho)
void ATarsisDirector::GearNag()
{
	if (!bGearTaken || GearNagT > 0.0f) return;
	GearNagT = 6.0f;
	ShowMessage(Tx(TEXT("equipo_falta"), TEXT("TE LO HAN QUITADO\nLinterna, prismaticos y dardos estan en el cajon de Peris, en la sala de guardia.")), 4.0f);
}

FString ATarsisDirector::GearPrompt() const
{
	if (!bGearTaken || GearSpot.IsZero() || !NearPlayer(GearSpot, GearRadius)) return FString();
	if (bGearSearching) return Tx(TEXT("p_cajon_buscando"), TEXT("REGISTRANDO EL CAJON...  {0} s"), { FMath::CeilToInt(FMath::Max(GearSeconds - GearT, 0.0f)) });
	return Tx(TEXT("p_cajon"), TEXT("E   REGISTRAR EL CAJON DE PERIS"));
}

bool ATarsisDirector::GearInteract()
{
	if (!bGearTaken || GearSpot.IsZero() || !NearPlayer(GearSpot, GearRadius)) return false;
	if (bGearSearching) return true;
	bGearSearching = true;
	GearT = 0.0f;
	GearNoiseT = 0.0f;
	++GearTries;
	return true;
}

void ATarsisDirector::GearTick(float DeltaSeconds)
{
	if (GearNagT > 0.0f) GearNagT -= DeltaSeconds;
	if (!bGearSearching) return;
	if (bCapturing || !NearPlayer(GearSpot, GearRadius + 40.0f))
	{
		bGearSearching = false;
		if (!bCapturing) ShowMessage(Tx(TEXT("cajon_dejado"), TEXT("CAJON A MEDIAS\nTe apartas y lo dejas como estaba. Hay que empezar otra vez.")), 3.0f);
		return;
	}
	GearT += DeltaSeconds;
	GearNoiseT -= DeltaSeconds;
	if (GearNoiseT <= 0.0f)
	{
		// revolver un cajon de chapa se oye en la sala y en la puerta
		GearNoiseT = 1.2f;
		PlaySfx(TEXT("taquilla"), GearSpot + FVector(0.0f, 0.0f, 80.0f), 0.5f);
		for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
		{
			if (It->bAlly || It->State == ETarsisGuardState::Down || It->State == ETarsisGuardState::Alert) continue;
			if (FVector::Dist(It->GetActorLocation(), GearSpot) < GearHeard) It->HearNoise(GearSpot);
		}
	}
	if (GearT < GearSeconds) return;
	bGearSearching = false;
	bGearTaken = false;
	bGearBack = true;
	bHasTorch = bGearHadTorch;
	Darts += GearDarts;
	GearDarts = 0;
	SetFlag(FName(TEXT("equipo")));
	PlaySfx(TEXT("recoger"), GearSpot + FVector(0.0f, 0.0f, 80.0f), 0.8f);
	ShowMessage(Tx(TEXT("equipo_vuelve"), TEXT("TUS COSAS\nLinterna, prismaticos y dardos, envueltos en tu propia chaqueta.\nDebajo, un reloj de pulsera parado a las tres y dos.")), 8.0f);
}
