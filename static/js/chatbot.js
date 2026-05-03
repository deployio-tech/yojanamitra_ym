/**
 * YojanaMitra Global Chatbot JS
 * Automatically injects the chatbot UI and handles messaging logic.
 */

(function () {
    // 1. Inject CSS for portability
    const chatbotStyles = `
    .chatbot-fab-container {
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 100000;
        pointer-events: none;
    }
    .chatbot-bubble {
        position: absolute;
        bottom: 70px;
        right: 36px;
        background: #0c0a1c;
        padding: 16px 36px 16px 18px;
        border-radius: 14px 14px 0 14px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        width: 210px;
        pointer-events: auto;
        cursor: pointer;
        animation: chatBubbleIn 0.3s ease-out;
    }
    .chatbot-bubble::after {
        content: '';
        position: absolute;
        bottom: -13px;
        right: -1px;
        width: 0;
        height: 0;
        border-left: 15px solid transparent;
        border-top: 14px solid #0c0a1c;
    }
    .chatbot-bubble .close-btn {
        position: absolute;
        top: 10px;
        right: 12px;
        font-size: 15px;
        color: #bbb;
        cursor: pointer;
        background: none;
        border: none;
        padding: 0;
        line-height: 1;
    }
    .chatbot-bubble .close-btn:hover { color: #888; }
    .chatbot-bubble h6 { margin: 0; font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 6px; }
    .chatbot-bubble p { margin: 0; font-size: 13px; color: rgba(255, 255, 255, 0.6); line-height: 1.55; }

    .chat-toggle-btn {
        width: 54px;
        height: 54px;
        border-radius: 50%;
        background: #0c0a1c;
        color: white;
        border: 1px solid rgba(139, 92, 246, 0.5);
        box-shadow: 0 4px 14px rgba(109, 40, 217, 0.4);
        cursor: pointer;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        pointer-events: auto;
        outline: none;
    }
    .chat-toggle-btn:hover { transform: scale(1.06); box-shadow: 0 6px 18px rgba(26, 86, 219, 0.45); }
    .chat-toggle-btn:active { transform: scale(0.97); }
    
    @keyframes chatBubbleIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .chatbox {
        position: fixed;
        bottom: 100px;
        right: 30px;
        width: 360px;
        height: 500px;
        max-height: 80vh;
        background: #0c0a1c;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.65), inset 0 0 0 1px rgba(255, 255, 255, 0.04);
        z-index: 100001;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }
    .chat-header { background: rgba(255, 255, 255, 0.03); border-bottom: 1px solid rgba(255, 255, 255, 0.06); color: white; padding: 1rem 1.25rem; display: flex; justify-content: space-between; align-items: center; font-weight: 700; }
    .chat-messages { flex-grow: 1; padding: 1rem; overflow-y: auto; background: transparent; display: flex; flex-direction: column; gap: 10px; }
    .message { padding: 0.75rem 1rem; border-radius: 12px; max-width: 85%; font-size: 13px; line-height: 1.5; }
    .message.bot { background: rgba(255, 255, 255, 0.04); color: #e4e4e7; border-bottom-left-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.08); align-self: flex-start; }
    .message.user { background: linear-gradient(135deg, rgba(109, 40, 217, 0.9), rgba(76, 29, 149, 0.9)); color: white; border-bottom-right-radius: 4px; align-self: flex-end; box-shadow: 0 4px 12px rgba(109, 40, 217, 0.2); }
    .chat-input-area { padding: 0.75rem; border-top: 1px solid rgba(255, 255, 255, 0.06); background: rgba(255, 255, 255, 0.02); }
    .chat-input-area .input-group { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 4px; display: flex; align-items: center; }
    .chat-input-area input { border: none; background: transparent; padding: 8px 12px; flex-grow: 1; outline: none; font-size: 13px; color: white; box-shadow: none !important; }
    .chat-input-area input::placeholder { color: rgba(255, 255, 255, 0.4); }
    .chat-header button { 
        background: transparent !important; 
        border: none !important; 
        color: white !important; 
        opacity: 0.8; 
        transition: opacity 0.2s; 
        box-shadow: none !important;
    }
    .chat-header button:hover { opacity: 1; background: transparent !important; }
    .chat-input-area button { width: 36px; height: 36px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 10px; background: rgba(139, 92, 246, 0.8); color: white; border: none; transition: background 0.2s; }
    .chat-input-area button:hover { background: rgba(139, 92, 246, 1); }
    .ym-chat-dots { display: inline-flex; align-items: center; gap: 5px; padding: 2px 0; }
    .ym-chat-dots span { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #94a3b8; animation: ym-chat-glow 1.2s ease-in-out infinite; }
    .ym-chat-dots span:nth-child(2) { animation-delay: 180ms; }
    .ym-chat-dots span:nth-child(3) { animation-delay: 360ms; }
    @keyframes ym-chat-glow { 0%,100% { opacity:.25; transform:scale(.85); } 50% { opacity:1; transform:scale(1.15); } }
    

    const styleSheet = document.createElement("style");
    styleSheet.innerText = chatbotStyles;
    document.head.appendChild(styleSheet);

    // 2. Inject HTML
    const path = window.location.pathname;
    const isDashboard = path.endsWith('dashboard') || path.endsWith('dashboard.html') || path.includes('/dashboard');
    
    let chatbotHTML = 
    '<div class="chatbot-fab-container">' +
    '    <!-- Round button with headset icon -->' +
    '    <button class="chat-toggle-btn" onclick="toggleChat()" title="Ask YojanaMitra AI">' +
    '        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">' +
    '            <path d="M5 10a7 7 0 0 1 14 0" stroke="white" stroke-width="1.9" stroke-linecap="round"/>' +
    '            <rect x="3" y="10" width="3.5" height="5.5" rx="1.5" fill="white"/>' +
    '            <rect x="17.5" y="10" width="3.5" height="5.5" rx="1.5" fill="white"/>' +
    '            <path d="M21 16c0 2-1.5 3.5-3.5 3.5H13" stroke="white" stroke-width="1.9" stroke-linecap="round"/>' +
    '            <circle cx="12" cy="19.5" r="1.2" fill="white"/>' +
    '        </svg>' +
    '    </button>';

    // Only add bubble if not on dashboard
    if (!isDashboard) {
        chatbotHTML += 
        '<!-- Tooltip -->' +
        '<div class="chatbot-bubble" id="chatbot-bubble" onclick="toggleChat()">' +
        '    <button class="close-btn" onclick="event.stopPropagation(); document.getElementById(\'chatbot-bubble\').style.display=\'none\'">×</button>' +
        '    <h6>Ask YojanaMitra AI</h6>' +
        '    <p>Ask me about schemes you qualify for.</p>' +
        '</div>';
    }

    chatbotHTML += 
    '</div>' +
    '<div id="chatbox" class="chatbox" style="display:none;">' +
    '    <div class="chat-header">' +
    '        <span><i class="fas fa-headset me-2"></i>YojanaMitra AI</span>' +
    '        <button onclick="toggleChat()" title="Close Chat">' +
    '            <i class="fas fa-times"></i>' +
    '        </button>' +
    '    </div>' +
    '    <div class="chat-messages" id="chat-messages">' +
    '        <div class="message bot">' +
    '            Hello! I\'m your official AI assistant. How can I help you navigate government schemes today?' +
    '        </div>' +
    '    </div>' +
    '    <div class="chat-input-area">' +
    '        <div class="input-group">' +
    '            <input type="text" id="chat-input" placeholder="Type your message..." ' +
    '                onkeypress="if(event.key===\'Enter\') sendChatMessage()">' +
    '            <button type="button" onclick="sendChatMessage()" title="Send Message">' +
    '                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>' +
    '            </button>' +
    '        </div>' +
    '        <div class="text-center mt-1" style="font-size: 9px; color: #94a3b8;">Verbatim AI responses may vary. Powered by Gemini.</div>' +
    '    </div>' +
    '</div>';

    function injectChatbot() {
        if (document.getElementById('yojanmitra-chatbot-container')) return; // already injected
        const div = document.createElement('div');
        div.id = 'yojanmitra-chatbot-container';
        div.innerHTML = chatbotHTML;
        document.body.appendChild(div);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectChatbot);
    } else {
        // DOM already ready — inject immediately
        injectChatbot();
    }

    // --- Expose functions to window for HTML onclick handlers ---
    window.toggleChat = function () {
        const chatbox = document.getElementById('chatbox');
        if (!chatbox) return;
        chatbox.style.display = chatbox.style.display === 'none' ? 'flex' : 'none';
        if (chatbox.style.display === 'flex') {
            document.getElementById('chat-input').focus();
        }
    };

    window.sendChatMessage = async function () {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        if (!message) return;

        addMessage(message, 'user');
        input.value = '';

        const typingId = addTypingIndicator();

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message })
            });
            const data = await res.json();

            const typingEl = document.getElementById(typingId);
            if (typingEl) typingEl.remove();

            addMessage(data.response, 'bot');
        } catch (e) {
            const typingEl = document.getElementById(typingId);
            if (typingEl) typingEl.remove();
            addMessage('Error connecting to assistant.', 'bot');
        }
    };

    function addTypingIndicator() {
        const container = document.getElementById('chat-messages');
        if (!container) return;
        const div = document.createElement('div');
        div.className = 'message bot';
        div.id = 'msg-' + Date.now() + Math.random().toString(36).substr(2, 5);
        div.innerHTML = '<span class="ym-chat-dots"><span></span><span></span><span></span></span>';
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return div.id;
    }

    function addMessage(text, sender) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        const div = document.createElement('div');
        div.className = `message ${ sender }`;
        div.textContent = text;
        div.id = 'msg-' + Date.now() + Math.random().toString(36).substr(2, 5);
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
        return div.id;
    }
})();