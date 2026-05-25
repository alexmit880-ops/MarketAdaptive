import logging

log = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, balance: float, max_risk_per_trade=0.02, max_total_exposure=0.1):
        self.balance = balance
        self.max_risk_per_trade = max_risk_per_trade
        self.max_total_exposure = max_total_exposure
        log.info(
            "RiskManager initialized (balance=%.2f, risk/trade=%.2f, max exposure=%.2f)",
            balance, max_risk_per_trade, max_total_exposure
        )

    def allow_trade(self, plan: dict, positions: dict) -> bool:
        """
        plan = {"action": "OPEN", "side": "BUY", "price": 100.5}
        positions = {"BTCUSDT": {"side": "LONG", "size": 0.01, "entry": 100.0}}
        """

        # считаем текущую экспозицию
        total_exposure = sum(
            pos["size"] * pos["entry"] for pos in positions.values()
        )
        max_allowed = self.balance * self.max_total_exposure

        if total_exposure >= max_allowed:
            log.warning("RiskManager blocked trade: exposure %.2f >= max %.2f", total_exposure, max_allowed)
            return False

        # риск на сделку
        trade_notional = plan["price"] * 0.01  # пока фиксируем qty=0.01
        max_trade = self.balance * self.max_risk_per_trade

        if trade_notional > max_trade:
            log.warning("RiskManager blocked trade: notional %.2f > max %.2f", trade_notional, max_trade)
            return False

        return True
