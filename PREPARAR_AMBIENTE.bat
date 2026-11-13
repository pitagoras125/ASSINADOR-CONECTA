@echo off
setlocal
cd /d "%~dp0"
set "venv_python=.venv\Scripts\python.exe"
if not exist "%venv_python%" (
  py -3.12 -m venv --without-pip .venv
  if errorlevel 1 goto python_error
)
"%venv_python%" -m pip --version >nul 2>&1
if not errorlevel 1 exit /b 0
echo Preparando o pip no ambiente do Conecta PDF...
"%venv_python%" -m ensurepip --upgrade
if errorlevel 1 goto pip_error
"%venv_python%" -m pip --version
if errorlevel 1 goto pip_error
exit /b 0
:python_error
echo Falha ao criar o ambiente. Confira se o Python 3.12 de 64 bits e o inicializador py estao instalados.
exit /b 1
:pip_error
echo Falha ao reparar o pip. Repare a instalacao do Python com o componente pip e tente novamente.
exit /b 1
