from src.utils.utils import format_reasons, format_stats, stats_summary
from src.config.postgres_connection import PostgresConnection
from src.resources.batch_partitioner import BatchPartitioner
from src.config.constants import CSV_FILES, VALIDATION_FILE
from src.resources.metric_analyzer import MetricAnalyzer
from src.resources.schema_manager import SchemaManager
from src.queries.queries import PipelineQueries
from src.resources.csv_loader import CsvLoader
from src.resources.validator import Validator
from src.config.logger import get_logger

logger = get_logger(__name__)


class PipelineService:
    """Orquesta la carga por micro-batches y el seguimiento de estadísticas."""

    def __init__(
        self,
        connection: PostgresConnection,
        loader: CsvLoader,
        partitioner: BatchPartitioner,
        analyzer: MetricAnalyzer,
        queries: PipelineQueries,
        schema: SchemaManager,
    ) -> None:
        self.connection = connection
        self.loader = loader
        self.partitioner = partitioner
        self.analyzer = analyzer
        self.queries = queries
        self.schema = schema
        self.is_ready = False

    def setup(self):
        """Asegura el esquema y reanuda el estado desde la BD."""
        logger.info("batch_size=%s", self.partitioner.batch_size)
        self.schema.create_tables()
        logger.info("Tablas creadas: transactions, pipeline_stats")
        self.analyzer.load_from_db(self.connection, self.queries)
        self.is_ready = True

    def run(self, files = None):
        """Carga los archivos indicados omitiendo los ya cargados."""
        files = files if files is not None else [self.loader.data_dir / name for name in CSV_FILES]
        Validator.validate_files(files)
        if not self.is_ready:
            self.setup()

        loaded = self.loaded_files()
        for path in files:
            if path.name in loaded:
                logger.warning("Archivo %s omitido: ya existe en transactions.source_file", path.name)
                continue
            self.process_file(path)

    def run_validation(self):
        """Pasa validation.csv por el mismo flujo de carga."""
        self.run([self.loader.data_dir / VALIDATION_FILE])

    def report(self, label = "Verificación"):
        """Compara las estadísticas en memoria con las calculadas directamente en la BD."""
        row = self.connection.execute(self.queries.select_verification_stats()).mappings().first()
        memory = stats_summary(self.analyzer.stats)
        database = {key: row[key] for key in memory}
        consistent = memory == database
        logger.info(
            "%s\n  en ejecución : %s\n  base de datos: %s\n  consistent=%s | filas en transactions=%s",
            label,
            format_stats(memory),
            format_stats(database),
            consistent,
            row["total_rows"],
        )
        return {
            "en_ejecucion": memory,
            "base_de_datos": database,
            "consistent": consistent,
            "filas_en_bd": row["total_rows"],
        }

    def process_file(self, path):
        """Carga un archivo en una sola transacción, batch a batch, y loguea su resumen."""
        loaded_rows = 0
        try:
            with self.connection.engine.begin() as connection:
                for batch in Validator.skip_empty(self.partitioner.partition(self.loader, path)):
                    self.process_batch(connection, path, batch)
                    loaded_rows += batch.rows
                connection.execute(self.queries.upsert_pipeline_stats(), self.analyzer.snapshot())
        except Exception:
            logger.exception("Fallo en el archivo %s: transacción revertida, se detiene el pipeline", path.name)
            raise

        loader = self.loader
        if loader.discarded_rows:
            reasons = format_reasons(loader.discard_reasons)
            logger.warning("Archivo %s: %s filas descartadas (%s)", path.name, loader.discarded_rows, reasons)
        logger.info(
            "Archivo %s cargado: %s filas (%s sin price, %s descartadas) | %s",
            path.name,
            loaded_rows,
            loader.null_price_rows,
            loader.discarded_rows,
            format_stats(stats_summary(self.analyzer.stats)),
        )

    def process_batch(self, connection, path, batch):
        """Inserta el batch en la transacción del archivo y actualiza las estadísticas en memoria."""
        rows = batch.frame.assign(source_file=path.name).to_dict("records")
        connection.execute(self.queries.insert_transactions(), rows)
        # Se insertan todas las filas, también las de price NULL, pero solo las que traen precio alimentan las estadísticas
        self.analyzer.update_batch(batch.frame["price"])

        logger.debug("Batch %s de %s: %s filas", batch.number, path.name, batch.rows)

    def loaded_files(self) -> set[str]:
        """Nombres de archivo que ya tienen filas en transactions."""
        return set(self.connection.execute(self.queries.select_loaded_files()).scalars().all())
