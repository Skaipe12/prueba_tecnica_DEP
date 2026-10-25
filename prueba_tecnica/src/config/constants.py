from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

DATA_DIR: Path = Path(__file__).resolve().parents[2] / "data"
CSV_FILES = ("2012-1.csv", "2012-2.csv", "2012-3.csv", "2012-4.csv", "2012-5.csv")
VALIDATION_FILE = "validation.csv"
BATCH_SIZE = 10

TABLE_TRANSACTIONS = "transactions"
TABLE_STATS = "pipeline_stats"
CSV_COLUMNS = ("timestamp", "price", "user_id")
CSV_TIMESTAMP_FORMAT = "%m/%d/%Y"
REASON_INVALID_TIMESTAMP = "timestamp vacío o con formato inválido"