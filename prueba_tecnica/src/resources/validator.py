from src.config.constants import CSV_FILES, CSV_TIMESTAMP_FORMAT, DATA_DIR, VALIDATION_FILE
from src.resources.schemas.schemas import BatchResult
from collections.abc import Iterable, Iterator
from src.utils.utils import to_decimal, to_int
from pathlib import Path
import pandas as pd


class Validator:
    """Agrupa las validaciones de los archivos de entrada, los chunks y los batches."""

    @staticmethod
    def validate_files(files: list[Path]) -> None:
        """Lanza FileNotFoundError si no hay archivos que cargar o alguno no existe."""
        if not files:
            raise FileNotFoundError("No hay archivos CSV para cargar")
        missing = [str(path) for path in files if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Archivos no encontrados: {', '.join(missing)}")

    @classmethod
    def validate_inputs(cls, data_dir: Path = DATA_DIR) -> None:
        """Comprueba que existan en data_dir los CSV del reto y validation.csv."""
        cls.validate_files([data_dir / name for name in (*CSV_FILES, VALIDATION_FILE)])

    @staticmethod
    def validate_df(chunk: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
        """Tipa un chunk y descarta las filas sin timestamp válido.

        Devuelve el DataFrame resultante, las filas descartadas y las filas con price nulo.
        """
        timestamps = pd.to_datetime(chunk["timestamp"], format=CSV_TIMESTAMP_FORMAT, errors="coerce")
        valid = timestamps.notna()

        frame = pd.DataFrame(
            {
                "timestamp": timestamps[valid],
                "price": chunk["price"][valid].map(to_decimal),
                "user_id": chunk["user_id"][valid].map(to_int),
            }
        ).reset_index(drop=True)
        return frame, len(chunk) - len(frame), int(frame["price"].isna().sum())

    @staticmethod
    def skip_empty(batches: Iterable[BatchResult]) -> Iterator[BatchResult]:
        """Entrega solo los batches con filas; los vacíos, con todas sus filas descartadas, se omiten."""
        return (batch for batch in batches if batch.rows)
