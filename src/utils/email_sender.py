"""
Email Sender - Envía alertas por email usando SMTP
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import sqlite3

logging.basicConfig(level=logging.INFO)


class EmailSender:
    """Envía emails de alertas y reportes"""

    def __init__(self):
        self.settings = self._load_settings()

    def _load_settings(self):
        """Carga configuración de email desde DB"""
        conn = sqlite3.connect('email_settings.db')
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_config (
                id INTEGER PRIMARY KEY,
                smtp_host TEXT DEFAULT 'smtp.gmail.com',
                smtp_port INTEGER DEFAULT 587,
                smtp_user TEXT,
                smtp_password TEXT,
                from_email TEXT,
                enabled BOOLEAN DEFAULT 0
            )
        ''')

        cursor.execute('SELECT * FROM email_config WHERE id = 1')
        result = cursor.fetchone()

        if not result:
            # Crear configuración por defecto
            cursor.execute('''
                INSERT INTO email_config (id, enabled)
                VALUES (1, 0)
            ''')
            conn.commit()
            result = cursor.fetchone()

        conn.close()

        if result:
            return {
                'smtp_host': result[1] or 'smtp.gmail.com',
                'smtp_port': result[2] or 587,
                'smtp_user': result[3],
                'smtp_password': result[4],
                'from_email': result[5],
                'enabled': bool(result[6])
            }

        return {'enabled': False}

    def send_alert_email(self, to_email, alert_data):
        """
        Envía alerta por email

        Args:
            to_email: Email destinatario
            alert_data: Datos de la alerta
        """
        if not self.settings.get('enabled'):
            logging.info("📧 Email deshabilitado en configuración")
            return False

        subject = f"🔔 {alert_data.get('severity', '').upper()}: {alert_data.get('alert_type', 'Alert')}"

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px;">
                    <h2 style="color: #333;">NOLIVOS FBA - Nueva Alerta</h2>

                    <div style="background: #f9f9f9; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0;">
                        <h3 style="margin: 0 0 10px 0; color: #4CAF50;">
                            {alert_data.get('message', '')}
                        </h3>
                        <p style="margin: 5px 0;"><strong>Producto:</strong> {alert_data.get('product_name', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>ASIN:</strong> {alert_data.get('asin', 'N/A')}</p>
                        <p style="margin: 5px 0;"><strong>Fecha:</strong> {alert_data.get('created_at', 'N/A')}</p>
                    </div>

                    <div style="text-align: center; margin-top: 30px;">
                        <a href="https://www.amazon.com/dp/{alert_data.get('asin', '')}"
                           style="background: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            Ver en Amazon
                        </a>
                    </div>

                    <p style="color: #999; font-size: 12px; margin-top: 30px; text-align: center;">
                        NOLIVOS FBA - Amazon Product Research Tool
                    </p>
                </div>
            </body>
        </html>
        """

        return self._send_email(to_email, subject, html_body)

    def send_daily_digest(self, to_email, opportunities, alerts):
        """Envía resumen diario"""
        if not self.settings.get('enabled'):
            return False

        from datetime import datetime

        subject = f"📊 Resumen Diario - {datetime.now().strftime('%Y-%m-%d')}"

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>📊 Resumen Diario - NOLIVOS FBA</h2>

                <h3>💰 Nuevas Oportunidades: {len(opportunities)}</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr style="background: #4CAF50; color: white;">
                        <th style="padding: 10px; border: 1px solid #ddd;">Producto</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">ROI</th>
                        <th style="padding: 10px; border: 1px solid #ddd;">Ganancia</th>
                    </tr>
        """

        for opp in opportunities[:10]:
            html_body += f"""
                    <tr>
                        <td style="padding: 10px; border: 1px solid #ddd;">{opp.get('product_name', '')[:50]}</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">{opp.get('roi_percent', 0):.1f}%</td>
                        <td style="padding: 10px; border: 1px solid #ddd;">${opp.get('net_profit', 0):.2f}</td>
                    </tr>
            """

        html_body += f"""
                </table>

                <h3 style="margin-top: 30px;">🔔 Alertas Importantes: {len(alerts)}</h3>
                <ul>
        """

        for alert in alerts[:10]:
            html_body += f"<li>{alert.get('message', '')}</li>"

        html_body += """
                </ul>

                <p style="text-align: center; margin-top: 30px;">
                    <a href="http://localhost:4994/opportunities" style="background: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px;">
                        Ver Dashboard
                    </a>
                </p>
            </body>
        </html>
        """

        return self._send_email(to_email, subject, html_body)

    def _send_email(self, to_email, subject, html_body):
        """Envía email usando SMTP"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.settings.get('from_email', 'noreply@hectorfba.com')
            msg['To'] = to_email

            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)

            # Conectar a SMTP
            server = smtplib.SMTP(
                self.settings['smtp_host'],
                self.settings['smtp_port']
            )
            server.starttls()
            server.login(
                self.settings['smtp_user'],
                self.settings['smtp_password']
            )

            server.send_message(msg)
            server.quit()

            logging.info(f"✅ Email enviado a {to_email}")
            return True

        except Exception as e:
            logging.error(f"❌ Error enviando email: {e}")
            return False

    @staticmethod
    def configure_email(smtp_host, smtp_port, smtp_user, smtp_password, from_email):
        """Configura credenciales de email"""
        conn = sqlite3.connect('email_settings.db')
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE email_config
            SET smtp_host = ?, smtp_port = ?, smtp_user = ?, smtp_password = ?, from_email = ?, enabled = 1
            WHERE id = 1
        ''', (smtp_host, smtp_port, smtp_user, smtp_password, from_email))

        conn.commit()
        conn.close()

        logging.info("✅ Configuración de email guardada")
