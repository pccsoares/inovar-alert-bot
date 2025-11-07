"""Lightweight web scraper for Inovar portal using direct API calls."""
import json
import logging
import base64
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


class InovarScraperLightweight:
    """Lightweight scraper for Inovar +AZ portal using direct API calls."""

    BASE_URL = "https://aevf.inovarmais.com/consulta"

    def __init__(self, username: str, password: str, login_url: str = None, home_url: str = None):
        """
        Initialize the lightweight scraper.

        Args:
            username: Student process number (e.g., "21084")
            password: Password
            login_url: Not used (kept for compatibility)
            home_url: Not used (kept for compatibility)
        """
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.jwt_token: Optional[str] = None
        self.aluno_id: Optional[int] = None
        self.matricula_id: Optional[int] = None
        self.tipo_ensino: int = 1  # Default: Regular teaching (1)

        # Set common headers to mimic real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json;charset=UTF-8',
            'Referer': f'{self.BASE_URL}/app/index.html',
            'sec-ch-ua': '"Not=A?Brand";v="24", "Chromium";v="140"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Origin': f'{self.BASE_URL}',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty'
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

    def login(self) -> bool:
        """
        Login to Inovar portal using the API.

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Generate session ID
            session_id = self._generate_session_id()

            # Encode credentials
            username_b64 = self._encode_base64(self.username)
            password_b64 = self._encode_base64(self.password)
            session_id_b64 = self._encode_base64(session_id)

            # Prepare Basic Auth header
            basic_auth = self._encode_base64(f"{self.username}:{self.password}")

            # Prepare login payload
            payload = {
                "username": username_b64,
                "password": password_b64,
                "sessionId": session_id_b64
            }

            # Make login request
            logger.info(f"Attempting login for user: {self.username}")
            url = f"{self.BASE_URL}/api/loginFU/"

            headers = {
                'Authorization': f'Basic {basic_auth}',
                # Note: x-festmani appears to be a security token
                # Using a captured value - may need to be dynamically generated in future
                'x-festmani': 'BOEVWPDJeXR53H99PvF/X7noUsWl4ajpSDiNAk6QeYU='
            }

            response = self.session.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code != 200:
                logger.error(f"Login failed with status {response.status_code}: {response.text}")
                return False

            # Parse response
            data = response.json()
            logger.debug(f"Login response keys: {list(data.keys())}")

            # Extract JWT token from response (try both 'TokenLogin' and 'token' fields)
            token_login = data.get('TokenLogin') or data.get('token')
            if token_login:
                self.jwt_token = token_login
                # Set Authorization header for all subsequent requests
                # Note: NO SPACE between "Bearer" and the token (portal quirk)
                self.session.headers['Authorization'] = f'Bearer{self.jwt_token}'
                logger.info(f"JWT token extracted (first 50 chars): {str(self.jwt_token)[:50]}...")
            else:
                logger.error("No JWT token found in response!")
                logger.debug(f"TokenLogin value: {data.get('TokenLogin')}")
                logger.debug(f"token value: {data.get('token')}")
                return False

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
                return False

            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during login: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during login: {e}")
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
