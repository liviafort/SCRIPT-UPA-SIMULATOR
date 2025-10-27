"""Modelo de dados do paciente"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from .classification import ClassificacaoTriagem


class PatientStatus(Enum):
    """Status do paciente no fluxo da UPA"""
    AGUARDANDO_TRIAGEM = "AGUARDANDO_TRIAGEM"
    AGUARDANDO_ATENDIMENTO = "AGUARDANDO_ATENDIMENTO"
    EM_ATENDIMENTO = "EM_ATENDIMENTO"
    FINALIZADO = "FINALIZADO"


@dataclass
class Patient:
    """Paciente no sistema UPA"""
    patient_id: str
    upa_id: str
    upa_name: str
    bairro: str
    status: PatientStatus
    classificacao: Optional[ClassificacaoTriagem] = None
    entrada_timestamp: Optional[datetime] = None
    triagem_timestamp: Optional[datetime] = None
    atendimento_timestamp: Optional[datetime] = None
    finalizacao_timestamp: Optional[datetime] = None

    def __lt__(self, other):
        """Comparação para PriorityQueue - menor prioridade = mais urgente"""
        if self.classificacao and other.classificacao:
            return self.classificacao.prioridade < other.classificacao.prioridade
        return False
