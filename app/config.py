from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MIGRATION_DATABASE_URL: str
    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 10080
    ALLOWED_ORIGINS: str = "https://jogodavelha-online.com.br,http://localhost:8000,http://127.0.0.1:8000"
    TURNSTILE_SITE_KEY: str = ""
    TURNSTILE_SECRET_KEY: str = ""

    model_config = {"env_file": ".env"}

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
