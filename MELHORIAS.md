# Melhorias Implementadas - Simulador UPA

## Resumo das Mudanças

Refatoração completa do simulador com foco em:
1. **Código organizado** em módulos
2. **Demanda realista** com picos de horário
3. **Variabilidade** nos tempos de atendimento
4. **Formação de filas** para demonstração

---

## 1. Estrutura de Código Refatorada

### Antes
```
src/
└── upa_simulator.py (585 linhas - "god file")
```

### Agora
```
src/
├── upa_simulator.py          # Main (orquestração)
├── models/
│   ├── __init__.py
│   ├── patient.py            # Patient, PatientStatus
│   └── classification.py     # ClassificacaoTriagem
├── services/
│   ├── __init__.py
│   ├── api_client.py         # APIClient (HTTP com retry)
│   └── demand_calculator.py  # Curva de demanda por horário
└── utils/
    ├── __init__.py
    └── time_variability.py   # Eventos que causam atrasos
```

**Benefícios:**
- ✅ Código organizado e manutenível
- ✅ Fácil de testar módulos individualmente
- ✅ Separação de responsabilidades

---

## 2. Demanda Variável por Horário

### Implementação: `DemandCalculator`

**Multiplicadores por hora:**
- **Madrugada (0-6h):** 0.2-0.4x (baixíssima)
- **Manhã (7-10h):** 0.8-1.3x (crescente)
- **PICO MANHÃ (11-12h):** 1.8x
- **Tarde (13-16h):** 1.0-1.3x
- **PICO TARDE (17-19h):** 2.0-2.2x (MAIOR PICO)
- **Noite (20-23h):** 0.7-1.5x

### Taxas Base (AUMENTADAS para forçar filas)

**UPA Dinamérica:**
- Real: ~17 pac/hora (407/dia baseado em 12.203/mês)
- Simulador: **40 pac/hora** (2.3x)
- **Pico 18h:** até **88 pac/hora**

**UPA Alto Branco:**
- Real: ~12 pac/hora (estimado 70% da Dinamérica)
- Simulador: **30 pac/hora** (2.5x)
- **Pico 18h:** até **66 pac/hora**

**Objetivo:** Criar sobrecarga para formar filas e demonstrar sistema sob pressão

---

## 3. Variabilidade nos Tempos

### Implementação: `TimeVariabilityCalculator`

Simula eventos reais que causam atrasos:

| Evento | Probabilidade | Impacto | Aplicável a |
|--------|--------------|---------|-------------|
| **Pausa profissional** | 10% | +50% tempo | Todos |
| **Troca de turno** | 5% | +100% tempo | Todos |
| **Caso complexo** | 15% | +80% tempo | VERMELHO/AMARELO |
| **Aguarda equipamento** | 8% | +40% tempo | Todos |

**Exemplos:**
- Triagem normal: 2 min → Com pausa: 3 min
- Atendimento VERMELHO: 15 min → Caso complexo: 27 min
- Atendimento VERDE: 8 min → Troca de turno: 16 min

**Objetivo:** Simular realidade das UPAs (nem tudo é previsível)

---

## 4. Correções Críticas de Performance

### Problema Identificado
- ❌ **1 thread de triagem** para todas as UPAs
- ❌ **1 thread de atendimento** para todas as UPAs
- ❌ Paciente VERMELHO esperando 42+ minutos

### Solução Aplicada
- ✅ **Thread dedicada de triagem POR UPA**
- ✅ **Thread dedicada de atendimento POR UPA**
- ✅ **Processamento paralelo** - sem espera entre UPAs

### Arquitetura Agora

```
UPA Dinamérica:
  - Thread Entrada (demanda variável)
  - Thread Triagem (FIFO com variabilidade)
  - Thread Atendimento (priorizado com variabilidade)

UPA Alto Branco:
  - Thread Entrada (demanda variável)
  - Thread Triagem (FIFO com variabilidade)
  - Thread Atendimento (priorizado com variabilidade)

Monitor:
  - Thread Monitor (estatísticas a cada minuto)
```

