"""
Calculadora Multi-Modelo de Arbitraje FBA
Soporta los 4 modelos: Retail Arbitrage, Online Arbitrage, Wholesale, Private Label/China
"""
import logging
from typing import Dict, List

logging.basicConfig(level=logging.INFO)


class ArbitrageCalculator:
    """
    Calcula ROI para los 4 modelos de arbitraje FBA
    """

    # Costos promedio de shipping a FBA warehouse (por libra)
    SHIPPING_TO_FBA = {
        'local': 0.50,      # Retail Arbitrage: llevas tú mismo o UPS Ground
        'online': 0.75,     # Online Arbitrage: ya viene con shipping
        'wholesale': 0.60,  # Wholesale: pallet shipping
        'china': 1.20       # China: incluye consolidación y envío a FBA
    }

    def __init__(self):
        pass

    def calculate_all_models(
        self,
        amazon_price: float,
        product_name: str = "",
        weight_lbs: float = 1.0,
        dimensions: tuple = (10, 8, 6),  # L, W, H en pulgadas
        category: str = "general",

        # Precios por modelo
        retail_price: float = 0,      # Precio en tienda física (Walmart, Target)
        online_price: float = 0,      # Precio en sitio web (Walmart.com, eBay)
        wholesale_price: float = 0,   # Precio mayorista (distribuidor)
        china_price: float = 0,       # Precio FOB China (Alibaba)

        # Cantidades por modelo
        retail_qty: int = 1,
        online_qty: int = 1,
        wholesale_qty: int = 100,
        china_qty: int = 500
    ) -> Dict:
        """
        Calcula ROI para LOS 4 MODELOS y devuelve comparación

        Returns:
            dict con results de cada modelo + recomendación del mejor
        """
        results = {}

        # 1. RETAIL ARBITRAGE
        if retail_price > 0:
            results['retail_arbitrage'] = self._calculate_retail_arbitrage(
                amazon_price=amazon_price,
                retail_price=retail_price,
                weight_lbs=weight_lbs,
                dimensions=dimensions,
                quantity=retail_qty
            )

        # 2. ONLINE ARBITRAGE
        if online_price > 0:
            results['online_arbitrage'] = self._calculate_online_arbitrage(
                amazon_price=amazon_price,
                online_price=online_price,
                weight_lbs=weight_lbs,
                dimensions=dimensions,
                quantity=online_qty
            )

        # 3. WHOLESALE
        if wholesale_price > 0:
            results['wholesale'] = self._calculate_wholesale(
                amazon_price=amazon_price,
                wholesale_price=wholesale_price,
                weight_lbs=weight_lbs,
                dimensions=dimensions,
                quantity=wholesale_qty
            )

        # 4. PRIVATE LABEL / CHINA
        if china_price > 0:
            results['china_import'] = self._calculate_china_import(
                amazon_price=amazon_price,
                china_price=china_price,
                weight_lbs=weight_lbs,
                dimensions=dimensions,
                quantity=china_qty,
                category=category
            )

        # Determinar el MEJOR modelo
        best_model = self._get_best_model(results)

        return {
            'product_name': product_name,
            'amazon_price': amazon_price,
            'models': results,
            'best_model': best_model,
            'comparison_table': self._create_comparison_table(results)
        }

    def _calculate_retail_arbitrage(
        self,
        amazon_price: float,
        retail_price: float,
        weight_lbs: float,
        dimensions: tuple,
        quantity: int = 1
    ) -> Dict:
        """Modelo 1: RETAIL ARBITRAGE (Compras en tienda física)"""

        # Costos
        product_cost = retail_price * quantity
        tax = retail_price * 0.08 * quantity  # Sales tax ~8%
        gas_cost = 5.00  # Promedio: gasolina para ir a la tienda

        # FBA fees
        fba_fee = self._calculate_fba_fee(amazon_price, weight_lbs, dimensions)
        referral_fee = amazon_price * 0.15

        # Shipping a FBA (llevas tú mismo o UPS)
        shipping_to_fba = weight_lbs * self.SHIPPING_TO_FBA['local'] * quantity

        # Total costs
        total_cost = product_cost + tax + gas_cost + shipping_to_fba
        total_fees = (fba_fee + referral_fee) * quantity

        # Revenue
        total_revenue = amazon_price * quantity
        net_profit = total_revenue - total_cost - total_fees

        # ROI
        roi_percent = (net_profit / total_cost) * 100 if total_cost > 0 else 0

        return {
            'model': 'Retail Arbitrage',
            'difficulty': 'Fácil ⭐',
            'capital_needed': total_cost,
            'quantity': quantity,
            'unit_cost': retail_price,
            'costs_breakdown': {
                'product_cost': product_cost,
                'sales_tax': tax,
                'gas': gas_cost,
                'shipping_to_fba': shipping_to_fba,
                'fba_fees': total_fees
            },
            'net_profit': net_profit,
            'roi_percent': roi_percent,
            'time_to_start': '1 día',
            'pros': ['Sin MOQ', 'Rápido', 'Fácil', 'Ves el producto'],
            'cons': ['No escalable', 'Requiere salir', 'Inventario limitado']
        }

    def _calculate_online_arbitrage(
        self,
        amazon_price: float,
        online_price: float,
        weight_lbs: float,
        dimensions: tuple,
        quantity: int = 1
    ) -> Dict:
        """Modelo 2: ONLINE ARBITRAGE (Compras en sitios web)"""

        # Costos
        product_cost = online_price * quantity
        shipping_from_seller = 0  # Muchos tienen free shipping o ya incluido
        if online_price < 35:  # Sin free shipping
            shipping_from_seller = 5.99 * quantity

        # FBA fees
        fba_fee = self._calculate_fba_fee(amazon_price, weight_lbs, dimensions)
        referral_fee = amazon_price * 0.15

        # Shipping a FBA
        shipping_to_fba = weight_lbs * self.SHIPPING_TO_FBA['online'] * quantity

        # Total costs
        total_cost = product_cost + shipping_from_seller + shipping_to_fba
        total_fees = (fba_fee + referral_fee) * quantity

        # Revenue
        total_revenue = amazon_price * quantity
        net_profit = total_revenue - total_cost - total_fees

        # ROI
        roi_percent = (net_profit / total_cost) * 100 if total_cost > 0 else 0

        return {
            'model': 'Online Arbitrage',
            'difficulty': 'Media ⭐⭐',
            'capital_needed': total_cost,
            'quantity': quantity,
            'unit_cost': online_price,
            'costs_breakdown': {
                'product_cost': product_cost,
                'shipping_from_seller': shipping_from_seller,
                'shipping_to_fba': shipping_to_fba,
                'fba_fees': total_fees
            },
            'net_profit': net_profit,
            'roi_percent': roi_percent,
            'time_to_start': '1 semana',
            'pros': ['Desde casa', 'Sin MOQ', 'Escalable con bots', 'Más inventario'],
            'cons': ['Competencia alta', 'Precios cambian', 'Riesgo daños']
        }

    def _calculate_wholesale(
        self,
        amazon_price: float,
        wholesale_price: float,
        weight_lbs: float,
        dimensions: tuple,
        quantity: int = 100
    ) -> Dict:
        """Modelo 3: WHOLESALE (Compras al mayoreo de distribuidores)"""

        # Costos
        product_cost = wholesale_price * quantity

        # Setup costs (solo primera vez, pero los incluimos)
        llc_cost = 200  # LLC formation (amortizado)
        tax_id_cost = 0  # Free

        # FBA fees
        fba_fee = self._calculate_fba_fee(amazon_price, weight_lbs, dimensions)
        referral_fee = amazon_price * 0.15

        # Shipping a FBA (pallet)
        shipping_to_fba = weight_lbs * self.SHIPPING_TO_FBA['wholesale'] * quantity

        # Total costs
        total_cost = product_cost + llc_cost + shipping_to_fba
        total_fees = (fba_fee + referral_fee) * quantity

        # Revenue
        total_revenue = amazon_price * quantity
        net_profit = total_revenue - total_cost - total_fees

        # ROI
        roi_percent = (net_profit / total_cost) * 100 if total_cost > 0 else 0

        return {
            'model': 'Wholesale',
            'difficulty': 'Media ⭐⭐',
            'capital_needed': total_cost,
            'quantity': quantity,
            'unit_cost': wholesale_price,
            'costs_breakdown': {
                'product_cost': product_cost,
                'llc_setup': llc_cost,
                'shipping_to_fba': shipping_to_fba,
                'fba_fees': total_fees
            },
            'net_profit': net_profit,
            'roi_percent': roi_percent,
            'time_to_start': '1-2 meses',
            'pros': ['Relación largo plazo', 'Inventario consistente', 'Profesional', 'Escalable'],
            'cons': ['Capital alto', 'MOQ alto', 'Márgenes bajos', 'Necesitas LLC']
        }

    def _calculate_china_import(
        self,
        amazon_price: float,
        china_price: float,
        weight_lbs: float,
        dimensions: tuple,
        quantity: int = 500,
        category: str = "general"
    ) -> Dict:
        """Modelo 4: PRIVATE LABEL / CHINA IMPORT"""

        # Costos del producto
        product_cost = china_price * quantity

        # Import costs
        tariff_rate = self._get_tariff_rate(category)
        tariff_cost = product_cost * tariff_rate

        # Shipping from China (sea freight)
        total_weight = weight_lbs * quantity
        shipping_from_china = total_weight * 0.50  # Sea freight: $0.50/lb

        # Additional import fees
        customs_broker = 150
        mpf_fee = max(27.75, min(538.40, product_cost * 0.003464))
        hmf_fee = product_cost * 0.00125

        # Branding costs (Private Label)
        logo_design = 300
        packaging_design = 200
        sample_cost = china_price * 5  # 5 muestras

        # FBA fees
        fba_fee = self._calculate_fba_fee(amazon_price, weight_lbs, dimensions)
        referral_fee = amazon_price * 0.15

        # Total costs
        total_cost = (
            product_cost +
            tariff_cost +
            shipping_from_china +
            customs_broker +
            mpf_fee +
            hmf_fee +
            logo_design +
            packaging_design +
            sample_cost
        )

        total_fees = (fba_fee + referral_fee) * quantity

        # Revenue
        total_revenue = amazon_price * quantity
        net_profit = total_revenue - total_cost - total_fees

        # ROI
        roi_percent = (net_profit / total_cost) * 100 if total_cost > 0 else 0

        return {
            'model': 'Private Label / China Import',
            'difficulty': 'Difícil ⭐⭐⭐⭐',
            'capital_needed': total_cost,
            'quantity': quantity,
            'unit_cost': china_price,
            'costs_breakdown': {
                'product_cost': product_cost,
                'tariff': tariff_cost,
                'shipping_from_china': shipping_from_china,
                'customs_broker': customs_broker,
                'import_fees': mpf_fee + hmf_fee,
                'branding': logo_design + packaging_design + sample_cost,
                'fba_fees': total_fees
            },
            'net_profit': net_profit,
            'roi_percent': roi_percent,
            'time_to_start': '2-4 meses',
            'pros': ['Márgenes altos', 'Tu marca', 'Escalable infinito', 'Menos competencia precio'],
            'cons': ['Capital MUY alto', 'MOQ altísimo', 'Tiempo largo', 'Riesgo alto']
        }

    def _calculate_fba_fee(self, price: float, weight_lbs: float, dimensions: tuple) -> float:
        """Calcula FBA fulfillment fee"""
        length, width, height = dimensions

        # Small standard
        if weight_lbs <= 1 and max(length, width, height) <= 15:
            return 3.22 if price >= 10 else 3.06

        # Large standard
        if weight_lbs <= 1:
            return 3.86
        elif weight_lbs <= 2:
            return 4.75
        else:
            return 4.75 + ((weight_lbs - 2) * 0.38)

    def _get_tariff_rate(self, category: str) -> float:
        """Retorna tariff rate por categoría"""
        tariff_rates = {
            'electronics': 0.00,
            'toys': 0.00,
            'clothing': 0.165,
            'shoes': 0.125,
            'home-goods': 0.065,
            'beauty': 0.00,
            'sports': 0.045,
            'automotive': 0.025,
            'general': 0.10
        }
        return tariff_rates.get(category, 0.10)

    def _get_best_model(self, results: Dict) -> Dict:
        """Determina el mejor modelo basado en ROI y dificultad"""
        if not results:
            return None

        # Ordenar por ROI
        sorted_models = sorted(
            results.items(),
            key=lambda x: x[1]['roi_percent'],
            reverse=True
        )

        best = sorted_models[0][1]

        return {
            'model_name': best['model'],
            'roi_percent': best['roi_percent'],
            'net_profit': best['net_profit'],
            'capital_needed': best['capital_needed'],
            'difficulty': best['difficulty'],
            'recommendation': self._get_recommendation(best)
        }

    def _get_recommendation(self, model: Dict) -> str:
        """Genera recomendación basada en el modelo"""
        roi = model['roi_percent']
        capital = model['capital_needed']

        if roi >= 50 and capital < 1000:
            return "🟢 EXCELENTE - Alto ROI con poco capital"
        elif roi >= 30 and capital < 2000:
            return "🟡 BUENO - ROI decente, inversión moderada"
        elif roi >= 20:
            return "🟠 MARGINAL - Solo si tienes capital y experiencia"
        else:
            return "🔴 NO RECOMENDADO - ROI muy bajo"

    def _create_comparison_table(self, results: Dict) -> List[Dict]:
        """Crea tabla comparativa de todos los modelos"""
        table = []
        for model_key, data in results.items():
            table.append({
                'model': data['model'],
                'capital': f"${data['capital_needed']:.2f}",
                'quantity': data['quantity'],
                'roi': f"{data['roi_percent']:.1f}%",
                'profit': f"${data['net_profit']:.2f}",
                'difficulty': data['difficulty'],
                'time': data['time_to_start']
            })

        # Ordenar por ROI
        table.sort(key=lambda x: float(x['roi'].replace('%', '')), reverse=True)
        return table


