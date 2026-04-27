import uuid
from flask import Blueprint, request, jsonify, g
from database import get_db_connection
from utils import token_required, make_qr_base64, make_qr_bytes, create_notification, sign_ticket_data, verify_ticket_signature, send_email, send_ticket_confirmation_email, limiter, sanitize_html, cache, SECRET_KEY
import jwt
from datetime import datetime, timedelta

tickets_bp = Blueprint('tickets', __name__, url_prefix='/api/tickets')

# ─────────────────────────────────────────────────────────────────────────────
# GUEST TICKET PURCHASE
# ─────────────────────────────────────────────────────────────────────────────
@tickets_bp.route('/guest-buy', methods=['POST'])
@limiter.limit("5 per minute")
def guest_buy_ticket():
    data = request.get_json()
    event_id     = data.get('event_id')
    guest_email  = (data.get('guest_email') or '').strip().lower()
    guest_name   = (data.get('guest_name')  or '').strip()
    guest_surname= (data.get('guest_surname') or '').strip()
    promo_code   = data.get('promo_code', '').strip().upper()
    tickets_info = data.get('tickets_info', [])
    quantity     = len(tickets_info)

    if not event_id:
        return jsonify({'message': 'event_id is required'}), 400
    if not guest_email or '@' not in guest_email:
        return jsonify({'message': 'Please enter a valid email address'}), 400
    if quantity < 1:
        return jsonify({'message': 'Quantity must be at least 1'}), 400

    card_name   = data.get('card_name', '').strip()
    card_number = data.get('card_number', '').replace(' ', '')
    card_exp    = data.get('card_exp', '').strip()
    cvc         = data.get('cvc', '').strip()
    if not card_name or not card_number or not cvc or not card_exp:
        return jsonify({'message': 'Payment information missing!'}), 400

    conn = get_db_connection()
    c = conn.cursor()

    # User management
    existing = c.execute("SELECT * FROM users WHERE email = ? AND role = 'guest'", (guest_email,)).fetchone()
    if existing:
        guest_user_id = existing['id']
        guest_fullname = existing['fullname']
    else:
        real_user = c.execute("SELECT id FROM users WHERE email = ? AND role != 'guest'", (guest_email,)).fetchone()
        if real_user:
            conn.close()
            return jsonify({'message': 'Account exists for this email. Please log in.'}), 409
        import secrets
        from werkzeug.security import generate_password_hash
        random_pw = generate_password_hash(secrets.token_hex(32))
        guest_fullname = f"{guest_name} {guest_surname}"
        c.execute("INSERT INTO users (fullname, email, password, role) VALUES (?, ?, ?, 'guest')", (guest_fullname, guest_email, random_pw))
        guest_user_id = c.lastrowid

    # Event Check
    event = c.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if not event:
        conn.close()
        return jsonify({'message': 'Event not found'}), 404
    if event['status'] != 'active':
        conn.close()
        return jsonify({'message': 'Event is not active'}), 400

    total_price = 0
    seat_labels_str = "Standard"
    seats_dict = {}

    if event['has_seating']:
        seat_ids = [t.get('seat_id') for t in tickets_info if t.get('seat_id')]
        if len(seat_ids) != quantity:
            conn.close()
            return jsonify({'message': 'Seat selection required.'}), 400
        placeholders = ','.join(['?'] * len(seat_ids))
        seats = c.execute(f"SELECT * FROM seats WHERE id IN ({placeholders}) AND event_id = ? AND status = 'available'", seat_ids + [event_id]).fetchall()
        if len(seats) != quantity:
            conn.close()
            return jsonify({'message': 'Some seats are already sold.'}), 400
        for s in seats:
            total_price += s['price']
            seats_dict[str(s['id'])] = s
        seat_labels_str = ", ".join(f"{s['zone']} {s['row_label']}-{s['col_label']}" for s in seats)
    else:
        total_price = event['price'] * quantity

    # Promo Code
    promo_record = None
    if promo_code:
        promo_record = c.execute('SELECT * FROM promotions WHERE event_id = ? AND code = ?', (event_id, promo_code)).fetchone()
        if not promo_record:
            conn.close()
            return jsonify({'message': 'Invalid promo code.'}), 400
        if promo_record['usage_limit'] and promo_record['used_count'] >= promo_record['usage_limit']:
            conn.close()
            return jsonify({'message': 'Promo limit reached.'}), 400
        if promo_record['discount_type'] == 'percentage':
            total_price -= (total_price * promo_record['discount_value']) // 100
        else:
            total_price -= promo_record['discount_value']
        total_price = max(0, total_price)

    # PAYMENT
    from payment import PaymentGateway
    pay_res = PaymentGateway.process_payment(total_price, card_name, card_number, card_exp, cvc)
    if not pay_res['success']:
        conn.close()
        return jsonify({'message': pay_res['message']}), 400

    # UPDATE COUNTS AFTER SUCCESSFUL PAYMENT
    if event['has_seating']:
        c.execute(f"UPDATE seats SET status = 'sold' WHERE id IN ({placeholders})", seat_ids)
        c.execute("UPDATE events SET sold_count = sold_count + ? WHERE id = ?", (quantity, event_id))
    else:
        c.execute("UPDATE events SET sold_count = sold_count + ? WHERE id = ? AND capacity - sold_count >= ? AND status = 'active'", (quantity, event_id, quantity))
        if c.rowcount == 0:
            conn.close()
            return jsonify({'message': 'Capacity filled or event inactive.'}), 400

    # ────────────────────────────────────────────────────────
    # DYNAMIC PRICING (SURGE PRICING) - %80 DOLULUĞA ULAŞINCA FİYAT ARTAR
    # ────────────────────────────────────────────────────────
    updated_event = c.execute("SELECT sold_count, capacity, price FROM events WHERE id = ?", (event_id,)).fetchone()
    if updated_event and updated_event['capacity'] > 0:
        occupancy = updated_event['sold_count'] / updated_event['capacity']
        if occupancy > 0.8:
            new_price = int(updated_event['price'] * 1.2)
            c.execute("UPDATE events SET price = ? WHERE id = ? AND price = ?", (new_price, event_id, updated_event['price']))
    # ────────────────────────────────────────────────────────

    if promo_record:
        c.execute('UPDATE promotions SET used_count = used_count + 1 WHERE id = ?', (promo_record['id'],))

    # GENERATE TICKETS
    gen_tix = []
    for t_info in tickets_info:
        key = uuid.uuid4().hex.upper()[:12]
        # Statik QR yerine Dinamik QR altyapısı için temel seed
        q_data = sign_ticket_data(f"EVENTIX-{key}-{event_id}")
        t_p = event['price'] if not event['has_seating'] else seats_dict[str(t_info['seat_id'])]['price']
        sid = t_info.get('seat_id') if event['has_seating'] else None
        
        t_name = sanitize_html(t_info.get('name', ''))
        t_surname = sanitize_html(t_info.get('surname', ''))
        
        c.execute("INSERT INTO tickets (user_id, event_id, ticket_key, qr_code, quantity, total_price, status, owner_name, owner_surname, seat_id) VALUES (?, ?, ?, ?, ?, ?, 'valid', ?, ?, ?)",
                  (guest_user_id, event_id, key, q_data, 1, t_p, t_name, t_surname, sid))
        ticket_db_id = c.lastrowid
        
        gen_tix.append({'id': ticket_db_id, 'ticket_key': key, 'qr_code': make_qr_base64(q_data), 'name': t_name, 'surname': t_surname, 'price': t_p, 'seat_id': sid})

    conn.commit()
    conn.close()
    
    cache.clear()
    try:
        send_ticket_confirmation_email(guest_email, guest_fullname, event, gen_tix, total_price, seat_labels_str)
    except: pass

    return jsonify({'message': 'Success!', 'tickets': gen_tix, 'total_price': total_price}), 201

