# Abre el editor de PruebaLumen con ZenServer (la cache de Unreal) ya en marcha y listo.
#
# Por que: al arrancar, si ZenServer tarda mas de 20 s en avisar, Unreal saca el cuadro «¿Esperar a ZenServer?» y el
# editor se queda parado hasta que alguien contesta (ZenServerInterface.cpp); el 26-11-2026 estuvo asi 4 h 16 min.
# Con ZenServer ya arrancado y contestando en /health/ready, el editor lo encuentra y no espera.
#
# Uso:   powershell -ExecutionPolicy Bypass -File tools\unreal\abrir_editor.ps1 [-Mapa /Game/Tarsis/Mapas/Tarsis]
# Deshacer: no hace falta cambiar nada; basta con abrir el editor como antes. Para cerrar el ZenServer que deja en
# marcha:  & "$env:LOCALAPPDATA\UnrealEngine\Common\Zen\Install\zenserver.exe" down --port 8558
# (o cerrar zenserver.exe en el Administrador de tareas con el editor cerrado). No toca DefaultEngine.ini ni la cache.
param(
    [string]$Mapa = '/Game/Tarsis/Mapas/Tarsis',
    [string]$Proyecto = 'D:\PruebaLumen\PruebaLumen\PruebaLumen.uproject',
    [string]$Editor = 'D:\ue_5.8\Engine\Binaries\Win64\UnrealEditor.exe',
    [int]$Puerto = 8558,
    [int]$EsperaMax = 180
)

$zenDir = Join-Path $env:LOCALAPPDATA 'UnrealEngine\Common\Zen'
$zen = Join-Path $zenDir 'Install\zenserver.exe'
$datos = Join-Path $zenDir 'Data'
$listo = "http://127.0.0.1:$Puerto/health/ready"

function Test-ZenListo {
    try { return (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 $listo).Content -match 'OK' } catch { return $false }
}

if (Get-Process UnrealEditor -ErrorAction SilentlyContinue) {
    Write-Output 'Ya hay un editor abierto: no abro otro.'
    exit 1
}

if (-not (Test-ZenListo)) {
    if (-not (Test-Path $zen)) { Write-Output "No encuentro $zen"; exit 1 }
    # los mismos parametros con que lo lanza el editor, sin --owner-pid (asi no se cierra con el editor) ni --child-id
    $zargs = @('--port', $Puerto, '--data-dir', $datos, '--http', 'asio',
              '--gc-cache-duration-seconds', '1209600', '--gc-interval-seconds', '21600',
              '--gc-low-diskspace-threshold', '2147483648', '--cache-bucket-limit-overwrites', '--quiet',
              '--restrict-content-types', '--allow-external-oidctoken-exe=false',
              '--plugins-config', (Join-Path $zenDir 'Install\zen_plugins_v1.json'),
              '--security-config-path', (Join-Path $zenDir 'Install\security-config.json'))
    Start-Process -FilePath $zen -ArgumentList $zargs -WindowStyle Hidden
    $t0 = Get-Date
    while (-not (Test-ZenListo)) {
        if (((Get-Date) - $t0).TotalSeconds -gt $EsperaMax) { Write-Output "ZenServer no contesta tras $EsperaMax s"; exit 1 }
        Start-Sleep -Seconds 1
    }
    Write-Output ("ZenServer listo en {0:N0} s" -f ((Get-Date) - $t0).TotalSeconds)
} else {
    Write-Output 'ZenServer ya estaba listo.'
}

Start-Process -FilePath $Editor -ArgumentList @("`"$Proyecto`"", $Mapa)
Write-Output 'Editor lanzado.'
