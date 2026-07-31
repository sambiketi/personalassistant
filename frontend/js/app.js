// ==========================================
// STATE
// ==========================================
const state = {
  apiKey: localStorage.getItem('focus_api_key') || '',
  messages: JSON.parse(localStorage.getItem('focus_messages') || '[]'),
  isProcessing: false,
  taskCount: 0,
  userId: localStorage.getItem('focus_user_id') || 'demo_user',
};
localStorage.setItem('focus_user_id', state.userId);

const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000/api'
  : '/api';

const client = new FocusAgentClient(API_BASE, state.userId);

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
  statusDot: $('statusDot'),
  statusText: $('statusText'),
  taskCount: $('taskCount'),
  clearBtn: $('clearBtn'),
  installBtn: $('installBtn'),
  scheduleList: $('scheduleList'),
  goalsList: $('goalsList'),
  habitsList: $('habitsList'),
  progressStats: $('progressStats'),
};

// ==========================================
// CENTRALIZED ERROR / FEEDBACK HELPERS
// ==========================================
/** Show a fading success/error message inside a form. Auto-clears after `ms`. */
function showFormMessage(el, text, type = 'success', ms = 3000) {
  el.textContent = text;
  el.className = `form-msg ${type}`;
  // force reflow so the opacity transition re-triggers on repeated messages
  void el.offsetWidth;
  el.classList.add('visible');
  clearTimeout(el._fadeTimer);
  el._fadeTimer = setTimeout(() => {
    el.classList.remove('visible');
  }, ms);
}

/** Toggle a button's loading state (spinner + disabled) consistently everywhere. */
function setButtonLoading(btn, loading) {
  btn.disabled = loading;
  btn.classList.toggle('loading', loading);
}

/** One place that turns any thrown error into user-facing text + console log. */
function reportError(context, error) {
  console.error(`[${context}]`, error);
  return error && error.message ? error.message : 'Something went wrong. Please try again.';
}

// ==========================================
// INIT
// ==========================================
function init() {
  if (state.apiKey) {
    els.apiKeyInput.value = state.apiKey;
    els.apiStatus.textContent = '✅ API key loaded';
    els.apiStatus.className = 'api-status ready';
  }

  if (state.messages.length > 0) {
    els.emptyState.classList.add('hidden');
    state.messages.forEach(renderMessage);
  }

  setupEventListeners();
  setupAutoResize();
  checkApiHealth();
  loadDashboardData();
}

async function checkApiHealth() {
  try {
    const base = API_BASE.replace(/\/api$/, '');
    const response = await fetch(`${base}/health`);
    setStatus(response.ok ? 'online' : 'offline', response.ok ? 'Connected' : 'API Error');
  } catch {
    setStatus('offline', 'API Offline');
  }
}

// ==========================================
// DASHBOARD DATA
// ==========================================
async function loadDashboardData() {
  const results = await Promise.allSettled([
    client.getSchedule(),
    client.getGoals(),
    client.getHabits(),
    client.getProgress(),
  ]);

  const [scheduleR, goalsR, habitsR, progressR] = results;

  if (scheduleR.status === 'fulfilled') renderSchedule(scheduleR.value.schedule);
  else reportError('loadSchedule', scheduleR.reason);

  if (goalsR.status === 'fulfilled') renderGoals(goalsR.value.goals);
  else reportError('loadGoals', goalsR.reason);

  if (habitsR.status === 'fulfilled') renderHabits(habitsR.value.habits);
  else reportError('loadHabits', habitsR.reason);

  if (progressR.status === 'fulfilled') renderProgress(progressR.value);
  else reportError('loadProgress', progressR.reason);
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
      handleSend();
    });
  });

  els.clearBtn.addEventListener('click', clearChat);
  els.installBtn.addEventListener('click', installPWA);

  document.getElementById('taskForm').addEventListener('submit', handleTaskForm);
  document.getElementById('goalForm').addEventListener('submit', handleGoalForm);
  document.getElementById('habitForm').addEventListener('submit', handleHabitForm);
}

