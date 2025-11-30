"""
Test FBA Rules Checker Integration
Prueba el análisis de producto con validación FBA integrada
"""
import sys
import logging
from datetime import datetime
from src.analyzers.product_discovery import ProductDiscoveryScanner

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

def test_fba_integration():
    """Prueba la integración de FBARulesChecker con ProductDiscoveryScanner"""

    print("=" * 80)
    print("TEST: Integración FBARulesChecker en Product Discovery")
    print("=" * 80)

    # ASIN de prueba solicitado
    test_asin = "B09B8V1LZ3"
    test_category = "electronics"
    scan_date = datetime.now().date().isoformat()

    print(f"\n📦 Analizando ASIN: {test_asin}")
    print(f"📂 Categoría: {test_category}")
    print(f"📅 Fecha: {scan_date}")
    print("-" * 80)

    scanner = ProductDiscoveryScanner()

    # Analizar el producto
    try:
        opportunity = scanner._analyze_product(test_asin, test_category, scan_date)

        if not opportunity:
            print("\n❌ No se pudo analizar el producto o no es rentable")
            return

        # Mostrar resultados
        print("\n" + "=" * 80)
        print("RESULTADOS DEL ANÁLISIS")
        print("=" * 80)

        print(f"\n📦 PRODUCTO:")
        print(f"   Nombre: {opportunity['product_name'][:80]}...")
        print(f"   ASIN: {opportunity['asin']}")
        print(f"   Categoría: {opportunity['category']}")

        print(f"\n💰 PRECIOS:")
        print(f"   Amazon: ${opportunity['amazon_price']:.2f}")
        print(f"   Proveedor ({opportunity['supplier_name']}): ${opportunity['supplier_price']:.2f}")
        print(f"   Costo Total: ${opportunity['total_cost']:.2f}")

        print(f"\n📊 RENTABILIDAD:")
        print(f"   Ganancia Neta: ${opportunity['net_profit']:.2f}")
        print(f"   ROI: {opportunity['roi_percent']:.1f}%")
        print(f"   Margen: {opportunity['margin_percent']:.1f}%")
        print(f"   Competitividad: {opportunity['competitiveness_level']} ({opportunity['competitiveness_score']}/100)")

        print(f"\n📏 DIMENSIONES & PESO:")
        print(f"   Largo: {opportunity['product_length']:.2f} pulgadas")
        print(f"   Ancho: {opportunity['product_width']:.2f} pulgadas")
        print(f"   Alto: {opportunity['product_height']:.2f} pulgadas")
        print(f"   Peso: {opportunity['product_weight']:.2f} lbs")

        print(f"\n🎯 FBA COMPLIANCE:")
        print(f"   Cumplimiento: {'✅ SÍ' if opportunity['fba_compliant'] else '❌ NO'}")
        print(f"   Size Tier: {opportunity['fba_size_tier']}")

        # Parsear y mostrar warnings/violaciones
        import json
        fba_issues = json.loads(opportunity['fba_warnings'])

        if fba_issues:
            print(f"\n⚠️  ADVERTENCIAS/VIOLACIONES FBA ({len(fba_issues)}):")
            for issue in fba_issues:
                severity = issue.get('severity', 'UNKNOWN')
                message = issue.get('message', 'Sin mensaje')
                detail = issue.get('detail', '')

                emoji = '🚫' if severity == 'CRITICAL' else '⚠️' if severity in ['HIGH', 'MEDIUM'] else 'ℹ️'
                print(f"   {emoji} [{severity}] {message}")
                if detail:
                    print(f"      → {detail}")
        else:
            print(f"\n✅ Sin advertencias o violaciones FBA")

        print(f"\n⭐ REVIEWS:")
        print(f"   Rating: {opportunity['product_rating']:.1f}/5.0")
        print(f"   Total Reviews: {opportunity['review_count']:,}")

        print(f"\n📈 VENTAS:")
        print(f"   BSR: #{opportunity['bsr']:,}")
        print(f"   Ventas Estimadas/Mes: {opportunity['estimated_monthly_sales']:,} unidades")

        # Guardar en base de datos
        print("\n" + "-" * 80)
        print("💾 Guardando en base de datos...")
        scanner.db.save_opportunity(opportunity)
        print("✅ Oportunidad guardada exitosamente")

        # Verificar que se guardó
        print("\n" + "-" * 80)
        print("🔍 Verificando datos en base de datos...")

        import sqlite3
        conn = sqlite3.connect('opportunities.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT asin, product_name, fba_compliant, fba_size_tier,
                   product_length, product_width, product_height, product_weight,
                   product_rating, review_count
            FROM opportunities
            WHERE asin = ?
        ''', (test_asin,))

        row = cursor.fetchone()
        if row:
            print("✅ Producto encontrado en base de datos:")
            print(f"   ASIN: {row['asin']}")
            print(f"   FBA Compliant: {row['fba_compliant']}")
            print(f"   Size Tier: {row['fba_size_tier']}")
            print(f"   Dimensiones: {row['product_length']}x{row['product_width']}x{row['product_height']} in")
            print(f"   Peso: {row['product_weight']} lbs")
            print(f"   Rating: {row['product_rating']}")
            print(f"   Reviews: {row['review_count']}")
        else:
            print("❌ Producto no encontrado en base de datos")

        conn.close()

        print("\n" + "=" * 80)
        print("✅ TEST COMPLETADO EXITOSAMENTE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return

if __name__ == "__main__":
    test_fba_integration()
