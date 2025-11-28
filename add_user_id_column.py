"""
Migration script to add user_id column to member table
"""
import sqlite3

# Connect to database
conn = sqlite3.connect('instance/lembah_fitness.db')
cursor = conn.cursor()

try:
    # Check if column exists
    cursor.execute("PRAGMA table_info(member)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'user_id' not in columns:
        # Add the user_id column
        cursor.execute('ALTER TABLE member ADD COLUMN user_id INTEGER')
        conn.commit()
        print("✓ Column user_id added successfully to member table")
    else:
        print("✓ Column user_id already exists in member table")
        
except Exception as e:
    print(f"✗ Error: {e}")
    conn.rollback()
finally:
    conn.close()

print("\nMigration completed!")
