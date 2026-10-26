from pathlib import Path

import pytest

from app.forecasting.statements import dataset_from_statements
from app.importers.statement import StatementError

FIXTURES = Path(__file__).parent / "fixtures"


def test_dataset_from_statement():
    ds = dataset_from_statements("person1", [FIXTURES / "tbank.csv"])
    assert ds.name == "person1"
    assert len(ds.history.txs) > 0
    assert set(ds.history.txs["kind"]) <= {"expense", "income", "transfer"}


def test_bad_file(tmp_path):
    bad = tmp_path / "x.csv"
    bad.write_text("nothing here\n1;2\n", encoding="utf-8")
    with pytest.raises(StatementError):
        dataset_from_statements("p", [bad])
