import uuid
import json
from flask import Blueprint, request, jsonify, g
from database import get_db_connection
from utils import token_required, role_required, event_to_dict, create_notification, sanitize_html, cache

events_bp = Blueprint('events', __name__, url_prefix='/api/events')

@events_bp.route('', methods=['GET'])
@cache.cached(timeout=60, query_string=True)
def get_events():
    category = request.args.get('category', '').strip()
    search = request.args.get('search', '').strip()

    conn = get_db_connection()
    query = "SELECT * FROM events WHERE status = 'active' AND parent_event_id IS NULL"
    params = []

    if category and category != 'all':
        query += " AND category = ?"
        params.append(category)

    if search:
        query += " AND (title LIKE ? OR location LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])

    min_price = request.args.get('min_price', type=int)
    max_price = request.args.get('max_price', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    loc = request.args.get('location')

    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)
    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date + "T00:00:00")
    if end_date:
        query += " AND date <= ?"
        params.append(end_date + "T23:59:59")
    if loc and loc != 'all':
        query += " AND location LIKE ?"
        params.append(f'%{loc.strip()}%')

    sort_opt = request.args.get('sort')
    if sort_opt == 'price_asc':
        query += " ORDER BY price ASC"
    elif sort_opt == 'price_desc':
        query += " ORDER BY price DESC"
    elif sort_opt == 'date_desc':
        query += " ORDER BY date DESC"
    else:
        # Default sort by date upcoming
        query += " ORDER BY date ASC"

    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 12, type=int)
    offset = (page - 1) * limit

    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    events = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([event_to_dict(e) for e in events]), 200

@events_bp.route('/locations', methods=['GET'])
@cache.cached(timeout=300)
def get_locations():
    conn = get_db_connection()
    rows = conn.execute("SELECT DISTINCT location FROM events WHERE status = 'active' AND parent_event_id IS NULL").fetchall()
    conn.close()
    
    locations = set()
    for r in rows:
        loc_str = r['location'].strip()
        if loc_str:
            locations.add(loc_str)
            
    return jsonify(sorted(list(locations))), 200

@events_bp.route('/<event_id>', methods=['GET'])
def get_event(event_id):
    # Manually check for token if present to populate g.user for session visibility
    from utils import decode_token
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            g.user = decode_token(token)
        except Exception:
            g.user = None

    conn = get_db_connection()
    e = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if not e:
        conn.close()
        return jsonify({'message': 'Event not found'}), 404
    
    event_dict = event_to_dict(e)
    
    # Check if recurring and load sessions
    sessions = []
    if event_dict.get('recurring_config') or event_dict.get('parent_event_id'):
        parent_id = event_dict.get('parent_event_id') or event_dict['id']
        # If admin, show everything. If public, show only active.
        status_filter = "('active', 'pending', 'rejected')" if hasattr(g, 'user') and g.user and g.user.get('role') == 'admin' else "('active')"
        
        rows = conn.execute(f'''
            SELECT id, date, title 
            FROM events 
            WHERE (id = ? OR parent_event_id = ?) 
              AND status IN {status_filter}
            ORDER BY date ASC
        ''', (parent_id, parent_id)).fetchall()
        for r in rows:
            sessions.append({'id': r['id'], 'date': r['date'], 'title': r['title']})
            
    conn.close()
    event_dict['sessions'] = sessions

    if event_dict.get('has_seating'):
        # Just include a flag so the frontend knows it needs to fetch seats
        pass
        
    return jsonify(event_dict), 200

