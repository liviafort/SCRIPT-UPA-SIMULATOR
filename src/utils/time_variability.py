"""Calculadora de variabilidade nos tempos (simula eventos reais)"""
import random
from typing import Tuple


class TimeVariabilityCalculator:
    """
    Simula eventos que causam atrasos no atendimento:
    - Pausa do médico/enfermeiro
    - Troca de turno
    - Casos complexos
    - Equipamentos

    Objetivo: Criar FILAS realistas para demonstração
    """

    # Probabilidades de eventos
    PAUSA_PROBABILITY = 0.10          # 10% - pausa/intervalo
    TROCA_TURNO_PROBABILITY = 0.05    # 5% - troca de turno
    CASO_COMPLEXO_PROBABILITY = 0.15  # 15% - caso complexo (VERMELHO/AMARELO)
    EQUIPAMENTO_PROBABILITY = 0.08    # 8% - espera por equipamento

    # Multiplicadores de tempo
    PAUSA_MULTIPLIER = 1.5            # +50% tempo
    TROCA_TURNO_MULTIPLIER = 2.0      # +100% tempo
    CASO_COMPLEXO_MULTIPLIER = 1.8    # +80% tempo
    EQUIPAMENTO_MULTIPLIER = 1.4      # +40% tempo

    @classmethod
    def apply_variability(cls, base_time: float, patient_classification: str = None) -> Tuple[float, str]:
        """
        Aplica variabilidade ao tempo base

        Args:
            base_time: Tempo base em segundos
            patient_classification: Classificação do paciente (VERMELHO, AMARELO, etc)

        Returns:
            Tuple[float, str]: (tempo_ajustado, motivo)
        """
        multiplier = 1.0
        reason = "Normal"

        # Pausa (qualquer classificação)
        if random.random() < cls.PAUSA_PROBABILITY:
            multiplier = cls.PAUSA_MULTIPLIER
            reason = "Pausa profissional"
            return base_time * multiplier, reason

        # Troca de turno (raro, mas grande impacto)
        if random.random() < cls.TROCA_TURNO_PROBABILITY:
            multiplier = cls.TROCA_TURNO_MULTIPLIER
            reason = "Troca de turno"
            return base_time * multiplier, reason

        # Caso complexo (mais comum em VERMELHO/AMARELO)
        if patient_classification in ['VERMELHO', 'AMARELO']:
            if random.random() < cls.CASO_COMPLEXO_PROBABILITY:
                multiplier = cls.CASO_COMPLEXO_MULTIPLIER
                reason = "Caso complexo"
                return base_time * multiplier, reason

        # Espera por equipamento
        if random.random() < cls.EQUIPAMENTO_PROBABILITY:
            multiplier = cls.EQUIPAMENTO_MULTIPLIER
            reason = "Aguardando equipamento"
            return base_time * multiplier, reason

        return base_time, reason

    @classmethod
    def apply_triagem_variability(cls, base_time: float) -> Tuple[float, str]:
        """
        Aplica variabilidade específica para triagem

        Args:
            base_time: Tempo base de triagem em segundos

        Returns:
            Tuple[float, str]: (tempo_ajustado, motivo)
        """
        # Triagem DEVE ser rápida para formar filas no atendimento
        # Variabilidade mínima (apenas 2% de chance de atraso)
        if random.random() < 0.02:  # 2% de chance
            return base_time * 1.2, "Pausa enfermeiro"

        return base_time, "Normal"

    @classmethod
    def get_statistics(cls) -> dict:
        """Retorna estatísticas sobre probabilidades configuradas"""
        return {
            "pausa": {
                "probability": cls.PAUSA_PROBABILITY,
                "multiplier": cls.PAUSA_MULTIPLIER,
                "avg_delay_minutes": (cls.PAUSA_MULTIPLIER - 1) * 3  # Assumindo 3min base
            },
            "troca_turno": {
                "probability": cls.TROCA_TURNO_PROBABILITY,
                "multiplier": cls.TROCA_TURNO_MULTIPLIER,
                "avg_delay_minutes": (cls.TROCA_TURNO_MULTIPLIER - 1) * 3
            },
            "caso_complexo": {
                "probability": cls.CASO_COMPLEXO_PROBABILITY,
                "multiplier": cls.CASO_COMPLEXO_MULTIPLIER,
                "note": "Apenas VERMELHO/AMARELO"
            },
            "equipamento": {
                "probability": cls.EQUIPAMENTO_PROBABILITY,
                "multiplier": cls.EQUIPAMENTO_MULTIPLIER
            }
        }
