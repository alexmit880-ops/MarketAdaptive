class EMACrossStrategy:
    name = "EMA_CROSS"

    def on_candle(self, candle, indicators):
        # ИСПРАВКА: ema20 и ema50 вместо ema_fast и ema_slow
        fast = indicators.get("ema20")
        slow = indicators.get("ema50")

        if fast is None or slow is None:
            return []

        price = candle["close"]

        if fast > slow:
            return [{"strategy": self.name, "side": "LONG", "price": price}]
        elif fast < slow:
            return [{"strategy": self.name, "side": "SHORT", "price": price}]

        return []
