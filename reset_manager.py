import os
import sqlite3
from werkzeug.security import generate_password_hash

# Targets (update both to avoid mismatch)
paths = [
    os.path.abspath(os.path.join('instance','lembah_fitness.db')),
    r'D:\Praktikum Apsi\BISMILLAH\instance\lembah_fitness.db'
]

username = 'manager'
new_password = 'lembahfitness'

hash_pw = generate_password_hash(new_password, method='scrypt')

for db in paths:
    print('-> Checking', db)
    if not os.path.exists(db):
        print('   MISSING, skipping')
        continue
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT id, username FROM user WHERE username = ?", (username,))
        row = cur.fetchone()
        if not row:
            print('   No user with username', username, 'in this DB')
        else:
            cur.execute("UPDATE user SET password = ? WHERE id = ?", (hash_pw, row[0]))
            conn.commit()
            print('   Updated password for', username, 'in', db)
        conn.close()
    except Exception as e:
        print('   ERROR while updating', db, e)

print('\nDone. Restart Flask server and try logging in as:')
print('Username:', username)
print('Password:', new_password)
