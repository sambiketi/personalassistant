FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

ENV PORT=8000 \
    DB_PATH=focus_agent.db \
    LLM_PROVIDER=deepseek \
    ENVIRONMENT=production

EXPOSE 8000

CMD ["python", "run_server.py"]
