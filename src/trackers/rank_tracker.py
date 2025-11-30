"""
Rank Tracker para Amazon Keywords.
Track posición orgánica de ASINs por keyword (como Helium 10 Keyword Tracker).
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from amzscraper import AmazonWebRobot
import logging
import sqlite3
from datetime import datetime, timedelta
import time

logging.basicConfig(level=logging.INFO)

class RankTracker(AmazonWebRobot):
    def __init__(self):
        super().__init__()
        self.db_path = 'data/rank_tracking.db'
        self._init_database()
        
    def _init_database(self):
        """Inicializa database de rank tracking"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla de keywords trackeadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tracked_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                keyword TEXT NOT NULL,
                current_rank INTEGER,
                previous_rank INTEGER,
                rank_change INTEGER,
                last_checked DATETIME,
                UNIQUE(asin, keyword)
            )
        ''')
        
        # Tabla de historial de ranks
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rank_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                keyword TEXT NOT NULL,
                rank_position INTEGER,
                page_number INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tracked_asin_keyword 
            ON tracked_keywords(asin, keyword)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_history_asin_keyword 
            ON rank_history(asin, keyword)
        ''')
        
        conn.commit()
        conn.close()
        logging.info(f"Rank tracking database initialized at {self.db_path}")
    
    def track_keyword_rank(self, asin, keyword, max_pages=5):
        """
        Trackea la posición de un ASIN para una keyword específica.
        Retorna: dict con rank position, page number, etc.
        """
        try:
            logging.info(f"Tracking rank for ASIN {asin}, keyword: '{keyword}'")
            
            # Buscar en resultados de Amazon
            rank_position = None
            page_number = None
            
            for page in range(1, max_pages + 1):
                # Construir URL de búsqueda
                search_url = f"{self.amazon_link_prefix}/s?k={keyword.replace(' ', '+')}&page={page}"
                
                soup = self.get_soup(search_url)
                
                if not soup:
                    logging.error(f"No se pudo obtener HTML para keyword: {keyword}, page {page}")
                    break
                
                # Buscar productos en la página
                products = soup.find_all('div', {'data-component-type': 's-search-result'})
                
                for idx, product in enumerate(products):
                    # Extraer ASIN del producto
                    product_asin = product.get('data-asin', '')
                    
                    if product_asin == asin:
                        # Encontrado!
                        rank_position = (page - 1) * len(products) + idx + 1
                        page_number = page
                        logging.info(f"Found ASIN {asin} at position {rank_position} (page {page})")
                        break
                
                if rank_position:
                    break
                
                # Delay entre páginas para evitar rate limiting
                time.sleep(5)
            
            if not rank_position:
                logging.warning(f"ASIN {asin} not found in top {max_pages} pages for keyword: {keyword}")
                rank_position = 999  # No encontrado
                page_number = 0
            
            # Guardar en historial
            self._save_rank_history(asin, keyword, rank_position, page_number)
            
            # Actualizar tracked_keywords
            self._update_tracked_keyword(asin, keyword, rank_position)
            
            # Detectar cambios significativos
            self._check_rank_changes(asin, keyword, rank_position)
            
            return {
                'asin': asin,
                'keyword': keyword,
                'rank_position': rank_position,
                'page_number': page_number,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logging.error(f"Error tracking rank for {asin}/{keyword}: {e}")
            return None
    
    def batch_track(self, asin, keywords_list, delay=10):
        """
        Trackea múltiples keywords para un ASIN en batch.
        delay: segundos entre cada keyword (rate limiting)
        """
        results = []
        
        for idx, keyword in enumerate(keywords_list):
            try:
                result = self.track_keyword_rank(asin, keyword)
                if result:
                    results.append(result)
                
                # Delay entre keywords (excepto el último)
                if idx < len(keywords_list) - 1:
                    logging.info(f"Waiting {delay}s before next keyword...")
                    time.sleep(delay)
                    
            except Exception as e:
                logging.error(f"Error tracking keyword '{keyword}': {e}")
                continue
        
        return results
    
    def _save_rank_history(self, asin, keyword, rank_position, page_number):
        """Guarda snapshot de rank en historial"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO rank_history (asin, keyword, rank_position, page_number)
                VALUES (?, ?, ?, ?)
            ''', (asin, keyword, rank_position, page_number))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error saving rank history: {e}")
    
    def _update_tracked_keyword(self, asin, keyword, new_rank):
        """Actualiza tabla de tracked_keywords"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Obtener rank anterior
            cursor.execute('''
                SELECT current_rank FROM tracked_keywords
                WHERE asin = ? AND keyword = ?
            ''', (asin, keyword))
            
            row = cursor.fetchone()
            previous_rank = row[0] if row else None
            
            # Calcular cambio
            rank_change = 0
            if previous_rank and new_rank != 999:
                rank_change = previous_rank - new_rank  # Positivo = mejoró
            
            # Insertar o actualizar
            cursor.execute('''
                INSERT OR REPLACE INTO tracked_keywords 
                (asin, keyword, current_rank, previous_rank, rank_change, last_checked)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (asin, keyword, new_rank, previous_rank, rank_change, datetime.now()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Error updating tracked keyword: {e}")
    
    def _check_rank_changes(self, asin, keyword, new_rank):
        """Detecta cambios significativos y dispara webhooks"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT previous_rank, rank_change FROM tracked_keywords
                WHERE asin = ? AND keyword = ?
            ''', (asin, keyword))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row or not row[0]:
                return
            
            previous_rank, rank_change = row
            
            # Cambio significativo: >5 posiciones
            if abs(rank_change) >= 5:
                if rank_change > 0:
                    # Mejoró
                    self._trigger_webhook('rank_improved', {
                        'asin': asin,
                        'keyword': keyword,
                        'previous_rank': previous_rank,
                        'current_rank': new_rank,
                        'improvement': rank_change
                    })
                else:
                    # Empeoró
                    self._trigger_webhook('rank_dropped', {
                        'asin': asin,
                        'keyword': keyword,
                        'previous_rank': previous_rank,
                        'current_rank': new_rank,
                        'drop': abs(rank_change)
                    })
            
        except Exception as e:
            logging.error(f"Error checking rank changes: {e}")
    
    def _trigger_webhook(self, event_type, payload):
        """Dispara webhook para cambios de rank"""
        try:
            from src.api.webhook_sender import webhook_sender
            webhook_sender.send_event(event_type, payload)
            logging.info(f"Webhook {event_type} triggered for {payload['asin']}/{payload['keyword']}")
        except ImportError:
            logging.warning("webhook_sender not available")
        except Exception as e:
            logging.error(f"Error triggering webhook: {e}")
    
    def get_tracked_keywords(self, asin=None):
        """Obtiene lista de keywords trackeadas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if asin:
            cursor.execute('''
                SELECT asin, keyword, current_rank, previous_rank, rank_change, last_checked
                FROM tracked_keywords
                WHERE asin = ?
                ORDER BY current_rank ASC
            ''', (asin,))
        else:
            cursor.execute('''
                SELECT asin, keyword, current_rank, previous_rank, rank_change, last_checked
                FROM tracked_keywords
                ORDER BY last_checked DESC
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        keywords = []
        for row in rows:
            keywords.append({
                'asin': row[0],
                'keyword': row[1],
                'current_rank': row[2],
                'previous_rank': row[3],
                'rank_change': row[4],
                'last_checked': row[5],
                'trend': 'up' if row[4] > 0 else ('down' if row[4] < 0 else 'stable')
            })
        
        return keywords
    
    def get_rank_history(self, asin, keyword, days=30):
        """Obtiene historial de ranks para una keyword"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = datetime.now() - timedelta(days=days)
        
        cursor.execute('''
            SELECT rank_position, page_number, timestamp
            FROM rank_history
            WHERE asin = ? AND keyword = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (asin, keyword, cutoff))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'rank': row[0],
                'page': row[1],
                'timestamp': row[2]
            })
        
        return history
    
    def add_keyword_to_track(self, asin, keyword):
        """Añade una keyword para tracking"""
        try:
            # Hacer primer check
            result = self.track_keyword_rank(asin, keyword)
            
            if result:
                logging.info(f"Added keyword '{keyword}' for ASIN {asin}")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error adding keyword: {e}")
            return False
    
    def remove_keyword(self, asin, keyword):
        """Remueve una keyword del tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM tracked_keywords
                WHERE asin = ? AND keyword = ?
            ''', (asin, keyword))
            
            conn.commit()
            conn.close()
            
            logging.info(f"Removed keyword '{keyword}' for ASIN {asin}")
            return True
            
        except Exception as e:
            logging.error(f"Error removing keyword: {e}")
            return False
