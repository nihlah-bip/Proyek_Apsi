import sqlite3
import os
DB = r'D:\Praktikum Apsi\BISMILLAH\instance\lembah_fitness.db'
print('Checking DB:', DB)
print('Exists:', os.path.exists(DB))
if not os.path.exists(DB):
    raise SystemExit('DB not found')
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print('\nTables:')
for t in tables:
    print('-', t[0])

if any(t[0]=='user' for t in tables):
    cur.execute("SELECT id, username, role, password FROM user")
    rows = cur.fetchall()
    print('\nUsers:')
    for r in rows:
        print(r)
else:
    print('\nNo user table in this DB')
conn.close()
