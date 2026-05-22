import os
import libsql_client
from dotenv import load_dotenv

load_dotenv()

TURSO_DB_URL = os.getenv('TURSO_DB_URL')
if TURSO_DB_URL and TURSO_DB_URL.startswith('libsql://'):
    TURSO_DB_URL = TURSO_DB_URL.replace('libsql://', 'https://')
TURSO_AUTH_TOKEN = os.getenv('TURSO_AUTH_TOKEN')

print("TURSO URL:", TURSO_DB_URL)
if not TURSO_DB_URL or not TURSO_AUTH_TOKEN:
    print("Error: Turso credentials missing in .env")
    exit(1)

try:
    print("Connecting to Turso...")
    client = libsql_client.create_client_sync(url=TURSO_DB_URL, auth_token=TURSO_AUTH_TOKEN)
    print("Connected successfully!")
    
    # 1. Check tables
    res = client.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in res.rows]
    print("Tables in Turso:", tables)
    
    # 2. Check events if table exists
    if 'events' in tables:
        res = client.execute("SELECT COUNT(*) FROM events")
        print("Total events in Turso:", res.rows[0][0])
        
        res = client.execute("SELECT id, title, status, parent_event_id FROM events")
        print("Events details:")
        for row in res.rows:
            print(f"- ID: {row[0]}, Title: {row[1]}, Status: {row[2]}, Parent: {row[3]}")
    else:
        print("Events table does not exist in Turso!")
        
except Exception as e:
    print("Error connecting/querying Turso:", e)