@events_bp.route('/<event_id>/seats', methods=['GET'])
def get_event_seats(event_id):
    session_id = request.headers.get('X-Session-ID', 'guest_session')

    # Mevcut kullanıcının ID'sini JWT'den al (opsiyonel - yoksa None)
    current_user_id = None
    try:
        import jwt as _jwt
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            from utils import SECRET_KEY
            payload = _jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            current_user_id = payload.get('id')
    except (_jwt.ExpiredSignatureError, _jwt.InvalidTokenError, Exception):
        current_user_id = None

    conn = get_db_connection()
    seats_raw = conn.execute('SELECT * FROM seats WHERE event_id = ?', (event_id,)).fetchall()

    # Mevcut kullanıcının bu etkinlikte satın aldığı koltuk ID'lerini çek
    my_seat_ids = set()
    if current_user_id:
        my_tickets = conn.execute(
            "SELECT seat_id FROM tickets WHERE event_id = ? AND user_id = ? AND seat_id IS NOT NULL AND status IN ('valid', 'used')",
            (event_id, current_user_id)
        ).fetchall()
        my_seat_ids = {row['seat_id'] for row in my_tickets}

    conn.close()

    from datetime import datetime
    now = datetime.now()

    seats = []
    for s in seats_raw:
        seat_dict = dict(s)
        is_locked = False
        is_my_lock = False

        # Hiyerarşi Kontrolü: Koltuk zaten SATILMIŞSA (sold), sepet (lock) kontrolünü atla.
        if seat_dict.get('status') != 'sold' and seat_dict.get('locked_until'):
            locked_dt = None
            val = str(seat_dict.get('locked_until'))

            # Eğer değer tamamen rakamlardan oluşuyorsa (timestamp - milisaniye)
            if val.isdigit():
                try:
                    from datetime import datetime
                    locked_dt = datetime.fromtimestamp(int(val) / 1000.0)
                except (ValueError, OSError):
                    pass
            else:
                # Checkout formatlarını dene
                for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%dT%H:%M:%S'):
                    try:
                        locked_dt = datetime.strptime(val, fmt)
                        break
                    except ValueError:
                        continue

            if locked_dt and locked_dt > now:
                is_locked = True
                if seat_dict.get('locked_by_session') == session_id:
                    is_my_lock = True

        seat_dict['is_locked'] = is_locked
        seat_dict['is_my_lock'] = is_my_lock
        # is_mine: Bu koltuk mevcut giriş yapmış kullanıcı tarafından satın alındıysa True
        seat_dict['is_mine'] = seat_dict['id'] in my_seat_ids
        seats.append(seat_dict)

    return jsonify(seats), 200

