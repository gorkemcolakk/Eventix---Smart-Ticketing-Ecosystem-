from app import app
from database import get_db_connection
import json

with app.test_client() as client:
    # Get a user and a ticket
    conn = get_db_connection()
    user = conn.execute("SELECT id, email FROM users WHERE role = 'customer' LIMIT 1").fetchone()
    ticket = conn.execute("SELECT id FROM tickets WHERE user_id = ? AND status = 'valid' LIMIT 1", (user['id'],)).fetchone()
    if not ticket:
        print('No valid ticket found to test.')
    else:
        print(f"Testing with ticket {ticket['id']} for user {user['email']}")
        # We need a token for the user
        from utils import SECRET_KEY
        import jwt, datetime
        token = jwt.encode({'user_id': user['id'], 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, SECRET_KEY, algorithm='HS256')
        
        response = client.post(f"/api/tickets/{ticket['id']}/refund", headers={'Authorization': f'Bearer {token}'})
        print(response.status_code)
        print(response.get_data(as_text=True))
    conn.close()
