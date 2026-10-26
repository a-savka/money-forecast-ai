from app.forecasting.base import ForecastStrategy
from app.forecasting.strategies.baseline import BaselineStrategy
from app.forecasting.strategies.ml_gbm import MLGBMStrategy
from app.forecasting.strategies.stat_llm import StatLLMStrategy
from app.forecasting.strategies.statistical import StatisticalStrategy

STRATEGIES: dict[str, ForecastStrategy] = {
    s.name: s
    for s in [BaselineStrategy(), StatisticalStrategy(), StatLLMStrategy(), MLGBMStrategy()]
}
DEFAULT_STRATEGY = "statistical"
