"""
PPC Bid Optimizer - Optimiza bids de keywords basado en performance
Nivel Helium 10
"""
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)


class PPCBidOptimizer:
    """Optimiza bids de keywords basado en performance data"""

    def __init__(self):
        pass

    def optimize_bids(self, campaign_data: Dict) -> Dict:
        """
        Analiza performance por keyword y sugiere ajustes de bid
        
        Args:
            campaign_data: Datos de la campaña con estructura:
                {
                    'target_acos': 25.0,
                    'keywords': [
                        {
                            'keyword': 'product name',
                            'current_bid': 1.50,
                            'clicks': 100,
                            'impressions': 5000,
                            'spend': 150.0,
                            'sales': 10,
                            'revenue': 200.0,
                            'acos': 75.0,
                            'ctr': 0.02,
                            'conversion_rate': 0.10
                        },
                        ...
                    ]
                }
        
        Returns:
            dict con sugerencias de optimización
        """
        target_acos = campaign_data.get('target_acos', 30.0)
        keywords = campaign_data.get('keywords', [])
        
        if not keywords:
            return {
                'error': 'No keywords provided',
                'optimizations': []
            }
        
        optimizations = []
        total_current_spend = sum(kw.get('spend', 0) for kw in keywords)
        total_projected_spend = 0
        
        for kw_data in keywords:
            keyword = kw_data.get('keyword', 'Unknown')
            current_bid = kw_data.get('current_bid', 0)
            current_acos = kw_data.get('acos', 100)
            clicks = kw_data.get('clicks', 0)
            impressions = kw_data.get('impressions', 0)
            sales = kw_data.get('sales', 0)
            revenue = kw_data.get('revenue', 0)
            ctr = kw_data.get('ctr', 0)
            conversion_rate = kw_data.get('conversion_rate', 0.10)
            
            # Calcular métricas si no están disponibles
            if ctr == 0 and impressions > 0:
                ctr = clicks / impressions
            
            if conversion_rate == 0 and clicks > 0:
                conversion_rate = sales / clicks
            
            # Analizar performance y sugerir optimización
            optimization = self._analyze_keyword_performance(
                keyword, current_bid, current_acos, target_acos,
                clicks, impressions, ctr, conversion_rate, revenue
            )
            
            optimizations.append(optimization)
            
            # Acumular spend proyectado
            if optimization.get('new_bid'):
                total_projected_spend += optimization['projected_spend']
            else:
                total_projected_spend += kw_data.get('spend', 0)
        
        # Ordenar por impacto esperado
        optimizations.sort(key=lambda x: abs(x.get('bid_change_percent', 0)), reverse=True)
        
        return {
            'target_acos': target_acos,
            'total_keywords': len(keywords),
            'current_total_spend': round(total_current_spend, 2),
            'projected_total_spend': round(total_projected_spend, 2),
            'optimizations': optimizations,
            'summary': self._generate_summary(optimizations, target_acos)
        }

    def _analyze_keyword_performance(self, keyword: str, current_bid: float,
                                    current_acos: float, target_acos: float,
                                    clicks: int, impressions: int, ctr: float,
                                    conversion_rate: float, revenue: float) -> Dict:
        """
        Analiza performance individual de una keyword y sugiere optimización
        """
        optimization = {
            'keyword': keyword,
            'current_bid': current_bid,
            'current_acos': current_acos,
            'action': 'keep',
            'new_bid': None,
            'bid_change_percent': 0,
            'reason': '',
            'projected_acos': current_acos,
            'projected_spend': 0,
            'priority': 'medium'
        }
        
        # Caso 1: ACOS mucho más alto que objetivo - REDUCIR BID
        if current_acos > target_acos * 1.5:
            # Reducir bid agresivamente
            reduction = min(0.50, (current_acos - target_acos) / current_acos)
            new_bid = current_bid * (1 - reduction)
            optimization.update({
                'action': 'decrease',
                'new_bid': round(new_bid, 2),
                'bid_change_percent': round(-reduction * 100, 1),
                'reason': f'ACOS muy alto ({current_acos:.1f}%) vs objetivo ({target_acos:.1f}%)',
                'priority': 'high'
            })
        
        # Caso 2: ACOS ligeramente sobre objetivo - REDUCIR BID LEVE
        elif current_acos > target_acos * 1.2:
            reduction = 0.20  # Reducir 20%
            new_bid = current_bid * 0.80
            optimization.update({
                'action': 'decrease',
                'new_bid': round(new_bid, 2),
                'bid_change_percent': -20.0,
                'reason': f'ACOS alto ({current_acos:.1f}%) - reducir bid moderadamente',
                'priority': 'high'
            })
        
        # Caso 3: ACOS bajo (rentable) - AUMENTAR BID para escalar
        elif current_acos < target_acos * 0.7 and clicks >= 50:
            # Aumentar bid para obtener más tráfico
            increase = min(0.30, (target_acos - current_acos) / target_acos)
            new_bid = current_bid * (1 + increase)
            optimization.update({
                'action': 'increase',
                'new_bid': round(new_bid, 2),
                'bid_change_percent': round(increase * 100, 1),
                'reason': f'ACOS bajo ({current_acos:.1f}%) - aumentar bid para escalar',
                'priority': 'medium'
            })
        
        # Caso 4: ACOS cerca del objetivo pero CTR bajo - EVALUAR
        elif target_acos * 0.8 <= current_acos <= target_acos * 1.2:
            if ctr < 0.01 and impressions >= 1000:  # CTR muy bajo
                optimization.update({
                    'action': 'evaluate',
                    'reason': f'CTR bajo ({ctr*100:.2f}%) - considerar negative keyword',
                    'priority': 'low'
                })
            else:
                optimization.update({
                    'action': 'keep',
                    'reason': f'Performance dentro del objetivo',
                    'priority': 'low'
                })
        
        # Caso 5: Sin datos suficientes
        elif clicks < 10:
            optimization.update({
                'action': 'wait',
                'reason': f'Datos insuficientes ({clicks} clicks) - necesita más tiempo',
                'priority': 'low'
            })
        
        # Calcular proyecciones si hay nuevo bid
        if optimization.get('new_bid'):
            # Proyectar nuevo ACOS basado en relación bid/ACOS
            # Asumir relación lineal: ACOS nuevo ≈ ACOS actual * (nuevo_bid / bid_actual)
            bid_ratio = optimization['new_bid'] / current_bid if current_bid > 0 else 1
            projected_acos = current_acos * bid_ratio
            
            # Proyectar nuevo spend (asumiendo mismo CTR pero con nuevo bid)
            if clicks > 0 and impressions > 0:
                projected_clicks = clicks * bid_ratio  # Más bid = más clicks (hasta cierto punto)
                projected_spend = projected_clicks * optimization['new_bid']
            else:
                projected_spend = revenue * (projected_acos / 100) if revenue > 0 else 0
            
            optimization['projected_acos'] = round(projected_acos, 2)
            optimization['projected_spend'] = round(projected_spend, 2)
        else:
            optimization['projected_acos'] = current_acos
            optimization['projected_spend'] = revenue * (current_acos / 100) if revenue > 0 else 0
        
        return optimization

    def _generate_summary(self, optimizations: List[Dict], target_acos: float) -> Dict:
        """Genera resumen de optimizaciones"""
        increase_count = sum(1 for opt in optimizations if opt.get('action') == 'increase')
        decrease_count = sum(1 for opt in optimizations if opt.get('action') == 'decrease')
        keep_count = sum(1 for opt in optimizations if opt.get('action') == 'keep')
        
        high_priority = [opt for opt in optimizations if opt.get('priority') == 'high']
        
        return {
            'total_keywords': len(optimizations),
            'increase_bids': increase_count,
            'decrease_bids': decrease_count,
            'keep_bids': keep_count,
            'high_priority': len(high_priority),
            'recommendations': [
                f'Ajustar {increase_count} bids hacia arriba para escalar',
                f'Reducir {decrease_count} bids para mejorar ACOS',
                f'{len(high_priority)} keywords requieren acción inmediata'
            ]
        }

    def calculate_target_acos(self, margin: float, desired_profit: float,
                             product_price: float, estimated_sales: float) -> Dict:
        """
        Calcula ACOS objetivo óptimo basado en margen y ganancia deseada
        
        Args:
            margin: Margen de ganancia por unidad (precio - costo)
            desired_profit: Ganancia deseada por unidad después de PPC
            product_price: Precio de venta del producto
            estimated_sales: Ventas estimadas por mes
        
        Returns:
            dict con ACOS objetivo y recomendaciones
        """
        if product_price == 0:
            return {
                'error': 'Product price cannot be zero',
                'target_acos': 0
            }
        
        # ACOS máximo = margen disponible / precio
        max_acos = (margin / product_price) * 100
        
        # ACOS objetivo = (margen - ganancia deseada) / precio * 100
        if margin > desired_profit:
            target_acos = ((margin - desired_profit) / product_price) * 100
        else:
            target_acos = max_acos * 0.7  # Conservador si no hay margen suficiente
        
        # Asegurar que no exceda el máximo
        target_acos = min(target_acos, max_acos)
        
        # Calcular presupuesto recomendado
        if estimated_sales > 0:
            monthly_revenue = estimated_sales * product_price
            recommended_budget = monthly_revenue * (target_acos / 100)
        else:
            recommended_budget = 0
        
        return {
            'max_acos': round(max_acos, 2),
            'target_acos': round(target_acos, 2),
            'breakeven_acos': round(max_acos, 2),
            'margin_per_unit': round(margin, 2),
            'desired_profit_per_unit': round(desired_profit, 2),
            'recommended_monthly_budget': round(recommended_budget, 2),
            'estimated_monthly_sales': estimated_sales,
            'recommendation': self._get_target_acos_recommendation(target_acos, max_acos)
        }

    def _get_target_acos_recommendation(self, target_acos: float, max_acos: float) -> str:
        """Genera recomendación basada en ACOS objetivo"""
        if target_acos >= max_acos * 0.9:
            return '⚠️ ACOS objetivo muy cerca del máximo - margen limitado. Considera aumentar precio o reducir costos.'
        elif target_acos >= max_acos * 0.7:
            return '✅ ACOS objetivo conservador - buen margen de seguridad.'
        else:
            return '✅ ACOS objetivo agresivo - margen excelente. Puedes escalar agresivamente.'

