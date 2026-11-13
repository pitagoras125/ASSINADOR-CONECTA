@echo off
setlocal
cd /d "%~dp0"
call PREPARAR_AMBIENTE.bat
if errorlevel 1 (
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto erro
.venv\Scripts\python.exe app.py %*
if errorlevel 1 goto erro
exit /b 0
:erro
echo Nao foi possivel iniciar. Confira o erro exibido acima.
pause
exit /b 1
