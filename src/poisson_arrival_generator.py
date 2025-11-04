#!/usr/bin/env python3
"""
Gerador de Chegadas usando Processo Poisson Não-Homogêneo
Baseado em dados reais de UPAs
"""

import numpy as np
from datetime import datetime
from typing import Dict, Optional
import json
from pathlib import Path


class PoissonArrivalGenerator:
    """
    Gera intervalos de chegada usando processo Poisson não-homogêneo.

    A taxa de chegada (λ) varia por hora do dia, baseada em dados históricos.
    Intervalos entre chegadas seguem distribuição exponencial: Exp(λ).
    """

    def __init__(self, upa_name: str, simulation_params_path: str = "simulation_params.json"):
        """
        Inicializa o gerador de chegadas Poisson.

        Args:
            upa_name: Nome da UPA
            simulation_params_path: Caminho para arquivo com parâmetros extraídos dos dados
        """
        self.upa_name = upa_name
        self.hourly_rates = {}
        self.default_rate = 10.0  # Taxa padrão caso não haja dados

        self._load_simulation_params(simulation_params_path)

    def _load_simulation_params(self, params_path: str):
        """Carrega parâmetros de simulação extraídos dos dados reais"""
        try:
            params_file = Path(params_path)
            if not params_file.exists():
                print(f"[AVISO] Arquivo {params_path} nao encontrado. Usando taxas padrao.")
                print(f"   Execute: python src/data_analyzer.py")
                self._use_default_rates()
                return

            with open(params_path, 'r', encoding='utf-8') as f:
                all_params = json.load(f)

            # Busca configuração da UPA
            upa_config = None
            for key, config in all_params.items():
                if key.lower() in self.upa_name.lower() or self.upa_name.lower() in key.lower():
                    upa_config = config
                    break

            if not upa_config:
                print(f"[AVISO] Configuracao para '{self.upa_name}' nao encontrada. Usando taxas padrao.")
                self._use_default_rates()
                return

            # Carrega taxas por hora
            self.hourly_rates = upa_config.get('hourly_arrival_rates', {})

            # Converte chaves para int se necessário
            if self.hourly_rates and isinstance(list(self.hourly_rates.keys())[0], str):
                self.hourly_rates = {int(k): float(v) for k, v in self.hourly_rates.items()}

            avg_rate = upa_config.get('summary', {}).get('avg_daily_arrivals', 0)
            print(f"[OK] Taxas de chegada carregadas para {self.upa_name}")
            print(f"  Taxa media diaria: {avg_rate:.0f} pacientes")

        except Exception as e:
            print(f"[AVISO] Erro ao carregar parametros: {e}. Usando taxas padrao.")
            self._use_default_rates()

    def _use_default_rates(self):
        """Define taxas padrão quando não há dados disponíveis"""
        # Padrão: horário comercial mais movimentado
        self.hourly_rates = {
            0: 5, 1: 3, 2: 2, 3: 2, 4: 3, 5: 5,
            6: 15, 7: 25, 8: 35, 9: 40, 10: 38, 11: 35,
            12: 30, 13: 28, 14: 32, 15: 35, 16: 38, 17: 40,
            18: 35, 19: 30, 20: 25, 21: 20, 22: 15, 23: 10
        }

    def get_current_rate(self, current_time: Optional[datetime] = None) -> float:
        """
        Retorna taxa de chegada (λ) para o horário atual.

        Args:
            current_time: Horário atual (usa datetime.now() se None)

        Returns:
            Taxa de chegada em pacientes por hora
        """
        if current_time is None:
            current_time = datetime.now()

        hour = current_time.hour
        return self.hourly_rates.get(hour, self.default_rate)

    def get_next_interval_seconds(self, current_time: Optional[datetime] = None) -> float:
        """
        Gera próximo intervalo de tempo até chegada do próximo paciente.

        Usa distribuição exponencial: tempo entre eventos em processo Poisson.
        Intervalo médio = 3600 / λ segundos (onde λ é pacientes/hora)

        Args:
            current_time: Horário atual (usa datetime.now() se None)

        Returns:
            Intervalo em segundos até próxima chegada
        """
        lambda_rate = self.get_current_rate(current_time)

        if lambda_rate <= 0:
            return 3600.0  # 1 hora se taxa inválida

        # Intervalo médio em segundos = 3600 / λ
        mean_interval_seconds = 3600.0 / lambda_rate

        # Gera intervalo usando distribuição exponencial
        # np.random.exponential(scale) onde scale = média
        interval = np.random.exponential(mean_interval_seconds)

        return interval

    def get_rate_info(self, current_time: Optional[datetime] = None) -> Dict:
        """
        Retorna informações sobre a taxa atual.

        Args:
            current_time: Horário atual

        Returns:
            Dicionário com informações da taxa
        """
        if current_time is None:
            current_time = datetime.now()

        hour = current_time.hour
        rate = self.get_current_rate(current_time)

        # Identifica picos
        max_rate = max(self.hourly_rates.values()) if self.hourly_rates else rate
        is_peak = rate >= max_rate * 0.8  # Pico se >= 80% da taxa máxima

        return {
            'hour': hour,
            'current_rate': rate,
            'is_peak': is_peak,
            'peak_type': 'PICO' if is_peak else 'normal',
            'mean_interval_seconds': 3600.0 / rate if rate > 0 else 3600.0
        }

    def apply_multiplier(self, multiplier: float):
        """
        Aplica multiplicador às taxas (para testes/ajustes).

        Args:
            multiplier: Fator multiplicador (ex: 1.5 = 50% mais pacientes)
        """
        self.hourly_rates = {hour: rate * multiplier for hour, rate in self.hourly_rates.items()}


# Classe de compatibilidade com código antigo
class DemandCalculator:
    """
    Classe mantida para compatibilidade com código existente.
    Wrapper para PoissonArrivalGenerator.
    """

    def __init__(self, base_rate: float, upa_name: str = "UPA"):
        """
        Args:
            base_rate: Taxa base (usado apenas se não houver dados reais)
            upa_name: Nome da UPA
        """
        self.poisson_generator = PoissonArrivalGenerator(upa_name)

        # Se não conseguiu carregar dados, usa base_rate
        if not self.poisson_generator.hourly_rates:
            avg_rate_per_hour = base_rate / 24
            self.poisson_generator.hourly_rates = {h: avg_rate_per_hour for h in range(24)}

    def get_interval_seconds(self) -> float:
        """Retorna intervalo até próxima chegada (compatibilidade)"""
        return self.poisson_generator.get_next_interval_seconds()

    def get_peak_info(self) -> Dict:
        """Retorna informações do pico atual (compatibilidade)"""
        return self.poisson_generator.get_rate_info()

    @staticmethod
    def get_recommended_rates() -> Dict[str, float]:
        """Taxas recomendadas por UPA (compatibilidade - não usado mais)"""
        return {
            "UPA Dinamérica": 150,
            "UPA Alto Branco": 120
        }