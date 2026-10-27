@echo off
where pythonw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pythonw.exe "%~dp0abrir_laboratorio.pyw"
    exit /b
)
where pyw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pyw.exe -3 "%~dp0abrir_laboratorio.pyw"
    exit /b
)
echo No se encontro Python. Instala Python 3.11 o posterior y vuelve a abrir el laboratorio.
pause
