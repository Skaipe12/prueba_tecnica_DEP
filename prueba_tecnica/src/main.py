from src.config.postgres_connection import PostgresConnection
from src.resources.batch_partitioner import BatchPartitioner
from src.services.pipeline_service import PipelineService
from src.resources.metric_analyzer import MetricAnalyzer
from src.resources.schema_manager import SchemaManager
from src.queries.queries import PipelineQueries
from src.resources.csv_loader import CsvLoader
from src.resources.validator import Validator



def build_pipeline() -> PipelineService:
    """Construye PipelineService inyectando todas sus dependencias."""
    connection = PostgresConnection()
    queries = PipelineQueries()
    
    return PipelineService(
        connection=connection,
        loader=CsvLoader(),
        partitioner=BatchPartitioner(),
        analyzer=MetricAnalyzer(),
        queries=queries,
        schema=SchemaManager(connection, queries),
    )


if __name__ == "__main__":
    Validator.validate_inputs()
    pipeline = build_pipeline()
    try:
        pipeline.run()
        pipeline.report("Verificación tras los 5 archivos")
        pipeline.run_validation()
        pipeline.report("Verificación tras validation.csv")
    finally:
        pipeline.connection.dispose()
