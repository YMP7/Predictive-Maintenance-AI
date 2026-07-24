import os
from psycopg_pool import ConnectionPool

db_url = os.environ.get("DATABASE_URL", "postgresql://dtwin:devpassword123@localhost:5433/digital_twin")
pool = ConnectionPool(db_url, open=True)

with pool.connection() as conn:
    row = conn.execute(
        "SELECT embedding <=> (SELECT embedding FROM amkb_experiences WHERE machine_id='unit_14' AND cycle=30 LIMIT 1) "
        "FROM amkb_experiences WHERE machine_id='unit_64' AND cycle=151 LIMIT 1"
    ).fetchone()
    print("Exact distance between unit_14(30) and unit_64(151):", row[0])
