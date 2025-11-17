import { LambdaPorHora } from './types';

export class PoissonGenerator {
  private lambdasPorHora: LambdaPorHora[];

  constructor(lambdasPorHora: LambdaPorHora[]) {
    this.lambdasPorHora = lambdasPorHora;
  }

  private getCurrentLambda(): number {
    const hour = new Date().getHours();
    const hourData = this.lambdasPorHora.find(h => h.Hora === hour);
    return hourData ? hourData.Lambda : this.lambdasPorHora[0].Lambda;
  }

  getNextInterval(): number {
    const lambda = this.getCurrentLambda();
    const lambdaPerSecond = lambda / 3600;
    const u = Math.random();
    const intervalSeconds = -Math.log(1 - u) / lambdaPerSecond;
    return intervalSeconds;
  }

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
