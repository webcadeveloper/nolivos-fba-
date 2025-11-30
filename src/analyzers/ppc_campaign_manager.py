"""
PPC Campaign Manager - Gestiona campañas PPC y su base de datos
"""
import sqlite3
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)


class PPCCampaignManager:
    """Gestiona campañas PPC y almacena datos en base de datos"""

    def __init__(self, db_path='ppc_campaigns.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Crea tablas para gestión de campañas PPC"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabla de campañas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ppc_campaigns (
                campaign_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                asin TEXT,
                budget REAL,
                target_acos REAL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabla de keywords por campaña
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ppc_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                keyword TEXT NOT NULL,
                bid REAL,
                match_type TEXT DEFAULT 'exact',
                status TEXT DEFAULT 'active',
                clicks INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                spend REAL DEFAULT 0,
                sales INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0,
                acos REAL DEFAULT 0,
                ctr REAL DEFAULT 0,
                conversion_rate REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (campaign_id) REFERENCES ppc_campaigns(campaign_id)
            )
        ''')

        # Tabla de performance diaria
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ppc_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                date DATE NOT NULL,
                clicks INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                spend REAL DEFAULT 0,
                sales INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0,
                acos REAL DEFAULT 0,
                tacos REAL DEFAULT 0,
                roas REAL DEFAULT 0,
                FOREIGN KEY (campaign_id) REFERENCES ppc_campaigns(campaign_id),
                UNIQUE(campaign_id, date)
            )
        ''')

        # Índices
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_campaign_status
            ON ppc_campaigns(status)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_keywords_campaign
            ON ppc_keywords(campaign_id, status)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_performance_date
            ON ppc_performance(campaign_id, date DESC)
        ''')

        conn.commit()
        conn.close()
        logging.info("PPC Campaign database initialized")

    def create_campaign(self, campaign_id: str, name: str, asin: Optional[str] = None,
                       budget: float = 0, target_acos: float = 30.0) -> bool:
        """Crea una nueva campaña PPC"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO ppc_campaigns
                (campaign_id, name, asin, budget, target_acos, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (campaign_id, name, asin, budget, target_acos))

            conn.commit()
            conn.close()
            logging.info(f"Campaign {campaign_id} created/updated")
            return True

        except Exception as e:
            logging.error(f"Error creating campaign: {e}")
            return False

    def add_keywords(self, campaign_id: str, keywords: List[Dict]) -> bool:
        """Añade keywords a una campaña"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for kw in keywords:
                cursor.execute('''
                    INSERT OR REPLACE INTO ppc_keywords
                    (campaign_id, keyword, bid, match_type, status, updated_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    campaign_id,
                    kw.get('keyword', ''),
                    kw.get('bid', 0),
                    kw.get('match_type', 'exact'),
                    kw.get('status', 'active')
                ))

            conn.commit()
            conn.close()
            logging.info(f"Added {len(keywords)} keywords to campaign {campaign_id}")
            return True

        except Exception as e:
            logging.error(f"Error adding keywords: {e}")
            return False

    def update_keyword_performance(self, campaign_id: str, keyword: str, 
                                   performance_data: Dict) -> bool:
        """Actualiza performance de una keyword"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE ppc_keywords
                SET clicks = ?, impressions = ?, spend = ?, sales = ?,
                    revenue = ?, acos = ?, ctr = ?, conversion_rate = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE campaign_id = ? AND keyword = ?
            ''', (
                performance_data.get('clicks', 0),
                performance_data.get('impressions', 0),
                performance_data.get('spend', 0),
                performance_data.get('sales', 0),
                performance_data.get('revenue', 0),
                performance_data.get('acos', 0),
                performance_data.get('ctr', 0),
                performance_data.get('conversion_rate', 0),
                campaign_id,
                keyword
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logging.error(f"Error updating keyword performance: {e}")
            return False

    def get_campaign(self, campaign_id: str) -> Optional[Dict]:
        """Obtiene datos de una campaña"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM ppc_campaigns
                WHERE campaign_id = ?
            ''', (campaign_id,))

            row = cursor.fetchone()
            conn.close()

            return dict(row) if row else None

        except Exception as e:
            logging.error(f"Error getting campaign: {e}")
            return None

    def get_all_campaigns(self) -> List[Dict]:
        """Obtiene todas las campañas"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM ppc_campaigns
                ORDER BY created_at DESC
            ''')

            campaigns = [dict(row) for row in cursor.fetchall()]
            
            # Agregar métricas agregadas
            for campaign in campaigns:
                campaign_id = campaign['campaign_id']
                metrics = self.get_campaign_metrics(campaign_id)
                campaign.update(metrics)
            
            conn.close()
            return campaigns

        except Exception as e:
            logging.error(f"Error getting campaigns: {e}")
            return []

    def get_campaign_keywords(self, campaign_id: str) -> List[Dict]:
        """Obtiene keywords de una campaña"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM ppc_keywords
                WHERE campaign_id = ?
                ORDER BY spend DESC, acos ASC
            ''', (campaign_id,))

            keywords = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return keywords

        except Exception as e:
            logging.error(f"Error getting keywords: {e}")
            return []

    def get_campaign_metrics(self, campaign_id: str, days: int = 30) -> Dict:
        """Obtiene métricas agregadas de una campaña"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Métricas de keywords
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_keywords,
                    SUM(clicks) as total_clicks,
                    SUM(impressions) as total_impressions,
                    SUM(spend) as total_spend,
                    SUM(sales) as total_sales,
                    SUM(revenue) as total_revenue,
                    AVG(acos) as avg_acos,
                    AVG(ctr) as avg_ctr
                FROM ppc_keywords
                WHERE campaign_id = ? AND status = 'active'
            ''', (campaign_id,))

            kw_row = cursor.fetchone()
            
            # Métricas de performance reciente
            cursor.execute('''
                SELECT 
                    SUM(clicks) as total_clicks,
                    SUM(impressions) as total_impressions,
                    SUM(spend) as total_spend,
                    SUM(sales) as total_sales,
                    SUM(revenue) as total_revenue,
                    AVG(acos) as avg_acos,
                    AVG(tacos) as avg_tacos,
                    AVG(roas) as avg_roas
                FROM ppc_performance
                WHERE campaign_id = ? 
                AND date >= date('now', '-' || ? || ' days')
            ''', (campaign_id, days))

            perf_row = cursor.fetchone()
            conn.close()

            total_revenue = (kw_row[5] or 0) if kw_row else 0
            total_spend = (kw_row[3] or 0) if kw_row else 0
            total_sales = (kw_row[4] or 0) if kw_row else 0

            # Calcular ACOS total
            overall_acos = (total_spend / total_revenue * 100) if total_revenue > 0 else 0

            return {
                'total_keywords': kw_row[0] if kw_row else 0,
                'total_clicks': kw_row[1] if kw_row else 0,
                'total_impressions': kw_row[2] if kw_row else 0,
                'total_spend': round(total_spend, 2),
                'total_sales': total_sales,
                'total_revenue': round(total_revenue, 2),
                'overall_acos': round(overall_acos, 2),
                'avg_acos': round(kw_row[6] or 0, 2) if kw_row else 0,
                'avg_ctr': round((kw_row[7] or 0) * 100, 2) if kw_row else 0,
                'roas': round(total_revenue / total_spend, 2) if total_spend > 0 else 0
            }

        except Exception as e:
            logging.error(f"Error getting campaign metrics: {e}")
            return {}

