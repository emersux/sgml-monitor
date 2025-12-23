# Use uma imagem Python oficial leve
FROM python:3.9-slim

# Define o diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias (se houver) e limpa cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de requisitos
COPY requirements.txt .

# Instala as dependências Python
# Removemos pywin32 e wmi pois não rodam em container Linux (servidor)
RUN sed -i '/pywin32/d' requirements.txt && \
    sed -i '/wmi/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copia o código do servidor
COPY server/ ./server/
COPY machines.db . 

# Define variáveis de ambiente
ENV FLASK_APP=server/app.py
ENV PYTHONUNBUFFERED=1

# Expõe a porta (padrão 5000, mas adaptável via variável de ambiente)
EXPOSE 5000

# Comando para iniciar o servidor com Gunicorn
# Bind na porta definida pela nuvem (PORT) ou 5000
CMD gunicorn --bind 0.0.0.0:$PORT server.app:app
