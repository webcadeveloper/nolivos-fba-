"""
Migration: Add all_supplier_urls column to store multiple provider links
"""
import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO)

def add_all_supplier_urls_column():
    """Add column for storing all 4 provider URLs as JSON"""

    conn = sqlite3.connect('opportunities.db')
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(opportunities)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'all_supplier_urls' in columns:
        logging.info("✅ Column 'all_supplier_urls' already exists!")
        conn.close()
        return

    # Add new column
    logging.info("📝 Adding 'all_supplier_urls' column...")
    cursor.execute("""
        ALTER TABLE opportunities
        ADD COLUMN all_supplier_urls TEXT
    """)

    conn.commit()

    # Generate all_supplier_urls for existing products
    logging.info("🔄 Generating provider URLs for existing products...")
    cursor.execute("""
        SELECT id, product_name, supplier_url
        FROM opportunities
        WHERE all_supplier_urls IS NULL
    """)

    products = cursor.fetchall()
    updated_count = 0

    for product_id, product_name, existing_url in products:
        # Generate search URLs for all 4 providers
        search_query = product_name.replace(' ', '+')

        all_urls = {
            'aliexpress': {
                'name': 'AliExpress',
                'url': f"https://www.aliexpress.com/wholesale?SearchText={search_query}",
                'icon': '🇨🇳'
            },
            'ebay': {
                'name': 'eBay',
                'url': f"https://www.ebay.com/sch/i.html?_nkw={search_query}",
                'icon': '🛒'
            },
            'walmart': {
                'name': 'Walmart',
                'url': f"https://www.walmart.com/search?q={search_query}",
                'icon': '🏪'
            },
            'target': {
                'name': 'Target',
                'url': f"https://www.target.com/s?searchTerm={search_query}",
                'icon': '🎯'
            }
        }

        # Store as JSON
        cursor.execute("""
            UPDATE opportunities
            SET all_supplier_urls = ?
            WHERE id = ?
        """, (json.dumps(all_urls), product_id))

        updated_count += 1
        if updated_count % 10 == 0:
            logging.info(f"   Procesados {updated_count}/{len(products)} productos...")

    conn.commit()
    conn.close()

    logging.info(f"✅ Migración completada!")
    logging.info(f"   - Columna agregada: all_supplier_urls")
    logging.info(f"   - Productos actualizados: {updated_count}")
    logging.info(f"   - Ahora cada producto tiene links a los 4 proveedores!")

if __name__ == "__main__":
    print("=" * 70)
    print("MIGRACIÓN: Agregar URLs de múltiples proveedores")
    print("=" * 70)
    print()

    add_all_supplier_urls_column()

    print()
    print("=" * 70)
    print("✅ MIGRACIÓN COMPLETA!")
    print("=" * 70)
