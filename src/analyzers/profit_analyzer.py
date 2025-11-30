"""
Profit Analyzer - Compara precios de proveedores vs Amazon y calcula ganancia real
"""
import logging
from src.scrapers.supplier_scraper import SupplierScraper, SupplierPriceEstimator
from src.scrapers.product_info import ProductInfoScraper
from src.analyzers.fba_calculator import FBACalculator

logging.basicConfig(level=logging.INFO)


class ProfitAnalyzer:
    """
    Analiza la rentabilidad real de un producto comparando:
    - Precio de compra (proveedores chinos)
    - Precio de venta (Amazon)
    - Fees de Amazon
    - Ganancia neta y ROI
    """

    def __init__(self, asin, product_name=None):
        self.asin = asin
        self.product_name = product_name
        self.product_data = None
        self.supplier_data = None
        self.fba_calculation = None

    def analyze_full_profit(self):
        """
        Análisis completo de rentabilidad
        Returns dict con toda la información de ganancia
        """
        logging.info(f"Iniciando análisis de rentabilidad para ASIN: {self.asin}")

        # 1. Obtener información del producto Amazon
        product_scraper = ProductInfoScraper(self.asin)
        self.product_data = product_scraper.scrape_product_info()

        if not self.product_data:
            logging.error("No se pudo obtener información del producto")
            return {
                'success': False,
                'error': 'No se pudo obtener información del producto de Amazon'
            }

        # Usar nombre del producto para búsqueda en proveedores
        if not self.product_name:
            self.product_name = self.product_data.get('title', '')

        amazon_price = self.product_data.get('price', 0)

        logging.info(f"Producto: {self.product_name}")
        logging.info(f"Precio Amazon: ${amazon_price}")

        # 2. Buscar precios en proveedores
        supplier_scraper = SupplierScraper(self.product_name, self.asin)
        supplier_results = supplier_scraper.get_best_supplier_price()

        if not supplier_results or not supplier_results.get('best_option'):
            logging.warning("No se encontraron precios de proveedores, usando estimación")
            # Usar estimación
            estimator = SupplierPriceEstimator()
            estimation = estimator.estimate_supplier_price(amazon_price)
            supplier_price = estimation['total_estimated']
            supplier_info = {
                'supplier': 'Estimado',
                'price': estimation['estimated_price'],
                'shipping': estimation['estimated_shipping'],
                'total': supplier_price,
                'moq': 1,
                'estimated': True,
                'note': estimation['note']
            }
        else:
            best = supplier_results['best_option']
            supplier_price = best.get('total', 0)
            supplier_info = best

            # Si el precio es 0, usar estimación
            if supplier_price == 0:
                estimator = SupplierPriceEstimator()
                estimation = estimator.estimate_supplier_price(amazon_price)
                supplier_price = estimation['total_estimated']
                supplier_info.update({
                    'price': estimation['estimated_price'],
                    'shipping': estimation['estimated_shipping'],
                    'total': supplier_price,
                    'estimated': True,
                    'note': estimation['note']
                })

        logging.info(f"Precio proveedor: ${supplier_price} ({supplier_info.get('supplier', 'Unknown')})")

        # 3. Calcular fees de Amazon usando FBACalculator
        cost_data = {
            'product_cost': supplier_info.get('price', supplier_price * 0.85),
            'shipping_cost': supplier_info.get('shipping', supplier_price * 0.15),
            'month': 1  # Enero (lowest storage fees)
        }

        calculator = FBACalculator(self.product_data, cost_data)
        self.fba_calculation = calculator.calculate_all()

        # 4. Calcular ganancia y ROI reales
        net_profit = self.fba_calculation['net_profit']
        roi_percent = self.fba_calculation['roi_percent']
        margin_percent = self.fba_calculation['margin_percent']

        # 5. Calcular precio de venta óptimo (target 30% ROI mínimo)
        optimal_price = self._calculate_optimal_price(supplier_price, self.product_data)

        # 6. Análisis de competitividad
        competitiveness = self._analyze_competitiveness(
            amazon_price,
            supplier_price,
            net_profit,
            roi_percent
        )

        # 7. Preparar resultado completo
        result = {
            'success': True,
            'asin': self.asin,
            'product_name': self.product_name,

            # Precios
            'amazon_price': amazon_price,
            'supplier_price': supplier_price,
            'supplier_info': supplier_info,

            # Costos y fees
            'total_cost': self.fba_calculation['total_cost'],
            'amazon_fees': self.fba_calculation['total_fees'],
            'referral_fee': self.fba_calculation['referral_fee'],
            'fulfillment_fee': self.fba_calculation['fulfillment_fee'],
            'storage_fee': self.fba_calculation['storage_fee'],

            # Ganancia
            'net_profit': net_profit,
            'roi_percent': roi_percent,
            'margin_percent': margin_percent,

            # Recomendaciones
            'optimal_selling_price': optimal_price,
            'competitiveness': competitiveness,

            # Datos adicionales
            'all_suppliers': supplier_results.get('all_options', []) if supplier_results else [],
            'product_data': self.product_data
        }

        return result

    def _calculate_optimal_price(self, supplier_cost, product_data):
        """
        Calcula precio de venta óptimo para obtener 30-40% ROI
        """
        # Target: 30% ROI mínimo
        target_roi = 0.30

        # Estimate fees (approximately 30% of selling price for FBA)
        # Formula: selling_price = (supplier_cost * (1 + target_roi)) / (1 - 0.30)
        estimated_optimal = (supplier_cost * (1 + target_roi)) / 0.70

        # Round to .99 pricing
        optimal_price = round(estimated_optimal - 0.01, 2)

        # Get market price from product_data
        market_price = product_data.get('price', 0)

        return {
            'recommended_price': optimal_price,
            'market_price': market_price,
            'difference_from_market': market_price - optimal_price,
            'can_compete': optimal_price <= market_price,
            'target_roi': f"{int(target_roi * 100)}%",
            'note': 'Precio calculado para 30% ROI mínimo'
        }

    def _analyze_competitiveness(self, amazon_price, supplier_price, net_profit, roi_percent):
        """
        Analiza qué tan competitivo es el producto
        """
        if amazon_price <= 0 or supplier_price <= 0:
            return {
                'level': 'unknown',
                'score': 0,
                'recommendation': 'Faltan datos para análisis',
                'reasons': []
            }

        reasons = []
        score = 0

        # Factor 1: ROI (40 puntos)
        if roi_percent >= 50:
            score += 40
            reasons.append("✅ ROI excelente (50%+)")
        elif roi_percent >= 30:
            score += 30
            reasons.append("✅ ROI bueno (30-50%)")
        elif roi_percent >= 15:
            score += 20
            reasons.append("⚠️ ROI aceptable (15-30%)")
        else:
            score += 5
            reasons.append("❌ ROI bajo (<15%)")

        # Factor 2: Ganancia por unidad (30 puntos)
        if net_profit >= 15:
            score += 30
            reasons.append("✅ Ganancia alta ($15+)")
        elif net_profit >= 10:
            score += 20
            reasons.append("✅ Ganancia buena ($10-15)")
        elif net_profit >= 5:
            score += 10
            reasons.append("⚠️ Ganancia baja ($5-10)")
        else:
            score += 0
            reasons.append("❌ Ganancia muy baja (<$5)")

        # Factor 3: Relación precio compra/venta (30 puntos)
        ratio = supplier_price / amazon_price if amazon_price > 0 else 1
        if ratio <= 0.30:
            score += 30
            reasons.append("✅ Margen excelente (proveedor 30% o menos)")
        elif ratio <= 0.40:
            score += 20
            reasons.append("✅ Margen bueno (proveedor 30-40%)")
        elif ratio <= 0.50:
            score += 10
            reasons.append("⚠️ Margen justo (proveedor 40-50%)")
        else:
            score += 0
            reasons.append("❌ Margen estrecho (proveedor 50%+)")

        # Determinar nivel
        if score >= 80:
            level = '🟢 EXCELENTE'
            recommendation = 'Producto muy rentable - RECOMENDADO para FBA'
        elif score >= 60:
            level = '🟡 BUENO'
            recommendation = 'Producto rentable - Considera vender en FBA'
        elif score >= 40:
            level = '🟠 REGULAR'
            recommendation = 'Margen ajustado - Evalúa volumen de ventas'
        else:
            level = '🔴 BAJO'
            recommendation = 'No recomendado - Busca otros productos'

        return {
            'level': level,
            'score': score,
            'recommendation': recommendation,
            'reasons': reasons,
            'supplier_ratio': f"{int(ratio * 100)}%"
        }

    def get_summary_comparison(self):
        """Retorna resumen visual de comparación"""
        if not self.fba_calculation:
            return None

        return {
            'compra': {
                'proveedor': self.supplier_data.get('supplier', 'Estimado'),
                'precio': self.supplier_data.get('price', 0),
                'shipping': self.supplier_data.get('shipping', 0),
                'total': self.supplier_data.get('total', 0)
            },
            'venta': {
                'precio_amazon': self.product_data.get('price', 0),
                'fees': self.fba_calculation['total_fees'],
                'ganancia': self.fba_calculation['net_profit'],
                'roi': self.fba_calculation['roi_percent']
            },
            'decision': '✅ VENDER' if self.fba_calculation['roi_percent'] >= 30 else '❌ NO VENDER'
        }
