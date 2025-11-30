"""
FBA Rules Checker - Valida productos contra los mandamientos de FBA
Basado en FBA_MANDAMIENTOS.md
"""
import logging
import re

logging.basicConfig(level=logging.INFO)


class FBARulesChecker:
    """
    Verifica que un producto cumpla con las reglas de Amazon FBA
    """

    # MANDAMIENTO 1: Productos Prohibidos
    PROHIBITED_KEYWORDS = [
        'alcohol', 'beer', 'wine', 'vodka', 'whiskey',
        'gun', 'firearm', 'ammunition', 'bullet',
        'cbd', 'cannabis', 'marijuana', 'thc',
        'gift card', 'giftcard',
        'tire', 'tyre'
    ]

    # MANDAMIENTO 9: Categorías Restringidas
    RESTRICTED_CATEGORIES = [
        'automotive', 'powersports',
        'collectibles',
        'grocery', 'gourmet food',
        'health', 'personal care',
        'jewelry',
        'sexual wellness',
        'toys', 'games',
        'video', 'dvd', 'blu-ray'
    ]

    # MANDAMIENTO 2: Límites de tamaño/peso
    SIZE_LIMITS = {
        'standard': {
            'max_weight_lbs': 20,
            'max_length': 18,
            'max_width': 14,
            'max_height': 8
        },
        'large_bulky': {
            'max_weight_lbs': 50
        },
        'extra_large': {
            'max_weight_lbs': 150  # Requiere aprobación especial
        }
    }

    # MANDAMIENTO 3: Estructura de fees 2024
    FBA_FEES_2024 = {
        'fulfillment_base': {
            'small_standard': 3.22,
            'large_standard_1lb': 3.86,
            'large_standard_2lb': 4.75,
            'large_standard_3lb': 5.13
        },
        'storage_per_cubic_ft': {
            'jan_sep': 0.87,
            'oct_dec': 2.40
        },
        'inbound_placement': {
            'min': 0.21,
            'max': 6.00
        },
        'returns_processing': {
            'min': 1.78,
            'max': 157.00
        }
    }

    def __init__(self):
        pass

    def check_product(
        self,
        product_name: str,
        category: str,
        price: float,
        weight_lbs: float = 0,
        dimensions: dict = None,
        bsr: int = 0,
        review_count: int = 0
    ) -> dict:
        """
        Verifica un producto contra TODOS los mandamientos de FBA

        Args:
            product_name: Nombre del producto
            category: Categoría del producto
            price: Precio de venta en Amazon
            weight_lbs: Peso en libras
            dimensions: dict con 'length', 'width', 'height' en pulgadas
            bsr: Best Sellers Rank
            review_count: Número de reviews

        Returns:
            dict con:
                - is_compliant: bool
                - violations: list de violaciones
                - warnings: list de advertencias
                - recommendations: list de recomendaciones
        """
        violations = []
        warnings = []
        recommendations = []

        # MANDAMIENTO 1: Productos Prohibidos
        if self._is_prohibited(product_name):
            violations.append({
                'mandamiento': 1,
                'severity': 'CRITICAL',
                'message': '🚫 Producto PROHIBIDO detectado',
                'detail': 'Amazon puede destruir tu inventario SIN REEMBOLSO'
            })

        # MANDAMIENTO 2: Límites de tamaño/peso
        size_check = self._check_size_limits(weight_lbs, dimensions)
        if not size_check['compliant']:
            violations.append({
                'mandamiento': 2,
                'severity': 'HIGH',
                'message': '⚠️ Excede límites de tamaño/peso',
                'detail': size_check['message']
            })

        # MANDAMIENTO 3: Precio mínimo recomendado
        if price < 15:
            warnings.append({
                'mandamiento': 3,
                'severity': 'MEDIUM',
                'message': '💰 Precio bajo ($' + f'{price:.2f}' + ')',
                'detail': 'Recomendado: > $15 para cubrir fees adecuadamente'
            })

        # MANDAMIENTO 6: Investigación previa
        research_check = self._check_research_requirements(price, bsr, review_count)
        if not research_check['passed']:
            warnings.extend(research_check['warnings'])

        # MANDAMIENTO 9: Categorías Restringidas
        if self._is_restricted_category(category):
            warnings.append({
                'mandamiento': 9,
                'severity': 'MEDIUM',
                'message': '🔒 Categoría RESTRINGIDA',
                'detail': f'{category} requiere aprobación (ungating) de Amazon'
            })

        # Recomendaciones basadas en MANDAMIENTO 10 (Inventory Management)
        recommendations.append({
            'type': 'inventory',
            'message': '📦 Asegúrate de vender en < 90 días',
            'detail': 'Evita aged inventory surcharge ($0.50-$6.90/cubic ft)'
        })

        # Estrategia Ganadora (de FBA_MANDAMIENTOS.md)
        if self._is_ideal_product(price, weight_lbs, bsr):
            recommendations.append({
                'type': 'ideal',
                'message': '🎯 Producto IDEAL para FBA',
                'detail': 'Cumple con criterios: pequeño, ligero, precio óptimo, alta demanda'
            })

        is_compliant = len(violations) == 0

        return {
            'is_compliant': is_compliant,
            'violations': violations,
            'warnings': warnings,
            'recommendations': recommendations,
            'summary': self._generate_summary(is_compliant, violations, warnings)
        }

    def _is_prohibited(self, product_name: str) -> bool:
        """Verifica si el producto contiene keywords prohibidos"""
        name_lower = product_name.lower()
        for keyword in self.PROHIBITED_KEYWORDS:
            if keyword in name_lower:
                return True
        return False

    def _check_size_limits(self, weight_lbs: float, dimensions: dict) -> dict:
        """Verifica límites de tamaño y peso (MANDAMIENTO 2)"""
        if not dimensions or weight_lbs == 0:
            return {'compliant': True, 'message': 'No hay datos de dimensiones'}

        length = dimensions.get('length', 0)
        width = dimensions.get('width', 0)
        height = dimensions.get('height', 0)

        # Standard-size check
        if (weight_lbs <= 20 and
            length <= 18 and
            width <= 14 and
            height <= 8):
            return {'compliant': True, 'tier': 'standard', 'message': 'Cumple con standard-size'}

        # Large Bulky check
        if weight_lbs <= 50:
            return {'compliant': True, 'tier': 'large_bulky', 'message': 'Categoría: Large Bulky (fees más altos)'}

        # Extra-Large (requiere aprobación)
        if weight_lbs <= 150:
            return {
                'compliant': False,
                'tier': 'extra_large',
                'message': 'Extra-Large: Requiere aprobación especial de Amazon'
            }

        # Excede todos los límites
        return {
            'compliant': False,
            'tier': 'oversized',
            'message': f'Excede límite de 150 lbs (peso: {weight_lbs} lbs)'
        }

    def _check_research_requirements(self, price: float, bsr: int, review_count: int) -> dict:
        """Verifica checklist de investigación (MANDAMIENTO 6)"""
        warnings = []

        # BSR < 100,000
        if bsr > 100000:
            warnings.append({
                'mandamiento': 6,
                'severity': 'MEDIUM',
                'message': f'📊 BSR alto: #{bsr:,}',
                'detail': 'Recomendado: BSR < 100,000 para demanda validada'
            })

        # Reviews > 100
        if review_count < 100:
            warnings.append({
                'mandamiento': 6,
                'severity': 'LOW',
                'message': f'⭐ Pocas reviews: {review_count}',
                'detail': 'Recomendado: > 100 reviews (competencia validada)'
            })

        # Precio > $15
        if price < 15:
            warnings.append({
                'mandamiento': 6,
                'severity': 'MEDIUM',
                'message': f'💵 Precio bajo: ${price:.2f}',
                'detail': 'Recomendado: > $15 para cubrir fees'
            })

        return {
            'passed': len(warnings) == 0,
            'warnings': warnings
        }

    def _is_restricted_category(self, category: str) -> bool:
        """Verifica si la categoría está restringida (MANDAMIENTO 9)"""
        category_lower = category.lower()
        for restricted in self.RESTRICTED_CATEGORIES:
            if restricted in category_lower:
                return True
        return False

    def _is_ideal_product(self, price: float, weight_lbs: float, bsr: int) -> bool:
        """
        Verifica si cumple con "Productos IDEALES para FBA"
        Basado en Estrategia Ganadora de FBA_MANDAMIENTOS.md
        """
        # Pequeño y ligero: < 1 lb
        if weight_lbs >= 1:
            return False

        # Precio sweet spot: $20 - $50
        if not (20 <= price <= 50):
            return False

        # Alta demanda: BSR < 50,000
        if bsr > 50000:
            return False

        return True

    def _generate_summary(self, is_compliant: bool, violations: list, warnings: list) -> str:
        """Genera resumen del check"""
        if is_compliant:
            if len(warnings) == 0:
                return "✅ Producto APTO para FBA - Sin violaciones ni advertencias"
            else:
                return f"⚠️ Producto aceptable para FBA - {len(warnings)} advertencias"
        else:
            return f"🚫 Producto NO APTO para FBA - {len(violations)} violaciones críticas"

    def calculate_all_fees(
        self,
        price: float,
        weight_lbs: float,
        dimensions: dict,
        month: int = 1,  # 1-12, para storage fee
        storage_days: int = 30,
        is_holiday_peak: bool = False
    ) -> dict:
        """
        Calcula TODOS los fees de FBA 2024 (MANDAMIENTO 3)

        Args:
            price: Precio de venta
            weight_lbs: Peso en libras
            dimensions: dict con length, width, height
            month: Mes (1-12) para storage fee
            storage_days: Días en storage
            is_holiday_peak: Si está en Holiday Peak (Oct 15 - Ene 14)

        Returns:
            dict con breakdown de todos los fees
        """
        # 1. Fulfillment Fee
        fulfillment_fee = self._calculate_fulfillment_fee(price, weight_lbs, dimensions)

        # 2. Referral Fee (15% típico)
        referral_fee = price * 0.15

        # 3. Storage Fee
        cubic_ft = self._calculate_cubic_ft(dimensions)
        storage_rate = self.FBA_FEES_2024['storage_per_cubic_ft']['oct_dec'] if month >= 10 else self.FBA_FEES_2024['storage_per_cubic_ft']['jan_sep']
        storage_fee = cubic_ft * storage_rate * (storage_days / 30)

        # 4. Inbound Placement Fee (promedio $2.00)
        inbound_placement = 2.00

        # 5. Low-Inventory Fee (si < 28 días de inventory)
        low_inventory_fee = 0
        if storage_days < 28:
            low_inventory_fee = fulfillment_fee * 0.5  # Estimación: 50% del fulfillment fee

        # 6. Returns Processing Fee (promedio basado en precio)
        returns_processing = price * 0.20 if price < 10 else (1.78 + (price * 0.05))

        # 7. Holiday Peak Fee (Oct 15 - Ene 14)
        holiday_peak_fee = 0
        if is_holiday_peak:
            holiday_peak_fee = fulfillment_fee * 0.35  # 35% adicional

        # TOTAL
        total_fees = (
            fulfillment_fee +
            referral_fee +
            storage_fee +
            inbound_placement +
            low_inventory_fee +
            returns_processing +
            holiday_peak_fee
        )

        return {
            'fulfillment_fee': fulfillment_fee,
            'referral_fee': referral_fee,
            'storage_fee': storage_fee,
            'inbound_placement': inbound_placement,
            'low_inventory_fee': low_inventory_fee,
            'returns_processing': returns_processing,
            'holiday_peak_fee': holiday_peak_fee,
            'total_fees': total_fees,
            'net_after_fees': price - total_fees
        }

    def _calculate_fulfillment_fee(self, price: float, weight_lbs: float, dimensions: dict) -> float:
        """Calcula fulfillment fee según tier"""
        if not dimensions:
            return 3.22  # Default: small standard

        length = dimensions.get('length', 0)
        width = dimensions.get('width', 0)
        height = dimensions.get('height', 0)

        # Small standard
        if weight_lbs <= 1 and max(length, width, height) <= 15:
            if price < 10:
                return 3.06  # Low-price FBA discount
            return 3.22

        # Large standard
        if weight_lbs <= 1:
            return 3.86
        elif weight_lbs <= 2:
            return 4.75
        else:
            return 4.75 + ((weight_lbs - 2) * 0.38)

    def _calculate_cubic_ft(self, dimensions: dict) -> float:
        """Calcula cubic feet para storage fee"""
        if not dimensions:
            return 0.5  # Default: 0.5 cubic ft

        length = dimensions.get('length', 0)
        width = dimensions.get('width', 0)
        height = dimensions.get('height', 0)

        # Convertir a cubic feet (dimensiones en pulgadas)
        cubic_inches = length * width * height
        return cubic_inches / 1728  # 1728 cubic inches = 1 cubic ft


