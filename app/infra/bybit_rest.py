import asyncio
import logging
import time
import hmac
import hashlib
import json
from typing import Dict, Any, Optional

import aiohttp

# Настройка локального логгера
logger = logging.getLogger("Infrastructure.BybitREST")

class BybitREST:
    """
    Класс для работы с REST API Bybit v5.
    Автоматически синхронизирует время и создает цифровые подписи.
    """
    def __init__(self, api_key: str, api_secret: str, base_url: str = "", is_demo: bool = True, is_testnet: bool = False):
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        self.time_offset = 0
        
        # Точное разделение серверов: Демо, Тестнет или Боевой
        if is_demo:
            self.base_url = "https://api-demo.bybit.com"
        elif is_testnet:
            self.base_url = "https://api-testnet.bybit.com"
        else:
            self.base_url = base_url.rstrip("/") if base_url else "https://api.bybit.com"
            
        logger.info("BybitREST: Инициализация. Сервер: %s", self.base_url)
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            resolver = aiohttp.AsyncResolver(nameservers=["1.1.1.1", "8.8.8.8"])
            connector = aiohttp.TCPConnector(resolver=resolver, ttl_dns_cache=300)
            self.session = aiohttp.ClientSession(connector=connector)
        return self.session

    def _generate_signature(self, timestamp: str, recv_window: str, param_str: str) -> str:
        # Склейка строки строго по документации Bybit v5: timestamp + api_key + recv_window + params
        val = timestamp + self.api_key + recv_window + param_str
        # Выводим в лог точный вид строки, которую мы подписываем, для визуального контроля
        logger.info("ОТЛАДКА подписи. Строка для хэша: -> %s", val)
        return hmac.new(self.api_secret.encode("utf-8"), val.encode("utf-8"), hashlib.sha256).hexdigest()

    async def sync_clock(self):
        try:
            start_time = int(time.time() * 1000)
            res = await self.get_server_time()
            end_time = int(time.time() * 1000)
            if res and res.get("retCode") == 0:
                server_time = int(res["result"]["timeNano"]) // 1000000
                latency = (end_time - start_time) // 2
                self.time_offset = server_time - start_time - latency
                logger.info("BybitREST: Часы синхронизированы. Сдвиг ПК: %d ms", self.time_offset)
        except Exception as e:
            logger.error("Не удалось синхронизировать часы: %s", e)

    async def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, auth_required: bool = True) -> Dict[str, Any]:
        session = await self._get_session()
        if auth_required and self.time_offset == 0 and path != "/v5/market/time":
            await self.sync_clock()

        url = f"{self.base_url}{path}"
        timestamp = str(int(time.time() * 1000) + self.time_offset)
        recv_window = "20000"
        
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}

        if method == "GET":
            str_params = {}
            for k, v in clean_params.items():
                if isinstance(v, bool):
                    str_params[k] = "true" if v else "false"
                else:
                    str_params[k] = str(v)
            param_str = "&".join([f"{k}={v}" for k, v in sorted(str_params.items())]) if str_params else ""
            req_payload = None
        else:
            param_str = json.dumps(clean_params, separators=(",", ":")) if clean_params else ""
            req_payload = param_str

        headers = {"Content-Type": "application/json"}
        if auth_required:
            signature = self._generate_signature(timestamp, recv_window, param_str)
            headers.update({
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-RECV-WINDOW": recv_window,
            })

        try:
            if method == "GET":
                full_url = url + ("?" + param_str if param_str else "")
                async with session.get(full_url, headers=headers, timeout=10) as response:
                    raw_text = await response.text()
                    # Если нам вернулся HTML код ошибки вместо JSON, мы поймаем это здесь
                    if not raw_text.strip().startswith("{"):
                        logger.error("Биржа вернула не JSON ответ! Код статуса HTTP: %d", response.status)
                        logger.error("Текст ответа биржи (первые 200 символов): %s", raw_text[:200])
                        return {"retCode": -1, "retMsg": f"HTML response with status {response.status}"}
                    return json.loads(raw_text)
            else:
                async with session.post(url, data=req_payload, headers=headers, timeout=10) as response:
                    raw_text = await response.text()
                    if not raw_text.strip().startswith("{"):
                        logger.error("Биржа вернула не JSON ответ на POST! Код статуса HTTP: %d", response.status)
                        return {"retCode": -1, "retMsg": f"HTML response with status {response.status}"}
                    return json.loads(raw_text)
        except Exception as e:
            logger.error("Ошибка сети при запросе (%s %s): %s", method, path, e)
            return {"retCode": -1, "retMsg": str(e)}

    async def get_server_time(self) -> Dict[str, Any]:
        return await self._request("GET", "/v5/market/time", auth_required=False)

    async def get_positions(self, symbol: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        params = {"category": "linear"}
        if symbol:
            params["symbol"] = symbol
        else:
            params["settleCoin"] = "USDT"
        response = await self._request("GET", "/v5/position/list", params=params)
        if not response or response.get("retCode") != 0 or "result" not in response:
            return {}
        result = {}
        for pos in response.get("result", {}).get("list", []):
            size = float(pos.get("size", 0.0))
            if size == 0.0:
                continue
            result[pos["symbol"]] = {
                "side": "LONG" if pos.get("side") == "Buy" else "SHORT",
                "size": size,
                "entry": float(pos.get("avgPrice", 0.0)),
            }
        return result

    async def create_order(self, symbol: str, side: str, qty: float, price: float, order_type: str = "Limit", reduce_only: bool = False) -> Dict[str, Any]:
        body = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": str(qty),
            "price": str(price) if order_type == "Limit" else "0",
            "timeInForce": "GoodTillCancel",
            "reduceOnly": reduce_only,
        }
        response = await self._request("POST", "/v5/order/create", params=body)
        if not response or response.get("retCode") != 0:
            return {"status": "ERROR", "raw": response}
        return {"status": "OK", "raw": response}

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()