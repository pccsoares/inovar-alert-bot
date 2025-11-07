"""Email notification service using SMTP."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Email notification service."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_pass: str,
        smtp_from: str
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.smtp_from = smtp_from

    def send_alert_email(
        self,
        recipients: List[str],
        absences: List[Dict[str, Any]],
        behavior_alerts: List[Dict[str, Any]]
    ) -> bool:
        """Send alert email with new events."""
        if not recipients:
            logger.error("No recipients specified")
            return False

        if not absences and not behavior_alerts:
            logger.info("No new events to report, skipping email")
            return True

        try:
            # Create email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = self._get_subject(len(absences), len(behavior_alerts))
            msg['From'] = self.smtp_from
            msg['To'] = ', '.join(recipients)

            # Create HTML body
            html_body = self._create_html_body(absences, behavior_alerts)
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            # Send email
            logger.info(f"Sending email to {recipients}")
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)

            logger.info("Email sent successfully")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def _get_subject(self, absence_count: int, alert_count: int) -> str:
        """Generate email subject."""
        parts = []
        if absence_count > 0:
            parts.append(f"{absence_count} Nova(s) Falta(s)")
        if alert_count > 0:
            parts.append(f"{alert_count} Novo(s) Aviso(s)")

        if not parts:
            return "Inovar Alert - No New Events"

        return f"Inovar Alert - {' e '.join(parts)}"

    def _create_html_body(
        self,
        absences: List[Dict[str, Any]],
        behavior_alerts: List[Dict[str, Any]]
    ) -> str:
        """Create HTML email body."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #0066cc;
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            background-color: #f9f9f9;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 0 0 5px 5px;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .section-title {{
            color: #0066cc;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            border-bottom: 2px solid #0066cc;
            padding-bottom: 5px;
        }}
        .event {{
            background-color: white;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #ff9800;
            border-radius: 3px;
        }}
        .event-date {{
            font-weight: bold;
            color: #ff9800;
        }}
        .event-description {{
            margin-top: 5px;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 12px;
        }}
        .alert {{
            border-left-color: #f44336;
        }}
        .timestamp {{
            color: #999;
            font-size: 11px;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Inovar +AZ - Alerta de Faltas e Avisos</h1>
        </div>
        <div class="content">
"""

        # Add absences section
        if absences:
            html += """
            <div class="section">
                <div class="section-title">📅 Novas Faltas</div>
"""
            for absence in absences:
                date = absence.get('date', 'Data desconhecida')
                description = absence.get('description', 'Falta')
                subject = absence.get('subject', '')
                period = absence.get('period', '')

                details = []
                if subject:
                    details.append(f"Disciplina: {subject}")
                if period:
                    details.append(f"Período: {period}")

                details_str = " | ".join(details) if details else ""

                html += f"""
                <div class="event">
                    <div class="event-date">{date}</div>
                    <div class="event-description">{description}</div>
                    {f'<div class="timestamp">{details_str}</div>' if details_str else ''}
                </div>
"""
            html += """
            </div>
"""

        # Add behavior alerts section
        if behavior_alerts:
            html += """
            <div class="section">
                <div class="section-title">⚠️ Novos Avisos</div>
"""
            for alert in behavior_alerts:
                date = alert.get('date', 'Data desconhecida')
                description = alert.get('description', 'Aviso')

                html += f"""
                <div class="event alert">
                    <div class="event-date">{date}</div>
                    <div class="event-description">{description}</div>
                </div>
"""
            html += """
            </div>
"""

        # Add footer
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html += f"""
            <div class="footer">
                <p>Este é um email automático do sistema de monitorização Inovar +AZ</p>
                <p class="timestamp">Gerado em: {now}</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

        return html
