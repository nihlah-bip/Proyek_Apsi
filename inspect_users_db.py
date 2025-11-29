import sqlite3
import os

# Try project instance DB first
candidates = [
    os.path.join(os.path.dirname(__file__), 'instance', 'lembah_fitness.db'),
    os.path.join(os.path.dirname(__file__), '..', 'instance', 'lembah_fitness.db'),
    os.path.join(os.path.dirname(__file__), '..', '..', 'instance', 'lembah_fitness.db'),
]

for p in candidates:
    p = os.path.abspath(p)
    print('Checking:', p)
    if os.path.exists(p):
        db_path = p
        break
else:
    print('No database found in candidates')
    raise SystemExit(1)

print('\nUsing DB:', db_path)
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('\nTables:')
for row in cur.fetchall():
    print('-', row[0])

try:
    cur.execute("SELECT id, username, role, password FROM user")
    rows = cur.fetchall()
    print('\nUsers:')
    for r in rows:
        print(r)
except Exception as e:
    print('Error querying user table:', e)
finally:
    conn.close()