def test_all_models():
    """Test de los 4 modelos con el mismo producto"""
    print("=" * 80)
    print("COMPARACIÓN: Los 4 Modelos de Arbitraje FBA")
    print("=" * 80)

    calc = ArbitrageCalculator()

    # Producto ejemplo: Wireless Mouse
    result = calc.calculate_all_models(
        amazon_price=24.99,
        product_name="Logitech Wireless Mouse",
        weight_lbs=0.3,
        dimensions=(5, 3, 2),
        category='electronics',

        # Precios por modelo
        retail_price=18.99,      # Walmart en tienda
        online_price=16.49,      # Walmart.com
        wholesale_price=12.00,   # Distribuidor (MOQ 100)
        china_price=3.50,        # Alibaba FOB (MOQ 500)

        # Cantidades
        retail_qty=5,
        online_qty=10,
        wholesale_qty=100,
        china_qty=500
    )

    print(f"\n📦 Producto: {result['product_name']}")
    print(f"💰 Precio Amazon: ${result['amazon_price']}")

    print("\n" + "=" * 80)
    print("COMPARACIÓN DE MODELOS:")
    print("=" * 80)

    for item in result['comparison_table']:
        print(f"\n{item['model']} ({item['difficulty']})")
        print(f"   Capital necesario: {item['capital']}")
        print(f"   Cantidad: {item['quantity']} unidades")
        print(f"   ROI: {item['roi']}")
        print(f"   Ganancia neta: {item['profit']}")
        print(f"   Tiempo setup: {item['time']}")

    print("\n" + "=" * 80)
    print("MEJOR MODELO:")
    print("=" * 80)
    best = result['best_model']
    print(f"\n🏆 {best['model_name']}")
    print(f"   ROI: {best['roi_percent']:.1f}%")
    print(f"   Ganancia: ${best['net_profit']:.2f}")
    print(f"   Capital: ${best['capital_needed']:.2f}")
    print(f"   {best['recommendation']}")

    # Detalles del mejor
    print("\n" + "=" * 80)
    print(f"DETALLES: {best['model_name']}")
    print("=" * 80)
    best_data = result['models'][list(result['models'].keys())[0]]

    print(f"\n✅ PROS:")
    for pro in best_data['pros']:
        print(f"   • {pro}")

    print(f"\n❌ CONS:")
    for con in best_data['cons']:
        print(f"   • {con}")


if __name__ == "__main__":
    test_all_models()
