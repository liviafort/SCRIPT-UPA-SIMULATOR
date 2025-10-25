# UPA Patient Flow Simulator

Simulador de fluxo de pacientes para UPAs de Campina Grande - PB, implementando o **Protocolo de Manchester** para gestão de filas por prioridade.

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Protocolo de Manchester](#protocolo-de-manchester)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Execução](#execução)
- [Logs e Monitoramento](#logs-e-monitoramento)
- [Execução em Servidor (24/7)](#execução-em-servidor-247)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

Este simulador reproduz o fluxo completo de pacientes em Unidades de Pronto Atendimento (UPAs), desde a entrada até a finalização do atendimento, respeitando o Protocolo de Manchester de triagem.

### Funcionalidades

- ✅ Simulação de entrada contínua de pacientes
- ✅ Implementação completa do Protocolo de Manchester (4 níveis)
- ✅ Gestão de filas por prioridade
- ✅ Integração com serviço de monitoramento via API REST
- ✅ Configuração flexível de fluxo por UPA (por minuto/hora/dia)
- ✅ Logs detalhados com rotação automática
- ✅ Estatísticas em tempo real
- ✅ Execução 24/7 com tratamento de erros robusto

### Fluxo Simulado

```
Entrada → Fila de Triagem → Triagem (classificação) → Fila de Atendimento (priorizada) → Atendimento → Finalização
```

---

## 🏥 Protocolo de Manchester

O simulador implementa os 4 níveis de classificação do Protocolo de Manchester:

| Classificação | Prioridade | Tempo Máx. Espera | Descrição |
|--------------|------------|-------------------|-----------|
| 🔴 VERMELHO | 1 (mais urgente) | 0 minutos | Emergência - Atendimento imediato |
| 🟡 AMARELO | 2 | 60 minutos | Muito urgente |
| 🟢 VERDE | 3 | 120 minutos | Urgente |
| 🔵 AZUL | 4 (menos urgente) | 240 minutos | Pouco urgente |

### Gestão de Filas

- **Fila de Triagem**: FIFO (First In, First Out)
- **Fila de Atendimento**: Ordenada por prioridade (Vermelho → Amarelo → Verde → Azul)
- **Alertas**: O sistema emite alertas quando pacientes excedem o tempo máximo de espera

---

## 💻 Requisitos

- **Python**: 3.8 ou superior
- **Serviços**:
  - Serviço Monitoring rodando (porta 8086)
  - Serviço Gateway rodando (porta 8084)
  - Banco de dados PostgreSQL populado com UPAs

---

## 📦 Instalação

### 1. Clonar/Copiar arquivos

Certifique-se de ter os seguintes arquivos no servidor:

```
/opt/upa-simulator/
├── upa_simulator.py
├── config.json
├── requirements.txt
└── SIMULATOR_README.md
```

### 2. Criar ambiente virtual (recomendado)

```bash
cd /opt/upa-simulator
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuração

Edite o arquivo `config.json` para ajustar os parâmetros da simulação.

### Configurações Principais

#### 1. URLs dos Serviços

```json
{
  "monitoring_service": {
    "base_url": "http://localhost:8086"
  },
  "gateway_service": {
    "base_url": "http://localhost:8084"
  }
}
```

**Importante**: Se estiver rodando no servidor, use o IP do servidor ou `localhost`.

#### 2. Configuração de Fluxo por UPA

```json
{
  "upas": {
    "UPA Dinamérica": {
      "enabled": true,
      "patient_flow": {
        "mode": "per_hour",  // "per_minute", "per_hour", "per_day"
        "rate": 12           // 12 pacientes por hora
      }
    }
  }
}
```

**Modos de Fluxo**:
- `per_minute`: Taxa de pacientes por minuto (ex: `"rate": 2` = 2 pacientes/min)
- `per_hour`: Taxa de pacientes por hora (ex: `"rate": 12` = 12 pacientes/hora = 1 a cada 5 min)
- `per_day`: Taxa de pacientes por dia (ex: `"rate": 288` = 288 pacientes/dia = 1 a cada 5 min)

#### 3. Distribuição de Classificações

```json
{
  "classificacao_distribution": {
    "VERMELHO": 0.05,  // 5% dos pacientes
    "AMARELO": 0.25,   // 25% dos pacientes
    "VERDE": 0.50,     // 50% dos pacientes
    "AZUL": 0.20       // 20% dos pacientes
  }
}
```

**Importante**: A soma deve ser **1.0** (100%).

#### 4. Fator de Velocidade

```json
{
  "simulation": {
    "real_time_factor": 1.0  // 1.0 = tempo real, 2.0 = 2x mais rápido
  }
}
```

- `1.0`: Tempo real
- `2.0`: Simulação 2x mais rápida (útil para testes)
- `0.5`: Simulação 2x mais lenta

---

## 🚀 Execução

### Execução Manual

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Executar simulador
python upa_simulator.py
```

### Parar Simulação

Pressione `Ctrl+C` para parar gracefully.

---

## 📊 Logs e Monitoramento

### Arquivo de Log

O simulador gera logs em `upa_simulator.log` com rotação automática:

- **Tamanho máximo**: 10 MB
- **Backups**: 5 arquivos
- **Formato**: `YYYY-MM-DD HH:MM:SS - LEVEL - MESSAGE`

### Níveis de Log

- `INFO`: Eventos normais (entrada, triagem, atendimento)
- `WARNING`: Alertas (tempo de espera excedido)
- `ERROR`: Erros de comunicação com API
- `DEBUG`: Informações detalhadas (desabilitado por padrão)

### Visualizar Logs em Tempo Real

```bash
tail -f upa_simulator.log
```

### Estatísticas Automáticas

O simulador exibe estatísticas a cada 1 minuto:

```
================================================================================
ESTATÍSTICAS - 14:35:22
Total de pacientes ativos: 24
  [UPA Dinamérica] Triagem: 3, Atendimento: 8, Total: 11
  [UPA Alto Branco] Triagem: 5, Atendimento: 8, Total: 13
================================================================================
```

---

## 🖥️ Execução em Servidor (24/7)

### Opção 1: Screen (mais simples)

```bash
# Instalar screen
sudo apt-get install screen  # Ubuntu/Debian

# Criar sessão
screen -S upa-simulator

# Ativar ambiente e executar
cd /opt/upa-simulator
source venv/bin/activate
python upa_simulator.py

# Desanexar: Ctrl+A, depois D
# Reanexar: screen -r upa-simulator
```

### Opção 2: Systemd Service (recomendado para produção)

1. Criar arquivo de serviço:

```bash
sudo nano /etc/systemd/system/upa-simulator.service
```

2. Adicionar conteúdo:

```ini
[Unit]
Description=UPA Patient Flow Simulator
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=seu_usuario
WorkingDirectory=/opt/upa-simulator
ExecStart=/opt/upa-simulator/venv/bin/python /opt/upa-simulator/upa_simulator.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/upa-simulator.log
StandardError=append:/var/log/upa-simulator-error.log

[Install]
WantedBy=multi-user.target
```

3. Habilitar e iniciar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable upa-simulator
sudo systemctl start upa-simulator
```

4. Comandos úteis:

```bash
# Status
sudo systemctl status upa-simulator

# Parar
sudo systemctl stop upa-simulator

# Reiniciar
sudo systemctl restart upa-simulator

# Ver logs
sudo journalctl -u upa-simulator -f
```

### Opção 3: Docker (isolado)

1. Criar `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY upa_simulator.py config.json ./

CMD ["python", "upa_simulator.py"]
```

2. Build e Run:

```bash
docker build -t upa-simulator .
docker run -d --name upa-simulator --restart unless-stopped upa-simulator
```

---

## 🔧 Troubleshooting

### Problema: "Erro ao buscar UPAs da API"

**Solução**:
- Verifique se o serviço Gateway está rodando (`curl http://localhost:8084/actuator/health`)
- Confirme a URL no `config.json`
- O simulador continuará usando UUIDs mockados se não conseguir conectar

### Problema: "Falha ao registrar entrada/triagem/atendimento"

**Solução**:
- Verifique se o serviço Monitoring está rodando (`curl http://localhost:8086/actuator/health`)
- Confirme a URL no `config.json`
- Verifique logs do serviço Monitoring para erros

### Problema: Muitos pacientes acumulados

**Solução**:
- Reduza a taxa de entrada (`patient_flow.rate`)
- Aumente o `real_time_factor` para processar mais rápido
- Reduza os tempos de triagem/atendimento no `config.json`

### Problema: Poucos pacientes

**Solução**:
- Aumente a taxa de entrada
- Verifique se as UPAs estão com `"enabled": true`

---

## 📝 Exemplos de Configuração

### Cenário 1: Fluxo Intenso (Pico)

```json
{
  "UPA Dinamérica": {
    "patient_flow": {
      "mode": "per_hour",
      "rate": 30  // 30 pacientes/hora = 1 a cada 2 min
    }
  }
}
```

### Cenário 2: Fluxo Normal

```json
{
  "UPA Dinamérica": {
    "patient_flow": {
      "mode": "per_hour",
      "rate": 12  // 12 pacientes/hora = 1 a cada 5 min
    }
  }
}
```

### Cenário 3: Fluxo Baixo (Madrugada)

```json
{
  "UPA Dinamérica": {
    "patient_flow": {
      "mode": "per_hour",
      "rate": 4  // 4 pacientes/hora = 1 a cada 15 min
    }
  }
}
```

### Cenário 4: Testes Rápidos

```json
{
  "simulation": {
    "real_time_factor": 10.0  // 10x mais rápido
  },
  "UPA Dinamérica": {
    "patient_flow": {
      "mode": "per_minute",
      "rate": 1  // 1 paciente/minuto → processado em 6s
    }
  }
}
```

---

## 📈 Validação do Protocolo de Manchester

### O que o simulador valida:

1. ✅ **Priorização**: Pacientes VERMELHO são atendidos antes de AMARELO, VERDE e AZUL
2. ✅ **Tempo de Espera**: Alertas quando pacientes excedem o tempo máximo
3. ✅ **Distribuição**: Classificações seguem a distribuição configurada
4. ✅ **Fluxo Contínuo**: Sistema processa pacientes 24/7 sem interrupção

### Métricas no Dashboard

Após rodar o simulador, você pode validar no dashboard web:

- **Fila por Classificação**: Verificar se prioridades estão corretas
- **Tempo Médio de Espera**: Por classificação de Manchester
- **Ocupação**: Taxa de ocupação da UPA ao longo do tempo
- **Distribuição por Bairro**: Verificar origem dos pacientes

---

## 🆘 Suporte

Para problemas ou dúvidas:

1. Verifique os logs: `tail -f upa_simulator.log`
2. Verifique status dos serviços: `docker ps` ou `systemctl status`
3. Teste conectividade: `curl http://localhost:8086/actuator/health`

---

## 📄 Licença

Este simulador faz parte do projeto de TCC - UPA Campina Grande - PB.

---

**Desenvolvido para validação do Protocolo de Manchester no sistema UPA-TCC**