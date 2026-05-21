import sys
import os

# PyInstaller ile paketlendiğinde dosya yollarını doğru ayarla
if getattr(sys, 'frozen', False):
    # PyInstaller ile çalışıyor (exe modunda)
    BASE_DIR = sys._MEIPASS
    os.chdir(BASE_DIR)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, '.env'))  # Load SMTP and other settings from .env file

import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

from flask import Flask, request, session, render_template, redirect, make_response
from flask_cors import CORS
from utils import SECRET_KEY, limiter, cache, send_birthday_emails
import threading
import time
from datetime import datetime
from translations import TRANSLATIONS

from routes.auth import auth_bp
from routes.users import users_bp
from routes.events import events_bp
from routes.tickets import tickets_bp
from routes.wishlist import wishlist_bp
from routes.notifications import notifications_bp
from routes.organizer import organizer_bp
from routes.admin import admin_bp
from routes.upload import upload_bp

app = Flask(__name__, static_folder=None, template_folder=os.path.join(BASE_DIR, 'templates'))
CORS(app)
app.config['SECRET_KEY'] = SECRET_KEY
limiter.init_app(app)
cache.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(events_bp)
app.register_blueprint(tickets_bp)
app.register_blueprint(wishlist_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(organizer_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(upload_bp)

@app.errorhandler(429)
def ratelimit_handler(e):
    # Bekleme Odası (Waiting Room) Mantığı
    # Eğer API isteği ise JSON döndür (frontend bunu anlayıp bekleme odası modalı gösterebilir)
    if request.path.startswith('/api/'):
        return {"error": "ratelimit", "message": "High Traffic. You have been placed in the waiting room. Please try again in a few minutes."}, 429
    # Sayfa isteği ise basit bir HTML
    return "<h2>Waiting Room</h2><p>Due to high demand, you are in a queue. Please wait and refresh the page shortly.</p>", 429

# ─────────────────────────────────────────────
# I18N AND STATIC SERVE
# ─────────────────────────────────────────────

@app.route('/set_language/<lang>')
def set_language(lang):
    next_url = request.args.get('next') or request.referrer or '/'
    if lang in TRANSLATIONS:
        session['lang'] = lang
        # Also set a persistent cookie (survives browser close)
        resp = redirect(next_url)
        resp.set_cookie('lang', lang, max_age=60*60*24*365)  # 1 year
        return resp
    return redirect(next_url)

@app.context_processor
def inject_translations():
    # Priority: session > cookie > default 'tr'
    lang = session.get('lang') or request.cookies.get('lang', 'tr')
    if lang not in TRANSLATIONS:
        lang = 'tr'
    session['lang'] = lang  # ensure session is always set
    def t(key):
        return TRANSLATIONS.get(lang, TRANSLATIONS['tr']).get(key, key)
    return dict(t=t, current_lang=lang)

@app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path.endswith('.html'):
        try:
            return render_template(path)
        except Exception:
            return render_template('index.html')
    else:
        try:
            from flask import send_from_directory
            static_dir = os.path.join(BASE_DIR, 'frontend')
            return send_from_directory(static_dir, path)
        except Exception:
            return render_template('index.html')

def birthday_job():
    """Runs in background and sends emails at exactly 00:00."""
    while True:
        now = datetime.now()
        if now.hour == 0 and now.minute == 0:
            send_birthday_emails()
            time.sleep(65) # Aynı dakika içinde tekrar tetiklenmesini önle
        else:
            time.sleep(30)

if __name__ == '__main__':
    # init_db()  # <-- Turso kurulu olduğu için her başlatmada kapatıyoruz.
    
    # Check to prevent duplicate threads during development reload
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        t = threading.Thread(target=birthday_job, daemon=True)
        t.start()
        print(">>> Birthday Background Service Started (Waiting for 00:00)")
    # On Windows, using use_reloader=False is more stable for custom threading
    app.run(debug=True, host='0.0.0.0', port=5002, use_reloader=False)
