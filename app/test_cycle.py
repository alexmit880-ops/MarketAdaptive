import asyncio
import logging
import sys
from infra.bybit_rest import BybitREST

# Настраиваем вывод логов в консоль
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def main():
    # Замени эти заглушки на свои настоящие ключи от демо-счета Bybit
    api_key = "YOUR_DEMO_API_KEY"
    api_secret = "YOUR_DEMO_API_SECRET"
    base_url = "https://api-demo.bybit.com"

    # Инициализируем наш исправленный класс
    bybit = BybitREST(api_key, api_secret, base_url, is_demo=True)

    logging.info("=== Тестовый цикл сделки начат ===")

    # Шаг 1: Проверяем позиции ДО начала торговли (должно быть пусто)
    initial_positions = await bybit.get_positions("BTCUSDT")
    logging.info("Позиции ДО теста: %s", initial_positions)

    # Шаг 2: Открываем позицию РЫНОЧНЫМ ордером (Market)
    # Для рыночного ордера цена (price) не важна, передаем 0, так как Bybit исполнит его по текущей цене
    logging.info("Отправляем ордер на ПОКУПКУ (LONG)...")
    result_open = await bybit.create_order(
        symbol="BTCUSDT",
        side="Buy",
        qty=0.01,
        price=0,  
        order_type="Market",
        reduce_only=False
    )
    logging.info("Результат открытия: %s", result_open)

    # Даем бирже 1 секунду на обработку и обновление информации
    await asyncio.sleep(1)

    # Шаг 3: Проверяем, появилась ли позиция
    positions_after_open = await bybit.get_positions("BTCUSDT")
    logging.info("Позиции ПОСЛЕ ПОКУПКИ: %s", positions_after_open)

    # Шаг 4: Закрываем позицию РЫНОЧНЫМ ордером (Market)
    logging.info("Отправляем ордер на ПРОДАЖУ (CLOSE LONG)...")
    result_close = await bybit.create_order(
        symbol="BTCUSDT",
        side="Sell",
        qty=0.01,
        price=0,  
        order_type="Market",
        reduce_only=True  # Теперь это сработает, так как позиция реально открыта
    )
    logging.info("Результат закрытия: %s", result_close)

    # Даем бирже 1 секунду на обновление статуса
    await asyncio.sleep(1)

    # Шаг 5: Проверяем позиции ПОСЛЕ закрытия (должно снова стать пусто)
    positions_after_close = await bybit.get_positions("BTCUSDT")
    logging.info("Позиции ПОСЛЕ ЗАКРЫТИЯ: %s", positions_after_close)

    logging.info("=== Тестовый цикл сделки завершён ===")

    # Безопасно закрываем сетевую сессию
    await bybit.close()

if __name__ == "__main__":
    # Запуск асинхронного теста
    asyncio.run(main())