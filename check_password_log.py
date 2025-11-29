import sqlite3

db_path = 'instance/lembah_fitness.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check table structure
print("=== Table Structure ===")
cur.execute("PRAGMA table_info(password_reset_log)")
cols = cur.fetchall()
for col in cols:
    print(f"  {col[1]}: {col[2]} {'NOT NULL' if col[3] else 'NULL'}")

# Check data
print("\n=== Data in password_reset_log ===")
cur.execute("SELECT id, user_id, plain_password, created_by, created_at FROM password_reset_log ORDER BY created_at DESC LIMIT 10")
rows = cur.fetchall()
for row in rows:
    print(f"  ID: {row[0]}, User: {row[1]}, Plain: '{row[2]}', By: {row[3]}, At: {row[4]}")

# Check users
print("\n=== Users ===")
cur.execute("SELECT id, username, role FROM user")
users = cur.fetchall()
for u in users:
    print(f"  ID: {u[0]}, Username: {u[1]}, Role: {u[2]}")

conn.close()
