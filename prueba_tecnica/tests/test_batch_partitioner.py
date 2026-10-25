"""Tests de BatchPartitioner."""

from pathlib import Path

import pytest

from src.config.constants import BATCH_SIZE
from src.resources.batch_partitioner import BatchPartitioner
from src.resources.csv_loader import CsvLoader


def write_csv(directory: Path, rows: int) -> Path:
    path = directory / "2012-1.csv"
    lines = [f"1/{day}/2012,{day},1" for day in range(1, rows + 1)]
    path.write_text("timestamp,price,user_id\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_default_batch_size_comes_from_env() -> None:
    assert BatchPartitioner().batch_size == BATCH_SIZE


@pytest.mark.parametrize("batch_size", [0, -5])
def test_invalid_batch_size_raises(batch_size: int) -> None:
    with pytest.raises(ValueError):
        BatchPartitioner(batch_size=batch_size)


def test_partition_numbers_batches_from_one(tmp_path: Path) -> None:
    path = write_csv(tmp_path, rows=7)
    partitioner = BatchPartitioner(batch_size=3)

    batches = list(partitioner.partition(CsvLoader(data_dir=tmp_path), path))

    assert [batch.number for batch in batches] == [1, 2, 3]
    assert [batch.rows for batch in batches] == [3, 3, 1]
    assert all(batch.rows == len(batch.frame) for batch in batches)


def test_batch_larger_than_file_yields_single_batch(tmp_path: Path) -> None:
    path = write_csv(tmp_path, rows=4)
    partitioner = BatchPartitioner(batch_size=10)

    batches = list(partitioner.partition(CsvLoader(data_dir=tmp_path), path))

    assert [(batch.number, batch.rows) for batch in batches] == [(1, 4)]
