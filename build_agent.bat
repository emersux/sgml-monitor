@echo off
title Construindo Agente SGML (EXE)

echo ==========================================
echo      Construindo Executavel do Agente
echo ==========================================
echo.

if not exist "venv" (
    echo [1/3] Criando ambiente virtual...
    python -m venv venv
)

call venv\Scripts\activate

echo [2/3] Instalando requisitos (incluindo PyInstaller)...
pip install -r requirements.txt

echo.
echo [3/3] Gerando o executavel com PyInstaller...
echo Isso pode levar alguns minutos.

:: --hidden-import win32timezone is crucial for services
pyinstaller --noconfirm --log-level=WARN ^
    --onefile ^
    --hidden-import=win32timezone ^
    --name="SGMLAgent" ^
    --add-data="agent/agent.py;." ^
    agent/agent_service.py

echo.
if %errorLevel% == 0 (
    echo [SUCESSO] Executavel criado em dist\SGMLAgent.exe
    echo.
    echo Para distribuir:
    echo 1. Copie o arquivo dist\SGMLAgent.exe
    echo 2. Copie o arquivo config.json (crie um se precisar mudar o IP)
    echo 3. Copie o script install_service.bat
) else (
    echo [ERRO] Falha na criacao do executavel.
)

pause
