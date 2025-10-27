#!/usr/bin/env python3
"""
Simulador de Fluxo de Pacientes UPA - Protocolo de Manchester
Campina Grande - PB
"""

import json
import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from queue import PriorityQueue, Queue
from typing import Dict, List
from models import Patient, PatientStatus, ClassificacaoTriagem
from services import APIClient, DemandCalculator
from utils import TimeVariabilityCalculator


@dataclass
class UPAConfig:
    """Configuração de uma UPA"""
    name: str
    uuid: str
    enabled: bool
    flow_mode: str
    flow_rate: float
    bairros: List[str]
    classificacao_distribution: Dict[str, float]


class UPASimulator:
    """Simulador principal de fluxo de pacientes UPA"""

    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.monitoring_client = APIClient(self.config["monitoring_service"]["base_url"])
        self.gateway_client = APIClient(self.config["gateway_service"]["base_url"])

        self.upas: Dict[str, UPAConfig] = {}
        self.demand_calculators: Dict[str, DemandCalculator] = {}

        self.fila_triagem: Dict[str, Queue] = {}
        self.fila_atendimento: Dict[str, PriorityQueue] = {}
        self.fila_triagem_locks: Dict[str, threading.Lock] = {}
        self.fila_atendimento_locks: Dict[str, threading.Lock] = {}

        self.active_patients: Dict[str, Patient] = {}
        self.active_patients_lock = threading.Lock()

        self.running = True
        self.threads: List[threading.Thread] = []

    def _load_config(self, config_path: str) -> dict:
        """Carrega configuração do arquivo JSON"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _setup_logging(self):
        """Configura sistema de logs"""
        log_config = self.config["simulation"]["logging"]

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler = RotatingFileHandler(
            log_config["file"],
            maxBytes=log_config["max_bytes"],
            backupCount=log_config["backup_count"]
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        logger = logging.getLogger()
        logger.setLevel(getattr(logging, log_config["level"]))
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    def initialize(self):
        """Inicializa o simulador"""
        logging.info("Iniciando UPA Simulator - Protocolo de Manchester")

        self._fetch_upas()

        for upa_name, upa_config in self.upas.items():
            self.fila_triagem[upa_name] = Queue()
            self.fila_atendimento[upa_name] = PriorityQueue()
            self.fila_triagem_locks[upa_name] = threading.Lock()
            self.fila_atendimento_locks[upa_name] = threading.Lock()

            base_rate = DemandCalculator.get_recommended_rates().get(
                upa_name,
                upa_config.flow_rate
            )
            self.demand_calculators[upa_name] = DemandCalculator(base_rate)

        logging.info(f"Simulador inicializado com {len(self.upas)} UPA(s)")
        logging.info("Protocolo de Manchester: Classificação na triagem, atendimento priorizado")
        logging.info("MODO: Taxas aumentadas para forçar formação de filas")

        for upa_name, upa_config in self.upas.items():
            peak_info = self.demand_calculators[upa_name].get_peak_info()
            logging.info(
                f"  - {upa_name}: {peak_info['current_rate']:.1f} pacientes/hora "
                f"(hora {peak_info['hour']}h - {peak_info['peak_type'] or 'normal'})"
            )

    def _fetch_upas(self):
        """Busca UPAs da API"""
        logging.info("Buscando UPAs da API...")

        endpoint = self.config["gateway_service"]["endpoints"]["upas"]
        response = self.gateway_client.get(endpoint)

        if not response:
            logging.error("Falha ao buscar UPAs da API")
            return

        upas_api = response.get("data", [])
        logging.info(f"Encontradas {len(upas_api)} UPA(s) na API")

        config_upas = self.config.get("upas", {})

        for upa_data in upas_api:
            upa_name = upa_data["name"]

            if upa_name not in config_upas:
                continue

            upa_config_data = config_upas[upa_name]

            if not upa_config_data.get("enabled", True):
                continue

            flow_config = upa_config_data["patient_flow"]
            flow_rate = flow_config["rate"]

            self.upas[upa_name] = UPAConfig(
                name=upa_name,
                uuid=upa_data["id"],
                enabled=True,
                flow_mode=flow_config["mode"],
                flow_rate=flow_rate,
                bairros=upa_config_data["bairros"],
                classificacao_distribution=upa_config_data["classificacao_distribution"]
            )

            logging.info(f"UPA configurada: {upa_name} (UUID: {upa_data['id']})")

    def start(self):
        """Inicia threads de simulação"""
        for upa_name in self.upas.keys():
            thread = threading.Thread(
                target=self._entry_loop,
                args=(upa_name,),
                name=f"Entry-{upa_name}",
                daemon=True
            )
            thread.start()
            self.threads.append(thread)

        for upa_name in self.upas.keys():
            triagem_thread = threading.Thread(
                target=self._triagem_processing_loop,
                args=(upa_name,),
                name=f"Triagem-{upa_name}",
                daemon=True
            )
            triagem_thread.start()
            self.threads.append(triagem_thread)

        for upa_name in self.upas.keys():
            atendimento_thread = threading.Thread(
                target=self._atendimento_processing_loop,
                args=(upa_name,),
                name=f"Atendimento-{upa_name}",
                daemon=True
            )
            atendimento_thread.start()
            self.threads.append(atendimento_thread)

        monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            name="Monitor",
            daemon=True
        )
        monitor_thread.start()
        self.threads.append(monitor_thread)

        logging.info(f"Simulação iniciada com {len(self.threads)} threads")
        logging.info("Pressione Ctrl+C para parar")

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Para a simulação"""
        logging.info("Parando simulação...")
        self.running = False

        for thread in self.threads:
            thread.join(timeout=5)

        logging.info("Simulação finalizada")

    def _entry_loop(self, upa_name: str):
        """Loop de entrada de pacientes - usa demanda variável por horário"""
        upa_config = self.upas[upa_name]
        demand_calc = self.demand_calculators[upa_name]

        last_peak_log = None

        while self.running:
            try:
                interval = demand_calc.get_interval_seconds()
                peak_info = demand_calc.get_peak_info()

                current_hour = peak_info['hour']
                if current_hour != last_peak_log:
                    if peak_info['is_peak']:
                        logging.info(
                            f"[{upa_name}] {peak_info['peak_type']}: "
                            f"{peak_info['current_rate']:.0f} pac/h "
                            f"(intervalo: {interval:.0f}s)"
                        )
                    last_peak_log = current_hour

                patient = self._create_patient(upa_config)
                patient.entrada_timestamp = datetime.now()

                with self.fila_triagem_locks[upa_name]:
                    self.fila_triagem[upa_name].put(patient)
                    fila_size = self.fila_triagem[upa_name].qsize()

                self._register_entrada(patient)

                with self.active_patients_lock:
                    self.active_patients[patient.patient_id] = patient

                logging.info(
                    f"[{upa_name}] Entrada: Paciente {patient.patient_id[:8]} - {patient.bairro} "
                    f"(Fila triagem: {fila_size})"
                )

                time.sleep(interval)

            except Exception as e:
                logging.error(f"Erro no loop de entrada [{upa_name}]: {e}")
                time.sleep(5)

    def _create_patient(self, upa_config: UPAConfig) -> Patient:
        """Cria novo paciente SEM classificação (feita na triagem)"""
        return Patient(
            patient_id=str(uuid.uuid4()),
            upa_id=upa_config.uuid,
            upa_name=upa_config.name,
            bairro=random.choice(upa_config.bairros),
            status=PatientStatus.AGUARDANDO_TRIAGEM,
            classificacao=None,
            entrada_timestamp=datetime.now()
        )

    def _register_entrada(self, patient: Patient):
        """Registra entrada no serviço de monitoramento"""
        endpoint = self.config["monitoring_service"]["endpoints"]["entrada"]

        data = {
            "patientId": patient.patient_id,
            "upaId": patient.upa_id,
            "bairro": patient.bairro,
            "timestamp": patient.entrada_timestamp.isoformat()
        }

        response = self.monitoring_client.post(endpoint, data)

        if response:
            logging.debug(f"Entrada registrada: paciente {patient.patient_id[:8]}")
        else:
            logging.warning(f"Falha ao registrar entrada: paciente {patient.patient_id[:8]}")

    def _triagem_processing_loop(self, upa_name: str):
        """
        Loop de processamento de triagem - FIFO
        COM variabilidade de tempo (pausas, trocas)
        """
        triagem_config = self.config["simulation"]["triagem_time_seconds"]
        real_time_factor = self.config["simulation"]["real_time_factor"]

        while self.running:
            try:
                fila = self.fila_triagem[upa_name]

                if fila.empty():
                    time.sleep(1)
                    continue

                with self.fila_triagem_locks[upa_name]:
                    if fila.empty():
                        continue
                    patient = fila.get()

                base_time = random.randint(
                    triagem_config["min"],
                    triagem_config["max"]
                ) / real_time_factor

                triagem_time, reason = TimeVariabilityCalculator.apply_triagem_variability(base_time)

                reason_msg = f" ({reason})" if reason != "Normal" else ""
                logging.info(
                    f"[{upa_name}] Triagem: Paciente {patient.patient_id[:8]} "
                    f"({triagem_time:.0f}s{reason_msg})"
                )

                time.sleep(triagem_time)

                patient.classificacao = self._assign_classificacao(
                    self.upas[upa_name].classificacao_distribution
                )
                patient.triagem_timestamp = datetime.now()
                patient.status = PatientStatus.AGUARDANDO_ATENDIMENTO

                self._register_triagem(patient)

                with self.fila_atendimento_locks[upa_name]:
                    self.fila_atendimento[upa_name].put(patient)

                logging.info(
                    f"[{upa_name}] Classificação: Paciente {patient.patient_id[:8]} -> "
                    f"{patient.classificacao.name} (P{patient.classificacao.prioridade})"
                )

            except Exception as e:
                logging.error(f"Erro no loop de triagem [{upa_name}]: {e}")
                time.sleep(5)

    def _assign_classificacao(self, distribution: Dict[str, float]) -> ClassificacaoTriagem:
        """Atribui classificação de Manchester baseada em distribuição"""
        rand = random.random()
        cumulative = 0.0

        for classificacao_name, probability in distribution.items():
            cumulative += probability
            if rand <= cumulative:
                return ClassificacaoTriagem[classificacao_name]

        return ClassificacaoTriagem.VERDE

    def _register_triagem(self, patient: Patient):
        """Registra triagem no serviço de monitoramento"""
        endpoint = self.config["monitoring_service"]["endpoints"]["triagem"]

        data = {
            "patientId": patient.patient_id,
            "upaId": patient.upa_id,
            "classificacao": patient.classificacao.name,
            "timestamp": patient.triagem_timestamp.isoformat()
        }

        response = self.monitoring_client.post(endpoint, data)

        if response:
            logging.debug(f"Triagem registrada: paciente {patient.patient_id[:8]}")
        else:
            logging.warning(f"Falha ao registrar triagem: paciente {patient.patient_id[:8]}")

    def _atendimento_processing_loop(self, upa_name: str):
        """
        Loop de processamento de atendimento - PRIORIZADO
        COM variabilidade (pausas, trocas, casos complexos)
        """
        atendimento_config = self.config["simulation"]["atendimento_time_seconds"]
        real_time_factor = self.config["simulation"]["real_time_factor"]

        while self.running:
            try:
                fila = self.fila_atendimento[upa_name]

                if fila.empty():
                    time.sleep(1)
                    continue

                with self.fila_atendimento_locks[upa_name]:
                    if fila.empty():
                        continue
                    patient = fila.get()

                wait_time = (datetime.now() - patient.triagem_timestamp).total_seconds() / 60
                max_wait = patient.classificacao.max_wait_minutes

                if wait_time > max_wait and max_wait > 0:
                    logging.warning(
                        f"[{upa_name}] ALERTA PROTOCOLO MANCHESTER: Paciente {patient.patient_id[:8]} "
                        f"({patient.classificacao.name}) aguardou {wait_time:.1f} min "
                        f"(máximo: {max_wait} min) - TEMPO EXCEDIDO!"
                    )

                atend_config = atendimento_config[patient.classificacao.name]
                base_time = random.randint(
                    atend_config["min"],
                    atend_config["max"]
                ) / real_time_factor

                atendimento_time, reason = TimeVariabilityCalculator.apply_variability(
                    base_time,
                    patient.classificacao.name
                )

                reason_msg = f" - {reason}" if reason != "Normal" else ""
                logging.info(
                    f"[{upa_name}] Atendimento: Paciente {patient.patient_id[:8]} "
                    f"[{patient.classificacao.name}] ({atendimento_time:.0f}s, "
                    f"aguardou {wait_time:.1f}min{reason_msg})"
                )

                patient.status = PatientStatus.EM_ATENDIMENTO
                patient.atendimento_timestamp = datetime.now()

                self._register_atendimento(patient)

                time.sleep(atendimento_time)

                patient.status = PatientStatus.FINALIZADO
                patient.finalizacao_timestamp = datetime.now()

                with self.active_patients_lock:
                    if patient.patient_id in self.active_patients:
                        del self.active_patients[patient.patient_id]

                total_time = (patient.finalizacao_timestamp - patient.entrada_timestamp).total_seconds() / 60

                logging.info(
                    f"[{upa_name}] Finalizado: Paciente {patient.patient_id[:8]} "
                    f"[{patient.classificacao.name}] (total: {total_time:.1f}min)"
                )

            except Exception as e:
                logging.error(f"Erro no loop de atendimento [{upa_name}]: {e}")
                time.sleep(5)

    def _register_atendimento(self, patient: Patient):
        """Registra atendimento no serviço de monitoramento"""
        endpoint = self.config["monitoring_service"]["endpoints"]["atendimento"]

        data = {
            "patientId": patient.patient_id,
            "upaId": patient.upa_id,
            "timestamp": patient.atendimento_timestamp.isoformat()
        }

        response = self.monitoring_client.post(endpoint, data)

        if response:
            logging.debug(f"Atendimento registrado: paciente {patient.patient_id[:8]}")
        else:
            logging.warning(f"Falha ao registrar atendimento: paciente {patient.patient_id[:8]}")

    def _monitoring_loop(self):
        """Loop de monitoramento - estatísticas a cada minuto"""
        while self.running:
            try:
                time.sleep(60)

                stats = {"timestamp": datetime.now().isoformat(), "upas": {}}

                for upa_name in self.upas.keys():
                    fila_triagem_size = self.fila_triagem[upa_name].qsize()
                    fila_atendimento_size = self.fila_atendimento[upa_name].qsize()

                    stats["upas"][upa_name] = {
                        "fila_triagem": fila_triagem_size,
                        "fila_atendimento": fila_atendimento_size,
                        "total": fila_triagem_size + fila_atendimento_size
                    }

                total_active = sum(s["total"] for s in stats["upas"].values())

                logging.info(f"ESTATÍSTICAS [{datetime.now().strftime('%H:%M:%S')}] - Total de pacientes ativos: {total_active}")

                for upa_name, upa_stats in stats["upas"].items():
                    logging.info(
                        f"  [{upa_name}] "
                        f"Triagem (FIFO): {upa_stats['fila_triagem']}, "
                        f"Atendimento (PRIORIZADA): {upa_stats['fila_atendimento']}, "
                        f"Total: {upa_stats['total']}"
                    )

            except Exception as e:
                logging.error(f"Erro no loop de monitoramento: {e}")
                time.sleep(5)


def main():
    """Função principal"""
    simulator = UPASimulator()
    simulator._setup_logging()
    simulator.initialize()
    simulator.start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("\nInterrompido pelo usuário")
