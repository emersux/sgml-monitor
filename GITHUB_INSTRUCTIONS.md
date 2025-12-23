# Como enviar para o GitHub

O repositório Git local já foi criado e seus arquivos foram salvos. Agora, para enviar para o GitHub (para poder fazer deploy na nuvem), siga estes passos:

## 1. Crie o repositório no GitHub

1. Acesse [github.com/new](https://github.com/new) e faça login.
2. Em **Repository name**, digite `sgml-monitor` (ou o nome que preferir).
3. Deixe como **Public** ou **Private** (Private recomendado se não quiser que vejam seu código).
4. **Não** marque nenhuma opção de "Initialize this repository with..." (README, gitignore, etc), pois já temos isso localmente.
5. Clique em **Create repository**.

## 2. Conecte seu computador ao GitHub

Copie os comandos que aparecerão na tela do GitHub sob o título **"…or push an existing repository from the command line"**.

Eles serão parecidos com isso (substitua `SEU_USUARIO` pelo seu user real):

```bash
git remote add origin https://github.com/emersux/sgml-monitor.git
git branch -M main
git push -u origin main
```

## 3. Execute os comandos

Abra o terminal nesta pasta (`c:\Users\Emerson\.gemini\antigravity\scratch\SGML`) e cole os comandos acima, um por um.

Se pedir senha, lembre-se que o GitHub agora usa **Tokens de Acesso Pessoal** (PAT) em vez de senha de conta para HTTPS.

---

### Dica para Deploy (Render.com)

Assim que você fizer o `git push` e o código estiver no GitHub, você pode ir no [Render.com](https://render.com), criar um novo **Web Service** e selecionar esse repositório da lista. O deploy será automático!
