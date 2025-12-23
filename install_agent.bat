@echo off
setlocal
title Instalador do Agente SGML

echo ==========================================
echo      Instalador do Agente SGML
echo ==========================================
echo.

:: Check for Admin rights
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Executando como Administrador.
) else (
    echo [ERRO] Este script precisa ser executado como Administrador.
    echo Por favor, clique com o botao direito e selecione "Executar como Administrador".
    pause
    exit /b
)

echo.
echo [1/4] Criando ambiente virtual Python...
python -m venv venv
if %errorLevel% neq 0 (
    echo [ERRO] Falha ao criar ambiente virtual. Verifique se o Python esta instalado e no PATH.
    pause
    exit /b
)

echo.
echo [2/4] Instalando dependencias...
call venv\Scripts\activate
pip install -r requirements.txt
if %errorLevel% neq 0 (
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b
)

echo.
echo [3/4] Instalando o servico Windows...
python agent\agent_service.py --startup auto install
if %errorLevel% neq 0 (
    echo [ERRO] Falha ao instalar o servico.
    pause
    exit /b
)

echo.
echo [4/4] Iniciando o servico...
python agent\agent_service.py start
if %errorLevel% neq 0 (
    echo [ERRO] Falha ao iniciar o servico.
    pause
    exit /b
)

echo.
echo ==========================================
echo      Instalacao Concluida com Sucesso!
echo ==========================================
echo O agente esta rodando em segundo plano.
echo Para verificar, abra o Painel de Servicos e procure por "SGML Agent Service".
echo.
pause