# ─────────────────────────────────────────────────────────────────────────────
# SEAT RESERVATION (SEPETTE BEKLETME)
# ─────────────────────────────────────────────────────────────────────────────
@tickets_bp.route('/lock-seat', methods=['POST'])
def lock_seat():
    data = request.get_json()
    seat_id = data.get('seat_id')
    session_id = request.headers.get('X-Session-ID', 'guest_session') # Basit oturum takibi
    
    conn = get_db_connection()
    # Eğer koltuk başkası tarafından kilitlenmişse ve süresi dolmamışsa
    seat = conn.execute("SELECT locked_until, locked_by_session, status FROM seats WHERE id = ?", (seat_id,)).fetchone()
    if not seat or seat['status'] != 'available':
        conn.close()
        return jsonify({'success': False, 'message': 'Seat is not available'}), 400
        
    now = datetime.now()
    if seat['locked_until']:
        locked_dt = None
        val = str(seat['locked_until'])
        if val.isdigit():
            try:
                locked_dt = datetime.fromtimestamp(int(val) / 1000.0)
            except:
                pass
        else:
            for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
                try:
                    locked_dt = datetime.strptime(val, fmt)
                    break
                except ValueError:
                    continue
        if locked_dt and locked_dt > now:
            if seat['locked_by_session'] != session_id:
                conn.close()
                return jsonify({'success': False, 'message': 'Seat is temporarily reserved by someone else'}), 409
            
    # Kilitle (10 dakika)
    lock_time = now + timedelta(minutes=10)
    conn.execute("UPDATE seats SET locked_until = ?, locked_by_session = ? WHERE id = ?", (str(lock_time), session_id, seat_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'Seat locked for 10 minutes.'})

