# Usa uma imagem leve do Python 3.11
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema necessárias para algumas libs (como gcc para compilar)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de requisitos para dentro do container
COPY requirements.txt .

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código fonte para o container
COPY . .

# Expõe a porta 8000
EXPOSE 8000

# Comando padrão para iniciar a API (o docker-compose pode sobrescrever isso, mas é bom ter)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]