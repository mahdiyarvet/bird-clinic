"""
اسکریپت انتقال دیتا از SQLite به PostgreSQL (Neon)

استفاده:
  python migrate_to_postgres.py <NEON_DATABASE_URL>

مثال:
  python migrate_to_postgres.py "postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require"
"""
import sys
import os
import sqlite3

# Check args
if len(sys.argv) < 2:
    print("Usage: python migrate_to_postgres.py <NEON_DATABASE_URL>")
    sys.exit(1)

NEON_URL = sys.argv[1]

# Set env for app
os.environ['DATABASE_URL'] = NEON_URL

# Import app after setting env
from app import app, db, init_db

# SQLite source
SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'bird_clinic.db')

if not os.path.exists(SQLITE_PATH):
    print(f"❌ SQLite database not found at {SQLITE_PATH}")
    sys.exit(1)

print("📦 Connecting to SQLite...")
sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

print("🔗 Connecting to PostgreSQL (Neon)...")
with app.app_context():
    # Create all tables
    init_db()
    print("✅ Tables created in PostgreSQL")

    # Get all table names from SQLite
    tables_order = [
        'user', 'species', 'bird', 'medical_record', 'medication',
        'need_item', 'lab_result', 'surgery_record', 'activity_log',
        'notification', 'vaccine', 'treatment_log', 'note',
        'med_inventory'
    ]

    for table in tables_order:
        try:
            rows = sqlite_conn.execute(f'SELECT * FROM "{table}"').fetchall()
            if not rows:
                print(f"  ⏭️  {table}: empty, skipping")
                continue

            cols = [desc[0] for desc in sqlite_conn.execute(f'SELECT * FROM "{table}" LIMIT 1').description]
            
            # Clear existing data
            db.session.execute(db.text(f'DELETE FROM "{table}"'))
            
            # Insert rows
            for row in rows:
                values = dict(zip(cols, row))
                placeholders = ', '.join([f':{c}' for c in cols])
                col_names = ', '.join([f'"{c}"' for c in cols])
                db.session.execute(
                    db.text(f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})'),
                    values
                )
            
            db.session.commit()
            
            # Reset sequence for id column
            try:
                max_id = sqlite_conn.execute(f'SELECT MAX(id) FROM "{table}"').fetchone()[0]
                if max_id:
                    db.session.execute(db.text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), {max_id})"))
                    db.session.commit()
            except Exception:
                db.session.rollback()
            
            print(f"  ✅ {table}: {len(rows)} rows migrated")

        except Exception as e:
            db.session.rollback()
            print(f"  ⚠️  {table}: {e}")

sqlite_conn.close()
print("\n🎉 Migration complete!")
print("حالا میتونی Render رو دیپلوی کنی.")
