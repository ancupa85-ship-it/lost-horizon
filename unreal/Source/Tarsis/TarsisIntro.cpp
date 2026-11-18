// Lost Horizon: De Profundis - tanda 48: la intro de anime.
// Antes de dar el mando, la mision ensena un video (Content/Movies/<IntroMovie>): Cuttlas entra por la brecha. El rotulo
// de lugar y fecha no viene en el video: lo teclea el juego al pie, letra a letra, para que salga nitido y se pueda
// traducir. E o Espacio la saltan. Si el archivo no esta (o el video no arranca), la mision empieza con el sobrevuelo
// de siempre. Necesita MediaAssets y AudioMixer en el Build.cs del modulo (PruebaLumen.Build.cs, que no esta en el repo).
#include "TarsisDirector.h"

#include "FileMediaSource.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "Kismet/GameplayStatics.h"
#include "MediaPlayer.h"
#include "MediaSoundComponent.h"
#include "MediaTexture.h"
#include "Misc/Paths.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

bool ATarsisDirector::PlayIntroMovie()
{
	if (!bIntroMovie || IntroMovie.IsEmpty()) return false;
	const FString Path = FPaths::ConvertRelativePathToFull(FPaths::ProjectContentDir() / TEXT("Movies") / IntroMovie);
	if (!IFileManager::Get().FileExists(*Path)) return false;
	IntroPlayer = NewObject<UMediaPlayer>(this);
	IntroPlayer->SetLooping(false);
	IntroPlayer->PlayOnOpen = true;
	IntroTexture = NewObject<UMediaTexture>(this);
	IntroTexture->AutoClear = true;
	IntroTexture->ClearColor = FLinearColor::Black;
	IntroTexture->SetMediaPlayer(IntroPlayer);
	IntroTexture->UpdateResource();
	IntroSound = NewObject<UMediaSoundComponent>(this);
	IntroSound->SetMediaPlayer(IntroPlayer);
	IntroSound->bIsUISound = true;
	IntroSound->RegisterComponent();
	IntroSource = NewObject<UFileMediaSource>(this);
	IntroSource->SetFilePath(Path);
	if (!IntroPlayer->OpenSource(IntroSource)) { CloseIntroMovie(); return false; }
	bMovie = true;
	bCine = true;
	bCineIntro = true;
	MovieT = 0.0f;
	if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Pl->SetActorHiddenInGame(true);   // oculto, los guardias no lo ven
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0)) { PC->SetIgnoreMoveInput(true); PC->SetIgnoreLookInput(true); }
	++MoviesPlayed;
	return true;
}

void ATarsisDirector::CloseIntroMovie()
{
	if (IntroPlayer) IntroPlayer->Close();
	if (IntroSound) { IntroSound->Stop(); IntroSound->DestroyComponent(); }
	IntroPlayer = nullptr;
	IntroTexture = nullptr;
	IntroSound = nullptr;
	IntroSource = nullptr;
}

void ATarsisDirector::EndIntroMovie()
{
	if (!bMovie) return;
	bMovie = false;
	bCine = false;
	CloseIntroMovie();
	if (APawn* Pl = UGameplayStatics::GetPlayerPawn(this, 0)) Pl->SetActorHiddenInGame(false);
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0)) { PC->ResetIgnoreMoveInput(); PC->ResetIgnoreLookInput(); }
	MessageT = 0.0f;
	IntroText();
}

void ATarsisDirector::MovieTick(float DeltaSeconds)
{
	if (!bMovie) return;
	MovieT += DeltaSeconds;
	// con tirones el reloj del juego se queda atras del video: manda el del video
	if (IntroPlayer && IntroPlayer->IsPlaying()) MovieT = FMath::Max(MovieT, static_cast<float>(IntroPlayer->GetTime().GetTotalSeconds()));
	// se acabo, no ha arrancado en tres segundos o se pasa del tope: a jugar
	const bool bRunning = IntroPlayer && (IntroPlayer->IsPlaying() || IntroPlayer->IsPreparing() || IntroPlayer->IsBuffering());
	if (MovieT > MovieMaxSeconds || (MovieT > 3.0f && !bRunning)) EndIntroMovie();
}

FString ATarsisDirector::MovieCaption() const
{
	// el rotulo se teclea: a partir de MovieCaptionAt, MovieCaptionRate letras por segundo
	if (!bMovie || MovieT < MovieCaptionAt) return FString();
	const FString Full = Tx(TEXT("intro_rotulo"), TEXT("BASE DE TARSIS. MURO NORTE\n29 DE NOVIEMBRE DE 1983. 23:10"));
	const int32 N = FMath::Clamp(static_cast<int32>((MovieT - MovieCaptionAt) * MovieCaptionRate), 0, Full.Len());
	return Full.Left(N);
}
