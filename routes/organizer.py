from flask import Blueprint, request, jsonify, g, Response
from database import get_db_connection
from utils import role_required, event_to_dict, COMMISSION_RATE

organizer_bp = Blueprint('organizer', __name__, url_prefix='/api/organizer')

@organizer_bp.route('/events', methods=['GET'])
@role_required('organizer', 'admin')
def organizer_events():
    conn = get_db_connection()
    if g.user['role'] == 'admin':
        events = conn.execute('SELECT * FROM events ORDER BY date ASC').fetchall()
    else:
        events = conn.execute(
            'SELECT * FROM events WHERE organizer_id = ? ORDER BY date ASC',
            (g.user['id'],)
        ).fetchall()
    conn.close()
    
    # Debug log for you to see in terminal
    print(f"--- LOG: Organizator {g.user['id']} icin {len(events)} etkinlik/seans donduruldu. ---")
    
    return jsonify([event_to_dict(e) for e in events]), 200

@organizer_bp.route('/revenue', methods=['GET'])
@role_required('organizer', 'admin')
def organizer_revenue():
    conn = get_db_connection()
    if g.user['role'] == 'admin':
        event_filter = ""
        params = []
    else:
        event_filter = "AND e.organizer_id = ?"
        params = [g.user['id']]

    tickets = conn.execute(f'''
        SELECT t.total_price, t.quantity, t.status, e.title
        FROM tickets t
        JOIN events e ON t.event_id = e.id
        WHERE t.status IN ('valid', 'used') {event_filter}
    ''', params).fetchall()

    total_revenue = sum(t['total_price'] for t in tickets) if tickets else 0
    total_tickets = sum(t['quantity'] for t in tickets) if tickets else 0
    commission = round(total_revenue * COMMISSION_RATE)

    # Toplam iade tazminatları (refund compensation)
    refund_comp_rows = conn.execute(f'''
        SELECT COALESCE(SUM(r.organizer_compensation), 0) as total_org_comp
        FROM refunds r
        JOIN events e ON r.event_id = e.id
        WHERE 1=1 {event_filter}
    ''', params).fetchone()
    total_refund_comp = refund_comp_rows['total_org_comp'] if refund_comp_rows else 0

    # Net Income = (Total Revenue - Commission) + Refund Compensation
    net_revenue = (total_revenue - commission) + total_refund_comp

    # Toplam admin iade komisyonu (sadece admin için)
    total_admin_refund_fee = 0
    if g.user['role'] == 'admin':
        admin_fee_row = conn.execute("SELECT COALESCE(SUM(admin_fee), 0) as total FROM refunds").fetchone()
        total_admin_refund_fee = admin_fee_row['total'] if admin_fee_row else 0

    # Etkinlik bazlı döküm
    events_stats = conn.execute(f'''
        SELECT 
            e.id, 
            e.title, 
            e.date,
            e.capacity, 
            e.price, 
            e.status,
            u.fullname as organizer_name,
            COALESCE(SUM(CASE WHEN t.status IN ('valid', 'used') THEN t.quantity ELSE 0 END), 0) as real_sold_count,
            COALESCE(SUM(CASE WHEN t.status IN ('valid', 'used') THEN t.total_price ELSE 0 END), 0) as real_gross,
            COALESCE(SUM(CASE WHEN t.status = 'refunded' THEN t.total_price * 0.05 ELSE 0 END), 0) as ev_admin_fee_from_tickets
        FROM events e
        LEFT JOIN users u ON e.organizer_id = u.id
        LEFT JOIN tickets t ON e.id = t.event_id
        WHERE e.status = 'active' {event_filter}
        GROUP BY e.id
        ORDER BY e.date ASC
    ''', params).fetchall()

    breakdown = []
    for ev in events_stats:
        gross = ev['real_gross']
        try:
            from datetime import datetime
            dt_obj = datetime.fromisoformat(ev['date'].replace('T', ' '))
            day_str = dt_obj.strftime('%d %b')
            raw_title = ev['title']
            short_title = raw_title[:12] + '...' if len(raw_title) > 15 else raw_title
            display_title = f"{short_title} ({day_str})"
        except:
            display_title = ev['title']

        # Bu etkinliğe ait iade tazminatını çek (Admin fee'yi tickets üzerinden hesapladık)
        ev_refund_row = conn.execute(
            'SELECT COALESCE(SUM(organizer_compensation), 0) as ev_comp '
            'FROM refunds WHERE event_id = ?',
            (ev['id'],)
        ).fetchone()
        ev_refund_comp = ev_refund_row['ev_comp'] if ev_refund_row else 0
        ev_admin_fee = ev['ev_admin_fee_from_tickets']

        breakdown.append({
            'event_id': ev['id'],
            'title': display_title,
            'organizer_name': ev['organizer_name'],
            'sold_count': ev['real_sold_count'],
            'capacity': ev['capacity'],
            'gross_revenue': gross,
            'commission': round(gross * COMMISSION_RATE),
            'net_revenue': round(gross * (1 - COMMISSION_RATE)),
            'refund_comp': ev_refund_comp,
            'admin_fee': ev_admin_fee,
            'status': ev['status']
        })

    organizer_breakdown = []
    if g.user['role'] == 'admin':
        orgs_stats = conn.execute('''
            SELECT 
                u.id as organizer_id,
                u.fullname as organizer_name,
                u.email as organizer_email,
                COALESCE(SUM(t.quantity), 0) as total_tickets,
                COALESCE(SUM(t.total_price), 0) as total_gross
            FROM users u
            JOIN events e ON u.id = e.organizer_id
            LEFT JOIN tickets t ON e.id = t.event_id AND t.status IN ('valid', 'used')
            WHERE u.role = 'organizer'
            GROUP BY u.id
            HAVING total_tickets > 0
            ORDER BY total_gross DESC
        ''').fetchall()

        for org in orgs_stats:
            gross = org['total_gross']
            # Bu organizatöre ait iade tazminatını çek
            org_refund_row = conn.execute(
                'SELECT COALESCE(SUM(r.organizer_compensation), 0) as org_comp, '
                'COALESCE(SUM(r.admin_fee), 0) as adm_fee '
                'FROM refunds r JOIN events e ON r.event_id = e.id '
                'WHERE e.organizer_id = ?',
                (org['organizer_id'],)
            ).fetchone()
            org_refund_comp = org_refund_row['org_comp'] if org_refund_row else 0
            org_admin_fee = org_refund_row['adm_fee'] if org_refund_row else 0
            organizer_breakdown.append({
                'organizer_id': org['organizer_id'],
                'name': org['organizer_name'],
                'email': org['organizer_email'],
                'total_tickets': org['total_tickets'],
                'gross_revenue': gross,
                'commission': round(gross * COMMISSION_RATE),
                'net_revenue': round(gross * (1 - COMMISSION_RATE)),
                'refund_comp': org_refund_comp,
                'admin_refund_fee': org_admin_fee
            })

    conn.close()
    return jsonify({
        'total_revenue': total_revenue,
        'total_tickets': total_tickets,
        'commission': commission,
        'net_revenue': net_revenue,
        'commission_rate': COMMISSION_RATE,
        'total_refund_comp': total_refund_comp,
        'total_admin_refund_fee': total_admin_refund_fee,
        'platform_net_income': commission + total_admin_refund_fee,
        'breakdown': breakdown,
        'organizer_breakdown': organizer_breakdown
    }), 200

