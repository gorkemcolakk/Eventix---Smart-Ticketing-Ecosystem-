/* ─── EVENTİX auth.js — unified auth + theme ─── */
const API_BASE = '';

const getToken   = () => localStorage.getItem('token');
const getUser    = () => JSON.parse(localStorage.getItem('user') || 'null');
const authHeaders = () => ({
    'Content-Type':  'application/json',
    'Authorization': `Bearer ${getToken()}`
});

// Sepet ve Session için kullanıcıya özel anahtarlar üretir
window.getCartKey = () => {
    const user = getUser();
    return user ? `eventix_cart_${user.id}` : 'eventix_cart_guest';
};
window.getSessionKey = () => {
    const user = getUser();
    return user ? 'eventix_session_' + user.id : 'eventix_session_guest';
};

window.getOrCreateSessionId = () => {
    const key = window.getSessionKey();
    let sid = localStorage.getItem(key);
    if (!sid) {
        sid = 'sess_' + Math.random().toString(36).slice(2, 10) + '_' + Date.now();
        localStorage.setItem(key, sid);
    }
    return sid;
};

// ── ROUTE HELPERS ────────────────────────────────────────────
window.goToLogin = () => { window.location.href = 'login.html'; };
window.goToDashboard = () => {
    const u = getUser();
    if (!u) return goToLogin();
    window.location.href =
        u.role === 'admin'      ? 'admin.html'     :
        u.role === 'organizer'  ? 'organizer.html' : 'dashboard.html';
};
window.logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    // Sepeti SİLMİYORUZ, sadece oturum bilgisini kaldırıyoruz
    window.location.href = 'index.html';
};

// GLOBAL CART HELPERS
window.getCart = () => {
    try { return JSON.parse(localStorage.getItem(window.getCartKey())) || []; }
    catch { return []; }
};

window.saveCart = (cart) => {
    localStorage.setItem(window.getCartKey(), JSON.stringify(cart));
    if (typeof window.updateGlobalCartCount === 'function') window.updateGlobalCartCount();
    if (typeof window.renderCart === 'function') window.renderCart();
};

window.updateGlobalCartCount = () => {
    const cart = window.getCart();
    const count = cart.reduce((sum, item) => sum + (item.qty || 1), 0);
    const badge = document.getElementById('globalCartCount');
    if (badge) {
        badge.style.display = count > 0 ? 'inline-flex' : 'none';
        badge.textContent = count;
    }
};

window.addEventListener('storage', (e) => {
    if (e.key === window.getCartKey()) window.updateGlobalCartCount();
});

// ── THEME ─────────────────────────────────────────────────────
function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('eventix-theme', t);
    document.body.classList.toggle('light-mode', t === 'light');
    document.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: t } }));
}
window.toggleTheme = () => {
    const cur = document.documentElement.getAttribute('data-theme') || 'dark';
    applyTheme(cur === 'light' ? 'dark' : 'light');
};
// Apply immediately (no flash)
applyTheme(localStorage.getItem('eventix-theme') || 'dark');

// ── NAV RENDER ───────────────────────────────────────────────
const THEME_BTN = `
  <button class="theme-toggle" onclick="toggleTheme()" title="Theme" aria-label="Toggle theme">
    <svg class="icon-moon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
    <svg class="icon-sun"  width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
  </button>`;

const getLangFromCookie = () => {
    const match = document.cookie.match(new RegExp('(^| )lang=([^;]+)'));
    return match ? match[2].toLowerCase() : 'tr';
};

