(function () {
    'use strict';
    const SEL_MIN = 5, BUBBLE_R = 14;
    let currentText = '', lastText = '', panelOpen = false, hidden = false, safeProfCache = null;

    // Cleanup existing instances to prevent duplicates
    ['ym-bubble', 'ym-menu', 'ym-panel'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.remove();
    });

    /* ── Cache ── */
    const CACHE_KEY = 'ym_ai_cache3';
    function getCache(k) { try { const c = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}'); return c[k]?.reply || null; } catch (e) { return null; } }
    function setCache(k, v) { try { const c = JSON.parse(localStorage.getItem(CACHE_KEY) || '{}'); c[k] = { reply: v, ts: Date.now() }; const keys = Object.keys(c); if (keys.length > 100) { keys.sort((a, b) => (c[a].ts || 0) - (c[b].ts || 0)); keys.slice(0, keys.length - 100).forEach(x => delete c[x]); } localStorage.setItem(CACHE_KEY, JSON.stringify(c)); } catch (e) { } }

    /* ── Helper: Hide logic ── */
    const hideBubble = () => { bubble.style.display = 'none'; };
    const hideMenu = () => { menu.style.display = 'none'; };
    const hidePanel = () => { 
        panel.style.display = 'none'; 
        panelOpen = false;
        // Reset scroll when closing
        const body = document.getElementById('ym-body');
        if (body) body.scrollTop = 0;
    };
    const hideAll = () => { hideBubble(); hideMenu(); hidePanel(); };

    /* ── Build DOM ── */
    const bubble = document.createElement('div');
    bubble.id = 'ym-bubble';
    bubble.innerHTML = '<span>YM</span>';
    document.body.appendChild(bubble);

    const menu = document.createElement('div');
    menu.id = 'ym-menu';
    menu.innerHTML = `
        <div class="ym-menu-header"></div>
        <div class="ym-menu-body">
            <div class="ym-search">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><circle cx="7" cy="7" r="4.5" stroke="currentColor" stroke-width="2"/><path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
              <input id="ym-ask-input" type="text" placeholder="Ask…"/>
            </div>
            <div class="ym-row ym-active" data-action="explain">
              <div class="ym-row-icon"><div class="ym-icon-ring"></div></div>
              <span class="ym-row-label">Explain</span>
            </div>
            <div class="ym-row" data-action="summarize">
              <div class="ym-row-icon">
                <svg width="14" height="10" viewBox="0 0 18 14" fill="none" style="stroke:currentColor;stroke-width:2.5;stroke-linecap:round;"><line x1="2" y1="2" x2="16" y2="2"/><line x1="2" y1="7" x2="12" y2="7"/><line x1="2" y1="12" x2="16" y2="12"/></svg>
              </div>
              <span class="ym-row-label">Summarise</span>
            </div>
            <div class="ym-row" data-action="define">
              <div class="ym-row-icon">
                 <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
              </div>
              <span class="ym-row-label">Define</span>
              <span class="ym-ai-tag">AI</span>
            </div>
            <div class="ym-sep"></div>
            <div class="ym-hide-row" id="ym-hide-btn">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
              <span class="ym-hide-label">Hide</span>
              <div class="ym-hide-arrow"><svg width="10" height="10" viewBox="0 0 16 16" fill="none"><path d="M6 12l4-4-4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
            </div>
        </div>`;
    document.body.appendChild(menu);

    const panel = document.createElement('div');
    panel.id = 'ym-panel';
    panel.innerHTML = `
        <div id="ym-panel-header">
          <div class="ym-panel-logo"><span>YM</span></div>
          <span id="ym-panel-title">Explain</span>
          <div style="display:flex; gap:6px;">
            <button class="ym-panel-btn" id="ym-back-btn" title="Back">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
            </button>
            <button class="ym-panel-btn" id="ym-close-btn" title="Close">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </div>
        </div>
        <div id="ym-selected-text"></div>
        <div id="ym-body">
          <div class="ym-dots"><div class="ym-dot"></div><div class="ym-dot"></div><div class="ym-dot"></div></div>
        </div>`;
    document.body.appendChild(panel);

    /* ── Interaction Logic ── */
    // Already defined above

    function showBubble(x, y) {
        if (hidden) return;
        bubble.style.left = Math.max(4, Math.min(x - BUBBLE_R + 12, window.innerWidth - 32)) + 'px';
        bubble.style.top = Math.max(4, Math.min(y - BUBBLE_R + 10, window.innerHeight - 32)) + 'px';
        bubble.style.display = 'flex';
    }

    function openMenu() {
        hideBubble();
        const bLeft = parseInt(bubble.style.left), bTop = parseInt(bubble.style.top);
        const menuW = 165, menuH = 165, GAP = 8;
        let left = bLeft + 32 + GAP, top = bTop + GAP;
        if (left + menuW > window.innerWidth - 12) left = bLeft - menuW - GAP;
        if (top + menuH > window.innerHeight - 12) top = bTop - menuH - GAP;
        menu.style.left = Math.max(12, left) + 'px';
        menu.style.top = Math.max(12, top) + 'px';
        menu.style.display = 'block';
    }

    menu.querySelectorAll('.ym-row').forEach(row => {
        row.addEventListener('mouseenter', () => {
            menu.querySelectorAll('.ym-row').forEach(r => r.classList.remove('ym-active'));
            row.classList.add('ym-active');
        });
        row.addEventListener('click', (e) => {
            e.preventDefault(); e.stopPropagation();
            const action = row.dataset.action;
            if (action) openPanel(action);
        });
    });

    function openPanel(action) {
        hideMenu();
        const labels = { explain: 'Explain', summarize: 'Summarise', define: 'Define' };
        document.getElementById('ym-panel-title').textContent = labels[action] || 'Assistant';
        const txt = (currentText || lastText || '').trim();
        const selEl = document.getElementById('ym-selected-text');
        if (txt) {
            selEl.textContent = '"' + (txt.length > 100 ? txt.substring(0, 97) + '...' : txt) + '"';
            selEl.style.display = 'block';
            runAction(action, txt);
        } else {
            selEl.style.display = 'none';
            document.getElementById('ym-body').innerHTML = '<div class="ym-result-card">No text selected.</div>';
        }
        panel.style.display = 'flex';
        panelOpen = true;
    }

    async function runAction(action, text) {
        const body = document.getElementById('ym-body');
        body.innerHTML = '<div class="ym-dots"><div class="ym-dot"></div><div class="ym-dot"></div><div class="ym-dot"></div></div>';
        const cacheKey = action + '::' + text.slice(0, 150);
        const cached = getCache(cacheKey);
        if (cached) { renderReply(cached); return; }

        try {
            const res = await fetch('/api/contextual-ai', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selected_text: text, action, user_profile: await getSafeProfile() })
            });
            if (res.ok) {
                const d = await res.json();
                setCache(cacheKey, d.reply);
                renderReply(d.reply);
            } else throw Error();
        } catch (e) {
            body.innerHTML = '<div class="ym-result-card" style="color:#f87171;">Request failed.</div>';
        }
    }

    function renderReply(text) {
        const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        document.getElementById('ym-body').innerHTML = `<div class="ym-result-card"><div class="ym-result-text">${esc(text)}</div></div>`;
    }

    async function getSafeProfile() {
        if (safeProfCache) return safeProfCache;
        try { const res = await fetch('/api/profile'); if (res.ok) safeProfCache = await res.json(); } catch (e) {}
        return safeProfCache || {};
    }

    document.getElementById('ym-back-btn').addEventListener('click', e => { e.stopPropagation(); hidePanel(); openMenu(); });
    document.getElementById('ym-close-btn').addEventListener('click', e => { e.stopPropagation(); hideAll(); });
    document.getElementById('ym-hide-btn').addEventListener('click', e => { e.stopPropagation(); hideAll(); hidden = true; });

    /* ── Draggable Implementation ── */
    function makeDraggable(el, handle) {
        let dragging = false, ox = 0, oy = 0;
        handle.addEventListener('mousedown', e => {
            if (e.target.tagName === 'INPUT' || e.target.closest('button')) return;
            dragging = true; const r = el.getBoundingClientRect();
            ox = e.clientX - r.left; oy = e.clientY - r.top;
            handle.style.cursor = 'grabbing'; e.preventDefault();
        });
        document.addEventListener('mousemove', e => {
            if (!dragging) return;
            el.style.left = Math.max(0, Math.min(e.clientX - ox, window.innerWidth - el.offsetWidth)) + 'px';
            el.style.top = Math.max(0, Math.min(e.clientY - oy, window.innerHeight - el.offsetHeight)) + 'px';
            el.style.right = 'auto'; el.style.bottom = 'auto';
        });
        document.addEventListener('mouseup', () => { dragging = false; handle.style.cursor = 'move'; });
    }
    makeDraggable(panel, document.getElementById('ym-panel-header'));
    makeDraggable(menu, menu.querySelector('.ym-menu-header'));

    document.getElementById('ym-ask-input').addEventListener('keydown', e => {
        if (e.key === 'Enter') { const v = e.target.value.trim(); if (v) { currentText = v; openPanel('explain'); } }
    });

    document.addEventListener('mouseup', e => {
        if (bubble.contains(e.target) || menu.contains(e.target) || panel.contains(e.target)) return;
        setTimeout(() => {
            const sel = window.getSelection(), txt = (sel ? sel.toString() : '').trim();
            if (txt.length >= SEL_MIN) {
                currentText = txt; lastText = txt; if (hidden) return;
                const r = sel.getRangeAt(0).getClientRects()[0];
                if (r) showBubble(r.right, r.bottom);
            } else {
                currentText = ''; if (!panelOpen) hideBubble();
                hideMenu();
            }
        }, 30);
    });

    document.addEventListener('mousedown', e => {
        if (!bubble.contains(e.target) && !menu.contains(e.target) && !panel.contains(e.target)) {
            hideMenu(); if (!panelOpen) { const s = window.getSelection(); if (!s || !s.toString().trim()) hideBubble(); }
        }
    });

    bubble.addEventListener('click', e => { e.stopPropagation(); openMenu(); });
})();
