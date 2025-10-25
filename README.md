# Simulador de Fluxo de Pacientes - Protocolo de Manchester

Sistema de simulação para validação do fluxo de pacientes em Unidades de Pronto Atendimento (UPAs) de Campina Grande - PB, com implementação completa do Protocolo de Manchester para gestão de filas por classificação de risco.

---

## Sumário

- [Introdução](#introdução)
- [Fundamentação Teórica](#fundamentação-teórica)
- [Arquitetura do Sistema](#arquitetura-do-sistema)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Execução](#execução)
- [Monitoramento](#monitoramento)
- [Implantação em Produção](#implantação-em-produção)
- [Validação e Testes](#validação-e-testes)
- [Troubleshooting](#troubleshooting)
- [Referências](#referências)

---

## Introdução

Este simulador foi desenvolvido como ferramenta de validação para sistemas de gestão de UPAs, reproduzindo o fluxo completo de pacientes desde a entrada até a finalização do atendimento. O sistema implementa fielmente o Protocolo de Manchester de classificação de risco, conforme adotado pelas UPAs de Campina Grande - PB.

### Objetivos

1. Simular o fluxo contínuo de pacientes em ambiente de urgência e emergência
2. Validar a implementação do Protocolo de Manchester em sistemas de gestão
3. Gerar dados realistas para análise de desempenho e dimensionamento de recursos
4. Fornecer ambiente de testes para sistemas de monitoramento de UPAs

### Funcionalidades Principais

- Simulação de entrada contínua de pacientes com distribuição configurável
- Implementação do Protocolo de Manchester (4 níveis de classificação)
- Gestão de filas priorizadas em todas as etapas do fluxo
- Integração via API REST com serviços de monitoramento
- Sistema de logs com rotação automática
- Estatísticas em tempo real
- Execução 24/7 com tratamento robusto de erros

---

## Fundamentação Teórica

### Protocolo de Manchester

O Protocolo de Manchester é um sistema de triagem e classificação de risco amplamente utilizado em serviços de urgência e emergência. Desenvolvido no Manchester Royal Infirmary (Reino Unido) em 1994, o protocolo estabelece prioridades de atendimento baseadas na gravidade clínica do paciente, não na ordem de chegada.

#### Classificações Implementadas (Campina Grande - PB)

| Classificação | Prioridade | Tempo Máximo de Espera | Descrição |
|--------------|------------|------------------------|-----------|
| VERMELHO | 1 | 0 minutos | Emergência - Risco iminente de vida |
| AMARELO | 2 | 60 minutos | Muito urgente - Risco potencial de vida |
| VERDE | 3 | 120 minutos | Urgente - Necessita atendimento, sem risco imediato |
| AZUL | 4 | 240 minutos | Pouco urgente - Condições clínicas estáveis |

**Nota**: O sistema não implementa a classificação LARANJA, conforme especificação das UPAs de Campina Grande - PB.

### Diferença entre FIFO e Classificação de Risco

**FIFO (First In, First Out)**: Sistema tradicional onde pacientes são atendidos na ordem de chegada.

**Protocolo de Manchester**: Sistema que prioriza pacientes por gravidade clínica. Um paciente classificado como VERMELHO que chega às 10:30 será atendido antes de um paciente AZUL que chegou às 10:00.

**Importante**: O Protocolo de Manchester altera o FIFO tradicional da seguinte forma:
- **Até a triagem**: FIFO (ordem de chegada) - pacientes aguardam triagem sem classificação
- **Após a triagem**: PRIORIZAÇÃO por gravidade - pacientes são atendidos por classificação de risco

---

## Arquitetura do Sistema

### Visão Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                     UPA SIMULATOR (Python)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   Entry      │    │   Triagem    │    │ Atendimento  │     │
│  │   Threads    │───▶│   Processor  │───▶│  Processor   │     │
│  │  (por UPA)   │    │   Thread     │    │   Thread     │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                   │                    │             │
│         ▼                   ▼                    ▼             │
│  ┌──────────────────────────────────────────────────────┐     │
│  │           PriorityQueues (Thread-Safe)               │     │
│  │  • Fila Triagem (priorizada)                         │     │
│  │  • Fila Atendimento (priorizada)                     │     │
│  └──────────────────────────────────────────────────────┘     │
│         │                   │                    │             │
│         └───────────────────┴────────────────────┘             │
│                            │                                   │
│                            ▼                                   │
│                    ┌──────────────┐                            │
│                    │  Monitoring  │                            │
│                    │    Thread    │                            │
│                    └──────────────┘                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
         │                            │
         ▼                            ▼
┌──────────────────┐        ┌──────────────────┐
│  Gateway Service │        │ Monitoring Service│
│   (porta 8084)   │        │   (porta 8086)    │
└──────────────────┘        └──────────────────┘
```

### Componentes Principais

#### 1. Classes de Dados

**ClassificacaoTriagem (Enum)**
- Define os 4 níveis do Protocolo de Manchester
- Armazena prioridade, tempo máximo de espera e descrição

**Patient (dataclass)**
- Representa um paciente com todos os atributos e timestamps
- Implementa `__lt__` para ordenação em PriorityQueue

**UPAConfig (dataclass)**
- Configuração de cada UPA (fluxo, bairros, distribuições)

#### 2. Cliente HTTP (APIClient)

- Baseado em `requests.Session`
- Retry automático com backoff exponencial
- Timeout configurável (padrão: 10 segundos)
- Tratamento de erros HTTP

#### 3. Simulador Principal (UPASimulator)

**Threads de Processamento**:

1. **Entry Threads** (uma por UPA): Gera pacientes em intervalos configurados
2. **Triagem Processor Thread**: Processa fila de triagem priorizada
3. **Atendimento Processor Thread**: Processa fila de atendimento priorizada
4. **Monitor Thread**: Coleta e exibe estatísticas a cada 60 segundos

**Sincronização Thread-Safe**:
- Locks individuais para cada fila de triagem
- Locks individuais para cada fila de atendimento
- Lock global para dicionário de pacientes ativos
- Double-check pattern para evitar race conditions

### Fluxo de Dados

```
1. Entrada (Recepção)
   └─> Paciente fornece dados pessoais (SEM classificação)
   └─> Registrado via API (POST /api/v1/events/entrada)
   └─> Adicionado à Queue de triagem (FIFO)

2. Triagem (Enfermeiro)
   └─> Paciente removido da fila FIFO (ordem de chegada)
   └─> Avaliação de sinais e sintomas (180-600 segundos simulados)
   └─> CLASSIFICAÇÃO DE MANCHESTER é atribuída (VERMELHO/AMARELO/VERDE/AZUL)
   └─> Registrado via API (POST /api/v1/events/triagem)
   └─> Adicionado à PriorityQueue de atendimento (priorizada)

3. Atendimento (Médico)
   └─> Paciente removido da fila por PRIORIDADE (VERMELHO primeiro)
   └─> Verificação de tempo de espera vs. limite do protocolo
   └─> Atendimento médico (tempo varia por classificação)
   └─> Registrado via API (POST /api/v1/events/atendimento)
   └─> Paciente finalizado e removido do sistema
```

---

## Requisitos

### Requisitos de Software

- **Python**: 3.8 ou superior
- **Dependências Python**:
  - `requests >= 2.31.0` - Cliente HTTP
  - `urllib3 >= 2.0.0` - Conexões HTTP
  - `typing-extensions >= 4.8.0` - Type hints

### Requisitos de Infraestrutura

**Importante**: O simulador é um **cliente** que se conecta aos serviços já existentes. Você **NÃO** precisa instalar ou configurar esses serviços para rodar o simulador.

Os serviços devem estar rodando (geralmente em Docker) e acessíveis:

- **Gateway Service**: Servidor rodando na porta 8084
  - Endpoint: `GET /api/v1/upas` (lista de UPAs)

- **Monitoring Service**: Servidor rodando na porta 8086
  - Endpoint: `POST /api/v1/events/entrada`
  - Endpoint: `POST /api/v1/events/triagem`
  - Endpoint: `POST /api/v1/events/atendimento`

**O simulador apenas envia dados HTTP para esses serviços.**

### Requisitos de Sistema

- **CPU**: Mínimo 2 cores (recomendado 4 cores para múltiplas UPAs)
- **Memória RAM**: Mínimo 512 MB (recomendado 1 GB)
- **Disco**: 1 GB para logs e ambiente virtual
- **Rede**: Acesso HTTP aos serviços Gateway e Monitoring

---

## Instalação

### 1. Clonar o Repositório

```bash
git clone <url-do-repositorio>
cd SCRIPT-UPA-SIMULATOR
```

### 2. Criar Arquivo de Configuração

O arquivo `config.json` não está versionado no Git por conter informações sensíveis. Crie-o a partir do template:

```bash
cp config.examples.json config.json
```

### 3. Configurar Ambiente Virtual Python

**Linux/macOS**:
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows**:
```bash
python -m venv venv
venv\Scripts\activate
```

### 4. Instalar Dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Verificar Instalação

```bash
python -c "import requests; print('Dependências OK')"
python -m py_compile upa_simulator.py
```

Se não houver erros, a instalação foi bem-sucedida.

---

## Configuração

### Estrutura do Arquivo `config.json`

```json
{
  "monitoring_service": {
    "base_url": "http://localhost:8086",
    "endpoints": {
      "entrada": "/api/v1/events/entrada",
      "triagem": "/api/v1/events/triagem",
      "atendimento": "/api/v1/events/atendimento"
    }
  },
  "gateway_service": {
    "base_url": "http://localhost:8084",
    "endpoints": {
      "upas": "/api/v1/upas"
    }
  },
  "upas": {
    "UPA Dinamérica": {
      "enabled": true,
      "patient_flow": {
        "mode": "per_hour",
        "rate": 12
      },
      "bairros": ["Dinamérica", "Malvinas", "..."],
      "classificacao_distribution": {
        "VERMELHO": 0.05,
        "AMARELO": 0.25,
        "VERDE": 0.50,
        "AZUL": 0.20
      }
    }
  },
  "simulation": {
    "real_time_factor": 1.0,
    "triagem_time_seconds": {
      "min": 180,
      "max": 600
    },
    "atendimento_time_seconds": {
      "VERMELHO": {"min": 1200, "max": 3600},
      "AMARELO": {"min": 900, "max": 2400},
      "VERDE": {"min": 600, "max": 1800},
      "AZUL": {"min": 300, "max": 1200}
    },
    "logging": {
      "level": "INFO",
      "file": "upa_simulator.log",
      "max_bytes": 10485760,
      "backup_count": 5
    }
  }
}
```

### Parâmetros de Configuração

#### URLs dos Serviços

**monitoring_service.base_url**: URL base do serviço de monitoramento
- Exemplo: `http://localhost:8086`
- Em produção: `http://<ip-servidor>:8086`

**gateway_service.base_url**: URL base do gateway
- Exemplo: `http://localhost:8084`
- Em produção: `http://<ip-servidor>:8084`

#### Configuração de Fluxo de Pacientes

**patient_flow.mode**: Define a unidade de tempo para taxa de entrada
- `per_minute`: Taxa por minuto (ex: `"rate": 2` = 2 pacientes/minuto = 1 a cada 30s)
- `per_hour`: Taxa por hora (ex: `"rate": 12` = 12 pacientes/hora = 1 a cada 5min)
- `per_day`: Taxa por dia (ex: `"rate": 288` = 288 pacientes/dia = 1 a cada 5min)

**patient_flow.rate**: Número de pacientes no período definido

**Cálculo do intervalo**:
```python
if mode == "per_minute":
    intervalo = 60 / rate  # segundos
elif mode == "per_hour":
    intervalo = 3600 / rate  # segundos
elif mode == "per_day":
    intervalo = 86400 / rate  # segundos
```

#### Distribuição de Classificações

**classificacao_distribution**: Probabilidade de cada classificação
- A soma de todas as probabilidades deve ser **exatamente 1.0** (100%)
- Baseado em dados reais das UPAs de Campina Grande - PB

**Exemplo**:
```json
"classificacao_distribution": {
  "VERMELHO": 0.05,  // 5% dos pacientes
  "AMARELO": 0.25,   // 25% dos pacientes
  "VERDE": 0.50,     // 50% dos pacientes
  "AZUL": 0.20       // 20% dos pacientes
}
// Total: 1.00 (100%)
```

#### Fator de Velocidade da Simulação

**real_time_factor**: Multiplicador de velocidade
- `1.0`: Tempo real (padrão)
- `2.0`: 2x mais rápido (útil para testes)
- `0.5`: 2x mais lento (útil para debug)
- `10.0`: 10x mais rápido (testes intensivos)

**Impacto**:
```python
tempo_simulado = tempo_configurado / real_time_factor
```

#### Tempos de Processamento

**triagem_time_seconds**: Tempo de triagem (em segundos)
- `min`: Tempo mínimo (recomendado: 180s = 3 minutos)
- `max`: Tempo máximo (recomendado: 600s = 10 minutos)

**atendimento_time_seconds**: Tempo de atendimento por classificação
- VERMELHO: Casos mais complexos (20-60 minutos)
- AMARELO: Casos urgentes (15-40 minutos)
- VERDE: Casos moderados (10-30 minutos)
- AZUL: Casos simples (5-20 minutos)

#### Configuração de Logs

**logging.level**: Nível de detalhamento
- `DEBUG`: Máximo detalhamento (desenvolvimento)
- `INFO`: Eventos normais (produção)
- `WARNING`: Apenas alertas e erros
- `ERROR`: Apenas erros críticos

**logging.file**: Nome do arquivo de log
- Padrão: `upa_simulator.log`

**logging.max_bytes**: Tamanho máximo antes de rotacionar
- Padrão: 10485760 (10 MB)

**logging.backup_count**: Número de arquivos de backup
- Padrão: 5 (mantém últimos 5 arquivos)

### Exemplos de Configuração por Cenário

#### Cenário 1: Fluxo Normal (Produção)

```json
{
  "upas": {
    "UPA Dinamérica": {
      "enabled": true,
      "patient_flow": {
        "mode": "per_hour",
        "rate": 12
      }
    }
  },
  "simulation": {
    "real_time_factor": 1.0
  }
}
```

**Resultado**: 12 pacientes/hora = 1 paciente a cada 5 minutos em tempo real

#### Cenário 2: Fluxo Intenso (Horário de Pico)

```json
{
  "upas": {
    "UPA Dinamérica": {
      "patient_flow": {
        "mode": "per_hour",
        "rate": 30
      }
    }
  }
}
```

**Resultado**: 30 pacientes/hora = 1 paciente a cada 2 minutos

#### Cenário 3: Testes Rápidos

```json
{
  "upas": {
    "UPA Dinamérica": {
      "patient_flow": {
        "mode": "per_minute",
        "rate": 1
      }
    }
  },
  "simulation": {
    "real_time_factor": 10.0
  }
}
```

**Resultado**: 1 paciente/minuto acelerado 10x = 1 paciente a cada 6 segundos

---

## Execução

### Execução Básica

```bash
# Ativar ambiente virtual
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows

# Executar simulador
python upa_simulator.py
```

### Verificação Pré-Execução

Antes de executar, verifique a conectividade com os serviços:

```bash
# Testar Gateway Service
curl http://localhost:8084/actuator/health

# Testar Monitoring Service
curl http://localhost:8086/actuator/health

# Testar endpoint de UPAs
curl http://localhost:8084/api/v1/upas
```

### Saída Esperada

```
2025-10-25 14:30:15 - root - INFO - ================================================================================
2025-10-25 14:30:15 - root - INFO - Iniciando UPA Simulator - Protocolo de Manchester
2025-10-25 14:30:15 - root - INFO - ================================================================================
2025-10-25 14:30:15 - root - INFO - Buscando UPAs da API...
2025-10-25 14:30:15 - root - INFO - Encontradas 2 UPA(s) na API
2025-10-25 14:30:15 - root - INFO - UPA configurada: UPA Dinamérica (UUID: abc123...)
2025-10-25 14:30:15 - root - INFO - UPA configurada: UPA Alto Branco (UUID: def456...)
2025-10-25 14:30:15 - root - INFO - Simulador inicializado com 2 UPA(s)
2025-10-25 14:30:15 - root - INFO - Protocolo de Manchester: Filas priorizadas por classificação de risco
2025-10-25 14:30:15 - root - INFO -   - UPA Dinamérica: 12.0 pacientes/per_hour
2025-10-25 14:30:15 - root - INFO -   - UPA Alto Branco: 15.0 pacientes/per_hour
2025-10-25 14:30:15 - root - INFO - Simulação iniciada com 4 threads
2025-10-25 14:30:15 - root - INFO - Pressione Ctrl+C para parar
2025-10-25 14:30:15 - root - INFO - [UPA Dinamérica] Entrada de pacientes: 1 a cada 300.0s
2025-10-25 14:30:15 - root - INFO - [UPA Alto Branco] Entrada de pacientes: 1 a cada 240.0s
```

### Parar a Simulação

Para parar gracefully (permite finalização adequada):

```bash
# Pressione Ctrl+C
```

Saída esperada:
```
^C2025-10-25 14:35:22 - root - INFO - Parando simulação...
2025-10-25 14:35:23 - root - INFO - Simulação finalizada
```

---

## Monitoramento

### Logs em Tempo Real

```bash
# Visualizar logs enquanto simulador roda
tail -f upa_simulator.log

# Filtrar apenas entradas de pacientes
tail -f upa_simulator.log | grep "entrou"

# Filtrar apenas classificações VERMELHO
tail -f upa_simulator.log | grep "VERMELHO"

# Filtrar apenas alertas de tempo excedido
tail -f upa_simulator.log | grep "ALERTA"
```

### Estatísticas Automáticas

O simulador exibe estatísticas a cada 60 segundos:

```
================================================================================
ESTATÍSTICAS - 14:35:22
Total de pacientes ativos: 24
  [UPA Dinamérica] Aguardando Triagem (PRIORIZADA): 3, Aguardando Atendimento (PRIORIZADA): 8, Total: 11
  [UPA Alto Branco] Aguardando Triagem (PRIORIZADA): 5, Aguardando Atendimento (PRIORIZADA): 8, Total: 13
================================================================================
```

### Análise de Logs

#### Contar pacientes por classificação

```bash
grep "triado:" upa_simulator.log | grep -o "VERMELHO\|AMARELO\|VERDE\|AZUL" | sort | uniq -c
```

Saída exemplo:
```
  45 AMARELO
  12 AZUL
  89 VERDE
   8 VERMELHO
```

#### Contar alertas de tempo excedido

```bash
grep "ALERTA PROTOCOLO MANCHESTER" upa_simulator.log | wc -l
```

#### Tempo médio total por paciente

```bash
grep "finalizado" upa_simulator.log | grep -o "tempo total: [0-9.]*" | awk '{sum+=$3; count++} END {print "Média:", sum/count, "min"}'
```

### Rotação de Logs

Configuração padrão:
- Arquivo atual: `upa_simulator.log`
- Backups: `upa_simulator.log.1`, `upa_simulator.log.2`, ..., `upa_simulator.log.5`
- Rotação automática ao atingir 10 MB

Para ajustar:
```json
"logging": {
  "max_bytes": 20971520,  // 20 MB
  "backup_count": 10      // 10 arquivos
}
```

---

## Implantação em Produção

### Opção 1: Execução Direta (Simples)

Ideal para testes e validações rápidas.

```bash
# Executar em primeiro plano
cd /caminho/para/SCRIPT-UPA-SIMULATOR
source venv/bin/activate
python upa_simulator.py

# Para parar: Ctrl+C
```

### Opção 2: Screen (Testes Prolongados)

Ideal para manter o simulador rodando enquanto você trabalha em outras tarefas.

```bash
# Instalar screen
sudo apt-get install screen  # Ubuntu/Debian
sudo yum install screen      # CentOS/RHEL

# Criar sessão nomeada
screen -S upa-simulator

# Dentro da sessão, executar
cd /caminho/para/SCRIPT-UPA-SIMULATOR
source venv/bin/activate
python upa_simulator.py

# Desanexar sessão: Ctrl+A, depois D
# Reanexar: screen -r upa-simulator
# Listar sessões: screen -ls
# Matar sessão: screen -X -S upa-simulator quit
```

### Opção 3: systemd Service (Produção - Opcional)

Ideal apenas se você precisar que o simulador rode 24/7 automaticamente.

**Nota**: Esta opção é mais complexa e só é necessária se você realmente precisar de execução automática contínua.

#### Passo 1: Criar arquivo de serviço

```bash
sudo nano /etc/systemd/system/upa-simulator.service
```

#### Passo 2: Configurar serviço

```ini
[Unit]
Description=UPA Patient Flow Simulator - Protocolo de Manchester
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=seu_usuario
Group=seu_usuario
WorkingDirectory=/home/seu_usuario/SCRIPT-UPA-SIMULATOR
Environment="PATH=/home/seu_usuario/SCRIPT-UPA-SIMULATOR/venv/bin"
ExecStart=/home/seu_usuario/SCRIPT-UPA-SIMULATOR/venv/bin/python upa_simulator.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Ajustes necessários**:
- Substituir `seu_usuario` pelo seu usuário do sistema
- Ajustar `WorkingDirectory` para o caminho real do projeto

#### Passo 3: Habilitar e iniciar serviço

```bash
# Recarregar configuração do systemd
sudo systemctl daemon-reload

# Habilitar serviço (inicia automaticamente no boot)
sudo systemctl enable upa-simulator

# Iniciar serviço
sudo systemctl start upa-simulator

# Verificar status
sudo systemctl status upa-simulator
```

#### Comandos úteis do systemd

```bash
# Ver status detalhado
sudo systemctl status upa-simulator

# Parar serviço
sudo systemctl stop upa-simulator

# Reiniciar serviço
sudo systemctl restart upa-simulator

# Ver logs do serviço (últimas 100 linhas)
sudo journalctl -u upa-simulator -n 100

# Seguir logs em tempo real
sudo journalctl -u upa-simulator -f

# Ver logs desde data específica
sudo journalctl -u upa-simulator --since "2025-10-25 14:00:00"

# Ver logs entre datas
sudo journalctl -u upa-simulator --since "2025-10-25 00:00:00" --until "2025-10-25 23:59:59"

# Desabilitar auto-start no boot
sudo systemctl disable upa-simulator
```

### Resumo: Qual Opção Escolher?

| Cenário | Opção Recomendada |
|---------|-------------------|
| Demonstração para banca | **Opção 1** (Execução Direta) |
| Testes de 1-2 horas | **Opção 2** (Screen) |
| Validação 24/7 | **Opção 3** (systemd) |

**Para o TCC**: Na maioria dos casos, a **Opção 1 ou 2** é suficiente.

---

## Validação e Testes

### Validação do Protocolo de Manchester

O simulador valida os seguintes aspectos:

#### 1. Entrada Sem Classificação

Verificar que pacientes entram sem classificação:

```bash
grep "entrou na recepção" upa_simulator.log | head -5
```

Saída esperada:
```
[UPA Dinamérica] Paciente 3f2a8b9c entrou na recepção (Bairro: Malvinas, Aguardando triagem: 1)
[UPA Alto Branco] Paciente 7e5d4c1b entrou na recepção (Bairro: Alto Branco, Aguardando triagem: 2)
```

#### 2. Triagem FIFO

Verificar que pacientes são triados na ordem de chegada:

```bash
# Ver ordem de triagens
grep "Iniciando triagem do paciente" upa_simulator.log | head -10
```

#### 3. Classificação na Triagem

Verificar que classificação é atribuída na triagem:

```bash
grep "classificado como" upa_simulator.log | head -5
```

Saída esperada:
```
[UPA Dinamérica] Paciente 3f2a8b9c classificado como VERMELHO (prioridade 1)
[UPA Alto Branco] Paciente 7e5d4c1b classificado como VERDE (prioridade 3)
```

#### 4. Alertas de Tempo Excedido

```bash
grep "ALERTA PROTOCOLO MANCHESTER" upa_simulator.log
```

Exemplo:
```
[UPA Dinamérica] ALERTA PROTOCOLO MANCHESTER: Paciente 5b3c2a1d (AMARELO) aguardou 65.3 min (máximo permitido: 60 min) - TEMPO EXCEDIDO!
```

#### 5. Distribuição de Classificações

```bash
# Contar por classificação
for cor in VERMELHO AMARELO VERDE AZUL; do
  count=$(grep "triado:" upa_simulator.log | grep -c "$cor")
  echo "$cor: $count"
done
```

Comparar com distribuição configurada.

### Teste de Carga

Simular alta demanda:

```json
{
  "simulation": {
    "real_time_factor": 10.0
  },
  "upas": {
    "UPA Dinamérica": {
      "patient_flow": {
        "mode": "per_minute",
        "rate": 2
      }
    }
  }
}
```

Executar por 10 minutos e validar:
- Não há erros de sincronização (race conditions)
- Filas crescem/diminuem conforme esperado
- APIs respondem adequadamente

### Teste de Integração

Validar comunicação com serviços:

```bash
# Deve mostrar chamadas bem-sucedidas
grep "Entrada registrada" upa_simulator.log | wc -l
grep "Triagem registrada" upa_simulator.log | wc -l
grep "Atendimento registrado" upa_simulator.log | wc -l

# Deve ser igual ao número de pacientes gerados
```

---

## Troubleshooting

### Problema: Erro ao buscar UPAs da API

**Sintoma**:
```
ERROR - Erro ao fazer GET de /api/v1/upas: Connection refused
WARNING - Falha ao buscar UPAs da API. Usando configuração local.
```

**Causas possíveis**:
1. Gateway Service não está rodando
2. URL incorreta no `config.json`
3. Firewall bloqueando conexão

**Soluções**:

```bash
# 1. Verificar se serviço está rodando
curl http://localhost:8084/actuator/health

# 2. Verificar porta correta
sudo netstat -tulpn | grep 8084

# 3. Testar endpoint de UPAs
curl -v http://localhost:8084/api/v1/upas

# 4. Verificar logs do Gateway Service
docker logs gateway-service  # se Docker
journalctl -u gateway-service -n 50  # se systemd
```

**Workaround**: O simulador continuará usando UUIDs mockados.

### Problema: Falha ao registrar eventos

**Sintoma**:
```
WARNING - Falha ao registrar entrada: paciente 3f2a8b9c
```

**Causas possíveis**:
1. Monitoring Service não está rodando
2. URL incorreta no `config.json`
3. Timeout de rede
4. Serviço rejeitando requisições (ex: validação falhou)

**Soluções**:

```bash
# 1. Verificar serviço
curl http://localhost:8086/actuator/health

# 2. Testar endpoint manualmente
curl -X POST http://localhost:8086/api/v1/events/entrada \
  -H "Content-Type: application/json" \
  -d '{
    "patientId": "test-123",
    "upaId": "upa-uuid",
    "bairro": "Centro",
    "timestamp": "2025-10-25T14:30:00"
  }'

# 3. Ver logs do Monitoring Service
docker logs monitoring-service
```

**Ajuste de timeout**:

Edite `upa_simulator.py`:
```python
self.monitoring_client = APIClient(
    self.config["monitoring_service"]["base_url"],
    timeout=30  # Aumentar de 10 para 30 segundos
)
```

### Problema: Muitos pacientes acumulados nas filas

**Sintoma**:
```
ESTATÍSTICAS - 14:35:22
Total de pacientes ativos: 150
```

**Causas**:
1. Taxa de entrada muito alta
2. Tempo de triagem/atendimento muito longo
3. `real_time_factor` muito baixo

**Soluções**:

```json
// Opção 1: Reduzir taxa de entrada
"patient_flow": {
  "mode": "per_hour",
  "rate": 8  // Reduzir de 12 para 8
}

// Opção 2: Acelerar simulação
"simulation": {
  "real_time_factor": 5.0  // Processar 5x mais rápido
}

// Opção 3: Reduzir tempos de processamento
"triagem_time_seconds": {
  "min": 60,  // Reduzir de 180
  "max": 300  // Reduzir de 600
}
```

### Problema: Poucos pacientes sendo gerados

**Sintoma**:
```
ESTATÍSTICAS - 14:35:22
Total de pacientes ativos: 2
```

**Verificações**:

```bash
# 1. Confirmar UPAs habilitadas
grep "enabled.*true" config.json

# 2. Ver intervalo calculado
grep "Entrada de pacientes" upa_simulator.log
```

**Soluções**:

```json
// Aumentar taxa de entrada
"patient_flow": {
  "mode": "per_hour",
  "rate": 30  // Aumentar de 12 para 30
}
```

### Problema: Race conditions / Erros de thread

**Sintoma**:
```
Exception in thread Thread-3:
  File "queue.py", line 171, in get
    Empty
```

**Causa**: Problema de sincronização (já corrigido no código atual)

**Solução**: Atualizar para versão mais recente do código que usa locks.

### Problema: Logs não estão sendo gerados

**Verificações**:

```bash
# 1. Verificar permissões do diretório
ls -la upa_simulator.log

# 2. Verificar configuração de logging
grep -A5 "logging" config.json

# 3. Verificar se diretório é gravável
touch test.log && rm test.log
```

**Soluções**:

```bash
# Dar permissões
chmod 664 upa_simulator.log
chown usuario:usuario upa_simulator.log

# Criar diretório se necessário
mkdir -p /var/log/upa-simulator
```

### Problema: Distribuição de classificações incorreta

**Verificação**:

```bash
# Contar triagens por classificação
for cor in VERMELHO AMARELO VERDE AZUL; do
  count=$(grep "triado:" upa_simulator.log | grep -c "$cor")
  total=$(grep "triado:" upa_simulator.log | wc -l)
  pct=$(echo "scale=2; $count * 100 / $total" | bc)
  echo "$cor: $count ($pct%)"
done
```

**Causa**: Configuração incorreta em `config.json`

**Solução**:

```json
// Verificar que soma = 1.0
"classificacao_distribution": {
  "VERMELHO": 0.05,
  "AMARELO": 0.25,
  "VERDE": 0.50,
  "AZUL": 0.20
}
// 0.05 + 0.25 + 0.50 + 0.20 = 1.00 ✓
```

---

## Referências

### Protocolo de Manchester

1. **Manchester Triage Group**. Emergency Triage. 3rd ed. Wiley-Blackwell, 2014.

2. **Mackway-Jones, K., Marsden, J., Windle, J.** (2014). Sistema Manchester de Classificação de Risco. Grupo Brasileiro de Classificação de Risco.

3. **Brasil. Ministério da Saúde**. HumanizaSUS: Acolhimento com avaliação e classificação de risco. Brasília: Ministério da Saúde, 2004.

### Implementações em UPAs Brasileiras

4. **Souza, C.C., et al.** (2011). Classificação de risco em pronto-socorro: concordância entre um protocolo institucional brasileiro e Manchester. Revista Latino-Americana de Enfermagem, 19(1).

5. **Acosta, A.M., et al.** (2012). Acolhimento com classificação de risco em Unidades de Pronto Atendimento. Revista Gaúcha de Enfermagem, 33(4).

### Documentação Técnica

6. **Python Software Foundation**. Python Documentation - Threading. https://docs.python.org/3/library/threading.html

7. **Python Software Foundation**. Python Documentation - Queue. https://docs.python.org/3/library/queue.html

8. **Requests Documentation**. HTTP for Humans. https://requests.readthedocs.io/

### Contato e Suporte

Para dúvidas técnicas ou sugestões de melhoria:
- Abrir issue no repositório GitHub
- Consultar documentação adicional em `/docs` (se disponível)

---

**Desenvolvido como parte do Trabalho de Conclusão de Curso**
**Validação do Protocolo de Manchester em Sistemas de Gestão de UPAs**
**Campina Grande - PB**
