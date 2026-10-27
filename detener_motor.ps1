$ErrorActionPreference = 'Stop'
$taskPidFile = Join-Path $PSScriptRoot '.runtime\server.pid'
if (-not (Test-Path -LiteralPath $taskPidFile)) { throw 'No hay registro del motor iniciado por este proyecto.' }
$taskPid = [int](Get-Content -LiteralPath $taskPidFile)
$taskProcess = Get-Process -Id $taskPid -ErrorAction SilentlyContinue
if ($null -eq $taskProcess) { Write-Output 'El motor ya esta detenido.'; return }
$taskExpected = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '.runtime\ollama\ollama.exe')).Path
if ($taskProcess.Path -ne $taskExpected) { throw 'El PID corresponde a otro ejecutable. No se detiene.' }
Stop-Process -Id $taskPid
Write-Output 'Motor del proyecto detenido.'
