"""Генератор синтетических финансовых профилей.

Используется для демо, бэктеста стратегий прогноза и обучения ML-модели.
Профили соответствуют целевой аудитории из питча: молодой специалист, семья,
фрилансер, «бросивший учёт». Генерация детерминирована при фиксированном seed.
"""

from __future__ import annotations

import calendar
import math
import random
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from decimal import Decimal

Merchant = tuple[str, str | None]  # (описание, MCC)


@dataclass(frozen=True)
class SpendPattern:
    """Переменные траты в категории: число покупок ~ Poisson, сумма ~ lognormal."""

    category: str
    merchants: list[Merchant]
    per_week: float
    amount_mean: float
    amount_sd: float
    # Множители частоты по дням недели (пн..вс)
    weekday: tuple[float, ...] = (1, 1, 1, 1, 1, 1, 1)
    # Множитель частоты в первые 5 дней после поступления дохода
    payday_boost: float = 1.0
    account: int = 0


@dataclass(frozen=True)
class RecurringSpec:
    description: str
    category: str
    amount: float
    day: int
    mcc: str | None = None
    jitter: float = 0.0  # относительное отклонение суммы
    account: int = 0


@dataclass(frozen=True)
class IncomeSpec:
    description: str
    category: str
    amount: float
    day: int
    jitter: float = 0.0
    account: int = 0


@dataclass(frozen=True)
class IrregularIncome:
    """Нерегулярный доход фрилансера: N поступлений в месяц случайного размера."""

    descriptions: list[str]
    per_month: tuple[int, int]
    amount: tuple[float, float]


@dataclass(frozen=True)
class AccountSpec:
    name: str
    bank_name: str


@dataclass(frozen=True)
class ProfileSpec:
    key: str
    title: str
    description: str
    accounts: list[AccountSpec]
    patterns: list[SpendPattern]
    recurring: list[RecurringSpec]
    incomes: list[IncomeSpec] = field(default_factory=list)
    irregular_income: IrregularIncome | None = None
    # Остаток на картах в начале месяца; излишек уходит на накопительный счёт
    target_balance: float = 20000
    # Месяц отпуска (1..12) и сумма разовой крупной траты
    vacation: tuple[int, float] | None = None
    # Доля дохода, которую человек в среднем тратит (калибрует интенсивность трат)
    expense_ratio: float = 0.97


@dataclass(frozen=True)
class SyntheticTransaction:
    date: date
    amount: Decimal
    description: str
    mcc: str | None
    category: str
    account: int
    is_recurring: bool = False


@dataclass
class SyntheticProfile:
    spec: ProfileSpec
    start: date
    end: date
    transactions: list[SyntheticTransaction]
    balances_initial: list[Decimal]


WEEKEND_FUN = (0.7, 0.7, 0.8, 0.9, 1.4, 1.8, 1.3)
WORKDAYS = (1.2, 1.2, 1.2, 1.2, 1.1, 0.4, 0.3)
WEEKEND_SHOP = (0.8, 0.8, 0.9, 1.0, 1.1, 1.5, 1.3)

