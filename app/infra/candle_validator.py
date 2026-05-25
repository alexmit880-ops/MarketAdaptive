import logging
import time

log = logging.getLogger(__name__)


class CandleValidator:
    def __init__(self, symbol: str, interval: str, timeframe_sec: int = None):
        self.symbol = symbol
        self.interval = interval

        # интервал в секундах
        if timeframe_sec:
            self.tf = timeframe_sec
        else:
            self.tf = self._interval_to_seconds(interval)

        self.last_ts = None

    def _interval_to_seconds(self, interval: str) -> int:
        if interval.isdigit():
            return int(interval) * 60
        if interval.endswith("h"):
            return int(interval[:-1]) * 3600
        if interval.endswith("d"):
            return int(interval[:-1]) * 86400
        raise ValueError(f"Unsupported interval: {interval}")

    def validate(self, candle: dict) -> bool:
        ts = candle["ts"]

        # 1) timestamp не должен быть в будущем
        if ts > time.time() + 5:
            log.warning("Candle rejected: timestamp from future (%s)", ts)
            return False

        # 2) первая свеча — принимаем
        if self.last_ts is None:
            self.last_ts = ts
            return True

        # 3) обновление текущей свечи — принимаем, но НЕ обновляем last_ts
        if ts == self.last_ts:
            return False  # просто игнорируем обновления

        # 4) новая свеча — принимаем
        if ts > self.last_ts:
            self.last_ts = ts
            return True

        # 5) назад по времени — отклоняем
        if ts < self.last_ts:
            log.warning("Candle rejected: timestamp backwards (%s < %s)", ts, self.last_ts)
            return False

        return True
