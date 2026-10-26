from app.forecasting.base import ForecastStrategy
from app.forecasting.strategies.baseline import BaselineStrategy
from app.forecasting.strategies.statistical import StatisticalStrategy

STRATEGIES: dict[str, ForecastStrategy] = {
    s.name: s for s in [BaselineStrategy(), StatisticalStrategy()]
}
DEFAULT_STRATEGY = "statistical"
