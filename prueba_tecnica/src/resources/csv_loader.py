from src.config.constants import (CSV_COLUMNS, 
                                  DATA_DIR,
                                  REASON_INVALID_TIMESTAMP)
from src.resources.validator import Validator
from collections.abc import Iterator
from pathlib import Path
import pandas as pd


class CsvLoader:
    """Lectura de CSV por chunks con normalización de tipos."""

    def __init__(self, data_dir: Path = DATA_DIR) -> None:
        self.data_dir = data_dir
        self.discarded_rows: int = 0
        self.discard_reasons: dict[str, int] = {}
        self.null_price_rows: int = 0

    def read_batches(self, path: Path, batch_size: int) -> Iterator[pd.DataFrame]:
        """Genera DataFrames normalizados de hasta batch_size filas; reinicia los contadores del archivo."""
        self.discarded_rows = 0
        self.discard_reasons = {}
        self.null_price_rows = 0
        reader = pd.read_csv(path, chunksize=batch_size, usecols=list(CSV_COLUMNS), dtype=str)
        with reader:
            for chunk in reader:
                yield self.normalize(chunk)

    def normalize(self, chunk: pd.DataFrame) -> pd.DataFrame:
        """Tipa las columnas, descarta filas sin timestamp válido y deja price en None si no es numérico."""
        frame, discarded, null_prices = Validator.validate_df(chunk)
        if discarded:
            self.discard_reasons[REASON_INVALID_TIMESTAMP] = (
                self.discard_reasons.get(REASON_INVALID_TIMESTAMP, 0) + discarded
            )
        self.discarded_rows += discarded
        self.null_price_rows += null_prices
        return frame
