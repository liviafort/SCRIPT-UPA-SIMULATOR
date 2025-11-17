import { LambdaPorHora, UPAParams } from './types';

export class PoissonGenerator {
  private lambdasPorHora: LambdaPorHora[];
  private params: UPAParams;
  private readonly diasSemanaMap = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

  constructor(params: UPAParams) {
    this.params = params;
    this.lambdasPorHora = params.lambda_por_hora;
  }

  private getCurrentLambda(): number {
    const now = new Date();
    const hour = now.getHours();
    const dayOfWeek = this.diasSemanaMap[now.getDay()];

    const hourData = this.lambdasPorHora.find(h => h.Hora === hour);
    const baseLambda = hourData ? hourData.Lambda : this.lambdasPorHora[0].Lambda;

    const dayStats = this.params.dias_semana[dayOfWeek as keyof typeof this.params.dias_semana];
    const adjustmentFactor = dayStats.lambda_hora / this.params.lambda_hora_media;

    return baseLambda * adjustmentFactor;
  }

  getNextInterval(): number {
    const lambda = this.getCurrentLambda();
    const lambdaPerSecond = lambda / 3600;
    const u = Math.random();
    const intervalSeconds = -Math.log(1 - u) / lambdaPerSecond;
    return intervalSeconds;
  }

  getRateInfo(): { hour: number; lambda: number; percentual: number; dayOfWeek: string; adjustmentFactor: number } {
    const now = new Date();
    const hour = now.getHours();
    const dayOfWeek = this.diasSemanaMap[now.getDay()];
    const hourData = this.lambdasPorHora.find(h => h.Hora === hour);

    const dayStats = this.params.dias_semana[dayOfWeek as keyof typeof this.params.dias_semana];
    const adjustmentFactor = dayStats.lambda_hora / this.params.lambda_hora_media;
    const baseLambda = hourData ? hourData.Lambda : this.lambdasPorHora[0].Lambda;

    return {
      hour,
      lambda: baseLambda * adjustmentFactor,
      percentual: hourData?.Percentual || 0,
      dayOfWeek,
      adjustmentFactor
    };
  }
}
