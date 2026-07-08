from pydantic_settings import BaseSettings, SettingsConfigDict


class FileOperationsSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    max_backup_age_days: int = 7
    local_time_zone: str = "Asia/Kathmandu"
