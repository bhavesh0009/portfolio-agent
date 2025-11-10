"""
Database Migration Tool
Applies SQL migrations to the portfolio database
"""

import sqlite3
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / '.cache' / 'portfolio.db'
MIGRATIONS_DIR = Path(__file__).parent / 'migrations'

def get_applied_migrations(conn):
    """Get list of applied migrations"""
    cursor = conn.cursor()

    # Create migrations table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_file TEXT UNIQUE NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

    cursor.execute("SELECT migration_file FROM schema_migrations ORDER BY id")
    return {row[0] for row in cursor.fetchall()}

def apply_migration(conn, migration_file):
    """Apply a single migration file"""
    print(f"Applying migration: {migration_file.name}")

    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    cursor = conn.cursor()

    try:
        # Execute migration
        cursor.executescript(sql)

        # Record migration
        cursor.execute(
            "INSERT INTO schema_migrations (migration_file) VALUES (?)",
            (migration_file.name,)
        )

        conn.commit()
        print(f"  ✓ Successfully applied {migration_file.name}")
        return True

    except sqlite3.Error as e:
        conn.rollback()
        print(f"  ✗ Failed to apply {migration_file.name}: {e}")
        return False

def main():
    """Apply all pending migrations"""
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Please run the portfolio builder agent first to create the database.")
        sys.exit(1)

    print(f"Database: {DB_PATH}")
    print(f"Migrations directory: {MIGRATIONS_DIR}\n")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)

    # Get applied migrations
    applied = get_applied_migrations(conn)

    # Find all migration files
    migration_files = sorted(MIGRATIONS_DIR.glob('*.sql'))

    if not migration_files:
        print("No migration files found.")
        return

    # Apply pending migrations
    pending_count = 0
    for migration_file in migration_files:
        if migration_file.name not in applied:
            if apply_migration(conn, migration_file):
                pending_count += 1
        else:
            print(f"Skipping (already applied): {migration_file.name}")

    conn.close()

    print(f"\n{'=' * 60}")
    if pending_count > 0:
        print(f"Applied {pending_count} migration(s) successfully!")
    else:
        print("No pending migrations. Database is up to date.")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()
