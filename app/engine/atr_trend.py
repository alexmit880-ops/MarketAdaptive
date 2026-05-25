class ATRTrendStrategy:
    name = "ATR_TREND"

    def on_candle(self, candle, indicators):
        fast = indicators.get("ema_fast")
        slow = indicators.get("ema_slow")
        atr = indicators.get("atr")

        if fast is None or slow is None or atr is None:
            return []

        price = candle["close"]

        # тренд + фильтр волатильности
        if fast > slow and atr > 0:
            return [{"strategy": self.name, "side": "LONG", "price": price}]

        if fast < slow and atr > 0:
            return [{"strategy": self.name, "side": "SHORT", "price": price}]

        return []
