#!/usr/bin/env python3

import json
import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from queue import PriorityQueue, Queue
from typing import Dict, List, Optional
from collections import defaultdict

class ClassificacaoTriagem(Enum):
    VERMELHO = (1, 5, "Emergencia - Atendimento em ate 5 minutos")
    AMARELO = (2, 15, "Muito urgente - Atendimento em ate 15 minutos")
    VERDE = (3, 60, "Urgente - Atendimento em ate 60 minutos")
    AZUL = (4, 120, "Pouco urgente - Atendimento em ate 120 minutos")

    def __init__(self, prioridade: int, max_wait_minutes: int, descricao: str):
        self.prioridade = prioridade
        self.max_wait_minutes = max_wait_minutes
        self.descricao = descricao

@dataclass
class Patient:
    patient_id: str
    upa_name: str
    bairro: str
    entrada_timestamp: datetime
    triagem_timestamp: Optional[datetime] = None
    classificacao: Optional[ClassificacaoTriagem] = None
    
    def __lt__(self, other):
        if not self.classificacao or not other.classificacao:
            return False
            
        if self.classificacao.prioridade != other.classificacao.prioridade:
            return self.classificacao.prioridade < other.classificacao.prioridade
            
        if self.triagem_timestamp and other.triagem_timestamp:
            return self.triagem_timestamp < other.triagem_timestamp
            
        return False

