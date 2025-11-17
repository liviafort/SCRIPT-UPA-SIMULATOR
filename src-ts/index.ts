import { readFileSync } from 'fs';
import { join } from 'path';
import { UPASimulator } from './upa-simulator';
import { Config, SimulationParams } from './types';

async function main() {
  try {
    const configPath = join(__dirname, '..', 'config', 'config.json');
    const paramsPath = join(__dirname, '..', 'analise-dados', 'parametros_simulacao_upas.json');

    const config: Config = JSON.parse(readFileSync(configPath, 'utf-8'));
    const simulationParams: SimulationParams = JSON.parse(readFileSync(paramsPath, 'utf-8'));

    const simulator = new UPASimulator(config, simulationParams);
    await simulator.initialize();

    simulator.start();

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
