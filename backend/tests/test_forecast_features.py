from datetime import date

import pytest

from app.forecasting.data import history_from_synthetic
from app.forecasting.engine import build_context, month_end
from app.forecasting.features import RecurringItem, detect_recurring
from app.seed.synthetic import generate_profile

AS_OF = date(2026, 10, 12)


@pytest.fixture(scope="module")
def young():
    return history_from_synthetic(generate_profile("young", end=date(2026, 10, 26)), AS_OF)


def test_history_cut_at_as_of(young):
    assert young.txs["date"].max().date() <= AS_OF
    assert young.days_of_history > 300


def test_detects_rent_salary_and_subscriptions(young):
    items, idx = detect_recurring(young.txs, AS_OF)
    names = {i.name for i in items}
    assert "Перевод: аренда квартиры" in names
    assert "Зарплата ООО «ДАТАЛАБ»" in names
    assert "ЯНДЕКС ПЛЮС" in names
    rent = next(i for i in items if i.name.startswith("Перевод: аренда"))
    assert rent.period == "monthly" and rent.day_of_month == 3 and rent.amount == -38000
    # Обычные магазины не считаются регулярными платежами
    assert not any("ПЯТЁРОЧКА" in n for n in names)
    assert len(idx) >= sum(i.occurrences for i in items)


def test_upcoming_monthly():
    item = RecurringItem(
        "k", "Аренда", "housing", "expense", -100, "monthly", 30, 3, date(2026, 10, 3), 6, 1
    )
    assert item.upcoming(date(2026, 10, 12), date(2026, 12, 31)) == [
        date(2026, 11, 3),
        date(2026, 12, 3),
    ]
    # Платёж этого месяца запаздывает на 2 дня → ожидаем завтра
    late = RecurringItem(
        "k", "ЗП", "salary", "income", 100, "monthly", 30, 10, date(2026, 9, 10), 6, 1
    )
    assert late.upcoming(date(2026, 10, 12), date(2026, 10, 31)) == [date(2026, 10, 13)]


def test_context_income_dates(young):
    ctx = build_context(young, month_end(AS_OF))
    assert ctx.days[0] == date(2026, 10, 13) and ctx.days[-1] == date(2026, 10, 31)
    # Аванс 25-го числа (в выходной — в пятницу)
    assert any(d.day in (23, 24, 25) for d in ctx.income_dates)
    var = ctx.variable_expenses()
    assert (var["spend"] > 0).all()
    assert not var["description"].str.contains("аренда").any()
