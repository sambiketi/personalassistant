// ==========================================
// COMPONENT CATALOG FOR JSON-RENDER
// ==========================================

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

const Components = {
  Card: (props) => {
    const { title, subtitle, children, variant = 'default' } = props;
    return `
      <div class="card ${variant === 'default' ? '' : 'card-' + variant}">
        ${title ? `
          <div class="card-header">
            <div class="card-title">
              <h3>${escapeHtml(title)}</h3>
              ${subtitle ? `<span class="card-subtitle">${escapeHtml(subtitle)}</span>` : ''}
            </div>
          </div>
        ` : ''}
        <div class="card-body">
          ${renderChildren(children)}
        </div>
      </div>
    `;
  },

  TaskList: (props) => {
    const { tasks, showStats = true } = props;
    if (!tasks || tasks.length === 0) {
      return `<div class="empty-state">No tasks scheduled.</div>`;
    }
    const total = tasks.length;
    const completed = tasks.filter(t => t.status === 'completed').length;
    const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;
    return `
      <div class="task-list-container">
        ${showStats ? `
          <div class="task-stats">
            <span class="stat-badge">📋 ${total} tasks</span>
            <span class="stat-badge">✅ ${completionRate}% done</span>
          </div>
        ` : ''}
        <div class="task-list">
          ${tasks.map((task, index) => `
            <div class="task-row priority-${task.priority || 3}" data-status="${task.status || 'pending'}">
              <span class="task-number">${String(index + 1).padStart(2, '0')}</span>
              <div class="task-info">
                <span class="task-name">${escapeHtml(task.name)}</span>
                <span class="task-time">${task.start_time || '--:--'}${task.end_time ? ` - ${escapeHtml(task.end_time)}` : ''}</span>
              </div>
              <div class="task-meta">
                ${task.duration ? `<span class="task-duration">${task.duration}m</span>` : ''}
                <span class="task-status status-${task.status || 'pending'}">${task.status || 'pending'}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  },

  GoalsList: (props) => {
    const { goals } = props;
    if (!goals || goals.length === 0) return `<div class="empty-state">No goals set.</div>`;
    return `
      <div class="goals-list">
        ${goals.map(goal => `
          <div class="goal-row">
            <div class="goal-info">
              <span class="goal-name">${escapeHtml(goal.title)}</span>
              ${goal.category ? `<span class="goal-category">${escapeHtml(goal.category)}</span>` : ''}
            </div>
            <div class="goal-progress-track">
              <div class="goal-progress-bar" style="width: ${goal.progress || 0}%">
                <span class="goal-progress-text">${goal.progress || 0}%</span>
              </div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  },

  HabitsList: (props) => {
    const { habits } = props;
    if (!habits || habits.length === 0) return `<div class="empty-state">No habits tracked.</div>`;
    return `
      <div class="habits-list">
        ${habits.map(habit => `
          <div class="habit-row">
            <div class="habit-info">
              <span class="habit-name">${escapeHtml(habit.name)}</span>
              <span class="habit-frequency">${habit.frequency || 'daily'}</span>
            </div>
            <div class="habit-stats">
              <div class="streak-display">
                <span class="streak-flame">🔥</span>
                <span class="streak-count">${habit.current_streak || 0}</span>
                <span class="streak-label">day streak</span>
              </div>
              <span class="habit-best">best: ${habit.longest_streak || 0}d</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  },

  StatsGrid: (props) => {
    const { stats } = props;
    if (!stats || stats.length === 0) return `<div class="empty-state">No stats available.</div>`;
    return `
      <div class="stats-grid">
        ${stats.map(stat => `
          <div class="stat-item">
            ${stat.icon ? `<span class="stat-icon">${stat.icon}</span>` : ''}
            <div class="stat-info">
              <span class="stat-label">${escapeHtml(stat.label)}</span>
              <span class="stat-value">${escapeHtml(String(stat.value))}</span>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  },

  Suggestions: (props) => {
    const { items, title = '💡 Suggestions' } = props;
    if (!items || items.length === 0) return '';
    return `
      <div class="suggestions-section">
        <div class="suggestions-header">${title}</div>
        <div class="suggestions-list">
          ${items.map(item => `
            <div class="suggestion-item">
              <span class="suggestion-bullet">•</span>
              <span>${escapeHtml(item)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  },

  Reasoning: (props) => {
    const { text, title = '🧠 Reasoning' } = props;
    if (!text) return '';
    return `
      <div class="reasoning-section">
        <div class="reasoning-header">${title}</div>
        <div class="reasoning-text">${escapeHtml(text)}</div>
      </div>
    `;
  },

  Section: (props) => {
    const { title, children, variant = 'default' } = props;
    return `
      <div class="section ${variant === 'default' ? '' : 'section-' + variant}">
        ${title ? `<h2 class="section-title">${escapeHtml(title)}</h2>` : ''}
        <div class="section-body">${renderChildren(children)}</div>
      </div>
    `;
  },

  Text: (props) => {
    const { content, variant = 'body' } = props;
    const classes = { body: 'text-body', heading: 'text-heading', small: 'text-small', muted: 'text-muted' };
    return `<div class="${classes[variant] || classes.body}">${escapeHtml(content)}</div>`;
  },

  Divider: () => `<hr class="divider" />`,

  ProgressCard: (props) => {
    const { title = '📈 Progress', stats, habit_streaks } = props;
    if (!stats || stats.length === 0) return `<div class="empty-state">No progress data.</div>`;
    let html = `
      <div class="progress-card">
        <div class="card-header"><div class="card-title"><h3>${title}</h3></div></div>
        <div class="stats-grid">
          ${stats.map(stat => `
            <div class="stat-item">
              ${stat.icon ? `<span class="stat-icon">${stat.icon}</span>` : ''}
              <div class="stat-info">
                <span class="stat-label">${escapeHtml(stat.label)}</span>
                <span class="stat-value">${escapeHtml(String(stat.value))}</span>
              </div>
            </div>
          `).join('')}
        </div>
        ${habit_streaks && habit_streaks.length > 0 ? `
          <div class="habit-streaks">
            <h4>🔥 Habit Streaks</h4>
            <div class="streaks-grid">
              ${habit_streaks.map(h => `
                <div class="streak-item">
                  <span class="streak-name">${escapeHtml(h.name)}</span>
                  <span class="streak-value">${h.current_streak}d</span>
                  <span class="streak-best">best: ${h.longest_streak}d</span>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
    return html;
  },
};

function renderChildren(children) {
  if (!children) return '';
  if (Array.isArray(children)) {
    return children.map(child => renderSpec(child)).join('');
  }
  return renderSpec(children);
}

function renderSpec(spec) {
  if (!spec) return '';
  if (typeof spec === 'string') return escapeHtml(spec);
  const { type, props = {}, children } = spec;
  const component = Components[type];
  if (!component) {
    console.warn(`Unknown component type: ${type}`);
    return `<div class="unknown-component">Unknown component: ${type}</div>`;
  }
  try {
    return component({ ...props, children });
  } catch (error) {
    console.error(`Error rendering component ${type}:`, error);
    return `<div class="error-component">Error rendering ${type}</div>`;
  }
}

function renderResponse(content) {
  try {
    const data = typeof content === 'string' ? JSON.parse(content) : content;
    if (data.type && Components[data.type]) return renderSpec(data);
    if (data.tasks && Array.isArray(data.tasks)) {
      return renderSpec({
        type: 'Card',
        props: { title: `📅 ${data.date || 'Today\'s Schedule'}` },
        children: [
          { type: 'TaskList', props: { tasks: data.tasks } },
          ...(data.suggestions ? [{ type: 'Suggestions', props: { items: data.suggestions } }] : []),
          ...(data.reasoning ? [{ type: 'Reasoning', props: { text: data.reasoning } }] : []),
        ]
      });
    }
    if (data.goals && Array.isArray(data.goals)) {
      return renderSpec({
        type: 'Card',
        props: { title: '🎯 Goals' },
        children: [{ type: 'GoalsList', props: { goals: data.goals } }]
      });
    }
    if (data.habits && Array.isArray(data.habits)) {
      return renderSpec({
        type: 'Card',
        props: { title: '🔥 Habits' },
        children: [{ type: 'HabitsList', props: { habits: data.habits } }]
      });
    }
    if (data.completion_rate !== undefined || data.total !== undefined) {
      const stats = [];
      if (data.completion_rate !== undefined) stats.push({ icon: '📊', label: 'Completion Rate', value: `${data.completion_rate}%` });
      if (data.avg_duration_minutes !== undefined) stats.push({ icon: '⏱️', label: 'Avg Duration', value: `${data.avg_duration_minutes} min` });
      if (data.total !== undefined) stats.push({ icon: '📋', label: 'Tasks Logged', value: data.total });
      return renderSpec({ type: 'ProgressCard', props: { stats, habit_streaks: data.habit_streaks || [] } });
    }
    return escapeHtml(content);
  } catch {
    return escapeHtml(content);
  }
}

window.Components = Components;
window.renderSpec = renderSpec;
window.renderResponse = renderResponse;