const authI18n = {
    tr: {
        cart: 'Sepet',
        my_tickets: '🎟 Biletlerim',
        my_wishlist: '❤ Favorilerim',
        notifications: '🔔 Bildirimler',
        pending_approval: '⏳ Onay Bekleyenler',
        users: '👥 Kullanıcılar',
        all_events: '📋 Tüm Etkinlikler',
        platform_revenue: '💰 Platform Geliri',
        my_events: '🎪 Etkinliklerim',
        create_event: '➕ Etkinlik Oluştur',
        revenue_report: '💰 Gelir Raporu',
        sales_history: '📜 Satış Geçmişi',
        promotions: '🎫 Promosyonlar',
        qr_validation: '🔍 QR Doğrulama',
        logout: '🚪 Çıkış Yap',
        login: 'Giriş Yap',
        register: 'Kayıt Ol',
        please_login_wishlist: 'Favorilere eklemek için lütfen giriş yapın.',
        logging_in: 'Giriş yapılıyor...',
        login_failed: 'Giriş başarısız',
        server_error: 'Sunucuya bağlanılamadı',
        password_length: 'Şifre en az 6 karakter olmalıdır',
        register_success: 'Kayıt başarılı! Yönlendiriliyor...',
        register_failed: 'Kayıt başarısız',
        password_reset: 'Şifre Sıfırlama',
        set_new_password: 'Yeni şifrenizi belirleyin.',
        logging_in: 'Giriş yapılıyor...',
        new_password: 'Yeni Şifre',
        new_password_repeat: 'Yeni Şifre (Tekrar)',
        update_password: 'Şifreyi Güncelle',
        password_mismatch: 'Şifreler eşleşmiyor!',
        updating: 'Güncelleniyor...',
        password_updated: 'Şifreniz güncellendi! Girişe yönlendiriliyor...',
        token_expired: 'Bir hata oluştu. Token süresi dolmuş olabilir.',
        forgot_email_prompt: 'Şifre sıfırlama bağlantısı almak için kayıtlı e-posta adresinizi girin:',
        success: 'Başarılı',
        error_try_again: 'Bir hata oluştu. Lütfen tekrar deneyin.'
    },
    en: {
        cart: 'Cart',
        my_tickets: '🎟 My Tickets',
        my_wishlist: '❤ My Wishlist',
        notifications: '🔔 Notifications',
        pending_approval: '⏳ Pending Approval',
        users: '👥 Users',
        all_events: '📋 All Events',
        platform_revenue: '💰 Platform Revenue',
        my_events: '🎪 My Events',
        create_event: '➕ Create Event',
        revenue_report: '💰 Revenue Report',
        sales_history: '📜 Sales History',
        promotions: '🎫 Promotions',
        qr_validation: '🔍 QR Validation',
        logout: '🚪 Logout',
        login: 'Login',
        register: 'Register',
        please_login_wishlist: 'Please login to add to favorites.',
        logging_in: 'Logging in...',
        login_failed: 'Login failed',
        server_error: 'Could not connect to server',
        password_length: 'Password must be at least 6 characters',
        register_success: 'Registration successful! Redirecting...',
        register_failed: 'Registration failed',
        password_reset: 'Password Reset',
        set_new_password: 'Set your new password.',
        logging_in: 'Logging in...',
        new_password: 'New Password',
        new_password_repeat: 'New Password (Repeat)',
        update_password: 'Update Password',
        password_mismatch: 'Passwords do not match!',
        updating: 'Updating...',
        password_updated: 'Your password has been updated! Redirecting to login...',
        token_expired: 'An error occurred. Token may have expired.',
        forgot_email_prompt: 'Enter your registered email address to receive a password reset link:',
        success: 'Success',
        error_try_again: 'An error occurred. Please try again.'
    },
    de: {
        cart: 'Warenkorb',
        my_tickets: '🎟 Meine Tickets',
        my_wishlist: '❤ Meine Wunschliste',
        notifications: '🔔 Benachrichtigungen',
        pending_approval: '⏳ Ausstehende Genehmigung',
        users: '👥 Benutzer',
        all_events: '📋 Alle Ereignisse',
        platform_revenue: '💰 Plattformeinnahmen',
        my_events: '🎪 Meine Events',
        create_event: '➕ Event Erstellen',
        revenue_report: '💰 Einnahmenbericht',
        sales_history: '📜 Verkaufshistorie',
        promotions: '🎫 Werbeaktionen',
        qr_validation: '🔍 QR-Validierung',
        logout: '🚪 Abmelden',
        login: 'Anmelden',
        register: 'Registrieren',
        please_login_wishlist: 'Bitte melden Sie sich an, um zu Favoriten hinzuzufügen.',
        logging_in: 'Anmelden...',
        login_failed: 'Anmeldung fehlgeschlagen',
        server_error: 'Verbindung zum Server konnte nicht hergestellt werden',
        password_length: 'Das Passwort muss mindestens 6 Zeichen lang sein',
        register_success: 'Registrierung erfolgreich! Weiterleitung...',
        register_failed: 'Registrierung fehlgeschlagen',
        password_reset: 'Passwort zurücksetzen',
        set_new_password: 'Legen Sie Ihr neues Passwort fest.',
        logging_in: 'Anmelden...',
        new_password: 'Neues Passwort',
        new_password_repeat: 'Neues Passwort (Wiederholung)',
        update_password: 'Passwort aktualisieren',
        password_mismatch: 'Passwörter stimmen nicht überein!',
        updating: 'Aktualisieren...',
        password_updated: 'Ihr Passwort wurde aktualisiert! Weiterleitung zur Anmeldung...',
        token_expired: 'Ein Fehler ist aufgetreten. Token ist möglicherweise abgelaufen.',
        forgot_email_prompt: 'Geben Sie Ihre registrierte E-Mail-Adresse ein, um einen Link zum Zurücksetzen des Passworts zu erhalten:',
        success: 'Erfolg',
        error_try_again: 'Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.'
    }
};

