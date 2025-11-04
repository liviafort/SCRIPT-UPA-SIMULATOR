# Simulador de Fluxo de Pacientes em UPAs - Processo Poisson Não-Homogêneo

Sistema de simulação estocástica para modelagem de fluxo de pacientes em Unidades de Pronto Atendimento (UPAs) de Campina Grande - PB, baseado em Teoria das Filas e Processo de Poisson, implementando o Protocolo de Manchester para gestão de prioridades.

---

## Índice

1. [Fundamentação Teórica](#fundamentação-teórica)
2. [Modelagem Matemática](#modelagem-matemática)
3. [Arquitetura do Sistema](#arquitetura-do-sistema)
4. [Protocolo de Manchester](#protocolo-de-manchester)
5. [Dados Empíricos](#dados-empíricos)
6. [Instalação e Configuração](#instalação-e-configuração)
7. [Execução](#execução)
8. [Validação e Verificação](#validação-e-verificação)
9. [Referências Científicas](#referências-científicas)

---

## Fundamentação Teórica

### 1.1. Teoria das Filas

O sistema de atendimento em UPAs é modelado como um sistema de filas M/M/c:

- **M** (Markoviano): Chegadas seguem processo de Poisson
- **M** (Markoviano): Tempos de serviço seguem distribuição exponencial  
- **c**: Número de servidores (enfermeiros e médicos)

### 1.2. Processo de Poisson Não-Homogêneo

A chegada de pacientes é modelada como um processo de Poisson não-homogêneo, onde a taxa de chegadas lambda(t) varia em função da hora do dia:

```
N(t) ~ Poisson(Lambda(t))
```

Onde:
- `N(t)`: Número de chegadas até o tempo t
- `Lambda(t) = integral(lambda(s)ds, 0, t)`: Função de intensidade acumulada
- `lambda(t)`: Taxa instantânea de chegadas no tempo t (pacientes/hora)

### 1.3. Distribuição Exponencial dos Intervalos

Dado lambda(t) constante em um intervalo horário, os intervalos entre chegadas seguem distribuição exponencial:

```
T ~ Exp(lambda(t))
P(T > t) = e^(-lambda * t)
E[T] = 1/lambda
```

Implementação computacional:
```python
intervalo_segundos = np.random.exponential(3600.0 / lambda_t)
```

Onde:
- `3600/lambda_t`: Intervalo médio em segundos
- `lambda_t`: Taxa de chegadas na hora atual (pacientes/hora)

### 1.4. Disciplina de Filas

O sistema implementa duas disciplinas distintas:

1. **Triagem**: FIFO (First-In-First-Out)
   - Ordem de chegada preservada
   - Sem priorização

2. **Atendimento Médico**: Fila de Prioridade
   - Ordenação por classificação de risco (Manchester)
   - VERMELHO > LARANJA > AMARELO > VERDE > AZUL
   - Dentro da mesma prioridade: FIFO

---

## Modelagem Matemática

### 2.1. Parâmetros do Sistema

Para cada UPA, temos:

**Taxa de Chegadas Horária:**
```
lambda(h) = mu_daily * p(h)
```

Onde:
- `mu_daily`: Média diária de pacientes (estimada empiricamente)
- `p(h)`: Proporção de chegadas na hora h (soma = 1)
- `h in {0, 1, ..., 23}`: Hora do dia

**Dados Reais (UPA Alto Branco):**
- mu_daily = 249.52 pacientes/dia
- Desvio padrão = 59.40 pacientes/dia
- Período analisado: 396 dias (01/01/2025 a 31/10/2025)

**Dados Reais (UPA Dinamérica):**
- mu_daily = 353.73 pacientes/dia
- Desvio padrão = 63.19 pacientes/dia
- Período analisado: 396 dias (01/01/2025 a 31/10/2025)

