import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from engine.orchestrator import Orchestrator

log = logging.getLogger(__name__)
app = FastAPI()

# глобальный объект orchestrator
orchestrator: Orchestrator = None


@app.get("/api/positions")
async def get_positions():
    return JSONResponse(orchestrator.position_manager.positions)


@app.get("/api/equity")
async def get_equity():
    return JSONResponse({
        "equity_curve": orchestrator.pnl_tracker.get_equity_curve(),
        "total_pnl": orchestrator.pnl_tracker.get_total_pnl(),
        "drawdown": orchestrator.pnl_tracker.get_drawdown(),
        "winrate": orchestrator.pnl_tracker.get_winrate(),
    })


@app.get("/api/signals")
async def get_signals():
    # можно хранить последние сигналы в orchestrator
    return JSONResponse({"signals": getattr(orchestrator, "last_signals", [])})


@app.get("/api/system")
async def get_system_state():
    return JSONResponse({
        "risk_manager": {
            "balance": orchestrator.risk_manager.balance,
            "max_risk_per_trade": orchestrator.risk_manager.max_risk_per_trade,
            "max_total_exposure": orchestrator.risk_manager.max_total_exposure,
        },
        "kill_switch": orchestrator.kill_switch.is_active(),
    })
