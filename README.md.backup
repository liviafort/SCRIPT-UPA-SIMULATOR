# Simulador de Fluxo de Pacientes - Protocolo de Manchester

Sistema de simulação para validação do fluxo de pacientes em Unidades de Pronto Atendimento (UPAs) de Campina Grande - PB, implementando o Protocolo de Manchester para gestão de filas por classificação de risco.

---

## Índice

- [Sobre o Projeto](#sobre-o-projeto)
- [Protocolo de Manchester](#protocolo-de-manchester)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Requisitos](#requisitos)
- [Instalação e Execução](#instalação-e-execução)
- [Configuração](#configuração)
- [Validação](#validação)
- [Referências](#referências)

---

## Sobre o Projeto

Este simulador reproduz o fluxo completo de pacientes em UPAs, desde a entrada até a finalização do atendimento, servindo como ferramenta de validação para sistemas de gestão hospitalar.

### Objetivos

1. Simular fluxo contínuo de pacientes em ambiente de urgência e emergência
2. Validar implementação do Protocolo de Manchester em sistemas de gestão
3. Gerar dados realistas para análise de desempenho
4. Fornecer ambiente de testes para sistemas de monitoramento

### Funcionalidades

- Simulação de entrada contínua de pacientes
- Protocolo de Manchester com 4 níveis de classificação (sem LARANJA)
- Gestão de filas: FIFO para triagem, priorizada para atendimento médico
- Integração via API REST com serviços de monitoramento
- Logs otimizados com rotação automática
- Multi-threading para processamento paralelo
- Execução 24/7 via Docker

---

## Protocolo de Manchester

Sistema de triagem e classificação de risco utilizado em serviços de urgência e emergência, estabelecendo prioridades baseadas na gravidade clínica.

### Classificações (Campina Grande - PB)

| Classificação | Prioridade | Tempo Máximo | Descrição |
|--------------|------------|--------------|-----------|
| VERMELHO | 1 | 0 minutos | Emergência - Risco iminente de vida |
| AMARELO | 2 | 60 minutos | Muito urgente - Risco potencial de vida |
| VERDE | 3 | 120 minutos | Urgente - Necessita atendimento |
| AZUL | 4 | 240 minutos | Pouco urgente - Condições estáveis |

**Nota**: Sistema não implementa classificação LARANJA, conforme especificação das UPAs de Campina Grande - PB.

### Fluxo de Atendimento

#### 1. Recepção/Entrada
- Paciente fornece dados pessoais (nome, CPF, endereço)
- **SEM classificação** nesta etapa
- Aguarda triagem em **ordem de chegada (FIFO)**

#### 2. Triagem (Enfermagem)
- Atendimento por **ordem de chegada (FIFO)**
- Duração: **1-4 minutos** (mediana 2 minutos - baseado em estudo SciELO)
- Avaliação de sinais vitais e sintomas
- **Classificação de Manchester atribuída**
- Paciente direcionado para fila de atendimento médico

#### 3. Atendimento Médico
- Atendimento por **ordem de prioridade** (não por chegada)
- VERMELHO atendido antes de AMARELO, VERDE e AZUL
- Independente da hora de chegada

**Exemplo**: Paciente VERMELHO às 10:30 é atendido antes de paciente AZUL às 10:00.

---

## Estrutura do Projeto

```
SCRIPT-UPA-SIMULATOR/
├── config/
│   ├── config.json              # Configuração de produção (não versionado)
│   └── config.example.json      # Exemplo de configuração
├── docker/
│   ├── Dockerfile               # Definição da imagem Docker
│   └── docker-compose.yml       # Orquestração do container
├── scripts/
│   ├── install_simulator.sh     # Instalação manual (legacy)
│   └── run_simulator.sh         # Execução manual (legacy)
├── src/
│   ├── upa_simulator.py         # Código principal do simulador
│   └── requirements.txt         # Dependências Python
├── .dockerignore                # Arquivos ignorados no build
├── .gitignore                   # Arquivos não versionados
└── README.md                    # Este arquivo
```

---

## Requisitos

### Para execução com Docker (Recomendado)
- Docker 20.10+
- Docker Compose 1.29+
- 512MB RAM disponível
- 1 CPU core

### Para execução manual
- Python 3.11+
- pip
- 512MB RAM disponível

---

## Instalação e Execução

### Método 1: Docker (Recomendado para Produção)

#### 1. Clonar o repositório
```bash
git clone <repositorio-url> upa-simulator
cd upa-simulator
```

#### 2. Configurar arquivo de configuração
```bash
# Copiar exemplo e editar com suas URLs de produção
cp config/config.example.json config/config.json
nano config/config.json
```

Alterar as URLs:
```json
{
  "monitoring_service": {
    "base_url": "https://sua-url-monitoring.com"
  },
  "gateway_service": {
    "base_url": "https://sua-url-gateway.com"
  }
}
```

#### 3. Iniciar com Docker Compose
```bash
cd docker
docker-compose up -d
```

#### 4. Verificar status
```bash
# Ver logs em tempo real
docker-compose logs -f

# Ver status do container
docker-compose ps

# Ver últimas 100 linhas
docker-compose logs --tail=100
```

#### 5. Parar o simulador
```bash
docker-compose down
```

#### 6. Atualizar código
```bash
git pull
docker-compose down
docker-compose build
docker-compose up -d
```

### Método 2: Execução Manual (Desenvolvimento)

#### 1. Instalar dependências
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

pip install -r src/requirements.txt
```

#### 2. Configurar
```bash
cp config/config.example.json config/config.json
# Editar config/config.json com suas configurações
```

#### 3. Executar
```bash
python src/upa_simulator.py
```

---

## Configuração

### Arquivo: `config/config.json`

#### Serviços
```json
{
  "monitoring_service": {
    "base_url": "https://api.example.com/monitoring",
    "endpoints": {
      "entrada": "/api/v1/events/entrada",
      "triagem": "/api/v1/events/triagem",
      "atendimento": "/api/v1/events/atendimento"
    }
  },
  "gateway_service": {
    "base_url": "https://api.example.com/gateway",
    "endpoints": {
      "upas": "/api/v1/upas"
    }
  }
}
```

#### UPAs e Fluxo de Pacientes
```json
{
  "upas": {
    "UPA Dinamérica": {
      "enabled": true,
      "patient_flow": {
        "mode": "per_hour",    // per_minute, per_hour, per_day
        "rate": 20             // 20 pacientes por hora
      },
      "bairros": ["Dinamérica", "Malvinas", ...],
      "classificacao_distribution": {
        "VERMELHO": 0.05,      // 5% dos pacientes
        "AMARELO": 0.25,       // 25%
        "VERDE": 0.50,         // 50%
        "AZUL": 0.20           // 20%
      }
    }
  }
}
```

#### Tempos de Atendimento (baseados em estudos científicos)
```json
{
  "simulation": {
    "real_time_factor": 1.0,           // 1.0 = tempo real
    "triagem_time_seconds": {
      "min": 60,                       // 1 minuto
      "max": 240                       // 4 minutos
    },
    "atendimento_time_seconds": {
      "VERMELHO": {"min": 900, "max": 2400},   // 15-40 min
      "AMARELO": {"min": 600, "max": 1800},    // 10-30 min
      "VERDE": {"min": 300, "max": 900},       // 5-15 min
      "AZUL": {"min": 180, "max": 600}         // 3-10 min
    }
  }
}
```

#### Logs
```json
{
  "logging": {
    "level": "INFO",
    "file": "upa_simulator.log",
    "max_bytes": 5242880,      // 5MB por arquivo
    "backup_count": 2          // 2 backups (total: 15MB)
  }
}
```

### Gerenciamento de Logs (Docker)

O Docker está configurado para **limitar automaticamente** o tamanho dos logs:

- **Logs do Docker**: Máximo 10MB por arquivo, 3 arquivos (30MB total)
- **Logs da aplicação**: Máximo 5MB por arquivo, 2 backups (15MB total)
- **Total estimado**: ~45MB de espaço em disco

Limpar logs manualmente:
```bash
# Logs do Docker
docker-compose down
sudo truncate -s 0 /var/lib/docker/containers/*/*-json.log
docker-compose up -d

# Logs da aplicação
rm -f logs/*.log*
```

---

## Validação

### 1. Verificar logs do simulador
```bash
# Docker
docker-compose logs -f

# Manual
tail -f upa_simulator.log
```

### 2. Logs esperados

```
Iniciando UPA Simulator - Protocolo de Manchester
Simulador inicializado com 2 UPA(s)
[UPA Dinamérica] Entrada: Paciente abc12345 - Dinamérica (Fila triagem: 0)
[UPA Dinamérica] Triagem: Paciente abc12345 (180s)
[UPA Dinamérica] Classificação: Paciente abc12345 -> AMARELO (P2)
[UPA Dinamérica] Atendimento: Paciente abc12345 [AMARELO] (900s, aguardou 3.2min)
[UPA Dinamérica] Finalizado: Paciente abc12345 [AMARELO] (total: 18.5min)
ESTATÍSTICAS [14:30:00] - Total de pacientes ativos: 12
  [UPA Dinamérica] Triagem (FIFO): 3, Atendimento (PRIORIZADA): 6, Total: 9
  [UPA Alto Branco] Triagem (FIFO): 1, Atendimento (PRIORIZADA): 2, Total: 3
```

### 3. Verificar dados no sistema de monitoramento

Acessar o sistema de monitoramento configurado em `monitoring_service.base_url` e verificar se os eventos estão sendo recebidos:
- Eventos de entrada
- Eventos de triagem
- Eventos de atendimento

### 4. Monitorar recursos do container
```bash
docker stats upa-simulator
```

---

## Referências

### Estudos Científicos

1. **Sistema Manchester: tempo empregado na classificação de risco**
   - SciELO - Revista Gaúcha de Enfermagem
   - Tempo mediano de triagem: 2 minutos (IQR: 1-3 minutos)
   - https://www.scielo.br/j/rgenf/a/ZPt8CVtgXpftkT7MszL8KtP/

2. **Resolução COFEN 661/2021**
   - Tempo médio de triagem: 4 minutos
   - Limite: 15 classificações por hora por enfermeiro

### Protocolo de Manchester

1. **Grupo Brasileiro de Classificação de Risco**
   - http://www.gbcr.org.br/

2. **Manchester Triage System**
   - https://www.triagenet.net/

---

## Tecnologias

- **Python 3.11**: Linguagem principal
- **Docker**: Containerização
- **Threading**: Processamento paralelo
- **Requests**: Cliente HTTP
- **JSON**: Configuração e comunicação

---

## Licença

Este projeto foi desenvolvido para fins acadêmicos como parte do Trabalho de Conclusão de Curso (TCC).

---

## Contato

Para dúvidas ou sugestões sobre o projeto, entre em contato através do repositório.
