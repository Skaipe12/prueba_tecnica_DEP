from src.resources.schemas.schemas import BatchResult
from src.resources.csv_loader import CsvLoader
from src.config.constants import BATCH_SIZE


class BatchPartitioner:
    """Entrega los chunks numerados de un archivo con un tamaño de batch fijo."""

    def __init__(self, batch_size = BATCH_SIZE):
        if batch_size < 1:
            raise ValueError("batch_size debe ser >= 1")
        self.batch_size = batch_size

    def partition(self, loader: CsvLoader, path):
        """Entrega los batches normalizados del archivo numerados desde 1."""
        for number, frame in enumerate(loader.read_batches(path, self.batch_size), start=1):
            yield BatchResult(number=number, frame=frame, rows=len(frame))
