import asyncio
import logging
from typing import Dict, Any, List

from core.config import CoreConfig
from infra.bybit_rest import BybitREST
from infra.candle_stream import CandleStream
from infra.candle_validator import CandleValidator
from infra.outlier_filter import OutlierFilter
from infra.indicator_cache import IndicatorCache
from infra.time_sync import TimeSync

from engine.strategy_engine import StrategyEngine
from engine.ema_cross import EMACrossStrategy
from engine.atr_trend import ATRTrendStrategy
from engine.rsi_reversion import RSIReversionStrategy
from engine.breakout import BreakoutStrategy

from engine.order_router import OrderRouter
from engine.order_executor import OrderExecutor
from engine.position_manager import PositionManager
from engine.pnl_tracker import PnLTracker
from engine.risk_manager import RiskManager
from engine.position_sync import PositionSync
from engine.kill_switch import KillSwitch

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, cfg: CoreConfig) -> None:
        self.cfg = cfg
        logger.info("=== Orchestrator init started ===")

        self.candle_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

        # Автоматически определяем демо-режим на основе URL из конфигурации,
        # либо принудительно выставляем True для текущей отладки демо-счета.
        base_url_str = self.cfg.exchange.base_url or ""
        demo_flag = "demo" in base_url_str.lower() or True  # True форсирует демо-режим

        self.bybit = BybitREST(
            api_key=self.cfg.exchange.api_key,
            api_secret=self.cfg.exchange.api_secret,
            base_url=self.cfg.exchange.base_url,
            is_demo=demo_flag  # Передача флага в обновленный конструктор BybitREST
        )

        self.candle_stream = CandleStream(
            endpoint=self.cfg.ws.endpoint,
            symbol=self.cfg.symbol,
            interval=self.cfg.ws.interval,
            queue=self.candle_queue,
        )

        self.candle_validator = CandleValidator(symbol=self.cfg.symbol, interval=self.cfg.ws.interval)
        self.outlier_filter = OutlierFilter()
        self.indicator_cache = IndicatorCache(symbol=self.cfg.symbol, interval=self.cfg.ws.interval)

        self.time_sync = TimeSync(self.bybit, interval=10.0)
        self.position_manager = PositionManager(exchange=self.bybit)
        self.pnl_tracker = PnLTracker()

        self.strategy_engine = StrategyEngine(
            strategies=[EMACrossStrategy(), ATRTrendStrategy(), RSIReversionStrategy(), BreakoutStrategy()]
        )

        self.order_router = OrderRouter()
        self.order_executor = OrderExecutor(mode="BYBIT", bybit_client=self.bybit, default_symbol=self.cfg.symbol)

        self.risk_manager = RiskManager(
            balance=self.cfg.risk.balance,
            max_risk_per_trade=self.cfg.risk.max_risk_per_trade,
            max_total_exposure=self.cfg.risk.max_total_exposure,
        )

        self.position_sync = PositionSync(self.bybit, self.position_manager, interval=10.0)
        self.kill_switch = KillSwitch(self.position_manager, self.pnl_tracker)

        self._tasks: List[asyncio.Task] = []
        self._stopping = False

        logger.info("=== Orchestrator init completed ===")

    async def _start_background_tasks(self) -> None:
        logger.info("Starting background tasks...")
        self._tasks.append(asyncio.create_task(self.time_sync.run(), name="time_sync"))
        self._tasks.append(asyncio.create_task(self.position_sync.run(), name="position_sync"))
        self._tasks.append(asyncio.create_task(self.candle_stream.run(), name="candle_stream"))
        logger.info("Background tasks started")

    async def _stop_background_tasks(self) -> None:
        logger.info("Stopping background tasks...")
        self._stopping = True
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("Background tasks stopped")

    async def _process_candle(self, candle: Dict[str, Any]) -> None:
        try:
            if not self.candle_validator.validate(candle):
                return
            if not self.outlier_filter.validate(candle):
                return

            self.indicator_cache.update(candle)
            indicators = self.indicator_cache.get_indicators()
            signals = self.strategy_engine.on_candle(candle, indicators)
            if not signals:
                return

            position = self.position_manager.get_position(self.cfg.symbol)
            plan = self.order_router.route(signals, position, self.cfg.symbol, default_size=0.01)
            if not plan:
                return

            if not self.risk_manager.allow_trade(plan, self.position_manager.positions):
                return

            result = await self.order_executor.execute(plan)
            if not result or result.get("status") != "OK":
                return

            action, side, price, size = plan["action"], plan["side"], plan["price"], plan["size"]

            if action == "OPEN":
                self.position_manager.register_position(self.cfg.symbol, side, size, price)
            elif action == "FLIP":
                old = self.position_manager.get_position(self.cfg.symbol)
                if old:
                    self.pnl_tracker.record_trade(self.cfg.symbol, old["side"], old["entry"], price, old["size"])
                    self.position_manager.unregister_position(self.cfg.symbol)
                self.position_manager.register_position(self.cfg.symbol, side, size, price)

            if self.kill_switch.check():
                logger.error("KillSwitch triggered — stopping trading loop")
                self._stopping = True
        except Exception as e:
            logger.error("Error processing candle: %s", e, exc_info=True)

    async def run(self) -> None:
        """
        Главный цикл жизни робота. 
        Запускает фоновые задачи и удерживает поток, обрабатывая входящие свечи.
        """
        logger.info("=== Orchestrator run started ===")
        self._stopping = False
        await self._start_background_tasks()

        try:
            # Удерживаем метод run активным и обрабатываем очередь свечей из вебсокета
            while not self._stopping:
                # Проверяем, не упала ли одна из фоновых задач, пока мы ждем свечу
                for task in self._tasks:
                    if task.done() and task.exception():
                        exc = task.exception()
                        logger.critical(f"Критическая ошибка в фоновой задаче {task.get_name()}: {exc}", exc_info=exc)
                        self._stopping = True
                        break

                if self._stopping:
                    break

                try:
                    # Таймаут нужен, чтобы цикл регулярно просыпался и проверял статус фоновых задач
                    candle = await asyncio.wait_for(self.candle_queue.get(), timeout=1.0)
                    await self._process_candle(candle)
                    self.candle_queue.task_done()
                except asyncio.TimeoutError:
                    continue  # Очередь пуста, продолжаем проверку флага остановки
                    
        except asyncio.CancelledError:
            logger.info("Orchestrator execution loop received cancellation signal.")
        except Exception as e:
            logger.critical("Fatal crash in main orchestration loop: %s", e, exc_info=True)
        finally:
            # Гарантируем закрытие всех фоновых тасок при любом выходе из цикла
            await self._stop_background_tasks()
            logger.info("=== Orchestrator execution safely terminated ===")