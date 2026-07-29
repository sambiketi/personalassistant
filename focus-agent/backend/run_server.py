import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.main import app
    print("✅ App imported successfully!")
except Exception as e:
    print(f"❌ Error importing app: {e}")
    sys.exit(1)

import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 FOCUS AGENT WITH VANGUARD BRAIN")
    print("=" * 60)
    print("📍 API: http://localhost:8000")
    print("📍 API Docs: http://localhost:8000/docs")
    print("📍 Health: http://localhost:8000/health")
    print("=" * 60)
    print("🧠 Vanguard Brain Features:")
    print("  • Win Retrieval (starts every response with past success)")
    print("  • Sabotage Detection (>=4 occurrences triggers interventions)")
    print("  • Progressive Scaling (every 3 wins increases block size)")
    print("  • 50% Floor Rule (reduces chores after a skip)")
    print("  • Habit Sandwich (anchors new habits to existing ones)")
    print("=" * 60)
    print("")
    print("Starting server...")
    
    # Fixed: Use app:app as string for reload to work
    uvicorn.run(
        "app.main:app",  # Changed from app to "app.main:app"
        host="0.0.0.0", 
        port=8000,
        reload=True
    )
