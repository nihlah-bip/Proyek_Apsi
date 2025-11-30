import sqlite3
import os

# Path to database
db_path = os.path.join('instance', 'lembah_fitness.db')

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Columns to add
columns = [
    ('nama_lengkap', 'TEXT'),
    ('email', 'TEXT'),
    ('no_telepon', 'TEXT')
]

table_name = 'user'

print(f"Checking table {table_name}...")

# Get existing columns
cursor.execute(f"PRAGMA table_info({table_name})")
existing_columns = [row[1] for row in cursor.fetchall()]

for col_name, col_type in columns:
    if col_name not in existing_columns:
        print(f"Adding column {col_name}...")
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
            print(f"Column {col_name} added successfully.")
        except Exception as e:
            print(f"Error adding column {col_name}: {e}")
    else:
        print(f"Column {col_name} already exists.")

conn.commit()
conn.close()
print("Database update complete.")
