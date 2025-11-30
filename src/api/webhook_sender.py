"""
Webhook Sender - Envía eventos a n8n, Zapier, Make, etc.
"""
import requests
import sqlite3
import logging
import json
from datetime import datetime

logging.basicConfig(level=logging.INFO)


class WebhookSender:
    """Envía eventos a webhooks registrados"""

    def __init__(self, db_path='webhooks.db'):
        self.db_path = db_path

    def send_event(self, event_type, data):
        """
        Envía evento a todos los webhooks suscritos

        Args:
            event_type: Tipo de evento ('opportunity_found', 'price_alert', etc.)
            data: Datos del evento
        """
        webhooks = self._get_webhooks_for_event(event_type)

        if not webhooks:
            logging.info(f"No hay webhooks registrados para evento: {event_type}")
            return

        payload = {
            'event': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }

        for webhook in webhooks:
            self._send_to_webhook(webhook['url'], payload, webhook['id'])

    def _get_webhooks_for_event(self, event_type):
        """Obtiene webhooks suscritos a un evento"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM webhooks
                WHERE is_active = 1
            ''')

            all_webhooks = [dict(row) for row in cursor.fetchall()]

            # Filtrar por evento
            webhooks = []
            for wh in all_webhooks:
                events = wh.get('events', '').split(',')
                if event_type in events or '*' in events:
                    webhooks.append(wh)

            conn.close()
            return webhooks

        except Exception as e:
            logging.error(f"Error obteniendo webhooks: {e}")
            conn.close()
            return []

    def _send_to_webhook(self, url, payload, webhook_id):
        """Envía payload a un webhook específico"""
        try:
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code in [200, 201, 204]:
                logging.info(f"✅ Webhook enviado exitosamente a {url}")
                self._log_webhook_call(webhook_id, True, response.status_code)
            else:
                logging.warning(f"⚠️ Webhook respondió con {response.status_code}: {url}")
                self._log_webhook_call(webhook_id, False, response.status_code, response.text)

        except requests.exceptions.Timeout:
            logging.error(f"❌ Timeout enviando a webhook: {url}")
            self._log_webhook_call(webhook_id, False, 0, 'Timeout')

        except Exception as e:
            logging.error(f"❌ Error enviando a webhook {url}: {e}")
            self._log_webhook_call(webhook_id, False, 0, str(e))

    def _log_webhook_call(self, webhook_id, success, status_code, error=None):
        """Registra llamada al webhook"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS webhook_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                webhook_id INTEGER,
                success BOOLEAN,
                status_code INTEGER,
                error TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            INSERT INTO webhook_logs (webhook_id, success, status_code, error)
            VALUES (?, ?, ?, ?)
        ''', (webhook_id, success, status_code, error))

        conn.commit()
        conn.close()


# Funciones helper para enviar eventos comunes

def notify_opportunity_found(opportunity_data):
    """Notifica nueva oportunidad encontrada"""
    sender = WebhookSender()
    sender.send_event('opportunity_found', {
        'asin': opportunity_data.get('asin'),
        'product_name': opportunity_data.get('product_name'),
        'roi': opportunity_data.get('roi_percent'),
        'profit': opportunity_data.get('net_profit'),
        'amazon_price': opportunity_data.get('amazon_price'),
        'supplier_price': opportunity_data.get('supplier_price'),
        'supplier': opportunity_data.get('supplier_name'),
        'competitiveness': opportunity_data.get('competitiveness_level'),
        'url': f"https://www.amazon.com/dp/{opportunity_data.get('asin')}"
    })


def notify_price_alert(asin, product_name, old_price, new_price, source='supplier'):
    """Notifica cambio de precio"""
    sender = WebhookSender()
    sender.send_event('price_alert', {
        'asin': asin,
        'product_name': product_name,
        'source': source,
        'old_price': old_price,
        'new_price': new_price,
        'change_percent': ((old_price - new_price) / old_price * 100) if old_price > 0 else 0,
        'url': f"https://www.amazon.com/dp/{asin}"
    })


def notify_bsr_change(asin, product_name, old_bsr, new_bsr):
    """Notifica cambio importante en BSR"""
    sender = WebhookSender()
    sender.send_event('bsr_change', {
        'asin': asin,
        'product_name': product_name,
        'old_bsr': old_bsr,
        'new_bsr': new_bsr,
        'change': old_bsr - new_bsr,
        'trend': 'improving' if new_bsr < old_bsr else 'declining',
        'url': f"https://www.amazon.com/dp/{asin}"
    })


def notify_high_roi_alert(opportunity_data):
    """Notifica ROI alto (>50%)"""
    sender = WebhookSender()
    sender.send_event('high_roi_alert', {
        'asin': opportunity_data.get('asin'),
        'product_name': opportunity_data.get('product_name'),
        'roi': opportunity_data.get('roi_percent'),
        'profit': opportunity_data.get('net_profit'),
        'amazon_price': opportunity_data.get('amazon_price'),
        'supplier': opportunity_data.get('supplier_name'),
        'urgency': 'HIGH',
        'url': f"https://www.amazon.com/dp/{opportunity_data.get('asin')}"
    })
