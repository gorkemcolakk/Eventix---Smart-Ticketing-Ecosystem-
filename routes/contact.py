import os
import re
from flask import Blueprint, request, jsonify
from utils import send_email, sanitize_html, limiter, build_contact_form_email_html

contact_bp = Blueprint('contact', __name__, url_prefix='/api/contact')

CONTACT_TO = os.getenv('CONTACT_TO') or os.getenv('SMTP_USERNAME') or 'ticketeventix@gmail.com'
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


@contact_bp.route('', methods=['POST'])
@limiter.limit('5 per hour')
def submit_contact():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    subject = (data.get('subject') or '').strip()
    message = (data.get('message') or '').strip()

    if not name or not email or not subject or not message:
        return jsonify({'message': 'Missing required fields'}), 400
    if len(name) > 120 or len(email) > 254 or len(subject) > 200 or len(message) > 5000:
        return jsonify({'message': 'Input too long'}), 400
    if not EMAIL_RE.match(email):
        return jsonify({'message': 'Invalid email address'}), 400

    safe_name = sanitize_html(name)
    safe_subject = sanitize_html(subject)
    safe_message = sanitize_html(message)

    mail_subject = f'[Eventix İletişim] {safe_subject}'
    plain = (
        f'Yeni iletişim formu mesajı\n\n'
        f'Gönderen: {safe_name}\n'
        f'E-posta: {email}\n'
        f'Konu: {safe_subject}\n\n'
        f'Mesaj:\n{safe_message}\n'
    )
    html = build_contact_form_email_html(safe_name, email, safe_subject, safe_message)

    sent = send_email(
        CONTACT_TO,
        mail_subject,
        plain,
        html_message=html,
        reply_to=email,
    )
    if not sent:
        return jsonify({'message': 'Email could not be sent. Please try again later.'}), 503

    return jsonify({'message': 'Message sent successfully'}), 200
