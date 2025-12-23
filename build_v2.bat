@echo off
title Construindo Agente SGML v2

echo ==========================================
echo      Construindo SGML Monitor v2
echo ==========================================
echo.

if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate
pip install -r requirements.txt

echo.
echo [Build] Gerando executavel...

:: Usando novo nome para evitar conflito de arquivo em uso
pyinstaller --noconfirm --log-level=WARN ^
    --onefile ^
    --hidden-import=win32timezone ^
    --name="SGMLMonitor" ^
    --add-data="agent/agent.py;." ^
    agent/agent_service.py

echo.
if %errorLevel% == 0 (
    echo [SUCESSO] Novo executavel criado: dist\SGMLMonitor.exe
) else (
    echo [ERRO] Falha na criacao.
)
pause
