from app import app
from database import get_db_connection
import json

with app.test_client() as client:
    conn = get_db_connection()
    ticket = conn.execute("SELECT id, user_id FROM tickets WHERE status = 'valid' LIMIT 1").fetchone()
    if not ticket:
        print('No valid ticket found globally to test.')
    else:
        print(f"Testing with ticket {ticket['id']} for user {ticket['user_id']}")
        from utils import SECRET_KEY
        import jwt, datetime
        token = jwt.encode({'id': ticket['user_id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, SECRET_KEY, algorithm='HS256')
        
        response = client.post(f"/api/tickets/{ticket['id']}/refund", headers={'Authorization': f'Bearer {token}'})
        print(response.status_code)
        print(response.get_data(as_text=True))
    conn.close()
