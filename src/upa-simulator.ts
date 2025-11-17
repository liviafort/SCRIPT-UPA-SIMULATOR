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

export class UPASimulator {
  private config: Config;
  private simulationParams: SimulationParams;
  private monitoringClient: APIClient;
  private gatewayClient: APIClient;
  private upas: Map<string, UPAConfig> = new Map();
  private poissonGenerators: Map<string, PoissonGenerator> = new Map();
  private atendimentoQueues: Map<string, PriorityQueue> = new Map();
  private running: boolean = false;

  private readonly CLASSIFICATION_DISTRIBUTION: Record<ClassificacaoManchester, number>;
  private readonly TRIAGEM_TIME_SECONDS: number;
  private readonly ATENDIMENTO_TIME_SECONDS: number;
  private readonly MIN_WAIT_BEFORE_TRIAGEM_SECONDS: number;
  private readonly NUMERO_MEDICOS: number;

  constructor(config: Config, simulationParams: SimulationParams) {
    this.config = config;
    this.simulationParams = simulationParams;
    this.monitoringClient = new APIClient(config.monitoring_service.base_url, config.auth);
    this.gatewayClient = new APIClient(config.gateway_service.base_url);

    this.CLASSIFICATION_DISTRIBUTION = config.simulation.classification_distribution;
    this.TRIAGEM_TIME_SECONDS = config.simulation.triagem_time_minutes * 60;
    this.ATENDIMENTO_TIME_SECONDS = config.simulation.atendimento_time_minutes * 60;
    this.MIN_WAIT_BEFORE_TRIAGEM_SECONDS = config.simulation.min_wait_before_triagem_minutes * 60;
    this.NUMERO_MEDICOS = config.simulation.numero_medicos;
  }

  async initialize(): Promise<void> {
    console.log('Iniciando UPA Simulator - Versão Simplificada');
    console.log('Protocolo de Manchester | Processo de Poisson\n');

    await this.fetchUPAs();

    for (const [upaName, upaConfig] of this.upas) {
      let paramKey: 'Dinamerica' | 'Alto_Branco';

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

        const generator = new PoissonGenerator(params);
        this.poissonGenerators.set(upaName, generator);

        this.atendimentoQueues.set(upaName, new PriorityQueue());

        const rateInfo = generator.getRateInfo();
        console.log(`  -> Dia: ${rateInfo.dayOfWeek} | Hora ${rateInfo.hour}h`);
        console.log(`  -> Lambda ajustado: ${rateInfo.lambda.toFixed(2)} pac/h (fator: ${rateInfo.adjustmentFactor.toFixed(2)})`);
      }
    }

    console.log(`\nSimulador inicializado com ${this.upas.size} UPA(s)`);
    console.log(`Número de médicos por UPA: ${this.NUMERO_MEDICOS}`);
    console.log(`Tempo espera mínima: ${this.MIN_WAIT_BEFORE_TRIAGEM_SECONDS / 60} min`);
    console.log(`Tempo triagem: ${this.TRIAGEM_TIME_SECONDS / 60} min`);
    console.log(`Tempo atendimento: ${this.ATENDIMENTO_TIME_SECONDS / 60} min`);

