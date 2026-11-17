// Lost Horizon: De Profundis — el códec de Tarsis (tanda 29). Parte de ATarsisDirector: ver el bloque «códec» de
// TarsisDirector.h. Los diálogos vienen de la versión web (src/07-codec.js), adaptados a esta base.
#include "TarsisDirector.h"
#include "TarsisGuard.h"

#include "Engine/Texture.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"

// Textos solo en ASCII: MSVC lee los .cpp sin BOM como si no fueran UTF-8.

namespace
{
	FName CodecTextKey(FName Conv)
	{
		return FName(*(FString(TEXT("codec_")) + Conv.ToString()));
	}
}

void ATarsisDirector::CodecRing(FName Conv)
{
	if (Conv.IsNone() || bDone) return;
	if (bCodec) return;   // hablando: la que entra se pierde
	CodecPending = Conv;
	CodecRingT = CodecRingSeconds;
	bCodecMenu = false;
	if (USoundBase* S = Sfx(TEXT("codec_llamada"))) UGameplayStatics::PlaySound2D(this, S, 0.5f);
}

void ATarsisDirector::CodecKey()
{
	if (bCodec) { CodecNext(); return; }
	if (bMenu || bCine || bDone || bCapturing || bKeypad || bChoice || bRadioAsk) return;
	if (!CodecPending.IsNone())
	{
		OpenCodec(CodecPending);
		return;
	}
	bCodecMenu = !bCodecMenu;
	CodecMenuT = bCodecMenu ? CodecMenuSeconds : 0.0f;
	if (USoundBase* S = Sfx(TEXT("codec_tecla"))) UGameplayStatics::PlaySound2D(this, S, 0.4f);
}

void ATarsisDirector::CodecInput(FKey Key)
{
	if (Key == ActionKeys[7]) { CodecKey(); return; }
	if (bCodec) CodecNext();   // la E y el clic pasan de frase
}

bool ATarsisDirector::OpenCodec(FName Conv)
{
	return OpenCodecList({ Conv });
}

bool ATarsisDirector::OpenCodecList(const TArray<FName>& Convs)
{
	if (bCodec || bMenu || bCine || bDone || bCapturing) return false;
	TArray<FCodecLine> Lines;
	FString LastFreq = TEXT("141.12");
	for (const FName& Conv : Convs)
	{
		const FString Raw = Tx(CodecTextKey(Conv), TEXT(""));
		TArray<FString> Rows;
		Raw.ParseIntoArray(Rows, TEXT("\n"));
		for (const FString& Row : Rows)
		{
			FString Code, Body;
			if (!Row.Split(TEXT("|"), &Code, &Body)) { Code = TEXT("C"); Body = Row; }
			Body.TrimStartAndEndInline();
			if (Body.IsEmpty()) continue;
			FCodecLine L;
			L.Text = Body;
			if (Code == TEXT("T")) { L.Who = TEXT("CUTTLAS"); L.Port = TEXT("cuttlas"); L.Freq = LastFreq; L.bMe = true; }
			else if (Code == TEXT("R")) { L.Who = TEXT("ROIG"); L.Port = TEXT("roig"); L.Freq = TEXT("140.85"); }
			else if (Code == TEXT("F")) { L.Who = TEXT("- - -"); L.Port = TEXT("fuente"); L.Freq = TEXT("000.00"); bCodecVoiceHeard = true; }
			else { L.Who = TEXT("CONTROL"); L.Port = TEXT("control"); L.Freq = TEXT("141.12"); }
			LastFreq = L.Freq;
			Lines.Add(L);
		}
	}
	if (Lines.Num() == 0) return false;
	CodecLines = Lines;
	for (const FName& Conv : Convs)
	{
		CodecTaken.Add(Conv.ToString());
		if (CodecPending == Conv) CodecPending = NAME_None;
	}
	if (CodecTaken.Num() > 40) CodecTaken.RemoveAt(0, CodecTaken.Num() - 40);
	CodecRingT = 0.0f;
	bCodecMenu = false;
	bCodec = true;
	CodecIdx = 0;
	CodecBlips = 0;
	CodecLineStart = GetWorld() ? GetWorld()->GetRealTimeSeconds() : 0.0;
	UGameplayStatics::SetGamePaused(this, true);
	if (USoundBase* S = Sfx(TEXT("codec_abrir"))) UGameplayStatics::PlaySound2D(this, S, 0.5f);
	MusicTick(0.0f);   // en pausa MusicTick no corre: la música baja ya
	return true;
}

