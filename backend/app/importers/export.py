"""Экспорт операций в формате выписки Т-Банка — для демо импорта и тестов."""

import csv
import io
from datetime import date

from app.seed.synthetic import SyntheticTransaction

TBANK_HEADERS = [
    "Дата операции",
    "Дата платежа",
    "Номер карты",
    "Статус",
    "Сумма операции",
    "Валюта операции",
    "Сумма платежа",
    "Валюта платежа",
    "Кэшбэк",
    "Категория",
    "MCC",
    "Описание",
    "Бонусы (включая кэшбэк)",
]

SLUG_TO_TBANK = {
    "products": "Супермаркеты",
    "cafe": "Рестораны",
    "delivery": "Фастфуд",
    "transport": "Транспорт",
    "taxi": "Такси",
    "communication": "Мобильная связь",
    "utilities": "Коммунальные услуги",
    "health": "Аптеки",
    "clothes": "Одежда и обувь",
    "marketplace": "Маркетплейсы",
    "entertainment": "Развлечения",
    "education": "Образование",
    "kids": "Детские товары",
    "subscriptions": "Цифровые товары",
    "salary": "Зарплата",
}


def _money(x: object) -> str:
    return f"{float(x):.2f}".replace(".", ",")


def to_tbank_csv(txs: list[SyntheticTransaction], card: str = "*4417") -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL)
    writer.writerow(TBANK_HEADERS)
    for t in sorted(txs, key=lambda t: t.date, reverse=True):
        d: date = t.date
        writer.writerow(
            [
                d.strftime("%d.%m.%Y 12:00:00"),
                d.strftime("%d.%m.%Y"),
                card,
                "OK",
                _money(t.amount),
                "RUB",
                _money(t.amount),
                "RUB",
                "",
                SLUG_TO_TBANK.get(t.category, "Другое"),
                t.mcc or "",
                t.description,
                "0,00",
            ]
        )
    return buf.getvalue().encode("cp1251", errors="replace")
