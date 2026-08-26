import sqlite3
import os
import sys

# Ensure UTF-8 printing on Windows
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), "ruralbiz.db")

def inspect_database():
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at: {DB_PATH}")
        print("Run 'python run.py' once to generate and seed the database.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cursor.fetchall()]

    print("=" * 70)
    print(f"  RURALBIZ AI DATABASE INSPECTOR ({DB_PATH})")
    print("=" * 70)
    print(f"Tables Found: {', '.join(tables)}\n")

    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]

        print("-" * 70)
        print(f" TABLE: {table.upper()} (Total Rows: {count})")
        print(f" Columns: {', '.join(columns)}")
        print("-" * 70)

        # Show up to 3 sample rows
        cursor.execute(f"SELECT * FROM {table} LIMIT 3")
        rows = cursor.fetchall()
        for idx, row in enumerate(rows, 1):
            print(f"  Row {idx}: {row}")
        print()

    conn.close()

if __name__ == "__main__":
    inspect_database()

