class RSIReversionStrategy:
    name = "RSI_REV"

    def on_candle(self, candle, indicators):
        rsi = indicators.get("rsi")
        if rsi is None:
            return []

        price = candle["close"]

        # контртренд
        if rsi < 30:
            return [{"strategy": self.name, "side": "LONG", "price": price}]

        if rsi > 70:
            return [{"strategy": self.name, "side": "SHORT", "price": price}]

        return []
