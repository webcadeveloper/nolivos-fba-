"""
Telegram Bot - Envía alertas y comandos por Telegram
"""
import requests
import logging
import sqlite3

logging.basicConfig(level=logging.INFO)


class TelegramBot:
    """Bot de Telegram para notificaciones y comandos"""

    def __init__(self):
        self.config = self._load_config()
        self.bot_token = self.config.get('bot_token')
        self.enabled = self.config.get('enabled', False)

    def _load_config(self):
        """Carga configuración del bot"""
        conn = sqlite3.connect('telegram_config.db')
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS telegram_config (
                id INTEGER PRIMARY KEY,
                bot_token TEXT,
                chat_id TEXT,
                enabled BOOLEAN DEFAULT 0
            )
        ''')

        cursor.execute('SELECT * FROM telegram_config WHERE id = 1')
        result = cursor.fetchone()

        if not result:
            cursor.execute('INSERT INTO telegram_config (id, enabled) VALUES (1, 0)')
            conn.commit()

        conn.close()

        return {
            'bot_token': result[1] if result else None,
            'chat_id': result[2] if result else None,
            'enabled': bool(result[3]) if result else False
        }

    def send_message(self, message, chat_id=None):
        """Envía mensaje por Telegram"""
        if not self.enabled or not self.bot_token:
            logging.info("🤖 Telegram deshabilitado")
            return False

        chat_id = chat_id or self.config.get('chat_id')

        if not chat_id:
            logging.error("❌ Chat ID no configurado")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }

        try:
            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logging.info("✅ Mensaje Telegram enviado")
                return True
            else:
                logging.error(f"❌ Error Telegram: {response.text}")
                return False

        except Exception as e:
            logging.error(f"❌ Error enviando Telegram: {e}")
            return False

    def send_alert(self, alert_data):
        """Envía alerta formateada"""
        severity_emoji = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🔵'
        }

        emoji = severity_emoji.get(alert_data.get('severity', 'low'), '🔔')

        message = f"""
{emoji} <b>ALERTA {alert_data.get('severity', '').upper()}</b>

<b>{alert_data.get('message', '')}</b>

📦 Producto: {alert_data.get('product_name', 'N/A')[:50]}
🔖 ASIN: {alert_data.get('asin', 'N/A')}
📅 Fecha: {alert_data.get('created_at', 'N/A')}

🔗 <a href="https://www.amazon.com/dp/{alert_data.get('asin', '')}">Ver en Amazon</a>
        """

        return self.send_message(message)

    def send_opportunity(self, opportunity):
        """Envía oportunidad encontrada"""
        message = f"""
💰 <b>NUEVA OPORTUNIDAD</b>

📦 {opportunity.get('product_name', '')[:60]}

💵 Amazon: ${opportunity.get('amazon_price', 0):.2f}
🏭 Proveedor: ${opportunity.get('supplier_price', 0):.2f} ({opportunity.get('supplier_name', '')})

📊 <b>ROI: {opportunity.get('roi_percent', 0):.1f}%</b>
💰 <b>Ganancia: ${opportunity.get('net_profit', 0):.2f}</b>

{opportunity.get('competitiveness_level', '')}

🔗 <a href="https://www.amazon.com/dp/{opportunity.get('asin', '')}">Ver Producto</a>
        """

        return self.send_message(message)

    def send_daily_summary(self, stats):
        """Envía resumen diario"""
        message = f"""
📊 <b>RESUMEN DIARIO - NOLIVOS FBA</b>

💰 Oportunidades: {stats.get('total_opportunities', 0)}
📈 ROI Promedio: {stats.get('avg_roi', 0):.1f}%
💵 Ganancia Promedio: ${stats.get('avg_profit', 0):.2f}

🔔 Alertas: {stats.get('total_alerts', 0)}
🔴 Alta prioridad: {stats.get('high_priority', 0)}
🟡 Media prioridad: {stats.get('medium_priority', 0)}

🚀 <a href="http://localhost:4994/opportunities">Ver Dashboard</a>
        """

        return self.send_message(message)

    @staticmethod
    def configure_bot(bot_token, chat_id):
        """Configura bot de Telegram"""
        conn = sqlite3.connect('telegram_config.db')
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE telegram_config
            SET bot_token = ?, chat_id = ?, enabled = 1
            WHERE id = 1
        ''', (bot_token, chat_id))

        conn.commit()
        conn.close()

        logging.info("✅ Bot de Telegram configurado")

    @staticmethod
    def get_chat_id(bot_token):
        """Helper para obtener chat_id (usuario debe enviar mensaje al bot primero)"""
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

        try:
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get('ok') and data.get('result'):
                latest = data['result'][-1]
                chat_id = latest['message']['chat']['id']
                return chat_id
            else:
                return None

        except Exception as e:
            logging.error(f"Error obteniendo chat_id: {e}")
            return None
