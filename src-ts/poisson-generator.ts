import { LambdaPorHora } from './types';

/**
 * Gerador de chegadas usando Processo de Poisson Não-Homogêneo
 * Taxa λ varia por hora do dia
 */
export class PoissonGenerator {
  private lambdasPorHora: LambdaPorHora[];

  constructor(lambdasPorHora: LambdaPorHora[]) {
    this.lambdasPorHora = lambdasPorHora;
  }

  /**
   * Obtém o lambda (taxa) para a hora atual
   */
  private getCurrentLambda(): number {
    const hour = new Date().getHours();
    const hourData = this.lambdasPorHora.find(h => h.Hora === hour);
    return hourData ? hourData.Lambda : this.lambdasPorHora[0].Lambda;
  }

  //Gera o próximo intervalo de tempo (em segundos) até a próxima chegada
  //Usa distribuição exponencial: -ln(U) / λ
  getNextInterval(): number {
    const lambda = this.getCurrentLambda();
    // Lambda está em pacientes/hora, convertemos para pacientes/segundo
    const lambdaPerSecond = lambda / 3600;

    // Gera número aleatório uniformemente distribuído entre 0 e 1
    const u = Math.random();

    // Aplica transformação exponencial inversa
    const intervalSeconds = -Math.log(1 - u) / lambdaPerSecond;

    return intervalSeconds;
  }

  //Retorna informações sobre a taxa atual
  getRateInfo(): { hour: number; lambda: number; percentual: number } {
    const hour = new Date().getHours();
    const hourData = this.lambdasPorHora.find(h => h.Hora === hour);

    return {
      hour,
      lambda: hourData?.Lambda || 0,
      percentual: hourData?.Percentual || 0
    };
  }
}
