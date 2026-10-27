$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskExe = Join-Path $taskRoot '.runtime\ollama\ollama.exe'
if (-not (Test-Path -LiteralPath $taskExe)) { throw 'Ejecutar primero python instalar_motor.py' }
try {
    $taskExisting = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/version' -TimeoutSec 2
} catch { $taskExisting = $null }
if ($null -ne $taskExisting) {
    Write-Output ('Ya hay un motor en 127.0.0.1:11434, version '+$taskExisting.version+'. No se inicia otro. Verificar doctor antes de continuar.')
    return
}
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_MODELS = Join-Path $taskRoot '.runtime\models'
$env:OLLAMA_NO_CLOUD = '1'
$taskProcess = Start-Process -FilePath $taskExe -ArgumentList 'serve' -WorkingDirectory $taskRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskRoot '.runtime\server.stdout.log') -RedirectStandardError (Join-Path $taskRoot '.runtime\server.stderr.log') -PassThru
$taskProcess.Id | Set-Content -LiteralPath (Join-Path $taskRoot '.runtime\server.pid')
Write-Output ('Motor iniciado solo en esta PC. PID '+$taskProcess.Id)