    const dist = this.CLASSIFICATION_DISTRIBUTION;
    console.log(`Distribuição Manchester: VERMELHO=${(dist.VERMELHO * 100).toFixed(0)}%, LARANJA=${(dist.LARANJA * 100).toFixed(0)}%, AMARELO=${(dist.AMARELO * 100).toFixed(0)}%, VERDE=${(dist.VERDE * 100).toFixed(0)}%, AZUL=${(dist.AZUL * 100).toFixed(0)}%\n`);
  }

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

      this.upas.set(upaName, {
        name: upaName,
        id: upa.id,
        bairros: configUpa.bairros,
        classificationDistribution: this.CLASSIFICATION_DISTRIBUTION
      });
    }
  }

  start(): void {
    this.running = true;
    console.log('Simulação iniciada! (Ctrl+C para parar)\n');

    for (const [upaName, upaConfig] of this.upas) {
      this.runUPALoop(upaName, upaConfig);

      for (let i = 0; i < this.NUMERO_MEDICOS; i++) {
        this.runAtendimentoProcessor(upaName, i + 1);
      }
    }
  }

  stop(): void {
    this.running = false;
    console.log('\nSimulação parada');
  }

  private async runUPALoop(upaName: string, upaConfig: UPAConfig): Promise<void> {
    const generator = this.poissonGenerators.get(upaName);

    if (!generator) {
      console.error(`Gerador Poisson não encontrado para ${upaName}`);
      return;
    }

    while (this.running) {
      try {
        const intervalSeconds = generator.getNextInterval();

        await this.sleep(intervalSeconds * 1000);

        const patient = this.createPatient(upaConfig);
        this.processPatient(patient);

      } catch (error) {
        console.error(`Erro no loop da ${upaName}:`, error);
        await this.sleep(5000);
      }
    }
  }

  private getBrazilTimestamp(): string {
    const now = new Date();
    const brazilDate = new Date(now.toLocaleString('en-US', { timeZone: 'America/Sao_Paulo' }));

    const year = brazilDate.getFullYear();
    const month = String(brazilDate.getMonth() + 1).padStart(2, '0');
    const day = String(brazilDate.getDate()).padStart(2, '0');
    const hours = String(brazilDate.getHours()).padStart(2, '0');
    const minutes = String(brazilDate.getMinutes()).padStart(2, '0');
    const seconds = String(brazilDate.getSeconds()).padStart(2, '0');

    return `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
  }

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

  private async processPatient(patient: Patient): Promise<void> {
    try {
      await this.registerEntrada(patient);
      console.log(`[${patient.upaName}] Entrada: ${patient.patientId.substring(0, 8)} - ${patient.bairro}`);

      await this.sleep(this.MIN_WAIT_BEFORE_TRIAGEM_SECONDS * 1000);

      patient.triagemTimestamp = this.getBrazilTimestamp();
      await this.registerTriagem(patient);
      console.log(`[${patient.upaName}] Triagem: ${patient.patientId.substring(0, 8)} -> ${patient.classificacao}`);

      await this.sleep(this.TRIAGEM_TIME_SECONDS * 1000);

      const queue = this.atendimentoQueues.get(patient.upaName);
      if (queue) {
        queue.enqueue(patient);
        const stats = queue.getStats();
        console.log(`[${patient.upaName}] ${patient.patientId.substring(0, 8)} entrou na fila de atendimento [${patient.classificacao}] - Fila: V:${stats.VERMELHO} L:${stats.LARANJA} A:${stats.AMARELO} VE:${stats.VERDE} AZ:${stats.AZUL}`);
      }
    } catch (error) {
      console.error(`[${patient.upaName}] Erro processando paciente ${patient.patientId.substring(0, 8)}:`, error);
    }
  }

  private async runAtendimentoProcessor(upaName: string, medicoId: number): Promise<void> {
    const queue = this.atendimentoQueues.get(upaName);

    if (!queue) {
      console.error(`Fila de atendimento não encontrada para ${upaName}`);
      return;
    }

    while (this.running) {
      try {
        if (!queue.isEmpty()) {
          const patient = queue.dequeue();

          if (patient) {
            patient.atendimentoTimestamp = this.getBrazilTimestamp();
            await this.registerAtendimento(patient);
            console.log(`[${patient.upaName}] Médico ${medicoId} - Atendimento: ${patient.patientId.substring(0, 8)} [${patient.classificacao}]`);

            await this.sleep(this.ATENDIMENTO_TIME_SECONDS * 1000);

            console.log(`[${patient.upaName}] Médico ${medicoId} - Finalizado: ${patient.patientId.substring(0, 8)}\n`);
          }
        } else {
          await this.sleep(1000);
        }
      } catch (error) {
        console.error(`[${upaName}] Médico ${medicoId} - Erro no processador de atendimentos:`, error);
        await this.sleep(5000);
      }
    }
  }

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

  private randomChoice<T>(array: T[]): T {
    return array[Math.floor(Math.random() * array.length)];
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
