"""
Test completo de FBA Rules Checker - Con datos simulados
Demuestra la validación completa de FBA con diferentes escenarios
"""
from src.utils.fba_rules_checker import FBARulesChecker
import json

def test_fba_scenarios():
    """Prueba diferentes escenarios de productos"""

    print("=" * 80)
    print("TEST COMPLETO: FBA Rules Checker - Diferentes Escenarios")
    print("=" * 80)

    checker = FBARulesChecker()

    # Escenario 1: Producto IDEAL para FBA (Amazon Echo Dot con dimensiones reales)
    print("\n" + "=" * 80)
    print("ESCENARIO 1: Producto IDEAL (Amazon Echo Dot)")
    print("=" * 80)

    result1 = checker.check_product(
        product_name="Amazon Echo Dot (5th Gen) - Smart speaker with Alexa",
        category="electronics",
        price=31.99,
        weight_lbs=0.67,  # Peso real aproximado
        dimensions={'length': 3.9, 'width': 3.9, 'height': 3.5},  # Dimensiones reales
        bsr=150,  # Muy bajo BSR
        review_count=177531
    )

    print(f"\n📊 RESUMEN: {result1['summary']}")
    print(f"✅ Cumplimiento FBA: {'SÍ' if result1['is_compliant'] else 'NO'}")

    # Obtener size tier
    size_check = checker._check_size_limits(0.67, {'length': 3.9, 'width': 3.9, 'height': 3.5})
    print(f"📦 Size Tier: {size_check.get('tier', 'Unknown').upper()}")

    print(f"\n💰 DIMENSIONES & PESO:")
    print(f"   Largo: 3.9 pulgadas")
    print(f"   Ancho: 3.9 pulgadas")
    print(f"   Alto: 3.5 pulgadas")
    print(f"   Peso: 0.67 lbs")

    if result1['violations']:
        print(f"\n🚫 VIOLACIONES ({len(result1['violations'])}):")
        for v in result1['violations']:
            print(f"   [{v['severity']}] {v['message']}")
            print(f"      → {v['detail']}")

    if result1['warnings']:
        print(f"\n⚠️  ADVERTENCIAS ({len(result1['warnings'])}):")
        for w in result1['warnings']:
            print(f"   [{w['severity']}] {w['message']}")
            print(f"      → {w['detail']}")

    if result1['recommendations']:
        print(f"\n✨ RECOMENDACIONES:")
        for r in result1['recommendations']:
            print(f"   {r['message']}")
            print(f"      → {r['detail']}")

    # Escenario 2: Producto PROHIBIDO
    print("\n\n" + "=" * 80)
    print("ESCENARIO 2: Producto PROHIBIDO (CBD Oil)")
    print("=" * 80)

    result2 = checker.check_product(
        product_name="CBD Oil 1000mg Full Spectrum",
        category="health",
        price=39.99,
        weight_lbs=0.5,
        dimensions={'length': 6, 'width': 2, 'height': 2},
        bsr=50000,
        review_count=200
    )

    print(f"\n📊 RESUMEN: {result2['summary']}")
    print(f"✅ Cumplimiento FBA: {'SÍ' if result2['is_compliant'] else 'NO'}")

    size_check2 = checker._check_size_limits(0.5, {'length': 6, 'width': 2, 'height': 2})
    print(f"📦 Size Tier: {size_check2.get('tier', 'Unknown').upper()}")

    if result2['violations']:
        print(f"\n🚫 VIOLACIONES ({len(result2['violations'])}):")
        for v in result2['violations']:
            print(f"   [{v['severity']}] {v['message']}")
            print(f"      → {v['detail']}")

    if result2['warnings']:
        print(f"\n⚠️  ADVERTENCIAS ({len(result2['warnings'])}):")
        for w in result2['warnings']:
            print(f"   [{w['severity']}] {w['message']}")

    # Escenario 3: Producto PESADO (excede límites)
    print("\n\n" + "=" * 80)
    print("ESCENARIO 3: Producto PESADO - Excede límites standard")
    print("=" * 80)

    result3 = checker.check_product(
        product_name="Heavy Dumbbell Set 25 lbs",
        category="sports",
        price=89.99,
        weight_lbs=25,  # Excede 20 lbs
        dimensions={'length': 20, 'width': 10, 'height': 8},
        bsr=80000,
        review_count=150
    )

    print(f"\n📊 RESUMEN: {result3['summary']}")
    print(f"✅ Cumplimiento FBA: {'SÍ' if result3['is_compliant'] else 'NO'}")

    size_check3 = checker._check_size_limits(25, {'length': 20, 'width': 10, 'height': 8})
    print(f"📦 Size Tier: {size_check3.get('tier', 'Unknown').upper()}")

    print(f"\n💰 DIMENSIONES & PESO:")
    print(f"   Largo: 20 pulgadas")
    print(f"   Ancho: 10 pulgadas")
    print(f"   Alto: 8 pulgadas")
    print(f"   Peso: 25 lbs (excede standard-size de 20 lbs)")

    if result3['violations']:
        print(f"\n🚫 VIOLACIONES ({len(result3['violations'])}):")
        for v in result3['violations']:
            print(f"   [{v['severity']}] {v['message']}")
            print(f"      → {v['detail']}")

    if result3['warnings']:
        print(f"\n⚠️  ADVERTENCIAS ({len(result3['warnings'])}):")
        for w in result3['warnings']:
            print(f"   [{w['severity']}] {w['message']}")

    # Escenario 4: Cálculo de FEES completos
    print("\n\n" + "=" * 80)
    print("ESCENARIO 4: Cálculo de FEES FBA 2024 (Echo Dot)")
    print("=" * 80)

    fees = checker.calculate_all_fees(
        price=31.99,
        weight_lbs=0.67,
        dimensions={'length': 3.9, 'width': 3.9, 'height': 3.5},
        month=11,  # Noviembre (Holiday Peak)
        storage_days=45,
        is_holiday_peak=True
    )

    print(f"\n💰 BREAKDOWN DE FEES:")
    print(f"   Precio de Venta: ${31.99}")
    print(f"   ─────────────────────────")
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
    print(f"   ─────────────────────────")
    print(f"   % de Fees sobre Precio: {(fees['total_fees'] / 31.99 * 100):.1f}%")

    # JSON Output simulado (como se guarda en base de datos)
    print("\n\n" + "=" * 80)
    print("EJEMPLO DE OUTPUT JSON (guardado en base de datos)")
    print("=" * 80)

    fba_data = {
        'asin': 'B09B8V1LZ3',
        'product_name': 'Amazon Echo Dot (5th Gen)',
        'fba_compliant': result1['is_compliant'],
        'fba_warnings': json.dumps(result1.get('violations', []) + result1.get('warnings', [])),
        'fba_size_tier': size_check.get('tier', 'Unknown'),
        'product_length': 3.9,
        'product_width': 3.9,
        'product_height': 3.5,
        'product_weight': 0.67,
        'product_rating': 4.7,
        'review_count': 177531
    }

    print(json.dumps(fba_data, indent=2, ensure_ascii=False))

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETO FINALIZADO")
    print("=" * 80)

if __name__ == "__main__":
    test_fba_scenarios()
