from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine

from .settings import MSSQLSettings

settings = MSSQLSettings()


def build_url(database: str | None = None) -> str:
    return URL.create(
        "mssql+pyodbc",
        username=settings.DB_USERNAME,
        password=settings.DB_PASSWORD,
        host=settings.DB_SERVER,
        port=settings.DB_PORT,
        database=database or settings.MAIN_DATABASE,
        query={"driver": settings.DRIVER},
    )


def get_engine(database: str | None = None) -> Engine:
    return create_engine(build_url(database), pool_pre_ping=True)
