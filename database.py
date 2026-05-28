import os
import sys
import sqlite3
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
from dotenv import load_dotenv

# PyInstaller ile paketlendiğinde dosya yollarını doğru ayarla
if getattr(sys, 'frozen', False):
    _BASE_DIR = sys._MEIPASS
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(_BASE_DIR, '.env'))

TURSO_DB_URL = os.getenv('TURSO_DB_URL')
if TURSO_DB_URL and TURSO_DB_URL.startswith('libsql://'):
    TURSO_DB_URL = TURSO_DB_URL.replace('libsql://', 'https://')
TURSO_AUTH_TOKEN = os.getenv('TURSO_AUTH_TOKEN')

DB_PATH = os.path.join(_BASE_DIR, 'database.db')

USING_TURSO = bool(TURSO_DB_URL and TURSO_AUTH_TOKEN)

import requests
_turso_session = requests.Session()

def _turso_val(typed_val):
    """Turso HTTP API typed value -> Python value."""
    if typed_val is None or typed_val.get('type') == 'null':
        return None
    t = typed_val.get('type')
    v = typed_val.get('value')
    if t == 'integer':
        return int(v)
    if t == 'float':
        return float(v)
    return v  # text, blob, etc.

def _make_turso_arg(a):
    if a is None:
        return {'type': 'null'}
    if isinstance(a, bool):
        return {'type': 'integer', 'value': '1' if a else '0'}
    if isinstance(a, int):
        return {'type': 'integer', 'value': str(a)}
    if isinstance(a, float):
        return {'type': 'float', 'value': str(a)}
    return {'type': 'text', 'value': str(a)}

