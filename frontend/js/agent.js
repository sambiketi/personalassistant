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
      // FastAPI validation errors come back as {detail: [...]} or {detail: "..."}
      const detail = Array.isArray(data.detail)
        ? data.detail.map(d => d.msg).join(', ')
        : (data.detail || `Request failed (${res.status})`);
      throw new Error(detail);
    }
    return data;
  }

  chat(message) {
    return this._request('/agent/process', {
      method: 'POST',
      body: JSON.stringify({ message, user_id: this.userId }),
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

  saveApiKey(apiKey) {
    return this._request('/user/apikey', {
      method: 'POST',
      body: JSON.stringify({ user_id: this.userId, api_key: apiKey }),
    });
  }
}

// ==========================================
// NATURAL LANGUAGE COMMAND ROUTER
// Recognizes structured "add X" phrasing and maps it straight to a POST
// helper instead of round-tripping through the full LLM chat pipeline.
// Falls through to `handled: false` for anything else (free-form chat).
// ==========================================
const NL_PATTERNS = {
  // "add task Deep work at 10am" / "add deep work block at 10:30"
  task: /^add\s+(?:a\s+)?(?:task\s+)?(.+?)\s+(?:at|@)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/i,
  // "add goal Learn Spanish" / "add goal Learn Spanish in Education"
  goal: /^add\s+goal\s+(.+)$/i,
  // "add habit Morning run" / "start habit Meditate daily"
  habit: /^(?:add|start)\s+habit\s+(.+)$/i,
};

function _to24h(hour, minute, meridiem) {
  let h = parseInt(hour, 10);
  const m = minute ? parseInt(minute, 10) : 0;
  if (meridiem) {
    const mer = meridiem.toLowerCase();
    if (mer === 'pm' && h < 12) h += 12;
    if (mer === 'am' && h === 12) h = 0;
  }
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

/**
 * Try to interpret free text as a structured command.
 * Returns { handled: true, kind, payload, promise } if matched, else { handled: false }.
 */
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
