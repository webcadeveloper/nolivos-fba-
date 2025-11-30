"""
Stock Monitor - Tracker de disponibilidad de stock con alertas
Detecta cambios: In Stock → Out of Stock, stock bajo, etc.
"""
import sqlite3
import logging
import re
from datetime import datetime, timedelta
import sys
import os

# Añadir path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.scrapers.product_info import ProductInfoScraper
from src.utils.alert_system import AlertSystem
from src.api.n8n_webhooks import N8NWebhookManager

logging.basicConfig(level=logging.INFO)


class StockMonitor:
    """Monitorea disponibilidad de stock para productos Amazon"""

    def __init__(self, db_path='stock_tracking.db'):
        self.db_path = db_path
        self.alert_system = AlertSystem()
        self.webhook_manager = N8NWebhookManager()
        self.init_database()

    def init_database(self):
        """Crea tablas para tracking de stock"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabla de historial de stock
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                status TEXT NOT NULL,  -- 'In Stock', 'Out of Stock', 'Low Stock'
                quantity INTEGER,  -- Cantidad disponible (si visible)
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                date DATE DEFAULT (date('now'))
            )
        ''')

        # Tabla de productos monitoreados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracked_stock (
                asin TEXT PRIMARY KEY,
                product_name TEXT,
                last_checked TIMESTAMP,
                current_status TEXT,
                current_quantity INTEGER,
                low_stock_threshold INTEGER DEFAULT 10,
                is_monitored BOOLEAN DEFAULT 1
            )
        ''')

        # Índices para búsquedas rápidas
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_stock_asin_date
            ON stock_history(asin, date DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_stock_timestamp
            ON stock_history(timestamp DESC)
        ''')

        conn.commit()
        conn.close()
        logging.info("Stock Monitor database initialized")

    def check_stock_availability(self, asin, product_name=None):
        """
        Verifica disponibilidad de stock de un producto

        Args:
            asin: ASIN del producto
            product_name: Nombre del producto (opcional)

        Returns:
            dict con status, quantity, y metadata
        """
        try:
            # Scrape información del producto
            scraper = ProductInfoScraper(asin)
            soup = scraper.get_soup(scraper.product_url)

            if not soup:
                logging.warning(f"No se pudo obtener HTML para {asin}")
                return None

            # Extraer estado de disponibilidad
            status = self._extract_availability_status(soup)
            quantity = self._extract_quantity(soup, status)

            # Determinar si es "Low Stock"
            if status == 'In Stock' and quantity and quantity < 10:
                status = 'Low Stock'

            # Guardar en histórico
            self._save_stock_snapshot(asin, status, quantity, product_name)

            # Verificar cambios y disparar alertas
            self._check_stock_changes(asin, status, quantity, product_name)

            return {
                'asin': asin,
                'status': status,
                'quantity': quantity,
                'timestamp': datetime.now().isoformat(),
                'product_name': product_name
            }

        except Exception as e:
            logging.error(f"Error checking stock for {asin}: {e}")
            return None

    def _extract_availability_status(self, soup):
        """Extrae el estado de disponibilidad de la página"""
        try:
            # Buscar div de disponibilidad
            availability = soup.find('div', {'id': 'availability'})
            if availability:
                avail_text = availability.text.strip().lower()

                if 'in stock' in avail_text:
                    # Verificar si menciona cantidad
                    if 'only' in avail_text or 'left' in avail_text:
                        return 'Low Stock'
                    return 'In Stock'
                elif 'out of stock' in avail_text:
                    return 'Out of Stock'
                elif 'temporarily out' in avail_text:
                    return 'Out of Stock'
                elif 'available' in avail_text:
                    return 'In Stock'
                else:
                    return 'Unknown'

            # Buscar en otros lugares comunes
            stock_indicators = [
                soup.find('span', {'id': 'availability_feature_div'}),
                soup.find('div', {'class': re.compile(r'availability', re.I)}),
                soup.find('span', string=re.compile(r'in stock|out of stock', re.I))
            ]

            for indicator in stock_indicators:
                if indicator:
                    text = indicator.text.strip().lower()
                    if 'in stock' in text:
                        return 'In Stock'
                    elif 'out of stock' in text:
                        return 'Out of Stock'

            # Fallback: si hay precio, asumir que está disponible
            price = soup.find('span', {'class': 'a-price-whole'})
            if price:
                return 'In Stock'

            return 'Unknown'

        except Exception as e:
            logging.error(f"Error extracting availability status: {e}")
            return 'Unknown'

    def _extract_quantity(self, soup, status):
        """Extrae cantidad disponible si es visible"""
        try:
            if status == 'Out of Stock':
                return 0

            # Buscar indicadores de cantidad
            availability = soup.find('div', {'id': 'availability'})
            if availability:
                text = availability.text.strip()

                # Patrones comunes: "Only 5 left", "5 in stock", etc.
                patterns = [
                    r'only\s+(\d+)\s+left',
                    r'(\d+)\s+left',
                    r'(\d+)\s+in\s+stock',
                    r'only\s+(\d+)',
                ]

                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        qty = int(match.group(1))
                        return qty

            # Si no se puede extraer, retornar None
            return None

        except Exception as e:
            logging.error(f"Error extracting quantity: {e}")
            return None

    def _save_stock_snapshot(self, asin, status, quantity, product_name=None):
        """Guarda snapshot de stock en historial"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Guardar en historial
        cursor.execute('''
            INSERT INTO stock_history (asin, status, quantity, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (asin, status, quantity, datetime.now()))

        # Actualizar estado actual
        cursor.execute('''
            INSERT OR REPLACE INTO tracked_stock
            (asin, product_name, last_checked, current_status, current_quantity)
            VALUES (?, ?, ?, ?, ?)
        ''', (asin, product_name, datetime.now(), status, quantity))

        conn.commit()
        conn.close()

        logging.info(f"Stock snapshot saved: {asin} - {status} (Qty: {quantity})")

    def _check_stock_changes(self, asin, new_status, new_quantity, product_name):
        """Detecta cambios de stock y dispara alertas"""
        try:
            # Obtener último estado previo
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT current_status, current_quantity, low_stock_threshold
                FROM tracked_stock
                WHERE asin = ?
            ''', (asin,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                # Primera vez que se trackea este producto
                return

            old_status = row[0]
            old_quantity = row[1] or 0
            threshold = row[2] or 10

            # No hay cambio si el estado es el mismo
            if old_status == new_status and old_status not in ['Low Stock', 'In Stock']:
                return

            # Detectar cambios significativos
            changes_detected = []

            # Cambio 1: In Stock → Out of Stock
            if old_status == 'In Stock' and new_status == 'Out of Stock':
                changes_detected.append('out_of_stock')
                self._trigger_out_of_stock_alert(asin, product_name)

            # Cambio 2: Out of Stock → In Stock
            elif old_status == 'Out of Stock' and new_status == 'In Stock':
                changes_detected.append('back_in_stock')
                self._trigger_back_in_stock_alert(asin, product_name)

            # Cambio 3: Stock bajo (< threshold)
            if new_status == 'Low Stock' or (new_quantity and new_quantity < threshold):
                # Solo alertar si no estaba en Low Stock antes
                if old_status != 'Low Stock' and old_quantity != new_quantity:
                    changes_detected.append('low_stock')
                    self._trigger_low_stock_alert(asin, product_name, new_quantity, threshold)

            # Cambio 4: Cantidad bajó significativamente (50% o más)
            if old_quantity and new_quantity:
                decrease_percent = ((old_quantity - new_quantity) / old_quantity) * 100
                if decrease_percent >= 50 and new_quantity < threshold:
                    changes_detected.append('stock_dropped')
                    self._trigger_stock_drop_alert(asin, product_name, old_quantity, new_quantity)

            if changes_detected:
                logging.info(f"🔔 Stock changes detected for {asin}: {', '.join(changes_detected)}")

        except Exception as e:
            logging.error(f"Error checking stock changes for {asin}: {e}")

    def _trigger_out_of_stock_alert(self, asin, product_name):
        """Dispara alerta cuando producto sale de stock"""
        message = f"⚠️ PRODUCTO AGOTADO: {product_name or asin} está Out of Stock"
        
        self.alert_system.create_alert(
            asin, product_name or f'Product {asin}',
            'stock_out',
            'high',
            message,
            {'status': 'Out of Stock'}
        )

        # Disparar webhook
        try:
            self.webhook_manager.sender.send_event('stock_low', {
                'asin': asin,
                'product_name': product_name,
                'status': 'Out of Stock',
                'quantity': 0,
                'alert_type': 'out_of_stock',
                'severity': 'high',
                'url': f"https://www.amazon.com/dp/{asin}"
            })
        except Exception as e:
            logging.warning(f"Error sending stock webhook: {e}")

    def _trigger_back_in_stock_alert(self, asin, product_name):
        """Dispara alerta cuando producto vuelve a stock"""
        message = f"✅ PRODUCTO DISPONIBLE: {product_name or asin} está de vuelta In Stock"
        
        self.alert_system.create_alert(
            asin, product_name or f'Product {asin}',
            'stock_back',
            'medium',
            message,
            {'status': 'In Stock'}
        )

    def _trigger_low_stock_alert(self, asin, product_name, quantity, threshold):
        """Dispara alerta cuando stock está bajo"""
        message = f"🔔 STOCK BAJO: {product_name or asin} tiene solo {quantity} unidades (threshold: {threshold})"
        
        self.alert_system.create_alert(
            asin, product_name or f'Product {asin}',
            'stock_low',
            'medium' if quantity >= 5 else 'high',
            message,
            {'quantity': quantity, 'threshold': threshold}
        )

        # Disparar webhook 'stock_low'
        try:
            self.webhook_manager.sender.send_event('stock_low', {
                'asin': asin,
                'product_name': product_name,
                'status': 'Low Stock',
                'quantity': quantity,
                'threshold': threshold,
                'alert_type': 'low_stock',
                'severity': 'high' if quantity < 5 else 'medium',
                'url': f"https://www.amazon.com/dp/{asin}",
                'message': message
            })
        except Exception as e:
            logging.warning(f"Error sending low stock webhook: {e}")

    def _trigger_stock_drop_alert(self, asin, product_name, old_quantity, new_quantity):
        """Dispara alerta cuando stock baja significativamente"""
        drop_percent = ((old_quantity - new_quantity) / old_quantity) * 100
        message = f"📉 STOCK BAJÓ: {product_name or asin} - {old_quantity} → {new_quantity} unidades ({drop_percent:.0f}% menos)"
        
        self.alert_system.create_alert(
            asin, product_name or f'Product {asin}',
            'stock_drop',
            'medium',
            message,
            {'old_quantity': old_quantity, 'new_quantity': new_quantity, 'drop_percent': drop_percent}
        )

    def get_stock_history(self, asin, days=30):
        """Obtiene histórico de stock para un producto"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM stock_history
            WHERE asin = ?
            AND date >= date('now', '-' || ? || ' days')
            ORDER BY timestamp ASC
        ''', (asin, days))

        history = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return history

    def get_current_stock_status(self, asin):
        """Obtiene estado actual de stock de un producto"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM tracked_stock
            WHERE asin = ? AND is_monitored = 1
        ''', (asin,))

        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    def track_product(self, asin, product_name=None, low_stock_threshold=10):
        """Añade un producto al tracking de stock"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO tracked_stock
            (asin, product_name, low_stock_threshold, is_monitored)
            VALUES (?, ?, ?, 1)
        ''', (asin, product_name, low_stock_threshold))

        conn.commit()
        conn.close()

        logging.info(f"Product {asin} added to stock tracking")

    def get_all_tracked_products(self):
        """Obtiene todos los productos trackeados"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM tracked_stock
            WHERE is_monitored = 1
            ORDER BY last_checked DESC
        ''')

        products = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return products

