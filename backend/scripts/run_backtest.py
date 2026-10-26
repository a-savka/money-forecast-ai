"""Бэктест стратегий прогноза на синтетических профилях → Markdown/CSV-отчёт.

uv run python -m scripts.run_backtest [--months 6] [--strategies baseline,statistical]
    [--end 2026-10-26] [--out ../docs/backtest]
"""

import argparse
import csv
from datetime import date
from pathlib import Path

from app.config import get_settings
from app.forecasting.backtest import Dataset, StrategyReport, run_backtest
from app.forecasting.data import history_from_synthetic
from app.forecasting.registry import STRATEGIES
from app.forecasting.statements import dataset_from_statements
from app.seed.synthetic import PROFILES, generate_profile

COLUMNS = [
    ("wape", "WAPE", "pct"),
    ("mae", "MAE, ₽", "rub"),
    ("bias", "Смещение", "pct"),
    ("coverage_p10_p90", "Покрытие P10–P90", "pct"),
    ("category_wape", "WAPE по категориям", "pct"),
    ("gap_precision", "Разрыв: precision", "pct"),
    ("gap_recall", "Разрыв: recall", "pct"),
    ("latency_ms", "Время, мс", "num"),
    ("llm_cost_rub", "LLM, ₽ за весь бэктест", "num"),
]


def fmt(value, kind: str) -> str:
    if value is None:
        return "—"
    if kind == "pct":
        return f"{value * 100:.1f}%"
    if kind == "rub":
        return f"{value:,.0f}".replace(",", " ")
    return f"{value:g}"


def markdown(
    reports: list[StrategyReport], datasets: list[str], months: int, source: str = "синтетика"
) -> str:
    titles = {name: s.title for name, s in STRATEGIES.items()}
    cases = reports[0].metrics["cases"]
    lines = [
        "# Бэктест стратегий прогноза",
        "",
        f"Дата: {date.today().isoformat()} · LLM: `{get_settings().llm_provider}` · "
        f"данные: {source} · профили: {', '.join(datasets)} · "
        f"отсечения: 1, 10, 20 число за {months} мес. · случаев на стратегию: {cases}",
        "",
        "Прогноз — сумма трат от даты отсечения до конца месяца; факт — реальные траты "
        "за тот же период. Меньше WAPE/MAE — лучше; покрытие интервала P10–P90 в идеале ≈ 80%.",
        "",
        "| Стратегия | " + " | ".join(t for _, t, _ in COLUMNS) + " |",
        "|---|" + "---:|" * len(COLUMNS),
    ]
    for r in sorted(reports, key=lambda r: r.metrics["wape"]):
        row = [fmt(r.metrics.get(k), kind) for k, _, kind in COLUMNS]
        lines.append(f"| {titles.get(r.strategy, r.strategy)} | " + " | ".join(row) + " |")

    best = min(reports, key=lambda r: r.metrics["wape"])
    lines += [
        "",
        "## Ошибка по профилям (WAPE)",
        "",
        "| Стратегия | " + " | ".join(datasets) + " |",
        "|---|" + "---:|" * len(datasets),
    ]
    for r in reports:
        cells = []
        for ds in datasets:
            sub = [c for c in r.cases if c.dataset == ds]
            actual = sum(c.actual for c in sub) or 1
            cells.append(fmt(sum(abs(c.error) for c in sub) / actual, "pct"))
        lines.append(f"| {titles.get(r.strategy, r.strategy)} | " + " | ".join(cells) + " |")
    lines += [
        "",
        f"**Лучшая по WAPE:** {titles.get(best.strategy, best.strategy)} "
        f"({fmt(best.metrics['wape'], 'pct')}).",
        "",
        (
            "> Синтетика — модельные данные: ML (H3) обучен на похожем генераторе, поэтому его "
            "преимущество здесь завышено. Честное сравнение — на реальных выписках (W4-6)."
            if source == "синтетика"
            else "> Реальные выписки: ML (H3) обучен только на синтетике и этих данных не видел. "
            "В выписках обычно нет начального остатка, поэтому метрики кассового разрыва "
            "здесь не интерпретируем — смотрим на WAPE/MAE и покрытие интервала."
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--strategies", default=",".join(STRATEGIES))
    parser.add_argument("--end", type=date.fromisoformat, default=date.today())
    parser.add_argument("--out", type=Path, default=Path("../docs/backtest"))
    parser.add_argument(
        "--statements", type=Path, help="папка с подпапками-людьми и выписками внутри"
    )
    args = parser.parse_args()

    names = args.strategies.split(",")
    if args.statements:
        datasets = [
            dataset_from_statements(d.name, sorted(f for f in d.iterdir() if f.is_file()))
            for d in sorted(args.statements.iterdir())
            if d.is_dir() and not d.name.startswith(".") and d != args.out
        ]
        for ds in datasets:
            print(f"{ds.name}: {len(ds.history.txs)} операций, {ds.history.days_of_history} дней")
    else:
        datasets = [
            Dataset(k, history_from_synthetic(generate_profile(k, end=args.end), args.end))
            for k in PROFILES
        ]
    reports = run_backtest({n: STRATEGIES[n] for n in names}, datasets, months=args.months)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.md").write_text(
        markdown(
            reports,
            [d.name for d in datasets],
            args.months,
            "реальные выписки" if args.statements else "синтетика",
        ),
        encoding="utf-8",
    )
    with (args.out / "cases.csv").open("w", newline="", encoding="utf-8") as f:
        rows = [{"strategy": r.strategy, **c} for r in reports for c in r.cases_json()]
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Отчёт: {args.out / 'report.md'}, случаи: {args.out / 'cases.csv'}")


if __name__ == "__main__":
    main()
