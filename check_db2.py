import os
from dotenv import load_dotenv
from psycopg_pool import ConnectionPool

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL not set in environment or .env file")

pool = ConnectionPool(db_url, open=True)

with pool.connection() as conn:
    row = conn.execute(
        "SELECT embedding <=> (SELECT embedding FROM amkb_experiences WHERE machine_id='unit_14' AND cycle=30 LIMIT 1) "
        "FROM amkb_experiences WHERE machine_id='unit_64' AND cycle=151 LIMIT 1"
    ).fetchone()
    print("Exact distance between unit_14(30) and unit_64(151):", row[0])
