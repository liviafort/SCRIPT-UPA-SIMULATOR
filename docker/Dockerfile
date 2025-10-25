# Imagem base leve do Python
FROM python:3.11-slim

WORKDIR /app

COPY src/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY src/upa_simulator.py .

COPY config/config.json .

RUN mkdir -p /app/logs

CMD ["python", "-u", "upa_simulator.py"]