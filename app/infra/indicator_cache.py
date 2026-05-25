import logging
from collections import deque

log = logging.getLogger(__name__)


# Конвертация интервала в секунды
def interval_to_seconds(interval: str) -> int:
    if interval.isdigit():
        return int(interval) * 60
    if interval.endswith("h"):
        return int(interval[:-1]) * 3600
    if interval.endswith("d"):
        return int(interval[:-1]) * 86400
    raise ValueError(f"Unsupported interval: {interval}")


class IndicatorCache:
    def __init__(self, symbol: str, interval: str, maxlen: int = 500):
        self.symbol = symbol
        self.interval = interval
        self.tf = interval_to_seconds(interval)

        # Храним историю свечей
        self.candles = deque(maxlen=maxlen)

        # Кэш индикаторов
        self.indicators = {}

    def update(self, candle: dict):
        """
        candle = {
            "ts": ...,
            "open": ...,
            "high": ...,
            "low": ...,
            "close": ...,
            "volume": ...
        }
        """
        self.candles.append(candle)

        # Пересчёт индикаторов
        closes = [c["close"] for c in self.candles]

        if len(closes) >= 14:
            self.indicators["rsi"] = self._calc_rsi(closes, 14)

        if len(closes) >= 20:
            self.indicators["ema20"] = self._ema(closes, 20)

        if len(closes) >= 50:
            self.indicators["ema50"] = self._ema(closes, 50)

        if len(closes) >= 14:
            self.indicators["atr"] = self._calc_atr()

    def get_indicators(self) -> dict:
        return self.indicators

    # --------------------------
    # Индикаторы
    # --------------------------

    def _ema(self, values, period):
        k = 2 / (period + 1)
        ema = values[0]
        for v in values[1:]:
            ema = v * k + ema * (1 - k)
        return ema

    def _calc_rsi(self, closes, period):
        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i - 1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(-diff)

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calc_atr(self, period=14):
        if len(self.candles) < period + 1:
            return None

        trs = []
        for i in range(1, period + 1):
            c1 = self.candles[-i]
            c0 = self.candles[-i - 1]

            high = c1["high"]
            low = c1["low"]
            prev_close = c0["close"]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            trs.append(tr)

        return sum(trs) / period
