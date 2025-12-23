# Sistema de Gerenciamento de Máquinas Locais (SGML)

Este sistema permite monitorar hardware, software e métricas de máquinas em uma rede local. O sistema é composto por um servidor central (dashboard) e um agente que deve ser instalado em cada máquina a ser monitorada.

## Estrutura do Projeto

- `server/`: Código do servidor Web (Flask).
- `agent/`: Código do agente de coleta de dados.
- `requirements.txt`: Dependências do projeto.
- `install_agent.bat`: Script para instalar o agente como serviço Windows.
- `run_server.bat`: Script para iniciar o servidor.

## Pré-requisitos

- Python 3.8 ou superior instalado.
- Acesso de Administrador para instalar o agente.

## Configuração

### 1. Servidor

1. Execute o arquivo `run_server.bat`.
2. O servidor iniciará em `http://0.0.0.0:5000`.
3. Acesse `http://localhost:5000` para ver o dashboard.

### 2. Agente (Cliente)

**Importante**: Antes de instalar, edite o arquivo `agent/agent.py` e altere a variável `SERVER_URL` para o IP do servidor, caso não esteja na mesma máquina.
Exemplo: `SERVER_URL = "http://192.168.1.10:5000/api/report"`

Para instalar o agente como um serviço do Windows (que roda automaticamente em segundo plano):

1. Clique com o botão direito em `install_agent.bat` e selecione **"Executar como Administrador"**.
2. O script irá:
   - Criar um ambiente virtual Python.
   - Instalar as dependências necessárias.
   - Registrar o "SGML Agent Service" no Windows.
   - Iniciar o serviço imediatamente.

O agente enviará dados a cada 60 segundos.

## Funcionalidades

- **Monitoramento de Hardware**: CPU, Memória, Disco, Fabricante, Serial.
- **Geolocalização**: Estimativa baseada em IP.
- **Inventário de Software**: Lista programas instalados (via Registro do Windows).
- **Status em Tempo Real**: Uptime e última conexão.

## Comandos Úteis do Agente

Se precisar gerenciar o serviço manualmente (dentro do ambiente virtual):

- **Parar**: `python agent/agent_service.py stop`
- **Iniciar**: `python agent/agent_service.py start`
- **Remover**: `python agent/agent_service.py remove`
- **Debug**: `python agent/agent_service.py debug`

## Troubleshooting

- **O serviço não inicia**: Verifique se o Python está no PATH do sistema. Use `python agent/agent_service.py debug` para ver erros detalhados.
- **Dashboard vazio**: Verifique se o firewall não está bloqueando a porta 5000 no servidor.
