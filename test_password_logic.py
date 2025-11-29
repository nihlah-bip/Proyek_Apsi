import sqlite3
from datetime import datetime

db_path = 'instance/lembah_fitness.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Simulate the new logic
print("=== Testing New Logic ===\n")

# Get all users
cur.execute("SELECT id, username, role FROM user")
users = cur.fetchall()
user_ids = [u[0] for u in users]

# Get logs ordered by created_at desc
cur.execute("""
    SELECT user_id, plain_password, created_at 
    FROM password_reset_log 
    WHERE user_id IN ({})
    ORDER BY created_at DESC
""".format(','.join('?' * len(user_ids))), user_ids)

logs = cur.fetchall()

# Process logs using new logic
last_pw = {}
for log in logs:
    user_id, plain_pwd, created_at = log
    
    if user_id not in last_pw:
        # Store the most recent timestamp
        last_pw[user_id] = {
            'plain': None,
            'at': created_at
        }
    
    # Try to find a legacy plaintext password (not empty)
    if plain_pwd and plain_pwd.strip() and last_pw[user_id]['plain'] is None:
        last_pw[user_id]['plain'] = plain_pwd

# Display results
print("Results:")
for user in users:
    user_id, username, role = user
    if user_id in last_pw:
        info = last_pw[user_id]
        print(f"\nUser: {username} (ID: {user_id})")
        print(f"  Role: {role}")
        if info['plain']:
            print(f"  Password: {info['plain']} (legacy)")
        else:
            print(f"  Last reset: {info['at']}")

conn.close()
