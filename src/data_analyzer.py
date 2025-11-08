#!/usr/bin/env python3
"""
Analisador de Dados UPA - Extrai parâmetros Poisson de dados reais
Baseado em Teoria das Filas (Queueing Theory)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Tuple
import json
from datetime import datetime


class UPADataAnalyzer:
    """
    Analisa dados históricos das UPAs usando Teoria das Filas.

    Processo Poisson:
    - λ(t) = taxa de chegadas variável por hora do dia
    - Baseado em % real de distribuição horária
    - Dados diários para estimar média
    """

    def __init__(self, data_folder: str):
        self.data_folder = Path(data_folder)
        self.upa_name = self.data_folder.name.replace('dados-', '').replace('-', ' ').title()

    def analyze_daily_arrivals(self) -> Tuple[float, float, int]:
        """
        Analisa atendimentos por dia (dados reais).

        Returns:
            (média_diária, desvio_padrão, total_dias)
        """
        try:
            # Procura arquivo de atendimentos por dia
            dia_files = list(self.data_folder.glob("atendimento-dia*.csv"))
            if not dia_files:
                print(f"[AVISO] Arquivo atendimento-dia*.csv nao encontrado")
                return (270.0, 50.0, 365)  # Default

            df = pd.read_csv(dia_files[0], skiprows=1)
            print(f"\nAnalisando {dia_files[0].name}...")

            # Coluna de atendimentos
            atendimentos = df.iloc[:, 1].dropna()

            media = atendimentos.mean()
            desvio = atendimentos.std()
            total_dias = len(atendimentos)

            print(f"Dados diarios:")
            print(f"  Total de dias: {total_dias}")
            print(f"  Media diaria: {media:.1f} pacientes/dia")
            print(f"  Desvio padrao: {desvio:.1f}")
            print(f"  Min/Max: {atendimentos.min():.0f} / {atendimentos.max():.0f}")

            return (float(media), float(desvio), int(total_dias))

        except Exception as e:
            print(f"Erro ao analisar dados diarios: {e}")
            return (270.0, 50.0, 365)

    def analyze_hourly_distribution(self) -> Dict[int, float]:
        """
        Analisa distribuição percentual por hora do dia.

        Returns:
            Dict[hora] = percentual (0.0 a 1.0)
        """
        try:
            hora_files = list(self.data_folder.glob("atendimento-hora*.csv"))
            if not hora_files:
                print(f"[AVISO] Arquivo atendimento-hora*.csv nao encontrado")
                return {}

            df = pd.read_csv(hora_files[0], skiprows=2)
            print(f"\nAnalisando {hora_files[0].name}...")

            hourly_pct = {}

            for idx, row in df.iterrows():
                try:
                    periodo = str(row.iloc[0])
                    if 'H -' in periodo or 'H-' in periodo:
                        hour = int(periodo.split('H')[0].strip())

                        # Pega % do total (última coluna)
                        pct_str = str(row.iloc[3]).replace('%', '').replace(',', '.')
                        pct = float(pct_str) / 100.0

                        hourly_pct[hour] = pct

                except (ValueError, AttributeError, IndexError):
                    continue

            if len(hourly_pct) != 24:
                print(f"[AVISO] Esperado 24 horas, encontrado {len(hourly_pct)}")

            # Normaliza para somar 1.0
            total = sum(hourly_pct.values())
            if total > 0:
                hourly_pct = {h: p/total for h, p in hourly_pct.items()}

            return hourly_pct

        except Exception as e:
            print(f"Erro ao analisar distribuicao horaria: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def calculate_poisson_rates(self) -> Dict[int, float]:
        """
        Calcula taxa λ(t) para cada hora usando Teoria das Filas.

        λ(t) = taxa de chegadas (pacientes/hora) no tempo t

        Formula:
            λ(hora) = media_diaria * percentual(hora)

        Returns:
            Dict[hora] = λ (pacientes/hora)
        """
        media_diaria, _, _ = self.analyze_daily_arrivals()
        hourly_pct = self.analyze_hourly_distribution()

        if not hourly_pct:
            print("[AVISO] Usando distribuicao padrao")
            # Distribuição padrão baseada em padrão de UPA
            hourly_pct = {
                0: 0.01, 1: 0.007, 2: 0.0055, 3: 0.0046, 4: 0.0047, 5: 0.0089,
                6: 0.024, 7: 0.0563, 8: 0.0771, 9: 0.083, 10: 0.0756, 11: 0.0625,
                12: 0.0562, 13: 0.0707, 14: 0.076, 15: 0.068, 16: 0.0571, 17: 0.0485,
                18: 0.0512, 19: 0.0486, 20: 0.0383, 21: 0.0293, 22: 0.0213, 23: 0.0151
            }

        # Calcula λ(t) para cada hora
        lambda_rates = {}
        for hour in range(24):
            pct = hourly_pct.get(hour, 1.0/24)
            # λ(hora) = pacientes/dia * % desta hora = pacientes/hora
            lambda_rates[hour] = media_diaria * pct

        print(f"\nTaxas Poisson lambda(t):")
        print(f"  Media diaria: {media_diaria:.1f} pacientes/dia")

        # Mostra top 5 horas de pico
        top_hours = sorted(lambda_rates.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\nHorarios de pico:")
        for hour, rate in top_hours:
            pct = hourly_pct.get(hour, 0) * 100
            intervalo_medio = 60.0 / rate if rate > 0 else 0
            print(f"  {hour}h: lambda={rate:.1f} pac/h ({pct:.1f}%), intervalo medio={intervalo_medio:.1f} min")

        return lambda_rates

    def analyze_classification_distribution(self) -> Dict[str, float]:
        """Analisa distribuição de classificações Manchester"""
        try:
            class_files = list(self.data_folder.glob("classificacao-dia*.csv"))
            if not class_files:
                print(f"[AVISO] Arquivo classificacao-dia*.csv nao encontrado")
                return self._default_classification()

            df = pd.read_csv(class_files[0], skiprows=1)
            print(f"\nAnalisando {class_files[0].name}...")

            # Soma total por classificação
            manchester_map = {
                'vermelho': 'VERMELHO', 'vermelhã': 'VERMELHO',
                'laranja': 'LARANJA',
                'amarelo': 'AMARELO', 'amarela': 'AMARELO',
                'verde': 'VERDE',
                'azul': 'AZUL'
            }

            distribution = {}

            # Processa cada linha (cada dia)
            for col_idx in range(1, len(df.columns)):
                col_name = str(df.columns[col_idx]).lower()

                # Identifica classificação
                class_name = None
                for key, value in manchester_map.items():
                    if key in col_name:
                        class_name = value
                        break

                if class_name:
                    total = df.iloc[:, col_idx].sum()
                    distribution[class_name] = distribution.get(class_name, 0) + total

            # Normaliza
            total = sum(distribution.values())
            if total > 0:
                distribution = {k: v/total for k, v in distribution.items()}
            else:
                return self._default_classification()

            return distribution

        except Exception as e:
            print(f"Erro ao analisar classificacoes: {e}")
            return self._default_classification()

    def _default_classification(self) -> Dict[str, float]:
        """Distribuição padrão de classificações (Campina Grande - 4 níveis sem LARANJA)"""
        return {
            'VERDE': 0.50,
            'AMARELO': 0.34,
            'VERMELHO': 0.10,
            'AZUL': 0.06
        }

    def analyze_service_times(self) -> Dict[str, Tuple[float, float]]:
        """
        Tempos de atendimento baseados no protocolo de Manchester.
        Campina Grande usa 4 níveis (sem LARANJA).

        Returns:
            Dict[classificacao] = (tempo_min, tempo_max) em minutos
        """
        service_times = {
            'VERMELHO': (5, 15),    # Emergência - Atendimento imediato
            'AMARELO': (20, 60),    # Muito urgente - Até 60 minutos
            'VERDE': (30, 90),      # Urgente - Até 120 minutos
            'AZUL': (20, 60)        # Pouco urgente - Até 240 minutos
        }
        return service_times

    def generate_simulation_config(self) -> Dict:
        """Gera configuração completa para simulação"""

        print(f"\n{'='*70}")
        print(f"ANALISE POISSON - {self.upa_name}")
        print(f"{'='*70}")

        lambda_rates = self.calculate_poisson_rates()
        classification_dist = self.analyze_classification_distribution()
        service_times = self.analyze_service_times()

        media_diaria, desvio, total_dias = self.analyze_daily_arrivals()

        config = {
            'upa_name': self.upa_name,
            'hourly_arrival_rates': lambda_rates,
            'classification_distribution': classification_dist,
            'service_times_minutes': service_times,
            'summary': {
                'avg_daily_arrivals': media_diaria,
                'std_daily_arrivals': desvio,
                'total_days_analyzed': total_dias,
                'peak_hour': max(lambda_rates.items(), key=lambda x: x[1])[0] if lambda_rates else 0,
                'peak_rate': max(lambda_rates.values()) if lambda_rates else 0
            }
        }

        print(f"\n{'='*70}")
        print(f"RESUMO - {self.upa_name}")
        print(f"{'='*70}")
        print(f"Media diaria: {config['summary']['avg_daily_arrivals']:.1f} pacientes")
        print(f"Desvio padrao: {config['summary']['std_daily_arrivals']:.1f}")
        print(f"Horario de pico: {config['summary']['peak_hour']}h")
        print(f"Taxa de pico: {config['summary']['peak_rate']:.1f} pac/h")

        if classification_dist:
            print(f"\nDistribuicao de classificacoes:")
            for class_name in ['VERMELHO', 'AMARELO', 'VERDE', 'AZUL']:
                prob = classification_dist.get(class_name, 0)
                if prob > 0:
                    print(f"  {class_name}: {prob*100:.1f}%")

        return config


def analyze_all_upas(base_path: str = "."):
    """Analisa todas as pastas de dados disponíveis"""
    base = Path(base_path)
    configs = {}

    data_folders = [f for f in base.iterdir() if f.is_dir() and f.name.startswith('dados-')]

    print(f"Encontradas {len(data_folders)} pastas de dados\n")

    for folder in data_folders:
        analyzer = UPADataAnalyzer(str(folder))
        config = analyzer.generate_simulation_config()
        configs[config['upa_name']] = config

    # Salva configurações
    output_file = base / 'simulation_params.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"Configuracoes salvas em: {output_file}")
    print(f"{'='*70}")

    return configs


if __name__ == "__main__":
    configs = analyze_all_upas()
