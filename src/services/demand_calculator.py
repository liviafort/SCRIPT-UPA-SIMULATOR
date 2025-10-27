"""Calculadora de demanda com padrões realistas de horário"""
from datetime import datetime
from typing import Dict


class DemandCalculator:
    """
    Calcula demanda de pacientes baseada em:
    - Horário do dia (picos 11-12h, 17-19h)
    - Taxa base da UPA
    - Dados reais: UPA Dinamérica ~12.200 atendimentos/mês

    IMPORTANTE: Taxas AUMENTADAS para forçar formação de filas
    """

    # Multiplicadores por hora do dia
    HOURLY_MULTIPLIERS = {
        0: 0.3, 1: 0.2, 2: 0.2, 3: 0.2, 4: 0.3, 5: 0.4,  # Madrugada (baixa)
        6: 0.6, 7: 0.9, 8: 1.1, 9: 1.2, 10: 1.3,         # Manhã (crescente)
        11: 1.8, 12: 1.7,                                # PICO MANHÃ
        13: 1.2, 14: 1.1, 15: 1.2, 16: 1.3,              # Tarde
        17: 2.0, 18: 2.2, 19: 1.9,                       # PICO TARDE (maior)
        20: 1.5, 21: 1.3, 22: 1.0, 23: 0.7               # Noite
    }

    def __init__(self, base_rate: float):
        """
        Args:
            base_rate: Taxa base de pacientes por hora (já aumentada para forçar filas)
        """
        self.base_rate = base_rate

    def get_current_rate(self) -> float:
        """
        Retorna taxa de pacientes/hora para o horário atual

        Returns:
            float: pacientes por hora ajustado pelo horário
        """
        hour = datetime.now().hour
        multiplier = self.HOURLY_MULTIPLIERS.get(hour, 1.0)
        return self.base_rate * multiplier

    def get_interval_seconds(self) -> float:
        """
        Retorna intervalo em segundos entre pacientes

        Returns:
            float: segundos entre cada paciente
        """
        rate = self.get_current_rate()
        return 3600 / rate  # 3600 segundos por hora

    @staticmethod
    def get_recommended_rates() -> Dict[str, float]:
        """
        Taxas recomendadas baseadas em dados reais
        AUMENTADAS para forçar filas e demonstrar o sistema sob pressão

        Returns:
            Dict com taxas base por UPA
        """
        return {
            "UPA Dinamérica": 40.0,   # ~960 pac/dia (vs 407 real) - 2.3x
            "UPA Alto Branco": 30.0   # ~720 pac/dia (vs ~285 real) - 2.5x
        }

    def get_peak_info(self) -> Dict:
        """Retorna informações sobre pico atual"""
        hour = datetime.now().hour
        multiplier = self.HOURLY_MULTIPLIERS.get(hour, 1.0)

        is_peak = multiplier >= 1.5
        peak_type = ""

        if 11 <= hour <= 12:
            peak_type = "Pico Manhã"
        elif 17 <= hour <= 19:
            peak_type = "Pico Tarde (maior)"
        elif multiplier >= 1.3:
            peak_type = "Alta demanda"

        return {
            "hour": hour,
            "multiplier": multiplier,
            "is_peak": is_peak,
            "peak_type": peak_type,
            "current_rate": self.get_current_rate()
        }
