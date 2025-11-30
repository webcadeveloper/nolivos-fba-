"""
Test del Scanner Paralelo - Verifica que todo funcione
"""
import sys
sys.path.insert(0, '/mnt/c/Users/Admin/OneDrive - Nolivos Law/Aplicaciones/AMAZON/amz-review-analyzer')

from src.analyzers.parallel_product_scanner import ParallelProductScanner
from src.analyzers.product_discovery import OpportunityDatabase

print("=" * 70)
print("🧪 TEST DEL SCANNER PARALELO")
print("=" * 70)

# 1. Verificar que la DB existe
print("\n1️⃣  Verificando base de datos...")
db = OpportunityDatabase()
try:
    opportunities = db.get_opportunities(min_roi=0, min_profit=0, limit=10)
    print(f"   ✅ DB funciona - {len(opportunities)} oportunidades existentes")
    for opp in opportunities:
        print(f"      - {opp['asin']}: ${opp['net_profit']:.2f} ganancia, {opp['roi_percent']:.1f}% ROI")
except Exception as e:
    print(f"   ❌ Error en DB: {e}")

# 2. Test del scanner
print("\n2️⃣  Probando scanner paralelo...")
try:
    scanner = ParallelProductScanner(max_workers=5)  # Pocos workers para test
    print("   ✅ Scanner creado correctamente")

    # Intentar escanear solo 2 productos por categoría
    print("\n3️⃣  Escaneando 2 productos por categoría (esto tomará ~30-60 segundos)...")
    results = scanner.scan_best_sellers_parallel(max_products_per_category=2)

    print("\n" + "=" * 70)
    print("📊 RESULTADOS DEL ESCANEO")
    print("=" * 70)
    print(f"Productos escaneados: {results['total_scanned']}")
    print(f"Oportunidades encontradas: {results['total_opportunities']}")
    print(f"Errores: {results.get('errors', 0)}")
    print(f"Tiempo: {results['elapsed_seconds']:.1f}s")
    print(f"Velocidad: {results['products_per_second']:.2f} productos/seg")

    # Verificar que se guardaron en DB
    print("\n4️⃣  Verificando que se guardaron en DB...")
    new_opportunities = db.get_opportunities(min_roi=0, min_profit=0, limit=20)
    print(f"   Total en DB ahora: {len(new_opportunities)}")

    if len(new_opportunities) > len(opportunities):
        print(f"   ✅ Se guardaron {len(new_opportunities) - len(opportunities)} nuevas oportunidades!")
    else:
        print("   ⚠️  No se guardaron nuevas oportunidades (quizás ninguna tenía ROI > 5%)")

    # Mostrar últimos 5 logs
    print("\n5️⃣  Últimos logs del escaneo:")
    for log in scanner.get_recent_logs(10):
        print(f"   [{log['timestamp']}] {log['message']}")

except Exception as e:
    print(f"   ❌ Error en scanner: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ Test completado")
print("=" * 70)