@events_bp.route('', methods=['POST'])
@role_required('organizer', 'admin')
def create_event():
    cache.clear()
    import datetime as dt
    import calendar as cal_mod

    data = request.get_json()
    is_seated = bool(data.get('has_seating'))

    required = ['title', 'category', 'date', 'location']
    if not is_seated:
        required.extend(['price', 'capacity'])
    for field in required:
        if not data.get(field) and data.get(field) != 0:
            return jsonify({'message': f'{field} field is required'}), 400

    recurring = data.get('recurring')  # {type: 'daily'|'weekly'|'monthly', end_date: 'YYYY-MM-DDTHH:MM'}
    if recurring:
        if not recurring.get('end_date'):
            return jsonify({'message': 'End date is required for recurring events'}), 400

    lineup_json = json.dumps(data.get('lineup', []))
    default_images = {
        'concert': 'https://images.unsplash.com/photo-1540039155733-5bb30b4a574b?w=800&auto=format&fit=crop',
        'theater': 'https://images.unsplash.com/photo-1503095396549-807759245b35?w=800&auto=format&fit=crop',
        'workshop': 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&auto=format&fit=crop',
    }
    image_url = data.get('image', '').strip() or default_images.get(data['category'], default_images['concert'])

    event_status = 'active' if g.user['role'] == 'admin' else 'pending'
    has_seating  = 1 if data.get('has_seating') else 0
    zones        = data.get('zones', [])

    conn = get_db_connection()

    # ── sanitize string inputs ──────────────────────────────
    s_title = sanitize_html(data.get('title'))
    s_cat = sanitize_html(data.get('category'))
    s_loc = sanitize_html(data.get('location'))
    s_desc = sanitize_html(data.get('description', ''))

    base_price     = int(data.get('price', 0))
    total_capacity = int(data.get('capacity', 0))
    if has_seating and zones:
        base_price     = min([int(z.get('price', 0)) for z in zones if 'price' in z], default=base_price)
        total_capacity = sum([int(z.get('rows', 1)) * int(z.get('cols', 1)) for z in zones])

    # ── helper: insert one event record + its seats ──────────────
    def _insert_event(ev_id, ev_date_str, parent_id=None, rec_cfg=None):
        conn.execute('''
            INSERT INTO events (id, title, category, date, location, price, image, featured,
                                description, lineup_json, capacity, sold_count, status,
                                organizer_id, has_seating, seating_image,
                                parent_event_id, recurring_config)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
        ''', (
            ev_id, s_title, s_cat, ev_date_str, s_loc,
            base_price, image_url, 1 if data.get('featured') else 0,
            s_desc, lineup_json, total_capacity,
            event_status, g.user['id'], has_seating, data.get('seating_image', ''),
            parent_id, json.dumps(rec_cfg) if rec_cfg else None
        ))
        if has_seating and zones:
            all_seats = []
            for z in zones:
                zn   = z.get('name', 'Blok')
                rows = int(z.get('rows', 1))
                cols = int(z.get('cols', 1))
                zp   = int(z.get('price', base_price))
                for r in range(1, rows + 1):
                    rl = chr(64 + r) if rows <= 26 else str(r)
                    for c in range(1, cols + 1):
                        all_seats.append((ev_id, zn, rl, str(c), zp))
            
            if all_seats:
                conn.executemany(
                    "INSERT INTO seats (event_id, zone, row_label, col_label, price, status) "
                    "VALUES (?, ?, ?, ?, ?, 'available')",
                    all_seats
                )

    # ── insert first (parent) event ──────────────────────────────
    parent_id = 'evt-' + uuid.uuid4().hex.upper()[:8]
    rec_cfg_save = {'type': recurring['type'], 'end_date': recurring['end_date']} if recurring else None
    _insert_event(parent_id, data['date'], parent_id=None, rec_cfg=rec_cfg_save)
    created_count = 1

    # ── generate child occurrences ───────────────────────────────
    if recurring:
        try:
            start_dt = dt.datetime.fromisoformat(data['date'])
            end_dt   = dt.datetime.fromisoformat(recurring['end_date'])
            if end_dt <= start_dt:
                conn.rollback()
                conn.close()
                return jsonify({'message': 'End date must be after the start date'}), 400

            rec_type = recurring.get('type', 'weekly')
            current_dt = start_dt
            while created_count <= 365:
                if rec_type == 'monthly':
                    m  = current_dt.month + 1
                    y  = current_dt.year + (m - 1) // 12
                    m  = (m - 1) % 12 + 1
                    d_num = min(current_dt.day, cal_mod.monthrange(y, m)[1])
                    next_dt = current_dt.replace(year=y, month=m, day=d_num)
                elif rec_type == 'weekly':
                    next_dt = current_dt + dt.timedelta(weeks=1)
                else:  # daily
                    next_dt = current_dt + dt.timedelta(days=1)

                if next_dt > end_dt:
                    break

                child_id = 'evt-' + uuid.uuid4().hex.upper()[:8]
                _insert_event(child_id, next_dt.isoformat(timespec='minutes'), parent_id=parent_id)
                current_dt = next_dt
                created_count += 1

        except Exception as ex:
            import traceback
            traceback.print_exc()
            conn.rollback()
            conn.close()
            return jsonify({'message': f'Failure at session {created_count}: {str(ex)}'}), 500

    if event_status == 'pending':
        notif = (
            f"Your event '{data['title']}' ({created_count} sessions) has been sent for admin approval."
            if created_count > 1
            else f"Your event '{data['title']}' has been sent for admin approval. It will appear on the site once approved."
        )
        create_notification(conn, g.user['id'], notif)

    conn.commit()
    conn.close()

    suffix = f" ({created_count} sessions created)" if created_count > 1 else ""
    msg = ('Event created and sent for admin approval.' if event_status == 'pending' else 'Event published.') + suffix
    return jsonify({'message': msg, 'event_id': parent_id, 'status': event_status, 'occurrences': created_count}), 201

