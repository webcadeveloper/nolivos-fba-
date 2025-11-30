"""
Migration script: Agrega campos FBA a la base de datos
Permite análisis de tamaño, peso y cumplimiento de reglas FBA
Sin perder los datos existentes
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

def migrate_database():
    """Agrega nuevos campos FBA a la tabla opportunities"""

    conn = sqlite3.connect('opportunities.db')
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(opportunities)")
    columns = [column[1] for column in cursor.fetchall()]

    migrations_needed = []

    # Campos de dimensiones (en pulgadas)
    if 'product_length' not in columns:
        migrations_needed.append(("product_length", "ALTER TABLE opportunities ADD COLUMN product_length REAL"))

    if 'product_width' not in columns:
        migrations_needed.append(("product_width", "ALTER TABLE opportunities ADD COLUMN product_width REAL"))

    if 'product_height' not in columns:
        migrations_needed.append(("product_height", "ALTER TABLE opportunities ADD COLUMN product_height REAL"))

    # Campo de peso (en libras)
    if 'product_weight' not in columns:
        migrations_needed.append(("product_weight", "ALTER TABLE opportunities ADD COLUMN product_weight REAL"))

    # Campos de rating y reviews
    if 'product_rating' not in columns:
        migrations_needed.append(("product_rating", "ALTER TABLE opportunities ADD COLUMN product_rating REAL"))

    if 'review_count' not in columns:
        migrations_needed.append(("review_count", "ALTER TABLE opportunities ADD COLUMN review_count INTEGER"))

    # Campos de cumplimiento FBA
    if 'fba_compliant' not in columns:
        migrations_needed.append(("fba_compliant", "ALTER TABLE opportunities ADD COLUMN fba_compliant BOOLEAN"))

    if 'fba_warnings' not in columns:
        migrations_needed.append(("fba_warnings", "ALTER TABLE opportunities ADD COLUMN fba_warnings TEXT"))

    if 'fba_size_tier' not in columns:
        migrations_needed.append(("fba_size_tier", "ALTER TABLE opportunities ADD COLUMN fba_size_tier TEXT"))

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
    print("DATABASE MIGRATION: Adding FBA Fields")
    print("=" * 70)
    print("\nThis will add:")
    print("   • product_length - Product length in inches")
    print("   • product_width - Product width in inches")
    print("   • product_height - Product height in inches")
    print("   • product_weight - Product weight in pounds")
    print("   • product_rating - Amazon rating (0-5 stars)")
    print("   • review_count - Number of customer reviews")
    print("   • fba_compliant - Whether product meets FBA requirements")
    print("   • fba_warnings - JSON with FBA compliance warnings")
    print("   • fba_size_tier - FBA size tier (Standard/Large/Oversize)")
    print("\n" + "=" * 70)

    migrate_database()

    print("\n" + "=" * 70)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 70)
