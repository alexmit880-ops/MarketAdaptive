import logging
import time

log = logging.getLogger(__name__)


class PnLTracker:
    def __init__(self):
        self.trades = []  # [{symbol, side, entry, exit, pnl, opened_at, closed_at}]
        self.equity_curve = [0.0]
        log.info("PnLTracker initialized")

    def record_trade(self, symbol, side, entry, exit, size):
        pnl = (exit - entry) * size if side == "LONG" else (entry - exit) * size
        trade = {
            "symbol": symbol,
            "side": side,
            "entry": entry,
            "exit": exit,
            "size": size,
            "pnl": pnl,
            "opened_at": time.time(),
            "closed_at": time.time(),
        }
        self.trades.append(trade)
        self.equity_curve.append(self.equity_curve[-1] + pnl)
        log.info("Trade recorded: %s", trade)
        return trade

    def get_equity_curve(self):
        return self.equity_curve

    def get_total_pnl(self):
        return sum(t["pnl"] for t in self.trades)

    def get_winrate(self):
        wins = sum(1 for t in self.trades if t["pnl"] > 0)
        total = len(self.trades)
        return wins / total if total > 0 else 0.0

    def get_drawdown(self):
        peak = 0.0
        dd = 0.0
        for eq in self.equity_curve:
            peak = max(peak, eq)
            dd = max(dd, peak - eq)
        return dd
