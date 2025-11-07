"""Web scraper for Inovar portal using Playwright."""
import json
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime

from playwright.sync_api import sync_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError
import requests

logger = logging.getLogger(__name__)


class InovarScraper:
    """Scraper for Inovar +AZ portal."""

    def __init__(self, username: str, password: str, login_url: str, home_url: str):
        self.username = username
        self.password = password
        self.login_url = login_url
        self.home_url = home_url
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.student_id: Optional[str] = None
        self.cookies: Optional[Dict[str, str]] = None

    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_browser()

    def start_browser(self):
        """Start Playwright browser."""
        logger.info("Starting browser...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        logger.info("Browser started successfully")

    def close_browser(self):
        """Close browser and cleanup."""
        if self.page:
            self.page.close()
        if self.browser:
            self.browser.close()
        if hasattr(self, 'playwright'):
            self.playwright.stop()
        logger.info("Browser closed")

    def login(self) -> bool:
        """Login to Inovar portal."""
        try:
            logger.info(f"Navigating to login page: {self.login_url}")
            self.page.goto(self.login_url, wait_until="networkidle", timeout=30000)

            # Wait for login form
            logger.info("Waiting for login form...")
            self.page.wait_for_timeout(3000)  # Give page time to fully load

            # Find username input (try multiple selectors)
            username_selectors = [
                "input#username",
                "input[name='username']",
                "input[name='user']",
                "input[ng-model*='username' i]",
                "input[ng-model*='user' i]",
                "input[placeholder*='utilizador' i]",
                "input[placeholder*='user' i]",
                "input[placeholder*='nome' i]",
                "input[type='text']:visible",
                "input[type='number']:visible",
                "input:not([type='password']):visible:first"
            ]

            username_input = None
            for selector in username_selectors:
                try:
                    inputs = self.page.query_selector_all(selector)
                    # Filter for visible inputs only
                    for inp in inputs:
                        if inp.is_visible():
                            username_input = inp
                            logger.info(f"Found username input with selector: {selector}")
                            break
                    if username_input:
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not username_input:
                logger.error("Could not find username input field")
                # Log all inputs for debugging
                all_inputs = self.page.query_selector_all("input")
                logger.error(f"Found {len(all_inputs)} input fields on page")
                for i, inp in enumerate(all_inputs[:5]):  # Log first 5
                    logger.error(f"  Input {i}: type={inp.get_attribute('type')}, id={inp.get_attribute('id')}, name={inp.get_attribute('name')}")
                return False

            # Find password input
            password_selectors = [
                "input#password",
                "input[name='password']",
                "input[name='senha']",
                "input[type='password']",
                "input[ng-model*='password' i]",
                "input[ng-model*='senha' i]",
                "input[placeholder*='password' i]",
                "input[placeholder*='senha' i]",
                "input[placeholder*='palavra' i]"
            ]

            password_input = None
            for selector in password_selectors:
                try:
                    inputs = self.page.query_selector_all(selector)
                    # Filter for visible inputs only
                    for inp in inputs:
                        if inp.is_visible():
                            password_input = inp
                            logger.info(f"Found password input with selector: {selector}")
                            break
                    if password_input:
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not password_input:
                logger.error("Could not find password input field")
                return False

            # Fill in credentials
            logger.info(f"Filling in credentials for user: {self.username}")
            username_input.click()  # Focus first
            self.page.wait_for_timeout(500)
            username_input.fill(self.username)
            self.page.wait_for_timeout(500)

            password_input.click()  # Focus first
            self.page.wait_for_timeout(500)
            password_input.fill(self.password)
            self.page.wait_for_timeout(1000)

            # Find and click submit button
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Entrar')",
                "button:has-text('Login')",
                "button:has-text('Iniciar')",
                "a:has-text('Entrar')",
                "button.btn-primary",
                "button.submit",
                "a.btn-primary"
            ]

            submit_button = None
            for selector in submit_selectors:
                try:
                    buttons = self.page.query_selector_all(selector)
                    # Filter for visible buttons only
                    for btn in buttons:
                        if btn.is_visible():
                            submit_button = btn
                            logger.info(f"Found submit button with selector: {selector}")
                            break
                    if submit_button:
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not submit_button:
                logger.error("Could not find submit button")
                # Try pressing Enter as fallback
                logger.info("Trying Enter key as fallback...")
                password_input.press("Enter")
            else:
                # Click submit and wait for navigation
                logger.info("Clicking submit button...")
                submit_button.click()

            # Wait for navigation with longer timeout
            logger.info("Waiting for login response...")
            self.page.wait_for_timeout(5000)  # Wait 5 seconds for response

            try:
                self.page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeoutError:
                logger.warning("Timeout waiting for networkidle, continuing anyway...")

            # Check if login was successful by checking URL or page content
            current_url = self.page.url
            logger.info(f"After login, current URL: {current_url}")

            if "login" in current_url.lower():
                # Check for error messages
                error_text = ""
                try:
                    error_selectors = [".error", ".alert-danger", ".alert", "[class*='error']"]
                    for sel in error_selectors:
                        errors = self.page.query_selector_all(sel)
                        for err in errors:
                            if err.is_visible():
                                error_text += err.inner_text() + " "
                except:
                    pass

                logger.error(f"Login failed - still on login page. Error: {error_text or 'No error message found'}")
                return False

            # Store cookies for API requests
            self.cookies = {}
            for cookie in self.page.context.cookies():
                self.cookies[cookie['name']] = cookie['value']

            logger.info("Login successful!")
            return True

        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout during login: {e}")
            return False
        except Exception as e:
            logger.error(f"Error during login: {e}")
            return False

    def navigate_to_home(self) -> bool:
        """Navigate to home page and extract student ID."""
        try:
            logger.info(f"Navigating to home page: {self.home_url}")
            self.page.goto(self.home_url, wait_until="networkidle", timeout=30000)

            # Wait for page to load
            self.page.wait_for_timeout(3000)

            # Try to extract student ID from various sources
            # 1. From URL parameters
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")

            # 2. From page content/JavaScript variables
            student_id = self.page.evaluate("""() => {
                // Try to find student ID in common places
                if (window.studentId) return window.studentId;
                if (window.alunoId) return window.alunoId;
                if (localStorage.getItem('studentId')) return localStorage.getItem('studentId');
                if (sessionStorage.getItem('studentId')) return sessionStorage.getItem('studentId');
                return null;
            }""")

            if student_id:
                self.student_id = str(student_id)
                logger.info(f"Extracted student ID: {self.student_id}")
                return True

            # 3. Try to extract from network requests by intercepting API calls
            logger.info("Could not extract student ID from page, will try to intercept API calls")

            # Listen for API calls that might contain student ID
            intercepted_id = None

            def handle_response(response):
                nonlocal intercepted_id
                if '/api/agenda/semana/' in response.url:
                    # Extract student ID from URL like: /api/agenda/semana/84796/1
                    match = re.search(r'/api/agenda/semana/(\d+)/', response.url)
                    if match:
                        intercepted_id = match.group(1)
                        logger.info(f"Intercepted student ID from API call: {intercepted_id}")

            self.page.on("response", handle_response)

            # Trigger some navigation or refresh to generate API calls
            self.page.reload(wait_until="networkidle", timeout=30000)
            self.page.wait_for_timeout(3000)

            if intercepted_id:
                self.student_id = intercepted_id
                logger.info(f"Successfully extracted student ID: {self.student_id}")
                return True

            logger.error("Could not extract student ID from any source")
            return False

        except Exception as e:
            logger.error(f"Error navigating to home page: {e}")
            return False

    def get_absences(self, week_number: int = 1) -> List[Dict[str, Any]]:
        """Get absences from the Faltas table on home page."""
        try:
            absences = []

            # Faltas should be visible on the current page (home)
            logger.info("Extracting absences from Faltas table on home page...")

            # Wait a bit for dynamic content to load
            self.page.wait_for_timeout(2000)

            # Look for table rows in the Faltas section
            # The table structure is: Data | Dia da semana | Hora | Disciplina | Tipo
            table_selectors = [
                "table tbody tr",
                "table tr",
                ".table tbody tr",
                ".table tr"
            ]

            rows_found = []
            for selector in table_selectors:
                try:
                    rows = self.page.query_selector_all(selector)
                    if rows and len(rows) > 0:
                        rows_found = rows
                        logger.info(f"Found {len(rows)} table rows with selector: {selector}")
                        break
                except:
                    continue

            if not rows_found:
                logger.warning("No table rows found for absences")
                return []

            # Parse each row
            for row in rows_found:
                try:
                    # Get all cells in the row
                    cells = row.query_selector_all("td")
                    if len(cells) < 4:  # Need at least date, time, subject, type
                        continue

                    # Extract cell text
                    cell_texts = [cell.inner_text().strip() for cell in cells]

                    # Filter out empty rows or header rows
                    if not any(cell_texts) or "Data" in cell_texts[0]:
                        continue

                    # Parse the row data
                    # Expected: Data | Dia da semana | Hora | Disciplina | Tipo
                    date = cell_texts[0] if len(cell_texts) > 0 else ""
                    day_of_week = cell_texts[1] if len(cell_texts) > 1 else ""
                    time = cell_texts[2] if len(cell_texts) > 2 else ""
                    subject = cell_texts[3] if len(cell_texts) > 3 else ""
                    absence_type = cell_texts[4] if len(cell_texts) > 4 else ""

                    # Only add if we have a valid date (DD-MM-YYYY format)
                    if date and len(date) >= 10 and '-' in date:
                        # Additional validation: check if it looks like a date
                        date_parts = date.split('-')
                        if len(date_parts) == 3 and date_parts[0].isdigit() and date_parts[2].isdigit():
                            absence = {
                                "type": "absence",
                                "date": date,
                                "day_of_week": day_of_week,
                                "time": time,
                                "subject": subject,
                                "absence_type": absence_type.strip(),
                                "description": f"{absence_type} - {subject} ({time})"
                            }
                            absences.append(absence)
                            logger.info(f"Parsed absence: {date} - {subject} - {absence_type}")

                except Exception as e:
                    logger.debug(f"Error parsing table row: {e}")
                    continue

            logger.info(f"Found {len(absences)} absences total")
            return absences

        except Exception as e:
            logger.error(f"Error fetching absences: {e}")
            return []

    def get_behavior_alerts(self) -> List[Dict[str, Any]]:
        """Get behavior alerts from the Comportamento page."""
        try:
            alerts = []

            # Navigate to comportamento page
            comportamento_url = "https://aevf.inovarmais.com/consulta/app/index.html#/comportamento"
            logger.info(f"Navigating to comportamento page: {comportamento_url}")
            self.page.goto(comportamento_url, wait_until="networkidle", timeout=30000)

            # Wait for dynamic content to load
            self.page.wait_for_timeout(3000)

            # Look for table rows
            table_selectors = [
                "table tbody tr",
                "table tr",
                ".table tbody tr",
                ".table tr"
            ]

            rows_found = []
            for selector in table_selectors:
                try:
                    rows = self.page.query_selector_all(selector)
                    if rows and len(rows) > 0:
                        rows_found = rows
                        logger.info(f"Found {len(rows)} behavior table rows with selector: {selector}")
                        break
                except:
                    continue

            if not rows_found:
                logger.warning("No table rows found for behavior alerts")
                return []

            # Parse each row
            # Expected structure: Data (with time) | Professor | Comportamento (with Grau and description)
            for row in rows_found:
                try:
                    # Get all cells in the row
                    cells = row.query_selector_all("td")
                    if len(cells) < 3:  # Need at least date, professor, comportamento
                        continue

                    # Extract cell text
                    cell_texts = [cell.inner_text().strip() for cell in cells]

                    # Filter out empty rows or header rows
                    if not any(cell_texts) or "Data" in cell_texts[0]:
                        continue

                    # Parse the row data
                    # Cell 0: Date (and maybe time on separate line)
                    # Cell 1: Professor name (subject)
                    # Cell 2: Grau and description
                    date_cell = cell_texts[0] if len(cell_texts) > 0 else ""
                    professor_cell = cell_texts[1] if len(cell_texts) > 1 else ""
                    behavior_cell = cell_texts[2] if len(cell_texts) > 2 else ""

                    # Parse date (might be multi-line with time)
                    date_lines = date_cell.split('\n')
                    date = date_lines[0].strip() if date_lines else ""
                    time = date_lines[1].strip() if len(date_lines) > 1 else ""

                    # Parse professor (might include subject in parentheses)
                    professor = professor_cell.strip()

                    # Parse behavior (contains "Grau: X" and description)
                    grau = ""
                    description = behavior_cell
                    if "Grau:" in behavior_cell:
                        parts = behavior_cell.split("Grau:")
                        if len(parts) > 1:
                            grau_and_rest = parts[1].strip()
                            grau_lines = grau_and_rest.split('\n')
                            grau = grau_lines[0].strip() if grau_lines else ""
                            description = '\n'.join(grau_lines[1:]).strip() if len(grau_lines) > 1 else ""

                    # Only add if we have at least a date
                    if date and len(date) >= 8:  # Date format: DD-MM-YYYY
                        alert = {
                            "type": "behavior_alert",
                            "date": date,
                            "time": time,
                            "professor": professor,
                            "grau": grau,
                            "description": description,
                            "full_description": f"[Grau {grau}] {professor} - {description}" if grau else f"{professor} - {description}"
                        }
                        alerts.append(alert)
                        logger.info(f"Parsed behavior alert: {date} - {professor} - Grau {grau}")

                except Exception as e:
                    logger.debug(f"Error parsing behavior row: {e}")
                    continue

            logger.info(f"Found {len(alerts)} behavior alerts")
            return alerts

        except Exception as e:
            logger.error(f"Error fetching behavior alerts: {e}")
            return []

    def _parse_absences(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse absences from API response."""
        absences = []

        # The API structure may vary, so we'll try to handle different formats
        # Common patterns: data.absences, data.faltas, data.events, or just a list

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try common keys
            items = data.get('faltas') or data.get('absences') or data.get('events') or data.get('items') or []
        else:
            logger.warning(f"Unexpected API response type: {type(data)}")
            return absences

        for item in items:
            if isinstance(item, dict):
                # Extract absence information
                absence = {
                    "type": "absence",
                    "date": item.get("data") or item.get("date") or "unknown",
                    "description": item.get("descricao") or item.get("description") or "Falta",
                    "subject": item.get("disciplina") or item.get("subject"),
                    "period": item.get("periodo") or item.get("period"),
                    "raw": item
                }
                absences.append(absence)

        return absences

    def scrape_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """Perform complete scraping: login, navigate, fetch absences and alerts."""
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

            # Navigate to home and extract student ID
            if not self.navigate_to_home():
                results["error"] = "Failed to extract student ID"
                return results

            # Get absences FIRST (from Faltas table on home page)
            results["absences"] = self.get_absences()

            # Then get behavior alerts (navigates to comportamento page)
            results["behavior_alerts"] = self.get_behavior_alerts()

            results["success"] = True
            logger.info(f"Scraping completed: {len(results['absences'])} absences, {len(results['behavior_alerts'])} alerts")

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            results["error"] = str(e)

        return results