@organizer_bp.route('/promotions', methods=['GET'])
@role_required('organizer', 'admin')
def get_promotions():
    conn = get_db_connection()
    if g.user['role'] == 'admin':
        promotions = conn.execute('''
            SELECT p.*, e.title as event_title 
            FROM promotions p 
            JOIN events e ON p.event_id = e.id 
            ORDER BY p.id DESC
        ''').fetchall()
    else:
        promotions = conn.execute('''
            SELECT p.*, e.title as event_title 
            FROM promotions p 
            JOIN events e ON p.event_id = e.id 
            WHERE e.organizer_id = ? 
            ORDER BY p.id DESC
        ''', (g.user['id'],)).fetchall()
    conn.close()
    return jsonify([dict(p) for p in promotions]), 200

@organizer_bp.route('/promotions', methods=['POST'])
@role_required('organizer', 'admin')
def create_promotion():
    data = request.get_json()
    event_id = data.get('event_id')
    code = data.get('code', '').strip().upper()
    discount_type = data.get('discount_type')
    discount_value = data.get('discount_value')
    usage_limit = data.get('usage_limit')

    if not event_id or not code or not discount_type or not discount_value:
        return jsonify({'message': 'Missing data: event_id, code, discount_type, and discount_value are required.'}), 400

    if discount_type not in ('percentage', 'fixed'):
        return jsonify({'message': 'Invalid discount type.'}), 400

    conn = get_db_connection()
    
    # Check if event belongs to organizer
    if g.user['role'] != 'admin':
        event = conn.execute('SELECT organizer_id FROM events WHERE id = ?', (event_id,)).fetchone()
        if not event or event['organizer_id'] != g.user['id']:
            conn.close()
            return jsonify({'message': 'You do not have permission to add a promotion to this event.'}), 403

    try:
        conn.execute('''
            INSERT INTO promotions (event_id, code, discount_type, discount_value, usage_limit)
            VALUES (?, ?, ?, ?, ?)
        ''', (event_id, code, discount_type, int(discount_value), usage_limit if usage_limit else None))
        conn.commit()
    except Exception as e:
        conn.close()
        return jsonify({'message': 'This code might already exist for this event.'}), 400

    conn.close()
    return jsonify({'message': 'Promotion created successfully.'}), 201

