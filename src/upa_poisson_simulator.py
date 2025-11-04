#!/usr/bin/env python3
"""
Simulador de UPA usando SimPy com Distribuição Poisson
Baseado em dados reais das UPAs de Campina Grande - PB
"""

import simpy
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import random
import uuid


class ClassificacaoManchester(Enum):
    """Classificação de Manchester"""
    VERMELHO = (1, 0, "Emergência")           
    LARANJA = (2, 10, "Muito Urgente")        
    AMARELO = (3, 60, "Urgente")              
    VERDE = (4, 120, "Pouco Urgente")         
    AZUL = (5, 240, "Não Urgente")            

    def __init__(self, prioridade, max_wait_minutes, descricao):
        self.prioridade = prioridade
        self.max_wait_minutes = max_wait_minutes
        self.descricao = descricao

    def __lt__(self, other):
        """Permite comparação para fila de prioridade"""
        return self.prioridade < other.prioridade


@dataclass
class Paciente:
    """Representa um paciente na UPA"""
    id: str
    upa_name: str
    hora_chegada: float
    classificacao: Optional[ClassificacaoManchester] = None
    hora_inicio_triagem: Optional[float] = None
    hora_fim_triagem: Optional[float] = None
    hora_inicio_atendimento: Optional[float] = None
    hora_fim_atendimento: Optional[float] = None

    def tempo_total(self, tempo_atual: float) -> float:
        """Calcula tempo total no sistema"""
        return tempo_atual - self.hora_chegada

    def tempo_espera_atendimento(self) -> float:
        """Tempo de espera para atendimento após triagem"""
        if self.hora_inicio_atendimento and self.hora_fim_triagem:
            return self.hora_inicio_atendimento - self.hora_fim_triagem
        return 0.0


@dataclass
class EstatisticasUPA:
    """Estatísticas da simulação"""
    pacientes_atendidos: int = 0
    pacientes_em_triagem: int = 0
    pacientes_em_atendimento: int = 0
    pacientes_aguardando_atendimento: int = 0
    tempo_espera_total: List[float] = field(default_factory=list)
    tempo_atendimento_total: List[float] = field(default_factory=list)
    violacoes_manchester: int = 0
    pacientes_por_classificacao: Dict[str, int] = field(default_factory=dict)


