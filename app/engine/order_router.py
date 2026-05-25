import logging
log = logging.getLogger(__name__)


class OrderRouter:
    """
    Простой, безопасный, детерминированный Router:
    - принимает список сигналов
    - принимает текущую позицию
    - возвращает торговый план (OPEN / FLIP / NONE)
    """

    def route(self, signals, position, symbol: str = None, default_size: float = 0.01):
        try:
            if not signals:
                return None

            # Берём первый сигнал (или позже можно сделать приоритеты)
            signal = signals[0]
            side = signal["side"]
            price = signal["price"]

            # Если позиции нет → OPEN
            if not position:
                return {
                    "action": "OPEN",
                    "side": side,
                    "price": price,
                    "symbol": symbol,
                    "size": default_size,
                }

            # Если есть позиция, но направление другое → FLIP
            if position["side"] != side:
                return {
                    "action": "FLIP",
                    "side": side,
                    "price": price,
                    "symbol": symbol,
                    "size": default_size,
                }

            # Если направление совпадает → ничего не делаем
            return None

        except Exception as e:
            log.exception("OrderRouter error: %s", e)
            return None
