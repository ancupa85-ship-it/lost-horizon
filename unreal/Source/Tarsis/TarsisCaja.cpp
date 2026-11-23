// Lost Horizon: De Profundis - tanda 40: la caja de carton y el uniforme.
// La caja (del hangar): con la X te la echas encima. Quieto dentro no te ve nadie (ni guardias, ni torres, ni el
// conductor); si la caja anda, te ven como siempre. Si te la pones delante de quien te persigue, no vale hasta que te
// pierda. En la caja del camion, con ella puesta, el registro del control no te encuentra: sirve para salir.
// El uniforme (capote y casco de una taquilla): de pie y andando, de lejos pasas por un guardia mas. No vale agachado,
// corriendo, ni con la base en alarma.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

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
	// tanda H: con el santo y sena de esta noche (oido en el relevo de las torres) te dejan acercarte mucho mas
	const bool bPass = bUniformNow && HasFlag(FName(TEXT("dato_relevo_santo"))) && !PasswordA.IsEmpty();
	ATarsisGuard::GFarLimit = bUniformNow ? (bPass ? FMath::Min(UniformPassDist, UniformDist) : UniformDist) : 0.0f;
	if (bPass) ChallengeTick();
}

void ATarsisDirector::ChallengeTick()
{
	// el primero que te tiene delante, a tiro de voz y sin nada en medio, te da el alto; Cuttlas contesta la sena.
	// Una vez por guardia: luego ya te ha visto la cara de lejos y te toma por uno de los suyos.
	const APawn* P = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!P || bCodec || bCine) return;
	const FVector PL = P->GetActorLocation();
	for (TActorIterator<ATarsisGuard> It(GetWorld()); It; ++It)
	{
		ATarsisGuard* G = *It;
		if (G->bAlly || G->bTowerSentry || G->State == ETarsisGuardState::Down || G->State == ETarsisGuardState::Alert || G->StunT > 0.0f) continue;
		if (Challenged.Contains(G->GuardName)) continue;
		const FVector D = PL - G->GetActorLocation();
		if (D.Size() > ChallengeDist || FMath::Abs(D.Z) > 250.0f) continue;
		if (FVector::DotProduct(G->GetActorForwardVector(), D.GetSafeNormal2D()) < 0.5f) continue;   // te tiene delante
		FCollisionQueryParams Q(SCENE_QUERY_STAT(TarsisSanto), false, G);
		Q.AddIgnoredActor(P);
		FHitResult Hit;
		if (GetWorld()->LineTraceSingleByChannel(Hit, G->GetActorLocation() + FVector(0.0f, 0.0f, 70.0f), PL + FVector(0.0f, 0.0f, 50.0f), ECC_Visibility, Q)) continue;
		Challenged.Add(G->GuardName);
		SaySubtitle(G->GuardName.ToUpper(), Tx(TEXT("santo_alto"), TEXT("Alto. {0}?"), { PasswordA }), 2.2f);
		const FString Reply = Tx(TEXT("santo_respuesta"), TEXT("{0}."), { PasswordB });
		FTimerHandle H;
		GetWorldTimerManager().SetTimer(H, FTimerDelegate::CreateWeakLambda(this, [this, Reply]() { SaySubtitle(TEXT("CUTTLAS"), Reply, 2.2f); }), 1.4f, false);
		Teach(TEXT("ensena_santo"), TEXT("SANTO Y SENA\nCon el uniforme y la sena de esta noche, los guardias te dejan acercarte mucho mas. De muy cerca, o corriendo, siguen viendote la cara."), {}, 4.5f);
		break;
	}
}
