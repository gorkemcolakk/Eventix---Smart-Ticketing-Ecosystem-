import os
import pytest
import sqlite3
import tempfile
import sys

# Disable Turso for local testing
os.environ['TURSO_DB_URL'] = ''
os.environ['TURSO_AUTH_TOKEN'] = ''

@pytest.fixture
def app():
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()
    os.environ['TEST_DB_PATH'] = db_path
    
    # Import here so that env vars are applied
    from app import app as flask_app
    from database import init_db, get_db_connection
    
    # Override the DB_PATH locally for tests
    import database
    database.DB_PATH = db_path
    
    flask_app.config['TESTING'] = True
    
    with flask_app.app_context():
        init_db()
        yield flask_app

    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def auth_tokens(client):
    """Register and return headers for admin, organizer, and normal user"""
    import json
    
    def register_and_login(fullname, email, password, role):
        # Insert directly to set roles securely
        from database import get_db_connection
        from werkzeug.security import generate_password_hash
        conn = get_db_connection()
        conn.execute("INSERT INTO users (fullname, email, password, role) VALUES (?, ?, ?, ?)",
                     (fullname, email, generate_password_hash(password), role))
        conn.commit()
        conn.close()
        
        # Login to get token
        response = client.post('/api/auth/login', json={'email': email, 'password': password})
        token = json.loads(response.data).get('token')
        return {'Authorization': f'Bearer {token}'}
        
    return {
        'admin': register_and_login('Test Admin', 'admin@eventix.com', 'Admin123!', 'admin'),
        'organizer': register_and_login('Test Org', 'org@eventix.com', 'Org123!', 'organizer'),
        'user': register_and_login('Test User', 'user@eventix.com', 'User123!', 'user')
    }
