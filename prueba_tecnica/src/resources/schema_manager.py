from src.config.postgres_connection import PostgresConnection
from src.queries.queries import PipelineQueries


class SchemaManager:
    """Crea y limpia el esquema del pipeline de forma idempotente."""

    def __init__(self, connection: PostgresConnection, queries: PipelineQueries) -> None:
        self._connection = connection
        self._queries = queries

    def create_tables(self) -> None:
        """Crea transactions y pipeline_stats si no existen."""
        with self._connection.engine.begin() as connection:
            connection.execute(self._queries.create_transactions())
            connection.execute(self._queries.create_pipeline_stats())

    def drop_tables(self) -> None:
        """Elimina las tablas del pipeline; uso exclusivo para pruebas o reinicio."""
        with self._connection.engine.begin() as connection:
            connection.execute(self._queries.drop_all())
