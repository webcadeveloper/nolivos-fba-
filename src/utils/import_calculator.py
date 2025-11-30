"""
Calculadora de Costos de Importación para productos desde China
Incluye: Shipping, Tariffs, Fees, Total Landed Cost
"""
import logging

logging.basicConfig(level=logging.INFO)


class ImportCostCalculator:
    """
    Calcula el costo total de importar productos desde China a USA
    Basado en FBA_MANDAMIENTOS.md y prácticas estándar de importación
    """

    # Tarifas estándar de importación USA (HTS Code dependiente)
    TARIFF_RATES = {
        'electronics': 0.00,      # Muchos electrónicos están exentos
        'toys': 0.00,              # Juguetes generalmente exentos
        'clothing': 0.165,         # 16.5% promedio
        'shoes': 0.125,            # 12.5% promedio
        'home-goods': 0.065,       # 6.5% promedio
        'beauty': 0.00,            # Cosméticos generalmente exentos
        'sports': 0.045,           # 4.5% promedio
        'automotive': 0.025,       # 2.5% promedio
        'default': 0.10            # 10% por defecto (promedio general)
    }

    # Costos de shipping aéreo desde China (por kg)
    AIR_SHIPPING_RATES = {
        'express': 8.50,      # DHL/FedEx Express (3-5 días)
        'standard': 6.00,     # Air freight estándar (7-10 días)
        'economy': 4.50       # Economía (10-15 días)
    }

    # Costos de shipping marítimo desde China (por kg)
    SEA_SHIPPING_RATES = {
        'fcl': 0.50,          # Full Container Load (30-45 días) - MUY barato
        'lcl': 1.20,          # Less than Container Load (30-45 días)
        'express': 2.00       # Sea express (20-25 días)
    }

    def __init__(self):
        pass

    def calculate_landed_cost(
        self,
        product_cost: float,
        weight_kg: float,
        category: str = 'default',
        shipping_method: str = 'air_standard',
        quantity: int = 1,
        include_customs_broker: bool = True
    ) -> dict:
        """
        Calcula el costo total de importación (landed cost)

        Args:
            product_cost: Precio del producto en China (USD por unidad)
            weight_kg: Peso del producto en kilogramos
            category: Categoría del producto (para calcular tarifa)
            shipping_method: Método de envío (air_express, air_standard, air_economy, sea_fcl, sea_lcl, sea_express)
            quantity: Cantidad de unidades a importar
            include_customs_broker: Incluir fee del customs broker ($100-200 típico)

        Returns:
            dict con breakdown completo de costos
        """
        try:
            # 1. Costo del producto (FOB China)
            total_product_cost = product_cost * quantity

            # 2. Shipping cost
            shipping_cost = self._calculate_shipping(weight_kg, quantity, shipping_method)

            # 3. Tariff (duty)
            tariff_rate = self.TARIFF_RATES.get(category, self.TARIFF_RATES['default'])
            tariff_cost = total_product_cost * tariff_rate

            # 4. Customs broker fee (solo si se incluye)
            customs_broker_fee = 0
            if include_customs_broker and shipping_method.startswith('sea'):
                # Sea freight siempre requiere customs broker
                customs_broker_fee = 150  # Promedio $100-200
            elif include_customs_broker and quantity >= 50:
                # Air freight en cantidades grandes puede requerir broker
                customs_broker_fee = 100

            # 5. MPF (Merchandise Processing Fee) - 0.3464% del valor, min $27.75, max $538.40
            mpf = max(27.75, min(538.40, total_product_cost * 0.003464))

            # 6. HMF (Harbor Maintenance Fee) - 0.125% para sea freight
            hmf = 0
            if shipping_method.startswith('sea'):
                hmf = total_product_cost * 0.00125

            # TOTAL LANDED COST
            total_landed_cost = (
                total_product_cost +
                shipping_cost +
                tariff_cost +
                customs_broker_fee +
                mpf +
                hmf
            )

            # Costo por unidad
            cost_per_unit = total_landed_cost / quantity

            return {
                'product_cost': total_product_cost,
                'shipping_cost': shipping_cost,
                'tariff_cost': tariff_cost,
                'tariff_rate': tariff_rate * 100,  # En porcentaje
                'customs_broker_fee': customs_broker_fee,
                'mpf_fee': mpf,
                'hmf_fee': hmf,
                'total_landed_cost': total_landed_cost,
                'cost_per_unit': cost_per_unit,
                'quantity': quantity,
                'shipping_method': shipping_method,
                'category': category
            }

        except Exception as e:
            logging.error(f"Error calculating landed cost: {e}")
            return None

    def _calculate_shipping(self, weight_kg: float, quantity: int, method: str) -> float:
        """Calcula el costo de shipping basado en peso y método"""
        total_weight = weight_kg * quantity

        if method == 'air_express':
            return total_weight * self.AIR_SHIPPING_RATES['express']
        elif method == 'air_standard':
            return total_weight * self.AIR_SHIPPING_RATES['standard']
        elif method == 'air_economy':
            return total_weight * self.AIR_SHIPPING_RATES['economy']
        elif method == 'sea_fcl':
            return total_weight * self.SEA_SHIPPING_RATES['fcl']
        elif method == 'sea_lcl':
            return total_weight * self.SEA_SHIPPING_RATES['lcl']
        elif method == 'sea_express':
            return total_weight * self.SEA_SHIPPING_RATES['express']
        else:
            # Default: air standard
            return total_weight * self.AIR_SHIPPING_RATES['standard']

    def calculate_fba_roi(
        self,
        amazon_price: float,
        china_cost: float,
        weight_kg: float,
        dimensions: tuple,  # (length, width, height) en inches
        category: str = 'default',
        shipping_method: str = 'sea_lcl',
        quantity: int = 100
    ) -> dict:
        """
        Calcula ROI completo incluyendo importación + FBA fees

        Args:
            amazon_price: Precio de venta en Amazon
            china_cost: Costo del producto en China (por unidad)
            weight_kg: Peso en kilogramos
            dimensions: Tupla (L, W, H) en pulgadas
            category: Categoría del producto
            shipping_method: Método de envío desde China
            quantity: Cantidad a importar (afecta shipping cost per unit)

        Returns:
            dict con análisis completo de ROI
        """
        try:
            # 1. Calcular landed cost (importación)
            landed = self.calculate_landed_cost(
                product_cost=china_cost,
                weight_kg=weight_kg,
                category=category,
                shipping_method=shipping_method,
                quantity=quantity
            )

            if not landed:
                return None

            cost_per_unit = landed['cost_per_unit']

            # 2. Calcular FBA fees
            fba_fees = self._calculate_fba_fees(
                price=amazon_price,
                weight_lbs=weight_kg * 2.20462,  # kg a lbs
                dimensions=dimensions
            )

            # 3. Amazon referral fee (15% típico, varía por categoría)
            referral_fee = amazon_price * 0.15

            # 4. Calcular ganancia y ROI
            total_fees = fba_fees['fulfillment_fee'] + referral_fee
            net_profit = amazon_price - cost_per_unit - total_fees
            roi_percent = (net_profit / cost_per_unit) * 100 if cost_per_unit > 0 else 0

            return {
                'amazon_price': amazon_price,
                'china_cost': china_cost,
                'landed_cost_per_unit': cost_per_unit,
                'import_breakdown': landed,
                'fba_fulfillment_fee': fba_fees['fulfillment_fee'],
                'amazon_referral_fee': referral_fee,
                'total_fees': total_fees,
                'net_profit': net_profit,
                'roi_percent': roi_percent,
                'quantity': quantity,
                'break_even_quantity': self._calculate_break_even(china_cost, shipping_method, weight_kg),
                'recommendation': self._get_recommendation(roi_percent, net_profit)
            }

        except Exception as e:
            logging.error(f"Error calculating FBA ROI: {e}")
            return None

    def _calculate_fba_fees(self, price: float, weight_lbs: float, dimensions: tuple) -> dict:
        """
        Calcula FBA fulfillment fee basado en tamaño/peso
        Basado en FBA Fee Schedule 2024
        """
        length, width, height = dimensions

        # Calcular dimensional weight
        dim_weight = (length * width * height) / 139

        # Usar el mayor entre peso real y dimensional
        billable_weight = max(weight_lbs, dim_weight)

        # Determinar tier
        is_small = (max(length, width, height) <= 15 and
                   min(length, width, height) <= 12 and
                   billable_weight <= 1)

        is_large_standard = (max(length, width, height) <= 18 and
                            min(length, width, height) <= 14 and
                            billable_weight <= 20)

        # Calcular fee según tier
        if is_small:
            if price < 10:
                fee = 3.06  # Small standard-size, low price
            else:
                fee = 3.22  # Small standard-size
        elif is_large_standard:
            if billable_weight <= 1:
                fee = 3.86
            elif billable_weight <= 2:
                fee = 4.75
            else:
                fee = 4.75 + ((billable_weight - 2) * 0.38)
        else:
            # Large bulky or oversize
            if billable_weight <= 50:
                fee = 8.26 + (billable_weight * 0.38)
            else:
                fee = 8.26 + (50 * 0.38) + ((billable_weight - 50) * 0.75)

        return {
            'fulfillment_fee': fee,
            'billable_weight': billable_weight,
            'size_tier': 'Small' if is_small else ('Large Standard' if is_large_standard else 'Large Bulky')
        }

    def _calculate_break_even(self, china_cost: float, shipping_method: str, weight_kg: float) -> int:
        """
        Calcula cantidad mínima para break-even en shipping
        """
        if shipping_method.startswith('sea'):
            # Sea freight tiene economía de escala - recomendar min 100 unidades
            return 100
        else:
            # Air freight - puede ser rentable con menos unidades
            return 50

    def _get_recommendation(self, roi_percent: float, net_profit: float) -> str:
        """Devuelve recomendación basada en ROI y ganancia"""
        if roi_percent >= 50 and net_profit >= 15:
            return "🟢 EXCELENTE - Alta ganancia y ROI"
        elif roi_percent >= 30 and net_profit >= 10:
            return "🟡 BUENO - ROI aceptable"
        elif roi_percent >= 20 and net_profit >= 5:
            return "🟠 MARGINAL - Considerar solo con alto volumen"
        else:
            return "🔴 NO RECOMENDADO - ROI muy bajo"