class UPASimulatorRealista:
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        self.filas_triagem: Dict[str, Queue] = {}
        self.filas_atendimento: Dict[str, PriorityQueue] = {}
        self.estatisticas: Dict[str, Dict] = {}
        self.locks: Dict[str, threading.Lock] = {}
        
        self.running = False
        self.threads = []
        self.pacientes_processados = 0

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _setup_logging(self):
        logging.basicConfig(
            level=getattr(logging, self.config["simulation"]["logging"]["level"]),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.config["simulation"]["logging"]["file"]),
                logging.StreamHandler()
            ]
        )

    def initialize(self):
        logging.info("INICIANDO SIMULACAO REALISTA - Protocolo de Manchester")
        
        for upa_name, upa_config in self.config["upas"].items():
            if upa_config["enabled"]:
                self.filas_triagem[upa_name] = Queue()
                self.filas_atendimento[upa_name] = PriorityQueue()
                self.locks[upa_name] = threading.Lock()
                self.estatisticas[upa_name] = {
                    "pacientes_processados": 0,
                    "alertas_manchester": 0,
                    "tempos_espera": defaultdict(list),
                    "violacoes_protocolo": defaultdict(int),
                    "max_fila_triagem": 0,
                    "max_fila_atendimento": 0
                }
                
        logging.info(f"{len(self.filas_triagem)} UPAs configuradas")
        logging.info(f"Fator aceleracao: {self.config['simulation']['real_time_factor']}x")
        logging.info("Configuracao realista: 1 triagista e 1 medico por UPA")

    def start(self):
        self.running = True
        
        for upa_name, upa_config in self.config["upas"].items():
            if upa_config["enabled"]:
                self._start_upa_threads(upa_name, upa_config)
        
        monitor_thread = threading.Thread(target=self._monitorar_simulacao, daemon=True)
        monitor_thread.start()
        self.threads.append(monitor_thread)
        
        logging.info("SIMULACAO REALISTA INICIADA - Pressione Ctrl+C para parar")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def _start_upa_threads(self, upa_name: str, upa_config: dict):
        capacidade = upa_config.get("capacidade", {"triagem": 1, "atendimento": 1})
        
        entrada_thread = threading.Thread(
            target=self._entrada_pacientes,
            args=(upa_name, upa_config),
            daemon=True,
            name=f"Entrada-{upa_name}"
        )
        entrada_thread.start()
        self.threads.append(entrada_thread)
        
        for i in range(capacidade["triagem"]):
            triagem_thread = threading.Thread(
                target=self._processar_triagem,
                args=(upa_name,),
                daemon=True,
                name=f"Triagem-{upa_name}-{i}"
            )
            triagem_thread.start()
            self.threads.append(triagem_thread)
        
        for i in range(capacidade["atendimento"]):
            atendimento_thread = threading.Thread(
                target=self._processar_atendimento, 
                args=(upa_name,),
                daemon=True,
                name=f"Atendimento-{upa_name}-{i}"
            )
            atendimento_thread.start()
            self.threads.append(atendimento_thread)

    def _entrada_pacientes(self, upa_name: str, upa_config: dict):
        taxa = upa_config["patient_flow"]["rate"]
        intervalo_base = 3600 / taxa
        real_time_factor = self.config["simulation"]["real_time_factor"]
        intervalo = intervalo_base / real_time_factor
        
        variacao = 0.3
        
        logging.info(f"[{upa_name}] Fluxo: {taxa}/hora = 1 paciente a cada {intervalo:.1f}s")
        
        while self.running:
            try:
                intervalo_variavel = intervalo * random.uniform(1 - variacao, 1 + variacao)
                
                paciente = Patient(
                    patient_id=str(uuid.uuid4())[:8],
                    upa_name=upa_name,
                    bairro=random.choice(upa_config["bairros"]),
                    entrada_timestamp=datetime.now()
                )
                
                with self.locks[upa_name]:
                    self.filas_triagem[upa_name].put(paciente)
                    fila_size = self.filas_triagem[upa_name].qsize()
                    if fila_size > self.estatisticas[upa_name]["max_fila_triagem"]:
                        self.estatisticas[upa_name]["max_fila_triagem"] = fila_size
                
                if fila_size % 10 == 0 and fila_size > 0:
                    logging.warning(f"[{upa_name}] FILA TRIAGEM CRESCENDO: {fila_size} pacientes")
                
                time.sleep(intervalo_variavel)
                
            except Exception as e:
                logging.error(f"Erro entrada {upa_name}: {e}")
                time.sleep(1)

    def _processar_triagem(self, upa_name: str):
        config_triagem = self.config["simulation"]["triagem_time_seconds"]
        real_time_factor = self.config["simulation"]["real_time_factor"]
        upa_config = self.config["upas"][upa_name]
        
        while self.running:
            try:
                with self.locks[upa_name]:
                    if self.filas_triagem[upa_name].empty():
                        time.sleep(0.1)
                        continue
                    paciente = self.filas_triagem[upa_name].get()
                
                tempo_triagem = random.uniform(config_triagem["min"], config_triagem["max"])
                time.sleep(tempo_triagem / real_time_factor)
                
                rand = random.random()
                cumulative = 0.0
                for classificacao_name, prob in upa_config["classificacao_distribution"].items():
                    cumulative += prob
                    if rand <= cumulative:
                        paciente.classificacao = ClassificacaoTriagem[classificacao_name]
                        break
                
                paciente.triagem_timestamp = datetime.now()
                
                with self.locks[upa_name]:
                    self.filas_atendimento[upa_name].put(paciente)
                    fila_atend_size = self.filas_atendimento[upa_name].qsize()
                    if fila_atend_size > self.estatisticas[upa_name]["max_fila_atendimento"]:
                        self.estatisticas[upa_name]["max_fila_atendimento"] = fila_atend_size
                
                logging.debug(f"[{upa_name}] Triagem: {paciente.patient_id} -> {paciente.classificacao.name}")
                
            except Exception as e:
                logging.error(f"Erro triagem {upa_name}: {e}")
                time.sleep(1)

    def _processar_atendimento(self, upa_name: str):
        config_atendimento = self.config["simulation"]["atendimento_time_seconds"]
        real_time_factor = self.config["simulation"]["real_time_factor"]
        
        while self.running:
            try:
                with self.locks[upa_name]:
                    if self.filas_atendimento[upa_name].empty():
                        time.sleep(0.1)
                        continue
                    paciente = self.filas_atendimento[upa_name].get()
                
                tempo_espera = (datetime.now() - paciente.triagem_timestamp).total_seconds() / 60
                max_wait = paciente.classificacao.max_wait_minutes
                
                if tempo_espera > max_wait:
                    self.estatisticas[upa_name]["alertas_manchester"] += 1
                    self.estatisticas[upa_name]["violacoes_protocolo"][paciente.classificacao.name] += 1
                    
                    logging.error(
                        f"[{upa_name}] VIOLACAO PROTOCOLO: {paciente.patient_id} "
                        f"({paciente.classificacao.name}) esperou {tempo_espera:.1f}min "
                        f"(MAXIMO: {max_wait}min) - EXCEDIDO: {tempo_espera - max_wait:.1f}min"
                    )
                
                config_class = config_atendimento[paciente.classificacao.name]
                tempo_atendimento = random.uniform(config_class["min"], config_class["max"])
                time.sleep(tempo_atendimento / real_time_factor)
                
                tempo_total = (datetime.now() - paciente.entrada_timestamp).total_seconds() / 60
                self.estatisticas[upa_name]["pacientes_processados"] += 1
                self.estatisticas[upa_name]["tempos_espera"][paciente.classificacao.name].append(tempo_espera)
                
                self.pacientes_processados += 1
                
                logging.info(
                    f"[{upa_name}] Atendido: {paciente.patient_id} [{paciente.classificacao.name}] "
                    f"(espera: {tempo_espera:.1f}min, total: {tempo_total:.1f}min)"
                )
                
            except Exception as e:
                logging.error(f"Erro atendimento {upa_name}: {e}")
                time.sleep(1)

    def _monitorar_simulacao(self):
        while self.running:
            time.sleep(30)
            
            total_pacientes = self.pacientes_processados
            logging.info("=" * 80)
            logging.info(f"RELATORIO MANCHESTER - {datetime.now().strftime('%H:%M:%S')}")
            logging.info(f"TOTAL DE PACIENTES PROCESSADOS: {total_pacientes}")
            
            for upa_name in self.config["upas"].keys():
                if not self.config["upas"][upa_name]["enabled"]:
                    continue
                    
                with self.locks[upa_name]:
                    fila_triagem = self.filas_triagem[upa_name].qsize()
                    fila_atendimento = self.filas_atendimento[upa_name].qsize()
                    stats = self.estatisticas[upa_name]
                
                logging.info(
                    f"[{upa_name}] Status - "
                    f"Triagem: {fila_triagem}, Atendimento: {fila_atendimento}, "
                    f"Processados: {stats['pacientes_processados']}, "
                    f"Alertas: {stats['alertas_manchester']}"
                )
                
                for classificacao in ClassificacaoTriagem:
                    nome_class = classificacao.name
                    tempos = stats["tempos_espera"][nome_class]
                    violacoes = stats["violacoes_protocolo"][nome_class]
                    max_wait = classificacao.max_wait_minutes
                    
                    if tempos:
                        tempo_medio = sum(tempos) / len(tempos)
                        percentual_violacao = (violacoes / len(tempos)) * 100 if tempos else 0
                        
                        status = "DENTRO" if tempo_medio <= max_wait else "FORA"
                        
                        logging.info(
                            f"[{upa_name}] {nome_class}: "
                            f"Media: {tempo_medio:.1f}min / Max: {max_wait}min {status} | "
                            f"Violacoes: {violacoes}/{len(tempos)} ({percentual_violacao:.1f}%)"
                        )
            
            logging.info("=" * 80)

    def stop(self):
        logging.info("Parando simulacao...")
        self.running = False
        
        for thread in self.threads:
            thread.join(timeout=5)
            
        self._gerar_relatorio_final()
        logging.info("Simulacao finalizada")

    def _gerar_relatorio_final(self):
        logging.info("=" * 80)
        logging.info("RELATORIO FINAL DA SIMULACAO")
        logging.info("=" * 80)
        
        for upa_name in self.config["upas"].keys():
            if not self.config["upas"][upa_name]["enabled"]:
                continue
                
            stats = self.estatisticas[upa_name]
            upa_config = self.config["upas"][upa_name]
            
            logging.info(f"UPA: {upa_name}")
            logging.info(f"  Taxa de entrada: {upa_config['patient_flow']['rate']} pacientes/hora")
            logging.info(f"  Capacidade: {upa_config['capacidade']['triagem']} triagista, {upa_config['capacidade']['atendimento']} medico")
            logging.info(f"  Pacientes processados: {stats['pacientes_processados']}")
            logging.info(f"  Maxima fila triagem: {stats['max_fila_triagem']}")
            logging.info(f"  Maxima fila atendimento: {stats['max_fila_atendimento']}")
            logging.info(f"  Total alertas Manchester: {stats['alertas_manchester']}")
            
            for classificacao in ClassificacaoTriagem:
                nome_class = classificacao.name
                tempos = stats["tempos_espera"][nome_class]
                violacoes = stats["violacoes_protocolo"][nome_class]
                max_wait = classificacao.max_wait_minutes
                
                if tempos:
                    tempo_medio = sum(tempos) / len(tempos)
                    tempo_max = max(tempos)
                    percentual_violacao = (violacoes / len(tempos)) * 100
                    
                    logging.info(f"  {nome_class}:")
                    logging.info(f"    Tempo medio de espera: {tempo_medio:.1f}min")
                    logging.info(f"    Tempo maximo de espera: {tempo_max:.1f}min") 
                    logging.info(f"    Limite Manchester: {max_wait}min")
                    logging.info(f"    Violacoes: {violacoes} ({percentual_violacao:.1f}%)")
                    
                    if percentual_violacao > 10:
                        logging.info(f"    ** ALERTA: Alta taxa de violacao do protocolo **")
            
            logging.info("-" * 40)

def main():
    simulator = UPASimulatorRealista("config.json")
    try:
        simulator.initialize()
        simulator.start()
    except KeyboardInterrupt:
        logging.info("Interrompido pelo usuario")
    except Exception as e:
        logging.error(f"Erro fatal: {e}", exc_info=True)
    finally:
        simulator.stop()

if __name__ == "__main__":
    main()