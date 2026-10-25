from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from src.resources.schemas.schemas import RunningStats
import pandas as pd

def to_decimal(value: object) -> Decimal | None:
    """Convierte a Decimal desde texto; None si viene vacío, no es numérico o no es finito."""
    if value is None or pd.isna(value):
        return None
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def to_int(value: object) -> int | None:
    """Convierte a int nativo de Python; None si viene vacío o no es un entero válido."""
    number = to_decimal(value)
    if number is None or number != number.to_integral_value():
        return None
    return int(number)


def stats_summary(stats: RunningStats) -> dict[str, int | Decimal | None]:
    """Resume las estadísticas con las mismas claves y redondeo que la consulta de verificación."""
    return {"count": stats.count, "avg": round_decimal(stats.price_avg), "min": stats.price_min, "max": stats.price_max}


def format_stats(summary: dict) -> str:
    """Escribe un resumen de estadísticas en una línea, por ejemplo 'count=20 avg=59.65 min=14 max=97'."""
    return " ".join(f"{key}={value}" for key, value in summary.items())


def format_reasons(reasons: dict[str, int]) -> str:
    """Une los motivos de descarte con su conteo, por ejemplo 'motivo: 2; otro: 1'."""
    return "; ".join(f"{reason}: {count}" for reason, count in reasons.items())


def round_decimal(value: Decimal | None, places: int = 4) -> Decimal | None:
    """Redondea un Decimal a places decimales con HALF_UP, igual que NUMERIC en PostgreSQL."""
    if value is None:
        return None
    return Decimal(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
