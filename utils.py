import qrcode
import io
import base64
import json
import jwt
import hmac
import hashlib
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from flask import request, jsonify, g
import uuid
from functools import wraps
from database import get_db_connection
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import html
from translations import TRANSLATIONS

SECRET_KEY = 'eventix-super-secret-key-2026'


def get_request_lang(data=None):
    lang = (data or {}).get('lang') if isinstance(data, dict) else None
    if not lang and request:
        lang = request.cookies.get('lang')
    if lang not in TRANSLATIONS:
        lang = 'tr'
    return lang


def _t_lang(lang, key, **kwargs):
    text = TRANSLATIONS.get(lang, TRANSLATIONS['tr']).get(key) or TRANSLATIONS['tr'].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text
COMMISSION_RATE = 0.10

limiter = Limiter(key_func=get_remote_address)
cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 30})

def sanitize_html(text):
    if text is None:
        return text
    return html.escape(str(text))

def sign_ticket_data(data: str) -> str:
    """Creates an HMAC-SHA256 signature for the ticket data."""
    signature = hmac.new(SECRET_KEY.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{data}-{signature[:16]}"

def verify_ticket_signature(signed_data: str) -> bool:
    """Verifies the HMAC signature of the ticket data."""
    parts = signed_data.rsplit('-', 1)
    if len(parts) != 2:
        return False
    data, signature = parts
    expected_signature = hmac.new(SECRET_KEY.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(signature, expected_signature)

def make_qr_base64(data: str) -> str:
    """Generate a QR code image and return it as a base64 PNG data URL."""
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{b64}"

def make_qr_bytes(data: str) -> bytes:
    """Generate a QR code image and return raw PNG bytes (for email CID embedding)."""
    qr = qrcode.QRCode(version=1, box_size=8, border=3)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def event_to_dict(e):
    evt = dict(e)
    evt['featured'] = bool(evt['featured'])
    evt['lineup'] = json.loads(evt['lineup_json']) if evt.get('lineup_json') else []
    evt.pop('lineup_json', None)
    return evt

def create_notification(conn, user_id: int, message: str):
    conn.execute(
        'INSERT INTO notifications (user_id, message) VALUES (?, ?)',
        (user_id, message)
    )

def send_email(to_email: str, subject: str, message: str, html_message: str = None, images: list = None, reply_to: str = None):
    """
    Gerçek SMTP kullanarak e-posta gönderir.
    images: [{'cid': 'unique_id', 'data': bytes_of_png}, ...] — CID ile gömülü resimler.
    Çevresel değişkenlerde SMTP ayarları yoksa mock (simülasyon) email atar.
    Returns True if sent via SMTP, False if mock/failed.
    """
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT', 587)
    smtp_username = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    from_name = os.environ.get('SMTP_FROM_NAME', 'Eventix')

    if smtp_server and smtp_username and smtp_password:
        try:
            # Eğer resim varsa related/mixed yapısı kur, yoksa alternative yeterli
            if images:
                outer = MIMEMultipart('mixed')
                outer['Subject'] = subject
                outer['From'] = f"{from_name} <{smtp_username}>"
                outer['To'] = to_email
                outer['Reply-To'] = reply_to or smtp_username

                alt = MIMEMultipart('alternative')
                alt.attach(MIMEText(message, 'plain'))
                if html_message:
                    related = MIMEMultipart('related')
                    related.attach(MIMEText(html_message, 'html'))
                    for img in images:
                        mime_img = MIMEImage(img['data'], _subtype='png')
                        mime_img.add_header('Content-ID', f"<{img['cid']}>")  
                        mime_img.add_header('Content-Disposition', 'inline', filename=f"{img['cid']}.png")
                        related.attach(mime_img)
                    alt.attach(related)
                outer.attach(alt)
            else:
                outer = MIMEMultipart('alternative')
                outer['Subject'] = subject
                outer['From'] = f"{from_name} <{smtp_username}>"
                outer['To'] = to_email
                outer['Reply-To'] = reply_to or smtp_username
                outer.attach(MIMEText(message, 'plain'))
                if html_message:
                    outer.attach(MIMEText(html_message, 'html'))

            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(outer)
            server.quit()
            print(f"[REAL] EMAIL SENT TO: {to_email}")
            return True
        except Exception as e:
            print(f"[ERROR] SMTP Email Sending Error: {e}")
            print("Warning: Continuing with Simulation (Mock) email...")

    # Fallback to mock
    send_mock_email(to_email, subject, message)
    return False

def build_contact_form_email_html(name: str, email: str, subject: str, message: str) -> str:
    """Styled HTML template for contact form notifications (admin inbox)."""
    from datetime import datetime
    sent_at = datetime.now().strftime('%d.%m.%Y %H:%M')
    message_html = str(message).replace('\n', '<br>')
    return f"""
    <html>
    <body style="margin:0;padding:0;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background-color:#09090f;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:linear-gradient(180deg,#09090f 0%,#14141f 100%);padding:36px 16px;">
        <tr>
          <td align="center">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#111118;border-radius:20px;overflow:hidden;border:1px solid rgba(245,158,11,0.25);box-shadow:0 20px 50px rgba(0,0,0,0.45);">
              <tr>
                <td style="padding:28px 32px 22px;background:linear-gradient(135deg,#7c3aed 0%,#ec4899 55%,#f59e0b 100%);text-align:center;">
                  <p style="margin:0 0 6px;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;color:rgba(255,255,255,0.85);font-weight:600;">EVENTIX</p>
                  <h1 style="margin:0;font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-0.02em;">Yeni İletişim Mesajı</h1>
                  <p style="margin:10px 0 0;font-size:13px;color:rgba(255,255,255,0.9);">Web sitesi iletişim formundan geldi</p>
                </td>
              </tr>
              <tr>
                <td style="padding:28px 32px 8px;">
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:rgba(245,158,11,0.06);border:1px solid rgba(245,158,11,0.2);border-radius:14px;">
                    <tr>
                      <td style="padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.06);">
                        <span style="display:block;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#f59e0b;font-weight:700;margin-bottom:4px;">Gönderen</span>
                        <span style="font-size:15px;color:#f1f0ef;font-weight:600;">{name}</span>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.06);">
                        <span style="display:block;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#f59e0b;font-weight:700;margin-bottom:4px;">E-posta</span>
                        <a href="mailto:{email}" style="font-size:15px;color:#a78bfa;text-decoration:none;font-weight:500;">{email}</a>
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:16px 20px;">
                        <span style="display:block;font-size:10px;text-transform:uppercase;letter-spacing:0.08em;color:#f59e0b;font-weight:700;margin-bottom:4px;">Konu</span>
                        <span style="font-size:15px;color:#f1f0ef;font-weight:600;">{subject}</span>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
              <tr>
                <td style="padding:12px 32px 24px;">
                  <p style="margin:0 0 10px;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;color:#9ca3af;font-weight:600;">Mesaj</p>
                  <div style="background:#0d0d14;border-left:4px solid #f59e0b;border-radius:0 12px 12px 0;padding:18px 20px;font-size:15px;line-height:1.65;color:#d1d5db;">
                    {message_html}
                  </div>
                </td>
              </tr>
              <tr>
                <td style="padding:0 32px 28px;text-align:center;">
                  <a href="mailto:{email}?subject=Re:%20{subject}" style="display:inline-block;padding:14px 28px;background:linear-gradient(135deg,#f59e0b,#d97706);color:#09090f;font-weight:700;font-size:14px;text-decoration:none;border-radius:30px;box-shadow:0 6px 20px rgba(245,158,11,0.35);">
                    Yanıtla →
                  </a>
                </td>
              </tr>
              <tr>
                <td style="padding:20px 32px 26px;border-top:1px solid rgba(255,255,255,0.06);text-align:center;background:rgba(0,0,0,0.2);">
                  <p style="margin:0 0 6px;font-size:12px;color:#6b7280;">Gönderim zamanı: {sent_at}</p>
                  <p style="margin:0;font-size:11px;color:#4b5563;">Eventix Biletleme Platformu © 2026</p>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


def send_mock_email(to_email: str, subject: str, message: str):
    """
    Simulates sending an email by printing formatted output to the console.
    """
    print(f"\n{'='*50}")
    print(f"[MOCK] EMAIL SENT TO: {to_email}")
    print(f"SUBJECT: {subject}")
    print(f"--------------------------------------------------")
    print(f"{message}")
    print(f"{'='*50}\n")

def send_birthday_emails():
    """
    Her gün çağrılıp, doğum günü bugün olan kullanıcılara HTML tasarımlı şık kutlama mailleri atar.
    Veritabanındaki format 'YYYY-MM-DD' olduğu için son 5 karakter (MM-DD) alınıp bugünün tarihi ile eşlenir.
    """
    from database import get_db_connection
    from datetime import datetime
    import os

    today_mm_dd = datetime.now().strftime("%m-%d")
    
    conn = get_db_connection()
    c = conn.cursor()
    # Tum kayitlari alip python ile MM-DD filter yapmak cloud sqlite (Turso vs) icin en guvenlisidir.
    users = c.execute("SELECT fullname, email, birthdate FROM users WHERE birthdate IS NOT NULL AND birthdate != ''").fetchall()
    conn.close()

    base_url = os.environ.get('FRONTEND_URL', 'http://localhost:5000').rstrip('/')

    count = 0
    for u in users:
        bdate = u['birthdate'] # format expected: YYYY-MM-DD
        if len(bdate) >= 10 and bdate[5:10] == today_mm_dd:
            name = u['fullname']
            email = u['email']

            subject = "🎂 Happy Birthday! - EVENTIX Special Surprise"
            plain_body = f"Happy birthday {name}! At Eventix, we wish you a wonderful year. To make your day special, we have a surprise for you: you've earned a 15% discount with the code BDAY26."
            html_body = f"""
            <html>
            <body style="font-family:'Segoe UI', sans-serif; background-color:#0f0f1a; padding:30px; color:#e2e8f0; text-align:center;">
              <div style="max-width:550px; margin:0 auto; background:linear-gradient(to bottom, #1e1e2e, #161625); border-radius:20px; padding:40px 30px; box-shadow:0 15px 35px rgba(0,0,0,0.6); border:1px solid #2d2d4e;">
                <div style="font-size:60px; margin-bottom:10px;">🎉🎂</div>
                <h1 style="color:#a78bfa; margin:0; font-size:32px; letter-spacing:1px;">Happy Birthday!</h1>
                <h2 style="color:#ffffff; margin-top:10px; font-weight:400;">Dear {name},</h2>
                
                <p style="font-size:16px; line-height:1.6; color:#94a3b8; margin:25px 0;">
                  As the Eventix family, we wish your new age brings you health, happiness, and many more unforgettable event-filled memories!
                </p>
                
                <div style="background:rgba(236,72,153,0.1); border:1px dashed #ec4899; padding:20px; border-radius:12px; margin:30px 0;">
                  <span style="display:block; font-size:12px; color:#ec4899; font-weight:700; text-transform:uppercase; margin-bottom:8px;">🎁 Our Special Surprise Gift for You</span>
                  <div style="font-family:monospace; font-size:24px; color:#ffffff; font-weight:bold; letter-spacing:3px;">BDAY26</div>
                  <span style="display:block; font-size:13px; color:#94a3b8; margin-top:8px;">A <strong>15% Discount</strong> coupon valid instantly on all event tickets!</span>
                </div>
                
                <a href="{base_url}/index.html" style="display:inline-block; padding:15px 32px; background:linear-gradient(135deg, #8b5cf6, #ec4899); color:#ffffff; font-weight:bold; text-decoration:none; border-radius:30px; font-size:15px; box-shadow:0 4px 15px rgba(236,72,153,0.4);">
                  Treat Yourself Today ✨
                </a>
                
                <div style="margin-top:40px; border-top:1px solid #2d2d4e; padding-top:20px;">
                  <p style="color:#475569; font-size:12px; margin:0;">Wishing you a very special day...<br>Eventix Ticketing Platform © 2026</p>
                </div>
              </div>
            </body>
            </html>
            """
            try:
                send_email(to_email=email, subject=subject, message=plain_body, html_message=html_body)
                count += 1
            except Exception as e:
                pass

    if count > 0:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {count} birthday emails successfully sent!")

def send_ticket_confirmation_email(to_email, fullname, event, generated_tickets, total_price, seat_labels_str, lang='tr'):
    """Send ticket confirmation email in the buyer's selected language."""
    from datetime import datetime

    def format_event_date(raw_date):
        months_tr = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
        months_de = ['', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']
        months_en = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        try:
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(str(raw_date), fmt)
                    months = months_tr if lang == 'tr' else (months_de if lang == 'de' else months_en)
                    if dt.hour or dt.minute:
                        return f"{dt.day} {months[dt.month]} {dt.year}, {dt.strftime('%H:%M')}"
                    return f"{dt.day} {months[dt.month]} {dt.year}"
                except ValueError:
                    continue
            return str(raw_date)
        except Exception:
            return str(raw_date)

    event_date_formatted = format_event_date(event['date'])
    event_title = event['title'] if isinstance(event, dict) else event['title']

    plain_body = f"{_t_lang(lang, 'email_ticket_greeting', name=fullname)}\n\n{_t_lang(lang, 'email_ticket_plain_intro', event=event_title)}\n\n"
    email_images = []
    tickets_html_parts = ""

    for gt in generated_tickets:
        plain_body += f"🎟️ {gt['name']} {gt['surname']} | #{gt['ticket_key']}\n"
        qr_cid = f"qr_{gt['ticket_key']}"
        if 'qr_bytes' in gt:
            email_images.append({'cid': qr_cid, 'data': gt['qr_bytes']})
        else:
            qr_data_val = gt.get('qr_data') or sign_ticket_data(f"EVENTIX-{gt['ticket_key']}-{event['id']}")
            email_images.append({'cid': qr_cid, 'data': make_qr_bytes(qr_data_val)})

        tickets_html_parts += f"""
        <div style="border:1px dashed #444; padding:20px; margin-bottom:20px; text-align:center; border-radius:12px; background:#1e1e2e; color:#ffffff;">
          <p style="margin:0 0 10px; font-weight:bold; font-size:1.1em; color:#a78bfa;">{gt['name']} {gt['surname']}</p>
          <img src="cid:{qr_cid}" alt="QR" style="width:180px; height:180px; display:block; margin:10px auto; border-radius:8px; border:4px solid #ffffff;" />
          <p style="margin:10px 0 0; font-family:monospace; font-size:1.2em; color:#c4b5fd; letter-spacing:2px; font-weight:bold;">#{gt['ticket_key']}</p>
        </div>"""

    final_html = f"""
    <html>
    <body style="font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color:#0f0f1a; padding:20px; color:#e2e8f0;">
      <div style="max-width:600px; margin:0 auto; background:#161625; border-radius:16px; padding:30px; box-shadow:0 10px 30px rgba(0,0,0,0.5); border:1px solid #2d2d4e;">
        <div style="text-align:center; margin-bottom:25px;">
           <h1 style="color:#a78bfa; margin:0; font-size:28px;">🎟️ {_t_lang(lang, 'email_ticket_heading')}</h1>
           <p style="color:#94a3b8; font-size:14px; margin-top:5px;">{_t_lang(lang, 'email_ticket_tagline')}</p>
        </div>
        <p style="font-size:16px;">{_t_lang(lang, 'email_ticket_greeting', name=fullname)}</p>
        <p style="font-size:16px; line-height:1.6;">{_t_lang(lang, 'email_ticket_intro', event=event_title)}</p>
        <div style="background:rgba(167,139,250,0.05); border-radius:12px; padding:20px; margin:25px 0; border:1px solid rgba(167,139,250,0.2);">
          <p style="margin:0 0 10px; font-size:14px;"><strong style="color:#a78bfa;">📅 {_t_lang(lang, 'date_and_time')}:</strong> {event_date_formatted}</p>
          <p style="margin:0 0 10px; font-size:14px;"><strong style="color:#a78bfa;">📍 {_t_lang(lang, 'location')}:</strong> {event['location']}</p>
          <p style="margin:0 0 10px; font-size:14px;"><strong style="color:#a78bfa;">🪑 {_t_lang(lang, 'email_ticket_seats_label')}:</strong> {seat_labels_str}</p>
          <p style="margin:0; font-size:18px; font-weight:bold;"><strong style="color:#2dd4bf;">💳 {_t_lang(lang, 'total')}:</strong> {total_price} ₺</p>
        </div>
        <h3 style="color:#ffffff; border-bottom:1px solid #2d2d4e; padding-bottom:10px; margin-bottom:20px;">{_t_lang(lang, 'email_ticket_section')}</h3>
        {tickets_html_parts}
        <div style="text-align:center; margin-top:30px; padding-top:20px; border-top:1px solid #2d2d4e;">
          <p style="color:#94a3b8; font-size:13px;">{_t_lang(lang, 'email_ticket_footer')}</p>
          <p style="color:#64748b; font-size:11px; margin-top:20px;">{_t_lang(lang, 'pdf_footer')}</p>
        </div>
      </div>
    </body>
    </html>"""

    send_email(
        to_email,
        _t_lang(lang, 'email_ticket_subject', event=event_title),
        plain_body,
        final_html,
        images=email_images
    )

def decode_token(token):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (data['id'],)).fetchone()
        conn.close()
        return dict(user) if user else None
    except:
        return None

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split()
            if len(parts) == 2 and parts[0] == 'Bearer':
                token = parts[1]
        if not token:
            return jsonify({'message': 'Token missing!'}), 401
        
        user_data = decode_token(token)
        if not user_data:
            return jsonify({'message': 'Token is invalid or expired!'}), 401
        
        g.user = user_data
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            if g.user.get('role') not in roles:
                return jsonify({'message': 'Insufficient permission!'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
