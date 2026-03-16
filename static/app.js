/* ═══════════════════════════════════════════════
   VOYAGR INDIA — app.js
   ═══════════════════════════════════════════════ */

// ─── CURSOR LIQUID GLASS ─────────────────────────

const cursorOrb = document.getElementById('cursorOrb');
const cursorDot = document.getElementById('cursorDot');
let mouseX = 0, mouseY = 0, orbX = 0, orbY = 0, dotX = 0, dotY = 0;

function animateCursor() {
    orbX += (mouseX - orbX) * 0.08;
    orbY += (mouseY - orbY) * 0.08;
    dotX += (mouseX - dotX) * 0.35;
    dotY += (mouseY - dotY) * 0.35;
    cursorOrb.style.left = orbX + 'px';
    cursorOrb.style.top = orbY + 'px';
    cursorDot.style.left = dotX + 'px';
    cursorDot.style.top = dotY + 'px';
    requestAnimationFrame(animateCursor);
}

document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;
    document.querySelectorAll('[data-glass]').forEach(panel => {
        const rect = panel.getBoundingClientRect();
        const x = ((e.clientX - rect.left) / rect.width) * 100;
        const y = ((e.clientY - rect.top) / rect.height) * 100;
        panel.style.setProperty('--mouse-x', x + '%');
        panel.style.setProperty('--mouse-y', y + '%');
    });
});

document.addEventListener('mouseover', (e) => {
    const interactive = e.target.closest('button, a, input, select, .pill, .rec-card, .day-card, .tab-btn');
    if (interactive) {
        cursorDot.style.width = '16px';
        cursorDot.style.height = '16px';
        cursorDot.style.opacity = '0.6';
    } else {
        cursorDot.style.width = '8px';
        cursorDot.style.height = '8px';
        cursorDot.style.opacity = '1';
    }
});

animateCursor();


// ─── PILL GROUPS ─────────────────────────────────

