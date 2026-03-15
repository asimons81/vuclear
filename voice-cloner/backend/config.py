from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    app_name: str = "vuclear"

    # Engine
    voice_engine: str = "chatterbox"

    # Storage
    data_dir: Path = Path("./data")

    # Audio
    denoise: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Rate limiting
    rate_limit_voice_upload: str = "10/hour"
    rate_limit_synthesize: str = "20/hour"

    # Logging
    log_level: str = "INFO"

    @field_validator("voice_engine")
    @classmethod
    def validate_engine(cls, v: str) -> str:
        allowed = {"chatterbox", "metavoice", "f5_noncommercial"}
        if v not in allowed:
            raise ValueError(f"VOICE_ENGINE must be one of {allowed}")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def voices_dir(self) -> Path:
        return self.data_dir / "voices"

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def temp_dir(self) -> Path:
        return self.data_dir / "tmp"

    @property
    def audit_log(self) -> Path:
        return self.logs_dir / "audit.jsonl"

    @property
    def app_log(self) -> Path:
        return self.logs_dir / "service.log"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


def ensure_dirs() -> None:
    for d in [
        settings.voices_dir,
        settings.outputs_dir,
        settings.jobs_dir,
        settings.logs_dir,
        settings.temp_dir,
    ]:
        d.mkdir(parents=True, exist_ok=True)
