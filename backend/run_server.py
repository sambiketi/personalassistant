import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("ENVIRONMENT", "development") != "production"

    print("=" * 60)
    print("🚀 FOCUS AGENT WITH VANGUARD BRAIN")
    print("=" * 60)
    print(f"📍 API:      http://localhost:{port}")
    print(f"📍 API Docs: http://localhost:{port}/docs")
    print(f"📍 Health:   http://localhost:{port}/health")
    print("=" * 60)

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=reload)
