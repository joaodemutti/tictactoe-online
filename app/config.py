from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MIGRATION_DATABASE_URL: str
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 10080

    model_config = {"env_file": ".env"}


settings = Settings()
