"""
PPC Calculator - Calcula costos y ROI de Amazon PPC (Sponsored Products)
"""
import logging

logging.basicConfig(level=logging.INFO)


class PPCCalculator:
    """Calcula costos de Amazon PPC y rentabilidad"""

    # CPC promedio por categoría (estimados)
    AVERAGE_CPC_BY_CATEGORY = {
        'electronics': 1.50,
        'home-kitchen': 0.80,
        'toys': 0.65,
        'sports': 0.75,
        'health': 1.20,
        'beauty': 1.10,
        'pet-supplies': 0.70,
        'office': 0.60,
        'clothing': 0.85,
        'default': 1.00
    }

    def __init__(self, product_price, product_cost, category='default'):
        self.product_price = product_price
        self.product_cost = product_cost
        self.category = category
        self.avg_cpc = self.AVERAGE_CPC_BY_CATEGORY.get(category, 1.00)

    def calculate_acos_target(self):
        """
        Calcula ACOS objetivo (Advertising Cost of Sale)

        ACOS = (Costo PPC / Ventas) * 100
        ACOS Objetivo = Margen de ganancia deseado
        """
        # Calcular margen base (sin PPC)
        margin = self.product_price - self.product_cost

        if self.product_price == 0:
            return 0

        # ACOS máximo = margen / precio * 100
        max_acos = (margin / self.product_price) * 100

        # ACOS objetivo conservador = 70% del máximo
        target_acos = max_acos * 0.7

        return {
            'max_acos': round(max_acos, 2),
            'target_acos': round(target_acos, 2),
            'recommended_acos': round(target_acos, 2),
            'breakeven_acos': round(max_acos, 2)
        }

    def calculate_cpc_bid(self, target_acos, conversion_rate=0.10):
        """
        Calcula CPC bid basado en ACOS objetivo

        Args:
            target_acos: ACOS objetivo (%)
            conversion_rate: Tasa de conversión (default 10%)

        Returns:
            dict con bid recomendado
        """
        # CPC Max = (Precio * ACOS Target) * Conversion Rate
        max_cpc = (self.product_price * (target_acos / 100)) * conversion_rate

        # Bid recomendado = 80% del máximo (para tener margen)
        recommended_bid = max_cpc * 0.8

        return {
            'max_cpc': round(max_cpc, 2),
            'recommended_bid': round(recommended_bid, 2),
            'category_avg_cpc': self.avg_cpc,
            'competitive': 'Sí' if recommended_bid >= self.avg_cpc else 'No'
        }

    def calculate_daily_budget(self, target_sales_per_day=10, conversion_rate=0.10):
        """
        Calcula presupuesto diario necesario

        Args:
            target_sales_per_day: Ventas objetivo por día
            conversion_rate: Tasa de conversión

        Returns:
            dict con presupuesto
        """
        # Clicks necesarios = Ventas / Conversion Rate
        clicks_needed = target_sales_per_day / conversion_rate

        # Budget = Clicks * CPC
        daily_budget = clicks_needed * self.avg_cpc

        return {
            'target_sales': target_sales_per_day,
            'clicks_needed': round(clicks_needed, 0),
            'daily_budget': round(daily_budget, 2),
            'monthly_budget': round(daily_budget * 30, 2)
        }

    def calculate_ppc_roi(self, monthly_ad_spend, conversion_rate=0.10):
        """
        Calcula ROI de campaña PPC

        Args:
            monthly_ad_spend: Gasto mensual en ads
            conversion_rate: Tasa de conversión

        Returns:
            dict con análisis de ROI
        """
        # Clicks = Gasto / CPC
        total_clicks = monthly_ad_spend / self.avg_cpc

        # Sales = Clicks * Conversion Rate
        estimated_sales = total_clicks * conversion_rate

        # Revenue = Sales * Price
        revenue = estimated_sales * self.product_price

        # Profit = Revenue - (Product Cost * Sales) - Ad Spend
        product_costs = self.product_cost * estimated_sales
        profit = revenue - product_costs - monthly_ad_spend

        # ROI = (Profit / Ad Spend) * 100
        roi = (profit / monthly_ad_spend * 100) if monthly_ad_spend > 0 else 0

        # ACOS Real
        acos = (monthly_ad_spend / revenue * 100) if revenue > 0 else 0

        return {
            'monthly_ad_spend': monthly_ad_spend,
            'estimated_clicks': round(total_clicks, 0),
            'estimated_sales': round(estimated_sales, 0),
            'estimated_revenue': round(revenue, 2),
            'estimated_profit': round(profit, 2),
            'roi_percent': round(roi, 2),
            'acos_percent': round(acos, 2),
            'profitable': profit > 0
        }

    def full_ppc_analysis(self, target_sales_per_day=10, conversion_rate=0.10):
        """Análisis completo de PPC"""

        acos_targets = self.calculate_acos_target()
        cpc_bid = self.calculate_cpc_bid(acos_targets['target_acos'], conversion_rate)
        daily_budget = self.calculate_daily_budget(target_sales_per_day, conversion_rate)
        monthly_roi = self.calculate_ppc_roi(daily_budget['monthly_budget'], conversion_rate)

        return {
            'product_price': self.product_price,
            'product_cost': self.product_cost,
            'category': self.category,
            'conversion_rate': conversion_rate,

            'acos': acos_targets,
            'cpc': cpc_bid,
            'budget': daily_budget,
            'roi_projection': monthly_roi,

            'recommendation': self._get_recommendation(monthly_roi, cpc_bid)
        }

    def _get_recommendation(self, roi_data, cpc_data):
        """Genera recomendación basada en análisis"""

        if not roi_data['profitable']:
            return {
                'decision': '❌ NO LANZAR PPC',
                'reason': 'No será rentable con estos números',
                'suggestion': 'Reduce costos de producto o aumenta precio'
            }

        if roi_data['roi_percent'] >= 100:
            return {
                'decision': '🟢 LANZAR PPC',
                'reason': f"ROI excelente: {roi_data['roi_percent']:.1f}%",
                'suggestion': 'Escala el presupuesto gradualmente'
            }

        elif roi_data['roi_percent'] >= 50:
            return {
                'decision': '🟡 LANZAR CON PRECAUCIÓN',
                'reason': f"ROI moderado: {roi_data['roi_percent']:.1f}%",
                'suggestion': 'Empieza con presupuesto bajo y optimiza'
            }

        else:
            return {
                'decision': '🟠 EVALUAR MÁS',
                'reason': f"ROI bajo: {roi_data['roi_percent']:.1f}%",
                'suggestion': 'Mejora conversion rate o reduce CPC'
            }

    def simulate_campaign(self, budget: float, target_acos: float, keywords: list, 
                         conversion_rate: float = 0.10, default_cpc: float = None):
        """
        Simula una campaña PPC completa con múltiples keywords
        
        Args:
            budget: Presupuesto total de la campaña
            target_acos: ACOS objetivo (%)
            keywords: Lista de keywords con estructura:
                [
                    {'keyword': 'product name', 'bid': 1.50, 'estimated_cpc': 1.50},
                    ...
                ]
            conversion_rate: Tasa de conversión promedio (default 10%)
            default_cpc: CPC por defecto si no se especifica en keyword
        
        Returns:
            dict con proyección completa por keyword y total
        """
        if not keywords:
            return {
                'error': 'No keywords provided',
                'total_clicks': 0,
                'total_sales': 0,
                'total_profit': 0,
                'total_revenue': 0,
                'total_ad_spend': 0,
                'overall_acos': 0,
                'keywords': []
            }
        
        default_cpc = default_cpc or self.avg_cpc
        
        keyword_results = []
        total_clicks = 0
        total_sales = 0
        total_revenue = 0
        total_ad_spend = 0
        
        # Distribuir presupuesto proporcionalmente por bid
        total_bid_weight = sum(kw.get('bid', default_cpc) for kw in keywords)
        
        for keyword_data in keywords:
            keyword = keyword_data.get('keyword', 'Unknown')
            bid = keyword_data.get('bid', default_cpc)
            estimated_cpc = keyword_data.get('estimated_cpc', bid)
            
            # Calcular presupuesto asignado a este keyword
            # (proporcional al bid)
            keyword_budget = (bid / total_bid_weight) * budget if total_bid_weight > 0 else budget / len(keywords)
            
            # Proyección para este keyword
            clicks = keyword_budget / estimated_cpc if estimated_cpc > 0 else 0
            sales = clicks * conversion_rate
            revenue = sales * self.product_price
            ad_spend = min(keyword_budget, clicks * estimated_cpc)  # No exceder presupuesto
            
            # Calcular ganancia
            product_costs = sales * self.product_cost
            profit = revenue - product_costs - ad_spend
            
            # ACOS para este keyword
            keyword_acos = (ad_spend / revenue * 100) if revenue > 0 else 0
            
            # ROI para este keyword
            keyword_roi = (profit / ad_spend * 100) if ad_spend > 0 else 0
            
            # Estado de la keyword
            if keyword_acos <= target_acos:
                status = '🟢 Profitable'
            elif keyword_acos <= target_acos * 1.2:
                status = '🟡 Acceptable'
            else:
                status = '🔴 Needs Optimization'
            
            keyword_result = {
                'keyword': keyword,
                'bid': round(bid, 2),
                'estimated_cpc': round(estimated_cpc, 2),
                'budget_allocated': round(keyword_budget, 2),
                'projected_clicks': round(clicks, 0),
                'projected_sales': round(sales, 0),
                'projected_revenue': round(revenue, 2),
                'projected_ad_spend': round(ad_spend, 2),
                'projected_profit': round(profit, 2),
                'projected_acos': round(keyword_acos, 2),
                'projected_roi': round(keyword_roi, 2),
                'status': status,
                'meets_target': keyword_acos <= target_acos
            }
            
            keyword_results.append(keyword_result)
            
            # Acumular totales
            total_clicks += clicks
            total_sales += sales
            total_revenue += revenue
            total_ad_spend += ad_spend
        
        # Calcular métricas totales
        total_profit = total_revenue - (total_sales * self.product_cost) - total_ad_spend
        overall_acos = (total_ad_spend / total_revenue * 100) if total_revenue > 0 else 0
        overall_roi = (total_profit / total_ad_spend * 100) if total_ad_spend > 0 else 0
        
        # Ordenar keywords por profit (mejor primero)
        keyword_results.sort(key=lambda x: x['projected_profit'], reverse=True)
        
        return {
            'campaign_summary': {
                'total_budget': budget,
                'target_acos': target_acos,
                'total_keywords': len(keywords),
                'total_clicks': round(total_clicks, 0),
                'total_sales': round(total_sales, 0),
                'total_revenue': round(total_revenue, 2),
                'total_ad_spend': round(total_ad_spend, 2),
                'total_profit': round(total_profit, 2),
                'overall_acos': round(overall_acos, 2),
                'overall_roi': round(overall_roi, 2),
                'meets_target': overall_acos <= target_acos,
                'conversion_rate': conversion_rate
            },
            'keywords': keyword_results,
            'recommendations': self._get_campaign_recommendations(keyword_results, overall_acos, target_acos)
        }

    def _get_campaign_recommendations(self, keyword_results, overall_acos, target_acos):
        """Genera recomendaciones basadas en simulación"""
        recommendations = []
        
        profitable_keywords = [kw for kw in keyword_results if kw['meets_target']]
        unprofitable_keywords = [kw for kw in keyword_results if not kw['meets_target']]
        
        if overall_acos <= target_acos:
            recommendations.append({
                'type': 'success',
                'message': f'✅ Campaña proyectada es rentable (ACOS: {overall_acos:.1f}% ≤ {target_acos:.1f}%)',
                'action': 'Puedes lanzar la campaña con este presupuesto'
            })
        else:
            recommendations.append({
                'type': 'warning',
                'message': f'⚠️ ACOS proyectado ({overall_acos:.1f}%) excede objetivo ({target_acos:.1f}%)',
                'action': 'Reduce bids o elimina keywords no rentables'
            })
        
        if profitable_keywords:
            recommendations.append({
                'type': 'info',
                'message': f'🟢 {len(profitable_keywords)} keywords son rentables',
                'action': f'Considera aumentar presupuesto para: {", ".join([kw["keyword"] for kw in profitable_keywords[:3]])}'
            })
        
        if unprofitable_keywords:
            recommendations.append({
                'type': 'warning',
                'message': f'🔴 {len(unprofitable_keywords)} keywords no alcanzan objetivo ACOS',
                'action': f'Considera pausar o ajustar bids: {", ".join([kw["keyword"] for kw in unprofitable_keywords[:3]])}'
            })
        
        return recommendations
