/**
 * ╔══════════════════════════════════════════════════════════════════════════╗
 * ║  YOJANAMITRA — CONTEXTUAL AI ASSISTANT (Task 7)                        ║
 * ║  Text-selection popup with dynamic AI-powered actions                  ║
 * ║                                                                         ║
 * ║  Features:                                                              ║
 * ║  • Detects text selection on page                                      ║
 * ║  • Shows floating popup with: Ask, Explain, Summarize, Eligibility     ║
 * ║  • Sends sanitized user profile (no PII) to backend                    ║
 * ║  • Context-aware responses grounded in selected text                   ║
 * ╚══════════════════════════════════════════════════════════════════════════╝
 */

(function () {
  'use strict';

  // ── Configuration ────────────────────────────────────────────────────────
  const CONFIG = {
    API_ENDPOINT:     '/api/contextual-assist',
    MIN_SELECTION:    15,    // Minimum chars to trigger popup
    POPUP_DELAY:      200,   // ms delay before showing popup
    POPUP_OFFSET_Y:   12,    // px above selection
    MAX_CONTEXT:      800,   // Max chars sent to AI from selected text
    TRANSITION_MS:    180,
    IDLE_HIDE_MS:     8000,  // Auto-hide after inactivity
  };

  // ── State ─────────────────────────────────────────────────────────────────
  let _popup       = null;
  let _responseBox = null;
  let _selectedTxt = '';
  let _hideTimer   = null;
  let _showTimer   = null;
  let _isOpen      = false;
  let _isLoading   = false;

  // ── Helpers ───────────────────────────────────────────────────────────────

  function getSanitizedProfile() {
    /**
     * Build a privacy-safe profile from the global currentUser if available.
     * NEVER includes: name, email, phone, aadhaar, PAN, DOB, address, IDs.
     */
    const ALLOWED_KEYS = [
      'age', 'gender', 'state', 'district', 'residence',
      'education', 'highest_education_level', 'caste',
      'income', 'annual_family_income', 'is_bpl', 'ration_card_type',
      'is_farmer', 'is_student', 'disability', 'disability_percentage',
      'is_widow_single_woman', 'is_senior_citizen', 'is_orphan',
      'is_tribal', 'minority_status', 'marital_status',
      'occupation', 'employment_status',
      'bank_account_available', 'aadhaar_available',
      'land_size_acres', 'income_certificate_available',
    ];

    const BLOCKED_KEYS = [
      'name', 'email', 'mobile', 'phone', 'aadhaar', 'aadhaarNumber',
      'pan', 'panNumber', 'voterId', 'passport', 'bankAccountNumber',
      'ifsc', 'id', 'userId', 'dob', 'dateOfBirth', 'address',
      'aadhaarLinkedBank', 'mobileLinkedBank',
    ];

    const raw = (window.currentUser && window.currentUser.profile)
      ? window.currentUser.profile
      : (window._userProfile || {});

    const safe = {};
    for (const [k, v] of Object.entries(raw)) {
      if (BLOCKED_KEYS.includes(k) || BLOCKED_KEYS.includes(k.toLowerCase())) continue;
      if (!ALLOWED_KEYS.includes(k)) continue;
      if (v !== null && v !== undefined && v !== '') safe[k] = v;
    }
    return safe;
  }

  function clampText(txt, maxLen) {
    if (!txt) return '';
    return txt.length > maxLen ? txt.slice(0, maxLen) + '…' : txt;
  }

  // ── Popup HTML builder ────────────────────────────────────────────────────

  function buildPopup() {
    const el = document.createElement('div');
    el.id = 'ym-ctx-popup';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-label', 'YojanaMitra AI Assistant');
    el.innerHTML = `
      <div class="ym-ctx-header">
        <span class="ym-ctx-logo">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
          </svg>
          YojanaMitra AI
        </span>
        <button class="ym-ctx-close" title="Close" aria-label="Close assistant">×</button>
      </div>

      <div class="ym-ctx-actions" id="ym-ctx-actions">
        <button class="ym-ctx-btn" data-action="explain"    title="Explain this in simple language">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
          Explain
        </button>
        <button class="ym-ctx-btn" data-action="summarize"  title="Summarize key points">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>
          Summarize
        </button>
        <button class="ym-ctx-btn ym-ctx-btn--eligibility" data-action="eligibility" title="Check your eligibility">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          Check Eligibility
        </button>
        <button class="ym-ctx-btn" data-action="ask"        title="Ask a question about this">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3M12 17h.01"/></svg>
          Ask
        </button>
      </div>

      <div class="ym-ctx-ask-row" id="ym-ctx-ask-row" style="display:none">
        <input type="text" id="ym-ctx-question" placeholder="What would you like to know?" maxlength="200" />
        <button id="ym-ctx-ask-submit">→</button>
      </div>

      <div class="ym-ctx-response" id="ym-ctx-response" style="display:none">
        <div class="ym-ctx-response-inner" id="ym-ctx-response-inner"></div>
      </div>
    `;

    // Inject styles
    injectStyles();

    document.body.appendChild(el);
    return el;
  }

  function injectStyles() {
    if (document.getElementById('ym-ctx-styles')) return;
    const style = document.createElement('style');
    style.id = 'ym-ctx-styles';
    style.textContent = `
      #ym-ctx-popup {
        position: fixed;
        z-index: 999999;
        background: #ffffff;
        border: 1px solid #e2e5f0;
        border-radius: 14px;
        box-shadow: 0 8px 32px rgba(30, 30, 80, 0.14), 0 2px 8px rgba(0,0,0,0.07);
        width: 320px;
        font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
        font-size: 13.5px;
        color: #1a1a2e;
        opacity: 0;
        transform: translateY(6px) scale(0.97);
        transition: opacity 0.18s ease, transform 0.18s ease;
        pointer-events: none;
        overflow: hidden;
      }
      #ym-ctx-popup.ym-ctx-visible {
        opacity: 1;
        transform: translateY(0) scale(1);
        pointer-events: all;
      }
      .ym-ctx-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 14px 8px;
        border-bottom: 1px solid #f0f2f8;
        background: linear-gradient(135deg, #f5f6ff 0%, #ffffff 100%);
      }
      .ym-ctx-logo {
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 700;
        font-size: 12px;
        letter-spacing: 0.02em;
        color: #5560f5;
      }
      .ym-ctx-close {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 18px;
        line-height: 1;
        color: #9099b4;
        padding: 2px 4px;
        border-radius: 4px;
        transition: color 0.15s, background 0.15s;
      }
      .ym-ctx-close:hover { color: #444; background: #f0f2f8; }

      .ym-ctx-actions {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        padding: 10px 12px;
      }
      .ym-ctx-btn {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 6px 11px;
        border-radius: 8px;
        border: 1.5px solid #e4e6f0;
        background: #fff;
        color: #3a4060;
        font-size: 12.5px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s;
        font-family: inherit;
        white-space: nowrap;
      }
      .ym-ctx-btn:hover {
        background: #f0f2ff;
        border-color: #5560f5;
        color: #5560f5;
      }
      .ym-ctx-btn--eligibility {
        background: #5560f5;
        color: #fff;
        border-color: #5560f5;
      }
      .ym-ctx-btn--eligibility:hover {
        background: #3d47d4;
        border-color: #3d47d4;
        color: #fff;
      }
      .ym-ctx-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .ym-ctx-ask-row {
        display: flex;
        gap: 6px;
        padding: 0 12px 10px;
        align-items: center;
      }
      #ym-ctx-question {
        flex: 1;
        border: 1.5px solid #e0e3f0;
        border-radius: 8px;
        padding: 7px 10px;
        font-size: 12.5px;
        font-family: inherit;
        outline: none;
        color: #222;
        transition: border-color 0.15s;
      }
      #ym-ctx-question:focus { border-color: #5560f5; }
      #ym-ctx-ask-submit {
        background: #5560f5;
        color: #fff;
        border: none;
        border-radius: 8px;
        width: 32px;
        height: 32px;
        cursor: pointer;
        font-size: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.15s;
        flex-shrink: 0;
        font-family: inherit;
      }
      #ym-ctx-ask-submit:hover { background: #3d47d4; }

      .ym-ctx-response {
        border-top: 1px solid #f0f2f8;
        max-height: 220px;
        overflow-y: auto;
      }
      .ym-ctx-response-inner {
        padding: 12px 14px;
        font-size: 13px;
        line-height: 1.55;
        color: #2a2d3e;
        white-space: pre-wrap;
        word-break: break-word;
      }
      .ym-ctx-loading {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #7880a4;
        font-size: 12.5px;
        padding: 12px 14px;
      }
      .ym-ctx-spinner {
        width: 14px; height: 14px;
        border: 2px solid #e0e3f0;
        border-top-color: #5560f5;
        border-radius: 50%;
        animation: ym-spin 0.7s linear infinite;
        flex-shrink: 0;
      }
      @keyframes ym-spin { to { transform: rotate(360deg); } }

      .ym-ctx-verdict {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 8px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 8px;
      }
      .ym-ctx-verdict--eligible    { background: #dcfce7; color: #15803d; }
      .ym-ctx-verdict--not-eligible { background: #fee2e2; color: #b91c1c; }
      .ym-ctx-verdict--possibly     { background: #fef9c3; color: #854d0e; }

      .ym-ctx-no-profile {
        font-size: 12px;
        color: #7880a4;
        padding: 10px 14px;
        border-top: 1px solid #f0f2f8;
        line-height: 1.4;
      }
      .ym-ctx-no-profile a {
        color: #5560f5;
        text-decoration: underline;
        cursor: pointer;
      }
    `;
    document.head.appendChild(style);
  }

  // ── Popup positioning ─────────────────────────────────────────────────────

  function positionPopup(rect) {
    const popup   = _popup;
    const vw      = window.innerWidth;
    const vh      = window.innerHeight;
    const pWidth  = 320;
    const pHeight = popup.offsetHeight || 140;

    let top  = rect.top  + window.scrollY - pHeight - CONFIG.POPUP_OFFSET_Y;
    let left = rect.left + window.scrollX + (rect.width / 2) - (pWidth / 2);

    // Flip below selection if not enough room above
    if (top < window.scrollY + 10) {
      top = rect.bottom + window.scrollY + CONFIG.POPUP_OFFSET_Y;
    }

    // Clamp horizontally
    left = Math.max(8, Math.min(left, vw - pWidth - 8));

    popup.style.top  = `${top}px`;
    popup.style.left = `${left}px`;
  }

  // ── Show/hide ─────────────────────────────────────────────────────────────

  function showPopup(selectedText, selectionRect) {
    if (!_popup) _popup = buildPopup();

    _selectedTxt = clampText(selectedText.trim(), CONFIG.MAX_CONTEXT);

    // Reset state
    resetPopupState();

    _popup.classList.add('ym-ctx-visible');
    positionPopup(selectionRect);
    _isOpen = true;

    // Auto-hide
    resetHideTimer();
  }

  function hidePopup() {
    if (!_popup) return;
    _popup.classList.remove('ym-ctx-visible');
    _isOpen = false;
    clearTimeout(_hideTimer);
    clearTimeout(_showTimer);
  }

  function resetPopupState() {
    const responseEl  = _popup.querySelector('#ym-ctx-response');
    const askRow      = _popup.querySelector('#ym-ctx-ask-row');
    const questionEl  = _popup.querySelector('#ym-ctx-question');
    responseEl.style.display = 'none';
    askRow.style.display     = 'none';
    if (questionEl) questionEl.value = '';
    _isLoading = false;
    enableButtons();
  }

  function resetHideTimer() {
    clearTimeout(_hideTimer);
    _hideTimer = setTimeout(hidePopup, CONFIG.IDLE_HIDE_MS);
  }

  // ── API call ──────────────────────────────────────────────────────────────

  async function callAssistant(action, question = '') {
    if (_isLoading) return;
    _isLoading = true;
    disableButtons();

    const responseEl = _popup.querySelector('#ym-ctx-response');
    const innerEl    = _popup.querySelector('#ym-ctx-response-inner');

    responseEl.style.display = 'block';
    innerEl.innerHTML = `
      <div class="ym-ctx-loading">
        <div class="ym-ctx-spinner"></div>
        <span>${getLoadingMessage(action)}</span>
      </div>
    `;

    try {
      const payload = {
        selected_text:  _selectedTxt,
        user_action:    action,
        question:       question,
        user_profile:   getSanitizedProfile(),
      };

      const res = await fetch(CONFIG.API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || 'Request failed');
      }

      renderResponse(action, data);

    } catch (err) {
      innerEl.innerHTML = `
        <span style="color:#c0392b;">⚠ ${escapeHtml(err.message || 'Something went wrong. Please try again.')}</span>
      `;
    } finally {
      _isLoading = false;
      enableButtons();
      resetHideTimer();
    }
  }

  function renderResponse(action, data) {
    const innerEl = _popup.querySelector('#ym-ctx-response-inner');
    clearTimeout(_hideTimer);  // Keep open while response is visible

    if (action === 'eligibility') {
      innerEl.innerHTML = renderEligibilityResponse(data);
    } else {
      const text = data.response || data.message || 'No response received.';
      innerEl.innerHTML = `<span>${escapeHtml(text)}</span>`;
    }
  }

  function renderEligibilityResponse(data) {
    const verdict  = (data.verdict || 'UNKNOWN').toUpperCase();
    const reason   = data.reasoning || data.response || '';
    const factors  = data.key_factors || [];

    const verdictClass = verdict === 'ELIGIBLE' || verdict === 'FULLY_ELIGIBLE'
      ? 'eligible'
      : verdict === 'NOT_ELIGIBLE'
      ? 'not-eligible'
      : 'possibly';

    const verdictText = verdict === 'ELIGIBLE' || verdict === 'FULLY_ELIGIBLE'
      ? '✓ Likely Eligible'
      : verdict === 'NOT_ELIGIBLE'
      ? '✗ Not Eligible'
      : '⚠ Possibly Eligible';

    let html = `
      <div class="ym-ctx-verdict ym-ctx-verdict--${verdictClass}">${verdictText}</div>
      <div>${escapeHtml(reason)}</div>
    `;

    if (factors.length) {
      html += `<div style="margin-top:8px;font-size:12px;color:#6b7280;">`;
      for (const f of factors.slice(0, 3)) {
        html += `<div style="margin-top:4px;">• ${escapeHtml(f)}</div>`;
      }
      html += `</div>`;
    }

    // Profile warning
    const profile = getSanitizedProfile();
    if (Object.keys(profile).length < 3) {
      html += `
        <div class="ym-ctx-no-profile">
          <strong>Tip:</strong> For accurate results, 
          <a onclick="document.querySelector('[data-section=profile]')?.click(); hideYMAssistant();">
            complete your profile
          </a> first.
        </div>
      `;
    }

    return html;
  }

  // ── Button state helpers ──────────────────────────────────────────────────

  function disableButtons() {
    if (!_popup) return;
    _popup.querySelectorAll('.ym-ctx-btn, #ym-ctx-ask-submit').forEach(b => {
      b.disabled = true;
    });
  }

  function enableButtons() {
    if (!_popup) return;
    _popup.querySelectorAll('.ym-ctx-btn, #ym-ctx-ask-submit').forEach(b => {
      b.disabled = false;
    });
  }

  // ── Event wiring ──────────────────────────────────────────────────────────

  function wirePopupEvents() {
    if (!_popup) return;

    // Close button
    _popup.querySelector('.ym-ctx-close').addEventListener('click', hidePopup);

    // Action buttons
    _popup.querySelectorAll('.ym-ctx-btn[data-action]').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.action;

        if (action === 'ask') {
          const askRow = _popup.querySelector('#ym-ctx-ask-row');
          const vis = askRow.style.display !== 'none';
          askRow.style.display = vis ? 'none' : 'flex';
          if (!vis) _popup.querySelector('#ym-ctx-question').focus();
        } else {
          callAssistant(action);
        }

        resetHideTimer();
      });
    });

    // Ask submit button
    const askSubmit = _popup.querySelector('#ym-ctx-ask-submit');
    const questionInput = _popup.querySelector('#ym-ctx-question');

    askSubmit.addEventListener('click', () => {
      const q = questionInput.value.trim();
      if (q) callAssistant('ask', q);
    });

    questionInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = questionInput.value.trim();
        if (q) callAssistant('ask', q);
      }
    });

    // Keep popup open on hover
    _popup.addEventListener('mouseenter', () => clearTimeout(_hideTimer));
    _popup.addEventListener('mouseleave', resetHideTimer);
  }

  // ── Document-level selection detection ───────────────────────────────────

  function onMouseUp(e) {
    // Ignore clicks inside the popup itself
    if (_popup && _popup.contains(e.target)) return;

    clearTimeout(_showTimer);
    _showTimer = setTimeout(() => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) {
        if (_isOpen && !_popup?.contains(e.target)) hidePopup();
        return;
      }

      const text = selection.toString().trim();
      if (text.length < CONFIG.MIN_SELECTION) {
        if (_isOpen && !_popup?.contains(e.target)) hidePopup();
        return;
      }

      // Get bounding rect of selection
      const range = selection.getRangeAt(0);
      const rect  = range.getBoundingClientRect();

      if (!_popup) {
        _popup = buildPopup();
        wirePopupEvents();
      }

      showPopup(text, rect);
    }, CONFIG.POPUP_DELAY);
  }

  function onKeyUp(e) {
    if (e.key === 'Escape') {
      hidePopup();
      return;
    }

    // Keyboard text selection (Shift + arrow keys)
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;
    const text = selection.toString().trim();
    if (text.length < CONFIG.MIN_SELECTION) return;

    clearTimeout(_showTimer);
    _showTimer = setTimeout(() => {
      const range = selection.getRangeAt(0);
      const rect  = range.getBoundingClientRect();
      if (!_popup) {
        _popup = buildPopup();
        wirePopupEvents();
      }
      showPopup(text, rect);
    }, CONFIG.POPUP_DELAY);
  }

  // ── Utility ───────────────────────────────────────────────────────────────

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function getLoadingMessage(action) {
    const msgs = {
      explain:     'Explaining…',
      summarize:   'Summarizing…',
      eligibility: 'Checking eligibility…',
      ask:         'Thinking…',
    };
    return msgs[action] || 'Processing…';
  }

  // ── Public API ────────────────────────────────────────────────────────────

  window.hideYMAssistant = hidePopup;
  window.showYMAssistant = showPopup;

  // ── Init ──────────────────────────────────────────────────────────────────

  function init() {
    document.addEventListener('mouseup', onMouseUp, { passive: true });
    document.addEventListener('keyup',   onKeyUp,   { passive: true });

    // Handle scroll — reposition popup if open
    window.addEventListener('scroll', () => {
      if (!_isOpen || !_popup) return;
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) return;
      try {
        const rect = selection.getRangeAt(0).getBoundingClientRect();
        positionPopup(rect);
      } catch (_) { /* Selection may have been cleared */ }
    }, { passive: true });

    // Ensure popup is closed when navigating within SPA
    document.addEventListener('click', (e) => {
      if (!_isOpen || !_popup) return;
      if (_popup.contains(e.target)) return;
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) hidePopup();
    });
  }

  // Wait for DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
