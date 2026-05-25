class BaseStrategy:
    def on_candle(self, candle, indicators):
        """
        candle = dict(...)
        indicators = {
            "ema_fast": float,
            "ema_slow": float,
            "atr": float
        }
        """
        raise NotImplementedError
