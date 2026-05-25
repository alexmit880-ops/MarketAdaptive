import logging
import time
from typing import Dict, Any, List, Optional

log = logging.getLogger(__name__)

class PositionManager:
    def __init__(self, exchange):
        self.exchange = exchange
        self.positions: Dict[str, Dict[str, Any]] = {}

    def register_position(self, symbol: str, side: str, size: float, entry: float, sl=None, tp=None):
        try:
            self.positions[symbol] = {
                "side": side,
                "size": size,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "opened_at": time.time(),
            }
            log.info("Position registered: %s %s size=%s entry=%s", symbol, side, size, entry)
        except Exception as e:
            log.exception("PositionManager register error: %s", e)

    def unregister_position(self, symbol: str):
        try:
            if symbol in self.positions:
                del self.positions[symbol]
                log.info("Position removed: %s", symbol)
        except Exception as e:
            log.exception("PositionManager unregister error: %s", e)

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            return self.positions.get(symbol)
        except Exception as e:
            log.exception("PositionManager get_position error: %s", e)
            return None

    # --- НОВЫЕ МЕТОДЫ ДЛЯ ПОЧИНКИ POSITION_SYNC ---

    def get_active_symbols(self) -> List[str]:
        """Возвращает список символов, по которым сейчас открыты локальные позиции"""
        try:
            return list(self.positions.keys())
        except Exception as e:
            log.exception("PositionManager get_active_symbols error: %s", e)
            return []

    def get_all_positions(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает весь словарь текущих локальных позиций для сверки параметров"""
        try:
            return self.positions
        except Exception as e:
            log.exception("PositionManager get_all_positions error: %s", e)
            return {}