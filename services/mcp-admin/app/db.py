"""Acceso a las dos bases de datos del proyecto.

BD 1: Postgres via SQLAlchemy (usuarios, roles, suscripciones, historial).
BD 2: MongoDB via PyMongo (datos analiticos y resultados de modelos).
Las conexiones son perezosas: no fallan al importar si la base no esta arriba.
"""
from pymongo import MongoClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

_mongo_client: MongoClient | None = None


def get_mongo_db():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=3000)
    return _mongo_client.get_default_database()
