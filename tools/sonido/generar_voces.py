"""Voces de los guardias de Tarsis con la síntesis de voz de Windows (sin conexión), en assets/unreal/sonidos/voz_<guardia>_<frase>.wav.

Usa la voz española de Windows (Microsoft Pablo, es-ES; si no está, Helena) a través de Windows.Media.SpeechSynthesis desde
PowerShell, con tono y velocidad distintos para cada guardia (SSML <prosody>). Luego, con numpy: recorta el silencio, iguala
el volumen y a las frases por radio les pone filtro de radio (banda de 300-3000 Hz, saturación, soplido y chasquidos).
Solo funciona en Windows. Uso: python tools/sonido/generar_voces.py
Las frases las dice ATarsisDirector::GuardSay (en 3D sobre el guardia, con subtítulo si está activado).
"""
import json, os, subprocess, sys, tempfile, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(os.path.dirname(HERE)), 'assets', 'unreal', 'sonidos')
rng = np.random.default_rng(11)

# clave -> (texto, por radio). El texto en pantalla lo pone el C++ (en ASCII); aquí va con tildes para que suene bien.
FRASES = {
    'quien': ('¿Quién anda ahí?', False),
    'ruido': ('¿Qué ha sido eso?', False),
    'viento': ('Bah. Habrá sido el viento.', False),
    'alto': ('¡Alto! ¡Quieto ahí!', False),
    'nadie': ('Aquí no hay nadie.', False),
    'suelo': ('Central, aquí patio. He encontrado a uno en el suelo.', True),
}
# guardia -> (tono, velocidad): un sargento grave y lento, un cuartelero joven y deprisa...
GUARDIAS = {
    'ibarra': ('-12%', '0.92'), 'moya': ('-2%', '1.0'), 'peris': ('+8%', '1.06'),
    'vega': ('-6%', '0.97'), 'ramos': ('+15%', '1.1'), 'centinela': ('-16%', '0.95'),
}

PS = r'''
param([string]$Lista)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Esperar($op, [Type]$tipo) { $t = $asTask.MakeGenericMethod($tipo).Invoke($null, @($op)); $t.Wait(-1) | Out-Null; $t.Result }
$s = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$voz = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | ? { $_.Language -like 'es-*' -and $_.DisplayName -like '*Pablo*' } | Select -First 1
if (-not $voz) { $voz = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | ? { $_.Language -like 'es-*' } | Select -First 1 }
if (-not $voz) { Write-Error 'No hay voz en espanol instalada'; exit 1 }
$s.Voice = $voz
Write-Output ("voz: " + $voz.DisplayName)
foreach ($e in (Get-Content $Lista -Raw -Encoding UTF8 | ConvertFrom-Json)) {
  $ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='$($voz.Language)'><prosody pitch='$($e.tono)' rate='$($e.vel)'>$($e.texto)</prosody></speak>"
  $st = Esperar ($s.SynthesizeSsmlToStreamAsync($ssml)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
  $r = New-Object Windows.Storage.Streams.DataReader($st.GetInputStreamAt(0))
  $n = [uint32]$st.Size
  $null = Esperar ($r.LoadAsync($n)) ([uint32])
  $b = New-Object byte[] $n
  $r.ReadBytes($b)
  [IO.File]::WriteAllBytes($e.ruta, $b)
}
'''

def leer(ruta):
    with wave.open(ruta, 'rb') as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2' if sw == 2 else np.uint8).astype(float)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x / (32768.0 if sw == 2 else 128.0), sr

def guardar(nombre, x, sr, pico=0.8):
    x = x / (np.max(np.abs(x)) + 1e-9) * pico
    with wave.open(os.path.join(OUT, nombre + '.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())
    print(nombre, round(len(x) / sr, 2), 's')

def recortar(x, sr):
    e = np.abs(x) > 0.02 * np.max(np.abs(x))
    i = np.argmax(e); j = len(x) - np.argmax(e[::-1])
    return x[max(0, i - int(0.03 * sr)):min(len(x), j + int(0.08 * sr))]

def polo(x, a):
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc = a * acc + (1 - a) * v; y[i] = acc
    return y

def radio(x, sr):
    # banda de walkie (fuera graves y agudos), algo de saturación, soplido y chasquido al apretar y soltar
    a_hp = np.exp(-2 * np.pi * 300 / sr); a_lp = np.exp(-2 * np.pi * 3000 / sr)
    y = x - polo(x, a_hp)
    y = polo(polo(y, a_lp), a_lp)
    y = np.tanh(y / (np.max(np.abs(y)) + 1e-9) * 2.5)
    y += 0.06 * (rng.normal(0, 1, len(y)))
    c = int(0.05 * sr); clic = rng.normal(0, 1, c) * np.exp(-np.arange(c) / (0.006 * sr)) * 0.8
    return np.concatenate([clic, np.zeros(int(0.04 * sr)), y, np.zeros(int(0.04 * sr)), clic * 0.6])

if __name__ == '__main__':
    if os.name != 'nt':
        sys.exit('Las voces se generan con la síntesis de voz de Windows: ejecuta este script en Windows.')
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='voces_')
    lista = []
    for g, (tono, vel) in GUARDIAS.items():
        for k, (texto, _) in FRASES.items():
            lista.append({'ruta': os.path.join(tmp, '%s_%s.wav' % (g, k)), 'texto': texto, 'tono': tono, 'vel': vel})
    with open(os.path.join(tmp, 'lista.json'), 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False)
    with open(os.path.join(tmp, 'voces.ps1'), 'w', encoding='utf-8-sig') as f:
        f.write(PS)
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(tmp, 'voces.ps1'),
                        '-Lista', os.path.join(tmp, 'lista.json')], capture_output=True, text=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        sys.exit(r.stderr)
    for g in GUARDIAS:
        for k, (texto, por_radio) in FRASES.items():
            x, sr = leer(os.path.join(tmp, '%s_%s.wav' % (g, k)))
            x = recortar(x, sr)
            if por_radio:
                x = radio(x, sr)
            guardar('voz_%s_%s' % (g, k), x, sr, 0.75 if por_radio else 0.85)
