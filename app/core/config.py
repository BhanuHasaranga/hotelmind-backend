from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "HotelMind API"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-key-change-in-production"

    # Database
    POSTGRES_USER: str = "hotelmind"
    POSTGRES_PASSWORD: str = "hotelmind_secret"
    POSTGRES_DB: str = "hotelmind_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS — comma-separated string becomes list via validator below
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP_PREFIX: str = "hotelmind"
    KAFKA_CLIENT_ID: str = "hotelmind-backend"
    KAFKA_DLQ_SUFFIX: str = ".dlq"
    KAFKA_MAX_RETRIES: int = 5
    KAFKA_RETRY_BACKOFF_BASE_SECONDS: float = 0.5
    KAFKA_RETRY_BACKOFF_MAX_SECONDS: float = 30.0
    KAFKA_AUTO_OFFSET_RESET: str = "earliest"

    # Event source identifier stamped on every published event
    EVENT_SOURCE: str = "hotelmind-backend"


settings = Settings()
