class BreakoutStrategy:
    name = "BREAKOUT"

    def __init__(self, lookback: int = 20):
        self.lookback = lookback
        self.highs = []
        self.lows = []

    def on_candle(self, candle, indicators):
        self.highs.append(candle["high"])
        self.lows.append(candle["low"])

        if len(self.highs) > self.lookback:
            self.highs.pop(0)
            self.lows.pop(0)

        if len(self.highs) < self.lookback:
            return []

        hh = max(self.highs)
        ll = min(self.lows)
        price = candle["close"]

        if price > hh:
            return [{"strategy": self.name, "side": "LONG", "price": price}]

        if price < ll:
            return [{"strategy": self.name, "side": "SHORT", "price": price}]

        return []
