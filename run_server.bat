@echo off
title Servidor SGML
echo Iniciando o Servidor SGML...
echo Acesse http://localhost:5000 no seu navegador.
echo.

if not exist "venv" (
    echo Criando ambiente virtual...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

python server\app.py
pause