@events_bp.route('/<event_id>', methods=['PATCH'])
@role_required('organizer', 'admin')
def update_event(event_id):
    cache.clear()
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if not event:
        conn.close()
        return jsonify({'message': 'Event not found'}), 404

    if g.user['role'] == 'organizer' and event['organizer_id'] != g.user['id']:
        conn.close()
        return jsonify({'message': 'You are not authorized to edit this event'}), 403

    data = request.get_json()
    fields = []
    values = []
    
    # Track if significant fields are changed
    needs_reapproval = False
    significant_fields = {'title', 'category', 'date', 'location', 'price', 'capacity', 'image', 'seating_image'}
    
    for col in ['title', 'category', 'date', 'location', 'price', 'capacity', 'description', 'image', 'featured', 'seating_image']:
        if col in data:
            # Koltuklu etkinliklerde fiyat/kapasite koltuklardan geldiği için 
            # manuel 0 gönderimini (düzenleme sırasında) yoksayalım.
            if col in ['price', 'capacity'] and event['has_seating'] and data[col] == 0:
                continue
                
            fields.append(f"{col} = ?")
            val = data[col]
            if col in ['title', 'category', 'location', 'description'] and isinstance(val, str):
                val = sanitize_html(val)
            values.append(val)
            
            if col in significant_fields:
                needs_reapproval = True

    if not fields:
        conn.close()
        return jsonify({'message': 'No fields to update'}), 400

    # If an organizer edits their event...
    if g.user['role'] == 'organizer':
        # 1. Any update to a REJECTED event should resubmit it for approval
        # 2. Significant updates to ACTIVE events should resubmit them for approval
        if event['status'] == 'rejected' or (needs_reapproval and event['status'] != 'pending'):
            fields.append("status = 'pending'")
            fields.append("rejection_reason = NULL") # Clear previous rejection reason
            create_notification(conn, g.user['id'], f"Your event '{event['title']}' status has been reset to pending for admin approval.")
            needs_reapproval = True # Ensure we return the 'pending' status in the response

    values.append(event_id)
    conn.execute(f"UPDATE events SET {', '.join(fields)} WHERE id = ?", values)
    
    # Koltuk güncelleme mantığı (Eğer zones gelmişse ve henüz bilet satılmamışsa)
    zones = data.get('zones')
    if (event['has_seating'] or data.get('has_seating')) and zones and event['sold_count'] == 0:
        needs_reapproval = True # Koltuk planı değiştiyse mutlaka onay gereksin
        # Eski koltukları temizle
        conn.execute("DELETE FROM seats WHERE event_id = ?", (event_id,))
        # Yeni koltukları oluştur
        all_new_seats = []
        for z in zones:
            zone_name = z.get('name', 'Blok')
            rows = int(z.get('rows', 1))
            cols = int(z.get('cols', 1))
            z_price = int(z.get('price', 0))
            for r in range(1, rows + 1):
                row_label = chr(64 + r) if rows <= 26 else str(r)
                for c in range(1, cols + 1):
                    all_new_seats.append((event_id, zone_name, row_label, str(c), z_price, 'available'))
        
        if all_new_seats:
            conn.executemany(
                'INSERT INTO seats (event_id, zone, row_label, col_label, price, status) VALUES (?,?,?,?,?,?)',
                all_new_seats
            )
    
    # Kapasite ve Fiyat senkronizasyonu (Koltuklu etkinlikse koltukları say)
    if event['has_seating'] or data.get('has_seating'):
        stats = conn.execute("SELECT COUNT(*), MIN(price) FROM seats WHERE event_id = ?", (event_id,)).fetchone()
        if stats and stats[0] > 0:
            conn.execute("UPDATE events SET capacity = ?, price = ? WHERE id = ?", (stats[0], stats[1], event_id))

    conn.commit()
    conn.close()
    
    if g.user['role'] == 'organizer' and needs_reapproval and event['status'] != 'pending':
        return jsonify({'message': 'Event updated and resubmitted for admin approval', 'status': 'pending'}), 200
    return jsonify({'message': 'Event updated', 'status': event['status']}), 200

