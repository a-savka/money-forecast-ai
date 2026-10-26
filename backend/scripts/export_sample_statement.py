"""Генерирует пример выписки Т-Банка из синтетического профиля.

uv run python -m scripts.export_sample_statement dropout 3 ../docs/samples/tbank_dropout_3m.csv
"""

import sys
from datetime import date
from pathlib import Path

from app.importers.export import to_tbank_csv
from app.seed.synthetic import generate_profile


def main() -> None:
    profile, months, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    p = generate_profile(profile, end=date.today(), months=months, seed=7)
    # В выписку одной карты попадают операции основного счёта
    txs = [t for t in p.transactions if t.account == 0 and t.category != "savings"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(to_tbank_csv(txs))
    print(f"{out}: {len(txs)} операций")


if __name__ == "__main__":
    main()
