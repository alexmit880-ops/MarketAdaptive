import os
import asyncio
from dotenv import load_dotenv

from core.config import load_config
from core.logging import setup_logging
from core.orchestrator import Orchestrator

# 1) Загружаем .env ПЕРЕД os.getenv
load_dotenv()

print("API KEY:", os.getenv("BYBIT_API_KEY"))

async def async_main():
    cfg = load_config()
    setup_logging(cfg.logging)

    orch = Orchestrator(cfg)
    await orch.run()

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