@events_bp.route('/<event_id>', methods=['DELETE', 'POST'])
@role_required('organizer', 'admin')
def cancel_event(event_id):
    cache.clear()
    permanent = request.args.get('permanent', 'false').lower() == 'true'
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    if not event:
        conn.close()
        return jsonify({'message': 'Event not found'}), 404

    if g.user['role'] == 'organizer' and event['organizer_id'] != g.user['id']:
        conn.close()
        return jsonify({'message': 'You are not authorized to manage this event'}), 403

    if permanent:
        # Önce biletleri kontrol et ve iade sürecini başlat (para yanmasın)
        tickets = conn.execute(
            "SELECT * FROM tickets WHERE event_id = ? AND status = 'valid'", (event_id,)
        ).fetchall()
        for ticket in tickets:
            conn.execute(
                "UPDATE tickets SET status = 'refund_pending' WHERE id = ?", (ticket['id'],)
            )
            create_notification(
                conn, ticket['user_id'],
                f"Event '{event['title']}' has been removed from the system. Your ticket (#{ticket['ticket_key']}) has been put into the refund process."
            )

        # Foreign Key kısıtlamalarını geçici olarak kapat (blok3 gibi verili ilanları silebilmek için)
        conn.execute("PRAGMA foreign_keys = OFF")
        
        # Tüm bağlı verileri temizle
        conn.execute("DELETE FROM seats WHERE event_id = ?", (event_id,))
        conn.execute("DELETE FROM wishlist WHERE event_id = ?", (event_id,))
        conn.execute("DELETE FROM promotions WHERE event_id = ?", (event_id,))
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        
        # Foreign Key kısıtlamalarını geri aç
        conn.execute("PRAGMA foreign_keys = ON")
        
        conn.commit()
        conn.close()
        return jsonify({'message': 'Refund notification sent to ticket holders and event deleted from everywhere'}), 200

    # Mevcut iptal mantığı
    reason = request.args.get('reason') or (request.json.get('reason') if request.is_json else 'Cancelled by the organizer')
    selected_ids = request.json.get('selected_ids', []) if request.is_json else []
    cancelled_by = g.user['role'] # 'admin' or 'organizer'
    
    if selected_ids:
        placeholders = ','.join(['?'] * len(selected_ids))
        conn.execute(f"UPDATE events SET status = 'cancelled', rejection_reason = ?, cancelled_by = ? WHERE id IN ({placeholders})", 
                     [reason, cancelled_by] + list(selected_ids))
    else:
        conn.execute("UPDATE events SET status = 'cancelled', rejection_reason = ?, cancelled_by = ? WHERE id = ?", 
                     (reason, cancelled_by, event_id))

    # Organizatöre bildirim gönder (Eğer admin iptal ettiyse)
    if cancelled_by == 'admin' and event['organizer_id']:
        create_notification(conn, event['organizer_id'], 
                            f"Your session(s) in event '{event['title']}' has been cancelled by the admin. Reason: {reason}")

    # Bilet iade süreçlerini başlat
    target_ids = selected_ids if selected_ids else [event_id]
    placeholders = ','.join(['?'] * len(target_ids))
    
    tickets = conn.execute(
        f"SELECT * FROM tickets WHERE event_id IN ({placeholders}) AND status = 'valid'", 
        list(target_ids)
    ).fetchall()
    
    for ticket in tickets:
        conn.execute(
            "UPDATE tickets SET status = 'refund_pending' WHERE id = ?", (ticket['id'],)
        )
        create_notification(
            conn, ticket['user_id'],
            f"Event '{event['title']}' has been cancelled. Your ticket (#{ticket['ticket_key']}) has been put into the refund process."
        )

    conn.commit()
    conn.close()
    return jsonify({'message': 'Event cancelled, tickets put into the refund process'}), 200