@tickets_bp.route('/unlock-seat', methods=['POST'])
def unlock_seat():
    data = request.get_json()
    seat_id = data.get('seat_id')
    session_id = request.headers.get('X-Session-ID', 'guest_session')
    
    conn = get_db_connection()
    seat = conn.execute("SELECT locked_by_session FROM seats WHERE id = ?", (seat_id,)).fetchone()
    
    if seat and seat['locked_by_session'] == session_id:
        conn.execute("UPDATE seats SET locked_until = NULL, locked_by_session = NULL WHERE id = ?", (seat_id,))
        conn.commit()
        
    conn.close()
    return jsonify({'success': True})

# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC QR GENERATION (SAHTECİLİK ÖNLEME)
# ─────────────────────────────────────────────────────────────────────────────
@tickets_bp.route('/<int:ticket_id>/dynamic-qr', methods=['GET'])
@token_required
def get_dynamic_qr(ticket_id):
    conn = get_db_connection()
    ticket = conn.execute("SELECT * FROM tickets WHERE id = ? AND user_id = ?", (ticket_id, g.user['id'])).fetchone()
    conn.close()
    if not ticket:
        return jsonify({'message': 'Not found'}), 404
        
    # Her 30 saniyede yenilenen dinamik token (JWT)
    exp_time = datetime.utcnow() + timedelta(seconds=30)
    dynamic_payload = {
        'ticket_key': ticket['ticket_key'],
        'exp': exp_time,
        'type': 'dynamic_entry'
    }
    token = jwt.encode(dynamic_payload, SECRET_KEY, algorithm='HS256')
    return jsonify({'qr_code': make_qr_base64(token), 'expires_in': 30})

