import logging

log = logging.getLogger(__name__)


class StrategyEngine:
    def __init__(self, strategies: list):
        """
        strategies = [
            EMACrossStrategy(),
            ATRTrendStrategy(),
            RSIReversionStrategy(),
            BreakoutStrategy(),
        ]
        """
        self.strategies = strategies

    def on_candle(self, candle: dict, indicators: dict):
        """
        Вызывает каждую стратегию.
        Стратегия должна вернуть либо None, либо dict:
        {
            "strategy": "ema_cross",
            "signal": "LONG" / "SHORT" / "EXIT",
            "confidence": float
        }
        """

        signals = []

        for strat in self.strategies:
            try:
                sig = strat.on_candle(candle, indicators)
                if sig:
                    signals.append(sig)
            except Exception as e:
                log.exception("Strategy %s failed: %s", strat.__class__.__name__, e)

        return signals
