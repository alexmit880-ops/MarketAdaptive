import asyncio
import logging

log = logging.getLogger(__name__)

class TimeSync:
    def __init__(self, bybit_client, interval: float = 10.0) -> None:
        self.bybit = bybit_client
        self.interval = interval

    async def run(self) -> None:
        log.info("TimeSync started (interval=%s sec)", self.interval)
        while True:
            try:
                # Убрали .session и добавили await, так как метод теперь асинхронный
                data = await self.bybit.get_server_time()
                log.debug("TimeSync OK: %s", data)
            except Exception as e:
                log.error("TimeSync error: %s", e)
                
            await asyncio.sleep(self.interval)