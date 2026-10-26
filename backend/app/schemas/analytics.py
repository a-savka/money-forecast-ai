from pydantic import BaseModel


class CategoryAmount(BaseModel):
    category_id: int
    amount: float  # положительное число — сумма трат
    count: int
    share: float  # доля от всех трат месяца, 0..1
    prev_amount: float  # за тот же период прошлого месяца


class MonthSummary(BaseModel):
    month: str  # YYYY-MM
    income: float
    expense: float
    net: float
    prev_expense: float
    # Сколько дней месяца прошло (для текущего месяца сравнение идёт «день в день»)
    days_elapsed: int
    days_in_month: int
    by_category: list[CategoryAmount]


class MonthPoint(BaseModel):
    month: str
    income: float
    expense: float
