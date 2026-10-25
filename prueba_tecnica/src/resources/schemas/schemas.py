from dataclasses import dataclass
from decimal import Decimal
import pandas as pd

@dataclass
class BatchResult:
    """Micro-batch normalizado con su número dentro del archivo."""

    number: int
    frame: pd.DataFrame
    rows: int


@dataclass
class RunningStats:
    """Estado acumulado de count, suma, mínimo y máximo de price."""

    count: int = 0
    price_sum: Decimal = Decimal("0")
    price_min: Decimal | None = None
    price_max: Decimal | None = None

    @property
    def price_avg(self) -> Decimal | None:
        """Promedio derivado de la suma; None si aún no hay filas."""
        if self.count == 0:
            return None
        return self.price_sum / self.count