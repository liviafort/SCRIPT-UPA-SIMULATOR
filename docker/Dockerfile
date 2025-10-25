# Imagem base leve do Python
FROM python:3.11-slim

WORKDIR /app

# Copiar requirements
COPY src/requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código do simulador
COPY src/upa_simulator.py .

# Copiar arquivo de configuração
COPY config/config.json .

# Criar diretório para logs
RUN mkdir -p /app/logs

# Executar o simulador
CMD ["python", "-u", "upa_simulator.py"]