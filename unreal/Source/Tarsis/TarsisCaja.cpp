// Lost Horizon: De Profundis - tanda 40: la caja de carton y el uniforme.
// La caja (del hangar): con la X te la echas encima. Quieto dentro no te ve nadie (ni guardias, ni torres, ni el
// conductor); si la caja anda, te ven como siempre. Si te la pones delante de quien te persigue, no vale hasta que te
// pierda. En la caja del camion, con ella puesta, el registro del control no te encuentra: sirve para salir.
// El uniforme (capote y casco de una taquilla): de pie y andando, de lejos pasas por un guardia mas. No vale agachado,
// corriendo, ni con la base en alarma.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

bool ATarsisDirector::BoxCloaked() const
{
	return bBoxOn && !bBoxSeen && BoxStillT >= BoxSettle;
}

bool ATarsisDirector::UniformWorks() const
{
	return bUniformNow;
}

bool ATarsisDirector::BoxBlocks()
{
	// lo que no se puede hacer con la caja puesta (dardo, piedra, linterna, prismaticos): avisa, con pausa entre avisos
	if (!bBoxOn) return false;
	if (BoxNagT <= 0.0f)
	{
		BoxNagT = 5.0f;
		ShowMessage(Tx(TEXT("caja_estorba"), TEXT("CON LA CAJA PUESTA, NO\nQuitatela antes (X).")), 3.0f);
	}
	return true;
}

void ATarsisDirector::ToggleBox()
{
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	if (!C || bCodec || bMenu || bCine || bDone || bKeypad || bChoice || bCellAsk) return;
	if (bBoxOn)
	{
		bBoxOn = false;
		BoxStillT = 0.0f;
		PlaySfx(TEXT("recoger"), C->GetActorLocation(), 0.5f);
		return;
	}
	if (!HasFlag(FName(TEXT("caja"))) || bHiding || bCapturing || Dragged || InCell()) return;
	if (bBinoculars) ToggleBinoculars();
	SetTorch(false);
	SprintOff();
	if (!bRiding && !C->bIsCrouched) C->Crouch();
	bBoxOn = true;
	BoxStillT = 0.0f;
	++BoxUses;
	// te la pones delante de quien te persigue: sabe que estas debajo
	bBoxSeen = false;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Alert && !It->bAlly && It->UnseenT < 1.5f) bBoxSeen = true;
	}
	PlaySfx(TEXT("recoger"), C->GetActorLocation(), 0.6f);
	Teach(TEXT("ensena_caja"), TEXT("DENTRO DE LA CAJA\nQuieto no te ve nadie. Si la caja anda, te ven como siempre.\nEn la caja del camion, con ella puesta, el registro no te encuentra. X para quitartela."), {}, 6.0f);
}

void ATarsisDirector::BoxTick(float DeltaSeconds)
{
	if (BoxNagT > 0.0f) BoxNagT -= DeltaSeconds;
	ACharacter* C = Cast<ACharacter>(UGameplayStatics::GetPlayerPawn(this, 0));
	bool bAlert = false;
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		if (It->State == ETarsisGuardState::Alert && !It->bAlly) { bAlert = true; break; }
	}
	if (bBoxOn)
	{
		// te cogen, te encierran o te metes en una taquilla: la caja se queda fuera
		if (!C || bCapturing || bHiding || InCell() || bDone) bBoxOn = false;
		else
		{
			const bool bStill = bRiding || C->GetVelocity().Size2D() < BoxStillSpeed;
			BoxStillT = bStill ? BoxStillT + DeltaSeconds : 0.0f;
			if (!bRiding && !C->bIsCrouched) C->Crouch();
			if (!bAlert) bBoxSeen = false;
		}
	}
	// el uniforme: de pie, andando y sin alarma
	bUniformNow = C && HasFlag(FName(TEXT("uniforme"))) && !bBoxOn && !C->bIsCrouched && !bSprint && !bAlert && !bHiding && !bRiding && !InCell();
	ATarsisGuard::GSeenMul = BoxCloaked() ? 0.0f : 1.0f;
	ATarsisGuard::GBoxNear = BoxNoticeDist;
	ATarsisGuard::GPrisoner = InCell();
	ATarsisGuard::GFarLimit = bUniformNow ? UniformDist : 0.0f;
}
