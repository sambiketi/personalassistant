// ==========================================
// API CLIENT
// ==========================================
class FocusAgentClient {
  constructor(apiBase, userId) {
    this.apiBase = apiBase;
    this.userId = userId;
  }

  async _request(path, options = {}) {
    const res = await fetch(`${this.apiBase}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    let data;
    try {
      data = await res.json();
    } catch {
      throw new Error(`Server returned an invalid response (${res.status})`);
    }
    if (!res.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg).join(', ')
        : (data.detail || data.error || `Request failed (${res.status})`);
      throw new Error(detail);
    }
    return data;
  }

  // ✅ FIXED: Accepts API key parameter
  chat(message, apiKey) {
    return this._request('/agent/process', {
      method: 'POST',
      body: JSON.stringify({ 
        message, 
        user_id: this.userId,
        api_key: apiKey || null
      }),
    });
  }

  getSchedule() {
    return this._request(`/schedule/${this.userId}`);
  }

  createTask(task) {
    return this._request(`/schedule/${this.userId}`, { method: 'POST', body: JSON.stringify(task) });
  }

  getGoals() {
    return this._request(`/goals/${this.userId}`);
  }

  createGoal(goal) {
    return this._request(`/goals/${this.userId}`, { method: 'POST', body: JSON.stringify(goal) });
  }

  getHabits() {
    return this._request(`/habits/${this.userId}`);
  }

  createHabit(habit) {
    return this._request(`/habits/${this.userId}`, { method: 'POST', body: JSON.stringify(habit) });
  }

  logHabit(habitId, date, completed = true) {
    return this._request(`/habits/${habitId}/log`, {
      method: 'POST',
      body: JSON.stringify({ date, completed }),
    });
  }

  getProgress() {
    return this._request(`/progress/${this.userId}`);
  }

  logTask(log) {
    return this._request(`/progress/${this.userId}/log`, { method: 'POST', body: JSON.stringify(log) });
  }

  // REMOVED: saveApiKey() - now handled entirely in localStorage by app.js
  // The app.js saveApiKey() function now only uses localStorage
}

// ==========================================
// NATURAL LANGUAGE COMMAND ROUTER
// ==========================================
const NL_PATTERNS = {
  task: /^add\s+(?:a\s+)?(?:task\s+)?(.+?)\s+(?:at|@)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/i,
  goal: /^add\s+goal\s+(.+)$/i,
  habit: /^(?:add|start)\s+habit\s+(.+)$/i,
};

function _to24h(hour, minute, meridiem) {
  let h = parseInt(hour, 10);
  const m = minute !== undefined && minute !== null ? parseInt(minute, 10) : 0;
  if (isNaN(m)) {
    return `${String(h).padStart(2, '0')}:00`;
  }
  if (meridiem) {
    const mer = meridiem.toLowerCase();
    if (mer === 'pm' && h < 12) h += 12;
    if (mer === 'am' && h === 12) h = 0;
  }
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function parseNaturalLanguageCommand(text, client) {
  const taskMatch = text.match(NL_PATTERNS.task);
  if (taskMatch) {
    const [, name, hour, minute, meridiem] = taskMatch;
    const start_time = _to24h(hour, minute, meridiem);
    const payload = { name: name.trim(), start_time, status: 'pending' };
    return { handled: true, kind: 'task', payload, promise: client.createTask(payload) };
  }

  const goalMatch = text.match(NL_PATTERNS.goal);
  if (goalMatch) {
    const payload = { title: goalMatch[1].trim() };
    return { handled: true, kind: 'goal', payload, promise: client.createGoal(payload) };
  }

  const habitMatch = text.match(NL_PATTERNS.habit);
  if (habitMatch) {
    const payload = { name: habitMatch[1].trim(), frequency: 'daily' };
    return { handled: true, kind: 'habit', payload, promise: client.createHabit(payload) };
  }

  return { handled: false };
}

window.FocusAgentClient = FocusAgentClient;
window.parseNaturalLanguageCommand = parseNaturalLanguageCommand;