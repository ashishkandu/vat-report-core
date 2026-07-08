from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MSSQLSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    DB_PASSWORD: str = Field(..., validation_alias="DB_PASSWORD")
    DB_SERVER: str = Field("localhost", validation_alias="DB_SERVER")
    DB_PORT: int = Field(1433, validation_alias="DB_PORT")
    DB_USERNAME: str = Field("sa", validation_alias="DB_USERNAME")
    DRIVER: str = "ODBC Driver 17 for SQL Server"
    MAIN_DATABASE: str = Field("master", validation_alias="DB_MAIN_DATABASE")
    MSSQL_DATA_PATH: Path = Field(
        "/var/opt/mssql/data",
        validation_alias="DB_MSSQL_DATA_PATH",
    )