class UPAPoissonSimulator:
    """
    Simulador de UPA usando SimPy com chegadas Poisson
    """

    def __init__(self, config_path: str = "simulation_params.json"):
        """
        Inicializa o simulador

        Args:
            config_path: Caminho para arquivo de configuração gerado pelo data_analyzer
        """
        self.config = self._load_config(config_path)
        self.env = simpy.Environment()
        self.upas = {}
        self.stats = {}

        self.num_enfermeiros_triagem = 2
        self.num_medicos_atendimento = 3
        self.tempo_simulacao_horas = 24 
        self.random_seed = 42

        random.seed(self.random_seed)
        np.random.seed(self.random_seed)

    def _load_config(self, config_path: str) -> dict:
        """Carrega configuração de parâmetros da simulação"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Arquivo de configuração não encontrado: {config_path}")
            logging.info("Execute primeiro: python src/data_analyzer.py")
            raise

    def setup_logging(self):
        """Configura sistema de logs"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

    def _get_arrival_rate(self, upa_config: dict, current_time_hours: float) -> float:
        """
        Retorna taxa de chegada (lambda) para hora atual

        Args:
            upa_config: Configuração da UPA
            current_time_hours: Tempo atual em horas

        Returns:
            Taxa de chegada em pacientes por hora
        """
        hour = int(current_time_hours % 24)
        hourly_rates = upa_config['hourly_arrival_rates']

        if isinstance(list(hourly_rates.keys())[0], str):
            hourly_rates = {int(k): v for k, v in hourly_rates.items()}

        return hourly_rates.get(hour, 10.0)  

    def processo_chegada_pacientes(self, env: simpy.Environment, upa_name: str, upa_config: dict):
        """
        Processo de chegada de pacientes usando distribuição Poisson

        A distribuição Poisson é ideal para modelar chegadas aleatórias e independentes.
        Usamos processo de Poisson não-homogêneo (taxa varia por hora do dia).
        """
        paciente_counter = 0

        while True:
            current_time_hours = env.now / 60 
            lambda_rate = self._get_arrival_rate(upa_config, current_time_hours)
            intervalo_minutos = np.random.exponential(60.0 / lambda_rate)

            yield env.timeout(intervalo_minutos)

            paciente_counter += 1
            paciente = Paciente(
                id=f"{upa_name[:3].upper()}-{paciente_counter:04d}",
                upa_name=upa_name,
                hora_chegada=env.now
            )

            logging.info(f"[{self._format_time(env.now)}] Paciente {paciente.id} chegou na {upa_name}")

            env.process(self.processo_triagem(env, upa_name, paciente))

    def processo_triagem(self, env: simpy.Environment, upa_name: str, paciente: Paciente):
        """
        Processo de triagem com classificação de Manchester
        """
        enfermeiros = self.upas[upa_name]['enfermeiros_triagem']
        stats = self.stats[upa_name]

        stats.pacientes_em_triagem += 1

        with enfermeiros.request() as req:
            yield req

            paciente.hora_inicio_triagem = env.now

            tempo_triagem = np.random.uniform(2, 5)
            yield env.timeout(tempo_triagem)

            paciente.classificacao = self._classificar_paciente(
                self.config[upa_name]['classification_distribution']
            )

            paciente.hora_fim_triagem = env.now
            stats.pacientes_em_triagem -= 1

            class_name = paciente.classificacao.name
            stats.pacientes_por_classificacao[class_name] = \
                stats.pacientes_por_classificacao.get(class_name, 0) + 1

            logging.info(
                f"[{self._format_time(env.now)}] Paciente {paciente.id} "
                f"classificado como {paciente.classificacao.name} "
                f"({paciente.classificacao.descricao})"
            )
            env.process(self.processo_atendimento(env, upa_name, paciente))

    def processo_atendimento(self, env: simpy.Environment, upa_name: str, paciente: Paciente):
        """
        Processo de atendimento médico com fila priorizada
        """
        medicos = self.upas[upa_name]['medicos_atendimento']
        stats = self.stats[upa_name]

        stats.pacientes_aguardando_atendimento += 1

        with medicos.request(priority=paciente.classificacao.prioridade) as req:
            yield req

            stats.pacientes_aguardando_atendimento -= 1
            stats.pacientes_em_atendimento += 1

            paciente.hora_inicio_atendimento = env.now
            tempo_espera_minutos = paciente.tempo_espera_atendimento()
            max_wait = paciente.classificacao.max_wait_minutes

            if max_wait > 0 and tempo_espera_minutos > max_wait:
                stats.violacoes_manchester += 1
                logging.warning(
                    f"[{self._format_time(env.now)}] ⚠️  VIOLAÇÃO PROTOCOLO: "
                    f"Paciente {paciente.id} [{paciente.classificacao.name}] "
                    f"aguardou {tempo_espera_minutos:.1f} min "
                    f"(máximo: {max_wait} min)"
                )

            service_times = self.config[upa_name]['service_times_minutes']
            class_name = paciente.classificacao.name

            if class_name in service_times:
                tempo_min, tempo_max = service_times[class_name]
                tempo_atendimento = np.random.uniform(tempo_min, tempo_max)
            else:
                tempo_atendimento = np.random.uniform(20, 60)

            yield env.timeout(tempo_atendimento)

            paciente.hora_fim_atendimento = env.now
            stats.pacientes_em_atendimento -= 1
            stats.pacientes_atendidos += 1

            tempo_total = paciente.tempo_total(env.now)
            stats.tempo_espera_total.append(tempo_espera_minutos)
            stats.tempo_atendimento_total.append(tempo_atendimento)

            logging.info(
                f"[{self._format_time(env.now)}] ✓ Paciente {paciente.id} "
                f"finalizado após {tempo_total:.1f} min no sistema"
            )

    def _classificar_paciente(self, distribution: Dict[str, float]) -> ClassificacaoManchester:
        """Classifica paciente segundo distribuição probabilística"""
        rand = random.random()
        cumulative = 0.0

        for class_name, prob in distribution.items():
            cumulative += prob
            if rand <= cumulative:
                return ClassificacaoManchester[class_name]

        return ClassificacaoManchester.VERDE

    def _format_time(self, minutes: float) -> str:
        """Formata tempo em minutos para HH:MM"""
        hours = int(minutes // 60) % 24
        mins = int(minutes % 60)
        return f"{hours:02d}:{mins:02d}"

    def processo_monitoramento(self, env: simpy.Environment):
        """Processo de monitoramento periódico das estatísticas"""
        while True:
            yield env.timeout(60) 

            logging.info(f"\n{'='*80}")
            logging.info(f"ESTATÍSTICAS - {self._format_time(env.now)}")
            logging.info(f"{'='*80}")

            for upa_name, stats in self.stats.items():
                logging.info(f"\n{upa_name}:")
                logging.info(f"  Pacientes atendidos: {stats.pacientes_atendidos}")
                logging.info(f"  Em triagem: {stats.pacientes_em_triagem}")
                logging.info(f"  Aguardando atendimento: {stats.pacientes_aguardando_atendimento}")
                logging.info(f"  Em atendimento: {stats.pacientes_em_atendimento}")
                logging.info(f"  Violações protocolo Manchester: {stats.violacoes_manchester}")

                if stats.tempo_espera_total:
                    avg_wait = np.mean(stats.tempo_espera_total)
                    logging.info(f"  Tempo médio de espera: {avg_wait:.1f} min")

                if stats.pacientes_por_classificacao:
                    logging.info(f"  Distribuição de classificações:")
                    for class_name, count in stats.pacientes_por_classificacao.items():
                        pct = 100 * count / sum(stats.pacientes_por_classificacao.values())
                        logging.info(f"    {class_name}: {count} ({pct:.1f}%)")

    def setup_upa(self, upa_name: str, upa_config: dict):
        """Configura recursos da UPA"""
        self.upas[upa_name] = {
            'enfermeiros_triagem': simpy.PriorityResource(self.env, capacity=self.num_enfermeiros_triagem),
            'medicos_atendimento': simpy.PriorityResource(self.env, capacity=self.num_medicos_atendimento),
        }
        self.stats[upa_name] = EstatisticasUPA()

    def run(self):
        """Executa a simulação"""
        self.setup_logging()

        logging.info("="*80)
        logging.info("SIMULADOR UPA - MODELAGEM POISSON")
        logging.info("="*80)
        logging.info(f"Tempo de simulação: {self.tempo_simulacao_horas} horas")
        logging.info(f"Enfermeiros por UPA: {self.num_enfermeiros_triagem}")
        logging.info(f"Médicos por UPA: {self.num_medicos_atendimento}")
        logging.info("="*80)

        for upa_name, upa_config in self.config.items():
            logging.info(f"\nConfigurando {upa_name}...")
            logging.info(f"  Taxa média diária: {upa_config['summary']['avg_daily_arrivals']:.0f} pacientes")
            logging.info(f"  Horário de pico: {upa_config['summary']['peak_hour']}h")

            self.setup_upa(upa_name, upa_config)

            self.env.process(self.processo_chegada_pacientes(self.env, upa_name, upa_config))

        self.env.process(self.processo_monitoramento(self.env))

        logging.info("\n" + "="*80)
        logging.info("INICIANDO SIMULAÇÃO...")
        logging.info("="*80 + "\n")

        tempo_simulacao_minutos = self.tempo_simulacao_horas * 60
        self.env.run(until=tempo_simulacao_minutos)

        self._print_final_report()

    def _print_final_report(self):
        """Imprime relatório final da simulação"""
        logging.info("\n" + "="*80)
        logging.info("RELATÓRIO FINAL DA SIMULAÇÃO")
        logging.info("="*80)

        for upa_name, stats in self.stats.items():
            logging.info(f"\n{upa_name}:")
            logging.info(f"{'─'*60}")
            logging.info(f"Total de pacientes atendidos: {stats.pacientes_atendidos}")
            logging.info(f"Violações do protocolo de Manchester: {stats.violacoes_manchester}")

            if stats.violacoes_manchester > 0:
                pct_violacao = 100 * stats.violacoes_manchester / stats.pacientes_atendidos
                logging.info(f"Taxa de violação: {pct_violacao:.2f}%")

            if stats.tempo_espera_total:
                logging.info(f"\nTempos de Espera:")
                logging.info(f"  Média: {np.mean(stats.tempo_espera_total):.1f} min")
                logging.info(f"  Mediana: {np.median(stats.tempo_espera_total):.1f} min")
                logging.info(f"  Máximo: {np.max(stats.tempo_espera_total):.1f} min")
                logging.info(f"  Mínimo: {np.min(stats.tempo_espera_total):.1f} min")

            if stats.tempo_atendimento_total:
                logging.info(f"\nTempos de Atendimento:")
                logging.info(f"  Média: {np.mean(stats.tempo_atendimento_total):.1f} min")
                logging.info(f"  Mediana: {np.median(stats.tempo_atendimento_total):.1f} min")

            if stats.pacientes_por_classificacao:
                logging.info(f"\nDistribuição de Classificações:")
                total_class = sum(stats.pacientes_por_classificacao.values())
                for class_name in ['VERMELHO', 'LARANJA', 'AMARELO', 'VERDE', 'AZUL']:
                    count = stats.pacientes_por_classificacao.get(class_name, 0)
                    pct = 100 * count / total_class if total_class > 0 else 0
                    logging.info(f"  {class_name}: {count} pacientes ({pct:.1f}%)")

        logging.info("\n" + "="*80)


def main():
    """Função principal"""
    try:
        simulator = UPAPoissonSimulator()
        simulator.run()
    except FileNotFoundError:
        logging.error("\nErro: Arquivo de configuração não encontrado!")
        logging.info("\nExecute primeiro o analisador de dados:")
        logging.info("   python src/data_analyzer.py")
        logging.info("\nIsso irá gerar o arquivo simulation_params.json necessário.")
    except Exception as e:
        logging.error(f"\nErro durante simulação: {e}")
        raise


if __name__ == "__main__":
    main()