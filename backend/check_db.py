import sqlite3

conn = sqlite3.connect('appointments.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("Tables:", tables)
for (table,) in tables:
    cur.execute(f"PRAGMA table_info({table})")
    cols = cur.fetchall()
    print(f"\n-- {table} --")
    for col in cols:
        print(col)
conn.close()
