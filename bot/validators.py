import re
from typing import Optional, Dict, Any


class ValidationError(ValueError):
    pass


def validate_symbol(symbol: str) -> str:
    if not symbol:
        raise ValidationError("Symbol cannot be empty.")

    cleaned = symbol.strip().upper()

    if not re.match(r"^[A-Z0-9]{3,12}$", cleaned):
        raise ValidationError(
            f"Invalid symbol format: '{symbol}'. "
            "Must be alphanumeric uppercase, e.g., 'BTCUSDT' or 'ETHUSDT'."
        )
    return cleaned


def validate_side(side: str) -> str:
    if not side:
        raise ValidationError("Order side cannot be empty.")

    cleaned = side.strip().upper()
    if cleaned not in ("BUY", "SELL"):
        raise ValidationError(f"Invalid side: '{side}'. Must be either 'BUY' or 'SELL'.")
    return cleaned


def validate_order_type(order_type: str) -> str:
    if not order_type:
        raise ValidationError("Order type cannot be empty.")

    cleaned = order_type.strip().upper()
    valid_types = ("MARKET", "LIMIT", "STOP_MARKET")
    if cleaned not in valid_types:
        raise ValidationError(
            f"Invalid order type: '{order_type}'. "
            f"Supported types are: {', '.join(valid_types)}."
        )
    return cleaned


def validate_quantity(quantity: Any) -> float:
    try:
        val = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Quantity must be a valid number, got '{quantity}'.")

    if val <= 0:
        raise ValidationError(f"Quantity must be greater than zero, got {val}.")
    return val


def validate_price(price: Any, order_type: str) -> Optional[float]:
    if order_type.upper() == "LIMIT":
        if price is None:
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            val = float(price)
        except (ValueError, TypeError):
            raise ValidationError(f"Price must be a valid number, got '{price}'.")

        if val <= 0:
            raise ValidationError(f"Price must be greater than zero, got {val}.")
        return val

    if price is not None:
        raise ValidationError(f"Price should not be specified for {order_type} orders.")
    return None


def validate_stop_price(stop_price: Any, order_type: str) -> Optional[float]:
    if order_type.upper() == "STOP_MARKET":
        if stop_price is None:
            raise ValidationError("Stop price (stopPrice) is required for STOP_MARKET orders.")
        try:
            val = float(stop_price)
        except (ValueError, TypeError):
            raise ValidationError(f"Stop price must be a valid number, got '{stop_price}'.")

        if val <= 0:
            raise ValidationError(f"Stop price must be greater than zero, got {val}.")
        return val

    if stop_price is not None:
        raise ValidationError(f"Stop price should not be specified for {order_type} orders.")
    return None


def validate_order_inputs(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Any,
    price: Any = None,
    stop_price: Any = None
) -> Dict[str, Any]:
    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, order_type),
        "stop_price": validate_stop_price(stop_price, order_type),
    }
