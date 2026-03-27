from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

from db.models import Base

load_dotenv()

# SQLite varsayılan — sunucu gerektirmez, tek bir .db dosyası
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./qa_tool.db")

# SQLite için check_same_thread=False gerekli (FastAPI çok thread kullanır)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Tabloları oluşturur — uygulama ilk başladığında çağrılır."""
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