def turso_http(sql, args=None):
    """Execute a single SQL via Turso HTTP API. Returns (columns, rows, last_insert_rowid)."""
    url = TURSO_DB_URL.rstrip('/') + '/v2/pipeline'
    headers = {
        'Authorization': 'Bearer ' + TURSO_AUTH_TOKEN,
        'Content-Type': 'application/json',
    }
    typed_args = [_make_turso_arg(a) for a in (args or [])]
    body = {
        'requests': [
            {'type': 'execute', 'stmt': {'sql': sql, 'args': typed_args}},
            {'type': 'close'}
        ]
    }
    resp = _turso_session.post(url, json=body, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    result = data['results'][0]
    if result.get('type') == 'error':
        msg = result.get('error', {}).get('message', 'Turso HTTP error')
        raise sqlite3.OperationalError(msg)
    exec_result = result['response']['result']
    columns = [c['name'] for c in exec_result['cols']]
    rows = [[_turso_val(v) for v in row] for row in exec_result['rows']]
    raw_lid = exec_result.get('last_insert_rowid')
    last_insert_rowid = int(raw_lid) if raw_lid is not None else None
    return columns, rows, last_insert_rowid

class TursoRowFakeDict:
    def __init__(self, row_values, columns):
        self._row = row_values  # plain Python list
        self._columns = columns
        
    def __getitem__(self, key):
        if isinstance(key, str):
            try:
                idx = self._columns.index(key)
                return self._row[idx]
            except ValueError:
                raise KeyError(key)
        return self._row[key]
        
    def keys(self):
        return self._columns

class TursoCursor:
    def __init__(self):
        self._columns = []
        self._rows = []
        self.lastrowid = None
        
    def execute(self, sql, parameters=()):
        args = list(parameters) if parameters else []
        try:
            columns, rows, last_insert_rowid = turso_http(sql, args)
            self._columns = columns
            self._rows = rows
            if last_insert_rowid is not None:
                self.lastrowid = last_insert_rowid
        except sqlite3.OperationalError:
            raise
        except Exception as e:
            raise sqlite3.OperationalError(str(e))
        return self
        
    def executemany(self, sql, seq_of_parameters):
        url = TURSO_DB_URL.rstrip('/') + '/v2/pipeline'
        headers = {
            'Authorization': 'Bearer ' + TURSO_AUTH_TOKEN,
            'Content-Type': 'application/json',
        }
        params_list = list(seq_of_parameters)
        batch_size = 500
        try:
            for i in range(0, len(params_list), batch_size):
                chunk = params_list[i:i + batch_size]
                reqs = []
                for p in chunk:
                    typed_args = [_make_turso_arg(a) for a in (p or [])]
                    reqs.append({'type': 'execute', 'stmt': {'sql': sql, 'args': typed_args}})
                reqs.append({'type': 'close'})
                resp = _turso_session.post(url, json={'requests': reqs}, headers=headers, timeout=30)
                resp.raise_for_status()
        except Exception as e:
            raise sqlite3.OperationalError(str(e))
        return self
        
    def fetchone(self):
        if self._rows:
            return TursoRowFakeDict(self._rows[0], self._columns)
        return None
        
    def fetchall(self):
        return [TursoRowFakeDict(r, self._columns) for r in self._rows]
        
    def close(self):
        pass

class TursoConnection:
    def __init__(self):
        self.row_factory = sqlite3.Row  # Fake property to pass validation
        
    def cursor(self):
        return TursoCursor()
        
    def execute(self, sql, parameters=()):
        cur = self.cursor()
        cur.execute(sql, parameters)
        return cur
        
    def executemany(self, sql, seq_of_parameters):
        cur = self.cursor()
        cur.executemany(sql, seq_of_parameters)
        return cur
        
    def commit(self):
        pass
        
    def close(self):
        pass

def get_db_connection():
    if USING_TURSO:
        return TursoConnection()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

def init_db():
    if USING_TURSO:
        try:
            # Hizli kontrol: Eger users tablosu ve tickets.owner_name kolonu varsa,
            # veritabani zaten kuruludur, 25 tane ayri HTTP istegi atmaya gerek yok.
            turso_http("SELECT id FROM users LIMIT 1", [])
            turso_http("SELECT owner_name FROM tickets LIMIT 1", [])
            # Refunds tablosunu da kontrol et - yoksa olusturmaya izin ver
            try:
                turso_http("SELECT id FROM refunds LIMIT 1", [])
                return  # Veritabani hazir, hizlica cik
            except Exception:
                pass  # refunds tablosu yok, asagidan olustur
        except Exception:
            pass  # Eger kurulu degilse, asagidan normal sekilde tablolari olusturmaya devam et
            
    conn = get_db_connection()
    c = conn.cursor()

    # Users table — role: customer / organizer / admin
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Events table — with capacity, status, organizer_id
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            price INTEGER NOT NULL,
            image TEXT NOT NULL,
            featured INTEGER NOT NULL DEFAULT 0,
            description TEXT,
            lineup_json TEXT,
            capacity INTEGER NOT NULL DEFAULT 100,
            sold_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            organizer_id INTEGER,
            has_seating INTEGER NOT NULL DEFAULT 0,
            seating_image TEXT,
            rejection_reason TEXT,
            parent_event_id TEXT,
            recurring_config TEXT,
            FOREIGN KEY (organizer_id) REFERENCES users (id)
        )
    ''')

    # Seats table
    c.execute('''
        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            zone TEXT NOT NULL,
            row_label TEXT NOT NULL,
            col_label TEXT NOT NULL,
            price INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'available',
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    ''')

    # Tickets table — with QR code and status
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id TEXT NOT NULL,
            ticket_key TEXT NOT NULL UNIQUE,
            qr_code TEXT NOT NULL UNIQUE,
            quantity INTEGER NOT NULL DEFAULT 1,
            total_price INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'valid',
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    ''')
    
    # Try adding seat_id to tickets if it doesn't exist
    try:
        c.execute('ALTER TABLE tickets ADD COLUMN seat_id INTEGER')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        c.execute('ALTER TABLE events ADD COLUMN has_seating INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute('ALTER TABLE events ADD COLUMN seating_image TEXT')
    except sqlite3.OperationalError:
        pass

    try:
        c.execute('ALTER TABLE events ADD COLUMN rejection_reason TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute('ALTER TABLE events ADD COLUMN cancelled_by TEXT')
    except sqlite3.OperationalError:
        pass

    try:
        c.execute('ALTER TABLE events ADD COLUMN parent_event_id TEXT')
    except sqlite3.OperationalError:
        pass

    try:
        c.execute('ALTER TABLE events ADD COLUMN recurring_config TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE tickets ADD COLUMN owner_name TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        c.execute("ALTER TABLE tickets ADD COLUMN owner_surname TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        c.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN birthdate TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE users ADD COLUMN bday_promo_used_year INTEGER")
    except sqlite3.OperationalError:
        pass

    # Optimistic Locking & Seat Reservation columns
    try:
        c.execute("ALTER TABLE seats ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE seats ADD COLUMN locked_until TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE seats ADD COLUMN locked_by_session TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE events ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    # Migration: add refunded_at to tickets if missing
    try:
        c.execute("ALTER TABLE tickets ADD COLUMN refunded_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    # Refunds table — tracks all refund transactions
    c.execute('''
        CREATE TABLE IF NOT EXISTS refunds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            event_id TEXT NOT NULL,
            original_price INTEGER NOT NULL DEFAULT 0,
            refund_to_customer INTEGER NOT NULL DEFAULT 0,
            organizer_compensation INTEGER NOT NULL DEFAULT 0,
            admin_fee INTEGER NOT NULL DEFAULT 0,
            refunded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES tickets (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (event_id) REFERENCES events (id)
        )
    ''')

    # Wishlist table
    c.execute('''
        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_id TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (event_id) REFERENCES events (id),
            UNIQUE(user_id, event_id)
        )
    ''')

    # Notifications table
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Promotions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            code TEXT NOT NULL,
            discount_type TEXT NOT NULL, -- 'percentage' or 'fixed'
            discount_value INTEGER NOT NULL,
            valid_from TIMESTAMP,
            valid_until TIMESTAMP,
            usage_limit INTEGER,
            used_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (event_id) REFERENCES events (id),
            UNIQUE(event_id, code)
        )
    ''')

    # PERFORMANS OPTIMIZASYONU - INDEx'ler:
    # Bu indeksler, Events tablosunu boydan boya okurken (Full Table Scan) 
    # B-Tree algoritması kullanarak sayfa yüklenme hızını artırır (O(logN)).
    c.execute("CREATE INDEX IF NOT EXISTS idx_events_status_parent ON events (status, parent_event_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON events (date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_events_price ON events (price)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_events_location ON events (location)")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database and tables created successfully.")
