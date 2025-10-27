"""Cliente HTTP para comunicação com APIs"""
import logging
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class APIClient:
    """
    Cliente HTTP com retry automático e timeout
    Usado para comunicação com Gateway e Monitoring Services
    """

    def __init__(self, base_url: str, timeout: int = 10):
        """
        Args:
            base_url: URL base da API (ex: https://api.example.com)
            timeout: Timeout em segundos para requisições
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

        # Estratégia de retry com backoff exponencial
        retry_strategy = Retry(
            total=3,                                      # 3 tentativas
            backoff_factor=1,                             # 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],  # HTTP codes para retry
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def post(self, endpoint: str, data: dict) -> Optional[dict]:
        """
        Faz POST para endpoint

        Args:
            endpoint: Caminho do endpoint (ex: /api/v1/events)
            data: Dados JSON para enviar

        Returns:
            dict ou None se falhar
        """
        try:
            url = f"{self.base_url}{endpoint}"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; UPA-Simulator/1.0)",
                "Accept": "application/json"
            }
            response = self.session.post(
                url,
                json=data,
                timeout=self.timeout,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro ao fazer POST para {endpoint}: {e}")
            return None

    def get(self, endpoint: str) -> Optional[dict]:
        """
        Faz GET para endpoint

        Args:
            endpoint: Caminho do endpoint (ex: /api/v1/upas)

        Returns:
            dict ou None se falhar
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro ao fazer GET de {endpoint}: {e}")
            return None
