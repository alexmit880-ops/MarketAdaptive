import asyncio
import json
import logging
import websockets  # pip install websockets

log = logging.getLogger(__name__)


class CandleStream:
    def __init__(self, endpoint: str, symbol: str, interval: str, queue: asyncio.Queue):
        self.endpoint = endpoint
        self.symbol = symbol
        self.interval = interval
        self.queue = queue
        self._stop = False

    def stop(self):
        self._stop = True

    async def run(self):
        while not self._stop:
            try:
                async with websockets.connect(self.endpoint, ping_interval=20) as ws:
                    sub_msg = {
                        "op": "subscribe",
                        "args": [f"kline.{self.interval}.{self.symbol}"],
                    }
                    await ws.send(json.dumps(sub_msg))
                    log.info("Subscribed to %s %s", self.symbol, self.interval)

                    async for msg in ws:
                        if self._stop:
                            break

                        data = json.loads(msg)
                        candle = self._parse_candle(data)

                        if candle:
                            await self.queue.put(candle)

            except Exception as e:
                log.exception("CandleStream error, reconnecting: %s", e)
                await asyncio.sleep(3)

    # ---------------------------------------------------------
    # Парсер свечей Bybit v5
    # ---------------------------------------------------------
    def _parse_candle(self, data: dict):
        try:
            # Bybit v5 формат:
            # {
            #   "topic": "kline.1.BTCUSDT",
            #   "data": [{
            #       "start": 1716282000000,
            #       "open": "68000",
            #       "high": "68100",
            #       "low": "67900",
            #       "close": "68050",
            #       "volume": "123.45"
            #   }]
            # }

            topic = data.get("topic") or data.get("arg", {}).get("topic")
            if not topic or "kline" not in topic:
                return None

            arr = data.get("data")
            if not arr or not isinstance(arr, list):
                return None

            k = arr[0]

            # FIX: timestamp → секунды
            ts = int(k["start"]) // 1000

            return {
                "ts": ts,
                "open": float(k["open"]),
                "high": float(k["high"]),
                "low": float(k["low"]),
                "close": float(k["close"]),
                "volume": float(k["volume"]),
            }

        except Exception as e:
            log.exception("Failed to parse candle: %s", e)
            return None
