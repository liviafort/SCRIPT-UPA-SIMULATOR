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

class ClassificacaoTriagem(Enum):
    VERMELHO = (1, 0, "Emergência - Atendimento imediato")
    AMARELO = (2, 15, "Muito urgente - Atendimento em 15min") 
    VERDE = (3, 60, "Urgente - Atendimento em 60min")
    AZUL = (4, 120, "Pouco urgente - Atendimento em 120min")

    def __init__(self, prioridade: int, target_minutes: int, descricao: str):
        self.prioridade = prioridade
        self.target_minutes = target_minutes
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
        """Comparação para PriorityQueue - Manchester protocol"""
        if not self.classificacao or not other.classificacao:
            return False
        return self.classificacao.prioridade < other.classificacao.prioridade

class UPASimulatorOtimizado:
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self._setup_logging()
        
        self.filas_triagem: Dict[str, Queue] = {}
        self.filas_atendimento: Dict[str, PriorityQueue] = {}
        self.estatisticas: Dict[str, Dict] = {}
        self.locks: Dict[str, threading.Lock] = {}
        
        self.running = False
        self.threads = []

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
        """Inicializa simulador com múltiplos recursos por UPA"""
        logging.info("Iniciando Simulação Otimizada - Protocolo de Manchester")
        
        for upa_name, upa_config in self.config["upas"].items():
            if upa_config["enabled"]:
                self.filas_triagem[upa_name] = Queue()
                self.filas_atendimento[upa_name] = PriorityQueue()
                self.locks[upa_name] = threading.Lock()
                self.estatisticas[upa_name] = {
                    "pacientes_processados": 0,
                    "tempo_medio_espera": 0,
                    "alertas_manchester": 0
                }
                
        logging.info(f"{len(self.filas_triagem)} UPAs configuradas")
        logging.info(f"Fator aceleração: {self.config['simulation']['real_time_factor']}x")

    def start(self):
        """Inicia simulação com processamento paralelo"""
        self.running = True
        
        for upa_name, upa_config in self.config["upas"].items():
            if upa_config["enabled"]:
                self._start_upa_threads(upa_name, upa_config)
        
        monitor_thread = threading.Thread(target=self._monitorar_simulacao, daemon=True)
        monitor_thread.start()
        self.threads.append(monitor_thread)
        
        logging.info("Simulação iniciada - Pressione Ctrl+C para parar")
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def _start_upa_threads(self, upa_name: str, upa_config: dict):
        """Inicia múltiplas threads para uma UPA"""
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
        """Gera entrada de pacientes otimizada"""
        taxa = upa_config["patient_flow"]["rate"]
        intervalo_base = 3600 / taxa  
        real_time_factor = self.config["simulation"]["real_time_factor"]
        intervalo = intervalo_base / real_time_factor
        
        logging.info(f"[{upa_name}] Taxa: {taxa}/hora = 1 paciente a cada {intervalo:.1f}s")
        
        while self.running:
            try:
                paciente = Patient(
                    patient_id=str(uuid.uuid4())[:8],
                    upa_name=upa_name,
                    bairro=random.choice(upa_config["bairros"]),
                    entrada_timestamp=datetime.now()
                )
                
                with self.locks[upa_name]:
                    self.filas_triagem[upa_name].put(paciente)
                    fila_size = self.filas_triagem[upa_name].qsize()
                
                if fila_size % 10 == 0: 
                    logging.info(f"[{upa_name}] 👥 Fila triagem: {fila_size} pacientes")
                
                time.sleep(intervalo)
                
            except Exception as e:
                logging.error(f"Erro entrada {upa_name}: {e}")
                time.sleep(1)

    def _processar_triagem(self, upa_name: str):
        """Processa triagem com múltiplos enfermeiros"""
        config_triagem = self.config["simulation"]["triagem_time_seconds"]
        real_time_factor = self.config["simulation"]["real_time_factor"]
        upa_config = self.config["upas"][upa_name]
        
        while self.running:
            try:
                with self.locks[upa_name]:
                    if self.filas_triagem[upa_name].empty():
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
                
                logging.debug(f"[{upa_name}] 🩺 Triagem: {paciente.patient_id} -> {paciente.classificacao.name}")
                
            except Exception as e:
                logging.error(f"Erro triagem {upa_name}: {e}")
                time.sleep(1)

    def _processar_atendimento(self, upa_name: str):
        """Processa atendimento com múltiplos médicos"""
        config_atendimento = self.config["simulation"]["atendimento_time_seconds"]
        real_time_factor = self.config["simulation"]["real_time_factor"]
        
        while self.running:
            try:
                with self.locks[upa_name]:
                    if self.filas_atendimento[upa_name].empty():
                        continue
                    paciente = self.filas_atendimento[upa_name].get()
                
                tempo_espera = (datetime.now() - paciente.triagem_timestamp).total_seconds() / 60
                max_wait = self.config["manchester_protocol"][paciente.classificacao.name]["max_wait_minutes"]
                
                if tempo_espera > max_wait:
                    self.estatisticas[upa_name]["alertas_manchester"] += 1
                    logging.warning(
                        f"[{upa_name}] ⚠️ ALERTA MANCHESTER: {paciente.patient_id} "
                        f"({paciente.classificacao.name}) esperou {tempo_espera:.1f}min "
                        f"(máx: {max_wait}min)"
                    )
                
                config_class = config_atendimento[paciente.classificacao.name]
                tempo_atendimento = random.uniform(config_class["min"], config_class["max"])
                time.sleep(tempo_atendimento / real_time_factor)
                
                tempo_total = (datetime.now() - paciente.entrada_timestamp).total_seconds() / 60
                self.estatisticas[upa_name]["pacientes_processados"] += 1
                
                logging.info(
                    f"[{upa_name}] Atendido: {paciente.patient_id} [{paciente.classificacao.name}] "
                    f"(espera: {tempo_espera:.1f}min, total: {tempo_total:.1f}min)"
                )
                
            except Exception as e:
                logging.error(f"Erro atendimento {upa_name}: {e}")
                time.sleep(1)

    def _monitorar_simulacao(self):
        """Monitoramento otimizado"""
        while self.running:
            time.sleep(30)
            
            for upa_name in self.config["upas"].keys():
                if not self.config["upas"][upa_name]["enabled"]:
                    continue
                    
                with self.locks[upa_name]:
                    fila_triagem = self.filas_triagem[upa_name].qsize()
                    fila_atendimento = self.filas_atendimento[upa_name].qsize()
                    stats = self.estatisticas[upa_name]
                
                logging.info(
                    f"[{upa_name}] 📈 Estatísticas - "
                    f"Triagem: {fila_triagem}, Atendimento: {fila_atendimento}, "
                    f"Processados: {stats['pacientes_processados']}, "
                    f"Alertas: {stats['alertas_manchester']}"
                )

    def stop(self):
        """Para a simulação"""
        logging.info("Parando simulação...")
        self.running = False
        for thread in self.threads:
            thread.join(timeout=5)
        logging.info("Simulação finalizada")

def main():
    simulator = UPASimulatorOtimizado("config.json")
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