// ==========================================
// SEND MESSAGE (chat + NL command routing)
// ==========================================
async function handleSend() {
  const text = els.userInput.value.trim();
  if (!text || state.isProcessing) return;

  els.userInput.value = '';
  els.emptyState.classList.add('hidden');
  addMessage('user', text);

  state.isProcessing = true;
  setButtonLoading(els.sendBtn, true);
  setStatus('processing', 'Processing...');

  try {
    // Try structured "add task/goal/habit at ..." commands first so simple
    // requests don't need a round trip through the LLM.
    const nl = parseNaturalLanguageCommand(text, client);
    if (nl.handled) {
      await nl.promise;
      addMessage('agent', `✅ Added ${nl.kind}: "${nl.payload.name || nl.payload.title}"`);
      loadDashboardData();
    } else {
      const { response } = await client.chat(text);
      addMessage('agent', response.message);
      if (response.schedule) loadDashboardData();
      if (response.suggestions?.length) addMessage('agent', '💡 ' + response.suggestions.join('\n'));
    }
  } catch (error) {
    addMessage('agent', '❌ ' + reportError('handleSend', error));
  } finally {
    state.isProcessing = false;
    setButtonLoading(els.sendBtn, false);
    setStatus('online', 'Ready');
  }
}

// ==========================================
// FORM HANDLERS (spinner + fade feedback)
// ==========================================
async function handleTaskForm(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button');
  const msg = document.getElementById('taskMsg');
  const name = document.getElementById('taskName').value.trim();
  const start_time = document.getElementById('taskTime').value || undefined;

  setButtonLoading(btn, true);
  try {
    await client.createTask({ name, start_time, status: 'pending' });
    showFormMessage(msg, '✅ Task added!', 'success');
    e.target.reset();
    loadDashboardData();
  } catch (err) {
    showFormMessage(msg, '❌ ' + reportError('createTask', err), 'error', 5000);
  } finally {
    setButtonLoading(btn, false);
  }
}

async function handleGoalForm(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button');
  const msg = document.getElementById('goalMsg');
  const title = document.getElementById('goalTitle').value.trim();
  const category = document.getElementById('goalCategory').value.trim() || undefined;

  setButtonLoading(btn, true);
  try {
    await client.createGoal({ title, category });
    showFormMessage(msg, '✅ Goal added!', 'success');
    e.target.reset();
    loadDashboardData();
  } catch (err) {
    showFormMessage(msg, '❌ ' + reportError('createGoal', err), 'error', 5000);
  } finally {
    setButtonLoading(btn, false);
  }
}

async function handleHabitForm(e) {
  e.preventDefault();
  const btn = e.target.querySelector('button');
  const msg = document.getElementById('habitMsg');
  const name = document.getElementById('habitName').value.trim();
  const frequency = document.getElementById('habitFrequency').value;

  setButtonLoading(btn, true);
  try {
    await client.createHabit({ name, frequency });
    showFormMessage(msg, '✅ Habit added!', 'success');
    e.target.reset();
    loadDashboardData();
  } catch (err) {
    showFormMessage(msg, '❌ ' + reportError('createHabit', err), 'error', 5000);
  } finally {
    setButtonLoading(btn, false);
  }
}

async function saveApiKey() {
  const key = els.apiKeyInput.value.trim();
  if (!key) {
    els.apiStatus.textContent = '⚠️ Please enter a valid API key';
    els.apiStatus.className = 'api-status error';
    return;
  }
  setButtonLoading(els.saveApiBtn, true);
  try {
    await client.saveApiKey(key);
    state.apiKey = key;
    localStorage.setItem('focus_api_key', key);
    els.apiStatus.textContent = '✅ API key saved!';
    els.apiStatus.className = 'api-status ready';
  } catch (err) {
    els.apiStatus.textContent = '❌ ' + reportError('saveApiKey', err);
    els.apiStatus.className = 'api-status error';
  } finally {
    setButtonLoading(els.saveApiBtn, false);
  }
}