def test_calculator():
    """Test de la calculadora con producto real"""
    print("=" * 70)
    print("TEST: Import Cost Calculator")
    print("=" * 70)

    calc = ImportCostCalculator()

    # Ejemplo: Wireless Mouse desde China
    print("\n📦 Producto: Wireless Mouse")
    print("   Costo China: $3.50 por unidad")
    print("   Peso: 0.15 kg")
    print("   Dimensiones: 5\" x 3\" x 2\"")
    print("   Cantidad: 200 unidades")
    print("   Precio Amazon: $15.99")

    result = calc.calculate_fba_roi(
        amazon_price=15.99,
        china_cost=3.50,
        weight_kg=0.15,
        dimensions=(5, 3, 2),
        category='electronics',
        shipping_method='sea_lcl',
        quantity=200
    )

    if result:
        print("\n" + "=" * 70)
        print("RESULTADOS:")
        print("=" * 70)
        print(f"\n💰 COSTOS:")
        print(f"   Producto (China): ${result['china_cost']:.2f}")
        print(f"   Landed Cost (USA): ${result['landed_cost_per_unit']:.2f}")
        print(f"   FBA Fee: ${result['fba_fulfillment_fee']:.2f}")
        print(f"   Amazon Referral: ${result['amazon_referral_fee']:.2f}")
        print(f"   Total Fees: ${result['total_fees']:.2f}")

        print(f"\n📊 GANANCIA:")
        print(f"   Precio Amazon: ${result['amazon_price']:.2f}")
        print(f"   Ganancia Neta: ${result['net_profit']:.2f}")
        print(f"   ROI: {result['roi_percent']:.1f}%")
        print(f"   Break-Even Qty: {result['break_even_quantity']} unidades")

        print(f"\n{result['recommendation']}")

        print("\n" + "=" * 70)
        print("DESGLOSE IMPORTACIÓN:")
        print("=" * 70)
        imp = result['import_breakdown']
        print(f"   Costo Producto: ${imp['product_cost']:.2f}")
        print(f"   Shipping ({imp['shipping_method']}): ${imp['shipping_cost']:.2f}")
        print(f"   Tariff ({imp['tariff_rate']:.1f}%): ${imp['tariff_cost']:.2f}")
        print(f"   Customs Broker: ${imp['customs_broker_fee']:.2f}")
        print(f"   MPF Fee: ${imp['mpf_fee']:.2f}")
        print(f"   HMF Fee: ${imp['hmf_fee']:.2f}")
        print(f"   TOTAL: ${imp['total_landed_cost']:.2f}")
        print(f"   Por Unidad: ${imp['cost_per_unit']:.2f}")


if __name__ == "__main__":
    test_calculator()
