import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://np_user:np_password@db:5432/np_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Создаёт все таблицы при старте приложения"""
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    print("[DB] Все таблицы инициализированы")