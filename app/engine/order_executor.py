import logging
from typing import Optional
from infra.bybit_rest import BybitREST

log = logging.getLogger(__name__)


class OrderExecutor:
    def __init__(self, mode: str = "BYBIT",
                 bybit_client: Optional[BybitREST] = None,
                 default_symbol: Optional[str] = None):

        self.mode = mode.upper()
        self.bybit = bybit_client
        self.default_symbol = default_symbol

        log.info("OrderExecutor initialized mode=%s", self.mode)

    async def execute(self, plan: dict) -> dict:
        try:
            log.info("Executing plan: %s", plan)

            action = plan["action"]
            side = plan["side"]
            price = plan["price"]
            symbol = plan.get("symbol") or self.default_symbol
            size = float(plan.get("size", 0.01))

            if self.mode != "BYBIT":
                return {"status": "ERROR", "reason": "invalid_mode"}

            bybit_side = "Buy" if side == "LONG" else "Sell"
            reduce_only = action == "CLOSE"

            resp = self.bybit.create_order(
                symbol=symbol,
                side=bybit_side,
                qty=size,
                price=price,
                order_type="Limit",
                reduce_only=reduce_only,
            )

            if resp.get("status") != "OK":
                log.error("Bybit order failed: %s", resp)
                return {"status": "ERROR", "raw": resp}

            log.info("Bybit order success: %s", resp)
            return {"status": "OK", "raw": resp}

        except Exception as e:
            log.exception("OrderExecutor fatal error: %s", e)
            return {"status": "ERROR", "reason": "fatal_exception"}