PRODUCTS: list[Merchant] = [
    ("ПЯТЁРОЧКА", "5411"),
    ("ПЕРЕКРЁСТОК", "5411"),
    ("ВКУСВИЛЛ", "5411"),
    ("МАГНИТ", "5411"),
    ("ЛЕНТА", "5411"),
]
CAFE: list[Merchant] = [
    ("ШОКОЛАДНИЦА", "5812"),
    ("ВКУСНО И ТОЧКА", "5814"),
    ("COFFEE LIKE", "5814"),
    ("ТЕРЕМОК", "5814"),
]
DELIVERY: list[Merchant] = [("ЯНДЕКС ЕДА", "5814"), ("DELIVERY CLUB", "5814"), ("САМОКАТ", "5499")]
TAXI: list[Merchant] = [("YANDEX.GO", "4121"), ("CITYMOBIL", "4121")]
TRANSPORT: list[Merchant] = [("МЕТРОПОЛИТЕН", "4111"), ("МОСГОРТРАНС", "4111")]
FUEL: list[Merchant] = [("АЗС ЛУКОЙЛ", "5541"), ("АЗС ГАЗПРОМНЕФТЬ", "5541")]
MARKETPLACE: list[Merchant] = [("WILDBERRIES", "5399"), ("OZON", "5399"), ("ЯНДЕКС МАРКЕТ", "5399")]
CLOTHES: list[Merchant] = [("LAMODA", "5651"), ("GLORIA JEANS", "5651"), ("ZARINA", "5621")]
HEALTH: list[Merchant] = [("АПТЕКА 36,6", "5912"), ("ГОРЗДРАВ", "5912"), ("ИНВИТРО", "8071")]
FUN: list[Merchant] = [("КИНОМАКС", "7832"), ("КАРО ФИЛЬМ", "7832"), ("STEAM", "5816")]
KIDS: list[Merchant] = [("ДЕТСКИЙ МИР", "5641"), ("ИГРУШКИ HAPPY", "5945")]


