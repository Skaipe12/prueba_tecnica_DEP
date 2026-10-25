"""Tests de CsvLoader con archivos temporales."""

import inspect
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from src.resources.csv_loader import REASON_INVALID_TIMESTAMP, CsvLoader

HEADER = "timestamp,price,user_id\n"


def write_csv(directory: Path, name: str, rows: list[str]) -> Path:
    path = directory / name
    path.write_text(HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def loader(tmp_path: Path) -> CsvLoader:
    return CsvLoader(data_dir=tmp_path)


def test_read_batches_is_lazy_and_respects_size(tmp_path: Path, loader: CsvLoader) -> None:
    rows = [f"1/{day}/2012,{day},1" for day in range(1, 11)]
    path = write_csv(tmp_path, "a.csv", rows)

    batches = loader.read_batches(path, batch_size=4)
    assert inspect.isgenerator(batches)

    first = next(batches)
    assert len(first) == 4
    assert [len(frame) for frame in batches] == [4, 2]


def test_normalize_types(tmp_path: Path, loader: CsvLoader) -> None:
    path = write_csv(tmp_path, "a.csv", ["1/10/2012,50.25,9"])

    frame = next(loader.read_batches(path, batch_size=10))
    row = frame.iloc[0]
    assert row["timestamp"] == pd.Timestamp(2012, 1, 10)
    assert row["price"] == Decimal("50.25")
    assert isinstance(row["price"], Decimal)
    assert row["user_id"] == 9


def test_rows_without_price_are_kept_with_none(tmp_path: Path, loader: CsvLoader) -> None:
    rows = ["1/10/2012,50,9", "1/11/2012,,2", "1/12/2012,abc,3", "1/13/2012,20,10"]
    path = write_csv(tmp_path, "a.csv", rows)

    frames = list(loader.read_batches(path, batch_size=2))
    prices = [price for frame in frames for price in frame["price"]]

    assert prices == [Decimal("50"), None, None, Decimal("20")]
    assert loader.null_price_rows == 2
    assert loader.discarded_rows == 0


def test_rows_without_price_become_null_when_inserted(tmp_path: Path, loader: CsvLoader) -> None:
    path = write_csv(tmp_path, "a.csv", ["1/11/2012,,2", "1/12/2012,,3"])

    records = next(loader.read_batches(path, batch_size=10)).to_dict("records")

    assert [record["price"] for record in records] == [None, None]


def test_invalid_timestamp_rows_are_discarded_with_reason(tmp_path: Path, loader: CsvLoader) -> None:
    rows = ["1/10/2012,50,9", "fecha-mala,40,4", ",,5", "1/13/2012,,10"]
    path = write_csv(tmp_path, "a.csv", rows)

    frames = list(loader.read_batches(path, batch_size=2))
    timestamps = [ts for frame in frames for ts in frame["timestamp"]]

    assert timestamps == [pd.Timestamp(2012, 1, 10), pd.Timestamp(2012, 1, 13)]
    assert loader.discarded_rows == 2
    assert loader.discard_reasons == {REASON_INVALID_TIMESTAMP: 2}
    assert loader.null_price_rows == 1


def test_counters_reset_between_files(tmp_path: Path, loader: CsvLoader) -> None:
    dirty = write_csv(tmp_path, "a.csv", ["1/10/2012,,9", "fecha-mala,10,9"])
    clean = write_csv(tmp_path, "b.csv", ["1/10/2012,10,9"])

    list(loader.read_batches(dirty, batch_size=10))
    list(loader.read_batches(clean, batch_size=10))

    assert loader.discarded_rows == 0
    assert loader.discard_reasons == {}
    assert loader.null_price_rows == 0


def test_missing_user_id_is_kept_as_none(tmp_path: Path, loader: CsvLoader) -> None:
    path = write_csv(tmp_path, "a.csv", ["1/10/2012,10,"])

    frame = next(loader.read_batches(path, batch_size=10))
    assert frame.iloc[0]["user_id"] is None
    assert loader.discarded_rows == 0
