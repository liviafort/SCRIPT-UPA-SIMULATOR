# Imagem base leve do Python
FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar TODO o diretório src (incluindo módulos)
COPY src/ ./

# Copiar arquivo de configuração
COPY config/config.json .

# Criar diretório para logs
RUN mkdir -p /app/logs

# Executar o simulador
CMD ["python", "-u", "upa_simulator.py"]