#!/usr/bin/env python3

import json
import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from logging.handlers import RotatingFileHandler
from queue import PriorityQueue
from typing import Dict, List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ClassificacaoTriagem(Enum):
    VERMELHO = (1, 0, "Emergência - Atendimento imediato")
    AMARELO = (2, 60, "Muito urgente - Atendimento em até 60 minutos")
    VERDE = (3, 120, "Urgente - Atendimento em até 120 minutos")
    AZUL = (4, 240, "Pouco urgente - Atendimento em até 240 minutos")

    def __init__(self, prioridade: int, max_wait_minutes: int, descricao: str):
        self.prioridade = prioridade
        self.max_wait_minutes = max_wait_minutes
        self.descricao = descricao


class PatientStatus(Enum):
    AGUARDANDO_TRIAGEM = "AGUARDANDO_TRIAGEM"
    AGUARDANDO_ATENDIMENTO = "AGUARDANDO_ATENDIMENTO"
    EM_ATENDIMENTO = "EM_ATENDIMENTO"
    FINALIZADO = "FINALIZADO"


@dataclass
class Patient:
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
        if self.classificacao and other.classificacao:
            return self.classificacao.prioridade < other.classificacao.prioridade
        return False


@dataclass
class UPAConfig:
    name: str
    uuid: str
    enabled: bool
    flow_mode: str
    flow_rate: float
    bairros: List[str]
    classificacao_distribution: Dict[str, float]


