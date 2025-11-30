"""
Migration script: Agrega campos de URLs e imágenes a la base de datos
Sin perder los datos existentes
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

def migrate_database():
    """Agrega nuevos campos a la tabla opportunities"""

    conn = sqlite3.connect('opportunities.db')
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(opportunities)")
    columns = [column[1] for column in cursor.fetchall()]

    migrations_needed = []

    if 'amazon_url' not in columns:
        migrations_needed.append(("amazon_url", "ALTER TABLE opportunities ADD COLUMN amazon_url TEXT"))

    if 'image_url' not in columns:
        migrations_needed.append(("image_url", "ALTER TABLE opportunities ADD COLUMN image_url TEXT"))

    if 'supplier_image_url' not in columns:
        migrations_needed.append(("supplier_image_url", "ALTER TABLE opportunities ADD COLUMN supplier_image_url TEXT"))

    if not migrations_needed:
        logging.info("✅ Database is already up to date! No migration needed.")
        conn.close()
        return

    # Run migrations
    for field_name, sql in migrations_needed:
        try:
            cursor.execute(sql)
            logging.info(f"✅ Added column: {field_name}")
        except Exception as e:
            logging.error(f"❌ Error adding {field_name}: {e}")

    conn.commit()
    conn.close()

    logging.info(f"\n🎉 Migration completed! Added {len(migrations_needed)} new fields.")
    logging.info("\nNew fields:")
    for field_name, _ in migrations_needed:
        logging.info(f"   - {field_name}")

if __name__ == "__main__":
    print("=" * 70)
    print("DATABASE MIGRATION: Adding URL and Image fields")
    print("=" * 70)
    print("\nThis will add:")
    print("   • amazon_url - Direct link to Amazon product")
    print("   • image_url - Product image from Amazon")
    print("   • supplier_image_url - Product image from supplier")
    print("\n" + "=" * 70)

    migrate_database()

    print("\n" + "=" * 70)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 70)
