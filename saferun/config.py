from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """SafeRun X402 Configuration"""

    # Application
    app_name: str = "SafeRun X402"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./saferun.db"

    # x402 Configuration
    x402_api_url: str = "https://api.x402.io"  # Replace with actual endpoint
    x402_api_key: Optional[str] = None

    # Agent Configuration
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Workflow Settings
    default_checkpoint_timeout: int = 300  # 5 minutes
    max_rollback_depth: int = 10
    enable_auto_reconciliation: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
