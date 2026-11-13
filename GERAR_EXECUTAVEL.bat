@echo off
setlocal
cd /d "%~dp0"
call PREPARAR_AMBIENTE.bat
if errorlevel 1 (
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.16.0
if errorlevel 1 goto erro
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --icon "assets\app_icon.ico" --add-data "assets;assets" --add-data "update_public_key.hex;." --name AssinadorConecta --collect-all cv2 --collect-all brazilfiscalreport --collect-all fpdf --collect-all barcode --collect-all PIL --collect-all pyhanko --collect-all pyhanko_certvalidator --collect-all pypdfium2 --collect-all pypdfium2_raw --copy-metadata cryptography --copy-metadata pyHanko --exclude-module PyQt6 --exclude-module PySide6.QtWebEngineCore app.py
if errorlevel 1 goto erro
echo Executavel criado em dist\AssinadorConecta\AssinadorConecta.exe
echo Para criar o instalador, compile instalador.iss com Inno Setup 6.
pause
exit /b 0
:erro
echo Falha na compilacao. Confira o erro acima.
pause
exit /b 1
