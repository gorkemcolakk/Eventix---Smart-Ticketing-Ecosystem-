import os
import sqlite3
import libsql_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TURSO_DB_URL = os.getenv('TURSO_DB_URL')
if TURSO_DB_URL and TURSO_DB_URL.startswith('libsql://'):
    TURSO_DB_URL = TURSO_DB_URL.replace('libsql://', 'https://')
TURSO_AUTH_TOKEN = os.getenv('TURSO_AUTH_TOKEN')

if not TURSO_DB_URL or not TURSO_AUTH_TOKEN:
    print("Error: TURSO_DB_URL or TURSO_AUTH_TOKEN is missing in .env!")
    exit(1)

# Debug: list all .db files in the folder and print their tables
print("Searching for databases in folder:")
db_files = [f for f in os.listdir('.') if f.endswith('.db')]
for f in db_files:
    print(f"- {f}")
    try:
        conn = sqlite3.connect(f)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        print(f"  Tables in {f}: {', '.join(tables)}")
        
        # Check if events table exists and has rows
        if 'events' in tables:
            c.execute("SELECT COUNT(*) FROM events")
            print(f"  Rows in 'events': {c.fetchone()[0]}")
        conn.close()
    except Exception as e:
        print(f"  Error reading {f}: {e}")

# Find local SQLite database containing data
local_db_file = None
for name in db_files:
    try:
        conn = sqlite3.connect(name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM events")
            count = cursor.fetchone()[0]
            if count > 0:
                local_db_file = name
                print(f"[FOUND] Found local SQLite database: {name} with {count} events!")
                conn.close()
                break
        conn.close()
    except Exception as e:
        pass

if not local_db_file:
    print("[ERROR] Could not find a local database file with event records to migrate.")
    exit(1)

print(f"[CONNECTING] Connecting to Turso Cloud DB: {TURSO_DB_URL}...")
try:
    turso_client = libsql_client.create_client_sync(url=TURSO_DB_URL, auth_token=TURSO_AUTH_TOKEN)
    print("[OK] Connected to Turso!")
except Exception as e:
    print(f"[ERROR] Failed to connect to Turso: {e}")
    exit(1)

# 1. Initialize schema in Turso (Run database.init_db() logic)
print("[INFO] Initializing tables on Turso...")
from database import init_db, USING_TURSO
# Force using Turso for initialization
import database
database.USING_TURSO = True
database._client = turso_client
init_db()
print("[OK] Turso schema is ready!")

# 2. Migration function
tables_to_migrate = ['users', 'events', 'seats', 'tickets', 'wishlist', 'notifications', 'promotions', 'refunds']

local_conn = sqlite3.connect(local_db_file)
local_conn.row_factory = sqlite3.Row
local_cursor = local_conn.cursor()

for table in tables_to_migrate:
    print(f"\n[SYNC] Migrating table: {table}...")
    try:
        # Check if table exists in local
        local_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not local_cursor.fetchone():
            print(f"[INFO] Table {table} does not exist locally. Skipping.")
            continue

        # Get rows from local
        local_cursor.execute(f"SELECT * FROM {table}")
        rows = local_cursor.fetchall()
        if not rows:
            print(f"[INFO] Table {table} is empty locally. Skipping.")
            continue

        print(f"Found {len(rows)} rows to migrate.")
        
        # Clear existing data in Turso for a clean sync
        print(f"[CLEAN] Clearing existing {table} in Turso...")
        turso_client.execute(f"DELETE FROM {table}")

        # Insert rows into Turso
        columns = rows[0].keys()
        col_names = ", ".join(columns)
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"

        # Convert Row objects to lists of values
        statements = []
        from libsql_client import Statement
        for r in rows:
            vals = [r[col] for col in columns]
            statements.append(Statement(sql, vals))

        # Upload in batches of 100 to avoid connection limits
        batch_size = 100
        for i in range(0, len(statements), batch_size):
            chunk = statements[i:i + batch_size]
            turso_client.batch(chunk)
            print(f"  Uploaded rows {i+1} to {min(i+batch_size, len(statements))}")

        print(f"[OK] Successfully migrated {table}!")
    except Exception as e:
        print(f"[ERROR] Failed to migrate {table}: {e}")

local_conn.close()
print("\n[SUCCESS] ALL LOCAL DATA SUCCESSFULLY MIGRATED TO TURSO CLOUD DB!")
