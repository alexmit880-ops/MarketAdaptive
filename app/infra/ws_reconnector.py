import asyncio
import logging
import time
import aiohttp

log = logging.getLogger(__name__)


class WSReconnector:
    def __init__(
        self,
        endpoint: str,
        heartbeat_interval: float = 10.0,
        stale_timeout: float = 3.0,
        reconnect_min_delay: float = 0.5,
        reconnect_max_delay: float = 20.0,
    ):
        self.endpoint = endpoint
        self.heartbeat_interval = heartbeat_interval
        self.stale_timeout = stale_timeout
        self.reconnect_min_delay = reconnect_min_delay
        self.reconnect_max_delay = reconnect_max_delay

        self.ws = None
        self.last_msg_ts = 0.0
        self._stop = False

    async def _connect(self):
        """Создаёт новое WS‑подключение."""
        session = aiohttp.ClientSession()
        try:
            self.ws = await session.ws_connect(self.endpoint, heartbeat=self.heartbeat_interval)
            self.last_msg_ts = time.time()
            log.info("WS connected: %s", self.endpoint)
            return session
        except Exception as e:
            log.error("WS connect error: %s", e)
            await session.close()
            return None

    async def _listen(self):
        """Слушает входящие сообщения."""
        async for msg in self.ws:
            self.last_msg_ts = time.time()

            if msg.type == aiohttp.WSMsgType.TEXT:
                # Здесь позже будет обработка тиков/свечей
                pass

            elif msg.type == aiohttp.WSMsgType.ERROR:
                log.error("WS error: %s", msg.data)
                break

    async def _check_stale(self):
        """Проверяет, не устарели ли данные."""
        if time.time() - self.last_msg_ts > self.stale_timeout:
            log.warning("WS stale data detected — reconnecting")
            return False
        return True

    async def run(self):
        """Основной цикл WS Reconnector."""
        delay = self.reconnect_min_delay

        while not self._stop:
            session = await self._connect()
            if session is None:
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.reconnect_max_delay)
                continue

            try:
                listen_task = asyncio.create_task(self._listen())

                while True:
                    await asyncio.sleep(1)

                    if not await self._check_stale():
                        break

                    if listen_task.done():
                        log.warning("WS listener stopped — reconnecting")
                        break

            except Exception as e:
                log.error("WS loop error: %s", e)

            finally:
                try:
                    await session.close()
                except:
                    pass

                log.info("WS reconnecting...")
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.reconnect_max_delay)

        log.info("WS Reconnector stopped")

    def stop(self):
        self._stop = True
