// frontend/js/agent.js
class FocusAgent {
    constructor() {
        this.apiBase = 'http://localhost:8000/api';
        this.userId = localStorage.getItem('focus_user_id') || 'default_user';
    }

    async processMessage(message) {
        try {
            const response = await fetch(`${this.apiBase}/agent/process`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    message: message
                })
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            return data.response;
        } catch (error) {
            console.error('Agent error:', error);
            throw error;
        }
    }

    async getSchedule(date) {
        const response = await fetch(`${this.apiBase}/schedule/${this.userId}?date=${date}`);
        return response.json();
    }

    async getGoals(status) {
        const url = status ? `${this.apiBase}/goals/${this.userId}?status=${status}` : `${this.apiBase}/goals/${this.userId}`;
        const response = await fetch(url);
        return response.json();
    }

    async getHabits(status = 'active') {
        const response = await fetch(`${this.apiBase}/habits/${this.userId}?status=${status}`);
        return response.json();
    }

    async logHabit(habitId, date, completed = true) {
        const response = await fetch(`${this.apiBase}/habit/${habitId}/log?date=${date}&completed=${completed}`, {
            method: 'POST'
        });
        return response.json();
    }

    async saveApiKey(apiKey) {
        const response = await fetch(`${this.apiBase}/user/apikey`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: this.userId,
                api_key: apiKey
            })
        });
        return response.json();
    }

    async getProgress() {
        const response = await fetch(`${this.apiBase}/progress/${this.userId}`);
        return response.json();
    }
}

// Export for use in app.js
window.FocusAgent = FocusAgent;