int32 ATarsisDirector::CodecTyped() const
{
	if (!bCodec || !CodecLines.IsValidIndex(CodecIdx)) return 0;
	const double Now = GetWorld() ? GetWorld()->GetRealTimeSeconds() : 0.0;
	const int32 N = FMath::FloorToInt32(FMath::Max(0.0, Now - CodecLineStart) * CodecCharsPerSecond);
	return FMath::Clamp(N, 0, CodecLines[CodecIdx].Text.Len());
}

void ATarsisDirector::CodecFrame()
{
	if (!bCodec || !CodecLines.IsValidIndex(CodecIdx)) return;
	const int32 Step = CodecTyped() / 4;
	if (Step > CodecBlips && CodecTyped() < CodecLines[CodecIdx].Text.Len())
	{
		const bool bVoice = CodecLines[CodecIdx].Port == TEXT("fuente");
		if (USoundBase* S = Sfx(bVoice ? TEXT("codec_tecla_grave") : TEXT("codec_tecla"))) UGameplayStatics::PlaySound2D(this, S, 0.22f);
	}
	CodecBlips = FMath::Max(CodecBlips, Step);
}

void ATarsisDirector::CodecNext()
{
	if (!bCodec) return;
	if (CodecLines.IsValidIndex(CodecIdx) && CodecTyped() < CodecLines[CodecIdx].Text.Len())
	{
		CodecLineStart = -100000.0;   // la frase entera de golpe
		return;
	}
	++CodecIdx;
	CodecBlips = 0;
	CodecLineStart = GetWorld() ? GetWorld()->GetRealTimeSeconds() : 0.0;
	if (CodecIdx >= CodecLines.Num()) CloseCodec();
}

void ATarsisDirector::CloseCodec()
{
	if (!bCodec) return;
	bCodec = false;
	CodecLines.Reset();
	CodecIdx = 0;
	if (!bMenu) UGameplayStatics::SetGamePaused(this, false);
	if (USoundBase* S = Sfx(TEXT("codec_cerrar"))) UGameplayStatics::PlaySound2D(this, S, 0.45f);
	MusicTick(0.0f);
}

FName ATarsisDirector::CodecControlConv() const
{
	if (CellT > 0.0f) return TEXT("control_celda");
	if (BaseState() == 2) return TEXT("control_alerta");
	// el primer objetivo cuya bandera esté puesta: «obj_llave» -> «control_llave»
	for (const FTarsisObjective& O : Objectives)
	{
		if (O.If.IsNone() || HasFlag(O.If))
		{
			FString K = O.Text.ToString();
			K.RemoveFromStart(TEXT("obj_"));
			return FName(*(FString(TEXT("control_")) + K));
		}
	}
	return TEXT("control_llave");
}

void ATarsisDirector::CodecCall(int32 Option)
{
	if (bCodec || Option < 1 || Option > 3) return;
	if (Option == 3 && !CodecVoiceOpen()) return;
	bCodecMenu = false;
	TArray<FName> Convs;
	if (Option == 1)
	{
		Convs.Add(CodecControlConv());
		Convs.Add(FName(*FString::Printf(TEXT("control_extra_%d"), CodecControlCalls % 4)));
		++CodecControlCalls;
	}
	else if (Option == 2)
	{
		// la pista del salmo, una vez y solo cuando ya has leído la mesa y el archivo sigue cerrado
		if (bNoteRead && !bVaultOpen && !CodecTaken.Contains(TEXT("roig_salmo"))) Convs.Add(TEXT("roig_salmo"));
		else if (bFile && !CodecTaken.Contains(TEXT("roig_salida"))) Convs.Add(TEXT("roig_salida"));
		else { Convs.Add(FName(*FString::Printf(TEXT("roig_%d"), CodecRoigCalls % 4))); ++CodecRoigCalls; }
	}
	else
	{
		Convs.Add(FName(*FString::Printf(TEXT("fuente_%d"), CodecVoiceCalls % 4)));
		++CodecVoiceCalls;
	}
	OpenCodecList(Convs);
}