# ─────────────────────────────────────────────────────────────────────────────
# LOGGED-IN TICKET PURCHASE
# ─────────────────────────────────────────────────────────────────────────────
@tickets_bp.route('/buy', methods=['POST'])
@token_required
@limiter.limit("5 per minute")
def buy_ticket():
    data = request.get_json()
    event_id = data.get('event_id')
    promo_code = data.get('promo_code', '').strip().upper()
    tickets_info = data.get('tickets_info', [])
    quantity = len(tickets_info)

    if not event_id or quantity < 1:
        return jsonify({'message': 'Invalid request.'}), 400

    card_name, card_number = data.get('card_name'), data.get('card_number', '').replace(' ', '')
    card_exp, cvc = data.get('card_exp'), data.get('cvc')
    if not all([card_name, card_number, card_exp, cvc]):
        return jsonify({'message': 'Payment info missing.'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    event = c.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if not event or event['status'] != 'active':
        conn.close()
        return jsonify({'message': 'Event not found or inactive.'}), 404

    total_price = 0
    seats_dict = {}
    seat_labels_str = "Standard"

    if event['has_seating']:
        seat_ids = [t.get('seat_id') for t in tickets_info if t.get('seat_id')]
        placeholders = ','.join(['?'] * len(seat_ids))
        seats = c.execute(f"SELECT * FROM seats WHERE id IN ({placeholders}) AND event_id = ? AND status = 'available'", seat_ids + [event_id]).fetchall()
        if len(seats) != quantity:
            conn.close()
            return jsonify({'message': 'Some seats are unavailable.'}), 400
        for s in seats:
            total_price += s['price']
            seats_dict[str(s['id'])] = s
        seat_labels_str = ", ".join(f"{s['zone']} {s['row_label']}-{s['col_label']}" for s in seats)
    else:
        total_price = event['price'] * quantity

    # PROMO
    promo_record = None
    if promo_code:
        if promo_code == 'BDAY26':
            u = c.execute('SELECT birthdate, bday_promo_used_year FROM users WHERE id = ?', (g.user['id'],)).fetchone()
            now = datetime.now()
            if not u or not u['birthdate'] or u['birthdate'][5:10] != now.strftime('%m-%d'):
                conn.close()
                return jsonify({'message': 'Only valid on your birthday.'}), 400
            if u['bday_promo_used_year'] == now.year:
                conn.close()
                return jsonify({'message': 'Already used this year.'}), 400
            promo_record = {'id': 0, 'is_bday': True, 'discount_type': 'percentage', 'discount_value': 15}
        else:
            res = c.execute('SELECT * FROM promotions WHERE event_id = ? AND code = ?', (event_id, promo_code)).fetchone()
            promo_record = dict(res) if res else None
        
        if not promo_record:
            conn.close()
            return jsonify({'message': 'Invalid promo code.'}), 400
        
        if promo_record.get('discount_type') == 'percentage':
            total_price -= (total_price * promo_record['discount_value']) // 100
        else:
            total_price -= promo_record.get('discount_value', 0)
        total_price = max(0, total_price)

    # PAYMENT
    from payment import PaymentGateway
    pay_res = PaymentGateway.process_payment(total_price, card_name, card_number, card_exp, cvc)
    if not pay_res['success']:
        conn.close()
        return jsonify({'message': pay_res['message']}), 400

    # UPDATE COUNTS
    if event['has_seating']:
        c.execute(f"UPDATE seats SET status = 'sold' WHERE id IN ({placeholders})", seat_ids)
        c.execute("UPDATE events SET sold_count = sold_count + ? WHERE id = ?", (quantity, event_id))
    else:
        c.execute("UPDATE events SET sold_count = sold_count + ? WHERE id = ? AND capacity - sold_count >= ? AND status = 'active'", (quantity, event_id, quantity))

    # ────────────────────────────────────────────────────────
    # DYNAMIC PRICING (SURGE PRICING)
    # ────────────────────────────────────────────────────────
    updated_event = c.execute("SELECT sold_count, capacity, price FROM events WHERE id = ?", (event_id,)).fetchone()
    if updated_event and updated_event['capacity'] > 0:
        occupancy = updated_event['sold_count'] / updated_event['capacity']
        if occupancy > 0.8:
            new_price = int(updated_event['price'] * 1.2)
            c.execute("UPDATE events SET price = ? WHERE id = ? AND price = ?", (new_price, event_id, updated_event['price']))
    # ────────────────────────────────────────────────────────

    if promo_record:
        if promo_record.get('is_bday'):
            c.execute('UPDATE users SET bday_promo_used_year = ? WHERE id = ?', (datetime.now().year, g.user['id']))
        elif promo_record.get('id', 0) != 0:
            c.execute('UPDATE promotions SET used_count = used_count + 1 WHERE id = ?', (promo_record['id'],))

    gen_tix = []
    for t_info in tickets_info:
        key = uuid.uuid4().hex.upper()[:12]
        q_data = sign_ticket_data(f"EVENTIX-{key}-{event_id}")
        t_p = event['price'] if not event['has_seating'] else seats_dict[str(t_info['seat_id'])]['price']
        sid = t_info.get('seat_id') if event['has_seating'] else None
        
        t_name = sanitize_html(t_info.get('name', ''))
        t_surname = sanitize_html(t_info.get('surname', ''))
        
        c.execute("INSERT INTO tickets (user_id, event_id, ticket_key, qr_code, quantity, total_price, status, owner_name, owner_surname, seat_id) VALUES (?, ?, ?, ?, ?, ?, 'valid', ?, ?, ?)",
                  (g.user['id'], event_id, key, q_data, 1, t_p, t_name, t_surname, sid))
        ticket_db_id = c.lastrowid
        gen_tix.append({'id': ticket_db_id, 'ticket_key': key, 'qr_code': make_qr_base64(q_data), 'name': t_name, 'surname': t_surname, 'price': t_p, 'seat_id': sid})

    create_notification(conn, g.user['id'], f"Successfully purchased {quantity} tickets.")
    conn.commit()
    conn.close()
    
    cache.clear()
    try:
        send_ticket_confirmation_email(g.user['email'], g.user['fullname'], event, gen_tix, total_price, seat_labels_str)
    except: pass
    return jsonify({'message': 'Success!', 'tickets': gen_tix}), 201


# ─────────────────────────────────────────────────────────────────────────────
# CART PURCHASE (MULTI-ITEM)
# ─────────────────────────────────────────────────────────────────────────────
@tickets_bp.route('/cart-buy', methods=['POST'])
@token_required
@limiter.limit("5 per minute")
def cart_buy():
    data = request.get_json()
    cart_items = data.get('cart_items', [])
    card_name = data.get('card_name', '').strip()
    card_number = data.get('card_number', '').replace(' ', '')
    card_exp = data.get('card_exp', '').strip()
    cvc = data.get('cvc', '').strip()
    
    if not cart_items or not card_name or not card_number or not cvc:
        return jsonify({'message': 'Invalid request.'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    total_price = 0
    all_gen_tix = []
    seat_updates = []
    event_updates = []
    inserts = []
    
    for item in cart_items:
        event_id = item.get('event_id')
        promo_code = item.get('promo_code', '').strip().upper()
        tickets_info = item.get('tickets_info', [])
        quantity = len(tickets_info)
        
        event = c.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
        if not event or event['status'] != 'active':
            return jsonify({'message': 'Event not found or inactive.'}), 404
            
        item_price = 0
        seats_dict = {}
        if event['has_seating']:
            seat_ids = [t.get('seat_id') for t in tickets_info if t.get('seat_id')]
            if len(seat_ids) != quantity:
                avail_seats = c.execute("SELECT id, price, zone, row_label, col_label FROM seats WHERE event_id = ? AND status = 'available' LIMIT ?", (event_id, quantity)).fetchall()
                if len(avail_seats) < quantity:
                    return jsonify({'message': 'Not enough seats available for ' + event['title']}), 400
                seats = avail_seats
                seat_ids = [s['id'] for s in seats]
                placeholders = ','.join(['?'] * len(seat_ids))
                for idx, t in enumerate(tickets_info):
                    t['seat_id'] = seat_ids[idx]
            else:
                placeholders = ','.join(['?'] * len(seat_ids))
                seats = c.execute(f"SELECT * FROM seats WHERE id IN ({placeholders}) AND event_id = ? AND status = 'available'", seat_ids + [event_id]).fetchall()
                if len(seats) != quantity:
                    return jsonify({'message': 'Some seats are unavailable.'}), 400
            for s in seats:
                item_price += s['price']
                seats_dict[str(s['id'])] = s
            seat_updates.append((f"UPDATE seats SET status = 'sold' WHERE id IN ({placeholders})", seat_ids))
            event_updates.append(("UPDATE events SET sold_count = sold_count + ? WHERE id = ?", (quantity, event_id)))
        else:
            item_price = event['price'] * quantity
            event_updates.append(("UPDATE events SET sold_count = sold_count + ? WHERE id = ? AND capacity - sold_count >= ? AND status = 'active'", (quantity, event_id, quantity)))
            
        promo_record = None
        if promo_code:
            promo_record = c.execute('SELECT * FROM promotions WHERE event_id = ? AND code = ?', (event_id, promo_code)).fetchone()
            if promo_record:
                if promo_record['discount_type'] == 'percentage':
                    item_price -= (item_price * promo_record['discount_value']) // 100
                else:
                    item_price -= promo_record['discount_value']
                item_price = max(0, item_price)
        total_price += item_price
        
        for t_info in tickets_info:
            key = uuid.uuid4().hex.upper()[:12]
            q_data = sign_ticket_data(f"EVENTIX-{key}-{event_id}")
            t_p = event['price'] if not event['has_seating'] else seats_dict[str(t_info['seat_id'])]['price']
            sid = t_info.get('seat_id') if event['has_seating'] else None
            
            t_name = sanitize_html(t_info.get('name', ''))
            t_surname = sanitize_html(t_info.get('surname', ''))
            
            inserts.append((g.user['id'], event_id, key, q_data, 1, t_p, t_name, t_surname, sid))
            all_gen_tix.append({'ticket_key': key, 'qr_code': make_qr_base64(q_data), 'name': t_name, 'surname': t_surname, 'price': t_p, 'event_id': event_id, 'seat_id': sid})
            
    # PAYMENT
    from payment import PaymentGateway
    pay_res = PaymentGateway.process_payment(total_price, card_name, card_number, card_exp, cvc)
    if not pay_res['success']:
        conn.close()
        return jsonify({'message': pay_res['message']}), 400

    # APPLY ALL UPDATES
    try:
        for sql, params in seat_updates:
            c.execute(sql, params)
        for sql, params in event_updates:
            c.execute(sql, params)
        for params in inserts:
            c.execute("INSERT INTO tickets (user_id, event_id, ticket_key, qr_code, quantity, total_price, status, owner_name, owner_surname, seat_id) VALUES (?, ?, ?, ?, ?, ?, 'valid', ?, ?, ?)", params)
    except Exception as e:
        pass
        
    create_notification(conn, g.user['id'], f"Successfully purchased {len(all_gen_tix)} tickets.")
    conn.commit()
    
    # E-POSTA GONDERIMI
    try:
        events_dict = {}
        for sql, params in event_updates:
            eid = params[-1] if 'WHERE id = ?' in sql and len(params)==2 else params[1] # A bit hacky, so let's just query events directly
        
        # Daha güvenli event bulma
        event_ids_in_cart = set([t['event_id'] for t in all_gen_tix])
        for eid in event_ids_in_cart:
            ev = conn.execute('SELECT * FROM events WHERE id = ?', (eid,)).fetchone()
            ev_tix = [t for t in all_gen_tix if t['event_id'] == eid]
            ev_price = sum(t['price'] for t in ev_tix)
            send_ticket_confirmation_email(g.user['email'], g.user['fullname'], ev, ev_tix, ev_price, "")
    except Exception as e:
        pass

    conn.close()
    
    return jsonify({'message': 'Success!', 'tickets': all_gen_tix}), 201

@tickets_bp.route('/guest-cart-buy', methods=['POST'])
@limiter.limit("5 per minute")
def guest_cart_buy():
    data = request.get_json()
    cart_items = data.get('cart_items', [])
    guest_email = (data.get('guest_email') or '').strip().lower()
    guest_name = (data.get('guest_name') or '').strip()
    guest_surname = (data.get('guest_surname') or '').strip()
    
    card_name = data.get('card_name', '').strip()
    card_number = data.get('card_number', '').replace(' ', '')
    card_exp = data.get('card_exp', '').strip()
    cvc = data.get('cvc', '').strip()
    
    if not cart_items or not card_name or not card_number or not cvc or not guest_email:
        return jsonify({'message': 'Invalid request mapping.'}), 400

    conn = get_db_connection()
    c = conn.cursor()
    
    existing = c.execute("SELECT * FROM users WHERE email = ? AND role = 'guest'", (guest_email,)).fetchone()
    if existing:
        guest_user_id = existing['id']
    else:
        real_user = c.execute("SELECT id FROM users WHERE email = ? AND role != 'guest'", (guest_email,)).fetchone()
        if real_user:
            conn.close()
            return jsonify({'message': 'Account exists for this email.'}), 409
        import secrets
        from werkzeug.security import generate_password_hash
        random_pw = generate_password_hash(secrets.token_hex(32))
        c.execute("INSERT INTO users (fullname, email, password, role) VALUES (?, ?, ?, 'guest')", (f"{guest_name} {guest_surname}", guest_email, random_pw))
        guest_user_id = c.lastrowid
        
    total_price = 0
    all_gen_tix = []
    seat_updates = []
    event_updates = []
    inserts = []
    
    for item in cart_items:
        event_id = item.get('event_id')
        tickets_info = item.get('tickets_info', [])
        quantity = len(tickets_info)
        
        event = c.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
        if not event or event['status'] != 'active':
            return jsonify({'message': 'Event not found.'}), 404
            
        item_price = 0
        seats_dict = {}
        if event['has_seating']:
            seat_ids = [t.get('seat_id') for t in tickets_info if t.get('seat_id')]
            if len(seat_ids) != quantity:
                avail_seats = c.execute("SELECT id, price, zone, row_label, col_label FROM seats WHERE event_id = ? AND status = 'available' LIMIT ?", (event_id, quantity)).fetchall()
                if len(avail_seats) < quantity:
                    return jsonify({'message': 'Not enough seats available for ' + event['title']}), 400
                seats = avail_seats
                seat_ids = [s['id'] for s in seats]
                placeholders = ','.join(['?'] * len(seat_ids))
                for idx, t in enumerate(tickets_info):
                    t['seat_id'] = seat_ids[idx]
            else:
                placeholders = ','.join(['?'] * len(seat_ids))
                seats = c.execute(f"SELECT * FROM seats WHERE id IN ({placeholders}) AND event_id = ? AND status = 'available'", seat_ids + [event_id]).fetchall()
                if len(seats) != quantity:
                    return jsonify({'message': 'Some seats are unavailable.'}), 400
            for s in seats:
                item_price += s['price']
                seats_dict[str(s['id'])] = s
            seat_updates.append((f"UPDATE seats SET status = 'sold' WHERE id IN ({placeholders})", seat_ids))
            event_updates.append(("UPDATE events SET sold_count = sold_count + ? WHERE id = ?", (quantity, event_id)))
        else:
            item_price = event['price'] * quantity
            event_updates.append(("UPDATE events SET sold_count = sold_count + ? WHERE id = ? AND capacity - sold_count >= ? AND status = 'active'", (quantity, event_id, quantity)))
            
        total_price += item_price # Simplified without promo code for guest for now to keep size small
        for t_info in tickets_info:
            key = uuid.uuid4().hex.upper()[:12]
            q_data = sign_ticket_data(f"EVENTIX-{key}-{event_id}")
            t_p = event['price'] if not event['has_seating'] else seats_dict[str(t_info['seat_id'])]['price']
            t_name = sanitize_html(t_info.get('name', ''))
            t_surname = sanitize_html(t_info.get('surname', ''))
            sid = t_info.get('seat_id') if event['has_seating'] else None
            
            inserts.append((guest_user_id, event_id, key, q_data, 1, t_p, t_name, t_surname, sid))
            all_gen_tix.append({'ticket_key': key, 'qr_code': make_qr_base64(q_data), 'name': t_name, 'surname': t_surname, 'price': t_p, 'event_id': event_id, 'seat_id': sid})
            
    from payment import PaymentGateway
    pay_res = PaymentGateway.process_payment(total_price, card_name, card_number, card_exp, cvc)
    if not pay_res['success']:
        conn.close()
        return jsonify({'message': pay_res['message']}), 400

    for sql, params in seat_updates:
        c.execute(sql, params)
    for sql, params in event_updates:
        c.execute(sql, params)
    for params in inserts:
        c.execute("INSERT INTO tickets (user_id, event_id, ticket_key, qr_code, quantity, total_price, status, owner_name, owner_surname, seat_id) VALUES (?, ?, ?, ?, ?, ?, 'valid', ?, ?, ?)", params)
        
    conn.commit()
    
    # E-POSTA GONDERIMI
    try:
        event_ids_in_cart = set([t['event_id'] for t in all_gen_tix])
        for eid in event_ids_in_cart:
            ev = conn.execute('SELECT * FROM events WHERE id = ?', (eid,)).fetchone()
            ev_tix = [t for t in all_gen_tix if t['event_id'] == eid]
            ev_price = sum(t['price'] for t in ev_tix)
            send_ticket_confirmation_email(guest_email, guest_name + " " + guest_surname, ev, ev_tix, ev_price, "")
    except Exception as e:
        pass

    conn.close()
    
    return jsonify({'message': 'Success!', 'tickets': all_gen_tix}), 201

# --- MY TICKETS ---

@tickets_bp.route('/my-tickets', methods=['GET'])
@token_required
def my_tickets():
    conn = get_db_connection()
    tickets = conn.execute('''
        SELECT t.id, t.ticket_key, t.qr_code, t.quantity, t.total_price,
               t.status, t.purchase_date, t.owner_name, t.owner_surname,
               e.title, e.date, e.location, e.image, e.id as event_id,
               s.zone, s.row_label, s.col_label
        FROM tickets t
        JOIN events e ON t.event_id = e.id
        LEFT JOIN seats s ON t.seat_id = s.id
        WHERE t.user_id = ?
        ORDER BY t.id DESC
    ''', (g.user['id'],)).fetchall()
    conn.close()
    return jsonify([dict(t) for t in tickets]), 200

# --- VALIDATE ---
@tickets_bp.route('/validate_by_qr', methods=['POST'])
@token_required
def validate_by_qr():
    data = request.get_json() or {}
    qr_code = data.get('qr_code', '').strip()
    action  = data.get('action', 'check') 
    # Dinamik QR için JWT kontrolü
    is_dynamic = False
    try:
        payload = jwt.decode(qr_code, SECRET_KEY, algorithms=['HS256'])
        if payload.get('type') == 'dynamic_entry':
            ticket_key = payload['ticket_key']
            is_dynamic = True
    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'message': 'Dynamic QR Code expired! Please refresh.'}), 400
    except jwt.InvalidTokenError:
        is_dynamic = False
    
    conn = get_db_connection()
    if is_dynamic:
        t = conn.execute('''
            SELECT t.*, e.organizer_id, e.title, e.date, e.location
            FROM tickets t JOIN events e ON t.event_id = e.id
            WHERE t.ticket_key = ?
        ''', (ticket_key,)).fetchone()
    else:
        # Statik QR Geri Dönük Uyumluluk
        if not verify_ticket_signature(qr_code):
            conn.close()
            return jsonify({'valid': False, 'message': 'Invalid signature.'}), 400
            
        t = conn.execute('''
            SELECT t.*, e.organizer_id, e.title, e.date, e.location
            FROM tickets t JOIN events e ON t.event_id = e.id
            WHERE t.qr_code = ?
        ''', (qr_code,)).fetchone()

    if not t:
        conn.close()
        return jsonify({'valid': False, 'message': 'Not found.'}), 404
    if g.user['role'] == 'organizer' and t['organizer_id'] != g.user['id']:
        conn.close()
        return jsonify({'valid': False, 'message': 'No permission.'}), 403

    ticket_data = dict(t)

    # Already used ticket - return invalid with status
    if t['status'] == 'used':
        conn.close()
        return jsonify({
            'valid': False,
            'status': 'already_used',
            'message': 'This ticket has already been used!',
            'ticket': ticket_data
        }), 200

    if action == 'use' and t['status'] == 'valid':
        conn.execute("UPDATE tickets SET status = 'used' WHERE id = ?", (t['id'],))
        conn.commit()
        ticket_data['status'] = 'used'

    conn.close()
    return jsonify({'valid': True, 'ticket': ticket_data}), 200

# --- PROMO VALIDATE ---
@tickets_bp.route('/validate_promo', methods=['POST'])
@token_required
def validate_promo():
    data = request.get_json()
    eid, code = data.get('event_id'), data.get('code', '').strip().upper()
    if code == 'BDAY26':
        conn = get_db_connection()
        u = conn.execute('SELECT birthdate FROM users WHERE id = ?', (g.user['id'],)).fetchone()
        conn.close()
        if not u or u['birthdate'][5:10] != datetime.now().strftime('%m-%d'):
            return jsonify({'valid': False, 'message': 'Only on birthday.'}), 400
        return jsonify({'valid': True, 'message': 'Birthday discount applied!', 'discount_type': 'percentage', 'discount_value': 15}), 200
    conn = get_db_connection()
    p = conn.execute('SELECT * FROM promotions WHERE event_id = ? AND code = ?', (eid, code)).fetchone()
    conn.close()
    if not p: return jsonify({'valid': False, 'message': 'Invalid promo code.'}), 404
    return jsonify({'valid': True, 'message': 'Promo code applied!', 'discount_type': p['discount_type'], 'discount_value': p['discount_value']}), 200
