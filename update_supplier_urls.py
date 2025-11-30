"""
Script para actualizar supplier_url de productos existentes
que tienen supplier_url vacío (productos con precios estimados)
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

def update_supplier_urls():
    """Actualiza URLs de proveedores para productos existentes"""

    conn = sqlite3.connect('opportunities.db')
    cursor = conn.cursor()

    # Obtener productos sin supplier_url
    cursor.execute("""
        SELECT id, product_name, supplier_name
        FROM opportunities
        WHERE supplier_url IS NULL OR supplier_url = ''
    """)

    products = cursor.fetchall()

    if not products:
        logging.info("✅ Todos los productos ya tienen supplier_url!")
        conn.close()
        return

    logging.info(f"📦 Encontrados {len(products)} productos sin supplier_url")

    updated_count = 0

    for product_id, product_name, supplier_name in products:
        # Generar URL de búsqueda en AliExpress
        search_query = product_name.replace(' ', '+')
        aliexpress_url = f"https://www.aliexpress.com/wholesale?SearchText={search_query}"

        # Actualizar
        cursor.execute("""
            UPDATE opportunities
            SET supplier_url = ?,
                supplier_name = CASE
                    WHEN supplier_name = 'Estimado' THEN 'Estimado (AliExpress)'
                    ELSE supplier_name
                END
            WHERE id = ?
        """, (aliexpress_url, product_id))

        updated_count += 1
        logging.info(f"   ✅ Actualizado: {product_name[:50]}...")

    conn.commit()
    conn.close()

    logging.info(f"\n🎉 {updated_count} productos actualizados con supplier_url!")
    logging.info("   Ahora todos los productos tienen link para comprar en AliExpress")

if __name__ == "__main__":
    print("=" * 70)
    print("ACTUALIZACIÓN: Agregando supplier_url a productos existentes")
    print("=" * 70)
    print()

    update_supplier_urls()

    print()
    print("=" * 70)
    print("✅ ACTUALIZACIÓN COMPLETA!")
    print("=" * 70)
