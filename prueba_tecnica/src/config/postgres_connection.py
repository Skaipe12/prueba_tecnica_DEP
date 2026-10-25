from sqlalchemy import create_engine
from src.config.env import DATABASE_URL

class PostgresConnection:
    """Encapsula el engine de SQLAlchemy."""

    def __init__(self, database_url = DATABASE_URL, echo = False):
        self.engine = create_engine(database_url, pool_pre_ping=True, future=True, echo=echo)

    def execute(self, query, params=None):
        """Ejecuta una lectura puntual y devuelve el resultado ya materializado."""
        with self.engine.begin() as connection:
            result = connection.execute(query, params or {})
            return result.freeze()() if result.returns_rows else result

    def dispose(self):
        """Libera el pool de conexiones del engine."""
        self.engine.dispose()
