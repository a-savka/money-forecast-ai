from datetime import date

import pytest

from app.forecasting.backtest import Dataset, cutoffs_for, metrics, run_backtest
from app.forecasting.data import history_from_synthetic
from app.forecasting.registry import STRATEGIES
from app.seed.synthetic import generate_profile

END = date(2026, 10, 26)


@pytest.fixture(scope="module")
def dataset():
    return Dataset("young", history_from_synthetic(generate_profile("young", end=END), END))


def test_cutoffs_only_complete_months(dataset):
    cuts = cutoffs_for(dataset, months=2)
    assert cuts == [
        date(2026, 8, 1),
        date(2026, 8, 10),
        date(2026, 8, 20),
        date(2026, 9, 1),
        date(2026, 9, 10),
        date(2026, 9, 20),
    ]


def test_cut_balance_matches_history(dataset):
    cut = dataset.cut(date(2026, 9, 1))
    direct = history_from_synthetic(generate_profile("young", end=END), date(2026, 9, 1))
    assert cut.balance == pytest.approx(direct.balance)
    assert cut.txs["date"].max() <= direct.txs["date"].max()


def test_backtest_metrics(dataset):
    reports = run_backtest(
        {k: STRATEGIES[k] for k in ("baseline", "statistical")}, [dataset], months=2
    )
    by_name = {r.strategy: r.metrics for r in reports}
    assert by_name["statistical"]["cases"] == 6
    for m in by_name.values():
        assert 0 <= m["wape"] < 1
        assert 0 <= m["coverage_p10_p90"] <= 1
    # H1 знает о регулярных платежах — точнее наивного среднего
    assert by_name["statistical"]["wape"] < by_name["baseline"]["wape"]


def test_metrics_empty():
    assert metrics([]) == {"cases": 0}


def test_api(client, auth):
    r = client.post(
        "/experiments/backtest",
        json={"strategies": ["baseline", "statistical"], "dataset": "me", "months": 2},
        headers=auth,
    )
    assert r.status_code == 200, r.text
    runs = r.json()
    assert [x["strategy"] for x in runs] == ["baseline", "statistical"]
    assert runs[0]["cases"] and "wape" in runs[0]["metrics"]
    listed = client.get("/experiments", headers=auth).json()
    assert len(listed) == 2
    bad = client.post("/experiments/backtest", json={"strategies": ["nope"]}, headers=auth)
    assert bad.status_code == 404
