# Guia de Deploy na Nuvem (Cloud)

Sim, é perfeitamente possível e recomendado hospedar o servidor na nuvem. Isso permite que agentes de diferentes redes enviem dados para um local centralizado.

Abaixo estão opções gratuitas ou baratas para hospedar o servidor Python (Flask).

## Opção 1: Render.com (Mais Fácil / Gratuito)

O Render tem um plano gratuito (Free Tier) para Web Services que entra em hibernação após inatividade, mas é ótimo para testes.

1. Crie uma conta no [Render.com](https://render.com).
2. Crie um novo "Web Service".
3. Conecte seu repositório GitHub/GitLab (você precisará subir esse código para lá).
4. Configure:
   - **Environment**: Docker
   - **Branch**: main
5. Clique em Deploy.
6. O Render vai gerar uma URL pública (ex: `https://sgml-app.onrender.com`).

**Importante sobre Banco de Dados (SQLite)**: 
Em serviços como Render/Heroku (Free Tier), o sistema de arquivos é "efêmero". Isso significa que se o servidor reiniciar, o arquivo `machines.db` será resetado.
*Solução*: Para produção real, recomenda-se usar um banco de dados externo (PostgreSQL) ou volumes persistentes (Render Disk).

## Opção 2: VPS (DigitalOcean / AWS / Oracle Cloud)

Se você tiver uma máquina virtual (VPS):

1. Instale o Docker na VPS.
2. Copie os arquivos do projeto para lá.
3. Construa e rode o container:
   ```bash
   docker build -t sgml-server .
   docker run -d -p 80:5000 -v $(pwd)/data:/app/data sgml-server
   ```
   *(Nota: O `-v` garante que o banco de dados seja salvo fora do container)*

## Atualizando o Agente

Após subir o servidor na nuvem:

1. Pegue a URL pública gerada (ex: `https://seu-projeto.onrender.com`).
2. Atualize o arquivo `config.json` nas máquinas dos clientes:
   ```json
   {
       "server_url": "https://seu-projeto.onrender.com/api/report"
   }
   ```
3. Reinicie o serviço do agente (`SGMLAgent.exe restart`).

## Segurança (Recomendado)

Atualmente o dashboard é público. Ao colocar na nuvem, qualquer pessoa com o link pode ver os dados. Recomendo adicionar uma senha simples de acesso no `app.py` se for usar em produção pública.
