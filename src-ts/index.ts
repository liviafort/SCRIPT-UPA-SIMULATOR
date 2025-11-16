import { readFileSync } from 'fs';
import { join } from 'path';
import { UPASimulator } from './upa-simulator';
import { Config, SimulationParams } from './types';

/**
 * Ponto de entrada do simulador
 */
async function main() {
  try {
    // Carrega configurações
    const configPath = join(__dirname, '..', 'config', 'config.json');
    const paramsPath = join(__dirname, '..', 'analise-dados', 'parametros_simulacao_upas.json');

    const config: Config = JSON.parse(readFileSync(configPath, 'utf-8'));
    const simulationParams: SimulationParams = JSON.parse(readFileSync(paramsPath, 'utf-8'));

    // Cria e inicializa simulador
    const simulator = new UPASimulator(config, simulationParams);
    await simulator.initialize();

    // Inicia simulação
    simulator.start();

    // Trata Ctrl+C
    process.on('SIGINT', () => {
      simulator.stop();
      process.exit(0);
    });

  } catch (error) {
    console.error('Erro fatal:', error);
    process.exit(1);
  }
}

main();
