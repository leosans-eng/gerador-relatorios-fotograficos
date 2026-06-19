@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0.."

set "PYTHON=.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
    echo Ambiente virtual nao encontrado.
    exit /b 1
)

for /f "delims=" %%V in ('"%PYTHON%" setup\read_app_version.py') do set "APPVER=%%V"
echo Versao do app: %APPVER%

echo.
echo [1/2] Gerando executavel com PyInstaller...
"%PYTHON%" -m pip install pyinstaller certifi --quiet
"%PYTHON%" -m PyInstaller ^
    --noconfirm ^
    --windowed ^
    --name GeradorRelatoriosFotograficos ^
    --icon setup\icone.ico ^
    --add-data "modelos;modelos" ^
    --add-data "setup;setup" ^
    --add-data "anomalias.json;." ^
    --hidden-import gerar_relatorio_word ^
    --hidden-import atualizacao ^
    --hidden-import app_paths ^
    --hidden-import certifi ^
    --collect-data certifi ^
    --hidden-import tkinterdnd2 ^
    main.py
if errorlevel 1 exit /b 1

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" (
    echo Inno Setup 6 nao encontrado. Instale em https://jrsoftware.org/isinfo.php
    echo O .exe esta em dist\GeradorRelatoriosFotograficos\GeradorRelatoriosFotograficos.exe
    exit /b 1
)

echo.
echo [2/2] Gerando instalador...
"%ISCC%" /DMyAppVersion=%APPVER% setup\grf_installer.iss
if errorlevel 1 exit /b 1

echo.
echo Concluido:
echo   dist\GeradorRelatoriosFotograficos\GeradorRelatoriosFotograficos.exe
echo   dist\GeradorRelatoriosFotograficos_Setup_%APPVER%.exe
echo.
echo Atualize version.json no GitHub com version=%APPVER% e o link do Setup.
