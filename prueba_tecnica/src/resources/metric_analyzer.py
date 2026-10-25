from src.resources.schemas.schemas import RunningStats
from src.utils.utils import round_decimal
from src.config.logger import get_logger
from decimal import Decimal


logger = get_logger(__name__)


class MetricAnalyzer:
    """Mantiene RunningStats actualizando solo con los valores nuevos."""

    def __init__(self, initial = None):
        self._stats = initial if initial is not None else RunningStats()

    @property
    def stats(self):
        """Estado actual en memoria."""
        return self._stats

    def update(self, price: Decimal):
        """Incorpora un precio al estado con cuatro operaciones O(1)."""
        stats = self._stats
        stats.count += 1
        stats.price_sum += price
        # En la primera fila min y max son None: el propio precio inicializa ambos.
        stats.price_min = price if stats.price_min is None else min(stats.price_min, price)
        stats.price_max = price if stats.price_max is None else max(stats.price_max, price)

    def update_batch(self, prices):
        """Aplica update fila a fila sin tocar la base de datos; los precios None se ignoran."""
        for price in prices:
            if price is not None:
                self.update(price)

    def load_from_db(self, connection, queries):
        """Reconstruye el estado desde pipeline_stats para reanudar una ejecución."""
        row = connection.execute(queries.select_pipeline_stats()).mappings().first()
        if row is None or not row["row_count"]:
            self._stats = RunningStats()
            return

        self._stats = RunningStats(
            count=int(row["row_count"]),
            price_sum=Decimal(row["price_sum"]),
            price_min=Decimal(row["price_min"]),
            price_max=Decimal(row["price_max"]),
        )
        logger.info(
            "Estado reanudado desde BD: %s filas, avg=%s, min=%s, max=%s",
            self._stats.count,
            round_decimal(self._stats.price_avg),
            self._stats.price_min,
            self._stats.price_max,
        )

    def snapshot(self):
        """Devuelve el estado con las claves que espera upsert_pipeline_stats."""
        return {
            "row_count": self._stats.count,
            "price_sum": self._stats.price_sum,
            "price_min": self._stats.price_min,
            "price_max": self._stats.price_max,
            "price_avg": self._stats.price_avg,
        }