document.querySelectorAll('#styleGroup .pill').forEach(pill => {
    pill.addEventListener('click', () => {
        document.querySelectorAll('#styleGroup .pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
    });
});

document.querySelectorAll('#interestGroup .pill').forEach(pill => {
    pill.addEventListener('click', () => pill.classList.toggle('active'));
});


// ─── COLLECT FORM DATA ───────────────────────────

function getFormData() {
    const style = document.querySelector('#styleGroup .pill.active')?.dataset.val || 'Relaxed Explorer';
    const interests = [...document.querySelectorAll('#interestGroup .pill.active')]
        .map(p => p.dataset.val).join(', ') || 'Sightseeing';

    return {
        destination: document.getElementById('destination').value.trim(),
        travelDate: document.getElementById('travelDate').value.trim(),
        days: document.getElementById('days').value || '7',
        travelers: document.getElementById('travelers').value || '2',
        budget: document.getElementById('budget').value || '50000',
        departureCity: document.getElementById('departureCity').value,
        tripType: document.getElementById('tripType').value,
        style,
        interests,
        dietary: document.getElementById('dietary').value,
        accommodation: document.getElementById('accommodation').value,
    };
}


// ─── LOADING STEPS ───────────────────────────────

function animateLoadingSteps() {
    let step = 0;
    const interval = setInterval(() => {
        if (step < 6) {
            document.getElementById(`lstep-${step}`)?.classList.add('done');
            step++;
        } else {
            clearInterval(interval);
        }
    }, 900);
    return interval;
}


// ─── GENERATE ────────────────────────────────────

async function handleGenerate() {
    const data = getFormData();
    if (!data.destination) {
        const el = document.getElementById('destination');
        el.style.borderColor = 'rgba(255,100,100,0.6)';
        el.focus();
        setTimeout(() => el.style.borderColor = '', 1500);
        return;
    }

    document.getElementById('formSection').style.display = 'none';
    document.getElementById('loadingSection').style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });

    for (let i = 0; i < 6; i++) document.getElementById(`lstep-${i}`)?.classList.remove('done');
    const stepTimer = animateLoadingSteps();

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const result = await response.json();

        clearInterval(stepTimer);
        for (let i = 0; i < 6; i++) document.getElementById(`lstep-${i}`)?.classList.add('done');

        await sleep(600);

        if (result.success && result.plan) {
            document.getElementById('loadingSection').style.display = 'none';
            document.getElementById('resultsSection').style.display = 'block';
            renderResults(result.plan);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
            showError(result.error || 'Something went wrong. Please try again.');
        }
    } catch (err) {
        clearInterval(stepTimer);
        showError('Network error — please check your connection.');
        console.error(err);
    }
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function showError(msg) {
    document.getElementById('loadingSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
    document.getElementById('resultsCard').innerHTML = `
    <div style="padding:2.5rem">
      <div class="error-box"><strong>⚠️ Couldn't generate your trip plan</strong>${msg}</div>
      <button class="btn-new-trip" style="margin-top:1.5rem;position:static;cursor:none" onclick="resetToForm()">← Try again</button>
    </div>`;
}

function resetToForm() {
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('formSection').style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function switchTab(idx) {
    document.querySelectorAll('.tab-btn').forEach((t, i) => t.classList.toggle('active', i === idx));
    document.querySelectorAll('.tab-pane').forEach((p, i) => p.classList.toggle('active', i === idx));
}

function mapsUrl(q) { return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`; }
function renderStars(r) { const n = Math.round(parseFloat(r) || 4); return '★'.repeat(n) + '☆'.repeat(Math.max(0, 5 - n)); }
function tierClass(t = '') { const s = t.toLowerCase(); return s.includes('luxury') ? 'tier-luxury' : s.includes('budget') ? 'tier-budget' : 'tier-mid'; }

const budgetColors = {
    flights_from_india: '#ff9f7f',
    accommodation: '#c4b0ff',
    food: '#6ee7f7',
    transport: '#ffd580',
    activities: '#a8e6cf',
    shopping: '#ffb3c6',
    buffer: 'rgba(255,255,255,0.25)',
};


// ─── RENDER RESULTS ──────────────────────────────

function renderResults(p) {
    const tabDefs = [
        { label: '📅 Itinerary', id: 'itinerary' },
        { label: '🏨 Hotels', id: 'hotels' },
        { label: '🍽️ Dining', id: 'dining' },
        { label: '🚌 Transport', id: 'transport' },
        { label: '📍 Explore', id: 'explore' },
        { label: '💰 Budget (₹)', id: 'budget' },
        { label: '🇮🇳 India Tips', id: 'india' },
        { label: '🧳 Essentials', id: 'essentials' },
    ];

    // Live weather banner
    let weatherBanner = '';
    if (p.live_weather && p.live_weather.success) {
        const w = p.live_weather;
        weatherBanner = `
      <div class="live-banner">
        <span class="live-dot"></span>
        <span>LIVE</span>
        <span style="color:var(--text-secondary);margin:0 8px">|</span>
        🌤️ ${w.city}: <strong>${w.temp_c}°C</strong>, ${w.description}
        &nbsp;·&nbsp; 💧 ${w.humidity}% humidity
        &nbsp;·&nbsp; 💱 1 USD = ₹${p.live_exchange?.usd_to_inr || '—'}
      </div>`;
    }

    const html = `
    ${weatherBanner}
    <div class="result-header">
      <button class="btn-new-trip" onclick="resetToForm()">← New Trip</button>
      <div class="result-destination">${p.destination || 'Your Trip'}</div>
      <div class="result-tagline">${p.tagline || ''}</div>
      <div class="result-meta">
        <div class="meta-chip"><span class="meta-icon">📅</span> ${p.days} days</div>
        <div class="meta-chip"><span class="meta-icon">👥</span> ${p.travelers} traveler(s)</div>
        <div class="meta-chip"><span class="meta-icon">💰</span> ₹${p.budget_inr}</div>
        <div class="meta-chip"><span class="meta-icon">🌤️</span> ${p.travel_season || ''}</div>
        <div class="meta-chip"><span class="meta-icon">🛂</span> ${p.visa_info ? p.visa_info.substring(0, 40) + '…' : ''}</div>
      </div>
    </div>

    <div class="tab-bar">
      ${tabDefs.map((t, i) => `<button class="tab-btn ${i === 0 ? 'active' : ''}" onclick="switchTab(${i})">${t.label}</button>`).join('')}
    </div>

    ${tabDefs.map((t, i) => `
      <div class="tab-pane ${i === 0 ? 'active' : ''}" id="pane-${t.id}">
        ${renderPane(t.id, p)}
      </div>`).join('')}
  `;

    document.getElementById('resultsCard').innerHTML = html;
    document.getElementById('resultsCard').setAttribute('data-glass', '');

    requestAnimationFrame(() => setTimeout(() => animateBudgetBars(p.budget_breakdown_inr || {}), 200));
}


// ─── RENDER PANES ────────────────────────────────

function renderPane(id, p) {
    switch (id) {
        case 'itinerary': return renderItinerary(p);
        case 'hotels': return renderHotels(p);
        case 'dining': return renderDining(p);
        case 'transport': return renderTransport(p);
        case 'explore': return renderExplore(p);
        case 'budget': return renderBudget(p);
        case 'india': return renderIndiaTips(p);
        case 'essentials': return renderEssentials(p);
        default: return '';
    }
}


// ── ITINERARY ──
function renderItinerary(p) {
    if (!p.itinerary?.length) return '<p style="color:var(--text-secondary)">No itinerary data.</p>';
    return p.itinerary.map(day => `
    <div class="day-card">
      <div class="day-number">Day ${day.day}</div>
      <div class="day-theme">${day.theme || ''}</div>
      <ul class="activity-list">
        ${(day.activities || []).map(a => `
          <li class="activity-item">
            <span class="activity-time">${a.time || ''}</span>
            <div class="activity-body">
              <div class="activity-name">${a.name || ''}</div>
              <div class="activity-note">${a.note || ''}</div>
              <div class="activity-meta">
                ${a.duration ? `<span>⏱ ${a.duration}</span>` : ''}
                ${a.cost_inr ? `<span>💰 ${a.cost_inr}</span>` : ''}
              </div>
              ${a.maps_query ? `<a href="${mapsUrl(a.maps_query)}" target="_blank" class="maps-link">📍 View on Google Maps</a>` : ''}
            </div>
          </li>`).join('')}
      </ul>
    </div>`).join('');
}


// ── HOTELS ──
function renderHotels(p) {
    if (!p.hotels?.length) return '<p style="color:var(--text-secondary)">No hotel data.</p>';
    return `<div class="rec-grid">
    ${p.hotels.map(h => `
      <div class="rec-card">
        <div class="tier-badge ${tierClass(h.tier)}">${h.tier || 'Hotel'}</div>
        <div class="rec-name">${h.name || ''}</div>
        ${h.area ? `<div style="font-size:11px;color:var(--accent-violet);margin-bottom:4px">📍 ${h.area}</div>` : ''}
        <div class="rec-sub">${h.why || ''}</div>
        ${(h.highlights || []).length ? `<ul class="rec-highlights">${h.highlights.map(hi => `<li>${hi}</li>`).join('')}</ul>` : ''}
        ${h.booking_tip ? `<div style="font-size:11px;color:var(--accent-teal);margin-top:8px">💡 ${h.booking_tip}</div>` : ''}
        <div class="rec-footer">
          <div class="rec-price">₹ ${(h.price_per_night_inr || '').replace('INR', '').trim()} <span style="font-weight:300;font-size:11px;color:var(--text-secondary)">/night</span></div>
          <div class="rec-rating"><span class="stars">${renderStars(h.rating)}</span> ${h.rating || ''}</div>
        </div>
        ${h.maps_query ? `<a href="${mapsUrl(h.maps_query)}" target="_blank" class="maps-link" style="margin-top:10px;display:inline-flex">📍 View on Maps</a>` : ''}
      </div>`).join('')}
  </div>`;
}


// ── DINING ──
function renderDining(p) {
    const restaurants = p.restaurants || [];
    const yelp = p.yelp_restaurants || [];

    let html = '';

    if (yelp.length) {
        html += `
      <div style="font-size:10.5px;letter-spacing:0.16em;text-transform:uppercase;color:var(--accent-violet);font-weight:600;margin-bottom:1rem">
        ⭐ Top Rated — Live from Yelp
      </div>
      <div class="rec-grid" style="margin-bottom:2rem">
        ${yelp.map(r => `
          <div class="rec-card">
            <div class="tier-badge tier-mid">${r.cuisine || 'Restaurant'}</div>
            <div class="rec-name">${r.name || ''}</div>
            <div class="rec-sub">${r.address || ''}</div>
            <div class="rec-footer">
              <div class="rec-rating"><span class="stars">${renderStars(r.rating)}</span> ${r.rating} <span style="color:var(--text-muted)">(${r.review_count} reviews)</span></div>
              <div class="rec-price">${r.price || '$$'}</div>
            </div>
            ${r.maps_query ? `<a href="${mapsUrl(r.maps_query)}" target="_blank" class="maps-link" style="margin-top:8px;display:inline-flex">📍 Maps</a>` : ''}
          </div>`).join('')}
      </div>`;
    }

    if (restaurants.length) {
        html += `
      <div style="font-size:10.5px;letter-spacing:0.16em;text-transform:uppercase;color:var(--accent-violet);font-weight:600;margin-bottom:1rem">
        🤖 AI Recommended Restaurants
      </div>
      <div class="rec-grid">
        ${restaurants.map(r => `
          <div class="rec-card">
            <div class="tier-badge tier-mid">${r.cuisine || ''}</div>
            <div class="rec-name">${r.name || ''}</div>
            ${r.meal_type ? `<div style="font-size:11px;color:var(--text-secondary);margin-bottom:4px">${r.meal_type}</div>` : ''}
            <div class="rec-sub">${r.why || ''}</div>
            ${r.dish ? `<div style="font-size:12px;color:var(--accent-gold);margin-top:6px">✦ Must try: ${r.dish}</div>` : ''}
            ${r.dietary_note ? `<div style="font-size:11px;color:var(--text-secondary);margin-top:4px">🌿 ${r.dietary_note}</div>` : ''}
            <div class="rec-footer">
              <div class="rec-price">${(r.price_range_inr || r.price_range || '').replace('INR', '₹')}</div>
              ${r.yelp_rating ? `<div class="rec-rating"><span class="stars">${renderStars(r.yelp_rating)}</span></div>` : ''}
            </div>
            ${r.maps_query ? `<a href="${mapsUrl(r.maps_query)}" target="_blank" class="maps-link" style="margin-top:8px;display:inline-flex">📍 Maps</a>` : ''}
          </div>`).join('')}
      </div>`;
    }

    return html || '<p style="color:var(--text-secondary)">No restaurant data.</p>';
}


// ── TRANSPORT ──
function renderTransport(p) {
    let html = '';

    if (p.flight_info) {
        html += `
      <div class="weather-banner" style="margin-bottom:1.5rem">
        <div class="weather-icon-big">✈️</div>
        <div>
          <div class="weather-banner-title">Flights from India</div>
          <div class="weather-banner-text">${p.flight_info}</div>
        </div>
      </div>`;
    }

    if (!p.transport?.length) return html + '<p style="color:var(--text-secondary)">No transport data.</p>';

    html += `<div class="rec-grid">
    ${p.transport.map(t => `
      <div class="rec-card">
        <div class="tier-badge tier-budget">${t.type || ''}</div>
        <div class="rec-name">${t.name || ''}</div>
        <div class="rec-sub">${t.description || ''}</div>
        ${t.tip ? `<div style="font-size:11.5px;color:var(--accent-teal);margin-top:6px">💡 ${t.tip}</div>` : ''}
        ${t.from_airport ? `<div style="font-size:11px;color:var(--accent-violet);margin-top:4px">✈️ Available from airport</div>` : ''}
        <div class="rec-footer">
          <div class="rec-price">${(t.cost_inr || t.approx_cost || '').replace('INR', '₹')}</div>
          ${t.maps_query ? `<a href="${mapsUrl(t.maps_query)}" target="_blank" class="maps-link">📍 Maps</a>` : ''}
        </div>
      </div>`).join('')}
  </div>`;

    return html;
}


// ── EXPLORE ──
function renderExplore(p) {
    let html = '';
    const fsq = p.foursquare_places || {};

    if (fsq.attractions?.length) {
        html += `
      <div style="font-size:10.5px;letter-spacing:0.16em;text-transform:uppercase;color:var(--accent-violet);font-weight:600;margin-bottom:1rem">
        📍 Real Attractions — Verified by Foursquare
      </div>
      <div class="rec-grid" style="margin-bottom:2rem">
        ${fsq.attractions.map(a => `
          <div class="rec-card">
            <div class="tier-badge tier-mid">${a.category || 'Attraction'}</div>
            <div class="rec-name">${a.name || ''}</div>
            <div class="rec-sub">${a.address || ''}</div>
            ${a.maps_query ? `<a href="${mapsUrl(a.maps_query)}" target="_blank" class="maps-link" style="margin-top:8px;display:inline-flex">📍 Maps</a>` : ''}
          </div>`).join('')}
      </div>`;
    }

    if (p.best_areas?.length) {
        html += `
      <div style="font-size:10.5px;letter-spacing:0.16em;text-transform:uppercase;color:var(--accent-violet);font-weight:600;margin-bottom:1rem">
        🏘️ Best Neighbourhoods
      </div>
      <div class="area-grid" style="margin-bottom:2rem">
        ${p.best_areas.map(a => `
          <div class="area-card">
            <div class="area-name">${a.name}</div>
            <div class="area-vibe">${a.vibe}</div>
            <div class="area-good">Perfect for: ${a.good_for}</div>
          </div>`).join('')}
      </div>`;
    }

    if (p.day_trips?.length) {
        html += `
      <div style="font-size:10.5px;letter-spacing:0.16em;text-transform:uppercase;color:var(--accent-violet);font-weight:600;margin-bottom:1rem">
        🗺️ Day Trips
      </div>
      <div class="rec-grid">
        ${p.day_trips.map(d => `
          <div class="rec-card">
            <div class="rec-name">${d.name}</div>
            <div style="font-size:11px;color:var(--text-secondary);margin-bottom:4px">📏 ${d.distance}</div>
            <div class="rec-sub">${d.why_go}</div>
            <div style="font-size:12px;color:var(--accent-teal);margin-top:6px">🚌 ${d.how_to_get}</div>
            <div style="font-size:11px;color:var(--accent-violet);margin-top:4px">Best for: ${d.best_for}</div>
          </div>`).join('')}
      </div>`;
    }

    return html || '<p style="color:var(--text-secondary)">No explore data.</p>';
}


// ── BUDGET (INR) ──
function renderBudget(p) {
    const bd = p.budget_breakdown_inr || {};
    const total = Object.values(bd).reduce((a, b) => a + Number(b), 0) || 1;

    const rows = [
        { key: 'flights_from_india', label: '✈️ Flights from India', icon: '✈️' },
        { key: 'accommodation', label: '🏨 Accommodation', icon: '🏨' },
        { key: 'food', label: '🍽️ Food & Dining', icon: '🍽️' },
        { key: 'transport', label: '🚌 Local Transport', icon: '🚌' },
        { key: 'activities', label: '🎯 Activities', icon: '🎯' },
        { key: 'shopping', label: '🛍️ Shopping', icon: '🛍️' },
        { key: 'buffer', label: '🛡️ Buffer / Misc', icon: '🛡️' },
    ];

    return `
    <div class="budget-summary">
      <div>
        <div class="budget-total-label">Total Budget</div>
        <div class="budget-total-amount">₹${p.budget_inr}</div>
        ${p.budget_usd_approx ? `<div style="font-size:12px;color:var(--text-secondary);margin-top:4px">≈ USD ${p.budget_usd_approx}</div>` : ''}
      </div>
      <div style="color:var(--text-secondary);font-size:13px;line-height:1.7">
        For ${p.travelers} traveler(s) over ${p.days} days<br/>
        ${p.currency_info || ''}
      </div>
    </div>

    <div class="budget-breakdown">
      ${rows.map(r => {
        const val = Number(bd[r.key] || 0);
        const pct = Math.round(val / total * 100);
        return `
          <div class="budget-row">
            <div class="budget-label">${r.label}</div>
            <div class="budget-bar-track">
              <div class="budget-bar-fill" data-width="${pct}" style="background:${budgetColors[r.key] || '#c4b0ff'};width:0%"></div>
            </div>
            <div class="budget-amount">₹${val.toLocaleString('en-IN')}</div>
          </div>`;
    }).join('')}
    </div>

    ${p.money_tips?.length ? `
      <div class="money-tips">
        <div class="tip-section-label">💡 Money-saving tips for Indian travelers</div>
        ${p.money_tips.map((t, i) => `
          <div class="money-tip">
            <div class="tip-bullet">${i + 1}</div>
            <div>${t}</div>
          </div>`).join('')}
      </div>`: ''}
  `;
}


// ── INDIA TIPS ──
function renderIndiaTips(p) {
    let html = '';

    if (p.visa_info) {
        html += `
      <div class="weather-banner">
        <div class="weather-icon-big">🛂</div>
        <div>
          <div class="weather-banner-title">Visa for Indian Passport Holders</div>
          <div class="weather-banner-text">${p.visa_info}</div>
        </div>
      </div>`;
    }

    if (p.flight_info) {
        html += `
      <div class="weather-banner" style="border-color:rgba(255,213,128,0.2);background:linear-gradient(135deg,rgba(255,213,128,0.08),rgba(196,176,255,0.06))">
        <div class="weather-icon-big">✈️</div>
        <div>
          <div class="weather-banner-title" style="color:var(--accent-gold)">Flights from India</div>
          <div class="weather-banner-text">${p.flight_info}</div>
        </div>
      </div>`;
    }

    if (p.india_specific_tips?.length) {
        html += `
      <div class="essentials-section-label">🇮🇳 Tips Specifically for Indian Travelers</div>
      <ul class="tip-list">
        ${p.india_specific_tips.map((t, i) => `
          <li class="tip-item">
            <div class="tip-bullet">${i + 1}</div>
            <div style="font-size:13px;color:var(--text-secondary);line-height:1.6">${t}</div>
          </li>`).join('')}
      </ul>`;
    }

    if (p.emergency) {
        html += `
      <div class="essentials-section-label" style="margin-top:2rem">🚨 Emergency Contacts</div>
      <div class="emergency-grid">
        ${Object.entries(p.emergency).map(([k, v]) => `
          <div class="emergency-row">
            <div class="emergency-key">${k.replace(/_/g, ' ')}</div>
            <div class="emergency-val">${v}</div>
          </div>`).join('')}
      </div>`;
    }

    return html || '<p style="color:var(--text-secondary)">No India tips data.</p>';
}


// ── ESSENTIALS ──
function renderEssentials(p) {
    let html = '';

    if (p.weather_advisory) {
        html += `
      <div class="weather-banner">
        <div class="weather-icon-big">🌤️</div>
        <div>
          <div class="weather-banner-title">Weather Advisory</div>
          <div class="weather-banner-text">${p.weather_advisory}</div>
        </div>
      </div>`;
    }

    if (p.packing_list) {
        const sections = {
            documents: { label: '📄 Documents', icon: '📄' },
            essentials: { label: '🎒 Essentials', icon: '🎒' },
            clothing: { label: '👗 Clothing', icon: '👗' },
            tech: { label: '💻 Tech', icon: '💻' },
            health: { label: '💊 Health', icon: '💊' },
        };
        for (const [key, meta] of Object.entries(sections)) {
            const items = p.packing_list[key];
            if (items?.length) {
                html += `
          <div class="essentials-section-label">${meta.label}</div>
          <div class="pack-grid">
            ${items.map(item => `
              <div class="pack-item"><span class="pack-icon">${meta.icon}</span>${item}</div>`).join('')}
          </div>`;
            }
        }
    }

    if (p.local_tips?.length) {
        html += `
      <div class="essentials-section-label" style="margin-top:2rem">🧠 Local Insider Tips</div>
      <ul class="tip-list">
        ${p.local_tips.map((t, i) => `
          <li class="tip-item">
            <div class="tip-bullet">${i + 1}</div>
            <div style="font-size:13px;color:var(--text-secondary);line-height:1.6">${t}</div>
          </li>`).join('')}
      </ul>`;
    }

    if (p.phrases?.length) {
        html += `
      <div class="essentials-section-label" style="margin-top:2rem">🗣️ Useful Phrases</div>
      <div class="phrases-grid">
        ${p.phrases.map(ph => `
          <div class="phrase-card">
            <div class="phrase-english">${ph.original}</div>
            <div class="phrase-local">${ph.local}</div>
            <div class="phrase-pronounce">${ph.pronunciation}</div>
          </div>`).join('')}
      </div>`;
    }

    return html || '<p style="color:var(--text-secondary)">No essentials data.</p>';
}


// ─── ANIMATE BUDGET BARS ─────────────────────────

function animateBudgetBars() {
    document.querySelectorAll('.budget-bar-fill').forEach(bar => {
        const w = bar.dataset.width + '%';
        bar.style.width = '0';
        setTimeout(() => bar.style.width = w, 50);
    });
}


// ─── EXPOSE GLOBALS ──────────────────────────────

window.handleGenerate = handleGenerate;
window.resetToForm = resetToForm;
window.switchTab = switchTab;