const _lang = getLangFromCookie();
const t = (key) => (authI18n[_lang] || authI18n['tr'])[key] || key;

const LANG_OPTIONS = [
  { code: 'tr', label: 'TR', flag: 'tr' },
  { code: 'en', label: 'EN', flag: 'gb' },
  { code: 'de', label: 'DE', flag: 'de' },
];

function langFlagImg(flagCode) {
  return `<img src="./images/flags/${flagCode}.svg" alt="" class="lang-flag" width="20" height="15" loading="lazy" decoding="async">`;
}

const _currentLang = LANG_OPTIONS.find(l => l.code === _lang) || LANG_OPTIONS[0];
const _langMenuItems = LANG_OPTIONS.map(l =>
  `<a href="#" onclick="window.location.href='/set_language/${l.code}?next=' + encodeURIComponent(window.location.href)" class="dropdown-item lang-option" style="text-decoration:none;">${langFlagImg(l.flag)}<span>${l.label}</span></a>`
).join('');

const LANG_BTN = `
  <div class="lang-dropdown" style="position:relative; display:inline-block; margin-right:5px;">
    <button class="btn btn-outline" style="padding:6px 12px; font-size:0.85rem; border-radius:8px; display:flex; align-items:center; gap:6px;" onclick="event.stopPropagation(); document.getElementById('langMenu').classList.toggle('active')">
      ${langFlagImg(_currentLang.flag)}<span id="currentLangLabel">${_currentLang.label}</span> ▾
    </button>
    <div id="langMenu" class="user-dropdown-menu" style="right:0; left:auto; top:120%;">
      ${_langMenuItems}
    </div>
  </div>
`;

const CART_BTN = `
  <a href="cart.html" class="nav-link cart-link-nav" style="position:relative; margin-right:10px; display:flex; align-items:center; gap:5px; text-decoration:none;">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
    <span style="font-weight:600;" id="navCartText">${t('cart')}</span> <span id="globalCartCount" style="background:#ec4899; color:white; border-radius:10px; padding:2px 6px; font-size:0.7rem; font-weight:bold; margin-left:4px; display:none;">0</span>
  </a>
`;

