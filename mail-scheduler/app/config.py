from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Mail scheduler settings."""
    
    SERVICE_NAME: str = "mail-scheduler"
    WORKER_ID: str = "worker-1"
    
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "phishing_user"
    POSTGRES_PASSWORD: str = "phishing_password"
    POSTGRES_DB: str = "phishing_db"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"
    
    PREFETCH_COUNT: int = 10
    MAX_RETRIES: int = 3
    RETRY_DELAYS: list = [60, 300, 900]
    
    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@phishingplatform.com"
    SMTP_FROM_NAME: str = "PhishingPlatform"
    SMTP_USE_TLS: bool = False
    
    RATE_LIMIT_PER_MINUTE: int = 100
    RATE_LIMIT_PER_HOUR: int = 1000
    
    TRACKING_BASE_URL: str = "http://localhost:8000"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
