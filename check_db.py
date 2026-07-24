import os
from psycopg_pool import ConnectionPool

db_url = os.environ.get("DATABASE_URL", "postgresql://dtwin:devpassword123@localhost:5433/digital_twin")
pool = ConnectionPool(db_url, open=True)

print("--- DB QUERY RESULTS ---")
with pool.connection() as conn:
    rows = conn.execute(
        "SELECT machine_id, cycle, rul_cycles, metadata->>'raw_rul' as raw_rul "
        "FROM amkb_experiences WHERE metadata->>'raw_rul' IS NOT NULL "
        "ORDER BY (metadata->>'raw_rul')::float DESC LIMIT 10"
    ).fetchall()
    
    print("Top 10 experiences by raw RUL:")
    for r in rows:
        print(f"Machine: {r[0]}, Cycle: {r[1]}, DB rul_cycles: {r[2]}, Metadata raw_rul: {r[3]}")
