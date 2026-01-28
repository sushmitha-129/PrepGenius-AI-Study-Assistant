from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///prepgenius.db"

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    kind = Column(String(50), index=True)  # notes, quiz, questions, chat, mentor
    title = Column(String(255))
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def init_db():
    Base.metadata.create_all(bind=engine)
