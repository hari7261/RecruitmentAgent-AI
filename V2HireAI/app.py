import sys
from pathlib import Path
import uvicorn

# Ensure the root directory is in PYTHONPATH so app package is importable
root_path = Path(__file__).resolve().parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("      === Starting AI Recruitment Platform (FastAPI) ===")
    print("=" * 60)
    print("  Login Portal: http://localhost:8000/ui/auth/login.html")
    print("  API Docs:     http://localhost:8000/docs")
    print("=" * 60 + "\n")
    
    # Run the Uvicorn development server
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
