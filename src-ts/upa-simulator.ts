import { randomUUID } from 'crypto';
import { PoissonGenerator } from './poisson-generator';
import { APIClient } from './api-client';
import { PriorityQueue } from './priority-queue';
import {
  ClassificacaoManchester,
  Patient,
  UPAConfig,
  Config,
  SimulationParams
} from './types';

/**
 * Simulador simplificado de UPA
 * - Chegadas seguem processo de Poisson (baseado em dados reais)
 * - Atendimento fixo de 2 minutos
 * - Protocolo de Manchester
 */
export class UPASimulator {
  private config: Config;
  private simulationParams: SimulationParams;
  private monitoringClient: APIClient;
  private gatewayClient: APIClient;
  private upas: Map<string, UPAConfig> = new Map();
  private poissonGenerators: Map<string, PoissonGenerator> = new Map();
  private atendimentoQueues: Map<string, PriorityQueue> = new Map();
  private running: boolean = false;

  // Configurações carregadas do config.json
  private readonly CLASSIFICATION_DISTRIBUTION: Record<ClassificacaoManchester, number>;
  private readonly TRIAGEM_TIME_SECONDS: number;
  private readonly ATENDIMENTO_TIME_SECONDS: number;
  private readonly MIN_WAIT_BEFORE_TRIAGEM_SECONDS: number;

  constructor(config: Config, simulationParams: SimulationParams) {
    this.config = config;
    this.simulationParams = simulationParams;
    this.monitoringClient = new APIClient(config.monitoring_service.base_url, config.auth);
    this.gatewayClient = new APIClient(config.gateway_service.base_url);

    // Carrega configurações da simulação
    this.CLASSIFICATION_DISTRIBUTION = config.simulation.classification_distribution;
    this.TRIAGEM_TIME_SECONDS = config.simulation.triagem_time_minutes * 60;
    this.ATENDIMENTO_TIME_SECONDS = config.simulation.atendimento_time_minutes * 60;
    this.MIN_WAIT_BEFORE_TRIAGEM_SECONDS = config.simulation.min_wait_before_triagem_minutes * 60;
  }

  /**
   * Inicializa o simulador: busca UPAs da API e configura geradores Poisson
   */
  async initialize(): Promise<void> {
    console.log('Iniciando UPA Simulator - Versão Simplificada');
    console.log('Protocolo de Manchester | Processo de Poisson\n');

    await this.fetchUPAs();

    // Configura geradores Poisson e filas de prioridade para cada UPA
    for (const [upaName, upaConfig] of this.upas) {
      // Determina qual chave usar baseado no nome da UPA
      let paramKey: 'Dinamerica' | 'Alto_Branco';

      // Remove acentos e normaliza para comparação
      const normalizedName = upaName
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '');

      if (normalizedName.includes('dinamerica') || normalizedName.includes('dinamérica')) {
        paramKey = 'Dinamerica';
      } else if (normalizedName.includes('alto') && normalizedName.includes('branco')) {
        paramKey = 'Alto_Branco';
      } else {
        console.warn(`[AVISO] UPA "${upaName}" não reconhecida. Usando Alto_Branco como padrão.`);
        paramKey = 'Alto_Branco';
      }

      const params = this.simulationParams[paramKey];

      if (params) {
        console.log(`\n[DEBUG] Configurando ${upaName}:`);
        console.log(`  -> Mapeado para: ${paramKey}`);
        console.log(`  -> Lambda médio: ${params.lambda_hora_media.toFixed(2)} pac/h`);
        console.log(`  -> Total horas no array: ${params.lambda_por_hora.length}`);

        const generator = new PoissonGenerator(params.lambda_por_hora);
        this.poissonGenerators.set(upaName, generator);

        // Cria fila de prioridade para atendimentos
        this.atendimentoQueues.set(upaName, new PriorityQueue());

        const rateInfo = generator.getRateInfo();
        console.log(`  -> Lambda atual (hora ${rateInfo.hour}h): ${rateInfo.lambda.toFixed(2)} pac/h`);
      }
    }

    console.log(`\nSimulador inicializado com ${this.upas.size} UPA(s)`);
    console.log(`Tempo espera mínima: ${this.MIN_WAIT_BEFORE_TRIAGEM_SECONDS / 60} min`);
    console.log(`Tempo triagem: ${this.TRIAGEM_TIME_SECONDS / 60} min`);
    console.log(`Tempo atendimento: ${this.ATENDIMENTO_TIME_SECONDS / 60} min`);

