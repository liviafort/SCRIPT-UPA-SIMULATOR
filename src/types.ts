export type ClassificacaoManchester = 'VERMELHO' | 'AMARELO' | 'VERDE' | 'AZUL';

export interface Patient {
  patientId: string;
  upaId: string;
  upaName: string;
  bairro: string;
  classificacao: ClassificacaoManchester;
  entradaTimestamp: string;
  triagemTimestamp?: string;
  atendimentoTimestamp?: string;
}

export interface UPAConfig {
  name: string;
  id: string;
  bairros: string[];
  classificationDistribution: Record<ClassificacaoManchester, number>;
}

export interface LambdaPorHora {
  Hora: number;
  Lambda: number;
  Percentual: number;
}

export interface DiaSemanaStats {
  media: number;
  std: number;
  lambda_hora: number;
}

export interface UPAParams {
  lambda_hora_media: number;
  lambda_dia: number;
  lambda_por_hora: LambdaPorHora[];
  tempo_entre_chegadas_minutos: number;
  dias_semana: {
    Seg: DiaSemanaStats;
    Ter: DiaSemanaStats;
    Qua: DiaSemanaStats;
    Qui: DiaSemanaStats;
    Sex: DiaSemanaStats;
    Sáb: DiaSemanaStats;
    Dom: DiaSemanaStats;
  };
}

export interface AuthConfig {
  username: string;
  password: string;
  base_url: string;
  endpoints: {
    login: string;
    refresh: string;
  };
}

export interface AuthResponse {
  token: string;
  expiresIn: number;
}

export interface Config {
  auth: AuthConfig;
  monitoring_service: {
    base_url: string;
    endpoints: {
      entrada: string;
      triagem: string;
      atendimento: string;
    };
  };
  gateway_service: {
    base_url: string;
    endpoints: {
      upas: string;
    };
  };
  upas: {
    [key: string]: {
      enabled: boolean;
      bairros: string[];
    };
  };
  simulation: {
    triagem_time_minutes: number;
    atendimento_time_minutes: number;
    min_wait_before_triagem_minutes: number;
    classification_distribution: Record<ClassificacaoManchester, number>;
  };
}

export interface SimulationParams {
  Dinamerica: UPAParams;
  Alto_Branco: UPAParams;
}