// ==========================================
// RENDERING
// ==========================================
function renderSchedule(schedule) {
  const tasks = schedule?.tasks || [];
  state.taskCount = tasks.length;
  els.taskCount.textContent = state.taskCount;

  if (!tasks.length) {
    els.scheduleList.innerHTML = '<div class="empty-hint">No tasks scheduled. Create one!</div>';
    return;
  }
  els.scheduleList.innerHTML = tasks.map(t => `
    <div class="task-item">
      <span class="task-time">${t.start_time || '--:--'}</span>
      <span class="task-name">${escapeHtml(t.name)}</span>
      <span class="task-status status-${t.status}">${t.status}</span>
    </div>`).join('');
}

function renderGoals(goals) {
  if (!goals?.length) {
    els.goalsList.innerHTML = '<div class="empty-hint">No goals set. Add your first goal!</div>';
    return;
  }
  els.goalsList.innerHTML = goals.map(g => `
    <div class="goal-item">
      <span class="goal-name">${escapeHtml(g.title)}</span>
      <div class="goal-progress"><div class="goal-progress-bar" style="width:${g.progress}%"></div></div>
      <span class="goal-percent">${g.progress}%</span>
    </div>`).join('');
}

function renderHabits(habits) {
  if (!habits?.length) {
    els.habitsList.innerHTML = '<div class="empty-hint">No habits tracked. Start a habit today!</div>';
    return;
  }
  els.habitsList.innerHTML = habits.map(h => `
    <div class="habit-item">
      <span class="habit-name">${escapeHtml(h.name)}</span>
      <span class="habit-streak">🔥 ${h.current_streak} day streak</span>
    </div>`).join('');
}

function renderProgress(progress) {
  const stats = [
    { label: 'Completion rate', value: `${progress.completion_rate ?? 0}%` },
    { label: 'Avg task duration', value: `${progress.avg_duration_minutes ?? 0} min` },
    { label: 'Tasks logged', value: progress.total ?? 0 },
  ];
  (progress.habit_streaks || []).forEach(h => {
    stats.push({ label: `${h.name} streak`, value: `${h.current_streak}d (best ${h.longest_streak}d)` });
  });

  els.progressStats.innerHTML = stats.map(s => `
    <div class="stat-item">
      <span class="stat-label">${escapeHtml(s.label)}</span>
      <span class="stat-value">${escapeHtml(String(s.value))}</span>
    </div>`).join('');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

// ==========================================
// CHAT UI HELPERS
// ==========================================
function addMessage(type, content) {
  const msg = { type, content, timestamp: new Date().toISOString() };
  state.messages.push(msg);
  localStorage.setItem('focus_messages', JSON.stringify(state.messages));
  renderMessage(msg);
}

function renderMessage(msg) {
  const div = document.createElement('div');
  div.className = `message ${msg.type}`;
  const avatar = msg.type === 'user' ? '👤' : '🤖';
  div.innerHTML = `
    <div class="avatar">${avatar}</div>
    <div class="bubble">${formatContent(msg.content)}<span class="time">${formatTime(msg.timestamp)}</span></div>`;
  els.messages.appendChild(div);
  els.messages.scrollTop = els.messages.scrollHeight;
}

function formatContent(content) {
  return escapeHtml(content).replace(/\n/g, '<br>');
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function setStatus(status, text) {
  els.statusDot.className = `status-dot ${status}`;
  els.statusText.textContent = text;
}

function clearChat() {
  if (confirm('Clear all messages?')) {
    state.messages = [];
    localStorage.setItem('focus_messages', '[]');
    els.messages.innerHTML = '';
    els.emptyState.classList.remove('hidden');
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
window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  deferredPrompt = e;
  els.installBtn.style.display = 'block';
});

async function installPWA() {
  if (deferredPrompt) {
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
    els.installBtn.style.display = 'none';
  } else {
    alert('📱 To install:\n• Chrome: Menu → "Add to Home Screen"\n• Safari: Share → "Add to Home Screen"');
  }
}

document.addEventListener('DOMContentLoaded', init);