class APIClient:

    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def post(self, endpoint: str, data: dict) -> Optional[dict]:
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.post(
                url,
                json=data,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro ao fazer POST para {endpoint}: {e}")
            return None

    def get(self, endpoint: str) -> Optional[dict]:
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro ao fazer GET de {endpoint}: {e}")
            return None


class UPASimulator:
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.monitoring_client = APIClient(self.config["monitoring_service"]["base_url"])
        self.gateway_client = APIClient(self.config["gateway_service"]["base_url"])

        self.upas: Dict[str, UPAConfig] = {}
        self.fila_triagem: Dict[str, PriorityQueue] = {}  # PRIORIZADA - Protocolo de Manchester desde entrada
        self.fila_atendimento: Dict[str, PriorityQueue] = {}  # PRIORIZADA - Atendimento médico
        self.active_patients: Dict[str, Patient] = {}

        # Locks para thread safety
        self.fila_triagem_locks: Dict[str, threading.Lock] = {}
        self.fila_atendimento_locks: Dict[str, threading.Lock] = {}
        self.active_patients_lock = threading.Lock()

        self.running = False
        self.threads: List[threading.Thread] = []

        self._setup_logging()

    def _load_config(self, config_path: str) -> dict:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar configuração: {e}")
            raise

    def _setup_logging(self):
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
        logging.info("=" * 80)
        logging.info("Iniciando UPA Simulator - Protocolo de Manchester")
        logging.info("=" * 80)

        self._fetch_upas()

        for upa_name in self.upas.keys():
            self.fila_triagem[upa_name] = PriorityQueue()  # Priorizada desde a entrada
            self.fila_atendimento[upa_name] = PriorityQueue()  # Priorizada para atendimento
            self.fila_triagem_locks[upa_name] = threading.Lock()
            self.fila_atendimento_locks[upa_name] = threading.Lock()

        logging.info(f"Simulador inicializado com {len(self.upas)} UPA(s)")
        logging.info("Protocolo de Manchester: Filas priorizadas por classificação de risco")
        for upa_name, upa_config in self.upas.items():
            logging.info(f"  - {upa_name}: {upa_config.flow_rate} pacientes/{upa_config.flow_mode}")

    def _fetch_upas(self):
        logging.info("Buscando UPAs da API...")

        endpoint = self.config["gateway_service"]["endpoints"]["upas"]
        response = self.gateway_client.get(endpoint)

        if not response or "data" not in response:
            logging.error("Falha ao buscar UPAs da API. Usando configuração local.")
            self._use_mock_upas()
            return

        upas_api = response["data"]
        logging.info(f"Encontradas {len(upas_api)} UPA(s) na API")

        for upa_data in upas_api:
            upa_name = upa_data["name"]

            if upa_name in self.config["upas"] and self.config["upas"][upa_name]["enabled"]:
                upa_local_config = self.config["upas"][upa_name]

                self.upas[upa_name] = UPAConfig(
                    name=upa_name,
                    uuid=upa_data["id"],
                    enabled=True,
                    flow_mode=upa_local_config["patient_flow"]["mode"],
                    flow_rate=upa_local_config["patient_flow"]["rate"],
                    bairros=upa_local_config["bairros"],
                    classificacao_distribution=upa_local_config["classificacao_distribution"]
                )

                logging.info(f"UPA configurada: {upa_name} (UUID: {upa_data['id']})")

    def _use_mock_upas(self):
        logging.warning("Usando UUIDs mockados para UPAs")

        for upa_name, upa_config in self.config["upas"].items():
            if upa_config["enabled"]:
                self.upas[upa_name] = UPAConfig(
                    name=upa_name,
                    uuid=str(uuid.uuid4()),
                    enabled=True,
                    flow_mode=upa_config["patient_flow"]["mode"],
                    flow_rate=upa_config["patient_flow"]["rate"],
                    bairros=upa_config["bairros"],
                    classificacao_distribution=upa_config["classificacao_distribution"]
                )

    def start(self):
        self.running = True

        for upa_name in self.upas.keys():
            thread = threading.Thread(
                target=self._patient_entry_loop,
                args=(upa_name,),
                name=f"Entry-{upa_name}",
                daemon=True
            )
            thread.start()
            self.threads.append(thread)

        triagem_thread = threading.Thread(
            target=self._triagem_processing_loop,
            name="Triagem-Processor",
            daemon=True
        )
        triagem_thread.start()
        self.threads.append(triagem_thread)

        atendimento_thread = threading.Thread(
            target=self._atendimento_processing_loop,
            name="Atendimento-Processor",
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

    def _patient_entry_loop(self, upa_name: str):
        """Loop de geração de entradas de pacientes para uma UPA"""
        upa_config = self.upas[upa_name]

        if upa_config.flow_mode == "per_minute":
            interval = 60.0 / upa_config.flow_rate
        elif upa_config.flow_mode == "per_hour":
            interval = 3600.0 / upa_config.flow_rate
        elif upa_config.flow_mode == "per_day":
            interval = 86400.0 / upa_config.flow_rate
        else:
            interval = 300

        real_time_factor = self.config["simulation"]["real_time_factor"]
        interval = interval / real_time_factor

        logging.info(f"[{upa_name}] Entrada de pacientes: 1 a cada {interval:.1f}s")

        while self.running:
            try:
                patient = self._create_patient(upa_config)

                self._register_entrada(patient)

                # Adiciona à fila de triagem PRIORIZADA (Protocolo de Manchester desde entrada)
                with self.fila_triagem_locks[upa_name]:
                    self.fila_triagem[upa_name].put(patient)
                    fila_size = self.fila_triagem[upa_name].qsize()

                with self.active_patients_lock:
                    self.active_patients[patient.patient_id] = patient

                logging.info(
                    f"[{upa_name}] 🚪 Paciente {patient.patient_id[:8]} entrou "
                    f"[Pré-classificação: {patient.classificacao.name}] "
                    f"(Bairro: {patient.bairro}, Fila triagem priorizada: {fila_size})"
                )

                time.sleep(interval)

            except Exception as e:
                logging.error(f"Erro no loop de entrada [{upa_name}]: {e}")
                time.sleep(5)

    def _create_patient(self, upa_config: UPAConfig) -> Patient:
        """
        Cria paciente com pré-classificação visual/sintomas relatados
        (como ocorre na recepção das UPAs reais)
        """
        # Pré-classificação baseada em sintomas relatados na entrada
        pre_classificacao = self._assign_classificacao(upa_config.classificacao_distribution)

        return Patient(
            patient_id=str(uuid.uuid4()),
            upa_id=upa_config.uuid,
            upa_name=upa_config.name,
            bairro=random.choice(upa_config.bairros),
            status=PatientStatus.AGUARDANDO_TRIAGEM,
            classificacao=pre_classificacao,  # Já entra com classificação preliminar
            entrada_timestamp=datetime.now()
        )

    def _register_entrada(self, patient: Patient):
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

    def _triagem_processing_loop(self):
        """
        Loop de processamento de triagem - PRIORIZADO por classificação
        Pacientes mais graves (pré-classificados na entrada) são triados primeiro
        """
        triagem_config = self.config["simulation"]["triagem_time_seconds"]
        real_time_factor = self.config["simulation"]["real_time_factor"]

        while self.running:
            try:
                for upa_name in self.upas.keys():
                    fila = self.fila_triagem[upa_name]

                    # Verifica se há pacientes na fila
                    if fila.empty():
                        continue

                    # Remove paciente da fila PRIORIZADA (maior prioridade primeiro)
                    with self.fila_triagem_locks[upa_name]:
                        if fila.empty():  # Double-check após lock
                            continue
                        patient = fila.get()

                    # Tempo de triagem pode ser menor para casos críticos
                    classificacao_inicial = patient.classificacao.name
                    triagem_time = random.randint(
                        triagem_config["min"],
                        triagem_config["max"]
                    ) / real_time_factor

                    logging.info(
                        f"[{upa_name}] 🩺 Iniciando triagem detalhada do paciente {patient.patient_id[:8]} "
                        f"[Pré-classificação: {classificacao_inicial}] "
                        f"(tempo estimado: {triagem_time:.0f}s)"
                    )

                    time.sleep(triagem_time)

                    # Confirma ou ajusta classificação de Manchester após avaliação detalhada
                    # (85% mantém, 15% pode mudar após exame mais detalhado)
                    if random.random() > 0.15:
                        # Mantém classificação inicial
                        pass
                    else:
                        # Reclassifica após avaliação detalhada
                        patient.classificacao = self._assign_classificacao(
                            self.upas[upa_name].classificacao_distribution
                        )

                    patient.triagem_timestamp = datetime.now()
                    patient.status = PatientStatus.AGUARDANDO_ATENDIMENTO

                    self._register_triagem(patient)

                    # Adiciona à fila de atendimento (PRIORIZADA por classificação final)
                    with self.fila_atendimento_locks[upa_name]:
                        self.fila_atendimento[upa_name].put(patient)

                    status_msg = "confirmada" if classificacao_inicial == patient.classificacao.name else f"RECLASSIFICADA: {classificacao_inicial} → {patient.classificacao.name}"

                    logging.info(
                        f"[{upa_name}] ✓ Paciente {patient.patient_id[:8]} triado: "
                        f"{patient.classificacao.name} (prioridade {patient.classificacao.prioridade}) - {status_msg}"
                    )

                time.sleep(1)

            except Exception as e:
                logging.error(f"Erro no loop de triagem: {e}")
                time.sleep(5)

    def _assign_classificacao(self, distribution: Dict[str, float]) -> ClassificacaoTriagem:
        """Atribui classificação de Manchester baseada em distribuição de probabilidade"""
        rand = random.random()
        cumulative = 0.0

        for classificacao_name, probability in distribution.items():
            cumulative += probability
            if rand <= cumulative:
                return ClassificacaoTriagem[classificacao_name]

        return ClassificacaoTriagem.VERDE

    def _register_triagem(self, patient: Patient):
        """Registra evento de triagem no serviço de monitoramento"""
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

    def _atendimento_processing_loop(self):
        """Loop de processamento de atendimento - PRIORIZADO (Protocolo de Manchester)"""
        atendimento_config = self.config["simulation"]["atendimento_time_seconds"]
        real_time_factor = self.config["simulation"]["real_time_factor"]

        while self.running:
            try:
                for upa_name in self.upas.keys():
                    fila = self.fila_atendimento[upa_name]

                    if fila.empty():
                        continue

                    # Remove paciente da fila priorizada (maior prioridade primeiro)
                    with self.fila_atendimento_locks[upa_name]:
                        if fila.empty():  # Double-check após lock
                            continue
                        patient = fila.get()

                    wait_time = (datetime.now() - patient.triagem_timestamp).total_seconds() / 60
                    max_wait = patient.classificacao.max_wait_minutes

                    # Alerta se excedeu tempo máximo de espera
                    if wait_time > max_wait and max_wait > 0:
                        logging.warning(
                            f"[{upa_name}] ⚠️  ALERTA PROTOCOLO MANCHESTER: Paciente {patient.patient_id[:8]} "
                            f"({patient.classificacao.name}) aguardou {wait_time:.1f} min "
                            f"(máximo permitido: {max_wait} min) - TEMPO EXCEDIDO!"
                        )

                    atend_config = atendimento_config[patient.classificacao.name]
                    atendimento_time = random.randint(
                        atend_config["min"],
                        atend_config["max"]
                    ) / real_time_factor

                    logging.info(
                        f"[{upa_name}] 🏥 Iniciando atendimento do paciente {patient.patient_id[:8]} "
                        f"[{patient.classificacao.name} - Prioridade {patient.classificacao.prioridade}] "
                        f"(tempo estimado: {atendimento_time:.0f}s, aguardou: {wait_time:.1f}min)"
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
                        f"[{upa_name}] ✅ Paciente {patient.patient_id[:8]} finalizado "
                        f"[{patient.classificacao.name}] (tempo total: {total_time:.1f} min)"
                    )

                time.sleep(1)

            except Exception as e:
                logging.error(f"Erro no loop de atendimento: {e}")
                time.sleep(5)

    def _register_atendimento(self, patient: Patient):
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
        """Loop de monitoramento e estatísticas"""
        while self.running:
            try:
                time.sleep(60)

                stats = {
                    "timestamp": datetime.now().isoformat(),
                    "upas": {}
                }

                for upa_name in self.upas.keys():
                    with self.fila_triagem_locks[upa_name]:
                        fila_triagem_size = self.fila_triagem[upa_name].qsize()

                    with self.fila_atendimento_locks[upa_name]:
                        fila_atendimento_size = self.fila_atendimento[upa_name].qsize()

                    stats["upas"][upa_name] = {
                        "fila_triagem": fila_triagem_size,
                        "fila_atendimento": fila_atendimento_size,
                        "total": fila_triagem_size + fila_atendimento_size
                    }

                total_active = sum(s["total"] for s in stats["upas"].values())

                logging.info("=" * 80)
                logging.info(f"📊 ESTATÍSTICAS - {datetime.now().strftime('%H:%M:%S')}")
                logging.info(f"Total de pacientes ativos: {total_active}")

                for upa_name, upa_stats in stats["upas"].items():
                    logging.info(
                        f"  [{upa_name}] "
                        f"Aguardando Triagem (PRIORIZADA): {upa_stats['fila_triagem']}, "
                        f"Aguardando Atendimento (PRIORIZADA): {upa_stats['fila_atendimento']}, "
                        f"Total: {upa_stats['total']}"
                    )

                logging.info("=" * 80)

            except Exception as e:
                logging.error(f"Erro no loop de monitoramento: {e}")
                time.sleep(5)


def main():
    """Função principal"""
    simulator = UPASimulator(config_path="config.json")

    try:
        simulator.initialize()
        simulator.start()
    except KeyboardInterrupt:
        logging.info("\nInterrompido pelo usuário")
    except Exception as e:
        logging.error(f"Erro fatal: {e}", exc_info=True)
    finally:
        simulator.stop()


if __name__ == "__main__":
    main()