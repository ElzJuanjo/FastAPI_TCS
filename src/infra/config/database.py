import pyodbc
import warnings
from sqlalchemy import create_engine, exc as sa_exc
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from src.infra.config.settings import get_settings

warnings.filterwarnings(
    "ignore",
    r".*Unrecognized server version info.*",
    sa_exc.SAWarning,
)

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency: yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_mssql_connection():
    """Direct pyodbc connection for raw queries (OPENQUERY, etc.)."""
    return pyodbc.connect(settings.PYODBC_CONN_STR)
