/**
 * YojanaMitra — Contextual AI Assistant
 * Sitewide. Include on any page — inlined or as an external file.
 *
 * Behaviour:
 *  1. User selects text (≥5 chars) → YM bubble appears pinned to the
 *     bottom-right corner of the selection strip (circle edge touches corner).
 *  2. Clicking bubble opens action menu (Explain / Summarise / Define
 *     / Ask anything… / Hide).
 *  3. Choosing an action sends selected text + sanitized profile to
 *     POST /api/contextual-ai and shows the response in a draggable dark panel.
 *  4. Hide dismisses everything; next selection re-triggers from step 1.
 *  5. ESC closes everything at any stage.
 */

(function () {
  'use strict';

  /* ── constants ─────────────────────────────────────────────────── */
  const SEL_MIN     = 5;      // minimum chars to trigger
  const DEBOUNCE_MS = 280;
  const BUBBLE_R    = 14;     // radius px — half of 28px diameter (30% smaller than 38px)

  /* ── state ──────────────────────────────────────────────────────── */
  let currentText   = '';
  let lastText      = '';
  let panelOpen     = false;
  let hidden        = false;  // user pressed Hide — suppress until new selection
  let debTimer      = null;
  let safeProfCache = null;
  // Persistent AI response cache — survives page refresh
  const AI_CACHE_KEY = 'ym_ai_cache';
  const AI_CACHE_MAX = 120;  // max entries before pruning oldest

  function _loadAICache() {
    try { return JSON.parse(localStorage.getItem(AI_CACHE_KEY) || '{}'); }
    catch(e) { return {}; }
  }
  function _saveAICache(cache) {
    try { localStorage.setItem(AI_CACHE_KEY, JSON.stringify(cache)); }
    catch(e) {}
  }
  function getCachedResponse(key) {
    const cache = _loadAICache();
    const entry = cache[key];
    if (!entry) return null;
    return entry.reply;
  }
  function setCachedResponse(key, reply) {
    const cache = _loadAICache();
    cache[key] = { reply, ts: Date.now() };
    // Prune if over limit — remove oldest entries first
    const keys = Object.keys(cache);
    if (keys.length > AI_CACHE_MAX) {
      keys.sort((a, b) => (cache[a].ts || 0) - (cache[b].ts || 0));
      keys.slice(0, keys.length - AI_CACHE_MAX).forEach(k => delete cache[k]);
    }
    _saveAICache(cache);
  }

  /* ── inject CSS ─────────────────────────────────────────────────── */
  const style = document.createElement('style');
  style.textContent = `
    #ym-ctx-bubble {
      position: fixed;
      z-index: 10001;
      width: ${BUBBLE_R * 2}px;
      height: ${BUBBLE_R * 2}px;
      border-radius: 50%;
      background: #1e293b;
      display: none;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 2px 10px rgba(0,0,0,0.30);
      transition: transform .15s, box-shadow .15s;
      user-select: none;
      pointer-events: all;
    }
    #ym-ctx-bubble:hover {
      transform: scale(1.12);
      box-shadow: 0 4px 16px rgba(0,0,0,0.38);
    }
    #ym-ctx-bubble span {
      font-size: 8px;
      font-weight: 800;
      color: #fff;
      letter-spacing: -.3px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      pointer-events: none;
    }

    #ym-ctx-menu {
      position: fixed;
      z-index: 10002;
      display: none;
      background: #1e293b;
      border-radius: 13px;
      padding: 6px;
      min-width: 218px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.32);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    .ym-menu-ask {
      background: rgba(255,255,255,.07);
      border-radius: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 11px;
      margin-bottom: 4px;
    }
    .ym-menu-ask input {
      background: transparent;
      border: none;
      outline: none;
      font-size: 12.5px;
      color: #94a3b8;
      width: 100%;
      font-family: inherit;
    }
    .ym-menu-ask input::placeholder { color: #4b5563; }
    .ym-menu-row {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 11px;
      border-radius: 8px;
      cursor: pointer;
      transition: background .1s;
    }
    .ym-menu-row:hover { background: rgba(255,255,255,.08); }
    .ym-menu-row span  { font-size: 13px; color: #e2e8f0; font-weight: 500; }
    .ym-menu-row.hide-row span { font-size: 12.5px; color: #64748b; }
    .ym-menu-sep {
      height: 1px;
      background: rgba(255,255,255,.07);
      margin: 4px 6px;
    }
    .ym-ai-badge {
      margin-left: auto;
      font-size: 10px;
      background: rgba(74,222,128,.12);
      color: #4ade80;
      padding: 2px 8px;
      border-radius: 20px;
      font-weight: 700;
    }

    #ym-ctx-panel {
      position: fixed;
      z-index: 10003;
      top: 80px;
      right: 24px;
      width: 310px;
      display: none;
      flex-direction: column;
      background: #1e293b;
      border-radius: 14px;
      box-shadow: 0 12px 44px rgba(0,0,0,0.36);
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      max-height: calc(100vh - 100px);
    }
    #ym-panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 11px 13px 10px;
      border-bottom: 1px solid rgba(255,255,255,.07);
      cursor: grab;
      flex-shrink: 0;
    }
    #ym-panel-header:active { cursor: grabbing; }
    .ym-panel-avatar {
      width: 24px; height: 24px; border-radius: 50%;
      background: rgba(165,180,252,.15);
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    .ym-panel-avatar span {
      font-size: 8px; font-weight: 800; color: #a5b4fc;
    }
    #ym-panel-title {
      font-size: 13px; font-weight: 600; color: #e2e8f0;
    }
    .ym-icon-btn {
      width: 22px; height: 22px; border-radius: 6px;
      background: rgba(255,255,255,.06);
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; border: none; padding: 0;
      transition: background .1s;
    }
    .ym-icon-btn:hover { background: rgba(255,255,255,.13); }

    #ym-selected-chip {
      margin: 10px 12px 0;
      background: rgba(255,255,255,.05);
      border-radius: 7px;
      padding: 7px 10px;
      flex-shrink: 0;
    }
    #ym-selected-chip .chip-label {
      font-size: 9.5px; color: #475569; font-weight: 700;
      margin-bottom: 3px; letter-spacing: .05em; text-transform: uppercase;
    }
    #ym-selected-chip .chip-text {
      font-size: 11.5px; color: #64748b; line-height: 1.5; font-style: italic;
    }

    #ym-response-body {
      padding: 12px;
      overflow-y: auto;
      flex: 1;
      font-size: 13px;
      color: #cbd5e1;
      line-height: 1.65;
    }
    #ym-response-body p { margin: 0 0 8px; }
    #ym-response-body p:last-child { margin-bottom: 0; }

    .ym-spinner {
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
      padding: 44px 0; gap: 14px;
    }
    .ym-dots {
      display: flex; align-items: center; gap: 8px;
    }
    .ym-dot {
      width: 7px; height: 7px; border-radius: 50%;
      background: #a5b4fc;
      animation: ym-glow 1.2s ease-in-out infinite;
    }
    .ym-dot:nth-child(2) { animation-delay: 180ms; }
    .ym-dot:nth-child(3) { animation-delay: 360ms; }
    @keyframes ym-glow {
      0%, 100% { opacity: 0.2; transform: scale(0.85); }
      50%       { opacity: 1;   transform: scale(1.15); box-shadow: 0 0 8px rgba(165,180,252,.7); }
    }
    .ym-spinner-text { font-size: 12.5px; color: #64748b; }

    .ym-elig-row {
      padding: 6px 9px; border-radius: 6px;
      font-size: 12px; margin-bottom: 4px;
    }
    .ym-elig-pass    { background: rgba(74,222,128,.07); border-left: 2px solid #4ade80; color: #86efac; }
    .ym-elig-fail    { background: rgba(248,113,113,.07); border-left: 2px solid #f87171; color: #fca5a5; }
    .ym-elig-unknown { background: rgba(251,191,36,.07); border-left: 2px solid #fbbf24; color: #fcd34d; }
    .ym-verdict {
      padding: 8px 10px; border-radius: 8px; margin-top: 10px;
    }
    .ym-verdict-title { font-size: 12.5px; font-weight: 700; }
    .ym-verdict-reason { font-size: 11.5px; color: #64748b; margin-top: 2px; }

    #ym-panel-footer {
      display: flex; gap: 5px;
      padding: 8px 12px 11px;
      border-top: 1px solid rgba(255,255,255,.06);
      flex-shrink: 0;
    }
    .ym-footer-btn {
      flex: 1; padding: 6px 0; border-radius: 7px;
      border: 1px solid rgba(255,255,255,.1);
      background: transparent; color: #94a3b8;
      font-size: 11.5px; cursor: pointer;
      font-family: inherit; transition: all .12s;
    }
    .ym-footer-btn:hover { background: rgba(255,255,255,.07); }
    .ym-footer-btn.elig {
      border-color: rgba(74,222,128,.3);
      background: rgba(74,222,128,.06);
      color: #4ade80;
    }
    .ym-footer-btn.elig:hover { background: rgba(74,222,128,.12); }
    .ym-footer-btn.define {
      border-color: rgba(56,189,248,.3);
      background: rgba(56,189,248,.06);
      color: #38bdf8;
    }
    .ym-footer-btn.define:hover { background: rgba(56,189,248,.12); }
    .ym-footer-btn.active {
      border-color: rgba(165,180,252,.5);
      background: rgba(165,180,252,.08);
      color: #a5b4fc;
    }
  `;
  document.head.appendChild(style);

  /* ── build DOM ───────────────────────────────────────────────────── */
  // Bubble
  const bubble = document.createElement('div');
  bubble.id = 'ym-ctx-bubble';
  bubble.innerHTML = '<span>YM</span>';
  document.body.appendChild(bubble);

  // Menu
  const menu = document.createElement('div');
  menu.id = 'ym-ctx-menu';
  menu.innerHTML = `
    <div class="ym-menu-ask">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input id="ym-ask-input" type="text" placeholder="Ask anything…" />
    </div>
    <div class="ym-menu-row" data-action="explain">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
      <span>Explain</span>
    </div>
    <div class="ym-menu-row" data-action="summarize">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a5b4fc" stroke-width="2"><line x1="21" y1="10" x2="3" y2="10"/><line x1="21" y1="6" x2="3" y2="6"/><line x1="21" y1="14" x2="3" y2="14"/><line x1="14" y1="18" x2="3" y2="18"/></svg>
      <span>Summarise</span>
    </div>
    <div class="ym-menu-row" data-action="define">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#38bdf8" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
      <span>Define</span>
      <span class="ym-ai-badge" style="background:rgba(56,189,248,.15);color:#38bdf8;">AI</span>
    </div>
    <div class="ym-menu-sep"></div>
    <div class="ym-menu-row hide-row" id="ym-hide-btn">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      <span>Hide</span>
      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2" style="margin-left:auto"><polyline points="9 18 15 12 9 6"/></svg>
    </div>`;
  document.body.appendChild(menu);

  // Panel
  const panel = document.createElement('div');
  panel.id = 'ym-ctx-panel';
  panel.innerHTML = `
    <div id="ym-panel-header">
      <div style="display:flex;align-items:center;gap:8px;">
        <div class="ym-panel-avatar"><span>YM</span></div>
        <span id="ym-panel-title">AI Assistant</span>
      </div>
      <div style="display:flex;gap:5px;">
        <button class="ym-icon-btn" id="ym-back-btn" title="Back">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
        <button class="ym-icon-btn" id="ym-close-btn" title="Close">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    </div>
    <div id="ym-selected-chip">
      <div class="chip-label">Selected</div>
      <div class="chip-text" id="ym-chip-text"></div>
    </div>
    <div id="ym-response-body"></div>
    <div id="ym-panel-footer">
      <button class="ym-footer-btn"      data-action="explain">Explain</button>
      <button class="ym-footer-btn"      data-action="summarize">Summarise</button>
      <button class="ym-footer-btn define" data-action="define">Define</button>
    </div>`;
  document.body.appendChild(panel);

  /* ── helpers ─────────────────────────────────────────────────────── */
  function showBubble(x, y) {
    // x,y are viewport coords from getBoundingClientRect (no scroll offset for position:fixed)
    const vw = window.innerWidth, vh = window.innerHeight;
    let left = x - BUBBLE_R;
    let top  = y - BUBBLE_R;
    left = Math.max(4, Math.min(left, vw - BUBBLE_R * 2 - 4));
    top  = Math.max(4, Math.min(top,  vh - BUBBLE_R * 2 - 4));
    bubble.style.left    = left + 'px';
    bubble.style.top     = top  + 'px';
    bubble.style.display = 'flex';
  }

  function hideBubble()  { bubble.style.display = 'none'; }
  function hideMenu()    { menu.style.display   = 'none'; }
  function hidePanel()   { panel.style.display  = 'none'; panelOpen = false; }

  function hideAll() {
    hideBubble(); hideMenu(); hidePanel();
  }

  function openMenu() {
    hideBubble();
    const bLeft  = parseInt(bubble.style.left);
    const bTop   = parseInt(bubble.style.top);
    const bRight = bLeft + BUBBLE_R * 2;
    const bBot   = bTop  + BUBBLE_R * 2;
    const menuW  = 224, menuH = 226, GAP = 6;
    const vw = window.innerWidth, vh = window.innerHeight;

    let left = bRight + GAP;
    let top  = bBot   + GAP;

    if (left + menuW > vw - 8) left = bLeft - menuW - GAP;
    if (top  + menuH > vh - 8) top  = bTop  - menuH - GAP;

    left = Math.max(8, left);
    top  = Math.max(8, top);

    menu.style.left    = left + 'px';
    menu.style.top     = top  + 'px';
    menu.style.display = 'block';
    setTimeout(() => document.getElementById('ym-ask-input').focus(), 50);
  }

  function openPanel(action) {
    hideMenu();
    panel.style.display = 'flex';
    panelOpen = true;
    runAction(action);
  }

  /* ── safe profile ────────────────────────────────────────────────── */
  async function getSafeProfile() {
    if (safeProfCache) return safeProfCache;
    try {
      const data = await fetch('/api/user').then(r => r.json());
      const u = data.user || data;
      const p = u.profile || {};
      const age = Number(p.age) || 0;
      safeProfCache = {
        age_bracket:       age < 18 ? 'minor' : age < 26 ? '18-25' : age < 36 ? '26-35' : age < 46 ? '36-45' : age < 61 ? '46-60' : '60+',
        gender:            p.gender || '',
        state:             p.state  || '',
        district:          p.district || '',
        income_bracket:    p.incomeSlab || (p.income <= 100000 ? 'EWS' : p.income <= 300000 ? 'LIG' : p.income <= 800000 ? 'MIG' : 'HIG'),
        caste_category:    p.caste  || 'general',
        religion:          p.religion || '',
        occupation:        p.occupation || '',
        employment_status: p.employmentStatus || '',
        education_level:   p.highestEducationLevel || p.education || '',
        marital_status:    p.maritalStatus || '',
        is_farmer:         p.isFarmer === 'Yes',
        is_disabled:       p.disability === 'Yes',
        disability_bracket: !p.disabilityPercentage ? 'none' : p.disabilityPercentage < 40 ? 'below 40%' : p.disabilityPercentage < 80 ? '40-79%' : '80%+',
        is_bpl:            ['bpl','antyodaya','aay'].includes((p.rationCardType||'').toLowerCase()),
        ration_card_type:  p.rationCardType || '',
        residence:         p.residence || '',
        has_aadhaar:       p.aadhaarAvailable === 'Yes',
        has_bank_account:  p.bankAccountAvailable === 'Yes',
        is_senior:         age >= 60,
        is_minority:       p.minorityStatus === 'Yes',
      };
    } catch (e) { safeProfCache = {}; }
    return safeProfCache;
  }

  /* ── run AI action ───────────────────────────────────────────────── */
  async function runAction(action) {
    const text = currentText || lastText;
    if (!text) return;

    // Update panel header
    const titles = { explain:'Explain', summarize:'Summarise', define:'Define', ask:'Ask' };
    document.getElementById('ym-panel-title').textContent = titles[action] || 'AI Assistant';

    // Update chip preview
    document.getElementById('ym-chip-text').textContent =
      '"' + (text.length > 100 ? text.slice(0, 100) + '…' : text) + '"';

    // Highlight active footer button
    panel.querySelectorAll('.ym-footer-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.action === action);
    });

    // Cache check — persistent across sessions
    const key = action + '::' + text.slice(0, 200);
    const cached = getCachedResponse(key);
    if (cached) {
      renderResponse(cached, action);
      return;
    }

    // Show spinner
    document.getElementById('ym-response-body').innerHTML =
      '<div class="ym-spinner"><div class="ym-dots"><span class="ym-dot"></span><span class="ym-dot"></span><span class="ym-dot"></span></div><div class="ym-spinner-text">Thinking…</div></div>';

    try {
      const profile = await getSafeProfile();
      const res  = await fetch('/api/contextual-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ selected_text: text, action, user_profile: profile }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Request failed');
      setCachedResponse(key, data.reply);
      renderResponse(data.reply, action);
    } catch (e) {
      document.getElementById('ym-response-body').innerHTML =
        `<div style="padding:16px;background:rgba(248,113,113,.1);border-radius:10px;border:1px solid rgba(248,113,113,.2);">
           <div style="font-size:13px;font-weight:600;color:#fca5a5;margin-bottom:4px;">Request failed</div>
           <div style="font-size:12px;color:#64748b;">${e.message}</div>
         </div>`;
    }
  }

  function renderResponse(reply, action) {
    const body = document.getElementById('ym-response-body');
    if (action === 'define') {
      const lines = reply.split('\n');
      let html = '';
      lines.forEach(line => {
        const l = line.trim();
        if (!l) return;
        if (l.startsWith('MAIN TERM:')) {
          const term = l.slice(10).trim();
          if (term && term !== 'None') {
            html += `<div style="font-size:16px;font-weight:700;color:#38bdf8;margin-bottom:10px;">${term}</div>`;
          }
        } else if (l.startsWith('DEFINITION:')) {
          html += `<div style="font-size:13px;color:#cbd5e1;line-height:1.65;margin-bottom:10px;">${l.slice(11).trim()}</div>`;
        } else if (l.startsWith('IN CONTEXT:')) {
          const ctx = l.slice(11).trim();
          if (ctx && ctx !== 'N/A') {
            html += `<div style="padding:8px 11px;background:rgba(56,189,248,.07);border-left:2px solid #38bdf8;border-radius:0 6px 6px 0;font-size:12.5px;color:#7dd3fc;line-height:1.5;margin-bottom:12px;">${ctx}</div>`;
          }
        } else if (l.startsWith('OTHER TERMS:')) {
          html += `<div style="font-size:9.5px;font-weight:700;color:#475569;letter-spacing:.05em;text-transform:uppercase;margin-bottom:6px;">Other terms</div>`;
        } else if (l.startsWith('- ')) {
          const content = l.slice(2);
          const colonIdx = content.indexOf(':');
          const term    = colonIdx > -1 ? content.slice(0, colonIdx).trim() : content;
          const def     = colonIdx > -1 ? content.slice(colonIdx + 1).trim() : '';
          html += `<div style="padding:6px 10px;background:rgba(255,255,255,.04);border-radius:6px;margin-bottom:4px;">
            <span style="font-size:12px;font-weight:700;color:#94a3b8;">${term}</span>
            ${def ? `<span style="font-size:12px;color:#64748b;"> — ${def}</span>` : ''}
          </div>`;
        } else {
          html += `<p>${l}</p>`;
        }
      });
      body.innerHTML = `<div style="display:flex;flex-direction:column;gap:0;">${html}</div>`;
    } else {
      // Plain text — preserve paragraphs
      const paras = reply.split(/\n\n+/).filter(Boolean);
      body.innerHTML = paras.map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
    }
  }

  /* ── get selection bottom-right corner ──────────────────────────── */
  function getSelectionCorner() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return null;
    const range  = sel.getRangeAt(0);
    const rects  = range.getClientRects();
    if (!rects || rects.length === 0) return null;
    // Last rect = last line of multi-line selection
    const last = rects[rects.length - 1];
    return {
      x: last.right,   // pure viewport coords — no scroll offset needed for position:fixed
      y: last.bottom,
    };
  }

  /* ── text selection detection ────────────────────────────────────── */
  document.addEventListener('mouseup', function (e) {
    if (bubble.contains(e.target) || menu.contains(e.target) || panel.contains(e.target)) return;

    // Capture selection IMMEDIATELY before debounce delay can clear it
    const sel    = window.getSelection();
    const text   = sel ? sel.toString().trim() : '';
    const corner = (text.length >= SEL_MIN) ? getSelectionCorner() : null;

    clearTimeout(debTimer);
    debTimer = setTimeout(() => {
      if (text.length >= SEL_MIN && corner) {
        currentText = text;
        lastText    = text;
        hidden      = false;   // any new valid selection always re-enables
        showBubble(corner.x, corner.y);
        hideMenu();
      } else if (!hidden) {
        hideBubble();
        hideMenu();
        currentText = '';
      }
    }, DEBOUNCE_MS);
  });

  /* ── bubble click → open menu ────────────────────────────────────── */
  bubble.addEventListener('click', function (e) {
    e.stopPropagation();
    openMenu();
  });

  /* ── menu row clicks ─────────────────────────────────────────────── */
  menu.querySelectorAll('.ym-menu-row[data-action]').forEach(row => {
    row.addEventListener('click', function (e) {
      e.stopPropagation();
      openPanel(this.dataset.action);
    });
  });

  // Ask input — submit on Enter
  document.getElementById('ym-ask-input').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && this.value.trim()) {
      currentText = this.value.trim() + ' (context: ' + (lastText.slice(0, 120) || 'selected text') + ')';
      this.value = '';
      openPanel('ask');
    }
  });

  // Hide
  document.getElementById('ym-hide-btn').addEventListener('click', function (e) {
    e.stopPropagation();
    hidden = true;
    hideAll();
  });

  /* ── panel controls ──────────────────────────────────────────────── */
  document.getElementById('ym-back-btn').addEventListener('click', function (e) {
    e.stopPropagation();
    hidePanel();
    openMenu();
  });
  document.getElementById('ym-close-btn').addEventListener('click', function (e) {
    e.stopPropagation();
    hideAll();
    hidden = true;
  });

  // Footer action buttons
  panel.querySelectorAll('.ym-footer-btn[data-action]').forEach(btn => {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      runAction(this.dataset.action);
    });
  });

  /* ── click outside → dismiss menu (not panel) ────────────────────── */
  document.addEventListener('mousedown', function (e) {
    if (!bubble.contains(e.target) && !menu.contains(e.target) && !panel.contains(e.target)) {
      hideMenu();
    }
  });

  /* ── ESC closes everything ───────────────────────────────────────── */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') {
      if (panelOpen) { hidePanel(); }
      else { hideAll(); hidden = true; }
    }
  });

  /* ── draggable panel ─────────────────────────────────────────────── */
  const header = document.getElementById('ym-panel-header');
  let dragging = false, dragOX = 0, dragOY = 0;

  header.addEventListener('mousedown', function (e) {
    dragging = true;
    const r = panel.getBoundingClientRect();
    dragOX = e.clientX - r.left;
    dragOY = e.clientY - r.top;
    header.style.cursor = 'grabbing';
    e.preventDefault();
  });
  document.addEventListener('mousemove', function (e) {
    if (!dragging) return;
    const vw = window.innerWidth, vh = window.innerHeight;
    const pw = panel.offsetWidth,  ph = panel.offsetHeight;
    let newLeft = e.clientX - dragOX;
    let newTop  = e.clientY - dragOY;
    newLeft = Math.max(0, Math.min(newLeft, vw - pw));
    newTop  = Math.max(0, Math.min(newTop,  vh - ph));
    panel.style.left   = newLeft + 'px';
    panel.style.top    = newTop  + 'px';
    panel.style.right  = 'auto';
    panel.style.bottom = 'auto';
  });
  document.addEventListener('mouseup', function () {
    if (dragging) { dragging = false; header.style.cursor = 'grab'; }
  });

  /* ── pre-warm profile cache ──────────────────────────────────────── */
  getSafeProfile();

})();