from typing import Dict, Any, Optional
from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from bot.logging_config import logger

# Binance Futures Testnet limitation: conditional order types (STOP, STOP_MARKET,
# TAKE_PROFIT, TAKE_PROFIT_MARKET) are not supported on /fapi/v1/order.
# Error code -4120 is returned. This is a testnet restriction only.
_TESTNET_CONDITIONAL_NOT_SUPPORTED = -4120


class OrderManager:
    """Manages order placement and formats parameters for the Binance client."""

    def __init__(self, client: BinanceFuturesClient):
        self.client = client

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Routes to the correct order method based on order type."""
        logger.info(
            f"Preparing {order_type} {side} order for {symbol} | Qty: {quantity} "
            f"{f'| Price: {price}' if price else ''} "
            f"{f'| Stop Price: {stop_price}' if stop_price else ''}"
        )

        try:
            if order_type == "MARKET":
                return self._place_market_order(symbol, side, quantity)
            elif order_type == "LIMIT":
                return self._place_limit_order(symbol, side, quantity, price)
            elif order_type == "STOP_MARKET":
                return self._place_stop_market_order(symbol, side, quantity, stop_price)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
        except (BinanceAPIError, BinanceNetworkError, ValueError) as e:
            logger.error(f"Order placement failed: {e}")
            raise

    def _place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        """Places a MARKET order."""
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity
        }
        return self.client.request("POST", "/fapi/v1/order", params)

    def _place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> Dict[str, Any]:
        """Places a LIMIT order with GTC (Good 'Til Canceled) time-in-force."""
        params = {
            "symbol": symbol,
            "side": side,
            "type": "LIMIT",
            "quantity": quantity,
            "price": price,
            "timeInForce": "GTC"
        }
        return self.client.request("POST", "/fapi/v1/order", params)

    def _place_stop_market_order(self, symbol: str, side: str, quantity: float, stop_price: float) -> Dict[str, Any]:
        """Places a STOP_MARKET order.

        Note: The Binance Futures Testnet blocks all conditional order types
        (STOP, STOP_MARKET, TAKE_PROFIT, TAKE_PROFIT_MARKET) on /fapi/v1/order
        with error -4120. On the live production exchange these work normally.
        If the testnet -4120 error is returned, a clear user-facing message is raised.
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": "STOP_MARKET",
            "quantity": quantity,
            "stopPrice": stop_price,
            "workingType": "CONTRACT_PRICE"
        }
        try:
            return self.client.request("POST", "/fapi/v1/order", params)
        except BinanceAPIError as e:
            if e.code == _TESTNET_CONDITIONAL_NOT_SUPPORTED:
                raise BinanceAPIError(
                    code=e.code,
                    msg=(
                        "STOP_MARKET orders are not supported on the Binance Futures "
                        "Testnet (/fapi/v1/order). This is a testnet-only restriction "
                        "— the same order works on the live exchange. "
                        "Use --mock to simulate this order type locally."
                    ),
                    status_code=e.status_code
                ) from e
            raise
