# Data/db_context.py

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Base único, para todos os Models (Iracema e outros)
Base = declarative_base()


class DbContext:
    def __init__(self, host: str, port: int, user: str, password: str, db: str):
        self._url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
        self._engine: Engine = create_engine(self._url, pool_pre_ping=True)
        self._SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine,
        )

    @property
    def engine(self) -> Engine:
        return self._engine

    def create_session(self) -> Session:
        """
        Cria uma nova Session do SQLAlchemy, para ser usada em repositórios.
        Use sempre em bloco try/finally para fechar.
        """
        return self._SessionLocal()
