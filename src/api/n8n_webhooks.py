"""
n8n Webhooks - Sistema completo con 25+ tipos de eventos
Automatización total para flujos n8n
"""
import requests
import sqlite3
import logging
import json
from datetime import datetime
from src.api.webhook_sender import WebhookSender

logging.basicConfig(level=logging.INFO)


class N8NWebhookManager:
    """Manager especializado para n8n con eventos granulares"""

    # TODOS LOS EVENTOS POSIBLES
    WEBHOOK_EVENTS = {
        # Oportunidades
        'opportunity_found': 'Nueva oportunidad detectada',
        'high_roi_opportunity': 'Oportunidad con ROI > 50%',
        'ultra_high_roi': 'Oportunidad con ROI > 100%',
        'low_competition_opportunity': 'Oportunidad con baja competencia',
        'trending_opportunity': 'Producto trending con buena oportunidad',

        # Precios
        'price_drop': 'Precio bajó',
        'price_drop_significant': 'Precio bajó > 20%',
        'supplier_price_drop': 'Precio proveedor bajó',
        'amazon_price_increase': 'Precio Amazon subió',
        'price_match': 'Precio Amazon = Precio objetivo',

        # BSR y Demanda
        'bsr_improved': 'BSR mejoró',
        'bsr_improved_significant': 'BSR mejoró > 1000 posiciones',
        'bsr_declined': 'BSR empeoró',
        'demand_increasing': 'Demanda aumentando rápidamente',
        'demand_decreasing': 'Demanda bajando',

        # Competencia
        'competition_decreased': 'Competencia bajó',
        'competition_increased': 'Competencia aumentó',
        'seller_left_market': 'Seller salió del mercado',
        'new_competitor': 'Nuevo competidor detectado',
        'buybox_won': 'Buy Box ganado',
        'buybox_lost': 'Buy Box perdido',

        # Categorías y Trends
        'hot_category_detected': 'Categoría caliente detectada',
        'category_trend_change': 'Cambio de tendencia en categoría',
        'seasonal_trend': 'Tendencia estacional detectada',

        # Alertas Críticas
        'stock_low': 'Stock bajo',
        'review_spike': 'Spike de reviews',
        'negative_review_spike': 'Spike de reviews negativas',
        'rating_dropped': 'Rating bajó',

        # Escaneo
        'scan_completed': 'Escaneo completado',
        'scan_failed': 'Escaneo falló',
        'daily_scan_completed': 'Escaneo diario completado',

        # Keywords
        'keyword_opportunity': 'Keyword con poca competencia',
        'keyword_trending': 'Keyword en tendencia',

        # PPC
        'ppc_profitable': 'PPC sería rentable',
        'ppc_not_profitable': 'PPC no rentable',

        # Sistema
        'database_full': 'Base de datos llena',
        'error_occurred': 'Error en el sistema'
    }

    def __init__(self):
        self.sender = WebhookSender()

    # ==================== OPORTUNIDADES ====================

    def trigger_opportunity_found(self, opportunity):
        """Oportunidad general encontrada"""
        self.sender.send_event('opportunity_found', {
            'asin': opportunity.get('asin'),
            'product_name': opportunity.get('product_name'),
            'amazon_price': opportunity.get('amazon_price'),
            'supplier_price': opportunity.get('supplier_price'),
            'supplier': opportunity.get('supplier_name'),
            'roi': opportunity.get('roi_percent'),
            'profit': opportunity.get('net_profit'),
            'category': opportunity.get('category'),
            'competitiveness': opportunity.get('competitiveness_level'),
            'url': f"https://www.amazon.com/dp/{opportunity.get('asin')}",
            'dashboard_url': f"http://localhost:4994/opportunities"
        })

        # Trigger adicionales según ROI
        roi = opportunity.get('roi_percent', 0)

        if roi >= 100:
            self.trigger_ultra_high_roi(opportunity)
        elif roi >= 50:
            self.trigger_high_roi(opportunity)

    def trigger_high_roi(self, opportunity):
        """ROI > 50%"""
        self.sender.send_event('high_roi_opportunity', {
            'asin': opportunity.get('asin'),
            'product_name': opportunity.get('product_name'),
            'roi': opportunity.get('roi_percent'),
            'profit': opportunity.get('net_profit'),
            'amazon_price': opportunity.get('amazon_price'),
            'supplier_price': opportunity.get('supplier_price'),
            'urgency': 'HIGH',
            'action_required': 'REVISAR INMEDIATAMENTE',
            'url': f"https://www.amazon.com/dp/{opportunity.get('asin')}"
        })

    def trigger_ultra_high_roi(self, opportunity):
        """ROI > 100% - URGENTE"""
        self.sender.send_event('ultra_high_roi', {
            'asin': opportunity.get('asin'),
            'product_name': opportunity.get('product_name'),
            'roi': opportunity.get('roi_percent'),
            'profit': opportunity.get('net_profit'),
            'amazon_price': opportunity.get('amazon_price'),
            'supplier_price': opportunity.get('supplier_price'),
            'urgency': 'CRITICAL',
            'action_required': 'COMPRAR YA',
            'recommended_quantity': 100,
            'url': f"https://www.amazon.com/dp/{opportunity.get('asin')}"
        })

    def trigger_low_competition(self, opportunity, seller_count):
        """Baja competencia (< 10 sellers)"""
        self.sender.send_event('low_competition_opportunity', {
            'asin': opportunity.get('asin'),
            'product_name': opportunity.get('product_name'),
            'seller_count': seller_count,
            'roi': opportunity.get('roi_percent'),
            'profit': opportunity.get('net_profit'),
            'reason': f'Solo {seller_count} sellers - fácil entrar',
            'url': f"https://www.amazon.com/dp/{opportunity.get('asin')}"
        })

    # ==================== PRECIOS ====================

    def trigger_price_drop(self, asin, product_name, old_price, new_price, source='amazon'):
        """Precio bajó"""
        change_percent = ((old_price - new_price) / old_price * 100) if old_price > 0 else 0

        event_type = 'price_drop_significant' if change_percent >= 20 else 'price_drop'

        self.sender.send_event(event_type, {
            'asin': asin,
            'product_name': product_name,
            'source': source,
            'old_price': old_price,
            'new_price': new_price,
            'change_amount': round(old_price - new_price, 2),
            'change_percent': round(change_percent, 2),
            'urgency': 'HIGH' if change_percent >= 20 else 'MEDIUM',
            'url': f"https://www.amazon.com/dp/{asin}"
        })

    def trigger_supplier_price_drop(self, asin, product_name, supplier, old_price, new_price):
        """Precio de proveedor bajó"""
        self.sender.send_event('supplier_price_drop', {
            'asin': asin,
            'product_name': product_name,
            'supplier': supplier,
            'old_price': old_price,
            'new_price': new_price,
            'savings': round(old_price - new_price, 2),
            'action': 'ACTUALIZAR CÁLCULOS DE ROI',
            'url': f"https://www.amazon.com/dp/{asin}"
        })

    # ==================== BSR Y DEMANDA ====================

    def trigger_bsr_change(self, asin, product_name, old_bsr, new_bsr):
        """Cambio en BSR"""
        change = old_bsr - new_bsr  # Positivo = mejoró
        trend = 'improving' if change > 0 else 'declining'

        if abs(change) >= 1000:
            event_type = 'bsr_improved_significant' if change > 0 else 'bsr_declined'
            urgency = 'HIGH'
        else:
            event_type = 'bsr_improved' if change > 0 else 'bsr_declined'
            urgency = 'MEDIUM'

        self.sender.send_event(event_type, {
            'asin': asin,
            'product_name': product_name,
            'old_bsr': old_bsr,
            'new_bsr': new_bsr,
            'change': abs(change),
            'trend': trend,
            'urgency': urgency,
            'interpretation': 'DEMANDA AUMENTANDO' if change > 0 else 'DEMANDA BAJANDO',
            'url': f"https://www.amazon.com/dp/{asin}"
        })

    def trigger_demand_change(self, asin, product_name, direction, magnitude):
        """Cambio de demanda"""
        event_type = 'demand_increasing' if direction == 'up' else 'demand_decreasing'

        self.sender.send_event(event_type, {
            'asin': asin,
            'product_name': product_name,
            'direction': direction,
            'magnitude': magnitude,
            'action': 'AUMENTAR STOCK' if direction == 'up' else 'REDUCIR PEDIDOS',
            'url': f"https://www.amazon.com/dp/{asin}"
        })

    # ==================== COMPETENCIA ====================

    def trigger_competition_change(self, asin, product_name, old_count, new_count):
        """Cambio en número de sellers"""
        change = new_count - old_count

        if change < 0:
            event_type = 'competition_decreased'
            message = f'{abs(change)} sellers salieron'
            action = 'OPORTUNIDAD PARA ENTRAR'
        else:
            event_type = 'competition_increased'
            message = f'{change} sellers nuevos'
            action = 'MONITOREAR PRECIOS'

        self.sender.send_event(event_type, {
            'asin': asin,
            'product_name': product_name,
            'old_seller_count': old_count,
            'new_seller_count': new_count,
            'change': change,
            'message': message,
            'action': action,
            'url': f"https://www.amazon.com/dp/{asin}"
        })

    def trigger_buybox_change(self, asin, product_name, won=True, seller_name=''):
        """Cambio de Buy Box"""
        event_type = 'buybox_won' if won else 'buybox_lost'

        self.sender.send_event(event_type, {
            'asin': asin,
            'product_name': product_name,
            'status': 'WON' if won else 'LOST',
            'seller': seller_name,
            'urgency': 'HIGH',
            'action': 'CELEBRAR' if won else 'AJUSTAR PRECIO',
            'url': f"https://www.amazon.com/dp/{asin}"
        })

    # ==================== CATEGORÍAS ====================

    def trigger_hot_category(self, category, trending_count, avg_roi):
        """Categoría caliente detectada"""
        self.sender.send_event('hot_category_detected', {
            'category': category,
            'trending_products': trending_count,
            'avg_roi': avg_roi,
            'action': 'BUSCAR MÁS PRODUCTOS EN ESTA CATEGORÍA',
            'dashboard_url': f"http://localhost:4994/trends"
        })

    def trigger_seasonal_trend(self, category, season, confidence):
        """Tendencia estacional"""
        self.sender.send_event('seasonal_trend', {
            'category': category,
            'season': season,
            'confidence': confidence,
            'action': 'PREPARAR STOCK PARA TEMPORADA',
            'examples': ['Black Friday', 'Navidad', 'Back to School']
        })

    # ==================== KEYWORDS ====================

    def trigger_keyword_opportunity(self, keyword, competition_score, search_volume_estimate):
        """Keyword con oportunidad"""
        self.sender.send_event('keyword_opportunity', {
            'keyword': keyword,
            'competition_score': competition_score,
            'competition_level': 'BAJA' if competition_score < 40 else 'MEDIA',
            'search_volume_estimate': search_volume_estimate,
            'action': 'CREAR LISTING CON ESTE KEYWORD',
            'urgency': 'HIGH' if competition_score < 30 else 'MEDIUM'
        })

    # ==================== PPC ====================

    def trigger_ppc_analysis(self, product_data, ppc_analysis):
        """Resultado de análisis PPC"""
        profitable = ppc_analysis.get('roi_projection', {}).get('profitable', False)

        event_type = 'ppc_profitable' if profitable else 'ppc_not_profitable'

        self.sender.send_event(event_type, {
            'asin': product_data.get('asin'),
            'product_name': product_data.get('product_name'),
            'profitable': profitable,
            'estimated_roi': ppc_analysis.get('roi_projection', {}).get('roi_percent', 0),
            'recommended_budget': ppc_analysis.get('budget', {}).get('daily_budget', 0),
            'recommended_cpc': ppc_analysis.get('cpc', {}).get('recommended_bid', 0),
            'action': ppc_analysis.get('recommendation', {}).get('decision', 'EVALUAR'),
            'reason': ppc_analysis.get('recommendation', {}).get('reason', '')
        })

    # ==================== ESCANEO ====================

    def trigger_scan_completed(self, stats):
        """Escaneo completado"""
        self.sender.send_event('scan_completed', {
            'total_scanned': stats.get('total_scanned', 0),
            'opportunities_found': stats.get('total_opportunities', 0),
            'completion_time': stats.get('completion_time'),
            'scan_date': stats.get('scan_date'),
            'summary': f"Escaneados {stats.get('total_scanned', 0)} productos, encontradas {stats.get('total_opportunities', 0)} oportunidades",
            'dashboard_url': 'http://localhost:4994/opportunities'
        })

    def trigger_daily_scan_completed(self, stats, top_opportunities):
        """Escaneo diario completado"""
        self.sender.send_event('daily_scan_completed', {
            'total_scanned': stats.get('total_scanned', 0),
            'opportunities_found': stats.get('total_opportunities', 0),
            'top_opportunities': top_opportunities[:5],  # Top 5
            'best_roi': max([o.get('roi_percent', 0) for o in top_opportunities]) if top_opportunities else 0,
            'avg_roi': sum([o.get('roi_percent', 0) for o in top_opportunities]) / len(top_opportunities) if top_opportunities else 0,
            'completion_time': stats.get('completion_time'),
            'scan_date': stats.get('scan_date'),
            'dashboard_url': 'http://localhost:4994/opportunities'
        })

    # ==================== SISTEMA ====================

    def trigger_error(self, error_type, error_message, context=None):
        """Error en el sistema"""
        self.sender.send_event('error_occurred', {
            'error_type': error_type,
            'error_message': error_message,
            'context': context or {},
            'timestamp': datetime.now().isoformat(),
            'urgency': 'HIGH',
            'action': 'REVISAR LOGS'
        })

    # ==================== HELPERS ====================

    def get_all_events(self):
        """Retorna todos los eventos disponibles"""
        return self.WEBHOOK_EVENTS

    def test_webhook(self, webhook_url):
        """Test de webhook"""
        try:
            response = requests.post(
                webhook_url,
                json={
                    'event': 'test',
                    'message': 'Test webhook from NOLIVOS FBA',
                    'timestamp': datetime.now().isoformat(),
                    'status': 'success'
                },
                timeout=10
            )

            return {
                'success': response.status_code in [200, 201, 204],
                'status_code': response.status_code,
                'response': response.text[:200]
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
n8n_webhooks = N8NWebhookManager()
