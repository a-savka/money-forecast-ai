"""Обучение глобальной ML-модели H3 на синтетических профилях.

uv run python -m scripts.train_ml_gbm [n_profiles]
"""

import sys

from app.forecasting.strategies.ml_gbm import save_model, train


def main() -> None:
    n_profiles = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    model = train(n_profiles=n_profiles)
    path = save_model(model)
    print(f"Модель сохранена: {path}")
    print(model["meta"])


if __name__ == "__main__":
    main()
