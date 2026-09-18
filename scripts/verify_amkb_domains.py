import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL not set in environment or .env file")

pool = ConnectionPool(db_url, open=True)

with pool.connection() as conn:
    # 1. Counts by domain
    rows = conn.execute("SELECT domain, count(*) FROM amkb_experiences GROUP BY domain ORDER BY domain").fetchall()
    print("=== AMKB DOMAIN COUNTS ===")
    for domain, count in rows:
        print(f"  {domain}: {count} experiences")
    print()

    # 2. Inspect latest laptop rows
    laptop_rows = conn.execute(
        "SELECT id, domain, machine_id, cycle, health_index, rul_cycles "
        "FROM amkb_experiences WHERE domain = 'laptop' ORDER BY id DESC LIMIT 3"
    ).fetchall()
    print("=== LAPTOP EXPERIENCES (latest 3) ===")
    for r in laptop_rows:
        print(f"  id={r[0]} machine={r[2]} cycle={r[3]} health={r[4]:.4f} true_rul={r[5]}")

pool.close()