def test_checker():
    """Test del FBA Rules Checker"""
    print("=" * 70)
    print("TEST: FBA Rules Checker")
    print("=" * 70)

    checker = FBARulesChecker()

    # Test 1: Producto IDEAL
    print("\n" + "=" * 70)
    print("TEST 1: Producto IDEAL (Wireless Mouse)")
    print("=" * 70)
    result = checker.check_product(
        product_name="Logitech Wireless Mouse",
        category="electronics",
        price=24.99,
        weight_lbs=0.3,
        dimensions={'length': 5, 'width': 3, 'height': 2},
        bsr=15000,
        review_count=5000
    )
    print(f"\n{result['summary']}")
    if result['recommendations']:
        for rec in result['recommendations']:
            print(f"   {rec['message']}")

    # Test 2: Producto PROHIBIDO
    print("\n" + "=" * 70)
    print("TEST 2: Producto PROHIBIDO (CBD Oil)")
    print("=" * 70)
    result = checker.check_product(
        product_name="CBD Oil 1000mg",
        category="health",
        price=39.99,
        weight_lbs=0.5,
        dimensions={'length': 6, 'width': 2, 'height': 2},
        bsr=50000,
        review_count=200
    )
    print(f"\n{result['summary']}")
    if result['violations']:
        for viol in result['violations']:
            print(f"   {viol['message']} - {viol['detail']}")

    # Test 3: Producto PESADO
    print("\n" + "=" * 70)
    print("TEST 3: Producto PESADO (25 lbs)")
    print("=" * 70)
    result = checker.check_product(
        product_name="Heavy Dumbbell Set",
        category="sports",
        price=89.99,
        weight_lbs=25,
        dimensions={'length': 20, 'width': 10, 'height': 8},
        bsr=80000,
        review_count=150
    )
    print(f"\n{result['summary']}")
    if result['violations']:
        for viol in result['violations']:
            print(f"   {viol['message']}")
    if result['warnings']:
        for warn in result['warnings']:
            print(f"   {warn['message']}")

    # Test 4: Cálculo de FEES completos
    print("\n" + "=" * 70)
    print("TEST 4: Cálculo de TODOS los fees FBA 2024")
    print("=" * 70)
    fees = checker.calculate_all_fees(
        price=24.99,
        weight_lbs=0.3,
        dimensions={'length': 5, 'width': 3, 'height': 2},
        month=11,  # Noviembre (Holiday Peak)
        storage_days=45,
        is_holiday_peak=True
    )
    print(f"\n💰 Breakdown de Fees:")
    print(f"   Fulfillment Fee: ${fees['fulfillment_fee']:.2f}")
    print(f"   Referral Fee (15%): ${fees['referral_fee']:.2f}")
    print(f"   Storage Fee: ${fees['storage_fee']:.2f}")
    print(f"   Inbound Placement: ${fees['inbound_placement']:.2f}")
    print(f"   Low-Inventory Fee: ${fees['low_inventory_fee']:.2f}")
    print(f"   Returns Processing: ${fees['returns_processing']:.2f}")
    print(f"   Holiday Peak Fee: ${fees['holiday_peak_fee']:.2f}")
    print(f"   ─────────────────────────")
    print(f"   TOTAL FEES: ${fees['total_fees']:.2f}")
    print(f"   NET (después de fees): ${fees['net_after_fees']:.2f}")


if __name__ == "__main__":
    test_checker()
