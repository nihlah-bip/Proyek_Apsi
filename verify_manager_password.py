import sqlite3
import os
from werkzeug.security import check_password_hash

DB = os.path.join(os.path.dirname(__file__), 'instance', 'lembah_fitness.db')
print('Using DB:', DB)
if not os.path.exists(DB):
    raise SystemExit('DB not found')

conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("SELECT username, password FROM user WHERE username='manager'")
row = cur.fetchone()
if not row:
    print('manager user not found')
    conn.close()
    raise SystemExit(1)

username, pw_hash = row
print('Username:', username)
print('Stored hash prefix:', pw_hash.split('$', 1)[0])

for attempt in ['lembahfitness', 'Lembah Fitness', 'admin123', 'password']:
    ok = check_password_hash(pw_hash, attempt)
    print(f"Check '{attempt}':", ok)

conn.close()
