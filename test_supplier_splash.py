"""
Test del SupplierScraper usando AmazonWebRobot + Splash
Verifica que los proveedores se scrateen correctamente
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.scrapers.supplier_scraper import SupplierScraper
import logging

logging.basicConfig(level=logging.INFO)

def test_supplier_scraper():
    """Test rápido del scraper de proveedores"""

    print("=" * 70)
    print("TEST: SupplierScraper con AmazonWebRobot + Splash")
    print("=" * 70)

    # Producto de prueba (algo común que existe en varios proveedores)
    product_name = "wireless mouse"

    print(f"\n🔍 Buscando: '{product_name}'\n")

    scraper = SupplierScraper(product_name)

    # Test 1: AliExpress (China wholesale)
    print("\n" + "=" * 70)
    print("TEST 1: AliExpress (China Wholesale)")
    print("=" * 70)
    try:
        results = scraper.search_aliexpress(max_results=3)
        if results:
            print(f"✅ AliExpress: {len(results)} productos encontrados")
            for idx, item in enumerate(results[:2], 1):
                print(f"   {idx}. {item['title'][:60]}")
                print(f"      Precio: ${item['price']} | Total: ${item['total']}")
        else:
            print("❌ AliExpress: Sin resultados")
    except Exception as e:
        print(f"⚠️  AliExpress Error: {e}")

    # Test 2: eBay (Marketplace)
    print("\n" + "=" * 70)
    print("TEST 2: eBay (Marketplace)")
    print("=" * 70)
    try:
        results = scraper.search_ebay(max_results=3)
        if results:
            print(f"✅ eBay: {len(results)} productos encontrados")
            for idx, item in enumerate(results[:2], 1):
                print(f"   {idx}. {item['title'][:60]}")
                print(f"      Precio: ${item['price']} | Total: ${item['total']}")
        else:
            print("❌ eBay: Sin resultados")
    except Exception as e:
        print(f"⚠️  eBay Error: {e}")

    # Test 3: Walmart (USA Retail)
    print("\n" + "=" * 70)
    print("TEST 3: Walmart (USA Retail)")
    print("=" * 70)
    try:
        results = scraper.search_walmart(max_results=3)
        if results:
            print(f"✅ Walmart: {len(results)} productos encontrados")
            for idx, item in enumerate(results[:2], 1):
                print(f"   {idx}. {item['title'][:60]}")
                print(f"      Precio: ${item['price']} | Total: ${item['total']}")
        else:
            print("❌ Walmart: Sin resultados")
    except Exception as e:
        print(f"⚠️  Walmart Error: {e}")

    # Test 4: DHgate (China wholesale)
    print("\n" + "=" * 70)
    print("TEST 4: DHgate (China Wholesale)")
    print("=" * 70)
    try:
        results = scraper.search_dhgate(max_results=3)
        if results:
            print(f"✅ DHgate: {len(results)} productos encontrados")
            for idx, item in enumerate(results[:2], 1):
                print(f"   {idx}. {item['title'][:60]}")
                print(f"      Precio: ${item['price']} | Total: ${item['total']}")
        else:
            print("❌ DHgate: Sin resultados")
    except Exception as e:
        print(f"⚠️  DHgate Error: {e}")

    print("\n" + "=" * 70)
    print("✅ TEST COMPLETADO")
    print("=" * 70)
    print("\nAhora todos los proveedores usan AmazonWebRobot + Splash!")
    print("Misma infraestructura que Amazon scraping = mejor consistencia")

if __name__ == "__main__":
    test_supplier_scraper()
