"""Lightweight web scraper for Inovar portal using direct API calls."""
import json
import logging
import base64
import uuid
import hmac
import hashlib
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# Import proxy support
try:
    from utils.webshare import Webshare
    PROXY_AVAILABLE = True
except ImportError:
    PROXY_AVAILABLE = False
    logger.warning("Webshare proxy module not available")


class InovarScraperLightweight:
    """Lightweight scraper for Inovar +AZ portal using direct API calls."""

    BASE_URL = "https://aevf.inovarmais.com/consulta"

    def __init__(self, username: str, password: str, login_url: str = None, home_url: str = None, use_proxy: bool = None):
        """
        Initialize the lightweight scraper.

        Args:
            username: Student process number (e.g., "21084")
            password: Password
            login_url: Not used (kept for compatibility)
            home_url: Not used (kept for compatibility)
            use_proxy: Whether to use Webshare proxy. If None, auto-detects (uses proxy in Azure, not locally)
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.jwt_token: Optional[str] = None
        self.aluno_id: Optional[int] = None
        self.matricula_id: Optional[int] = None
        self.tipo_ensino: int = 1  # Default: Regular teaching (1)
        self.proxy_manager: Optional[Webshare] = None

        # Auto-detect if we should use proxy (check if running in Azure)
        if use_proxy is None:
            use_proxy = os.getenv('WEBSITE_INSTANCE_ID') is not None  # Azure Function App indicator

        # Initialize proxy if needed
        if use_proxy and PROXY_AVAILABLE:
            try:
                logger.info("Initializing Webshare proxy...")
                self.proxy_manager = Webshare()
                proxy_dict = self.proxy_manager.get_proxy_dict()
                self.session.proxies.update(proxy_dict)
                logger.info(f"Proxy configured: {self.proxy_manager.current_proxy['host']}:{self.proxy_manager.current_proxy['port']}")
            except Exception as e:
                logger.error(f"CRITICAL: Failed to initialize proxy: {e}")
                logger.error(f"CRITICAL: Without proxy, Azure datacenter IPs will be blocked by Cloudflare!")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.proxy_manager = None

        # Set common headers to mimic real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Referer': f'{self.BASE_URL}/app/index.html'
        })

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close the session."""
        self.session.close()

    def _generate_session_id(self) -> str:
        """Generate a session ID (UUID format)."""
        return str(uuid.uuid4())

    def _encode_base64(self, text: str) -> str:
        """Encode text to base64."""
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')

    def _generate_festmani_token(self) -> str:
        """
        Generate x-festmani security token.

        This token is a daily HMAC-SHA256 hash of the current UTC date.
        JavaScript equivalent: TK() function in app.js
        """
        # Get current UTC date in YYYYMMDD format
        utc_date = datetime.utcnow().strftime("%Y%m%d")

        # Secret key (hardcoded in the portal's JavaScript)
        secret_key = "0c24b08e-d78b-4d53-96a6-68db2bf2611f"

        # Create HMAC-SHA256
        hmac_digest = hmac.new(
            secret_key.encode('utf-8'),
            utc_date.encode('utf-8'),
            hashlib.sha256
        ).digest()

        # Base64 encode
        token = base64.b64encode(hmac_digest).decode('utf-8')

        return token

    def login(self) -> bool:
        """
        Login to Inovar portal using the API.
        Automatically retries with different proxies if proxy connection fails.

        Returns:
            True if login successful, False otherwise
        """
        # Prepare login data (same for all attempts)
        session_id = self._generate_session_id()
        username_b64 = self._encode_base64(self.username)
        password_b64 = self._encode_base64(self.password)
        session_id_b64 = self._encode_base64(session_id)
        basic_auth = self._encode_base64(f"{self.username}:{self.password}")

        payload = {
            "username": username_b64,
            "password": password_b64,
            "sessionId": session_id_b64
        }

        url = f"{self.BASE_URL}/api/loginFU/"
        headers = {
            'Authorization': f'Basic {basic_auth}',
            'x-festmani': self._generate_festmani_token()
        }

        # Retry logic: try up to 3 times with different proxies if using proxy
        max_attempts = 3 if self.proxy_manager else 1

        for attempt in range(1, max_attempts + 1):
            try:
                if attempt > 1:
                    logger.info(f"Login attempt {attempt}/{max_attempts}...")
                else:
                    logger.info(f"Attempting login for user: {self.username}")

                response = self.session.post(url, json=payload, headers=headers, timeout=30)

                # Check response status
                if response.status_code != 200:
                    logger.error(f"Login failed with status {response.status_code}")
                    logger.error(f"Response headers: {dict(response.headers)}")
                    logger.error(f"Response text (first 500 chars): {response.text[:500]}")

                    # If using proxy and not the last attempt, rotate proxy and retry
                    if self.proxy_manager and attempt < max_attempts:
                        logger.warning("Rotating to a different proxy...")
                        new_proxy = self.proxy_manager.get_proxy_dict()
                        self.session.proxies.update(new_proxy)
                        logger.info(f"Switched to proxy: {self.proxy_manager.current_proxy['host']}:{self.proxy_manager.current_proxy['port']}")
                        continue
                    return False

                # Parse response
                data = response.json()
                logger.debug(f"Login response keys: {list(data.keys())}")

                # Extract JWT token from response (try both 'TokenLogin' and 'token' fields)
                token_login = data.get('TokenLogin') or data.get('token')
                if not token_login:
                    logger.error("No JWT token found in response!")
                    logger.debug(f"TokenLogin value: {data.get('TokenLogin')}")
                    logger.debug(f"token value: {data.get('token')}")

                    # If using proxy and not the last attempt, rotate proxy and retry
                    if self.proxy_manager and attempt < max_attempts:
                        logger.warning("Rotating to a different proxy...")
                        new_proxy = self.proxy_manager.get_proxy_dict()
                        self.session.proxies.update(new_proxy)
                        logger.info(f"Switched to proxy: {self.proxy_manager.current_proxy['host']}:{self.proxy_manager.current_proxy['port']}")
                        continue
                    return False

                # Success! Set JWT token
                self.jwt_token = token_login
                # Set Authorization header for all subsequent requests
                # Note: NO SPACE between "Bearer" and the token (portal quirk)
                self.session.headers['Authorization'] = f'Bearer{self.jwt_token}'
                logger.info(f"JWT token extracted (first 50 chars): {str(self.jwt_token)[:50]}...")

                # Extract student info
                aluno = data.get('Aluno', {})
                self.aluno_id = aluno.get('AlunoId')

                # Get current year's matricula (first in list is usually current)
                matriculas = data.get('Matriculas', [])
                if matriculas:
                    current_matricula = matriculas[0]  # First one is current year
                    self.matricula_id = current_matricula.get('MatriculaId')
                    self.tipo_ensino = current_matricula.get('TipoEnsino', 1)

                    logger.info(f"Login successful!")
                    logger.info(f"  Student: {aluno.get('Nome')}")
                    logger.info(f"  Aluno ID: {self.aluno_id}")
                    logger.info(f"  Matricula ID: {self.matricula_id}")
                    logger.info(f"  Tipo Ensino: {self.tipo_ensino}")
                else:
                    logger.error("No matriculas found in login response")

                    # If using proxy and not the last attempt, rotate proxy and retry
                    if self.proxy_manager and attempt < max_attempts:
                        logger.warning("Rotating to a different proxy...")
                        new_proxy = self.proxy_manager.get_proxy_dict()
                        self.session.proxies.update(new_proxy)
                        logger.info(f"Switched to proxy: {self.proxy_manager.current_proxy['host']}:{self.proxy_manager.current_proxy['port']}")
                        continue
                    return False

                return True

            except requests.exceptions.ProxyError as e:
                logger.error(f"Proxy error on attempt {attempt}: {e}")

                # If using proxy and not the last attempt, rotate proxy and retry
                if self.proxy_manager and attempt < max_attempts:
                    logger.warning("Rotating to a different proxy...")
                    new_proxy = self.proxy_manager.get_proxy_dict()
                    self.session.proxies.update(new_proxy)
                    logger.info(f"Switched to proxy: {self.proxy_manager.current_proxy['host']}:{self.proxy_manager.current_proxy['port']}")
                    continue

                logger.error(f"All proxy attempts failed")
                return False

            except requests.exceptions.RequestException as e:
                logger.error(f"Network error on attempt {attempt}: {e}")

                # If using proxy and not the last attempt, rotate proxy and retry
                if self.proxy_manager and attempt < max_attempts:
                    logger.warning("Rotating to a different proxy...")
                    new_proxy = self.proxy_manager.get_proxy_dict()
                    self.session.proxies.update(new_proxy)
                    logger.info(f"Switched to proxy: {self.proxy_manager.current_proxy['host']}:{self.proxy_manager.current_proxy['port']}")
                    continue

                logger.error(f"All attempts failed")
                return False

            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt}: {e}")

                # If using proxy and not the last attempt, rotate proxy and retry
                if self.proxy_manager and attempt < max_attempts:
                    logger.warning("Rotating to a different proxy...")
                    new_proxy = self.proxy_manager.get_proxy_dict()
                    self.session.proxies.update(new_proxy)
                    logger.info(f"Switched to proxy: {self.proxy_manager.current_proxy['host']}:{self.proxy_manager.current_proxy['port']}")
                    continue

                return False

        # If we get here, all attempts failed
        logger.error(f"Login failed after {max_attempts} retry attempts")
        logger.error(f"Proxy manager active: {self.proxy_manager is not None}")
        if self.proxy_manager:
            logger.error(f"Last proxy used: {self.proxy_manager.current_proxy}")
        return False

    def get_absences(self, week_number: int = 1) -> List[Dict[str, Any]]:
        """
        Get absences (faltas) from the API.

        Args:
            week_number: Not used (kept for compatibility)

        Returns:
            List of absence dictionaries
        """
        try:
            if not self.matricula_id:
                logger.error("No matricula_id available. Login first.")
                return []

            url = f"{self.BASE_URL}/api/faltas/{self.matricula_id}/{self.tipo_ensino}"
            logger.info(f"Fetching absences from: {url}")

            response = self.session.get(url, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to fetch absences: {response.status_code}")
                return []

            data = response.json()
            faltas = data.get('Faltas', [])

            logger.info(f"Found {len(faltas)} absences")

            # Convert to standardized format
            absences = []
            for falta in faltas:
                absence = {
                    "type": "absence",
                    "date": falta.get('DataDescricao', ''),  # DD-MM-YYYY format
                    "day_of_week": falta.get('DiaDaSemana', ''),
                    "time": falta.get('Hora', ''),
                    "subject": falta.get('Disciplina', ''),
                    "absence_type": falta.get('Tipo', ''),
                    "description": f"{falta.get('Tipo', '')} - {falta.get('Disciplina', '')} ({falta.get('Hora', '')})",
                    "raw": falta
                }
                absences.append(absence)
                logger.debug(f"Absence: {absence['date']} - {absence['subject']} - {absence['absence_type']}")

            return absences

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching absences: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching absences: {e}")
            return []

    def get_behavior_alerts(self) -> List[Dict[str, Any]]:
        """
        Get behavior alerts (avisos de comportamento) from the API.

        Returns:
            List of behavior alert dictionaries
        """
        try:
            if not self.matricula_id:
                logger.error("No matricula_id available. Login first.")
                return []

            url = f"{self.BASE_URL}/api/comportamento/{self.matricula_id}/{self.tipo_ensino}"
            logger.info(f"Fetching behavior alerts from: {url}")

            response = self.session.get(url, timeout=30)

            if response.status_code != 200:
                logger.error(f"Failed to fetch behavior alerts: {response.status_code}")
                return []

            data = response.json()
            comportamentos = data.get('Comportamentos', [])

            logger.info(f"Found {len(comportamentos)} behavior alerts")

            # Convert to standardized format
            alerts = []
            for comp in comportamentos:
                alert = {
                    "type": "behavior_alert",
                    "date": comp.get('DataPrettyPrint', ''),  # DD-MM-YYYY format
                    "time": comp.get('Tempo', ''),
                    "professor": comp.get('Professor', ''),
                    "grau": comp.get('Grau', ''),
                    "description": comp.get('Descricao', ''),
                    "full_description": f"[Grau {comp.get('Grau', '')}] {comp.get('Professor', '')} - {comp.get('Descricao', '')}",
                    "raw": comp
                }
                alerts.append(alert)
                logger.debug(f"Behavior alert: {alert['date']} - {alert['professor']} - Grau {alert['grau']}")

            return alerts

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching behavior alerts: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching behavior alerts: {e}")
            return []

    def scrape_all(self) -> Dict[str, Any]:
        """
        Perform complete scraping: login, fetch absences and alerts.

        Returns:
            Dictionary with results
        """
        results = {
            "absences": [],
            "behavior_alerts": [],
            "success": False,
            "error": None
        }

        try:
            # Login
            if not self.login():
                results["error"] = "Login failed"
                return results

            # Get absences
            results["absences"] = self.get_absences()

            # Get behavior alerts
            results["behavior_alerts"] = self.get_behavior_alerts()

            results["success"] = True
            logger.info(f"Scraping completed: {len(results['absences'])} absences, {len(results['behavior_alerts'])} alerts")

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            results["error"] = str(e)

        return results
