"""Разбор QR-кода кассового чека (формат ФНС).

Пример строки: t=20261025T1942&s=1245.50&fn=7380440700076549&i=41975&fp=2026408802&n=1
Сумма и дата берутся прямо из QR, без обращения к внешним сервисам.
Позиции чека (что именно куплено) из QR не получить — для этого нужен API ФНС (вне MVP).
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs

# Признак расчёта: 1 — приход (покупка), 2 — возврат прихода
OPERATION_TYPES = {"1": -1, "2": 1, "3": 1, "4": -1}


class ReceiptError(ValueError):
    pass


@dataclass(frozen=True)
class ReceiptQR:
    timestamp: datetime
    amount: Decimal  # со знаком: покупка < 0
    fn: str
    fd: str
    fp: str


def parse_receipt_qr(raw: str) -> ReceiptQR:
    params = {k.lower(): v[0] for k, v in parse_qs(raw.strip(), keep_blank_values=True).items()}
    if "t" not in params or "s" not in params:
        raise ReceiptError("Это не QR-код кассового чека")
    t = params["t"]
    # strptime жадно разбирает «1942» как 19:04:02, поэтому формат выбираем по длине
    fmt = "%Y%m%dT%H%M%S" if len(t) == 15 else "%Y%m%dT%H%M"
    try:
        ts = datetime.strptime(t, fmt)
    except ValueError as exc:
        raise ReceiptError(f"Не удалось разобрать дату чека «{t}»") from exc
    try:
        total = Decimal(params["s"].replace(",", "."))
    except InvalidOperation as exc:
        raise ReceiptError(f"Не удалось разобрать сумму чека «{params['s']}»") from exc
    sign = OPERATION_TYPES.get(params.get("n", "1"), -1)
    return ReceiptQR(
        ts, total * sign, params.get("fn", ""), params.get("i", ""), params.get("fp", "")
    )
