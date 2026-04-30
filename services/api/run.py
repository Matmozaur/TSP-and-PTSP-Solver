"""Console script entry point for running the application."""

import sys
from pathlib import Path

# Add services/api to path to allow imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
