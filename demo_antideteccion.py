#!/usr/bin/env python3
"""
🥷 Demo del Sistema Anti-Detección de NOLIVOS FBA
================================================

Este script demuestra:
1. Scraping individual con anti-detección
2. Scraping paralelo de múltiples productos
3. Comparación de velocidad: secuencial vs paralelo

Uso:
    python demo_antideteccion.py
"""

import time
from datetime import datetime
from amzscraper import AmazonWebRobot
from src.utils.parallel_scraper import ParallelScraper, scrape_products_parallel


def demo_1_scraping_individual():
    """Demo 1: Scraping individual con anti-detección"""
    print("\n" + "=" * 60)
    print("🥷 DEMO 1: Scraping Individual con Anti-Detección")
    print("=" * 60)

    # ASIN de ejemplo
    asin = "B08N5WRWNW"
    url = f"https://www.amazon.com/dp/{asin}"

    print(f"\n📦 Producto: {asin}")
    print(f"🌐 URL: {url}")

    # Crear robot con stealth enabled
    print("\n🔧 Inicializando robot con stealth mode...")
    robot = AmazonWebRobot(enable_stealth=True, session_id=asin)

    # Scrape producto
    print("🕵️  Scrapeando producto (con anti-detección)...")
    start_time = time.time()

    try:
        soup = robot.get_soup(url)

        # Extraer información básica
        title_elem = soup.find("span", {"id": "productTitle"})
        title = title_elem.text.strip() if title_elem else "No encontrado"

        price_elem = soup.find("span", {"class": "a-price-whole"})
        price = price_elem.text.strip() if price_elem else "No disponible"

        rating_elem = soup.find("span", {"class": "a-icon-alt"})
        rating = rating_elem.text.strip() if rating_elem else "No rating"

        duration = time.time() - start_time

        # Resultados
        print("\n✅ SCRAPING EXITOSO")
        print("-" * 60)
        print(f"📝 Título: {title[:80]}...")
        print(f"💰 Precio: ${price}")
        print(f"⭐ Rating: {rating}")
        print(f"⏱️  Duración: {duration:.2f}s")
        print("-" * 60)

        print("\n🔍 Características Anti-Detección Usadas:")
        print("  ✅ User-Agent aleatorio (rotado)")
        print("  ✅ Browser fingerprint realista")
        print("  ✅ Headers HTTP completos")
        print("  ✅ Delays aleatorios (comportamiento humano)")
        print("  ✅ Cookies persistentes")
        print("  ✅ JavaScript evasion (Lua script)")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")


def demo_2_scraping_paralelo():
    """Demo 2: Scraping paralelo de múltiples productos"""
    print("\n" + "=" * 60)
    print("⚡ DEMO 2: Scraping Paralelo (Múltiples Productos)")
    print("=" * 60)

    # ASINs de ejemplo (productos reales de Amazon)
    asins = [
        "B08N5WRWNW",  # PlayStation 5
        "B08L5VFJ2G",  # Xbox Series S
        "B09G9BL5N7",  # Nintendo Switch OLED
        "B0CYDVZ1F8",  # AirPods Pro
        "B0BY912KPY",  # Fire TV Stick
    ]

    print(f"\n📦 Productos a scrapear: {len(asins)}")
    for i, asin in enumerate(asins, 1):
        print(f"   {i}. {asin}")

    # Función de scraping
    def scrape_product(url):
        """Scrape un producto y extrae info básica"""
        import re
        asin = re.search(r'/dp/([A-Z0-9]{10})', url).group(1)

        robot = AmazonWebRobot(session_id=asin)
        soup = robot.get_soup(url)

        # Extraer datos
        title_elem = soup.find("span", {"id": "productTitle"})
        price_elem = soup.find("span", {"class": "a-price-whole"})

        return {
            'asin': asin,
            'title': title_elem.text.strip()[:50] if title_elem else "N/A",
            'price': price_elem.text.strip() if price_elem else "N/A",
            'url': url
        }

    # Scraper paralelo
    print("\n🔧 Configurando scraper paralelo...")
    scraper = ParallelScraper(
        max_workers=5,        # 5 threads paralelos
        max_retries=2,        # 2 reintentos
        rate_limit=20         # 20 requests/min
    )

    # Scrape en paralelo
    urls = [f"https://www.amazon.com/dp/{asin}" for asin in asins]

    print("🕵️  Iniciando scraping paralelo...")
    start_time = time.time()

    results = scraper.scrape_urls(
        urls=urls,
        scrape_func=scrape_product
    )

    duration = time.time() - start_time

    # Procesar resultados
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print("\n" + "=" * 60)
    print("📊 RESULTADOS DEL SCRAPING PARALELO")
    print("=" * 60)

    for result in successful:
        data = result.data
        print(f"\n✅ {data['asin']}")
        print(f"   Título: {data['title']}")
        print(f"   Precio: ${data['price']}")
        print(f"   Duración: {result.duration:.2f}s")

    if failed:
        print("\n❌ FALLOS:")
        for result in failed:
            print(f"   - {result.url}: {result.error}")

    print("\n" + "=" * 60)
    print("📈 ESTADÍSTICAS")
    print("=" * 60)
    print(f"Total URLs: {len(urls)}")
    print(f"✅ Exitosos: {len(successful)}")
    print(f"❌ Fallidos: {len(failed)}")
    print(f"⏱️  Tiempo total: {duration:.2f}s")
    print(f"📊 Promedio por URL: {duration / len(urls):.2f}s")
    print(f"🚀 Throughput: {len(urls) / duration:.2f} URLs/segundo")
    print("=" * 60)


