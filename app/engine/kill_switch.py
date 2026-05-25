import logging

log = logging.getLogger(__name__)


class KillSwitch:
    """
    Останавливает торговлю при критическом дроудауне или других условиях.
    """

    def __init__(self, position_manager, pnl_tracker, max_drawdown_pct: float = 0.3):
        """
        position_manager — нужен, чтобы закрыть позиции
        pnl_tracker — нужен, чтобы смотреть текущий PnL
        max_drawdown_pct — процент дроудауна, при котором стопаем торговлю
        """
        self.position_manager = position_manager
        self.pnl_tracker = pnl_tracker
        self.max_drawdown_pct = max_drawdown_pct

        self.initial_balance = pnl_tracker.initial_balance if hasattr(pnl_tracker, "initial_balance") else 1000.0

    def check(self) -> bool:
        """
        Возвращает True → KillSwitch должен остановить торговлю.
        """

        current_equity = self.pnl_tracker.get_equity()
        if current_equity is None:
            return False

        drawdown = 1 - (current_equity / self.initial_balance)

        if drawdown >= self.max_drawdown_pct:
            log.error(
                "KILLSWITCH TRIGGERED: drawdown %.2f%% (equity=%.2f, initial=%.2f)",
                drawdown * 100,
                current_equity,
                self.initial_balance,
            )

            # Закрываем все позиции
            for sym, pos in list(self.position_manager.positions.items()):
                try:
                    self.position_manager.unregister_position(sym)
                except Exception as e:
                    log.exception("Failed to close position %s: %s", sym, e)

            return True

        return False
