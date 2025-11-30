"""
Review Monitor para Amazon FBA.
Monitorea reviews recientes y detecta cambios negativos.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from amzscraper import AmazonWebRobot
import logging
import sqlite3
from datetime import datetime, timedelta
import re

logging.basicConfig(level=logging.INFO)

class ReviewMonitor(AmazonWebRobot):
    def __init__(self, asin: str):
        super().__init__()
        self.asin = asin
        self.product_url = f"{self.amazon_link_prefix}/product-reviews/{self.asin}"
        self.db_path = 'data/review_history.db'
        self._init_database()
        
    def _init_database(self):
        """Inicializa la tabla de historial de reviews"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS review_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                review_id TEXT NOT NULL,
                rating INTEGER,
                text TEXT,
                review_date DATE,
                verified BOOLEAN,
                scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(asin, review_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rating_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                avg_rating REAL,
                total_reviews INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_review_asin 
            ON review_history(asin)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_review_date 
            ON review_history(review_date)
        ''')
        
        conn.commit()
        conn.close()
        logging.info(f"Review history database initialized at {self.db_path}")
    
    def scrape_recent_reviews(self, max_reviews=10):
        """
        Scrape las últimas N reviews del producto.
        Retorna lista de dicts con review data.
        """
        try:
            soup = self.get_soup(self.product_url)
            
            if not soup:
                logging.error(f"No se pudo obtener HTML para reviews de {self.asin}")
                return []
            
            reviews = []
            review_elements = soup.find_all('div', {'data-hook': 'review'})
            
            for review_elem in review_elements[:max_reviews]:
                try:
                    review_data = self._parse_review(review_elem)
                    if review_data:
                        reviews.append(review_data)
                except Exception as e:
                    logging.error(f"Error parsing individual review: {e}")
                    continue
            
            logging.info(f"Scraped {len(reviews)} reviews for {self.asin}")
            
            # Guardar en historial
            self._save_reviews_to_history(reviews)
            
            # Detectar cambios y alertas
            self._check_for_alerts(reviews)
            
            return reviews
            
        except Exception as e:
            logging.error(f"Error scraping reviews for {self.asin}: {e}")
            return []
    
    def _parse_review(self, review_elem):
        """Parsea un elemento de review individual"""
        try:
            # Review ID
            review_id = review_elem.get('id', '')
            if not review_id:
                return None
            
            # Rating (estrellas)
            rating_elem = review_elem.find('i', {'data-hook': 'review-star-rating'})
            rating = 0
            if rating_elem:
                rating_text = rating_elem.text.strip()
                match = re.search(r'(\d+\.?\d*)', rating_text)
                if match:
                    rating = int(float(match.group(1)))
            
            # Texto del review
            text_elem = review_elem.find('span', {'data-hook': 'review-body'})
            text = text_elem.text.strip() if text_elem else ""
            
            # Fecha
            date_elem = review_elem.find('span', {'data-hook': 'review-date'})
            review_date = None
            if date_elem:
                date_text = date_elem.text.strip()
                # Formato: "Reviewed in the United States on January 15, 2024"
                match = re.search(r'on\s+(.+)$', date_text)
                if match:
                    try:
                        from dateutil import parser
                        review_date = parser.parse(match.group(1)).date()
                    except:
                        review_date = datetime.now().date()
            
            if not review_date:
                review_date = datetime.now().date()
            
            # Verified purchase
            verified_elem = review_elem.find('span', {'data-hook': 'avp-badge'})
            verified = verified_elem is not None
            
            return {
                'asin': self.asin,
                'review_id': review_id,
                'rating': rating,
                'text': text[:500],  # Primeros 500 chars
                'review_date': review_date,
                'verified': verified
            }
            
        except Exception as e:
            logging.error(f"Error parsing review element: {e}")
            return None
    
    def _save_reviews_to_history(self, reviews):
        """Guarda reviews en el historial (evita duplicados)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for review in reviews:
                cursor.execute('''
                    INSERT OR IGNORE INTO review_history 
                    (asin, review_id, rating, text, review_date, verified)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    review['asin'],
                    review['review_id'],
                    review['rating'],
                    review['text'],
                    review['review_date'],
                    review['verified']
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error saving reviews to history: {e}")
    
    def _check_for_alerts(self, recent_reviews):
        """Detecta cambios y dispara alertas"""
        try:
            # 1. Detectar spike de reviews negativos (1-2 estrellas)
            negative_reviews = [r for r in recent_reviews if r['rating'] <= 2]
            if len(negative_reviews) >= 3:  # 3+ reviews negativos en últimas 10
                self._trigger_alert('negative_review_spike', {
                    'asin': self.asin,
                    'negative_count': len(negative_reviews),
                    'total_recent': len(recent_reviews),
                    'reviews': negative_reviews[:3]  # Primeros 3
                })
            
            # 2. Detectar spike de reviews en general (>10 en 24h)
            reviews_24h = self._get_reviews_last_24h()
            if len(reviews_24h) > 10:
                self._trigger_alert('review_spike', {
                    'asin': self.asin,
                    'count_24h': len(reviews_24h),
                    'threshold': 10
                })
            
            # 3. Detectar caída de rating promedio
            self._check_rating_drop()
            
        except Exception as e:
            logging.error(f"Error checking for alerts: {e}")
    
    def _get_reviews_last_24h(self):
        """Obtiene reviews de las últimas 24 horas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(hours=24)
        
        cursor.execute('''
            SELECT * FROM review_history
            WHERE asin = ? AND scraped_at >= ?
        ''', (self.asin, cutoff))
        
        rows = cursor.fetchall()
        conn.close()
        
        return rows
    
    def _check_rating_drop(self):
        """Detecta si el rating promedio ha bajado"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener últimos 2 snapshots de rating
            cursor.execute('''
                SELECT avg_rating, total_reviews, timestamp
                FROM rating_snapshots
                WHERE asin = ?
                ORDER BY timestamp DESC
                LIMIT 2
            ''', (self.asin,))
            
            snapshots = cursor.fetchall()
            conn.close()
            
            if len(snapshots) >= 2:
                current_rating, current_total, _ = snapshots[0]
                previous_rating, previous_total, _ = snapshots[1]
                
                # Si bajó más de 0.3 estrellas
                if previous_rating - current_rating >= 0.3:
                    self._trigger_alert('rating_dropped', {
                        'asin': self.asin,
                        'previous_rating': previous_rating,
                        'current_rating': current_rating,
                        'drop': previous_rating - current_rating,
                        'total_reviews': current_total
                    })
            
        except Exception as e:
            logging.error(f"Error checking rating drop: {e}")
    
    def save_rating_snapshot(self, avg_rating, total_reviews):
        """Guarda un snapshot del rating actual"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO rating_snapshots (asin, avg_rating, total_reviews)
                VALUES (?, ?, ?)
            ''', (self.asin, avg_rating, total_reviews))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error saving rating snapshot: {e}")
    
    def _trigger_alert(self, alert_type, payload):
        """Dispara alerta y webhook"""
        try:
            logging.warning(f"ALERT: {alert_type} for {self.asin}")
            
            # Guardar en alert_system si existe
            try:
                from src.utils.alert_system import AlertSystem
                alert_system = AlertSystem()
                
                priority = 'high' if alert_type == 'negative_review_spike' else 'medium'
                
                alert_system.create_alert(
                    alert_type=alert_type,
                    title=f"{alert_type.replace('_', ' ').title()} - {self.asin}",
                    message=str(payload),
                    priority=priority,
                    data=payload
                )
            except ImportError:
                logging.warning("AlertSystem not available")
            
            # Disparar webhook
            try:
                from src.api.webhook_sender import webhook_sender
                webhook_sender.send_event(alert_type, payload)
            except ImportError:
                logging.warning("webhook_sender not available")
                
        except Exception as e:
            logging.error(f"Error triggering alert: {e}")
    
    def get_recent_reviews(self, limit=20):
        """Obtiene reviews recientes del historial"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT review_id, rating, text, review_date, verified, scraped_at
            FROM review_history
            WHERE asin = ?
            ORDER BY scraped_at DESC
            LIMIT ?
        ''', (self.asin, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        reviews = []
        for row in rows:
            reviews.append({
                'review_id': row[0],
                'rating': row[1],
                'text': row[2],
                'review_date': row[3],
                'verified': bool(row[4]),
                'scraped_at': row[5]
            })
        
        return reviews
    
    def get_review_stats(self):
        """Obtiene estadísticas de reviews"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total reviews
        cursor.execute('''
            SELECT COUNT(*) FROM review_history WHERE asin = ?
        ''', (self.asin,))
        total = cursor.fetchone()[0]
        
        # Rating promedio
        cursor.execute('''
            SELECT AVG(rating) FROM review_history WHERE asin = ?
        ''', (self.asin,))
        avg_rating = cursor.fetchone()[0] or 0
        
        # Distribución de ratings
        cursor.execute('''
            SELECT rating, COUNT(*) as count
            FROM review_history
            WHERE asin = ?
            GROUP BY rating
            ORDER BY rating DESC
        ''', (self.asin,))
        
        distribution = {}
        for row in cursor.fetchall():
            distribution[row[0]] = row[1]
        
        # Reviews negativos (1-2 estrellas)
        cursor.execute('''
            SELECT COUNT(*) FROM review_history 
            WHERE asin = ? AND rating <= 2
        ''', (self.asin,))
        negative_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_reviews': total,
            'avg_rating': round(avg_rating, 2),
            'distribution': distribution,
            'negative_count': negative_count,
            'negative_percent': round((negative_count / total * 100) if total > 0 else 0, 1)
        }
