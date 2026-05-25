import asyncio
import logging
from typing import Dict, Any, Set, Optional
from infra.bybit_rest import BybitREST
from engine.position_manager import PositionManager

# Настройка локального логгера в рамках общей структуры ядра
log = logging.getLogger("engine.position_sync")

class PositionSync:
    """
    Institutional-grade воркер реконсиляции позиций.
    
    Обеспечивает непрерывное сопоставление (reconciliation) и синхронизацию
    между реальным биржевым контуром Bybit и локальным кэшем PositionManager.
    Изолирует Alpha-слой от проблемы "призрачных позиций" (zombie positions).
    """
    def __init__(self, bybit_client: BybitREST, position_manager: PositionManager, interval: float = 10.0) -> None:
        self.bybit: BybitREST = bybit_client
        self.pm: PositionManager = position_manager
        self.interval: float = interval
        
        # Управление жизненным циклом асинхронной задачи
        self._is_running: bool = False
        self._main_task: Optional[asyncio.Task] = None
        self._lock: asyncio.Lock = asyncio.Lock()

    def start(self) -> None:
        """
        Запуск воркера как независимой фоновой задачи (Fire-and-Forget).
        Используется, если оркестратор управляет компонентами асинхронно.
        """
        if self._is_running:
            log.warning("PositionSync worker execution skipped: already running.")
            return
        
        self._is_running = True
        self._main_task = asyncio.create_task(self.run())
        log.info("PositionSync background task successfully dispatched via asyncio.create_task.")

    async def run(self) -> None:
        """
        Основной цикл сверки данных (Execution Loop).
        Может быть вызван напрямую через `await sync.run()` в долгоживущих группах задач.
        """
        # Потокобезопасный fail-safe взвод флага
        async with self._lock:
            self._is_running = True
            
        log.info("PositionSync loop initiated cleanly (interval=%s sec)", self.interval)
        
        while self._is_running:
            try:
                # 1. Асинхронное получение текущего слепка позиций с биржевого шлюза
                positions: Optional[Dict[str, Dict[str, Any]]] = await self.bybit.get_positions()
                
                # 2. Извлечение локального состояния для выявления расхождений
                local_active_symbols: Set[str] = set(self.pm.get_active_symbols())
                remote_active_symbols: Set[str] = set()

                # 3. Синхронизация активных и изменившихся позиций
                if positions:
                    for symbol, p in positions.items():
                        remote_active_symbols.add(symbol)
                        
                        # Атомарное обновление/регистрация параметров позиции в State
                        self.pm.register_position(
                            symbol=symbol,
                            side=p["side"],
                            size=p["size"],
                            entry=p["entry"],
                        )
                
                # 4. Двусторонняя реконсиляция: зачистка "зомби-позиций"
                # Если позиция удерживается локально, но отсутствует на бирже — она была закрыта извне
                closed_symbols = local_active_symbols - remote_active_symbols
                for symbol in closed_symbols:
                    log.warning("Reconciliation discrepancy detected: symbol %s closed on venue. Force-clearing local state.", symbol)
                    self.pm.force_close_position(symbol)

                log.debug("PositionSync cycle completed. Shared state is consistent. Active symbols: %s", remote_active_symbols)

            except asyncio.CancelledError:
                # Корректный перехват стандартного механизма отмены задач в asyncio
                log.info("PositionSync loop execution intercepted by CancelledError signal.")
                break
            except AttributeError as ae:
                log.error("Data structure parsing mismatch in PositionSync loop: %s", ae, exc_info=True)
            except Exception as e:
                # Паттерн Error Containment: ошибка одной итерации не должна валить всё ядро
                log.error("Unexpected exception in PositionSync telemetry loop: %s", e, exc_info=True)
            
            # 5. Переход к следующему тику с защитой от race condition при остановке
            try:
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                log.info("PositionSync sleep state broken by cancellation request.")
                break

        log.info("PositionSync loop gracefully finished execution chain.")

    async def stop(self) -> None:
        """
        Компонент Graceful Shutdown инфраструктуры.
        Останавливает цикл и дожидается полной деаллокации ресурсов воркера.
        """
        async with self._lock:
            if not self._is_running:
                log.warning("PositionSync stop requested, but worker is not active.")
                return
            self._is_running = False
            
        log.info("Initiating PositionSync graceful shutdown sequence...")
        
        if self._main_task:
            self._main_task.cancel()
            try:
                # Ожидаем завершения задачи для исключения RuntimeWarning
                await self._main_task
            except asyncio.CancelledError:
                pass # Корректное и ожидаемое завершение
                
        log.info("PositionSync subsystem completely stopped.")