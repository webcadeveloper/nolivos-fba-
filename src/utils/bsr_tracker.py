"""
BSR Tracker - Guarda histórico de BSR, precio, reviews para análisis de tendencias
Similar a Keepa/Jungle Scout
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from src.api.n8n_webhooks import n8n_webhooks

logging.basicConfig(level=logging.INFO)


class BSRTracker:
    """Trackea BSR histórico para detectar tendencias y predecir demanda"""

    def __init__(self, db_path='product_history.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Crea tablas para histórico de productos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Tabla de snapshots diarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Datos de ventas
                bsr INTEGER,
                category TEXT,
                estimated_monthly_sales INTEGER,

                -- Precios
                amazon_price REAL,

                -- Reviews
                review_count INTEGER,
                review_rating REAL,

                -- Competencia
                seller_count INTEGER,
                buybox_price REAL,

                -- Metadata
                product_name TEXT,
                date DATE DEFAULT (date('now'))
            )
        ''')

        # Índices para búsquedas rápidas
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_asin_date
            ON product_snapshots(asin, date DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_date
            ON product_snapshots(date DESC)
        ''')

        # Tabla de tendencias calculadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_trends (
                asin TEXT PRIMARY KEY,
                product_name TEXT,
                category TEXT,

                -- Trend indicators
                bsr_trend TEXT,  -- 'rising', 'falling', 'stable'
                bsr_change_30d INTEGER,
                bsr_change_percent REAL,

                demand_trend TEXT,  -- 'increasing', 'decreasing', 'stable'
                sales_change_30d INTEGER,

                price_trend TEXT,  -- 'rising', 'falling', 'stable'
                price_change_30d REAL,

                competition_trend TEXT,  -- 'increasing', 'decreasing', 'stable'
                seller_change_30d INTEGER,

                -- AI Analysis
                ai_recommendation TEXT,
                ai_confidence REAL,
                ai_analysis TEXT,

                -- Scores
                opportunity_score INTEGER,  -- 0-100
                trend_score INTEGER,  -- 0-100

                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        logging.info("BSR Tracker database initialized")

    def save_snapshot(self, product_data):
        """
        Guarda snapshot diario del producto

        Args:
            product_data: dict con datos del producto
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO product_snapshots
            (asin, bsr, category, estimated_monthly_sales, amazon_price,
             review_count, review_rating, seller_count, buybox_price, product_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_data.get('asin'),
            product_data.get('bsr'),
            product_data.get('category'),
            product_data.get('estimated_monthly_sales'),
            product_data.get('amazon_price'),
            product_data.get('review_count', 0),
            product_data.get('review_rating', 0),
            product_data.get('seller_count', 0),
            product_data.get('buybox_price', 0),
            product_data.get('product_name', '')[:200]
        ))

        conn.commit()
        conn.close()

    def get_history(self, asin, days=30):
        """Obtiene histórico de un producto"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM product_snapshots
            WHERE asin = ?
            AND date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC
        ''', (asin, days))

        history = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return history

    def calculate_trends(self, asin):
        """
        Calcula tendencias para un producto basado en histórico

        Returns:
            dict con análisis de tendencias
        """
        history = self.get_history(asin, days=30)

        if len(history) < 2:
            return None

        # Ordenar por fecha (más antiguo primero)
        history.sort(key=lambda x: x['date'])

        latest = history[-1]
        oldest = history[0]

        # Calcular cambios
        bsr_change = oldest['bsr'] - latest['bsr'] if oldest['bsr'] and latest['bsr'] else 0
        bsr_change_percent = (bsr_change / oldest['bsr'] * 100) if oldest['bsr'] else 0

        sales_change = latest.get('estimated_monthly_sales', 0) - oldest.get('estimated_monthly_sales', 0)
        price_change = latest['amazon_price'] - oldest['amazon_price'] if latest['amazon_price'] and oldest['amazon_price'] else 0
        seller_change = latest.get('seller_count', 0) - oldest.get('seller_count', 0)

        # Determinar tendencias
        # BSR: menor = mejor, entonces si bsr_change > 0 significa que el BSR bajó (mejoró)
        if bsr_change > 1000:
            bsr_trend = '🚀 Mejorando rápido'
            demand_trend = '📈 Aumentando'
        elif bsr_change > 0:
            bsr_trend = '📈 Mejorando'
            demand_trend = '↗️ Creciendo'
        elif bsr_change < -1000:
            bsr_trend = '📉 Empeorando rápido'
            demand_trend = '📉 Disminuyendo'
        elif bsr_change < 0:
            bsr_trend = '↘️ Empeorando'
            demand_trend = '↘️ Bajando'
        else:
            bsr_trend = '➡️ Estable'
            demand_trend = '➡️ Estable'

        if price_change > 2:
            price_trend = '📈 Subiendo'
        elif price_change < -2:
            price_trend = '📉 Bajando'
        else:
            price_trend = '➡️ Estable'

        if seller_change > 5:
            competition_trend = '⚠️ Aumentando rápido'
        elif seller_change > 0:
            competition_trend = '↗️ Aumentando'
        elif seller_change < -5:
            competition_trend = '✅ Disminuyendo rápido'
        elif seller_change < 0:
            competition_trend = '↘️ Disminuyendo'
        else:
            competition_trend = '➡️ Estable'

        # Calcular opportunity score (0-100)
        score = 50  # Base score

        # BSR mejorando = más puntos
        if bsr_change > 1000:
            score += 25
        elif bsr_change > 0:
            score += 15

        # Precio estable o bajando = bueno
        if price_change <= 0:
            score += 10

        # Competencia bajando = muy bueno
        if seller_change < 0:
            score += 15
        elif seller_change > 5:
            score -= 20

        score = max(0, min(100, score))

        trends = {
            'asin': asin,
            'product_name': latest['product_name'],
            'category': latest['category'],

            'bsr_trend': bsr_trend,
            'bsr_change_30d': bsr_change,
            'bsr_change_percent': round(bsr_change_percent, 2),

            'demand_trend': demand_trend,
            'sales_change_30d': sales_change,

            'price_trend': price_trend,
            'price_change_30d': round(price_change, 2),

            'competition_trend': competition_trend,
            'seller_change_30d': seller_change,

            'opportunity_score': score,

            'current_bsr': latest['bsr'],
            'current_price': latest['amazon_price'],
            'current_sellers': latest.get('seller_count', 0),

            'history_days': len(history)
        }

        # 🔥 WEBHOOKS: Enviar notificaciones de cambios significativos
        try:
            # BSR change webhook
            if abs(bsr_change) >= 1000 and oldest['bsr'] and latest['bsr']:
                n8n_webhooks.trigger_bsr_change(
                    asin, latest['product_name'], oldest['bsr'], latest['bsr']
                )

            # Price change webhook (más de $2)
            if abs(price_change) >= 2.0 and oldest['amazon_price'] and latest['amazon_price']:
                if price_change < 0:  # Precio bajó
                    n8n_webhooks.trigger_price_drop(
                        asin, latest['product_name'],
                        oldest['amazon_price'], latest['amazon_price'],
                        source='amazon'
                    )

            # Competition change webhook
            if abs(seller_change) >= 3:
                n8n_webhooks.trigger_competition_change(
                    asin, latest['product_name'],
                    oldest.get('seller_count', 0), latest.get('seller_count', 0)
                )

            # Demand change webhook
            if abs(bsr_change) >= 1000:
                direction = 'up' if bsr_change > 0 else 'down'
                magnitude = abs(bsr_change)
                n8n_webhooks.trigger_demand_change(
                    asin, latest['product_name'], direction, magnitude
                )

        except Exception as webhook_error:
            logging.warning(f"Error enviando webhooks de tendencias: {webhook_error}")

        return trends

    def save_trend_analysis(self, trend_data):
        """Guarda análisis de tendencias calculado"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO product_trends
            (asin, product_name, category, bsr_trend, bsr_change_30d, bsr_change_percent,
             demand_trend, sales_change_30d, price_trend, price_change_30d,
             competition_trend, seller_change_30d, opportunity_score, trend_score,
             ai_recommendation, ai_confidence, ai_analysis, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            trend_data['asin'],
            trend_data.get('product_name', ''),
            trend_data.get('category', ''),
            trend_data['bsr_trend'],
            trend_data['bsr_change_30d'],
            trend_data['bsr_change_percent'],
            trend_data['demand_trend'],
            trend_data['sales_change_30d'],
            trend_data['price_trend'],
            trend_data['price_change_30d'],
            trend_data['competition_trend'],
            trend_data['seller_change_30d'],
            trend_data['opportunity_score'],
            trend_data.get('trend_score', 50),
            trend_data.get('ai_recommendation'),
            trend_data.get('ai_confidence'),
            trend_data.get('ai_analysis')
        ))

        conn.commit()
        conn.close()

    def get_trending_products(self, limit=50):
        """Obtiene productos con mejor tendencia (BSR mejorando)"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM product_trends
            WHERE bsr_change_30d > 0
            ORDER BY opportunity_score DESC, bsr_change_30d DESC
            LIMIT ?
        ''', (limit,))

        trending = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return trending

    def get_hot_categories(self):
        """Identifica categorías con más productos en tendencia alcista"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                category,
                COUNT(*) as trending_products,
                AVG(bsr_change_30d) as avg_bsr_improvement,
                AVG(opportunity_score) as avg_score
            FROM product_trends
            WHERE bsr_change_30d > 0
            GROUP BY category
            ORDER BY trending_products DESC, avg_bsr_improvement DESC
            LIMIT 10
        ''')

        categories = []
        for row in cursor.fetchall():
            cat_data = {
                'category': row[0],
                'trending_products': row[1],
                'avg_bsr_improvement': round(row[2], 0) if row[2] else 0,
                'avg_score': round(row[3], 1) if row[3] else 0
            }
            categories.append(cat_data)

            # 🔥 WEBHOOK: Notificar categorías calientes (5+ productos trending)
            try:
                if cat_data['trending_products'] >= 5 and cat_data['avg_score'] >= 60:
                    n8n_webhooks.trigger_hot_category(
                        cat_data['category'],
                        cat_data['trending_products'],
                        cat_data['avg_score']
                    )
            except Exception as webhook_error:
                logging.warning(f"Error enviando webhook de categoría caliente: {webhook_error}")

        conn.close()
        return categories
