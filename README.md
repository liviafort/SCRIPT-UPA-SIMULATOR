# UPA Simulator

Simulador de Unidades de Pronto Atendimento (UPAs) baseado em dados reais e processo de Poisson não-homogêneo.

## Descrição

Este projeto implementa um simulador realista de fluxo de pacientes em UPAs, desenvolvido em TypeScript. O simulador utiliza análise estatística de dados históricos para reproduzir padrões de chegada de pacientes ao longo do dia, respeitando o Protocolo de Manchester para classificação de risco.

## Arquitetura do Projeto

### Análise de Dados

O diretório `analise-dados/` contém:

- **notebook.ipynb**: Jupyter notebook com análise exploratória dos dados históricos das UPAs
- **dados-dinamerica/** e **dados-alto-branco/**: Dados CSV com histórico de atendimentos
  - `atendimento-hora-*.csv`: Distribuição de atendimentos por hora
  - `atendimento-dia-*.csv`: Distribuição de atendimentos por dia
  - `classificacao-dia-*.csv`: Distribuição de classificações de Manchester
- **parametros_simulacao_upas.json**: Parâmetros estatísticos extraídos da análise

#### Análise Estatística

O notebook realiza:
- Análise de distribuição de chegadas por hora do dia
- Cálculo de taxas λ (lambda) para cada hora usando processo de Poisson
- Análise de variação por dia da semana
- Validação estatística dos padrões identificados
- Geração de parâmetros para o simulador

Os parâmetros calculados incluem:
- Lambda médio por hora (taxa de chegada de pacientes)
- Lambda específico para cada hora do dia (0-23h)
- Distribuições de classificação de Manchester
- Estatísticas por dia da semana

### Processo de Poisson Não-Homogêneo

O simulador utiliza um **Processo de Poisson Não-Homogêneo** para gerar chegadas de pacientes, onde a taxa λ varia ao longo do dia:

- **Taxa variável**: Cada hora possui um λ diferente, refletindo padrões reais de demanda
- **Distribuição exponencial**: Intervalos entre chegadas seguem distribuição exponencial com parâmetro λ(t)
- **Baseado em dados reais**: Os valores de λ foram extraídos de dados históricos das UPAs

Exemplo de variação de λ (UPA Dinamérica):
- Madrugada (3h-4h): λ ≈ 2.9 pacientes/hora
- Pico manhã (8h-9h): λ ≈ 24.3 pacientes/hora
- Noite (23h): λ ≈ 8.1 pacientes/hora

### Código do Simulador

Estrutura do código TypeScript em `src-ts/`:

#### `poisson-generator.ts`
Implementa o gerador de chegadas usando processo de Poisson:
- Seleciona λ apropriado baseado na hora atual
- Gera intervalos entre chegadas usando transformação inversa: `-ln(U) / λ`
- Converte taxa de pacientes/hora para pacientes/segundo

#### `priority-queue.ts`
Fila de prioridade para pacientes seguindo Protocolo de Manchester:
- Ordem: VERMELHO > AMARELO > VERDE > AZUL
- Desempate por FIFO (First In, First Out) dentro da mesma prioridade
- Estatísticas em tempo real da fila

#### `upa-simulator.ts`
Simulador principal que coordena:
- **Geração de chegadas**: Processo de Poisson não-homogêneo por UPA
- **Fluxo de atendimento**:
  1. Entrada do paciente (registro imediato)
  2. Espera mínima pré-triagem
  3. Triagem com atribuição de classificação Manchester
  4. Fila de atendimento com priorização
  5. Atendimento médico
- **Protocolo de Manchester**: Distribuição probabilística de classificações
- **Múltiplas UPAs**: Execução paralela de processos independentes

#### `api-client.ts`
Cliente HTTP com autenticação JWT:
- Login automático e renovação de token
- Gerenciamento de expiração
- Retry em caso de falha de autenticação

#### `types.ts`
Definições de tipos TypeScript para todo o projeto

#### `index.ts`
Ponto de entrada que carrega configurações e inicia o simulador

## Protocolo de Manchester

O simulador atribui classificações de risco seguindo distribuições configuráveis:

- **VERMELHO**: Emergência (padrão: 10%)
- **AMARELO**: Muito urgente (padrão: 34%)
- **VERDE**: Urgente (padrão: 50%)
- **AZUL**: Pouco urgente (padrão: 6%)

Pacientes são atendidos respeitando esta ordem de prioridade, com desempate por ordem de chegada.

## Configuração

### Arquivo de Configuração

Copie o arquivo de exemplo:

```bash
cp config/config.example.json config/config.json
```

Configure os seguintes parâmetros em `config/config.json`:

#### Autenticação (obrigatório)
```json
{
  "auth": {
    "username": "seu_usuario",
    "password": "sua_senha",
    "base_url": "https://sua-api.com",
    "endpoints": {
      "login": "/api/v1/auth/login",
      "refresh": "/api/v1/auth/refresh"
    }
  }
}
```

#### Serviços de API
```json
{
  "monitoring_service": {
    "base_url": "https://sua-api.com/monitoring",
    "endpoints": {
      "entrada": "/api/v1/events/entrada",
      "triagem": "/api/v1/events/triagem",
      "atendimento": "/api/v1/events/atendimento"
    }
  },
  "gateway_service": {
    "base_url": "https://sua-api.com/gateway",
    "endpoints": {
      "upas": "/api/v1/upas"
    }
  }
}
```

#### UPAs Habilitadas
```json
{
  "upas": {
    "UPA Dinamérica": {
      "enabled": true,
      "bairros": ["Alto Branco", "Conceição", ...]
    },
    "UPA Alto Branco": {
      "enabled": true,
      "bairros": ["Liberdade", "São José", ...]
    }
  }
}
```

#### Parâmetros de Simulação
```json
{
  "simulation": {
    "triagem_time_minutes": 2,
    "atendimento_time_minutes": 5,
    "min_wait_before_triagem_minutes": 1,
    "classification_distribution": {
      "VERDE": 0.50,
      "AMARELO": 0.34,
      "VERMELHO": 0.10,
      "AZUL": 0.06
    }
  }
}
```

**Nota**: O arquivo `config/config.json` não é versionado no git por questões de segurança.

## Instalação

```bash
# Instalar dependências
npm install

# Compilar TypeScript
npm run build
```

## Execução

```bash
# Desenvolvimento (ts-node)
npm run dev

# Produção (código compilado)
npm start

# Watch mode (recompila automaticamente)
npm run watch
```

## Saída do Simulador

O simulador exibe logs em tempo real:

```
Iniciando UPA Simulator - Versão Simplificada
Protocolo de Manchester | Processo de Poisson

[DEBUG] Configurando UPA Dinamérica:
  -> Lambda médio: 14.74 pac/h
  -> Lambda atual (hora 9h): 24.32 pac/h

[UPA Dinamérica] Entrada: a1b2c3d4 - Alto Branco
[UPA Dinamérica] Triagem: a1b2c3d4 -> AMARELO
[UPA Dinamérica] a1b2c3d4 entrou na fila de atendimento [AMARELO] - Fila: V:0 A:1 VE:2 AZ:0
[UPA Dinamérica] Atendimento: a1b2c3d4 [AMARELO]
[UPA Dinamérica] Finalizado: a1b2c3d4
```

## Características do Simulador

### Realismo
- Taxas de chegada baseadas em dados históricos reais
- Variação ao longo do dia e semana
- Distribuição de classificações de Manchester realista
- Tempos de espera e atendimento configuráveis

### Escalabilidade
- Múltiplas UPAs em paralelo
- Processos assíncronos independentes
- Sem bloqueio entre chegadas e atendimentos

### Monitoramento
- Logs detalhados de cada etapa
- Estatísticas em tempo real da fila
- Informações sobre taxa de chegada atual

## Tecnologias

- **TypeScript**: Linguagem principal
- **Node.js**: Runtime
- **Axios**: Cliente HTTP
- **Python**: Análise de dados (Jupyter notebook)
- **Processo de Poisson**: Modelagem matemática de chegadas

## Estrutura de Diretórios

```
.
├── analise-dados/           # Análise estatística e dados
│   ├── notebook.ipynb
│   ├── dados-dinamerica/
│   ├── dados-alto-branco/
│   └── parametros_simulacao_upas.json
├── config/                  # Configurações
│   ├── config.example.json
│   └── config.json (não versionado)
├── src-ts/                  # Código TypeScript
│   ├── index.ts
│   ├── poisson-generator.ts
│   ├── upa-simulator.ts
│   ├── priority-queue.ts
│   ├── api-client.ts
│   └── types.ts
├── dist/                    # Código compilado
└── package.json
```