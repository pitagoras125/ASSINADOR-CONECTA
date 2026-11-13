@echo off
setlocal
cd /d "%~dp0"
call PREPARAR_AMBIENTE.bat
if errorlevel 1 (
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt pytest
if errorlevel 1 exit /b 1
set QT_QPA_PLATFORM=offscreen
.venv\Scripts\python.exe -m pytest tests -q
if errorlevel 1 exit /b 1
call GERAR_EXECUTAVEL.bat
if errorlevel 1 exit /b 1
set "compiler=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%compiler%" set "compiler=ISCC.exe"
"%compiler%" instalador.iss
exit /b %errorlevel%
