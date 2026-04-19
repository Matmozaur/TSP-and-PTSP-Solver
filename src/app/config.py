"""Application configuration using Pydantic Settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "TSP-PTSP Solver"
    app_version: str = "2.0.0"
    debug: bool = False
    environment: str = "development"

    # API settings
    api_v1_prefix: str = "/api/v1"
    api_title: str = "TSP and PTSP Solver API"
    api_description: str = "Solve Traveling Salesman and Physical Traveling Salesman problems"

    # CORS settings
    cors_origins: list[str] = ["*"]
    cors_credentials: bool = True
    cors_methods: list[str] = ["*"]
    cors_headers: list[str] = ["*"]

    # Output paths
    media_path: Path = Path("./media")
    results_path: Path = Path("./results")

    # Go worker settings (Phase 2)
    go_worker_enabled: bool = False
    go_worker_url: str = "http://localhost:8080"
    go_worker_timeout_seconds: float = 30.0

    # Phase 3 async job persistence
    database_url: str | None = None

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }

    def __init__(self, **data):
        """Initialize settings and create required directories."""
        super().__init__(**data)
        # Create media and results directories if they don't exist
        self.media_path.mkdir(parents=True, exist_ok=True)
        self.results_path.mkdir(parents=True, exist_ok=True)


settings = Settings()
