import yaml
import os

# -----------------------------
# Logging config
# -----------------------------
class LoggingConfig:
    def __init__(self, level, file, rotation, retention):
        self.level = level
        self.file = file
        self.rotation = rotation
        self.retention = retention


# -----------------------------
# WebSocket config
# -----------------------------
class WSConfig:
    def __init__(self, endpoint, interval, reconnect_min_delay, reconnect_max_delay,
                 heartbeat_interval, stale_timeout):
        self.endpoint = endpoint
        self.interval = interval
        self.reconnect_min_delay = reconnect_min_delay
        self.reconnect_max_delay = reconnect_max_delay
        self.heartbeat_interval = heartbeat_interval
        self.stale_timeout = stale_timeout


# -----------------------------
# Exchange config
# -----------------------------
class ExchangeConfig:
    def __init__(self, api_key, api_secret, base_url):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url


# -----------------------------
# Risk config
# -----------------------------
class RiskConfig:
    def __init__(self, balance, max_risk_per_trade, max_total_exposure):
        self.balance = balance
        self.max_risk_per_trade = max_risk_per_trade
        self.max_total_exposure = max_total_exposure


# -----------------------------
# Core config
# -----------------------------
class CoreConfig:
    def __init__(self, raw):
        self.env = raw.get("env", "dev")
        self.symbol = raw.get("symbol", "BTCUSDT")

        # Logging
        log = raw.get("logging", {})
        self.logging = LoggingConfig(
            level=log.get("level", "INFO"),
            file=log.get("file", "logs/bot.log"),
            rotation=log.get("rotation", "10 MB"),
            retention=log.get("retention", "7 days"),
        )

        # WS
        ws = raw.get("ws", {})
        self.ws = WSConfig(
            endpoint=ws.get("endpoint"),
            interval=ws.get("interval", "1"),
            reconnect_min_delay=ws.get("reconnect_min_delay", 0.5),
            reconnect_max_delay=ws.get("reconnect_max_delay", 20.0),
            heartbeat_interval=ws.get("heartbeat_interval", 10.0),
            stale_timeout=ws.get("stale_timeout", 3.0),
        )

        # Exchange
        ex = raw.get("exchange", {})
        self.exchange = ExchangeConfig(
            api_key=ex.get("api_key", ""),
            api_secret=ex.get("api_secret", ""),
            base_url=ex.get("base_url", "https://api.bybit.com"),
        )

        # Risk
        risk = raw.get("risk", {})
        self.risk = RiskConfig(
            balance=risk.get("balance", 1000.0),
            max_risk_per_trade=risk.get("max_risk_per_trade", 0.02),
            max_total_exposure=risk.get("max_total_exposure", 0.1),
        )


# -----------------------------
# Loader
# -----------------------------
def load_config(path="configs/config.yaml"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return CoreConfig(raw)
