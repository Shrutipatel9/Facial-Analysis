"""Environment-driven application configuration.

A single Settings instance is created eagerly via get_settings() so that
missing or invalid configuration fails fast at process startup rather than
lazily, mid-request, the first time a given value is touched.
"""

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field(default="development", alias="ENVIRONMENT")

    # --- Database ---
    database_url: str = Field(alias="DATABASE_URL")

    # --- CORS ---
    cors_origins_raw: str = Field(alias="CORS_ORIGINS")

    # Optional comma-separated hostnames for TrustedHostMiddleware (no scheme).
    # Leave empty when FastAPI is only reached via an internal proxy/rewrite
    # whose Host header is not the public frontend hostname.
    trusted_hosts_raw: str = Field(default="", alias="TRUSTED_HOSTS")

    # --- Auth / JWT ---
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    # 7 days (was 30) -- AUTH-012 revised v1.4: the refresh token now travels
    # exclusively as an httpOnly cookie (never readable by JS at all, so the
    # earlier XSS-exposure rationale for a short lifetime no longer applies
    # the same way), but 7 days matches the client's explicit "log out after
    # 7 days of inactivity, or on explicit logout" request for this revision.
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # --- OTP ---
    otp_pepper: str = Field(alias="OTP_PEPPER")
    otp_expire_minutes: int = Field(default=10, alias="OTP_EXPIRE_MINUTES")
    otp_resend_cooldown_seconds: int = Field(default=60, alias="OTP_RESEND_COOLDOWN_SECONDS")
    otp_max_attempts: int = Field(default=5, alias="OTP_MAX_ATTEMPTS")
    otp_lockout_minutes: int = Field(default=15, alias="OTP_LOCKOUT_MINUTES")

    # --- Email delivery ---
    # "console" (dev default, logs the OTP instead of sending) or "smtp".
    # A SendGrid/SES/Postmark sender can be added later as another
    # EmailSender implementation (app/services/email_service.py) without
    # touching otp_service.py -- NFR-012's vendor choice was always meant to
    # be swappable.
    email_provider: str = Field(default="console", alias="EMAIL_PROVIDER")
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    email_from: str | None = Field(default=None, alias="EMAIL_FROM")

    @field_validator("jwt_secret", "otp_pepper")
    @classmethod
    def _reject_placeholder_secrets(cls, value: str) -> str:
        if not value or value.startswith("change-me"):
            raise ValueError(
                "refusing to start with a placeholder secret; "
                "generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return value

    @model_validator(mode="after")
    def _require_smtp_fields_when_selected(self) -> "Settings":
        if self.email_provider == "smtp":
            missing = [
                name
                for name, value in (
                    ("SMTP_HOST", self.smtp_host),
                    ("SMTP_USERNAME", self.smtp_username),
                    ("SMTP_PASSWORD", self.smtp_password),
                    ("EMAIL_FROM", self.email_from),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    f"EMAIL_PROVIDER=smtp requires {', '.join(missing)} to be set. "
                    "For Gmail, SMTP_PASSWORD must be a 16-character App Password "
                    "(https://myaccount.google.com/apppasswords) -- Gmail rejects "
                    "your normal account password over SMTP."
                )
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts_raw.split(",") if host.strip()]

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def cookie_secure(self) -> bool:
        # The refresh-token cookie's Secure attribute: browsers treat plain
        # http://localhost as a trustworthy-enough origin for Secure cookies
        # in practice, but 127.0.0.1/other dev hostnames don't get the same
        # exception -- so this is driven off environment, not the request,
        # to avoid a dev setup silently failing to receive the cookie at all.
        return not self.is_development


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # values come from .env / real env vars
