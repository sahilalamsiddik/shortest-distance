import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings, BASE_DIR
from app.models import Base

logger = logging.getLogger(__name__)

ACTIVE_DB_TYPE = "Unknown"
DB_ERROR_MESSAGE = ""

def build_mysql_url() -> str:
    pwd = f":{settings.MYSQL_PASSWORD}" if settings.MYSQL_PASSWORD else ""
    return f"mysql+pymysql://{settings.MYSQL_USER}{pwd}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB}"

def init_engine():
    global ACTIVE_DB_TYPE, DB_ERROR_MESSAGE

    # 1. Custom DATABASE_URL if explicitly given
    if settings.DATABASE_URL:
        try:
            eng = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            ACTIVE_DB_TYPE = "Custom Database URL"
            return eng
        except Exception as e:
            logger.warning(f"Failed to connect via custom DATABASE_URL: {e}")
            DB_ERROR_MESSAGE = str(e)

    # 2. Try MySQL connection
    mysql_server_url = f"mysql+pymysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/"
    try:
        # First ensure database exists on MySQL server
        temp_engine = create_engine(mysql_server_url, pool_pre_ping=True)
        with temp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {settings.MYSQL_DB}"))
            conn.commit()
        temp_engine.dispose()

        mysql_db_url = build_mysql_url()
        eng = create_engine(mysql_db_url, pool_pre_ping=True, pool_recycle=3600)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        ACTIVE_DB_TYPE = f"MySQL ({settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DB})"
        logger.info(f"Connected to MySQL successfully: {ACTIVE_DB_TYPE}")
        return eng
    except Exception as e:
        logger.warning(f"MySQL connection failed: {e}. Falling back to SQLite.")
        DB_ERROR_MESSAGE = f"MySQL connection error: {e}"

    # 3. Fallback to SQLite
    sqlite_path = BASE_DIR / "bengaluru_routing.db"
    sqlite_url = f"sqlite:///{sqlite_path}"
    eng = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    ACTIVE_DB_TYPE = f"SQLite Fallback ({sqlite_path.name})"
    logger.info(f"Active database: {ACTIVE_DB_TYPE}")
    return eng

engine = init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_tables():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

# Auto-create tables on import
create_db_tables()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_status():
    return {
        "active_database": ACTIVE_DB_TYPE,
        "is_mysql": "MySQL" in ACTIVE_DB_TYPE,
        "mysql_host": settings.MYSQL_HOST,
        "mysql_database": settings.MYSQL_DB,
        "error_details": DB_ERROR_MESSAGE if "SQLite" in ACTIVE_DB_TYPE else None
    }
