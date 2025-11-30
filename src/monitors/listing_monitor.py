"""
Listing Change Detector para Amazon FBA.
Detecta cambios en títulos, precios, bullets, descripciones e imágenes.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from amzscraper import AmazonWebRobot
import logging
import sqlite3
from datetime import datetime
import hashlib
import json

logging.basicConfig(level=logging.INFO)

class ListingMonitor(AmazonWebRobot):
    def __init__(self, asin: str):
        super().__init__()
        self.asin = asin
        self.product_url = f"{self.amazon_link_prefix}/dp/{self.asin}"
        self.db_path = 'data/listing_snapshots.db'
        self._init_database()
        
    def _init_database(self):
        """Inicializa la tabla de snapshots de listings"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listing_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                title TEXT,
                price REAL,
                bullet_points TEXT,
                description TEXT,
                images TEXT,
                bullets_hash TEXT,
                description_hash TEXT,
                images_hash TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS listing_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                change_type TEXT,
                field_changed TEXT,
                old_value TEXT,
                new_value TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_listing_asin 
            ON listing_snapshots(asin)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_changes_asin 
            ON listing_changes(asin)
        ''')
        
        conn.commit()
        conn.close()
        logging.info(f"Listing snapshots database initialized at {self.db_path}")
    
    def track_listing_changes(self):
        """
        Scrape el listing actual y detecta cambios.
        Retorna dict con cambios detectados.
        """
        try:
            soup = self.get_soup(self.product_url)
            
            if not soup:
                logging.error(f"No se pudo obtener HTML para {self.asin}")
                return None
            
            # Extraer datos del listing
            current_snapshot = {
                'asin': self.asin,
                'title': self._get_title(soup),
                'price': self._get_price(soup),
                'bullet_points': self._get_bullet_points(soup),
                'description': self._get_description(soup),
                'images': self._get_images(soup),
                'timestamp': datetime.now()
            }
            
            # Calcular hashes
            current_snapshot['bullets_hash'] = self._hash_content(current_snapshot['bullet_points'])
            current_snapshot['description_hash'] = self._hash_content(current_snapshot['description'])
            current_snapshot['images_hash'] = self._hash_content(current_snapshot['images'])
            
            # Obtener snapshot anterior
            previous_snapshot = self._get_latest_snapshot()
            
            # Detectar cambios
            changes = []
            if previous_snapshot:
                changes = self._detect_changes(previous_snapshot, current_snapshot)
            
            # Guardar snapshot actual
            self._save_snapshot(current_snapshot)
            
            # Guardar cambios detectados
            if changes:
                self._save_changes(changes)
                self._trigger_webhooks(changes)
            
            logging.info(f"Listing tracked for {self.asin}: {len(changes)} changes detected")
            
            return {
                'asin': self.asin,
                'changes_detected': len(changes),
                'changes': changes,
                'current_snapshot': current_snapshot
            }
            
        except Exception as e:
            logging.error(f"Error tracking listing for {self.asin}: {e}")
            return None
    
    def _get_title(self, soup):
        """Extrae el título del producto"""
        try:
            title = soup.find('span', {'id': 'productTitle'})
            return title.text.strip() if title else ""
        except:
            return ""
    
    def _get_price(self, soup):
        """Extrae el precio"""
        try:
            price = soup.find('span', {'class': 'a-price-whole'})
            if price:
                price_text = price.text.strip().replace(',', '').replace('$', '')
                return float(price_text)
            return 0.0
        except:
            return 0.0
    
    def _get_bullet_points(self, soup):
        """Extrae los bullet points"""
        try:
            bullets = []
            feature_div = soup.find('div', {'id': 'feature-bullets'})
            
            if feature_div:
                bullet_items = feature_div.find_all('span', {'class': 'a-list-item'})
                for item in bullet_items:
                    text = item.text.strip()
                    if text and len(text) > 5:  # Filtrar bullets vacíos
                        bullets.append(text)
            
            return bullets
        except:
            return []
    
    def _get_description(self, soup):
        """Extrae la descripción del producto"""
        try:
            desc_div = soup.find('div', {'id': 'productDescription'})
            if desc_div:
                # Limpiar HTML tags
                text = desc_div.get_text(separator=' ', strip=True)
                return text[:1000]  # Primeros 1000 chars
            return ""
        except:
            return ""
    
    def _get_images(self, soup):
        """Extrae URLs de imágenes"""
        try:
            images = []
            img_elements = soup.find_all('img', {'class': 'a-dynamic-image'})
            
            for img in img_elements[:7]:  # Máximo 7 imágenes
                if 'src' in img.attrs:
                    images.append(img['src'])
            
            return images
        except:
            return []
    
    def _hash_content(self, content):
        """Calcula hash MD5 del contenido"""
        try:
            if isinstance(content, list):
                content = json.dumps(content, sort_keys=True)
            elif not isinstance(content, str):
                content = str(content)
            
            return hashlib.md5(content.encode('utf-8')).hexdigest()
        except:
            return ""
    
    def _get_latest_snapshot(self):
        """Obtiene el snapshot más reciente"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT title, price, bullet_points, description, images,
                       bullets_hash, description_hash, images_hash, timestamp
                FROM listing_snapshots
                WHERE asin = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (self.asin,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'title': row[0],
                    'price': row[1],
                    'bullet_points': json.loads(row[2]) if row[2] else [],
                    'description': row[3],
                    'images': json.loads(row[4]) if row[4] else [],
                    'bullets_hash': row[5],
                    'description_hash': row[6],
                    'images_hash': row[7],
                    'timestamp': row[8]
                }
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting latest snapshot: {e}")
            return None
    
    def _detect_changes(self, previous, current):
        """Detecta cambios entre snapshots"""
        changes = []
        
        # Cambio de título
        if previous['title'] != current['title']:
            changes.append({
                'type': 'title_changed',
                'field': 'title',
                'old_value': previous['title'],
                'new_value': current['title']
            })
        
        # Cambio de precio (diferencia > $1)
        price_diff = abs(previous['price'] - current['price'])
        if price_diff > 1.0:
            changes.append({
                'type': 'price_changed',
                'field': 'price',
                'old_value': previous['price'],
                'new_value': current['price'],
                'difference': current['price'] - previous['price']
            })
        
        # Cambio de bullet points
        if previous['bullets_hash'] != current['bullets_hash']:
            changes.append({
                'type': 'bullets_changed',
                'field': 'bullet_points',
                'old_value': previous['bullet_points'],
                'new_value': current['bullet_points']
            })
        
        # Cambio de descripción
        if previous['description_hash'] != current['description_hash']:
            changes.append({
                'type': 'description_changed',
                'field': 'description',
                'old_value': previous['description'][:200],  # Primeros 200 chars
                'new_value': current['description'][:200]
            })
        
        # Cambio de imágenes
        if previous['images_hash'] != current['images_hash']:
            changes.append({
                'type': 'images_changed',
                'field': 'images',
                'old_value': len(previous['images']),
                'new_value': len(current['images']),
                'old_images': previous['images'],
                'new_images': current['images']
            })
        
        return changes
    
    def _save_snapshot(self, snapshot):
        """Guarda el snapshot actual"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO listing_snapshots 
                (asin, title, price, bullet_points, description, images,
                 bullets_hash, description_hash, images_hash, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot['asin'],
                snapshot['title'],
                snapshot['price'],
                json.dumps(snapshot['bullet_points']),
                snapshot['description'],
                json.dumps(snapshot['images']),
                snapshot['bullets_hash'],
                snapshot['description_hash'],
                snapshot['images_hash'],
                snapshot['timestamp']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error saving snapshot: {e}")
    
    def _save_changes(self, changes):
        """Guarda los cambios detectados"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for change in changes:
                cursor.execute('''
                    INSERT INTO listing_changes 
                    (asin, change_type, field_changed, old_value, new_value)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    self.asin,
                    change['type'],
                    change['field'],
                    json.dumps(change.get('old_value')),
                    json.dumps(change.get('new_value'))
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error saving changes: {e}")
    
    def _trigger_webhooks(self, changes):
        """Dispara webhooks para cambios detectados"""
        try:
            for change in changes:
                event_type = f"listing_{change['type']}"
                
                payload = {
                    'asin': self.asin,
                    'change_type': change['type'],
                    'field': change['field'],
                    'timestamp': datetime.now().isoformat()
                }
                
                # Añadir detalles específicos según tipo
                if change['type'] == 'price_changed':
                    payload['old_price'] = change['old_value']
                    payload['new_price'] = change['new_value']
                    payload['difference'] = change.get('difference', 0)
                elif change['type'] == 'title_changed':
                    payload['old_title'] = change['old_value']
                    payload['new_title'] = change['new_value']
                
                # Disparar webhook
                try:
                    from src.api.webhook_sender import webhook_sender
                    webhook_sender.send_event(event_type, payload)
                    logging.info(f"Webhook {event_type} triggered for {self.asin}")
                except ImportError:
                    logging.warning("webhook_sender not available")
                    
        except Exception as e:
            logging.error(f"Error triggering webhooks: {e}")
    
    def get_change_history(self, days=30):
        """Obtiene el historial de cambios"""
        from datetime import timedelta
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT change_type, field_changed, old_value, new_value, timestamp
            FROM listing_changes
            WHERE asin = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        ''', (self.asin, cutoff))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'change_type': row[0],
                'field': row[1],
                'old_value': json.loads(row[2]) if row[2] else None,
                'new_value': json.loads(row[3]) if row[3] else None,
                'timestamp': row[4]
            })
        
        return history
