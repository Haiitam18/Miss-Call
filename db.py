from dotenv import load_dotenv
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(verbose=True) # On met verbose=True pour voir ce qui se passe

# On récupère les valeurs
db_url = os.getenv("DATABASE_URL")
db_fallback = os.getenv("DB_URL")

# Si rien n'est trouvé, on affiche une erreur et on arrête
if not db_url and not db_fallback:
    print("ERREUR : Aucune variable DATABASE_URL ou DB_URL trouvée dans le .env !")
    print("Vérifie bien que ton fichier .env est à la racine et contient DATABASE_URL=...")
    exit(1)

DATABASE_URL = db_url or db_fallback


class Base(DeclarativeBase):
    """Base declarative SQLAlchemy."""


engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # passe à True pour le debug SQL
    future=True,
    connect_args={"statement_cache_size": 0},
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def init_db() -> None:
    """Crée les tables dans la base de données."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dépendance (FastAPI, etc.) pour obtenir une session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()