function renderNav() {
    const token = getToken(), user = getUser();

    // ── DYNAMIC MOBILE NAVIGATION GENERATION ──────────────────────
    let mobileOverlay = document.getElementById('mobileNav');
    if (!mobileOverlay) {
        mobileOverlay = document.createElement('div');
        mobileOverlay.className = 'mobile-nav-overlay';
        mobileOverlay.id = 'mobileNav';
        const exploreLabel = _lang === 'tr' ? 'Keşfet' : (_lang === 'de' ? 'Entdecken' : 'Explore');
        mobileOverlay.innerHTML = `
          <button class="mobile-menu-btn" id="closeMobileMenu" aria-label="Close" style="position:absolute;top:16px;right:16px;color:var(--text-muted);width:36px;height:36px;padding:6px;flex:none;">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>
          <ul class="nav-links" style="display:flex; flex-direction:column; text-align:center; gap:8px;">
            <li><a href="index.html" class="nav-link mobile-link" onclick="document.getElementById('mobileNav')?.classList.remove('active')">${exploreLabel}</a></li>
          </ul>
          <div id="mobileNavAuth" style="display:flex; flex-direction:column; gap:12px; width:100%; max-width:280px; margin-top: 15px;">
            <!-- auth.js tarafından dinamik doldurulur -->
          </div>
        `;
        document.body.appendChild(mobileOverlay);
    }

    const navContainer = document.querySelector('.navbar .nav-container') || document.querySelector('.navbar .container');
    if (navContainer && !navContainer.querySelector('#mobileMenuBtn')) {
        const btn = document.createElement('button');
        btn.className = 'mobile-menu-btn';
        btn.id = 'mobileMenuBtn';
        btn.type = 'button';
        btn.setAttribute('aria-label', 'Menu');
        btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>`;
        navContainer.appendChild(btn);
    }

    const curPath = window.location.pathname;
    const isIndex = curPath === '/' || curPath.endsWith('/index.html') || curPath === '' || (!curPath.includes('.html'));
    const isEventDetail = curPath.endsWith('/event-detail.html');
    const shouldBindOverlay = !isIndex && !isEventDetail;

    if (shouldBindOverlay) {
        const openBtn = document.getElementById('mobileMenuBtn');
        const closeBtn = document.getElementById('closeMobileMenu');
        if (openBtn && mobileOverlay && !openBtn.dataset.listened) {
            openBtn.dataset.listened = "true";
            openBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                mobileOverlay.classList.add('active');
                document.body.style.overflow = 'hidden';
            });
        }
        if (closeBtn && mobileOverlay && !closeBtn.dataset.listened) {
            closeBtn.dataset.listened = "true";
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                mobileOverlay.classList.remove('active');
                document.body.style.overflow = '';
            });
        }
    }

    const ctrls = document.querySelectorAll('.user-controls');
    
    ctrls.forEach(ctrl => {
        if (token && user) {
            const firstName = user.fullname.split(' ')[0];
            const dashBase = user.role === 'admin' ? 'admin.html' : user.role === 'organizer' ? 'organizer.html' : 'dashboard.html';
            
             let dropLinks = '';
            const commonLinks = `
              <hr style="border:0; border-top:1px solid var(--border); margin:4px 0;">
              <a href="dashboard.html?tab=tickets" class="dropdown-item">${t('my_tickets')}</a>
              <a href="dashboard.html?tab=wishlist" class="dropdown-item">${t('my_wishlist')}</a>
              <a href="dashboard.html?tab=notifications" class="dropdown-item">${t('notifications')}</a>
            `;

            if (user.role === 'admin') {
              dropLinks = `
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('pending') : window.location.href='admin.html?tab=pending'" class="dropdown-item">${t('pending_approval')}</a>
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('users') : window.location.href='admin.html?tab=users'" class="dropdown-item">${t('users')}</a>
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('allevents') : window.location.href='admin.html?tab=allevents'" class="dropdown-item">${t('all_events')}</a>
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('revenue') : window.location.href='admin.html?tab=revenue'" class="dropdown-item">${t('platform_revenue')}</a>
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('sales') : window.location.href='admin.html?tab=sales'" class="dropdown-item">${t('sales_history')}</a>
                ${commonLinks}
              `;
            } else if (user.role === 'organizer') {
              dropLinks = `
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('myevents') : window.location.href='organizer.html?tab=myevents'" class="dropdown-item">${t('my_events')}</a>
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('create') : window.location.href='organizer.html?tab=create'" class="dropdown-item">${t('create_event')}</a>
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('revenue') : window.location.href='organizer.html?tab=revenue'" class="dropdown-item">${t('revenue_report')}</a>
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('sales') : window.location.href='organizer.html?tab=sales'" class="dropdown-item">${t('sales_history')}</a>
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('promotions') : window.location.href='organizer.html?tab=promotions'" class="dropdown-item">${t('promotions')}</a>
                <a href="#" onclick="event.preventDefault(); typeof showTab==='function' ? showTab('validate') : window.location.href='organizer.html?tab=validate'" class="dropdown-item">${t('qr_validation')}</a>
                ${commonLinks}
              `;
            } else {
              dropLinks = `
                <a href="dashboard.html?tab=tickets" class="dropdown-item">${t('my_tickets')}</a>
                <a href="dashboard.html?tab=wishlist" class="dropdown-item">${t('my_wishlist')}</a>
                <a href="dashboard.html?tab=notifications" class="dropdown-item">${t('notifications')}</a>
              `;
            }

            ctrl.innerHTML = `
              ${CART_BTN}
              ${LANG_BTN}
              ${THEME_BTN}
              <div class="user-dropdown-wrapper">
                <div style="display:flex; align-items:center; gap:8px;">
                  <a href="${dashBase}?tab=profile" class="btn btn-outline" style="font-size:.85rem;display:flex;align-items:center;gap:6px;">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                    ${firstName}
                  </a>
                  <button class="btn btn-outline" style="padding: 8px; font-size: 1.1rem;" onclick="event.stopPropagation(); window.toggleUserDropdown()">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
                  </button>
                </div>
                <div id="userDropdown" class="user-dropdown-menu">
                  ${dropLinks}
                  <hr style="border:0; border-top:1px solid var(--border); margin:4px 0;">
                  <button onclick="logout()" class="dropdown-item" style="width:100%; border:0; background:none; cursor:pointer; color:var(--coral); text-align:left; font-weight:700;">${t('logout')}</button>
                </div>
              </div>`;
        } else {
            ctrl.innerHTML = `
              ${CART_BTN}
              ${LANG_BTN}
              ${THEME_BTN}
              <a href="login.html" class="btn btn-outline" style="font-size:.85rem;">${t('login')}</a>
              <a href="register.html" class="btn btn-primary" style="font-size:.85rem;">${t('register')}</a>`;
        }
    });

    // ── MOBİL NAV AUTH ALANI ─────────────────────────────────────
    const mobileAuthArea = document.getElementById('mobileNavAuth');
    if (mobileAuthArea) {
        if (token && user) {
            const firstName = user.fullname.split(' ')[0];
            const dashBase = user.role === 'admin' ? 'admin.html' : user.role === 'organizer' ? 'organizer.html' : 'dashboard.html';
            const lnk = (href, label) => {
              let tabName = '';
              if (href.includes('tab=')) {
                tabName = href.split('tab=')[1].split('&')[0];
              }
              const pageName = href.split('?')[0];
              const curPage = window.location.pathname.split('/').pop() || 'index.html';
              
              if (tabName && (pageName === curPage || (curPage === 'index.html' && pageName === 'index.html'))) {
                return `<a href="#" onclick="event.preventDefault(); document.getElementById('mobileNav')?.classList.remove('active'); document.body.style.overflow = ''; typeof showTab==='function' ? showTab('${tabName}') : window.location.href='${href}'" class="btn btn-outline mobile-link" style="justify-content:center;gap:8px;">${label}</a>`;
              }
              return `<a href="${href}" onclick="document.getElementById('mobileNav')?.classList.remove('active'); document.body.style.overflow = '';" class="btn btn-outline mobile-link" style="justify-content:center;gap:8px;">${label}</a>`;
            };

            let roleLinks = '';
            if (user.role === 'admin') {
              roleLinks = `
                ${lnk('admin.html?tab=pending', t('pending_approval'))}
                ${lnk('admin.html?tab=users', t('users'))}
                ${lnk('admin.html?tab=allevents', t('all_events'))}
                ${lnk('admin.html?tab=revenue', t('platform_revenue'))}
                ${lnk('admin.html?tab=sales', t('sales_history'))}`;
            } else if (user.role === 'organizer') {
              roleLinks = `
                ${lnk('organizer.html?tab=myevents', t('my_events'))}
                ${lnk('organizer.html?tab=create', t('create_event'))}
                ${lnk('organizer.html?tab=revenue', t('revenue_report'))}
                ${lnk('organizer.html?tab=sales', t('sales_history'))}
                ${lnk('organizer.html?tab=promotions', t('promotions'))}`;
            } else {
              roleLinks = `
                ${lnk('cart.html', '🛒 ' + t('cart'))}
                ${lnk(dashBase + '?tab=profile', '👤 ' + firstName)}
                ${lnk(dashBase + '?tab=tickets', t('my_tickets'))}
                ${lnk(dashBase + '?tab=wishlist', t('my_wishlist'))}
                ${lnk(dashBase + '?tab=notifications', t('notifications'))}`;
            }

            // Admin ve organizer için profil + biletler de ekle
            const commonBottom = (user.role !== 'customer') ? `
              ${lnk('dashboard.html?tab=tickets', t('my_tickets'))}
              ${lnk(dashBase + '?tab=profile', '👤 ' + firstName)}` : '';

            mobileAuthArea.innerHTML = `
              ${roleLinks}
              ${commonBottom}
              <button onclick="logout()" class="btn btn-danger mobile-link" style="justify-content:center;border-color:rgba(239,68,68,0.4);">
                ${t('logout')}
              </button>`;
        } else {
            mobileAuthArea.innerHTML = `
              <a href="cart.html" class="btn btn-outline mobile-link" style="justify-content:center; gap:8px;">
                🛒 ${t('cart')}
              </a>
              <a href="login.html" class="btn btn-outline mobile-link" style="justify-content:center;">${t('login')}</a>
              <a href="register.html" class="btn btn-primary mobile-link" style="justify-content:center;">${t('register')}</a>`;
        }
    }

    // Handle dropdown closing
    window.toggleUserDropdown = () => {
        const menu = document.getElementById('userDropdown');
        if (menu) menu.classList.toggle('active');
    };

    document.addEventListener('click', () => {
        document.getElementById('userDropdown')?.classList.remove('active');
        document.getElementById('langMenu')?.classList.remove('active');
    });
    // Ensure theme toggle is present even if .user-controls is missing
    if (ctrls.length === 0) {
        if (!document.querySelector('.theme-toggle')) {
            const wrapper = document.createElement('div');
            wrapper.style.display = 'flex';
            wrapper.style.alignItems = 'center';
            wrapper.style.gap = '10px';
            wrapper.innerHTML = LANG_BTN + THEME_BTN;
            
            const navC = document.querySelector('.navbar .container');
            if (navC) {
                wrapper.style.marginLeft = 'auto'; // push to the right
                navC.appendChild(wrapper);
            } else {
                // No navbar exists (e.g. login/register), float it top right
                wrapper.style.position = 'absolute';
                wrapper.style.top = '25px';
                wrapper.style.right = '25px';
                wrapper.style.zIndex = '9999';
                document.body.appendChild(wrapper);
            }
        }
    }
    
    // Restore cart count after re-rendering the nav bar
    if (typeof updateGlobalCartCount === 'function') {
        updateGlobalCartCount();
    }
}

// ── WISHLIST ──────────────────────────────────────────────────
let wishlistIds = new Set();

async function loadWishlistIds() {
    if (!getToken()) return;
    try {
        const r = await fetch('/api/wishlist', { headers: authHeaders() });
        if (r.ok) wishlistIds = new Set((await r.json()).map(e => e.id));
    } catch {}
}

window.toggleWishlist = async (eventId, btn) => {
    if (!getToken()) { alert(t('please_login_wishlist')); return goToLogin(); }
    const inList = wishlistIds.has(eventId);
    try {
        const r = await fetch(`/api/wishlist/${eventId}`, { method: inList ? 'DELETE' : 'POST', headers: authHeaders() });
        if (r.ok) {
            if (inList) { wishlistIds.delete(eventId); btn.classList.remove('wished'); }
            else        { wishlistIds.add(eventId);    btn.classList.add('wished');    }
        }
    } catch {}
};

// ── NOTIFICATIONS BADGE ───────────────────────────────────────
async function loadNotifBadge() {
    if (!getToken()) return;
    try {
        const r = await fetch('/api/notifications', { headers: authHeaders() });
        if (r.ok) {
            const unread = (await r.json()).filter(n => !n.is_read).length;
            document.querySelectorAll('.notif-badge').forEach(b => {
                b.style.display = unread > 0 ? 'inline-flex' : 'none';
                b.textContent = unread > 9 ? '9+' : unread;
            });
        }
    } catch {}
}

// ── TOAST ─────────────────────────────────────────────────────
window.showToast = (msg, type = 'default') => {
    document.querySelector('.toast')?.remove();
    const t = Object.assign(document.createElement('div'), { className: `toast ${type}`, innerHTML: msg });
    document.body.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 400); }, 3200);
};

// ── FORMS ─────────────────────────────────────────────────────
function initLoginForm() {
    const form = document.getElementById('loginForm');
    if (!form) return;
    form.addEventListener('submit', async e => {
        e.preventDefault();
        const btn = form.querySelector('[type=submit]'), orig = btn.textContent;
        btn.textContent = t('logging_in'); btn.disabled = true;
        try {
            const r = await fetch('/api/auth/login', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: document.getElementById('email').value, password: document.getElementById('password').value })
            });
            const d = await r.json();
            if (r.ok) {
                localStorage.setItem('token', d.token);
                localStorage.setItem('user', JSON.stringify(d.user));
                
                // Giriş yapınca yeni sepet anahtarı devreye girecek
                window.location.href = d.user.role === 'admin' ? 'admin.html' : d.user.role === 'organizer' ? 'organizer.html' : 'index.html';
            } else { setFeedback(form, d.message || t('login_failed'), 'error'); btn.textContent = orig; btn.disabled = false; }
        } catch { setFeedback(form, t('server_error'), 'error'); btn.textContent = orig; btn.disabled = false; }
    });
}

function initRegisterForm() {
    const form = document.getElementById('registerForm');
    if (!form) return;
    form.addEventListener('submit', async e => {
        e.preventDefault();
        const btn = form.querySelector('[type=submit]'), orig = btn.textContent;
        const password = document.getElementById('password').value;
        if (password.length < 6) {
          setFeedback(form, t('password_length'), 'error');
          btn.textContent = orig; btn.disabled = false;
          return;
        }
        const role = document.getElementById('role')?.value || 'customer';
        try {
            const r = await fetch('/api/auth/register', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    fullname: `${document.getElementById('firstName').value} ${document.getElementById('lastName').value}`,
                    phone: document.getElementById('phone').value,
                    birthdate: document.getElementById('birthdate').value,
                    email: document.getElementById('email').value,
                    password: password, role
                })
            });
            const d = await r.json();
            if (r.ok) { setFeedback(form, t('register_success'), 'success'); setTimeout(() => { window.location.href = 'login.html'; }, 1500); }
            else { setFeedback(form, d.message || t('register_failed'), 'error'); btn.textContent = orig; btn.disabled = false; }
        } catch { setFeedback(form, t('server_error'), 'error'); btn.textContent = orig; btn.disabled = false; }
    });
}

function setFeedback(form, msg, type) {
    let el = form.querySelector('.form-feedback');
    if (!el) { el = document.createElement('div'); el.className = 'form-feedback'; form.prepend(el); }
    el.className = `form-feedback auth-alert ${type}`;
    el.textContent = (type === 'error' ? '⚠ ' : '✓ ') + msg;
}

// ── INIT ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    renderNav();
    loadWishlistIds();
    loadNotifBadge();
    initLoginForm();
    initRegisterForm();
    initPasswordReset();
    window.addEventListener('scroll', () => {
        document.querySelector('.navbar')?.classList.toggle('scrolled', window.scrollY > 40);
    });
    const mobileOverlay = document.getElementById('mobileNav');
    const openBtn = document.getElementById('mobileMenuBtn');
    const closeBtn = document.getElementById('closeMobileMenu');
    if (mobileOverlay && openBtn && !openBtn.dataset.listened) {
        openBtn.dataset.listened = "true";
        openBtn.addEventListener('click', () => {
            mobileOverlay.classList.add('active');
            document.body.style.overflow = 'hidden';
        });
    }
    if (mobileOverlay && closeBtn && !closeBtn.dataset.listened) {
        closeBtn.dataset.listened = "true";
        closeBtn.addEventListener('click', () => {
            mobileOverlay.classList.remove('active');
            document.body.style.overflow = '';
        });
    }
});

// Password Reset Flow
function initPasswordReset() {
    const params = new URLSearchParams(window.location.search);
    const resetToken = params.get('reset_token');
    const form = document.getElementById('loginForm');

    // loginForm yoksa bu sayfa login sayfası değildir
    if (!form) return;

    if (resetToken) {
        // Başlıkları güncelle
        const title = document.querySelector('.auth-title');
        const subtitle = document.querySelector('.auth-subtitle');
        if (title) title.textContent = t('password_reset');
        if (subtitle) subtitle.textContent = t('set_new_password');

        form.innerHTML = `
            <div class="form-group">
                <label class="form-label">${t('new_password')}</label>
                <div class="password-input-wrapper">
                    <input type="password" id="new_password" class="form-control" placeholder="••••••••" required minlength="6">
                    <button type="button" class="password-toggle" onclick="togglePassword('new_password')">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="eye-icon"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
                    </button>
                </div>
            </div>
            <div class="form-group">
                <label class="form-label">${t('new_password_repeat')}</label>
                <div class="password-input-wrapper">
                    <input type="password" id="new_password_confirm" class="form-control" placeholder="••••••••" required minlength="6">
                </div>
            </div>
            <button type="submit" class="btn btn-primary auth-submit">${t('update_password')}</button>
        `;

        // Social login ve divider'ı gizle
        document.querySelectorAll('.social-login-grid, .auth-divider').forEach(g => g.style.display = 'none');

        // Düğmeyi değiştirerek eski event listener'ları temizle
        const newForm = form.cloneNode(true);
        form.parentNode.replaceChild(newForm, form);

        newForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = newForm.querySelector('button[type="submit"]');
            const orig = btn.textContent;
            const newPass = newForm.querySelector('#new_password').value;
            const confirmPass = newForm.querySelector('#new_password_confirm').value;

            if (newPass.length < 6) {
                setFeedback(newForm, t('password_length'), 'error');
                return;
            }

            if (newPass !== confirmPass) {
                setFeedback(newForm, t('password_mismatch'), 'error');
                return;
            }

            btn.textContent = t('updating');
            btn.disabled = true;
            try {
                const res = await fetch('/api/auth/reset-password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({token: resetToken, new_password: newPass})
                });
                const d = await res.json();
                if (res.ok) {
                    setFeedback(newForm, t('password_updated'), 'success');
                    setTimeout(() => { window.location.href = 'login.html'; }, 2000);
                } else {
                    setFeedback(newForm, d.message || t('token_expired'), 'error');
                    btn.textContent = orig;
                    btn.disabled = false;
                }
            } catch (err) {
                setFeedback(newForm, t('server_error'), 'error');
                btn.textContent = orig;
                btn.disabled = false;
            }
        });
        return;
    }

    // "Şifremi Unuttum" bağlantısını işle
    const forgotLink = document.querySelector('.forgot-password');
    if (forgotLink) {
        forgotLink.onclick = (e) => {
            e.preventDefault();
            const email = prompt(t('forgot_email_prompt'));
            if (email) {
                fetch('/api/auth/forgot-password', {
                    method: 'POST', headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email})
                })
                .then(r => r.json())
                .then(d => alert(d.message || t('success')))
                .catch(() => alert(t('error_try_again')));
            }
        };
    }
}

// Password toggle
window.togglePassword = id => {
    const el = document.getElementById(id);
    el.type = el.type === 'password' ? 'text' : 'password';
};
