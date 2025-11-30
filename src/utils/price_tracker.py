"""
Sistema de tracking de precios y BSR para productos de Amazon.
Usa SQLite para almacenar historial y detectar cambios.
"""
import sqlite3
import os
import sys
from datetime import datetime, timedelta
import logging

# Añadir path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.scrapers.product_info import ProductInfoScraper

logging.basicConfig(level=logging.INFO)

class PriceTracker:
    def __init__(self, db_path='data/tracking.db'):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Inicializa las tablas de la base de datos"""
        # Crear directorio data si no existe
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de historial de precios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                price REAL,
                bsr INTEGER,
                in_stock BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabla de productos trackeados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracked_products (
                asin TEXT PRIMARY KEY,
                product_name TEXT,
                last_checked DATETIME,
                alert_threshold REAL DEFAULT 10.0
            )
        ''')
        
        # Índices para mejorar performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_price_history_asin 
            ON price_history(asin)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_price_history_timestamp 
            ON price_history(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        logging.info(f"Database initialized at {self.db_path}")
    
    def track_product(self, asin, product_name=None):
        """Añade un producto a la lista de tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO tracked_products (asin, product_name, last_checked)
                VALUES (?, ?, ?)
            ''', (asin, product_name or f"Product {asin}", datetime.now()))
            
            conn.commit()
            logging.info(f"Product {asin} added to tracking")
            return True
        except Exception as e:
            logging.error(f"Error tracking product {asin}: {e}")
            return False
        finally:
            conn.close()
    
    def update_price(self, asin):
        """Scrape y guarda el precio actual del producto"""
        try:
            # Scrape product info
            scraper = ProductInfoScraper(asin)
            product_data = scraper.scrape_product_info()
            
            if not product_data:
                logging.warning(f"Could not scrape data for {asin}")
                return False
            
            # Guardar en historial
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            price = product_data.get('price', 0)
            bsr = product_data.get('bsr', {}).get('rank', 0)
            in_stock = price > 0  # Asumimos que si tiene precio, está en stock
            
            cursor.execute('''
                INSERT INTO price_history (asin, price, bsr, in_stock, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (asin, price, bsr, in_stock, datetime.now()))
            
            # Actualizar last_checked en tracked_products
            cursor.execute('''
                UPDATE tracked_products 
                SET last_checked = ?, product_name = ?
                WHERE asin = ?
            ''', (datetime.now(), product_data.get('title', f"Product {asin}"), asin))
            
            conn.commit()
            conn.close()
            
            logging.info(f"Price updated for {asin}: ${price}, BSR: {bsr}")
            return True
            
        except Exception as e:
            logging.error(f"Error updating price for {asin}: {e}")
            return False
    
    def get_price_history(self, asin, days=30):
        """Obtiene el historial de precios de los últimos N días"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT price, bsr, in_stock, timestamp
            FROM price_history
            WHERE asin = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (asin, cutoff_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'price': row[0],
                'bsr': row[1],
                'in_stock': bool(row[2]),
                'timestamp': row[3]
            })
        
        return history
    
    def check_alerts(self):
        """Detecta cambios de precio >threshold% en productos trackeados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Obtener todos los productos trackeados
        cursor.execute('SELECT asin, product_name, alert_threshold FROM tracked_products')
        products = cursor.fetchall()
        
        alerts = []
        
        for asin, product_name, threshold in products:
            # Obtener últimos 2 precios
            cursor.execute('''
                SELECT price, timestamp
                FROM price_history
                WHERE asin = ? AND price > 0
                ORDER BY timestamp DESC
                LIMIT 2
            ''', (asin,))
            
            prices = cursor.fetchall()
            
            if len(prices) >= 2:
                current_price = prices[0][0]
                previous_price = prices[1][0]
                
                if previous_price > 0:
                    change_percent = ((current_price - previous_price) / previous_price) * 100
                    
                    if abs(change_percent) >= threshold:
                        alerts.append({
                            'asin': asin,
                            'product_name': product_name,
                            'previous_price': previous_price,
                            'current_price': current_price,
                            'change_percent': change_percent,
                            'timestamp': prices[0][1]
                        })
        
        conn.close()
        return alerts
    
    def get_tracked_products(self):
        """Obtiene lista de todos los productos trackeados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT asin, product_name, last_checked, alert_threshold
            FROM tracked_products
            ORDER BY last_checked DESC
        ''')
        
        products = []
        for row in cursor.fetchall():
            products.append({
                'asin': row[0],
                'product_name': row[1],
                'last_checked': row[2],
                'alert_threshold': row[3]
            })
        
        conn.close()
        return products
    
    def update_all_tracked_products(self):
        """Actualiza precios de todos los productos trackeados"""
        products = self.get_tracked_products()
        
        logging.info(f"Updating {len(products)} tracked products...")
        
        for product in products:
            asin = product['asin']
            self.update_price(asin)
        
        # Check for alerts
        alerts = self.check_alerts()
        if alerts:
            logging.warning(f"Found {len(alerts)} price alerts!")
            for alert in alerts:
                logging.warning(
                    f"ALERT: {alert['product_name']} ({alert['asin']}) "
                    f"changed {alert['change_percent']:.2f}% "
                    f"(${alert['previous_price']} → ${alert['current_price']})"
                )
        
        return alerts
