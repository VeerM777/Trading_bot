import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from typing import Dict, Any, Optional
from bot.logging_config import logger


class BinanceAPIError(Exception):
    """Exception raised for Binance API specific errors."""
    def __init__(self, code: int, msg: str, status_code: int = 400):
        super().__init__(f"Binance API Error {code}: {msg} (HTTP {status_code})")
        self.code = code
        self.msg = msg
        self.status_code = status_code


class BinanceNetworkError(Exception):
    """Exception raised for network connectivity errors."""
    pass


class BinanceFuturesClient:
    """
    Binance Futures Testnet (USDT-M) REST Client.
    Handles signed requests, timestamp synchronization, and mock operations.
    """
    BASE_URL = "https://testnet.binancefuture.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        mock: bool = False
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.mock = mock
        self.session = requests.Session()
        self.time_offset = 0.0

        if self.mock:
            logger.warning("[bold yellow][!] Running in MOCK Mode. Orders will not be placed on real Testnet.[/bold yellow]")
        else:
            if not self.api_key or not self.api_secret:
                logger.warning(
                    "[bold yellow][!] Credentials missing or incomplete. "
                    "Auto-switching to MOCK Mode.[/bold yellow]"
                )
                self.mock = True
            else:
                self.session.headers.update({
                    "X-MBX-APIKEY": self.api_key,
                    "Content-Type": "application/x-www-form-urlencoded"
                })
                self.sync_time()

    def sync_time(self) -> None:
        """
        Fetches Binance server time and calculates drift offset to prevent
        timestamp rejection errors caused by local clock skew.
        """
        url = f"{self.BASE_URL}/fapi/v1/time"
        try:
            logger.debug(f"Syncing time with Binance server: {url}")
            t_before = time.time() * 1000
            response = self.session.get(url, timeout=10)
            t_after = time.time() * 1000

            rtt = (t_after - t_before) / 2

            if response.status_code == 200:
                server_time = response.json()["serverTime"]
                self.time_offset = server_time - (t_before + rtt)
                logger.debug(
                    f"Time synchronized. RTT: {rtt:.2f}ms, "
                    f"Offset: {self.time_offset:.2f}ms"
                )
            else:
                logger.warning(f"Failed to sync time (status {response.status_code}). Using local time.")
        except Exception as e:
            logger.warning(f"Network error during time sync: {e}. Using local time.")

    def get_server_timestamp(self) -> int:
        """Returns the drift-compensated server timestamp in milliseconds."""
        return int(time.time() * 1000 + self.time_offset)

    def _sign_parameters(self, params: Dict[str, Any]) -> str:
        """Generates an HMAC-SHA256 signature over the URL-encoded parameters."""
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sends a signed REST request to the Binance Futures Testnet."""
        if self.mock:
            return self._mock_request(method, endpoint, params)

        url = f"{self.BASE_URL}{endpoint}"
        params = params or {}

        params["timestamp"] = self.get_server_timestamp()
        params["recvWindow"] = 6000
        params["signature"] = self._sign_parameters(params)

        log_params = params.copy()
        if "signature" in log_params:
            log_params["signature"] = "******" + log_params["signature"][-6:]

        logger.debug(f"API Request | {method} {url} | Params: {log_params}")

        try:
            if method.upper() == "POST":
                response = self.session.post(url, data=params, timeout=15)
            elif method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=15)
            else:
                response = self.session.request(method, url, params=params, timeout=15)
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during API request: {e}")
            raise BinanceNetworkError(f"Connection failed: {e}")

        logger.debug(f"API Response | Status: {response.status_code} | Body: {response.text}")

        try:
            res_json = response.json()
        except ValueError:
            raise BinanceNetworkError(f"Invalid JSON response: {response.text}")

        if response.status_code != 200:
            code = res_json.get("code", -1)
            msg = res_json.get("msg", "Unknown error occurred")
            logger.error(f"Binance API error {code}: {msg}")
            raise BinanceAPIError(code=code, msg=msg, status_code=response.status_code)

        return res_json

    def _mock_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Simulates an HTTP REST request for dry-run (Mock Mode) execution."""
        params = params or {}
        logger.info(f"[cyan][MOCK API Request] {method} {self.BASE_URL}{endpoint}[/cyan]")
        logger.info(f"[cyan]Parameters: {params}[/cyan]")

        time.sleep(0.3)

        if endpoint == "/fapi/v1/order" and method.upper() == "POST":
            symbol = params.get("symbol", "BTCUSDT")
            side = params.get("side", "BUY")
            order_type = params.get("type", "LIMIT")
            quantity = params.get("quantity", "0.001")
            price = params.get("price", "0.0")
            stop_price = params.get("stopPrice", "0.0")
            order_id = int(time.time() * 1000)

            mock_resp = {
                "orderId": order_id,
                "symbol": symbol,
                "status": "FILLED" if order_type == "MARKET" else "NEW",
                "clientOrderId": f"mock_cli_{order_id}",
                "price": str(price),
                "avgPrice": str(price) if order_type != "MARKET" else "67450.25",
                "origQty": str(quantity),
                "executedQty": str(quantity) if order_type == "MARKET" else "0.000",
                "cumQty": str(quantity) if order_type == "MARKET" else "0.000",
                "cumQuote": "0.00",
                "timeInForce": params.get("timeInForce", "GTC"),
                "type": order_type,
                "reduceOnly": False,
                "closePosition": False,
                "side": side,
                "positionSide": "BOTH",
                "stopPrice": str(stop_price),
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "origType": order_type,
                "updateTime": int(time.time() * 1000)
            }
            logger.info(f"[green][MOCK API Response] Order Created | ID: {order_id}[/green]")
            return mock_resp

        raise BinanceAPIError(-1000, f"Unsupported mock endpoint: {endpoint}", 404)
