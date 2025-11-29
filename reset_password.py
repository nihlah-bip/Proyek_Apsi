import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash

# Config
USERNAME = 'manager'
NEW_PASSWORD = 'Lembah Fitness'

# Locate DB (same candidates as inspector)
candidates = [
    os.path.join(os.path.dirname(__file__), '..', 'instance', 'lembah_fitness.db'),
    os.path.join(os.path.dirname(__file__), '..', '..', 'instance', 'lembah_fitness.db'),
]

db_path = None
for p in candidates:
    p = os.path.abspath(p)
    if os.path.exists(p):
        db_path = p
        break

if not db_path:
    print('Database file not found in candidates:')
    for p in candidates:
        print('-', os.path.abspath(p))
    sys.exit(1)

print('Using DB:', db_path)

# Use scrypt to be consistent with existing hashes
new_hash = generate_password_hash(NEW_PASSWORD, method='scrypt')
print('Generated hash startswith:', new_hash.split('$',1)[0])

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute('SELECT id, username, role FROM user WHERE username=?', (USERNAME,))
row = cur.fetchone()
if not row:
    print('User not found:', USERNAME)
    conn.close()
    sys.exit(1)

print('Found user:', row)
cur.execute('UPDATE user SET password=? WHERE username=?', (new_hash, USERNAME))
conn.commit()
print('Password updated for user', USERNAME)

# Show updated row
cur.execute('SELECT id, username, role, password FROM user WHERE username=?', (USERNAME,))
print('Updated record:')
print(cur.fetchone())

conn.close()