@organizer_bp.route('/promotions/<int:promo_id>', methods=['DELETE'])
@role_required('organizer', 'admin')
def delete_promotion(promo_id):
    conn = get_db_connection()
    promo = conn.execute('''
        SELECT p.id, e.organizer_id 
        FROM promotions p 
        JOIN events e ON p.event_id = e.id 
        WHERE p.id = ?
    ''', (promo_id,)).fetchone()

    if not promo:
        conn.close()
        return jsonify({'message': 'Promotion not found.'}), 404

    if g.user['role'] != 'admin' and promo['organizer_id'] != g.user['id']:
        conn.close()
        return jsonify({'message': 'You do not have permission to delete this promotion.'}), 403

    conn.execute('DELETE FROM promotions WHERE id = ?', (promo_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Promotion deleted successfully.'}), 200


# ─────────────────────────────────────────────────────────────────────────────
# ATTENDEE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _query_attendees(event_id):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT
            t.ticket_key, t.owner_name, t.owner_surname,
            u.email, u.fullname,
            t.status, t.total_price, t.quantity, t.purchase_date,
            s.zone, s.row_label, s.col_label
        FROM tickets t
        JOIN events  e ON t.event_id = e.id
        JOIN users   u ON t.user_id  = u.id
        LEFT JOIN seats s ON t.seat_id = s.id
        WHERE t.event_id = ?
        ORDER BY t.purchase_date
    ''', (event_id,)).fetchall()
    conn.close()
    return rows


def _check_event_access(event_id):
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    conn.close()
    if not event:
        return None, 'not_found'
    if g.user['role'] != 'admin' and event['organizer_id'] != g.user['id']:
        return None, 'forbidden'
    return event, None


# ── GET /api/organizer/events/<event_id>/attendees  (JSON) ────────────────────
@organizer_bp.route('/events/<event_id>/attendees', methods=['GET'])
@role_required('organizer', 'admin')
def event_attendees(event_id):
    event, err = _check_event_access(event_id)
    if not event:
        return jsonify({'message': 'Event not found or unauthorized.'}), (404 if err == 'not_found' else 403)

    rows = _query_attendees(event_id)
    attendees = []
    for r in rows:
        seat  = f"{r['zone']} {r['row_label']}-{r['col_label']}" if r['zone'] else 'General Admission'
        name  = r['owner_name']   or (r['fullname'] or '').split()[0] or '-'
        surna = r['owner_surname'] or ' '.join((r['fullname'] or '').split()[1:]) or ''
        attendees.append({
            'ticket_key':   r['ticket_key'],
            'name':         name,
            'surname':      surna,
            'full_name':    f"{name} {surna}".strip(),
            'email':        r['email'],
            'seat':         seat,
            'status':       r['status'],
            'price':        r['total_price'],
            'quantity':     r['quantity'],
            'purchased_at': (r['purchase_date'] or '')[:16],
        })
    return jsonify({
        'event_title': event['title'],
        'event_date':  event['date'],
        'total':       len(attendees),
        'attendees':   attendees
    }), 200


# ── GET /api/organizer/events/<event_id>/attendees/export  (CSV) ──────────────
@organizer_bp.route('/events/<event_id>/attendees/export', methods=['GET'])
@role_required('organizer', 'admin')
def export_attendees(event_id):
    import io, csv

    event, err = _check_event_access(event_id)
    if not event:
        return jsonify({'message': 'Event not found or unauthorized.'}), (404 if err == 'not_found' else 403)

    rows = _query_attendees(event_id)
    buf  = io.StringIO()
    w    = csv.writer(buf)
    w.writerow(['Ticket Code', 'First Name', 'Last Name', 'Email',
                'Seat / Type', 'Status', 'Price (TL)', 'Quantity', 'Purchase Date'])

    status_map = {'valid': 'Valid', 'used': 'Used',
                  'refund_pending': 'Refund Pending', 'cancelled': 'Cancelled'}

    for r in rows:
        seat = f"{r['zone']} {r['row_label']}-{r['col_label']}" if r['zone'] else 'General Admission'
        w.writerow([
            r['ticket_key'],
            r['owner_name']    or (r['fullname'] or '-').split()[0],
            r['owner_surname'] or ' '.join((r['fullname'] or '').split()[1:]) or '-',
            r['email'],
            seat,
            status_map.get(r['status'], r['status']),
            r['total_price'],
            r['quantity'],
            (r['created_at'] or r['purchase_date'] or '')[:16],
        ])

    # UTF-8 BOM — Excel opens without encoding prompt
    csv_bytes = b'\xef\xbb\xbf' + buf.getvalue().encode('utf-8')
    safe  = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in (event['title'] or 'Event'))
    fname = f"Attendees_{safe}.csv"

    return Response(
        csv_bytes,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename="{fname}"',
            'Content-Type': 'text/csv; charset=utf-8',
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# SALES HISTORY
# ─────────────────────────────────────────────────────────────────────────────
_SALES_SELECT = '''
    SELECT
        t.ticket_key, t.owner_name, t.owner_surname, t.status, t.total_price,
        t.quantity, t.purchase_date, t.promo_code, t.original_price,
        u.email, u.fullname,
        e.id AS event_id, e.title AS event_title, e.date AS event_date, e.location AS event_location,
        s.zone, s.row_label, s.col_label, s.price AS seat_price, e.price AS event_price,
        org.fullname AS organizer_name
    FROM tickets t
    JOIN events e ON t.event_id = e.id
    JOIN users u ON t.user_id = u.id
    LEFT JOIN users org ON e.organizer_id = org.id
    LEFT JOIN seats s ON t.seat_id = s.id
'''


def _sales_filters():
    where = ['1=1']
    params = []

    if g.user['role'] != 'admin':
        where.append('e.organizer_id = ?')
        params.append(g.user['id'])
    else:
        org_id = request.args.get('organizer_id', '').strip()
        if org_id.isdigit():
            where.append('e.organizer_id = ?')
            params.append(int(org_id))

    event_id = request.args.get('event_id', '').strip()
    if event_id:
        where.append('t.event_id = ?')
        params.append(event_id)

    status = request.args.get('status', '').strip()
    if status and status != 'all':
        where.append('t.status = ?')
        params.append(status)

    search = request.args.get('search', '').strip().lower()
    if search:
        where.append('''(
            LOWER(t.ticket_key) LIKE ? OR LOWER(u.email) LIKE ?
            OR LOWER(COALESCE(t.owner_name, '')) LIKE ? OR LOWER(COALESCE(t.owner_surname, '')) LIKE ?
            OR LOWER(u.fullname) LIKE ?
        )''')
        q = f'%{search}%'
        params.extend([q, q, q, q, q])

    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    if date_from:
        where.append('DATE(t.purchase_date) >= DATE(?)')
        params.append(date_from)
    if date_to:
        where.append('DATE(t.purchase_date) <= DATE(?)')
        params.append(date_to)

    sort_by = request.args.get('sort_by', 'purchase_date')
    sort_order = request.args.get('sort_order', 'desc')
    sort_map = {
        'purchase_date': 't.purchase_date',
        'price': 't.total_price',
        'event_date': 'e.date',
        'event_title': 'e.title',
    }
    order_col = sort_map.get(sort_by, 't.purchase_date')
    order_dir = 'ASC' if sort_order == 'asc' else 'DESC'
    order_sql = f'{order_col} {order_dir}, t.id DESC'

    return ' AND '.join(where), params, order_sql


def _format_sales_row(r):
    seat = f"{r['zone']} {r['row_label']}-{r['col_label']}" if r['zone'] else 'General Admission'
    name = r['owner_name'] or (r['fullname'] or '').split()[0] or '-'
    surna = r['owner_surname'] or ' '.join((r['fullname'] or '').split()[1:]) or ''
    list_price = r['original_price'] or r['seat_price'] or r['event_price'] or r['total_price']
    list_price = int(list_price) if list_price else int(r['total_price'] or 0)
    paid = int(r['total_price'] or 0)
    return {
        'ticket_key': r['ticket_key'],
        'full_name': f"{name} {surna}".strip(),
        'email': r['email'],
        'event_id': r['event_id'],
        'event_title': r['event_title'],
        'event_date': (r['event_date'] or '')[:16],
        'event_location': r['event_location'],
        'seat': seat,
        'status': r['status'],
        'price': paid,
        'original_price': list_price,
        'has_discount': list_price > paid,
        'promo_code': r['promo_code'] or None,
        'quantity': r['quantity'],
        'purchased_at': (r['purchase_date'] or '')[:16],
        'organizer_name': r['organizer_name'],
    }


@organizer_bp.route('/sales-history', methods=['GET'])
@role_required('organizer', 'admin')
def sales_history():
    try:
        where_sql, params, order_sql = _sales_filters()
        page = max(1, int(request.args.get('page', 1) or 1))
        limit = min(200, max(1, int(request.args.get('limit', 50) or 50)))
        offset = (page - 1) * limit

        conn = get_db_connection()
        base = f'{_SALES_SELECT} WHERE {where_sql}'

        total = conn.execute(f'SELECT COUNT(*) AS c FROM ({base})', params).fetchone()['c']

        stats = conn.execute(f'''
            SELECT
                COUNT(*) AS total_count,
                COALESCE(SUM(t.total_price), 0) AS total_amount,
                SUM(CASE WHEN t.status = 'valid' THEN 1 ELSE 0 END) AS valid_count,
                SUM(CASE WHEN t.status = 'used' THEN 1 ELSE 0 END) AS used_count,
                SUM(CASE WHEN t.status IN ('refunded', 'refund_pending') THEN 1 ELSE 0 END) AS refunded_count,
                SUM(CASE WHEN t.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_count
            FROM tickets t
            JOIN events e ON t.event_id = e.id
            JOIN users u ON t.user_id = u.id
            WHERE {where_sql}
        ''', params).fetchone()

        rows = conn.execute(f'{base} ORDER BY {order_sql} LIMIT ? OFFSET ?', params + [limit, offset]).fetchall()
        conn.close()

        return jsonify({
            'items': [_format_sales_row(r) for r in rows],
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total,
                'pages': max(1, (total + limit - 1) // limit),
            },
            'summary': {
                'total_count': stats['total_count'] or 0,
                'total_amount': stats['total_amount'] or 0,
                'valid_count': stats['valid_count'] or 0,
                'used_count': stats['used_count'] or 0,
                'refunded_count': stats['refunded_count'] or 0,
                'cancelled_count': stats['cancelled_count'] or 0,
            },
        }), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@organizer_bp.route('/sales-history/export', methods=['GET'])
@role_required('organizer', 'admin')
def export_sales_history():
    import io, csv
    from translations import TRANSLATIONS
    from flask import session

    where_sql, params, order_sql = _sales_filters()
    conn = get_db_connection()
    rows = conn.execute(
        f'{_SALES_SELECT} WHERE {where_sql} ORDER BY {order_sql}',
        params
    ).fetchall()
    conn.close()

    lang = session.get('lang', 'tr')
    tr = TRANSLATIONS.get(lang, TRANSLATIONS['tr'])
    status_map = {
        'valid': tr.get('valid_status', 'Valid'),
        'used': tr.get('used_status', 'Used'),
        'refund_pending': tr.get('refund_pending_status', 'Refund Pending'),
        'refunded': tr.get('refunded_status', 'Refunded'),
        'cancelled': tr.get('cancelled_status', 'Cancelled'),
    }
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=';')
    w.writerow([
        tr.get('ticket_key_col', 'Ticket'),
        tr.get('buyer_col', 'Buyer'),
        tr.get('email_col', 'Email'),
        tr.get('event_col', 'Event'),
        tr.get('event_date_col', 'Event Date'),
        tr.get('location_col', 'Location'),
        tr.get('seat_col', 'Seat'),
        tr.get('status', 'Status'),
        tr.get('original_price', 'Original'),
        tr.get('paid_price', 'Paid'),
        tr.get('promo_code', 'Promo'),
        tr.get('purchase_date_col', 'Purchase'),
        tr.get('organizer', 'Organizer'),
    ])
    ga = tr.get('general_admission', 'General Admission')
    for r in rows:
        item = _format_sales_row(r)
        seat = item['seat'] if item['seat'] != 'General Admission' else ga
        w.writerow([
            item['ticket_key'], item['full_name'], item['email'], item['event_title'],
            item['event_date'], item['event_location'], seat,
            status_map.get(item['status'], item['status']),
            item['original_price'], item['price'], item['promo_code'] or '',
            item['purchased_at'], item['organizer_name'] or '',
        ])

    csv_bytes = b'\xef\xbb\xbf' + buf.getvalue().encode('utf-8')
    return Response(
        csv_bytes,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename="Sales_History.csv"',
            'Content-Type': 'text/csv; charset=utf-8',
        }
    )
