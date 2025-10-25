# Simulador de Fluxo de Pacientes - Protocolo de Manchester

Sistema de simulação para validação do fluxo de pacientes em Unidades de Pronto Atendimento (UPAs) de Campina Grande - PB, com implementação do Protocolo de Manchester para gestão de filas por classificação de risco.

---

## Índice

- [Introdução](#introdução)
- [Protocolo de Manchester](#protocolo-de-manchester)
- [Arquitetura](#arquitetura)
- [Requisitos](#requisitos)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Execução](#execução)
- [Validação](#validação)
- [Referências](#referências)

---

## Introdução

Este simulador foi desenvolvido como ferramenta de validação para sistemas de gestão de UPAs, reproduzindo o fluxo completo de pacientes desde a entrada até a finalização do atendimento.

### Objetivos

1. Simular o fluxo contínuo de pacientes em ambiente de urgência e emergência
2. Validar a implementação do Protocolo de Manchester em sistemas de gestão
3. Gerar dados realistas para análise de desempenho
4. Fornecer ambiente de testes para sistemas de monitoramento

### Funcionalidades

- Simulação de entrada contínua de pacientes
- Implementação do Protocolo de Manchester (4 níveis de classificação)
- Gestão de filas: FIFO para triagem, priorizada para atendimento
- Integração via API REST com serviços de monitoramento
- Logs detalhados com rotação automática
- Execução contínua com tratamento de erros

---

## Protocolo de Manchester

O Protocolo de Manchester é um sistema de triagem e classificação de risco utilizado em serviços de urgência e emergência. O protocolo estabelece prioridades de atendimento baseadas na gravidade clínica do paciente.

### Classificações Implementadas (Campina Grande - PB)

| Classificação | Prioridade | Tempo Máximo | Descrição |
|--------------|------------|--------------|-----------|
| VERMELHO | 1 | 0 minutos | Emergência - Risco iminente de vida |
| AMARELO | 2 | 60 minutos | Muito urgente - Risco potencial de vida |
| VERDE | 3 | 120 minutos | Urgente - Necessita atendimento |
| AZUL | 4 | 240 minutos | Pouco urgente - Condições estáveis |

**Nota**: O sistema não implementa a classificação LARANJA, conforme especificação das UPAs de Campina Grande - PB.

### Fluxo nas UPAs Reais

#### 1. Recepção/Entrada
- Paciente fornece apenas dados pessoais (nome, CPF, endereço)
- **NÃO há classificação** nesta etapa
- Paciente aguarda triagem em **ordem de chegada (FIFO)**

#### 2. Triagem (Enfermeiro)
- Atendimento por **ordem de chegada (FIFO)**
- Avaliação de sinais vitais e sintomas
- **Classificação de Manchester é atribuída**
- Paciente vai para fila de atendimento priorizada

#### 3. Atendimento Médico
- Atendimento por **ordem de prioridade** (não por ordem de chegada)
- Paciente VERMELHO é atendido antes de AMARELO, VERDE e AZUL
- Independente da hora de chegada

**Exemplo**: Um paciente VERMELHO que chegou às 10:30 é atendido antes de um paciente AZUL que chegou às 10:00.

---

## Arquitetura

### Componentes Principais

```
┌─────────────────────────────────────────────────────────────┐
│                  UPA SIMULATOR (Python)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │   Entry      │    │   Triagem    │    │ Atendimento  │ │
│  │   Threads    │───▶│   Processor  │───▶│  Processor   │ │
│  │  (por UPA)   │    │   (FIFO)     │    │ (Priorizado) │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                   │                    │         │
│         ▼                   ▼                    ▼         │
│  ┌──────────────────────────────────────────────────┐     │
│  │           Filas (Thread-Safe)                    │     │
│  │  • Triagem: Queue (FIFO)                         │     │
│  │  • Atendimento: PriorityQueue (Priorizada)       │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │                            │
         ▼                            ▼
┌──────────────────┐        ┌──────────────────┐
│  Gateway Service │        │ Monitoring Service│
│   (porta 8084)   │        │   (porta 8086)    │
└──────────────────┘        └──────────────────┘
```

### Fluxo de Dados

```
1. Entrada (Recepção)
   └─> Paciente fornece dados pessoais (SEM classificação)
   └─> Registrado via API (POST /api/v1/events/entrada)
   └─> Adicionado à Queue de triagem (FIFO)

2. Triagem (Enfermeiro)
   └─> Paciente removido da fila FIFO (ordem de chegada)
   └─> Avaliação de sintomas (180-600 segundos)
   └─> CLASSIFICAÇÃO atribuída (VERMELHO/AMARELO/VERDE/AZUL)
   └─> Registrado via API (POST /api/v1/events/triagem)
   └─> Adicionado à PriorityQueue de atendimento

3. Atendimento (Médico)
   └─> Paciente removido por PRIORIDADE (VERMELHO primeiro)
   └─> Verificação de tempo de espera vs. limite
   └─> Atendimento médico (tempo varia por classificação)
   └─> Registrado via API (POST /api/v1/events/atendimento)
   └─> Finalizado
```

---

## Requisitos

### Software

- Python 3.8 ou superior
- Dependências:
  - `requests >= 2.31.0`
  - `urllib3 >= 2.0.0`
  - `typing-extensions >= 4.8.0`

### Infraestrutura

**Importante**: O simulador é um cliente que se conecta aos serviços já existentes. Você não precisa instalá-los.

Os serviços devem estar rodando e acessíveis:

- **Gateway Service** (porta 8084): Fornece lista de UPAs
- **Monitoring Service** (porta 8086): Recebe eventos de entrada, triagem e atendimento

---

## Instalação

### 1. Clonar o Repositório

```bash
git clone <url-do-repositorio>
cd SCRIPT-UPA-SIMULATOR
```

### 2. Criar Arquivo de Configuração

O arquivo `config.json` não está no repositório por segurança. Crie-o:

```bash
cp config.examples.json config.json
nano config.json
```

Ajuste as URLs dos serviços:
```json
{
  "monitoring_service": {
    "base_url": "http://SEU_IP:8086"
  },
  "gateway_service": {
    "base_url": "http://SEU_IP:8084"
  }
}
```

### 3. Criar Ambiente Virtual

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 4. Instalar Dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Configuração

### Parâmetros Principais

#### URLs dos Serviços
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

#### Fluxo de Pacientes
```json
{
  "upas": {
    "UPA Dinamérica": {
      "enabled": true,
      "patient_flow": {
        "mode": "per_hour",  // per_minute, per_hour, per_day
        "rate": 12           // 12 pacientes por hora
      }
    }
  }
}
```

**Modos disponíveis**:
- `per_minute`: Taxa por minuto
- `per_hour`: Taxa por hora (recomendado)
- `per_day`: Taxa por dia

#### Distribuição de Classificações
```json
{
  "classificacao_distribution": {
    "VERMELHO": 0.05,  // 5%
    "AMARELO": 0.25,   // 25%
    "VERDE": 0.50,     // 50%
    "AZUL": 0.20       // 20%
  }
  // Total deve ser 1.0 (100%)
}
```

#### Velocidade da Simulação
```json
{
  "simulation": {
    "real_time_factor": 1.0  // 1.0 = tempo real, 10.0 = 10x mais rápido
  }
}
```

---

## Execução

### Execução Manual

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Executar
python upa_simulator.py
```

**Saída esperada**:
```
INFO - Iniciando UPA Simulator - Protocolo de Manchester
INFO - Buscando UPAs da API...
INFO - Encontradas 2 UPA(s) na API
INFO - Simulador inicializado com 2 UPA(s)
INFO - Protocolo de Manchester: Classificação na triagem, atendimento priorizado
INFO - Simulação iniciada
```

**Para parar**: `Ctrl+C`

### Execução 24/7 (Servidor)

#### Opção 1: Screen (Simples)

```bash
# Criar sessão
screen -S upa-simulator

# Executar
cd SCRIPT-UPA-SIMULATOR
source venv/bin/activate
python upa_simulator.py

# Desanexar: Ctrl+A, depois D
# Reanexar: screen -r upa-simulator
```

#### Opção 2: systemd (Produção)

Criar `/etc/systemd/system/upa-simulator.service`:

```ini
[Unit]
Description=UPA Patient Flow Simulator
After=network-online.target

[Service]
Type=simple
User=seu_usuario
WorkingDirectory=/caminho/para/SCRIPT-UPA-SIMULATOR
Environment="PATH=/caminho/para/SCRIPT-UPA-SIMULATOR/venv/bin"
ExecStart=/caminho/para/SCRIPT-UPA-SIMULATOR/venv/bin/python upa_simulator.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Habilitar e iniciar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable upa-simulator
sudo systemctl start upa-simulator
sudo systemctl status upa-simulator
```

### Monitoramento

#### Ver logs em tempo real
```bash
tail -f upa_simulator.log
```

#### Ver estatísticas
```bash
grep "ESTATÍSTICAS" upa_simulator.log
```

#### Contar pacientes por classificação
```bash
grep "classificado como" upa_simulator.log | grep -o "VERMELHO\|AMARELO\|VERDE\|AZUL" | sort | uniq -c
```

---

## Validação

### 1. Entrada Sem Classificação

Verificar que pacientes entram sem classificação:

```bash
grep "entrou na recepção" upa_simulator.log | head -5
```

Saída esperada:
```
[UPA Dinamérica] Paciente abc12345 entrou na recepção (Bairro: Malvinas, Aguardando triagem: 1)
```

### 2. Triagem FIFO

Verificar que triagem respeita ordem de chegada:

```bash
grep "Iniciando triagem" upa_simulator.log | head -10
```

### 3. Classificação na Triagem

Verificar que classificação é atribuída na triagem:

```bash
grep "classificado como" upa_simulator.log | head -5
```

Saída esperada:
```
[UPA Dinamérica] Paciente abc12345 classificado como VERMELHO (prioridade 1)
[UPA Alto Branco] Paciente def67890 classificado como VERDE (prioridade 3)
```

### 4. Priorização no Atendimento

Verificar que atendimento respeita prioridades:

```bash
grep "Iniciando atendimento" upa_simulator.log | grep -o "\[VERMELHO\|\[AMARELO\|\[VERDE\|\[AZUL" | head -20
```

Deve mostrar VERMELHO sendo atendido primeiro.

### 5. Alertas de Tempo Excedido

```bash
grep "ALERTA PROTOCOLO MANCHESTER" upa_simulator.log
```

Exemplo:
```
ALERTA PROTOCOLO MANCHESTER: Paciente abc12345 (AMARELO) aguardou 65.3 min (máximo: 60 min)
```

### 6. Distribuição de Classificações

```bash
# Contar por classificação
for cor in VERMELHO AMARELO VERDE AZUL; do
  count=$(grep "classificado como $cor" upa_simulator.log | wc -l)
  echo "$cor: $count"
done
```

Comparar com a distribuição configurada.

---

## Troubleshooting

### Erro ao buscar UPAs da API

**Sintoma**:
```
ERROR - Erro ao fazer GET de /api/v1/upas
```

**Solução**:
```bash
# Verificar se serviço está rodando
curl http://SEU_IP:8084/actuator/health

# Verificar URL no config.json
cat config.json | grep base_url
```

### Falha ao registrar eventos

**Sintoma**:
```
WARNING - Falha ao registrar entrada
```

**Solução**:
```bash
# Verificar serviço de monitoramento
curl http://SEU_IP:8086/actuator/health

# Testar endpoint manualmente
curl -X POST http://SEU_IP:8086/api/v1/events/entrada \
  -H "Content-Type: application/json" \
  -d '{"patientId":"test","upaId":"uuid","bairro":"Centro","timestamp":"2025-10-25T22:00:00"}'
```

### Muitos pacientes acumulados

**Solução**: Reduzir taxa de entrada ou aumentar `real_time_factor`:

```json
{
  "patient_flow": {
    "rate": 8  // reduzir de 12
  },
  "simulation": {
    "real_time_factor": 5.0  // acelerar processamento
  }
}
```

---

## Referências

### Protocolo de Manchester

1. **Manchester Triage Group**. Emergency Triage. 3rd ed. Wiley-Blackwell, 2014.

2. **Mackway-Jones, K., Marsden, J., Windle, J.** Sistema Manchester de Classificação de Risco. Grupo Brasileiro de Classificação de Risco, 2014.

3. **Brasil. Ministério da Saúde**. HumanizaSUS: Acolhimento com avaliação e classificação de risco. Brasília, 2004.

### Implementações em UPAs Brasileiras

4. **Souza, C.C., et al.** Classificação de risco em pronto-socorro: concordância entre um protocolo institucional brasileiro e Manchester. Rev. Latino-Am. Enfermagem, 2011.

5. **Acosta, A.M., et al.** Acolhimento com classificação de risco em Unidades de Pronto Atendimento. Rev. Gaúcha Enferm., 2012.

### Documentação Técnica

6. **Python Software Foundation**. Python Threading Documentation. https://docs.python.org/3/library/threading.html

7. **Python Software Foundation**. Python Queue Documentation. https://docs.python.org/3/library/queue.html

8. **Requests Library**. HTTP for Humans. https://requests.readthedocs.io/

---

**Desenvolvido como parte do Trabalho de Conclusão de Curso**
**Validação do Protocolo de Manchester em Sistemas de Gestão de UPAs**
**Campina Grande - PB**
