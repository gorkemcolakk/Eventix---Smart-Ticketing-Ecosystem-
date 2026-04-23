import json
import pytest

def test_auth_registration_and_login(client):
    # Registration
    res = client.post('/api/auth/register', json={
        'fullname': 'New User',
        'email': 'new@mail.com',
        'password': 'Password1!',
        'role': 'user'
    })
    assert res.status_code == 201

    # Registration Duplicate
    res2 = client.post('/api/auth/register', json={
        'fullname': 'New User2',
        'email': 'new@mail.com',
        'password': 'Password1!',
        'role': 'user'
    })
    assert res2.status_code == 409

    # Login
    res = client.post('/api/auth/login', json={'email': 'new@mail.com', 'password': 'Password1!'})
    assert res.status_code == 200
    assert 'token' in json.loads(res.data)

def test_event_creation_and_filtering(client, auth_tokens):
    # 1. Create an event as Organizer
    org_headers = auth_tokens['organizer']
    event_payload = {
        'title': 'Test Concert',
        'category': 'concert',
        'date': '2026-06-01T20:00',
        'location': 'Istanbul',
        'price': 100,
        'capacity': 500,
        'description': 'A nice concert'
    }
    res = client.post('/api/events', json=event_payload, headers=org_headers)
    assert res.status_code == 201
    
    # 2. Get Events as public - shouldn't appear yet because it's 'pending'
    res = client.get('/api/events')
    data = json.loads(res.data)
    assert len(data) == 0
    
    # 3. Create as Admin (should be 'active' immediately)
    admin_headers = auth_tokens['admin']
    event_payload['title'] = 'Admin Concert'
    event_payload['price'] = 200
    res = client.post('/api/events', json=event_payload, headers=admin_headers)
    assert res.status_code == 201
    event_id = json.loads(res.data)['event_id']

    # 4. Filter by Price
    res = client.get('/api/events?min_price=150')
    data = json.loads(res.data)
    assert len(data) == 1
    assert data[0]['title'] == 'Admin Concert'

    # 5. Filter by max_price (should be empty since it's 200)
    res = client.get('/api/events?max_price=150')
    assert len(json.loads(res.data)) == 0

    # 6. Filter by Location
    res = client.get('/api/events/locations')
    locs = json.loads(res.data)
    assert 'Istanbul' in locs

def test_cart_buy_integration(client, auth_tokens):
    # 1. Create an active event
    admin_headers = auth_tokens['admin']
    res = client.post('/api/events', json={
        'title': 'Cart Concert',
        'category': 'concert',
        'date': '2026-07-01T20:00',
        'location': 'Ankara',
        'price': 300,
        'capacity': 100
    }, headers=admin_headers)
    event_id = json.loads(res.data)['event_id']

    # 2. Perform cart_buy
    user_headers = auth_tokens['user']
    cart_payload = {
        'cart_items': [{
            'event_id': event_id,
            'tickets_info': [{'name': 'John', 'surname': 'Doe'}]
        }],
        'card_name': 'Test Card',
        'card_number': '1111222233334444',
        'card_exp': '12/28',
        'cvc': '123'
    }
    
    res = client.post('/api/tickets/cart-buy', json=cart_payload, headers=user_headers)
    assert res.status_code == 201, f"Purchase failed: {res.data}"
    
    data = json.loads(res.data)
    assert 'tickets' in data
    assert len(data['tickets']) == 1

def test_seat_allocation_bug(client, auth_tokens):
    # Tests the automatic seat allocation feature introduced in Phase 2 for cart_buy
    admin_headers = auth_tokens['admin']
    res = client.post('/api/events', json={
        'title': 'Seated Theater',
        'category': 'theater',
        'date': '2026-08-01T20:00',
        'location': 'Izmir',
        'has_seating': True,
        'zones': [
            {'name': 'VIP', 'rows': 1, 'cols': 2, 'price': 500} # 2 capacity
        ]
    }, headers=admin_headers)
    event_id = json.loads(res.data)['event_id']
    
    # Buy via Cart without specifying seat_ids => should auto-allocate
    user_headers = auth_tokens['user']
    cart_payload = {
        'cart_items': [{
            'event_id': event_id,
            'tickets_info': [{'name': 'Seat', 'surname': 'User'}, {'name': 'Seat2', 'surname': 'User2'}]
        }],
        'card_name': 'Test Card',
        'card_number': '1111222233334444',
        'card_exp': '12/28',
        'cvc': '123'
    }
    
    res = client.post('/api/tickets/cart-buy', json=cart_payload, headers=user_headers)
    assert res.status_code == 201
    
    # 3. Buy 1 more than capacity -> should fail gracefully
    cart_payload['cart_items'][0]['tickets_info'] = [{'name': 'Fail', 'surname': 'User'}]
    res = client.post('/api/tickets/cart-buy', json=cart_payload, headers=user_headers)
    assert res.status_code == 400
    assert b"Not enough seats available" in res.data