**Total: 7 threads** (vs 5 antes)

---

## 5. Tempos Atualizados (Baseados em Estudos)

### Triagem
- **Min:** 60s (1 min)
- **Max:** 240s (4 min)
- **Mediana:** 2 min (SciELO)

### Atendimento (por classificação)
- **VERMELHO:** 30-60 min
- **AMARELO:** 40-80 min
- **VERDE:** 50-100 min
- **AZUL:** 60-120 min

**Com variabilidade aplicada, pode ser ainda maior!**

---

## 6. Configuração Atualizada

### `config.json`

```json
{
  "upas": {
    "UPA Dinamérica": {
      "patient_flow": {
        "mode": "per_hour",
        "rate": 40  // Aumentado de 20
      }
    },
    "UPA Alto Branco": {
      "patient_flow": {
        "mode": "per_hour",
        "rate": 30  // Aumentado de 18
      }
    }
  },
  "simulation": {
    "real_time_factor": 1.0,  // Tempo real
    "triagem_time_seconds": {
      "min": 60,   // Reduzido de 120
      "max": 240
    }
  }
}
```

---

## 7. Resultados Esperados

### Formação de Filas
- **Manhã (11-12h):** Filas moderadas (mult. 1.8x)
- **Tarde (17-19h):** **FILAS GRANDES** (mult. 2.0-2.2x)
- **Madrugada:** Sem filas (mult. 0.2-0.3x)

### Métricas para Análise
- Tempo médio de espera por classificação
- Tamanho das filas por horário
- Taxa de violação do protocolo Manchester
- Impacto de eventos (pausas, trocas)

### Gráficos Possíveis
1. **Demanda por hora** (curva sinusoidal com 2 picos)
2. **Tamanho das filas** ao longo do dia
3. **Tempo de espera** por classificação
4. **Violações do protocolo** Manchester
5. **Comparação UPA Dinamérica vs Alto Branco**

---

## 8. Como Testar

### No servidor:

```bash
cd ~/SCRIPT-UPA-SIMULATOR
git pull
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
docker logs -f upa-simulator
```

### Observar nos logs:

```
[UPA Dinamérica] Pico Tarde: 88 pac/h (intervalo: 41s)
[UPA Dinamérica] Entrada: Paciente abc12345 - Dinamérica (Fila triagem: 15)
[UPA Dinamérica] Triagem: Paciente abc12345 (180s - Pausa enfermeiro)
[UPA Dinamérica] Classificação: Paciente abc12345 -> AMARELO (P2)
[UPA Dinamérica] Atendimento: Paciente abc12345 [AMARELO] (2700s, aguardou 8.5min - Caso complexo)
ESTATÍSTICAS [18:30:00] - Total de pacientes ativos: 45
  [UPA Dinamérica] Triagem (FIFO): 18, Atendimento (PRIORIZADA): 12, Total: 30
  [UPA Alto Branco] Triagem (FIFO): 10, Atendimento (PRIORIZADA): 5, Total: 15
```

---

## 9. Benefícios para o TCC

✅ **Realismo:** Baseado em dados reais + estudos científicos
✅ **Demonstrável:** Filas se formam e podem ser analisadas
✅ **Código profissional:** Organizado, documentado, manutenível
✅ **Gráficos interessantes:** Variação ao longo do dia
✅ **Protocolo Manchester:** Corretamente implementado e validado
✅ **Casos de estresse:** Demonstra sistema sob pressão

---

## Referências

1. **Dados reais:** Prefeitura de Campina Grande - UPA Dinamérica 12.203 atendimentos/mês (junho)
2. **Tempos de triagem:** SciELO - mediana 2 minutos
3. **Protocolo Manchester:** COFEN 661/2021, GBCR
4. **Padrões de demanda:** Estimados para UPAs urbanas brasileiras