    const dist = this.CLASSIFICATION_DISTRIBUTION;
    console.log(`Distribuição Manchester: VERDE=${(dist.VERDE * 100).toFixed(0)}%, AMARELO=${(dist.AMARELO * 100).toFixed(0)}%, VERMELHO=${(dist.VERMELHO * 100).toFixed(0)}%, AZUL=${(dist.AZUL * 100).toFixed(0)}%\n`);
  }

  /**
   * Busca UPAs da API
   */
  private async fetchUPAs(): Promise<void> {
    const response = await this.gatewayClient.get<{ data: any[] }>(
      this.config.gateway_service.endpoints.upas
    );

    if (!response || !response.data) {
      console.error('Falha ao buscar UPAs da API');
      return;
    }

    for (const upa of response.data) {
      const upaName = upa.name;
      const configUpa = this.config.upas[upaName];

      if (!configUpa || !configUpa.enabled) {
        continue;
      }

      // Usa a mesma distribuição para todas as UPAs
      this.upas.set(upaName, {
        name: upaName,
        id: upa.id,
        bairros: configUpa.bairros,
        classificationDistribution: this.CLASSIFICATION_DISTRIBUTION
      });
    }
  }

  /**
   * Inicia a simulação
   */
  start(): void {
    this.running = true;
    console.log('Simulação iniciada! (Ctrl+C para parar)\n');

    // Inicia loop de chegadas e processador de atendimentos para cada UPA
    for (const [upaName, upaConfig] of this.upas) {
      this.runUPALoop(upaName, upaConfig);
      this.runAtendimentoProcessor(upaName);
    }
  }

  /**
   * Para a simulação
   */
  stop(): void {
    this.running = false;
    console.log('\nSimulação parada');
  }

  /**
   * Loop principal de uma UPA
   */
  private async runUPALoop(upaName: string, upaConfig: UPAConfig): Promise<void> {
    const generator = this.poissonGenerators.get(upaName);

    if (!generator) {
      console.error(`Gerador Poisson não encontrado para ${upaName}`);
      return;
    }

    while (this.running) {
      try {
        // Gera intervalo usando processo Poisson
        const intervalSeconds = generator.getNextInterval();

        // Aguarda o intervalo
        await this.sleep(intervalSeconds * 1000);

        // Cria e processa paciente (NÃO-BLOQUEANTE - não aguarda finalização)
        const patient = this.createPatient(upaConfig);
        this.processPatient(patient); // Executa em paralelo sem await

      } catch (error) {
        console.error(`Erro no loop da ${upaName}:`, error);
        await this.sleep(5000);
      }
    }
  }

  /**
   * Obtém timestamp no timezone de São Paulo no formato esperado pela API
   * Formato: 2025-10-29T10:00:00 (sem millisegundos, sem timezone)
   */
  private getBrazilTimestamp(): string {
    const now = new Date();
    // Converte para o timezone de São Paulo (UTC-3)
    const brazilDate = new Date(now.toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }));

    // Formata no padrão esperado pela API
    const year = brazilDate.getFullYear();
    const month = String(brazilDate.getMonth() + 1).padStart(2, '0');
    const day = String(brazilDate.getDate()).padStart(2, '0');
    const hours = String(brazilDate.getHours()).padStart(2, '0');
    const minutes = String(brazilDate.getMinutes()).padStart(2, '0');
    const seconds = String(brazilDate.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
  }

  /**
   * Cria um novo paciente
   */
  private createPatient(upaConfig: UPAConfig): Patient {
    const bairro = this.randomChoice(upaConfig.bairros);
    const classificacao = this.assignClassification(upaConfig.classificationDistribution);

    return {
      patientId: randomUUID(),
      upaId: upaConfig.id,
      upaName: upaConfig.name,
      bairro,
      classificacao,
      entradaTimestamp: this.getBrazilTimestamp()
    };
  }

  /**
   * Processa entrada e triagem do paciente, depois adiciona à fila de atendimento
   */
  private async processPatient(patient: Patient): Promise<void> {
    try {
      // 1. ENTRADA (registra imediatamente)
      await this.registerEntrada(patient);
      console.log(`[${patient.upaName}] Entrada: ${patient.patientId.substring(0, 8)} - ${patient.bairro}`);

      // Espera mínima antes da triagem
      await this.sleep(this.MIN_WAIT_BEFORE_TRIAGEM_SECONDS * 1000);

      // 2. TRIAGEM (registra APÓS a espera, quando realmente acontece)
      patient.triagemTimestamp = this.getBrazilTimestamp();
      await this.registerTriagem(patient);
      console.log(`[${patient.upaName}] Triagem: ${patient.patientId.substring(0, 8)} -> ${patient.classificacao}`);

      // Tempo de triagem
      await this.sleep(this.TRIAGEM_TIME_SECONDS * 1000);

      // 3. ADICIONA À FILA DE ATENDIMENTO (respeitando prioridade)
      const queue = this.atendimentoQueues.get(patient.upaName);
      if (queue) {
        queue.enqueue(patient);
        const stats = queue.getStats();
        console.log(`[${patient.upaName}] ${patient.patientId.substring(0, 8)} entrou na fila de atendimento [${patient.classificacao}] - Fila: V:${stats.VERMELHO} A:${stats.AMARELO} VE:${stats.VERDE} AZ:${stats.AZUL}`);
      }
    } catch (error) {
      console.error(`[${patient.upaName}] Erro processando paciente ${patient.patientId.substring(0, 8)}:`, error);
    }
  }

  /**
   * Processador contínuo da fila de atendimento (respeita prioridade)
   */
  private async runAtendimentoProcessor(upaName: string): Promise<void> {
    const queue = this.atendimentoQueues.get(upaName);

    if (!queue) {
      console.error(`Fila de atendimento não encontrada para ${upaName}`);
      return;
    }

    while (this.running) {
      try {
        // Verifica se há pacientes na fila
        if (!queue.isEmpty()) {
          // Remove paciente com maior prioridade
          const patient = queue.dequeue();

          if (patient) {
            // Registra atendimento
            patient.atendimentoTimestamp = this.getBrazilTimestamp();
            await this.registerAtendimento(patient);
            console.log(`[${patient.upaName}] Atendimento: ${patient.patientId.substring(0, 8)} [${patient.classificacao}]`);

            // Tempo de atendimento
            await this.sleep(this.ATENDIMENTO_TIME_SECONDS * 1000);

            console.log(`[${patient.upaName}] Finalizado: ${patient.patientId.substring(0, 8)}\n`);
          }
        } else {
          // Fila vazia, aguarda um pouco antes de verificar novamente
          await this.sleep(1000);
        }
      } catch (error) {
        console.error(`[${upaName}] Erro no processador de atendimentos:`, error);
        await this.sleep(5000);
      }
    }
  }

  /**
   * Registra entrada na API
   */
  private async registerEntrada(patient: Patient): Promise<void> {
    const data = {
      patientId: patient.patientId,
      upaId: patient.upaId,
      bairro: patient.bairro,
      timestamp: patient.entradaTimestamp
    };

    await this.monitoringClient.post(
      this.config.monitoring_service.endpoints.entrada,
      data
    );
  }

  /**
   * Registra triagem na API
   */
  private async registerTriagem(patient: Patient): Promise<void> {
    const data = {
      patientId: patient.patientId,
      upaId: patient.upaId,
      classificacao: patient.classificacao,
      timestamp: patient.triagemTimestamp
    };

    await this.monitoringClient.post(
      this.config.monitoring_service.endpoints.triagem,
      data
    );
  }

  /**
   * Registra atendimento na API
   */
  private async registerAtendimento(patient: Patient): Promise<void> {
    const data = {
      patientId: patient.patientId,
      upaId: patient.upaId,
      timestamp: patient.atendimentoTimestamp
    };

    await this.monitoringClient.post(
      this.config.monitoring_service.endpoints.atendimento,
      data
    );
  }

  /**
   * Atribui classificação de Manchester baseada em distribuição probabilística
   */
  private assignClassification(distribution: Record<ClassificacaoManchester, number>): ClassificacaoManchester {
    const rand = Math.random();
    let cumulative = 0;

    for (const [classificacao, probability] of Object.entries(distribution)) {
      cumulative += probability;
      if (rand <= cumulative) {
        return classificacao as ClassificacaoManchester;
      }
    }

    return 'VERDE';
  }

  /**
   * Escolhe elemento aleatório de um array
   */
  private randomChoice<T>(array: T[]): T {
    return array[Math.floor(Math.random() * array.length)];
  }

  /**
   * Helper para sleep
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
