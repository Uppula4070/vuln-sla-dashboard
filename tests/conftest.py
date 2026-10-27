import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HEADER = ["id", "title", "asset", "owner", "severity", "cve", "source", "found_date", "closed_date", "status",
          "exception_expires"]  # fmt: skip


@pytest.fixture
def sample_csv() -> Path:
    return ROOT / "samples" / "findings.csv"


@pytest.fixture
def make_csv(tmp_path):
    """Write rows (dicts with only the fields a test cares about) to a CSV and return its path."""

    def _make(rows: list[dict], name: str = "f.csv") -> Path:
        path = tmp_path / name
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=HEADER)
            writer.writeheader()
            for i, row in enumerate(rows, 1):
                base = {"id": f"V-{i}", "title": "t", "asset": "a", "owner": "team-a", "severity": "high",
                        "found_date": "2026-01-01", "status": "open"}  # fmt: skip
                writer.writerow({**base, **row})
        return path

    return _make
