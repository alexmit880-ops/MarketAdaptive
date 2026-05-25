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
    """
    ОПТИМИЗАЦИЯ: Инкрементальные вычисления индикаторов вместо полного пересчета.
    - EMA вычисляется инкрементально (O(1) вместо O(n))
    - RSI вычисляется только при достаточном количестве свечей
    - ATR кэшируется
    """
    def __init__(self, symbol: str, interval: str, maxlen: int = 500):
        self.symbol = symbol
        self.interval = interval
        self.tf = interval_to_seconds(interval)

        # Храним историю свечей
        self.candles = deque(maxlen=maxlen)

        # Кэш индикаторов
        self.indicators = {}
        
        # ОПТИМИЗАЦИЯ: Кэш для инкрементальных вычислений EMA
        self._ema20_value = None
        self._ema50_value = None
        self._ema_k20 = 2 / (20 + 1)  # Предвычисленный коэффициент
        self._ema_k50 = 2 / (50 + 1)

    def update(self, candle: dict):
        """
        ОПТИМИЗАЦИЯ: Вместо полного пересчета, вычисляем инкрементально.
        """
        self.candles.append(candle)
        close = candle["close"]

        # RSI - вычисляем только при наличии достаточных данных
        if len(self.candles) >= 14:
            self.indicators["rsi"] = self._calc_rsi_incremental()
        
        # EMA20 - инкрементальное вычисление
        if len(self.candles) == 20:
            # Первый раз: простая средняя
            closes = [c["close"] for c in list(self.candles)[-20:]]
            self._ema20_value = sum(closes) / 20
            self.indicators["ema20"] = self._ema20_value
        elif len(self.candles) > 20:
            # Инкрементальное обновление
            self._ema20_value = close * self._ema_k20 + self._ema20_value * (1 - self._ema_k20)
            self.indicators["ema20"] = self._ema20_value

        # EMA50 - инкрементальное вычисление
        if len(self.candles) == 50:
            # Первый раз: простая средняя
            closes = [c["close"] for c in list(self.candles)[-50:]]
            self._ema50_value = sum(closes) / 50
            self.indicators["ema50"] = self._ema50_value
        elif len(self.candles) > 50:
            # Инкрементальное обновление
            self._ema50_value = close * self._ema_k50 + self._ema50_value * (1 - self._ema_k50)
            self.indicators["ema50"] = self._ema50_value

        # ATR
        if len(self.candles) >= 14:
            self.indicators["atr"] = self._calc_atr()

    def get_indicators(self) -> dict:
        return self.indicators

    # --------------------------
    # Индикаторы
    # --------------------------

    def _calc_rsi_incremental(self):
        """Оптимизированный RSI - только за последние 14 свечей"""
        if len(self.candles) < 14:
            return None
            
        candle_list = list(self.candles)
        closes = [c["close"] for c in candle_list[-14:]]
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

        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calc_atr(self, period=14):
        """ATR - вычисляем только за последние period свечей"""
        if len(self.candles) < period + 1:
            return None

        trs = []
        candle_list = list(self.candles)
        
        for i in range(len(candle_list) - period, len(candle_list)):
            c1 = candle_list[i]
            c0 = candle_list[i - 1]

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
