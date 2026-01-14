# Models/datasource_model.py

from datetime import datetime

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    Boolean,
    SmallInteger,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from Data.db_context import Base


class DataSource(Base):
    __tablename__ = "datasources"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    categoria_informacao = Column(String(150), nullable=False)
    classe_maior = Column(String(150), nullable=True)
    sub_classe_maior = Column(String(150), nullable=True)
    classe_menor = Column(String(150), nullable=True)

    identificador_tabela = Column(String(255), nullable=False)
    titulo_tabela = Column(String(255), nullable=False)
    descricao_tabela = Column(Text, nullable=True)

    colunas_tabela = Column(JSONB, nullable=False, default=list)

    fonte_dados = Column(Text, nullable=True)
    ano_elaboracao = Column(SmallInteger, nullable=True)

    is_ativo = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    palavras_chave = Column(Text, nullable=True)
    
    prompt_inicial = Column(
        Text,
        nullable=True,
        doc="Prompt base (system prompt) usado após a resolução do START para essa datasource."
    )


    __table_args__ = (
        UniqueConstraint("identificador_tabela", name="uq_datasources_identificador"),
    )
