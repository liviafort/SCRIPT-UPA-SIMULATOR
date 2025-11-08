# Simulador de Fluxo de Pacientes em UPAs - Processo Poisson Não-Homogêneo

Sistema de simulação estocástica para modelagem de fluxo de pacientes em Unidades de Pronto Atendimento (UPAs) de Campina Grande - PB, baseado em Teoria das Filas e Processo de Poisson Não-Homogêneo, implementando o Protocolo de Manchester (4 níveis) para gestão de prioridades.

---

## Índice

1. [Fundamentação Teórica](#fundamentação-teórica)
2. [Implementação do Processo de Poisson](#implementação-do-processo-de-poisson)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Protocolo de Manchester](#protocolo-de-manchester)
5. [Dados Empíricos](#dados-empíricos)
6. [Instalação e Configuração](#instalação-e-configuração)
7. [Execução](#execução)
8. [Validação](#validação)
9. [Referências](#referências)

---

## Fundamentação Teórica

### 1.1. Teoria das Filas

O sistema de atendimento em UPAs é modelado como um sistema de filas **M/M/c**:

- **M** (Markoviano): Chegadas seguem processo de Poisson
- **M** (Markoviano): Tempos de serviço seguem distribuição exponencial
- **c**: Número de servidores (enfermeiros para triagem e médicos para atendimento)

### 1.2. Processo de Poisson Não-Homogêneo

A chegada de pacientes é modelada como um **Processo de Poisson Não-Homogêneo (NHPP)**, onde a taxa de chegadas λ(t) varia em função da hora do dia. Esta abordagem captura a variabilidade temporal real do fluxo de pacientes em UPAs.

**Definição Matemática:**

```
N(t) ~ Poisson(Λ(t))
```

Onde:
- `N(t)`: Número de chegadas até o tempo t
- `Λ(t) = ∫[0,t] λ(s)ds`: Função de intensidade acumulada
- `λ(t)`: Taxa instantânea de chegadas no tempo t (pacientes/hora)

**Propriedades:**
- Para intervalos pequenos Δt, a probabilidade de uma chegada é aproximadamente λ(t)·Δt
- O número de chegadas em intervalos disjuntos são variáveis aleatórias independentes
- A taxa λ(t) é estimada a partir de dados históricos reais

### 1.3. Distribuição Exponencial dos Intervalos

Dado λ(t) constante em um intervalo horário, os **intervalos entre chegadas** seguem distribuição exponencial:

```
T ~ Exp(λ(t))
P(T > t) = e^(-λ·t)
E[T] = 1/λ
Var(T) = 1/λ²
```

**Propriedade Memoryless:** A distribuição exponencial não possui memória, ou seja, P(T > s+t | T > s) = P(T > t).

### 1.4. Disciplinas de Filas

O sistema implementa duas disciplinas distintas:

1. **Triagem**: FIFO (First-In-First-Out)
   - Ordem de chegada preservada
   - Sem priorização
   - Tempo de atendimento: 20-60 segundos

2. **Atendimento Médico**: Fila de Prioridade com Manchester
   - Ordenação por classificação de risco
   - **VERMELHO (P1) > AMARELO (P2) > VERDE (P3) > AZUL (P4)**
   - Dentro da mesma prioridade: FIFO
   - Tempo de atendimento varia por classificação

**Nota:** Campina Grande utiliza **4 níveis de classificação** (não inclui LARANJA).

---

## Implementação do Processo de Poisson

### 2.1. Biblioteca Python: NumPy

O simulador utiliza a biblioteca **NumPy** para geração de variáveis aleatórias da distribuição exponencial:

```python
import numpy as np

# Geração de intervalo entre chegadas
intervalo_segundos = np.random.exponential(scale=media_intervalo)
```

**Função `numpy.random.exponential(scale)`:**
- `scale`: Parâmetro de escala (média da distribuição) = 1/λ
- Retorna: Amostra da distribuição Exp(1/scale)

### 2.2. Arquitetura da Implementação

#### Classe: `PoissonArrivalGenerator`

Localização: [`src/poisson_arrival_generator.py`](src/poisson_arrival_generator.py)

**Responsabilidades:**
1. Carregar taxas horárias λ(h) de dados reais
2. Determinar taxa atual baseada na hora do sistema
3. Gerar intervalos exponenciais entre chegadas

**Método Principal:**

```python
def get_next_interval_seconds(self, current_time: Optional[datetime] = None) -> float:
    """
    Gera próximo intervalo até chegada do paciente.

    Processo:
    1. Obtém λ(t) para hora atual
    2. Calcula média do intervalo: μ = 3600/λ (segundos)
    3. Gera amostra: T ~ Exp(μ)

    Returns:
        float: Intervalo em segundos até próxima chegada
    """
    lambda_rate = self.get_current_rate(current_time)  # pacientes/hora

    if lambda_rate <= 0:
        return 3600.0  # Fallback: 1 hora

    # Intervalo médio em segundos
    mean_interval_seconds = 3600.0 / lambda_rate

    # Gera variável aleatória exponencial
    interval = np.random.exponential(mean_interval_seconds)

    return interval
```

**Exemplo Numérico:**

Para λ(9h) = 24.3 pacientes/hora (UPA Dinamérica, horário de pico):

```
μ = 3600 / 24.3 ≈ 148 segundos ≈ 2.5 minutos

Intervalo gerado: T ~ Exp(148)
- Valor esperado: E[T] = 148s
- Desvio padrão: σ(T) = 148s
- Probabilidade de T ≤ 5min: P(T ≤ 300) = 1 - e^(-300/148) ≈ 88%
```

### 2.3. Estimação de Parâmetros a partir de Dados Reais

#### Classe: `UPADataAnalyzer`

Localização: [`src/data_analyzer.py`](src/data_analyzer.py)

**Processo de Estimação:**

```python
def calculate_poisson_rates(self) -> Dict[int, float]:
    """
    Calcula λ(h) para cada hora usando dados históricos.

    Fórmula:
        λ(h) = μ_diário × p(h)

    Onde:
        - μ_diário: Média de pacientes por dia (estimador: média amostral)
        - p(h): Proporção de chegadas na hora h (estimador: frequência relativa)

    Returns:
        Dict[hora] -> λ(hora) em pacientes/hora
    """
    media_diaria, _, _ = self.analyze_daily_arrivals()
    hourly_pct = self.analyze_hourly_distribution()

    lambda_rates = {}
    for hour in range(24):
        pct = hourly_pct.get(hour, 1.0/24)
        lambda_rates[hour] = media_diaria * pct  # λ(h) = μ × p(h)

    return lambda_rates
```

**Dados de Entrada:**
- `atendimento-dia-*.csv`: Série temporal de atendimentos diários
- `atendimento-hora-*.csv`: Distribuição percentual por hora do dia

**Saída:** `simulation_params.json` contendo λ(h) para h ∈ {0, 1, ..., 23}

### 2.4. Fluxo de Simulação

```
1. Inicialização
   └─ PoissonArrivalGenerator carrega λ(h) do simulation_params.json

2. Loop de Entrada de Pacientes (_entry_loop)
   │
   ├─ Obtém hora atual: t_now
   │
   ├─ Busca taxa: λ(t_now)
   │
   ├─ Gera intervalo: T ~ Exp(3600/λ)
   │
   ├─ Aguarda T segundos: time.sleep(T)
   │
   ├─ Cria paciente com bairro aleatório
   │
   ├─ Adiciona à fila de triagem
   │
   └─ Repete
```

**Implementação em [`src/upa_simulator.py`](src/upa_simulator.py):**

```python
def _entry_loop(self, upa_name: str):
    """
    Loop de entrada de pacientes usando Processo Poisson Não-Homogêneo.
    """
    poisson_gen = self.poisson_generators[upa_name]

    while self.running:
        # Gera intervalo usando processo Poisson
        interval = poisson_gen.get_next_interval_seconds()

        # Aplica intervalo mínimo (configurável)
        if self.config["simulation"]["min_entry_interval_seconds"] > 0:
            interval = max(interval, self.config["simulation"]["min_entry_interval_seconds"])

        # Cria e registra paciente
        patient = self._create_patient(upa_config)

        with self.fila_triagem_locks[upa_name]:
            self.fila_triagem[upa_name].put(patient)

        self._register_entrada(patient)

        # Aguarda próxima chegada
        time.sleep(interval)
```

---

## Arquitetura do Sistema

### 3.1. Componentes Principais

```
upa_simulator.py (Simulador Principal)
    │
    ├─ PoissonArrivalGenerator (Geração de chegadas)
    │   └─ numpy.random.exponential()
    │
    ├─ Queue (Fila de triagem - FIFO)
    │
    ├─ PriorityQueue (Fila de atendimento - Priorizada)
    │
    ├─ APIClient (Comunicação com APIs externas)
    │   ├─ GET /api/v1/upas
    │   ├─ POST /api/v1/events/entrada
    │   ├─ POST /api/v1/events/triagem
    │   └─ POST /api/v1/events/atendimento
    │
    └─ TimeVariabilityCalculator (Variabilidade humana)
```

### 3.2. Threads de Simulação

Para cada UPA, o simulador cria 3 threads independentes:

1. **Entry Thread**: Gera chegadas usando Processo Poisson
2. **Triagem Thread**: Processa fila de triagem (FIFO)
3. **Atendimento Thread**: Processa fila de atendimento (Priorizada)

**Thread Adicional:**
- **Monitor Thread**: Coleta estatísticas a cada 60 segundos

---

## Protocolo de Manchester

### 4.1. Classificação de Risco (Campina Grande - 4 níveis)

| Classificação | Prioridade | Tempo Máximo de Espera | Descrição |
|---------------|------------|------------------------|-----------|
| VERMELHO      | 1          | Imediato (0 min)       | Emergência - risco de vida |
| AMARELO       | 2          | 60 minutos             | Muito urgente |
| VERDE         | 3          | 120 minutos            | Urgente |
| AZUL          | 4          | 240 minutos            | Pouco urgente |

### 4.2. Implementação

Localização: [`src/models/classification.py`](src/models/classification.py)

```python
class ClassificacaoTriagem(Enum):
    """Protocolo de Manchester - Campina Grande (4 níveis)"""
    VERMELHO = (1, 0, "Emergência - Atendimento imediato")
    AMARELO = (2, 60, "Muito urgente - Até 60 minutos")
    VERDE = (3, 120, "Urgente - Até 120 minutos")
    AZUL = (4, 240, "Pouco urgente - Até 240 minutos")

    def __lt__(self, other):
        """Comparação por prioridade para PriorityQueue"""
        return self.prioridade < other.prioridade
```

### 4.3. Distribuição de Classificações

Baseada em dados reais de 396 dias (01/01/2025 a 31/10/2025):

```json
{
  "VERDE": 0.50,     // 50% dos pacientes
  "AMARELO": 0.34,   // 34% dos pacientes
  "VERMELHO": 0.10,  // 10% dos pacientes
  "AZUL": 0.06       // 6% dos pacientes
}
```

---

## Dados Empíricos

### 5.1. UPA Alto Branco

**Estatísticas Descritivas:**
- Média diária: μ = 249.52 pacientes/dia
- Desvio padrão: σ = 59.40 pacientes/dia
- Período analisado: 396 dias
- Horário de pico: 9h (λ = 20.7 pacientes/hora)

**Taxas Horárias Selecionadas (λ(h)):**

| Hora | λ (pac/h) | Intervalo Médio |
|------|-----------|-----------------|
| 3h   | 1.15      | 52.2 min        |
| 9h   | 20.72     | 2.9 min (PICO)  |
| 14h  | 18.97     | 3.2 min         |
| 21h  | 7.31      | 8.2 min         |

### 5.2. UPA Dinamérica

**Estatísticas Descritivas:**
- Média diária: μ = 353.73 pacientes/dia
- Desvio padrão: σ = 63.19 pacientes/dia
- Período analisado: 396 dias
- Horário de pico: 9h (λ = 24.3 pacientes/hora)

**Taxas Horárias Selecionadas (λ(h)):**

| Hora | λ (pac/h) | Intervalo Médio |
|------|-----------|-----------------|
| 3h   | 2.87      | 20.9 min        |
| 9h   | 24.30     | 2.5 min (PICO)  |
| 14h  | 20.77     | 2.9 min         |
| 21h  | 14.50     | 4.1 min         |

### 5.3. Análise dos Dados

**Comando para regenerar parâmetros:**

```bash
python src/data_analyzer.py
```

**Saída:** Arquivo `simulation_params.json` contendo:
- `hourly_arrival_rates`: λ(h) para h ∈ {0, ..., 23}
- `classification_distribution`: Distribuição de classificações
- `service_times_minutes`: Tempos de atendimento por classificação
- `summary`: Estatísticas descritivas

---

## Instalação e Configuração

### 6.1. Requisitos

- Python 3.11+
- NumPy (geração de variáveis aleatórias exponenciais)
- Requests (comunicação com APIs)

```bash
pip install -r requirements.txt
```

### 6.2. Estrutura de Configuração

**Arquivo:** `config/config.json`

```json
{
  "monitoring_service": {
    "base_url": "https://api.vejamaisaude.com/upa-monitoring"
  },
  "gateway_service": {
    "base_url": "https://api.vejamaisaude.com/upa"
  },
  "upas": {
    "UPA Dinamérica": {
      "enabled": true,
      "bairros": ["Alto Branco", "Conceição", ...]
    },
    "UPA Alto Branco": {
      "enabled": true,
      "bairros": ["Alto Branco", "Prata", ...]
    }
  },
  "simulation": {
    "real_time_factor": 0.5,
    "min_entry_interval_seconds": 60
  }
}
```

**Arquivo:** `simulation_params.json` (gerado automaticamente)

```json
{
  "Alto Branco": {
    "hourly_arrival_rates": {
      "0": 2.52, "1": 1.77, ..., "23": 3.77
    },
    "classification_distribution": {
      "VERDE": 0.50, "AMARELO": 0.34,
      "VERMELHO": 0.10, "AZUL": 0.06
    },
    "summary": {
      "avg_daily_arrivals": 249.52,
      "peak_hour": 9,
      "peak_rate": 20.72
    }
  }
}
```

---

## Execução

### 7.1. Execução Local

```bash
python src/upa_simulator.py
```

**Saída esperada:**

```
2025-11-08 09:00:00 - INFO - Iniciando UPA Simulator - Protocolo de Manchester
2025-11-08 09:00:00 - INFO - Buscando UPAs da API...
2025-11-08 09:00:01 - INFO - Encontradas 2 UPA(s) na API
2025-11-08 09:00:01 - INFO - Dados carregados: 'UPA Alto Branco' -> 'Alto Branco'
2025-11-08 09:00:01 - INFO - UPA configurada: UPA Alto Branco
2025-11-08 09:00:01 - INFO -   Distribuição: VERMELHO=10%, AMARELO=34%, VERDE=50%, AZUL=6%
2025-11-08 09:00:01 - INFO - MODO: Processo Poisson com taxas baseadas em dados reais
2025-11-08 09:00:01 - INFO -   - UPA Alto Branco: 20.7 pacientes/hora (hora 9h - PICO)
2025-11-08 09:00:01 - INFO - Simulação iniciada com 7 threads
```

### 7.2. Execução via Docker

```bash
cd docker
docker-compose up -d --build
```

**Visualizar logs:**

```bash
docker-compose logs -f upa-simulator
```

**Parar simulação:**

```bash
docker-compose down
```

---

## Validação

### 8.1. Validação Estatística do Processo Poisson

Para validar que a implementação realmente segue um Processo de Poisson, podemos verificar:

**1. Teste de Intervalo Exponencial:**

```python
# Coletar N intervalos
intervalos = [poisson_gen.get_next_interval_seconds() for _ in range(1000)]

# Teste Kolmogorov-Smirnov
from scipy import stats
lambda_rate = 20.7  # para hora 9h
mean_expected = 3600 / lambda_rate
ks_stat, p_value = stats.kstest(intervalos, 'expon', args=(0, mean_expected))

# H0: Dados seguem Exp(mean_expected)
# Rejeitar H0 se p_value < 0.05
```

**2. Propriedade Memoryless:**

Para distribuição exponencial, P(T > s+t | T > s) = P(T > t).

**3. Contagem de Eventos:**

O número de chegadas em um intervalo [0, t] deve seguir Poisson(λ·t).

### 8.2. Logs de Monitoramento

O simulador registra:
- Taxa λ(t) atual
- Intervalos gerados
- Fila de triagem (tamanho)
- Fila de atendimento (tamanho, prioridades)
- Violações do Protocolo de Manchester

---

## Referências

### Teoria de Filas e Processos Estocásticos

1. **Ross, S. M.** (2014). *Introduction to Probability Models* (11th ed.). Academic Press.
   - Capítulo 5: The Exponential Distribution and the Poisson Process
   - Capítulo 8: Queueing Theory

2. **Kleinrock, L.** (1975). *Queueing Systems, Volume I: Theory*. Wiley-Interscience.
   - Capítulo 2: Exponential Queueing Systems

3. **Tijms, H. C.** (2003). *A First Course in Stochastic Models*. Wiley.
   - Capítulo 1: The Poisson Process and Related Processes

### Aplicações em Saúde

4. **Green, L. V., & Nguyen, V.** (2001). Strategies for cutting hospital beds: The impact on patient service. *Health Services Research*, 36(2), 421-442.

5. **Cochran, J. K., & Bharti, A.** (2006). Stochastic bed balancing of an obstetrics hospital. *Health Care Management Science*, 9(1), 31-45.

### Protocolo de Manchester

6. **Mackway-Jones, K., Marsden, J., & Windle, J.** (2014). *Emergency Triage: Manchester Triage Group* (3rd ed.). BMJ Books.

### Documentação Técnica

7. **NumPy Documentation** - Random Sampling (numpy.random):
   - https://numpy.org/doc/stable/reference/random/generated/numpy.random.exponential.html

8. **Python Threading Documentation**:
   - https://docs.python.org/3/library/threading.html

---

## Estrutura do Projeto

```
SCRIPT-UPA-SIMULATOR/
├── src/
│   ├── upa_simulator.py              # Simulador principal (threading)
│   ├── upa_poisson_simulator.py      # Simulador SimPy (acadêmico)
│   ├── poisson_arrival_generator.py  # Gerador Poisson (CORE)
│   ├── data_analyzer.py              # Análise de dados reais
│   ├── models/
│   │   ├── classification.py         # Protocolo Manchester
│   │   └── patient.py                # Modelo de paciente
│   ├── services/
│   │   └── api_client.py             # Cliente HTTP
│   └── utils/
│       └── time_variability.py       # Variabilidade humana
├── config/
│   └── config.json                   # Configuração do sistema
├── dados-alto-branco/                # Dados reais UPA Alto Branco
│   ├── atendimento-dia-*.csv
│   ├── atendimento-hora-*.csv
│   └── classificacao-dia-*.csv
├── dados-dinamerica/                 # Dados reais UPA Dinamérica
│   ├── atendimento-dia-*.csv
│   ├── atendimento-hora-*.csv
│   └── classificacao-dia-*.csv
├── simulation_params.json            # Parâmetros extraídos (λ(h))
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Autores e Contribuições

Desenvolvido para modelagem e análise de fluxo de pacientes em UPAs de Campina Grande - PB.

**Tecnologias:**
- Python 3.11+
- NumPy (variáveis aleatórias exponenciais)
- Threading (concorrência)
- Docker (containerização)

**Licença:** MIT
