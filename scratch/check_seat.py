from database import get_db_connection
conn = get_db_connection()
t = conn.execute("SELECT t.ticket_key, t.seat_id, s.zone, s.row_label, s.col_label FROM tickets t LEFT JOIN seats s ON t.seat_id = s.id WHERE t.ticket_key='2975D4E14A74'").fetchone()
print(dict(t) if t else 'Not found')
conn.close()
