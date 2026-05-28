document.addEventListener('DOMContentLoaded', async () => {
  const eventsGrid = document.getElementById('eventsGrid');
  const filterBtns = document.querySelectorAll('.filter-btn');
  const modalOverlay = document.getElementById('ticketModal');
  const closeModalBtn = document.getElementById('closeModal');
  const paymentForm = document.getElementById('paymentForm');
  const searchInput = document.getElementById('searchInput');

  const modalEventTitle = document.getElementById('modalEventTitle');
  const modalEventDate = document.getElementById('modalEventDate');
  const modalPrice = document.getElementById('modalPrice');
  const modalTotal = document.getElementById('modalTotal');
  const quantityInput = document.getElementById('ticketQuantity');
  const modalCapacity = document.getElementById('modalCapacity');

  let currentSelectedEvent = null;
  let globalEvents = [];
  let activeCategory = 'all';

  // Mobile nav
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const closeMobileMenuBtn = document.getElementById('closeMobileMenu');
  const mobileNav = document.getElementById('mobileNav');
  const mobileLinks = document.querySelectorAll('.mobile-link');

  const openMobileMenu = () => { if (mobileNav) { mobileNav.classList.add('active'); document.body.style.overflow = 'hidden'; } };
  const closeMobileMenuFn = () => { if (mobileNav) { mobileNav.classList.remove('active'); document.body.style.overflow = 'auto'; } };
  if (mobileMenuBtn) mobileMenuBtn.addEventListener('click', openMobileMenu);
  if (closeMobileMenuBtn) closeMobileMenuBtn.addEventListener('click', closeMobileMenuFn);
  mobileLinks.forEach(l => l.addEventListener('click', closeMobileMenuFn));

  const navbar = document.querySelector('.navbar');
  window.addEventListener('scroll', () => navbar && navbar.classList.toggle('scrolled', window.scrollY > 50));

  // ── RENDER EVENTS ──────────────────────────────────────────
   function getCategoryName(cat) {
     const val = { concert: window.I18N?.concerts || 'Concert', workshop: window.I18N?.workshops || 'Workshop', theater: window.I18N?.theater || 'Theater' }[cat] || cat;
     const lang = (document.cookie.match(new RegExp('(^| )lang=([^;]+)'))?.[2] || 'tr').toLowerCase();
     if (lang === 'tr') {
       return val.replace(/i/g, 'İ').replace(/ı/g, 'I').toUpperCase();
     }
     return val.toUpperCase();
   }
   function getCategoryClass(cat) {
     return { concert: 'category-concert', workshop: 'category-workshop', theater: 'category-theater' }[cat] || '';
   }

  function renderEvents(events) {
    if (!eventsGrid) return;
    eventsGrid.innerHTML = '';
    if (events.length === 0) {
      eventsGrid.innerHTML = `<p style="color:var(--text-muted);grid-column:1/-1;text-align:center;padding:60px;">${window.I18N?.noEvents || 'No events found matching these criteria.'}</p>`;
      return;
    }
    events.forEach((event, index) => {
      const isFull = event.capacity > 0 && event.sold_count >= event.capacity;
      const remaining = event.capacity - event.sold_count;
      const isWished = wishlistIds.has(event.id);

      const card = document.createElement('div');
      card.className = `event-card glass-panel animate-up delay-${(index % 3) + 1}`;
      card.style.cursor = 'pointer';
      card.onclick = (e) => {
        if (!e.target.closest('.buy-btn') && !e.target.closest('.wish-btn')) {
          window.location.assign('event-detail.html?id=' + event.id);
        }
      };

      card.innerHTML = `
        <div class="event-img-wrapper">
          <div class="event-category-badge ${getCategoryClass(event.category)}" style="text-transform:none;">${getCategoryName(event.category)}</div>
          ${event.featured ? `<div class="featured-badge">⭐ ${window.I18N?.featured || 'Featured'}</div>` : ''}
          <img src="${event.image}" alt="${event.title}" class="event-img" loading="lazy">
          <button class="wish-btn ${isWished ? 'wished' : ''}" title="${isWished ? 'Remove from wishlist' : 'Add to wishlist'}"
            onclick="event.stopPropagation(); toggleWishlist('${event.id}', this)">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="${isWished ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
          </button>
        </div>
        <div class="event-content">
          <div class="event-date">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
            ${(() => {
                try {
                    const d = new Date(event.date);
                    const locale = window.I18N?.locale || 'en-US';
                    if (!isNaN(d)) return d.toLocaleDateString(locale, {day:'numeric', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit'});
                } catch(e) {}
                return event.date;
            })()}
          </div>
          <h3 class="event-title">${event.title}</h3>
          <div class="event-location">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
            ${event.location}
          </div>
          ${event.capacity > 0 ? `
          <div class="capacity-bar-wrap">
            <div class="capacity-bar-track">
              <div class="capacity-bar-fill" style="width:${Math.min(100, Math.round(event.sold_count / event.capacity * 100))}%"></div>
            </div>
            <span class="capacity-label">${isFull ? `<span style="color:#ef4444">${window.I18N?.soldOut || 'Sold Out'}</span>` : remaining + ' ' + (window.I18N?.ticketsLeft || 'tickets left')}</span>
          </div>` : ''}
          <div class="event-footer">
            <div class="event-price">${event.price.toLocaleString('tr-TR')} ₺</div>
            <button class="btn btn-primary buy-btn" data-id="${event.id}" ${isFull ? 'disabled style="opacity:0.5;cursor:not-allowed;"' : ''}>
              ${isFull ? (window.I18N?.soldOut || 'Sold Out') : (window.I18N?.buyTickets || 'Buy Tickets')}
            </button>
          </div>
        </div>
      `;
      eventsGrid.appendChild(card);
    });
    attachBuyListeners();
  }


  // Expose category setter to global for index.html hero usage
  window._setActiveCategory = (cat) => { activeCategory = cat; };

  // Triggered manually when users click 'Apply Filters' or type
  window.executeServerFiltering = () => {
      const target = document.getElementById('events-section');
      if(target) target.scrollIntoView({behavior:'smooth'});
      
      const prevHtml = eventsGrid.innerHTML;
      eventsGrid.innerHTML = `
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
      `;
      fetchEvents(1, false);
  };

  let searchTimeout;
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
          fetchEvents(1, false);
      }, 500); // 500ms debounce
    });
  }


  // ── MODAL ──────────────────────────────────────────────────
  function attachBuyListeners() {
    document.querySelectorAll('.buy-btn:not([disabled])').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        window.location.assign('checkout.html?id=' + e.currentTarget.getAttribute('data-id'));
      });
    });
  }

  // ── INIT ──────────────────────────────────────────────────
  let currentPage = 1;
  const itemsPerPage = 48;
  const loadMoreBtn = document.createElement('button');
  loadMoreBtn.className = 'btn btn-outline';
  loadMoreBtn.style.margin = '30px auto';
  loadMoreBtn.style.display = 'none';
  loadMoreBtn.textContent = 'Load More';
  eventsGrid.parentNode.insertBefore(loadMoreBtn, eventsGrid.nextSibling);

  async function fetchEvents(page = 1, append = false) {
    if (!append) {
      globalEvents = [];
    }
    try {
      const sp = new URLSearchParams();
      sp.append('page', page);
      sp.append('limit', itemsPerPage);
      
      if(activeCategory && activeCategory !== 'all') sp.append('category', activeCategory);
      const searchVal = document.getElementById('searchInput')?.value.trim();
      if(searchVal) sp.append('search', searchVal);
      
      const loc = document.getElementById('filterLocation')?.value;
      if(loc && loc !== 'all') sp.append('location', loc);
      
      const minP = document.getElementById('filterMinP')?.value;
      if(minP) sp.append('min_price', minP);
      const maxP = document.getElementById('filterMaxP')?.value;
      if(maxP) sp.append('max_price', maxP);
      
      const sDay = document.getElementById('filterStart')?.value;
      if(sDay) sp.append('start_date', sDay);
      const eDay = document.getElementById('filterEnd')?.value;
      if(eDay) sp.append('end_date', eDay);
      
      const sortV = document.getElementById('filterSort')?.value || 'date_asc';
      sp.append('sort', sortV);

      const res = await fetch(`/api/events?${sp.toString()}`);
      if (res.ok) {
        const data = await res.json();
        globalEvents = append ? [...globalEvents, ...data] : data;
        // Don't call client-side applyFilters anymore, server did it:
        renderEvents(globalEvents);
        
        if (data.length < itemsPerPage) {
          loadMoreBtn.style.display = 'none';
        } else {
          loadMoreBtn.style.display = 'block';
        }
      }
    } catch (err) {
      console.error('Could not load events:', err);
    }
  }

  loadMoreBtn.addEventListener('click', () => {
    currentPage++;
    const prevText = loadMoreBtn.textContent;
    loadMoreBtn.textContent = 'Loading...';
    loadMoreBtn.disabled = true;
    fetchEvents(currentPage, true).finally(() => {
        loadMoreBtn.textContent = prevText;
        loadMoreBtn.disabled = false;
    });
  });

  async function loadLocations() {
      try {
          const res = await fetch('/api/events/locations');
          if(res.ok) {
              const locs = await res.json();
              const sel = document.getElementById('filterLocation');
              if(sel) {
                 locs.forEach(l => {
                    sel.innerHTML += `<option value="${l}">${l}</option>`;
                 });
              }
          }
      } catch(e){}
  }

  const urlCat = new URLSearchParams(window.location.search).get('category');
  if (urlCat && ['concert', 'theater', 'workshop', 'all'].includes(urlCat)) {
    activeCategory = urlCat;
    document.querySelectorAll('.hero-cat-item').forEach(b => {
      b.classList.toggle('cat-active', b.getAttribute('data-filter') === urlCat);
    });
  }

  await loadWishlistIds();
  await loadLocations();
  await fetchEvents(1, false);

  if (urlCat && urlCat !== 'all') {
    const target = document.getElementById('events-section');
    if (target) target.scrollIntoView({ behavior: 'smooth' });
  }

  loadNotifBadge();
});
