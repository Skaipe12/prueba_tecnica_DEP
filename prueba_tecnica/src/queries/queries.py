from src.config.constants import TABLE_STATS, TABLE_TRANSACTIONS
from sqlalchemy import text

class PipelineQueries:
    """Catálogo de sentencias SQL del pipeline."""

    def create_transactions(self):
        """Crea la tabla de hechos y su índice por archivo de origen si no existen."""
        return text(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_TRANSACTIONS} (
                id              BIGSERIAL PRIMARY KEY,
                event_timestamp TIMESTAMP     NOT NULL,
                price           NUMERIC(12,2),
                user_id         INTEGER,
                source_file     VARCHAR(64)   NOT NULL,
                loaded_at       TIMESTAMP     NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS ix_{TABLE_TRANSACTIONS}_source_file
                ON {TABLE_TRANSACTIONS} (source_file);
            """
        )

    def create_pipeline_stats(self):
        """Crea la tabla de estado incremental de fila única si no existe."""
        return text(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_STATS} (
                id         SMALLINT      PRIMARY KEY CHECK (id = 1),
                row_count  BIGINT        NOT NULL DEFAULT 0,
                price_sum  NUMERIC(18,2) NOT NULL DEFAULT 0,
                price_min  NUMERIC(12,2),
                price_max  NUMERIC(12,2),
                price_avg  NUMERIC(14,4),
                updated_at TIMESTAMP     NOT NULL DEFAULT NOW()
            );
            """
        )

    def drop_all(self):
        """Elimina las dos tablas del pipeline."""
        return text(f"DROP TABLE IF EXISTS {TABLE_TRANSACTIONS}, {TABLE_STATS};")


    def insert_transactions(self):
        """Inserta una fila de transacción; se ejecuta como executemany por batch."""
        return text(
            f"""
            INSERT INTO {TABLE_TRANSACTIONS} (event_timestamp, price, user_id, source_file)
            VALUES (:timestamp, :price, :user_id, :source_file);
            """
        )

    def upsert_pipeline_stats(self):
        """Crea la fila id=1 al terminar el primer archivo y la actualiza en los siguientes con el snapshot de RunningStats."""
        return text(
            f"""
            INSERT INTO {TABLE_STATS}
                (id, row_count, price_sum, price_min, price_max, price_avg, updated_at)
            VALUES
                (1, :row_count, :price_sum, :price_min, :price_max, :price_avg, NOW())
            ON CONFLICT (id) DO UPDATE SET
                row_count  = EXCLUDED.row_count,
                price_sum  = EXCLUDED.price_sum,
                price_min  = EXCLUDED.price_min,
                price_max  = EXCLUDED.price_max,
                price_avg  = EXCLUDED.price_avg,
                updated_at = EXCLUDED.updated_at;
            """
        )

    def select_pipeline_stats(self):
        """Lee el estado incremental persistido; no devuelve filas hasta que se carga el primer archivo."""
        return text(
            f"""
            SELECT row_count, price_sum, price_min, price_max, price_avg, updated_at
            FROM {TABLE_STATS}
            WHERE id = 1;
            """
        )

    def select_loaded_files(self):
        """Lista los archivos que ya tienen filas en transactions."""
        return text(f"SELECT DISTINCT source_file FROM {TABLE_TRANSACTIONS};")

    def select_verification_stats(self):
        """Calcula count, avg, min y max de price directamente sobre transactions (solo para verificar).

        count usa COUNT(price) y avg se redondea a 4 decimales, igual que las estadísticas en memoria;
        total_rows cuenta además las filas con price NULL.
        """
        return text(
            f"""
            SELECT
                COUNT(price)           AS count,
                ROUND(AVG(price), 4)   AS avg,
                MIN(price)             AS min,
                MAX(price)             AS max,
                COUNT(*)               AS total_rows
            FROM {TABLE_TRANSACTIONS};
            """
        )
