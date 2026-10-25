"""Runtime settings. Business rules do not live here."""

from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Values read from the environment. Defaults match local `backend/` as the cwd."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_dir: Path = Path("../data")
    # Base URL recorded in docs/samples/README.md.
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    decision_cutoff_time: str = "09:00"
    timezone: str = "Europe/London"
    allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> list[str]:
        """Accept a comma-separated ALLOWED_ORIGINS string or a list."""
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        if isinstance(value, list):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        message = "ALLOWED_ORIGINS must be a comma-separated string"
        raise ValueError(message)
