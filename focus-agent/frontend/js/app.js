// ==========================================
// STATE
// ==========================================
const state = {
    apiKey: localStorage.getItem('focus_api_key') || '',
    messages: JSON.parse(localStorage.getItem('focus_messages') || '[]'),
    schedule: JSON.parse(localStorage.getItem('focus_schedule') || 'null'),
    isProcessing: false,
    taskCount: 0,
    userId: localStorage.getItem('focus_user_id') || 'demo_user',
    vanguardStats: null
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
    installBtn: $('installBtn'),
    scheduleList: $('scheduleList'),
    goalsList: $('goalsList'),
    habitsList: $('habitsList')
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
    checkApiHealth();
    loadDashboardData();
    
    console.log('🎯 Focus Agent initialized');
    console.log('User ID:', state.userId);
}

// ==========================================
// CHECK API HEALTH
// ==========================================
async function checkApiHealth() {
    try {
        const response = await fetch('http://localhost:8000/health');
        if (response.ok) {
            setStatus('online', 'Connected');
            console.log('✅ API is healthy');
        } else {
            setStatus('offline', 'API Error');
        }
    } catch (error) {
        console.error('API not reachable:', error);
        setStatus('offline', 'API Offline');
    }
}

// ==========================================
// LOAD DASHBOARD DATA
// ==========================================
async function loadDashboardData() {
    try {
        // Load schedule
        const scheduleRes = await fetch(`${API_BASE}/schedule/${state.userId}`);
        const scheduleData = await scheduleRes.json();
        if (scheduleData.success && scheduleData.schedule) {
            renderSchedule(scheduleData.schedule);
        }

        // Load goals
        const goalsRes = await fetch(`${API_BASE}/goals/${state.userId}`);
        const goalsData = await goalsRes.json();
        if (goalsData.success) {
            renderGoals(goalsData.goals);
        }

        // Load habits
        const habitsRes = await fetch(`${API_BASE}/habits/${state.userId}`);
        const habitsData = await habitsRes.json();
        if (habitsData.success) {
            renderHabits(habitsData.habits);
        }

        // Load progress
        const progressRes = await fetch(`${API_BASE}/progress/${state.userId}`);
        const progressData = await progressRes.json();
        if (progressData.success) {
            updateStats(progressData);
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// ==========================================
// RENDER FUNCTIONS
// ==========================================
function renderSchedule(schedule) {
    const container = document.getElementById('scheduleList');
    if (!container) return;
    
    if (!schedule || !schedule.tasks || schedule.tasks.length === 0) {
        container.innerHTML = '<div style="color: #555577; text-align: center; padding: 20px;">No tasks scheduled today. Create one!</div>';
        return;
    }

    container.innerHTML = schedule.tasks.map(task => `
        <div class="task-item">
            <span class="task-time">${task.start_time || 'TBD'}</span>
            <span class="task-name">${task.name}</span>
            <span class="task-status status-${task.status || 'pending'}">${task.status || 'pending'}</span>
        </div>
    `).join('');

    document.getElementById('taskCount').textContent = schedule.tasks.length;
}

function renderGoals(goals) {
    const container = document.getElementById('goalsList');
    if (!container) return;
    
    if (!goals || goals.length === 0) {
        container.innerHTML = '<div style="color: #555577; text-align: center; padding: 20px;">No active goals. Add your first goal!</div>';
        return;
    }

    const activeGoals = goals.filter(g => g.status === 'active');
    container.innerHTML = activeGoals.map(goal => `
        <div class="goal-item">
            <span>${goal.title}</span>
            <div class="goal-progress">
                <div class="goal-progress-bar" style="width: ${goal.progress || 0}%"></div>
            </div>
            <span class="goal-percent">${goal.progress || 0}%</span>
        </div>
    `).join('');

    document.getElementById('goalCount').textContent = activeGoals.length;
}

function renderHabits(habits) {
    const container = document.getElementById('habitsList');
    if (!container) return;
    
    if (!habits || habits.length === 0) {
        container.innerHTML = '<div style="color: #555577; text-align: center; padding: 20px;">No habits tracked. Start a habit today!</div>';
        return;
    }

    container.innerHTML = habits.map(habit => `
        <div class="habit-item">
            <span>${habit.name}</span>
            <span class="habit-streak">🔥 ${habit.current_streak || 0} day streak</span>
        </div>
    `).join('');

    document.getElementById('habitCount').textContent = habits.length;
}

function updateStats(progressData) {
    if (progressData.progress) {
        const match = progressData.progress.match(/(\d+)%/);
        if (match) {
            document.getElementById('completionRate').textContent = match[1] + '%';
        }
    }
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
    setStatus('processing', 'Processing...');
    
    try {
        const response = await callAgent(text);
        
        // Display the response message
        addMessage('agent', response.message);
        
        // If there's Vanguard data, display it
        if (response.vanguard_data) {
            state.vanguardStats = response.vanguard_data;
            displayVanguardStats(response.vanguard_data);
        }
        
        // If schedule was updated, refresh dashboard
        if (response.schedule) {
            state.schedule = response.schedule;
            localStorage.setItem('focus_schedule', JSON.stringify(response.schedule));
            updateTaskCount();
            loadDashboardData();
        }
        
        // Display suggestions if any
        if (response.suggestions && response.suggestions.length > 0) {
            addMessage('agent', '💡 ' + response.suggestions.join('\n'));
        }
        
    } catch (error) {
        console.error('Error:', error);
        addMessage('agent', '❌ Sorry, I encountered an error. Please try again.\n\n' + error.message);
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
        headers: { 
            'Content-Type': 'application/json',
            'X-API-Key': state.apiKey
        },
        body: JSON.stringify({
            message: message,
            user_id: state.userId
        })
    });
    
    if (!response.ok) {
        const errorData = await response.text();
        throw new Error(`API error ${response.status}: ${errorData}`);
    }
    
    const data = await response.json();
    if (!data.success) {
        throw new Error(data.error || 'Unknown error');
    }
    
    return data.response;
}

// ==========================================
// DISPLAY VANGUARD BRAIN STATS
// ==========================================
function displayVanguardStats(stats) {
    // Update the stats section with Vanguard data
    const vanguardContainer = document.getElementById('vanguardStats') || createVanguardContainer();
    
    vanguardContainer.innerHTML = `
        <div class="vanguard-stats">
            <div class="stat-item">
                <span class="stat-label">🧠 Ambition</span>
                <span class="stat-value">${stats.core_ambition || 'Not set'}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">⏱️ Current Block</span>
                <span class="stat-value">${stats.current_block_mins || 15} mins</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">🎯 Target</span>
                <span class="stat-value">${stats.target_block_mins || 240} mins</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">📈 Progress</span>
                <span class="stat-value">${stats.progress_to_target || 0}%</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">🔥 Streak</span>
                <span class="stat-value">${stats.streak_count || 0} days</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">🏆 Wins</span>
                <span class="stat-value">${stats.total_wins || 0}</span>
            </div>
        </div>
    `;
}

function createVanguardContainer() {
    const container = document.createElement('div');
    container.id = 'vanguardStats';
    container.className = 'section';
    container.innerHTML = '<h2>🧠 Vanguard Brain</h2>';
    
    // Insert after the habits section
    const habitsSection = document.querySelector('.section:last-child');
    habitsSection.parentNode.insertBefore(container, habitsSection.nextSibling);
    
    return container;
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
    
    // Check if content contains schedule formatting
    let formattedContent = formatContent(msg.content);
    
    div.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="bubble">
            ${formattedContent}
            <span class="time">${formatTime(msg.timestamp)}</span>
        </div>
    `;
    
    els.messages.appendChild(div);
    els.messages.scrollTop = els.messages.scrollHeight;
}

function formatContent(content) {
    // Convert newlines to <br>
    let html = content.replace(/\n/g, '<br>');
    
    // Highlight Vanguard Brain sections
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Highlight emojis
    html = html.replace(/([🌟✅🚀💡🧠🎯📈🔥🏆⚠️🛡️🚨])/g, '<span style="font-size:1.2em;">$1</span>');
    
    return html;
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
    
    // Send API key to backend
    fetch(`${API_BASE}/user/apikey`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: state.userId,
            api_key: key
        })
    }).catch(console.error);
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
