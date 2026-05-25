class EMACrossStrategy:
    name = "EMA_CROSS"

    def on_candle(self, candle, indicators):
        fast = indicators.get("ema_fast")
        slow = indicators.get("ema_slow")

        if fast is None or slow is None:
            return []

        price = candle["close"]

        if fast > slow:
            return [{"strategy": self.name, "side": "LONG", "price": price}]
        elif fast < slow:
            return [{"strategy": self.name, "side": "SHORT", "price": price}]

        return []
