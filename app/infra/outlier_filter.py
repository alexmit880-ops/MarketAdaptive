import logging
import statistics

log = logging.getLogger(__name__)


class OutlierFilter:
    def __init__(self, window=50, max_deviation=4.0):
        """
        window — сколько последних свечей использовать для оценки нормальности
        max_deviation — сколько σ допускается (обычно 3–5)
        """
        self.window = window
        self.max_dev = max_deviation
        self.prices = []

    def validate(self, candle: dict) -> bool:
        close = candle["close"]

        # 1) Накопление истории
        self.prices.append(close)
        if len(self.prices) < self.window:
            return True  # пока нет статистики — пропускаем

        if len(self.prices) > self.window:
            self.prices.pop(0)

        # 2) Статистическая проверка
        mean = statistics.mean(self.prices)
        stdev = statistics.pstdev(self.prices)

        if stdev == 0:
            return True  # рынок стоял на месте

        z_score = abs(close - mean) / stdev

        if z_score > self.max_dev:
            log.warning(
                "Outlier detected: close=%s mean=%.4f stdev=%.4f z=%.2f",
                close, mean, stdev, z_score
            )
            return False

        return True
