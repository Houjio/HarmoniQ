from sqlalchemy import create_engine, Column, Integer, String, Float
import sqlalchemy
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic import BaseModel

from harmoniq import DB_PATH

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