TArray<FString> ATarsisDirector::CodecMenuLines() const
{
	TArray<FString> L;
	L.Add(Tx(TEXT("codec_menu"), TEXT("RADIO - ELIGE FRECUENCIA")));
	L.Add(TEXT("1    141.12    CONTROL"));
	L.Add(TEXT("2    140.85    ROIG"));
	if (CodecVoiceOpen()) L.Add(TEXT("3    000.00    - - -"));
	L.Add(Tx(TEXT("codec_colgar"), TEXT("{0}    colgar"), { ActionKeys[7].GetDisplayName().ToString().ToUpper() }));
	return L;
}

FString ATarsisDirector::CodecLine() const
{
	if (!bCodec || !CodecLines.IsValidIndex(CodecIdx)) return FString();
	const FCodecLine& L = CodecLines[CodecIdx];
	return FString::Printf(TEXT("%s|%s|%s"), *L.Who, *L.Freq, *L.Text);
}

FString ATarsisDirector::CodecPendingText() const
{
	if (CodecPending.IsNone() || bCodec || bCine || bDone) return FString();
	const TCHAR* Freq = CodecPending.ToString().StartsWith(TEXT("fuente")) ? TEXT("000.00") : (CodecPending.ToString().StartsWith(TEXT("roig")) ? TEXT("140.85") : TEXT("141.12"));
	const FString RK = ActionKeys[7].GetDisplayName().ToString().ToUpper();
	return CodecRingT > 0.0f ? Tx(TEXT("codec_llamada"), TEXT("LLAMADA  {0}  -  pulsa {1}"), { Freq, RK })
		: Tx(TEXT("codec_espera"), TEXT("{1}: llamada en espera ({0})"), { Freq, RK });
}

FString ATarsisDirector::CodecHelp() const
{
	return Tx(TEXT("codec_seguir"), TEXT("E o Espacio: seguir     Esc: colgar"));
}

UTexture* ATarsisDirector::Portrait(FName Key)
{
	if (TObjectPtr<UTexture>* Found = PortraitCache.Find(Key)) return *Found;
	const FString N = Key.ToString();
	UTexture* T = LoadObject<UTexture>(nullptr, *FString::Printf(TEXT("/Game/Tarsis/Retratos/%s.%s"), *N, *N), nullptr, LOAD_NoWarn | LOAD_Quiet);
	PortraitCache.Add(Key, T);   // también si falta: no se vuelve a buscar
	return T;
}

void ATarsisDirector::CodecTick(float DeltaSeconds)
{
	if (CodecRingT > 0.0f) CodecRingT = FMath::Max(0.0f, CodecRingT - DeltaSeconds);
	if (bCodecMenu)
	{
		CodecMenuT -= DeltaSeconds;
		if (CodecMenuT <= 0.0f || bRadioAsk || bKeypad || bChoice || bCine || bDone || bCapturing) bCodecMenu = false;
	}
	// llamadas entrantes: solo en el momento en que pasa cada cosa (al cargar un punto de control no se repiten)
	const bool bAlert = BaseState() == 2;
	if (!bCodecInit)
	{
		bCodecInit = true;
		bCodecPrevAlert = bAlert; bCodecPrevVault = bVaultOpen; bCodecPrevFile = bFile; bCodecPrevPower = bPowerOff;
		return;
	}
	if (bCodecCalls && !bCine && !bDone)
	{
		if (bFile && !bCodecPrevFile && !CodecTaken.Contains(TEXT("expediente"))) CodecRing(TEXT("expediente"));
		else if (bVaultOpen && !bCodecPrevVault && !CodecTaken.Contains(TEXT("archivo"))) CodecRing(TEXT("archivo"));
		else if (bPowerOff && !bCodecPrevPower && !CodecTaken.Contains(TEXT("fuente_luz"))) CodecRing(TEXT("fuente_luz"));
		else if (bAlert && !bCodecPrevAlert && !CodecTaken.Contains(TEXT("alarma")) && CodecPending.IsNone()) CodecRing(TEXT("alarma"));
	}
	bCodecPrevAlert = bAlert; bCodecPrevVault = bVaultOpen; bCodecPrevFile = bFile; bCodecPrevPower = bPowerOff;
}

void ATarsisDirector::CodecReset()
{
	CloseCodec();
	CodecPending = NAME_None;
	CodecRingT = 0.0f;
	bCodecMenu = false;
	CodecTaken.Reset();
	CodecControlCalls = CodecRoigCalls = CodecVoiceCalls = 0;
	bCodecVoiceHeard = false;
}
