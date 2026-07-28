// ==========================================
// STATE
// ==========================================
const state = {
    apiKey: localStorage.getItem('focus_api_key') || '',
    messages: JSON.parse(localStorage.getItem('focus_messages') || '[]'),
    schedule: JSON.parse(localStorage.getItem('focus_schedule') || 'null'),
    isProcessing: false,
    taskCount: 0,
    userId: 'device_' + (localStorage.getItem('focus_user_id') || Math.random().toString(36).substr(2, 9))
};

localStorage.setItem('focus_user_id', state.userId);

// ==========================================
// DOM REFS
// ==========================================
const $ = id => document.getElementById(id);
const els = {
    messages: $('messages'),
    emptyState: $('emptyState'),
    userInput: $('userInput'),
    sendBtn: $('sendBtn'),
    apiKeyInput: $('apiKeyInput'),
    saveApiBtn: $('saveApiBtn'),
    apiStatus: $('apiStatus'),
    apiSection: $('apiSection'),
    statusDot: $('statusDot'),
    statusText: $('statusText'),
    taskCount: $('taskCount'),
    clearBtn: $('clearBtn'),
    installBtn: $('installBtn')
};

const API_BASE = 'http://localhost:8000/api';

// ==========================================
// INIT
// ==========================================
function init() {
    if (state.apiKey) {
        els.apiKeyInput.value = state.apiKey;
        els.apiSection.classList.add('has-key');
        els.apiStatus.textContent = '✅ API key loaded';
        els.apiStatus.className = 'api-status ready';
    }
    
    if (state.messages.length > 0) {
        els.emptyState.classList.add('hidden');
        state.messages.forEach(msg => renderMessage(msg, false));
    }
    
    updateTaskCount();
    setupEventListeners();
    setupAutoResize();
    
    console.log('🎯 Focus Agent initialized');
    console.log('User ID:', state.userId);
}

// ==========================================
// EVENT LISTENERS
// ==========================================
function setupEventListeners() {
    els.sendBtn.addEventListener('click', handleSend);
    els.userInput.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });
    
    els.saveApiBtn.addEventListener('click', saveApiKey);
    els.apiKeyInput.addEventListener('keydown', e => {
        if (e.key === 'Enter') saveApiKey();
    });
    
    document.querySelectorAll('.quick-action').forEach(btn => {
        btn.addEventListener('click', () => {
            els.userInput.value = btn.dataset.text;
            els.userInput.focus();
            handleSend();
        });
    });
    
    els.clearBtn.addEventListener('click', clearChat);
    els.installBtn.addEventListener('click', installPWA);
}

// ==========================================
// SEND MESSAGE
// ==========================================
async function handleSend() {
    const text = els.userInput.value.trim();
    if (!text || state.isProcessing) return;
    
    if (!state.apiKey) {
        els.apiStatus.textContent = '⚠️ Please enter your DeepSeek API key';
        els.apiStatus.className = 'api-status error';
        els.apiKeyInput.focus();
        return;
    }
    
    els.userInput.value = '';
    els.userInput.style.height = 'auto';
    els.emptyState.classList.add('hidden');
    
    addMessage('user', text);
    
    state.isProcessing = true;
    els.sendBtn.disabled = true;
    els.sendBtn.classList.add('loading');
    setStatus('processing', 'Thinking...');
    
    try {
        const response = await callAgent(text);
        addMessage('agent', response.message);
        
        if (response.schedule) {
            state.schedule = response.schedule;
            localStorage.setItem('focus_schedule', JSON.stringify(response.schedule));
            updateTaskCount();
        }
        
        if (response.suggestions && response.suggestions.length > 0) {
            addMessage('agent', '💡 ' + response.suggestions.join('\n'));
        }
        
    } catch (error) {
        console.error('Error:', error);
        addMessage('agent', '❌ Sorry, I encountered an error. Please try again.');
    } finally {
        state.isProcessing = false;
        els.sendBtn.disabled = false;
        els.sendBtn.classList.remove('loading');
        setStatus('online', 'Ready');
    }
}

// ==========================================
// API CALL
// ==========================================
async function callAgent(message) {
    const response = await fetch(`${API_BASE}/agent/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: message,
            user_id: state.userId
        })
    });
    
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    
    const data = await response.json();
    return data.response;
}

// ==========================================
// RENDER MESSAGE
// ==========================================
function addMessage(type, content) {
    const msg = { type, content, timestamp: new Date().toISOString() };
    state.messages.push(msg);
    localStorage.setItem('focus_messages', JSON.stringify(state.messages));
    renderMessage(msg, true);
}

function renderMessage(msg, animate = true) {
    const div = document.createElement('div');
    div.className = `message ${msg.type}`;
    if (!animate) div.style.animation = 'none';
    
    const avatar = msg.type === 'user' ? '👤' : '🤖';
    
    div.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="bubble">
            ${formatContent(msg.content)}
            <span class="time">${formatTime(msg.timestamp)}</span>
        </div>
    `;
    
    els.messages.appendChild(div);
    els.messages.scrollTop = els.messages.scrollHeight;
}

function formatContent(content) {
    return content.replace(/\n/g, '<br>');
}

function formatTime(iso) {
    const date = new Date(iso);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ==========================================
// UI UPDATES
// ==========================================
function updateTaskCount() {
    if (state.schedule && state.schedule.tasks) {
        state.taskCount = state.schedule.tasks.length;
    } else {
        state.taskCount = 0;
    }
    els.taskCount.textContent = state.taskCount;
}

function setStatus(status, text) {
    els.statusDot.className = `status-dot ${status}`;
    els.statusText.textContent = text;
}

function saveApiKey() {
    const key = els.apiKeyInput.value.trim();
    if (!key) {
        els.apiStatus.textContent = '⚠️ Please enter a valid API key';
        els.apiStatus.className = 'api-status error';
        return;
    }
    
    state.apiKey = key;
    localStorage.setItem('focus_api_key', key);
    els.apiSection.classList.add('has-key');
    els.apiStatus.textContent = '✅ API key saved!';
    els.apiStatus.className = 'api-status ready';
}

function clearChat() {
    if (confirm('Clear all messages?')) {
        state.messages = [];
        localStorage.setItem('focus_messages', JSON.stringify([]));
        els.messages.querySelectorAll('.message').forEach(el => el.remove());
        els.emptyState.classList.remove('hidden');
        updateTaskCount();
    }
}

function setupAutoResize() {
    els.userInput.addEventListener('input', () => {
        els.userInput.style.height = 'auto';
        els.userInput.style.height = Math.min(els.userInput.scrollHeight, 100) + 'px';
    });
}

// ==========================================
// PWA INSTALL
// ==========================================
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    els.installBtn.style.display = 'block';
});

async function installPWA() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        const result = await deferredPrompt.userChoice;
        if (result.outcome === 'accepted') {
            console.log('✅ App installed');
        }
        deferredPrompt = null;
        els.installBtn.style.display = 'none';
    } else {
        alert('📱 To install:\n• Chrome: Menu → "Add to Home Screen"\n• Safari: Share → "Add to Home Screen"');
    }
}

// ==========================================
// START
// ==========================================
document.addEventListener('DOMContentLoaded', init);