PROFILES: dict[str, ProfileSpec] = {
    "young": ProfileSpec(
        key="young",
        title="Молодой специалист",
        description="24 года, аналитик, снимает квартиру, часто заказывает доставку.",
        accounts=[AccountSpec("Т-Банк Black", "Т-Банк"), AccountSpec("СберКарта", "Сбер")],
        incomes=[
            IncomeSpec("Зарплата ООО «ДАТАЛАБ»", "salary", 52000, 10),
            IncomeSpec("Аванс ООО «ДАТАЛАБ»", "salary", 38000, 25, account=1),
        ],
        recurring=[
            RecurringSpec("Перевод: аренда квартиры", "housing", 38000, 3),
            RecurringSpec("МТС мобильная связь", "communication", 650, 15, "4814"),
            RecurringSpec("ДОМ.RU интернет", "communication", 750, 18, "4814"),
            RecurringSpec("ЯНДЕКС ПЛЮС", "subscriptions", 399, 7, "5968"),
            RecurringSpec("КИНОПОИСК", "subscriptions", 299, 21, "5968", account=1),
            RecurringSpec("ФИТНЕС ДДХ абонемент", "health", 3900, 12, "7997"),
        ],
        patterns=[
            SpendPattern("products", PRODUCTS, 3.0, 1300, 0.5, WEEKEND_SHOP),
            SpendPattern("cafe", CAFE, 2.5, 650, 0.5, WEEKEND_FUN, 1.4),
            SpendPattern("delivery", DELIVERY, 2.2, 1100, 0.4, WEEKEND_FUN, 1.6),
            SpendPattern("taxi", TAXI, 1.8, 480, 0.5, WEEKEND_FUN, 1.3, account=1),
            SpendPattern("transport", TRANSPORT, 7.0, 65, 0.05, WORKDAYS),
            SpendPattern("marketplace", MARKETPLACE, 1.3, 2200, 0.8, WEEKEND_SHOP, 1.8),
            SpendPattern("clothes", CLOTHES, 0.25, 4500, 0.6, WEEKEND_SHOP, 2.0),
            SpendPattern("entertainment", FUN, 0.8, 900, 0.5, WEEKEND_FUN, 1.5, account=1),
            SpendPattern("health", HEALTH, 0.4, 900, 0.7),
        ],
        target_balance=55000,
        vacation=(7, 45000),
    ),
    "family": ProfileSpec(
        key="family",
        title="Семья",
        description="Пара 34 и 32 года, ребёнок 4 года, ипотека, общий бюджет.",
        accounts=[AccountSpec("СберКарта", "Сбер"), AccountSpec("Альфа-Карта", "Альфа-Банк")],
        incomes=[
            IncomeSpec("Зарплата АО «ТЕХНОПРОМ»", "salary", 98000, 5),
            IncomeSpec("Аванс АО «ТЕХНОПРОМ»", "salary", 42000, 20),
            IncomeSpec("Зарплата ГБОУ Школа №1520", "salary", 61000, 10, account=1),
        ],
        recurring=[
            RecurringSpec("Погашение ипотеки Сбербанк", "credit", 54300, 6),
            RecurringSpec("ЖКУ Москва", "utilities", 7800, 20, "4900", jitter=0.12),
            RecurringSpec("Детский сад: родительская плата", "kids", 6200, 1, "8211"),
            RecurringSpec("Развивающие занятия «Умка»", "education", 5600, 15, "8299"),
            RecurringSpec("МТС семейный тариф", "communication", 1450, 12, "4814"),
            RecurringSpec("РОСТЕЛЕКОМ интернет", "communication", 890, 16, "4814"),
            RecurringSpec("ЯНДЕКС ПЛЮС Мульти", "subscriptions", 449, 9, "5968", account=1),
            RecurringSpec("ОСАГО/КАСКО рассрочка", "transport", 3200, 25, "6300", account=1),
        ],
        patterns=[
            SpendPattern("products", PRODUCTS, 4.5, 2300, 0.55, WEEKEND_SHOP),
            SpendPattern("kids", KIDS, 0.8, 2100, 0.6, WEEKEND_SHOP, 1.3),
            SpendPattern("transport", FUEL, 1.2, 2800, 0.25, account=1),
            SpendPattern("cafe", CAFE, 1.0, 1800, 0.5, WEEKEND_FUN, 1.3),
            SpendPattern("delivery", DELIVERY, 0.8, 1600, 0.4, WEEKEND_FUN),
            SpendPattern("marketplace", MARKETPLACE, 1.8, 2400, 0.8, WEEKEND_SHOP, 1.5, 1),
            SpendPattern("health", HEALTH, 0.9, 1400, 0.8),
            SpendPattern("clothes", CLOTHES, 0.35, 5200, 0.6, WEEKEND_SHOP, 1.6, account=1),
            SpendPattern("entertainment", FUN, 0.5, 2200, 0.5, WEEKEND_FUN),
        ],
        target_balance=45000,
        expense_ratio=0.95,
        vacation=(8, 120000),
    ),
    "freelancer": ProfileSpec(
        key="freelancer",
        title="Фрилансер",
        description="29 лет, самозанятый дизайнер, доход нерегулярный.",
        accounts=[AccountSpec("Т-Банк Black", "Т-Банк"), AccountSpec("Озон Банк", "Озон Банк")],
        irregular_income=IrregularIncome(
            descriptions=[
                "Перевод от ООО «Студия Пиксель»",
                "Оплата по договору ИП Смирнов",
                "Перевод от клиента (Behance)",
                "Оплата заказа Kwork",
            ],
            per_month=(1, 4),
            amount=(12000, 75000),
        ),
        recurring=[
            RecurringSpec("Перевод: аренда квартиры", "housing", 32000, 1),
            RecurringSpec("Налог НПД (Мой налог)", "other", 3500, 25, jitter=0.4),
            RecurringSpec("Adobe Creative Cloud", "subscriptions", 1990, 4, "5734"),
            RecurringSpec("Figma Professional", "subscriptions", 1300, 11, "5734"),
            RecurringSpec("БИЛАЙН связь", "communication", 550, 17, "4814"),
            RecurringSpec("Коворкинг «Рабочая станция»", "other", 6500, 2, "7399"),
        ],
        patterns=[
            SpendPattern("products", PRODUCTS, 3.2, 1200, 0.5, WEEKEND_SHOP),
            SpendPattern("cafe", CAFE, 3.0, 520, 0.4, payday_boost=1.5),
            SpendPattern("delivery", DELIVERY, 1.5, 1000, 0.4, WEEKEND_FUN, 1.7),
            SpendPattern("taxi", TAXI, 1.0, 450, 0.5, WEEKEND_FUN, 1.5),
            SpendPattern("transport", TRANSPORT, 3.0, 65, 0.05, WORKDAYS),
            SpendPattern("marketplace", MARKETPLACE, 1.0, 2600, 0.9, WEEKEND_SHOP, 2.0, 1),
            SpendPattern("education", [("SKILLBOX", "8299"), ("STEPIK", "8299")], 0.15, 3500, 0.6),
            SpendPattern("entertainment", FUN, 0.6, 800, 0.5, WEEKEND_FUN, 1.6),
            SpendPattern("health", HEALTH, 0.3, 900, 0.7),
        ],
        target_balance=85000,
    ),
    "dropout": ProfileSpec(
        key="dropout",
        title="«Бросивший» учёт",
        description="27 лет, менеджер, импульсивные покупки после зарплаты, есть кредит.",
        accounts=[AccountSpec("СберКарта", "Сбер"), AccountSpec("Т-Банк Платинум", "Т-Банк")],
        incomes=[
            IncomeSpec("Зарплата ООО «РИТЕЙЛ ГРУПП»", "salary", 41000, 5),
            IncomeSpec("Аванс ООО «РИТЕЙЛ ГРУПП»", "salary", 30000, 20, account=1),
        ],
        recurring=[
            RecurringSpec("Погашение кредита Т-Банк", "credit", 8900, 14, account=1),
            RecurringSpec("Перевод маме: коммуналка", "transfers", 5000, 8),
            RecurringSpec("ТЕЛЕ2 связь", "communication", 500, 22, "4814"),
            RecurringSpec("VK МУЗЫКА", "subscriptions", 199, 3, "5968"),
            RecurringSpec("IVI", "subscriptions", 399, 26, "5968"),
        ],
        patterns=[
            SpendPattern("products", PRODUCTS, 3.5, 950, 0.55, WEEKEND_SHOP),
            SpendPattern("delivery", DELIVERY, 3.0, 950, 0.45, WEEKEND_FUN, 2.0),
            SpendPattern("cafe", CAFE, 2.0, 700, 0.5, WEEKEND_FUN, 1.8),
            SpendPattern("taxi", TAXI, 2.5, 420, 0.5, WEEKEND_FUN, 1.8, account=1),
            SpendPattern("marketplace", MARKETPLACE, 2.5, 1900, 0.9, WEEKEND_SHOP, 2.6, 1),
            SpendPattern("clothes", CLOTHES, 0.4, 3800, 0.6, WEEKEND_SHOP, 2.5, account=1),
            SpendPattern("entertainment", FUN, 1.2, 1100, 0.6, WEEKEND_FUN, 2.0),
            SpendPattern("transport", TRANSPORT, 5.0, 65, 0.05, WORKDAYS),
            SpendPattern("health", HEALTH, 0.3, 700, 0.7),
        ],
        target_balance=32000,
        expense_ratio=1.0,
    ),
}


