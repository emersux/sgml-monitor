# Guia de Instalação (Sem Python)

Para instalar o agente em máquinas que **NÃO** possuem Python instalado:

## 1. Preparação (Na sua máquina de desenvolvimento)

1. Execute o script `build_agent.bat`.
   - Isso criará uma pasta `dist` contendo o arquivo `SGMLAgent.exe`.

## 2. Deploy (Na máquina do cliente)

1. Copie os seguintes arquivos para uma pasta na máquina de destino (ex: `C:\SGML`):
   - `dist\SGMLAgent.exe` (Gerado no passo anterior)
   - `dist\install_service.bat` (Script de instalação)
   - `config.json` (Opcional, mas recomendado para definir o IP do servidor)

2. **Configuração do IP**:
   - Abra o arquivo `config.json` com o Bloco de Notas.
   - Altere o endereço para o IP do seu servidor:
     ```json
     {
         "server_url": "http://192.168.1.50:5000/api/report"
     }
     ```

3. **Instalação**:
   - Clique com o botão direito em `install_service.bat`.
   - Selecione **"Executar como Administrador"**.
   - O script irá instalar e iniciar o serviço automaticamente.

## Comandos Manuais (CMD como Admin)

Caso precise gerenciar manualmente na máquina do cliente:

- Instalar: `SGMLAgent.exe --startup auto install`
- Iniciar: `SGMLAgent.exe start`
- Parar: `SGMLAgent.exe stop`
- Remover: `SGMLAgent.exe remove`
