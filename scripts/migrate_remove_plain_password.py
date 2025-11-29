"""
Simple SQLite migration script to remove the `plain_password` column from
`PasswordResetLog` table by recreating the table without that column.

Usage:
  python scripts/migrate_remove_plain_password.py [path/to/lembah_fitness.db]

The script will create a backup copy of the DB next to the original with
`.backup-before-remove-plainpw-<timestamp>.db` suffix before applying changes.
"""
import sqlite3
import sys
import os
import shutil
from datetime import datetime

DEFAULT_DB = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'lembah_fitness.db'))


def main(db_path=None):
    if not db_path:
        db_path = DEFAULT_DB
    db_path = os.path.abspath(db_path)

    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return 1

    # backup
    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    backup = db_path + f".backup-before-remove-plainpw-{ts}.db"
    shutil.copy2(db_path, backup)
    print(f"Backup created: {backup}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Check if table exists and if column plain_password exists
    cur.execute("PRAGMA table_info(PasswordResetLog)")
    cols = cur.fetchall()
    col_names = [c[1] for c in cols]
    print('Existing columns:', col_names)

    if 'plain_password' not in col_names:
        print('Column plain_password not found; nothing to do.')
        conn.close()
        return 0

    try:
        # Create new table without plain_password
        cur.execute('''
        CREATE TABLE IF NOT EXISTS PasswordResetLog_new (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_by INTEGER,
            created_at DATETIME
        );
        ''')

        # Copy over existing data excluding plain_password
        cur.execute('''
        INSERT INTO PasswordResetLog_new (id, user_id, created_by, created_at)
        SELECT id, user_id, created_by, created_at FROM PasswordResetLog;
        ''')

        # Drop old table and rename
        cur.execute('DROP TABLE PasswordResetLog;')
        cur.execute('ALTER TABLE PasswordResetLog_new RENAME TO PasswordResetLog;')

        conn.commit()
        print('Migration completed: plain_password column removed (table recreated).')
    except Exception as e:
        conn.rollback()
        print('Migration failed:', e)
        print('Restoring from backup...')
        shutil.copy2(backup, db_path)
        print('Restored backup.')
        return 2
    finally:
        conn.close()

    return 0


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(main(arg))
