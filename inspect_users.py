import sqlite3
import os
import sys

# Path database relative to this script
db_path = os.path.join(os.path.dirname(__file__), 'lembah_fitness.db')
print('DB path:', db_path)
print('Exists:', os.path.exists(db_path))

if not os.path.exists(db_path):
    print('Database file not found at path above')
    sys.exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Show available tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('\nTables in DB:')
for row in cur.fetchall():
    print('-', row[0])

# Try to query user table
try:
    cur.execute("SELECT id, username, role, password FROM user")
    rows = cur.fetchall()
    print('\nUsers:')
    if not rows:
        print('No users found')
    for r in rows:
        print(r)
except Exception as e:
    print('\nError querying user table:', e)
    cur.execute("SELECT type, name, sql FROM sqlite_master LIMIT 50")
    for r in cur.fetchall():
        print(r)
finally:
    conn.close()