def _poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def _lognormal(rng: random.Random, mean: float, sd: float) -> float:
    """Lognormal с заданным средним и относительным разбросом sd."""
    sigma = math.sqrt(math.log(1 + sd**2))
    mu = math.log(mean) - sigma**2 / 2
    return rng.lognormvariate(mu, sigma)


def _money(x: float) -> Decimal:
    return Decimal(str(round(x))) if x >= 100 else Decimal(f"{x:.2f}")


def _shift_to_workday(d: date) -> date:
    """Зарплата, выпавшая на выходной, приходит в пятницу."""
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _month_day(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def _months(start: date, end: date) -> list[tuple[int, int]]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


VACATION_DESCRIPTIONS = ("АВИАБИЛЕТЫ АЭРОФЛОТ", "ОТЕЛЬ BOOKING")
SEASONAL = {12: 1.3, 1: 0.85, 3: 1.05, 5: 1.05}  # декабрь — подарки, январь — «после праздников»


def _period(end: date, months: int) -> date:
    start = (end.replace(day=1) - timedelta(days=1)).replace(day=1)
    for _ in range(months - 2):
        start = (start - timedelta(days=1)).replace(day=1)
    return start


def _simulate(
    spec: ProfileSpec, start: date, end: date, seed: int, scale: float
) -> list[SyntheticTransaction]:
    rng = random.Random(f"{spec.key}:{seed}")
    txs: list[SyntheticTransaction] = []

    def add(d: date, amount: float, desc: str, mcc: str | None, cat: str, acc: int, rec=False):
        if start <= d <= end:
            txs.append(SyntheticTransaction(d, _money(amount), desc, mcc, cat, acc, rec))

    # Доходы
    paydays: set[date] = set()
    for y, m in _months(start, end):
        for inc in spec.incomes:
            d = _shift_to_workday(_month_day(y, m, inc.day))
            amount = inc.amount * (1 + rng.uniform(-inc.jitter, inc.jitter))
            add(d, amount, inc.description, None, inc.category, inc.account, True)
            paydays.add(d)
        if spec.irregular_income:
            ii = spec.irregular_income
            last = calendar.monthrange(y, m)[1]
            for _ in range(rng.randint(*ii.per_month)):
                d = _shift_to_workday(date(y, m, rng.randint(1, last)))
                amount = round(rng.uniform(*ii.amount), -2)
                acc = 1 if len(spec.accounts) > 1 and rng.random() < 0.3 else 0
                add(d, amount, rng.choice(ii.descriptions), None, "freelance", acc)
                paydays.add(d)

    # Регулярные платежи
    for y, m in _months(start, end):
        for r in spec.recurring:
            d = _month_day(y, m, r.day)
            amount = r.amount * (1 + rng.uniform(-r.jitter, r.jitter))
            add(d, -amount, r.description, r.mcc, r.category, r.account, True)

    # Отпуск — разовая крупная трата
    if spec.vacation:
        v_month, v_amount = spec.vacation
        for y, m in _months(start, end):
            if m == v_month:
                # Отпуск оплачивается из накоплений
                flight, hotel = VACATION_DESCRIPTIONS
                for d, part, desc, mcc in ((10, 0.6, flight, "4511"), (14, 0.4, hotel, "7011")):
                    add(date(y, m, d), v_amount * part, SAVINGS_IN, None, "savings", 0)
                    add(date(y, m, d), -v_amount * part, desc, mcc, "entertainment", 0)

    # Переменные траты
    day = start
    while day <= end:
        after_payday = any(timedelta(0) <= day - p <= timedelta(days=4) for p in paydays)
        season = SEASONAL.get(day.month, 1.0)
        for pat in spec.patterns:
            lam = pat.per_week / 7 * pat.weekday[day.weekday()] * season * scale
            if after_payday:
                lam *= pat.payday_boost
            for _ in range(_poisson(rng, lam)):
                desc, mcc = rng.choice(pat.merchants)
                amount = _lognormal(rng, pat.amount_mean, pat.amount_sd)
                add(day, -amount, desc, mcc, pat.category, pat.account)
        day += timedelta(days=1)

    return txs


def generate_profile(
    spec: ProfileSpec | str,
    *,
    end: date | None = None,
    months: int = 12,
    seed: int = 42,
) -> SyntheticProfile:
    if isinstance(spec, str):
        spec = PROFILES[spec]
    end = end or date.today()
    start = _period(end, months)

    # Двухпроходная калибровка: подбираем интенсивность переменных трат так,
    # чтобы расходы составляли expense_ratio от доходов за период.
    txs = _simulate(spec, start, end, seed, 1.0)
    income = sum(float(t.amount) for t in txs if t.amount > 0 and t.category != "savings")
    expenses = [t for t in txs if t.amount < 0]
    is_fixed = [t.is_recurring or t.description in VACATION_DESCRIPTIONS for t in expenses]
    fixed = -sum(float(t.amount) for t, f in zip(expenses, is_fixed, strict=True) if f)
    variable = -sum(float(t.amount) for t, f in zip(expenses, is_fixed, strict=True) if not f)
    target_variable = income * spec.expense_ratio - fixed
    if variable > 0 and target_variable > 0:
        scale = min(2.0, max(0.3, target_variable / variable))
        txs = _simulate(spec, start, end, seed, scale)

    # Внутри дня сначала доходы, затем расходы
    txs.sort(key=lambda t: (t.date, -t.amount))
    txs = _rebalance_accounts(spec, txs)
    initial = _initial_balances(spec, txs)
    txs = _sweep_to_savings(spec, txs, initial)
    return SyntheticProfile(spec, start, end, txs, initial)


def _rebalance_accounts(
    spec: ProfileSpec, txs: list[SyntheticTransaction]
) -> list[SyntheticTransaction]:
    """Переносит переменные траты на другой счёт, если на «своём» денег заметно меньше.

    Так балансы отдельных карт не уезжают в минус, хотя доход и траты
    распределены между банками неравномерно.
    """
    n = len(spec.accounts)
    if n < 2:
        return txs
    running = [0.0] * n
    out: list[SyntheticTransaction] = []
    for t in txs:
        if t.amount < 0 and not t.is_recurring:
            richest = max(range(n), key=lambda i: running[i])
            if running[t.account] < running[richest] - 3000:
                t = replace(t, account=richest)
        running[t.account] += float(t.amount)
        out.append(t)
    return out


def _initial_balances(spec: ProfileSpec, txs: list[SyntheticTransaction]) -> list[Decimal]:
    """Начальный остаток на картах = target_balance, распределённый по счетам поровну."""
    n = len(spec.accounts)
    share = (Decimal(str(spec.target_balance)) / n).quantize(Decimal("1"))
    return [share] * n


SAVINGS_OUT = "Перевод на накопительный счёт"
SAVINGS_IN = "Перевод с накопительного счёта"


def _sweep_to_savings(
    spec: ProfileSpec, txs: list[SyntheticTransaction], initial: list[Decimal]
) -> list[SyntheticTransaction]:
    """1-го числа остаток на картах выравнивается до target_balance через накопительный счёт.

    Излишек уходит в накопления, нехватка покрывается из них — как делают люди,
    у которых есть «копилка». Такие переводы имеют категорию savings и не считаются
    ни доходом, ни расходом.
    """
    balances = list(initial)
    cap = Decimal(str(spec.target_balance))
    out: list[SyntheticTransaction] = []
    current_month: tuple[int, int] | None = None
    for t in txs:
        month = (t.date.year, t.date.month)
        if month != current_month:
            if current_month is not None:
                diff = (cap - sum(balances)).quantize(Decimal("1"))
                if diff != 0:
                    if diff > 0:
                        acc = min(range(len(balances)), key=lambda i: balances[i])
                        desc = SAVINGS_IN
                    else:
                        acc = max(range(len(balances)), key=lambda i: balances[i])
                        desc = SAVINGS_OUT
                    day = t.date.replace(day=1)
                    out.append(SyntheticTransaction(day, diff, desc, None, "savings", acc))
                    balances[acc] += diff
            current_month = month
        balances[t.account] += t.amount
        out.append(t)
    return out


def random_profile_spec(seed: int) -> ProfileSpec:
    """Случайная вариация одного из базовых профилей — для обучения глобальной ML-модели."""
    rng = random.Random(seed)
    base = PROFILES[rng.choice(list(PROFILES))]
    scale = rng.uniform(0.6, 1.5)
    patterns = [
        replace(
            p,
            per_week=p.per_week * rng.uniform(0.6, 1.5),
            amount_mean=p.amount_mean * scale * rng.uniform(0.8, 1.25),
        )
        for p in base.patterns
    ]
    incomes = [
        replace(i, amount=i.amount * scale, day=max(1, min(28, i.day + rng.randint(-3, 3))))
        for i in base.incomes
    ]
    recurring = [
        replace(r, amount=r.amount * scale * rng.uniform(0.8, 1.2)) for r in base.recurring
    ]
    return replace(
        base,
        key=f"random_{seed}",
        title=f"Случайный пользователь #{seed}",
        patterns=patterns,
        incomes=incomes,
        recurring=recurring,
        expense_ratio=rng.uniform(0.85, 1.05),
        target_balance=base.target_balance * scale,
    )
