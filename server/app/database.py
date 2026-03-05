"""Database connection and session management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from sqlalchemy import text

def init_db():
    """Create all tables and perform simple migrations."""
    Base.metadata.create_all(bind=engine)
    
    # 手动检查并添加 wx_openid 列 (针对存量数据库的自动迁移)
    with engine.connect() as conn:
        try:
            result = conn.execute(text("SHOW COLUMNS FROM users LIKE 'wx_openid'"))
            if not result.fetchone():
                print("Adding missing column 'wx_openid' to 'users' table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN wx_openid VARCHAR(128) UNIQUE AFTER is_active"))
                conn.commit()
        except Exception as e:
            print(f"Migration error (wx_openid): {e}")
