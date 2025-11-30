"""
Buy Box Winner Scraper para Amazon FBA.
Detecta quién tiene el Buy Box y trackea cambios.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from amzscraper import AmazonWebRobot
import logging
import sqlite3
from datetime import datetime

logging.basicConfig(level=logging.INFO)

class BuyBoxScraper(AmazonWebRobot):
    def __init__(self, asin: str):
        super().__init__()
        self.asin = asin
        self.product_url = f"{self.amazon_link_prefix}/dp/{self.asin}"
        self.db_path = 'data/buybox_history.db'
        self._init_database()
        
    def _init_database(self):
        """Inicializa la tabla de historial de Buy Box"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buybox_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                seller_name TEXT,
                price REAL,
                fulfillment TEXT,
                availability TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_buybox_asin 
            ON buybox_history(asin)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_buybox_timestamp 
            ON buybox_history(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        logging.info(f"BuyBox database initialized at {self.db_path}")
    
    def get_buybox_winner(self):
        """
        Scrape el ganador actual del Buy Box.
        Retorna dict con seller_name, price, fulfillment, availability
        """
        try:
            soup = self.get_soup(self.product_url)
            
            if not soup:
                logging.error(f"No se pudo obtener HTML para {self.asin}")
                return None
            
            buybox_data = {
                'asin': self.asin,
                'seller_name': self._get_seller_name(soup),
                'price': self._get_buybox_price(soup),
                'fulfillment': self._get_fulfillment_method(soup),
                'availability': self._get_availability(soup),
                'timestamp': datetime.now()
            }
            
            # Guardar en historial
            self._save_to_history(buybox_data)
            
            # Detectar cambios y disparar webhooks
            self._check_for_changes(buybox_data)
            
            logging.info(f"Buy Box scraped for {self.asin}: {buybox_data['seller_name']} @ ${buybox_data['price']}")
            return buybox_data
            
        except Exception as e:
            logging.error(f"Error scraping Buy Box for {self.asin}: {e}")
            return None
    
    def _get_seller_name(self, soup):
        """Extrae el nombre del seller que tiene el Buy Box"""
        try:
            # Opción 1: Buscar en merchant info
            merchant_info = soup.find('div', {'id': 'merchant-info'})
            if merchant_info:
                # Si dice "Ships from and sold by Amazon"
                if 'amazon' in merchant_info.text.lower():
                    return 'Amazon.com'
                
                # Buscar link del seller
                seller_link = merchant_info.find('a')
                if seller_link:
                    return seller_link.text.strip()
            
            # Opción 2: Buscar en tabpane
            tabpane = soup.find('div', {'id': 'tabular-buybox'})
            if tabpane:
                seller_span = tabpane.find('span', {'class': 'tabular-buybox-text'})
                if seller_span:
                    seller_text = seller_span.text.strip()
                    if 'amazon' in seller_text.lower():
                        return 'Amazon.com'
                    return seller_text
            
            # Opción 3: Buscar "Sold by"
            sold_by = soup.find(text=lambda t: t and 'Sold by' in t)
            if sold_by:
                parent = sold_by.parent
                if parent:
                    seller_link = parent.find('a')
                    if seller_link:
                        return seller_link.text.strip()
            
            return 'Unknown Seller'
            
        except Exception as e:
            logging.error(f"Error getting seller name: {e}")
            return 'Unknown Seller'
    
    def _get_buybox_price(self, soup):
        """Extrae el precio del Buy Box"""
        try:
            # Opción 1: Precio principal
            price_whole = soup.find('span', {'class': 'a-price-whole'})
            if price_whole:
                price_text = price_whole.text.strip().replace(',', '').replace('$', '')
                return float(price_text)
            
            # Opción 2: Precio en Buy Box
            buybox_price = soup.find('span', {'id': 'price_inside_buybox'})
            if buybox_price:
                price_text = buybox_price.text.strip().replace(',', '').replace('$', '')
                return float(price_text)
            
            # Opción 3: Precio en priceblock
            priceblock = soup.find('span', {'id': 'priceblock_ourprice'})
            if priceblock:
                price_text = priceblock.text.strip().replace(',', '').replace('$', '')
                return float(price_text)
            
            return 0.0
            
        except Exception as e:
            logging.error(f"Error getting Buy Box price: {e}")
            return 0.0
    
    def _get_fulfillment_method(self, soup):
        """Determina si es FBA o FBM"""
        try:
            merchant_info = soup.find('div', {'id': 'merchant-info'})
            if merchant_info:
                text = merchant_info.text.lower()
                
                if 'fulfillment by amazon' in text or 'ships from and sold by amazon' in text:
                    return 'FBA'
                elif 'ships from' in text and 'sold by' in text:
                    # Third party seller
                    if 'amazon' in text:
                        return 'FBA'
                    else:
                        return 'FBM'
            
            # Fallback: buscar badge de Prime
            prime_badge = soup.find('i', {'class': 'a-icon-prime'})
            if prime_badge:
                return 'FBA'
            
            return 'Unknown'
            
        except Exception as e:
            logging.error(f"Error getting fulfillment method: {e}")
            return 'Unknown'
    
    def _get_availability(self, soup):
        """Extrae el estado de disponibilidad"""
        try:
            availability = soup.find('div', {'id': 'availability'})
            if availability:
                avail_text = availability.text.strip()
                
                if 'in stock' in avail_text.lower():
                    return 'In Stock'
                elif 'out of stock' in avail_text.lower():
                    return 'Out of Stock'
                elif 'temporarily out' in avail_text.lower():
                    return 'Temporarily Out'
                else:
                    return avail_text[:50]  # Primeros 50 chars
            
            return 'Unknown'
            
        except Exception as e:
            logging.error(f"Error getting availability: {e}")
            return 'Unknown'
    
    def _save_to_history(self, buybox_data):
        """Guarda el estado actual del Buy Box en el historial"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO buybox_history (asin, seller_name, price, fulfillment, availability, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                buybox_data['asin'],
                buybox_data['seller_name'],
                buybox_data['price'],
                buybox_data['fulfillment'],
                buybox_data['availability'],
                buybox_data['timestamp']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error saving to Buy Box history: {e}")
    
    def _check_for_changes(self, current_data):
        """Detecta cambios en el Buy Box y dispara webhooks"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener el registro anterior
            cursor.execute('''
                SELECT seller_name, price, fulfillment
                FROM buybox_history
                WHERE asin = ?
                ORDER BY timestamp DESC
                LIMIT 1 OFFSET 1
            ''', (self.asin,))
            
            previous = cursor.fetchone()
            conn.close()
            
            if not previous:
                # Primera vez que se trackea este producto
                logging.info(f"First Buy Box tracking for {self.asin}")
                return
            
            prev_seller, prev_price, prev_fulfillment = previous
            
            # Detectar cambio de seller (ganó o perdió Buy Box)
            if prev_seller != current_data['seller_name']:
                logging.warning(f"BUY BOX CHANGE for {self.asin}: {prev_seller} → {current_data['seller_name']}")
                
                # Disparar webhook
                self._trigger_webhook('buybox_changed', {
                    'asin': self.asin,
                    'previous_seller': prev_seller,
                    'new_seller': current_data['seller_name'],
                    'current_price': current_data['price'],
                    'fulfillment': current_data['fulfillment'],
                    'timestamp': current_data['timestamp'].isoformat()
                })
            
            # Detectar cambio de precio
            if prev_price != current_data['price'] and abs(prev_price - current_data['price']) > 0.01:
                change_percent = ((current_data['price'] - prev_price) / prev_price) * 100
                logging.info(f"BUY BOX PRICE CHANGE for {self.asin}: ${prev_price} → ${current_data['price']} ({change_percent:+.1f}%)")
                
                # Disparar webhook si cambio significativo (>5%)
                if abs(change_percent) >= 5:
                    self._trigger_webhook('buybox_price_changed', {
                        'asin': self.asin,
                        'seller': current_data['seller_name'],
                        'previous_price': prev_price,
                        'new_price': current_data['price'],
                        'change_percent': change_percent,
                        'timestamp': current_data['timestamp'].isoformat()
                    })
            
        except Exception as e:
            logging.error(f"Error checking for Buy Box changes: {e}")
    
    def _trigger_webhook(self, event_type, payload):
        """Dispara webhook para eventos de Buy Box"""
        try:
            # Importar webhook sender si existe
            try:
                from src.api.webhook_sender import webhook_sender
                webhook_sender.send_event(event_type, payload)
                logging.info(f"Webhook {event_type} triggered for {self.asin}")
            except ImportError:
                logging.warning("webhook_sender not available, skipping webhook")
        except Exception as e:
            logging.error(f"Error triggering webhook: {e}")
    
    def get_buybox_history(self, days=30):
        """Obtiene el historial de Buy Box de los últimos N días"""
        from datetime import timedelta
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT seller_name, price, fulfillment, availability, timestamp
            FROM buybox_history
            WHERE asin = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (self.asin, cutoff_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'seller_name': row[0],
                'price': row[1],
                'fulfillment': row[2],
                'availability': row[3],
                'timestamp': row[4]
            })
        
        return history
