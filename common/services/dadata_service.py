import logging
import requests
from django.conf import settings
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class DadataService:
    def __init__(self):
        self.auth_token = getattr(settings, "DADATA_AUTH_TOKEN", None)
        self.api_url = "https://suggestions.dadata.ru/"
        self.timeout = 1 / 20

        if not self.auth_token:
            logger.error("DADATA_AUTH_TOKEN не установлен в настройках")
            raise ValueError("DADATA_AUTH_TOKEN не установлен в настройках")

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {self.auth_token}"
        }
        return headers

    def suggest_addresses(self, query: str, count: int = 10) -> List[Dict]:
        if not query or not query.strip():
            return []

        url = f"{self.api_url.rstrip('/')}/suggestions/api/4_1/rs/suggest/address"

        payload = {
            "query": query.strip(),
            "count": min(count, 20),
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            suggestions = data.get("suggestions", [])

            logger.info(f"Получено {len(suggestions)} подсказок для запроса: {query}")
            return suggestions

        except requests.Timeout:
            logger.error(f"Таймаут при запросе к Dadata API для запроса: {query}")
            return []
        except requests.RequestException as e:
            logger.error(f"Ошибка при запросе к Dadata API: {e}")
            return []
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка при парсинге ответа Dadata API: {e}")
            return []

    def clean_address(self, address: str) -> Optional[Dict]:
        if not address or not address.strip():
            return None

        if not self.auth_token:
            logger.error("DADATA_AUTH_TOKEN не установлен в настройках")
            raise ValueError("DADATA_AUTH_TOKEN не установлен в настройках")

        url = f"{self.api_url.rstrip('/')}/api/v1/clean/address"

        try:
            response = requests.post(
                url,
                json=[address.strip()],
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            if data and len(data) > 0:
                return data[0]

            return None

        except requests.Timeout:
            logger.error(f"Таймаут при нормализации адреса: {address}")
            return None
        except requests.RequestException as e:
            logger.error(f"Ошибка при нормализации адреса: {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"Ошибка при парсинге ответа Dadata API: {e}")
            return None
