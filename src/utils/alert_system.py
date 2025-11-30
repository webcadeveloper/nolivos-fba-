"""
Alert System - Sistema de alertas para oportunidades de FBA
Notifica cuando hay cambios importantes: precio baja, BSR mejora, competencia baja, etc.
"""
import sqlite3
import logging
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)


class AlertSystem:
    """Sistema de alertas para oportunidades FBA"""

    def __init__(self, db_path='alerts.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Crea tabla de alertas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                product_name TEXT,
                alert_type TEXT NOT NULL,
                severity TEXT,  -- 'high', 'medium', 'low'
                message TEXT,
                data JSON,
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_asin_alerts
            ON alerts(asin, created_at DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_unread
            ON alerts(is_read, severity, created_at DESC)
        ''')

        # Tabla de configuración de alertas del usuario
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alert_settings (
                id INTEGER PRIMARY KEY,
                user_email TEXT,
                notify_email BOOLEAN DEFAULT 0,
                notify_browser BOOLEAN DEFAULT 1,

                -- Thresholds para alertas
                min_roi_alert REAL DEFAULT 30.0,
                min_profit_alert REAL DEFAULT 10.0,
                bsr_improvement_threshold INTEGER DEFAULT 1000,
                price_drop_threshold REAL DEFAULT 5.0,
                competition_decrease_threshold INTEGER DEFAULT 5
            )
        ''')

        conn.commit()
        conn.close()
        logging.info("Alert system database initialized")

    def create_alert(self, asin, product_name, alert_type, severity, message, data=None):
        """
        Crea una nueva alerta

        Args:
            asin: ASIN del producto
            product_name: Nombre del producto
            alert_type: tipo de alerta ('price_drop', 'bsr_improvement', 'high_roi', etc.)
            severity: 'high', 'medium', 'low'
            message: mensaje descriptivo
            data: datos adicionales en JSON
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO alerts
            (asin, product_name, alert_type, severity, message, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (asin, product_name, alert_type, severity, message, json.dumps(data) if data else None))

        conn.commit()
        conn.close()

        logging.info(f"🔔 ALERTA {severity.upper()}: {message}")

    def check_opportunity_alerts(self, opportunity_data):
        """
        Verifica si una oportunidad merece alerta

        Args:
            opportunity_data: dict con datos de oportunidad

        Returns:
            list de alertas generadas
        """
        alerts = []
        asin = opportunity_data.get('asin')
        product_name = opportunity_data.get('product_name', '')[:100]
        roi = opportunity_data.get('roi_percent', 0)
        profit = opportunity_data.get('net_profit', 0)

        # Alerta: ROI ALTO
        if roi >= 50:
            self.create_alert(
                asin, product_name,
                'high_roi',
                'high',
                f"🚀 ROI EXCELENTE: {roi:.1f}% - Ganancia: ${profit:.2f}",
                {'roi': roi, 'profit': profit}
            )
            alerts.append('high_roi')

        elif roi >= 30:
            self.create_alert(
                asin, product_name,
                'good_roi',
                'medium',
                f"💰 Buen ROI: {roi:.1f}% - Ganancia: ${profit:.2f}",
                {'roi': roi, 'profit': profit}
            )
            alerts.append('good_roi')

        # Alerta: GANANCIA ALTA
        if profit >= 15:
            self.create_alert(
                asin, product_name,
                'high_profit',
                'high',
                f"💵 Alta ganancia por unidad: ${profit:.2f}",
                {'profit': profit}
            )
            alerts.append('high_profit')

        return alerts

    def check_trend_alerts(self, trend_data):
        """
        Verifica alertas basadas en tendencias

        Args:
            trend_data: dict con análisis de tendencias

        Returns:
            list de alertas generadas
        """
        alerts = []
        asin = trend_data.get('asin')
        product_name = trend_data.get('product_name', '')[:100]
        bsr_change = trend_data.get('bsr_change_30d', 0)
        seller_change = trend_data.get('seller_change_30d', 0)

        # Alerta: BSR MEJORANDO RÁPIDO (demanda aumentando)
        if bsr_change > 1000:
            self.create_alert(
                asin, product_name,
                'bsr_improvement',
                'high',
                f"📈 DEMANDA CRECIENDO: BSR mejoró {bsr_change} posiciones",
                {'bsr_change': bsr_change}
            )
            alerts.append('bsr_improvement')

        # Alerta: COMPETENCIA BAJANDO
        if seller_change < -5:
            self.create_alert(
                asin, product_name,
                'competition_decrease',
                'medium',
                f"✅ Competencia bajando: {abs(seller_change)} sellers menos",
                {'seller_change': seller_change}
            )
            alerts.append('competition_decrease')

        # Alerta: COMPETENCIA AUMENTANDO RÁPIDO
        elif seller_change > 10:
            self.create_alert(
                asin, product_name,
                'competition_increase',
                'low',
                f"⚠️ Competencia aumentando: +{seller_change} sellers",
                {'seller_change': seller_change}
            )
            alerts.append('competition_increase')

        return alerts

    def check_price_alerts(self, asin, product_name, old_price, new_price, source='supplier'):
        """
        Detecta cambios significativos de precio

        Args:
            asin: ASIN del producto
            product_name: nombre del producto
            old_price: precio anterior
            new_price: precio nuevo
            source: 'supplier' o 'amazon'
        """
        if not old_price or not new_price:
            return

        price_change = old_price - new_price
        price_change_percent = (price_change / old_price * 100) if old_price > 0 else 0

        # Alerta: PRECIO BAJÓ
        if price_change_percent >= 10:  # Bajó 10% o más
            severity = 'high' if price_change_percent >= 20 else 'medium'

            self.create_alert(
                asin, product_name,
                f'{source}_price_drop',
                severity,
                f"💸 Precio {source} bajó {price_change_percent:.1f}%: ${old_price:.2f} → ${new_price:.2f}",
                {
                    'old_price': old_price,
                    'new_price': new_price,
                    'change_percent': price_change_percent,
                    'source': source
                }
            )

    def get_unread_alerts(self, limit=50):
        """Obtiene alertas no leídas"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM alerts
            WHERE is_read = 0
            ORDER BY
                CASE severity
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                created_at DESC
            LIMIT ?
        ''', (limit,))

        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return alerts

    def get_alerts_by_asin(self, asin, limit=20):
        """Obtiene alertas para un ASIN específico"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM alerts
            WHERE asin = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (asin, limit))

        alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return alerts

    def mark_as_read(self, alert_ids):
        """Marca alertas como leídas"""
        if not alert_ids:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(alert_ids))
        cursor.execute(f'''
            UPDATE alerts
            SET is_read = 1
            WHERE id IN ({placeholders})
        ''', alert_ids)

        conn.commit()
        conn.close()

    def get_alert_summary(self):
        """Obtiene resumen de alertas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                COUNT(*) as total_unread,
                SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high_priority,
                SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) as medium_priority,
                SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) as low_priority
            FROM alerts
            WHERE is_read = 0
        ''')

        row = cursor.fetchone()
        conn.close()

        return {
            'total_unread': row[0] if row[0] else 0,
            'high_priority': row[1] if row[1] else 0,
            'medium_priority': row[2] if row[2] else 0,
            'low_priority': row[3] if row[3] else 0
        }

    def send_email_alert(self, alert_data, recipient_email):
        """
        Envía alerta por email (placeholder - implementar con SMTP)

        Args:
            alert_data: datos de la alerta
            recipient_email: email del usuario
        """
        # TODO: Implementar con smtplib o servicio como SendGrid
        logging.info(f"📧 Email alert would be sent to {recipient_email}: {alert_data['message']}")

        # Ejemplo básico (no implementado):
        # import smtplib
        # from email.mime.text import MIMEText
        # ...
        pass

    def generate_daily_digest(self):
        """Genera resumen diario de alertas importantes"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM alerts
            WHERE date(created_at) = date('now')
            AND severity IN ('high', 'medium')
            ORDER BY severity, created_at DESC
        ''')

        today_alerts = [dict(row) for row in cursor.fetchall()]
        conn.close()

        if not today_alerts:
            return "No hay alertas importantes hoy."

        digest = f"📊 RESUMEN DIARIO - {datetime.now().strftime('%Y-%m-%d')}\n"
        digest += f"Total alertas: {len(today_alerts)}\n\n"

        for alert in today_alerts[:10]:  # Top 10
            digest += f"{alert['severity'].upper()}: {alert['message']}\n"

        return digest