def demo_3_comparacion_velocidad():
    """Demo 3: Comparación secuencial vs paralelo"""
    print("\n" + "=" * 60)
    print("🏎️  DEMO 3: Comparación de Velocidad")
    print("=" * 60)

    asins = [
        "B08N5WRWNW",
        "B08L5VFJ2G",
        "B09G9BL5N7",
    ]

    print(f"\n📦 Scrapeando {len(asins)} productos")

    # Función simple de scraping
    def scrape_simple(url):
        """Scraping simple para comparación"""
        robot = AmazonWebRobot(enable_stealth=False)  # Sin stealth para velocidad
        try:
            soup = robot.get_soup(url)
            title = soup.find("span", {"id": "productTitle"})
            return {'title': title.text.strip()[:30] if title else "N/A"}
        except:
            return {'title': "ERROR"}

    # MÉTODO 1: Secuencial (uno por uno)
    print("\n⏳ MÉTODO 1: Scraping Secuencial")
    start_sequential = time.time()

    sequential_results = []
    for asin in asins:
        url = f"https://www.amazon.com/dp/{asin}"
        print(f"   Scraping {asin}...")
        result = scrape_simple(url)
        sequential_results.append(result)

    time_sequential = time.time() - start_sequential
    print(f"   ✅ Completado en {time_sequential:.2f}s")

    # MÉTODO 2: Paralelo (todos a la vez)
    print("\n⚡ MÉTODO 2: Scraping Paralelo")
    start_parallel = time.time()

    urls = [f"https://www.amazon.com/dp/{asin}" for asin in asins]

    scraper = ParallelScraper(max_workers=len(asins), rate_limit=60)
    parallel_results = scraper.scrape_urls(urls, scrape_simple)

    time_parallel = time.time() - start_parallel
    print(f"   ✅ Completado en {time_parallel:.2f}s")

    # Comparación
    speedup = time_sequential / time_parallel if time_parallel > 0 else 0

    print("\n" + "=" * 60)
    print("🏁 COMPARACIÓN FINAL")
    print("=" * 60)
    print(f"⏳ Secuencial: {time_sequential:.2f}s")
    print(f"⚡ Paralelo:   {time_parallel:.2f}s")
    print(f"🚀 Mejora:     {speedup:.1f}x más rápido")
    print("=" * 60)

    if speedup >= 2:
        print("✅ El scraping paralelo es MUCHO más rápido!")
    elif speedup >= 1.5:
        print("✅ El scraping paralelo es notablemente más rápido")
    else:
        print("⚠️  Con pocos productos, la diferencia es pequeña")


def main():
    """Ejecuta todos los demos"""
    print("\n")
    print("█" * 60)
    print("█" + " " * 58 + "█")
    print("█" + "  🥷 DEMO DEL SISTEMA ANTI-DETECCIÓN - NOLIVOS FBA  ".center(58) + "█")
    print("█" + " " * 58 + "█")
    print("█" * 60)

    print("\nEste demo muestra:")
    print("  1. ✅ Scraping individual con anti-detección completa")
    print("  2. ✅ Scraping paralelo de múltiples productos")
    print("  3. ✅ Comparación de velocidad (secuencial vs paralelo)")

    print("\n⚠️  NOTA: Este demo hace requests reales a Amazon")
    print("   Se usarán delays para no sobrecargar Splash")

    input("\n📌 Presiona ENTER para continuar...")

    try:
        # Demo 1
        demo_1_scraping_individual()
        input("\n📌 Presiona ENTER para continuar al Demo 2...")

        # Demo 2
        demo_2_scraping_paralelo()
        input("\n📌 Presiona ENTER para continuar al Demo 3...")

        # Demo 3
        demo_3_comparacion_velocidad()

        # Resumen final
        print("\n" + "=" * 60)
        print("🎉 TODOS LOS DEMOS COMPLETADOS")
        print("=" * 60)
        print("\n📚 Para más información, lee: SISTEMA_ANTIDETECCION.md")
        print("🚀 Ahora puedes usar el sistema en tus propios scripts!")
        print("\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrumpido por el usuario")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        print("💡 Verifica que Splash esté corriendo en puerto 8050")


if __name__ == "__main__":
    main()
