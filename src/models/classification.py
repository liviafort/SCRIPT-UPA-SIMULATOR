"""Classificação de Manchester - Protocolo de triagem"""
from enum import Enum


class ClassificacaoTriagem(Enum):
    """
    Protocolo de Manchester para classificação de risco
    Campina Grande - PB usa 4 níveis (sem LARANJA)
    """
    VERMELHO = (1, 0, "Emergência - Atendimento imediato")
    AMARELO = (2, 60, "Muito urgente - Atendimento em até 60 minutos")
    VERDE = (3, 120, "Urgente - Atendimento em até 120 minutos")
    AZUL = (4, 240, "Pouco urgente - Atendimento em até 240 minutos")

    def __init__(self, prioridade: int, max_wait_minutes: int, descricao: str):
        self.prioridade = prioridade
        self.max_wait_minutes = max_wait_minutes
        self.descricao = descricao
