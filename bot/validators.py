import re

class ValidationError(ValueError):
    """Custom exception raised when input validation fails."""
    pass

def validate_symbol(symbol: str) -> str:
    """Validates the trading symbol format (e.g., BTCUSDT)."""
    if not symbol:
        raise ValidationError("Symbol cannot be empty.")
    
    # Strip whitespace and capitalize
    symbol = symbol.strip().upper()
    
    # Basic regex validation for Binance USDT/BUSD/USDC futures pairs
    # Usually matches format like: BTCUSDT, ETHUSDC, etc.
    if not re.match(r"^[A-Z0-9]{2,12}(USDT|BUSD|USDC)$", symbol):
        raise ValidationError(
            f"Invalid symbol format: '{symbol}'. "
            "Must be uppercase and end with a valid quote currency (e.g., USDT, USDC, BUSD) "
            "like 'BTCUSDT' or 'ETHUSDT'."
        )
    return symbol

def validate_side(side: str) -> str:
    """Validates the order side (BUY or SELL)."""
    if not side:
        raise ValidationError("Order side cannot be empty.")
    
    side = side.strip().upper()
    if side not in ("BUY", "SELL"):
        raise ValidationError(f"Invalid order side: '{side}'. Must be 'BUY' or 'SELL'.")
    return side

def validate_order_type(order_type: str) -> str:
    """Validates the order type (MARKET, LIMIT, STOP_MARKET)."""
    if not order_type:
        raise ValidationError("Order type cannot be empty.")
    
    order_type = order_type.strip().upper()
    valid_types = ("MARKET", "LIMIT", "STOP_MARKET")
    if order_type not in valid_types:
        raise ValidationError(
            f"Invalid order type: '{order_type}'. "
            f"Supported types are: {', '.join(valid_types)}"
        )
    return order_type

def validate_quantity(quantity) -> float:
    """Validates that the quantity is a positive number."""
    if quantity is None:
        raise ValidationError("Quantity is required.")
        
    try:
        qty_val = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Invalid quantity: '{quantity}'. Must be a number.")
        
    if qty_val <= 0:
        raise ValidationError(f"Quantity must be greater than zero. Provided: {qty_val}")
    return qty_val

def validate_price(price, order_type: str) -> float:
    """Validates price. Required and must be positive for LIMIT orders."""
    order_type = order_type.strip().upper()
    
    if order_type == "LIMIT":
        if price is None or str(price).strip() == "":
            raise ValidationError("Price is required for LIMIT orders.")
        try:
            price_val = float(price)
        except (TypeError, ValueError):
            raise ValidationError(f"Invalid price: '{price}'. Must be a number.")
            
        if price_val <= 0:
            raise ValidationError(f"Price must be greater than zero. Provided: {price_val}")
        return price_val
    else:
        # For MARKET or STOP_MARKET, price is not used
        if price is not None and str(price).strip() != "":
            raise ValidationError(f"Price should not be provided for {order_type} orders.")
        return 0.0

def validate_trigger_price(trigger_price, order_type: str) -> float:
    """Validates trigger price. Required and must be positive for STOP_MARKET orders."""
    order_type = order_type.strip().upper()
    
    if order_type == "STOP_MARKET":
        if trigger_price is None or str(trigger_price).strip() == "":
            raise ValidationError("Trigger price is required for STOP_MARKET orders.")
        try:
            trigger_val = float(trigger_price)
        except (TypeError, ValueError):
            raise ValidationError(f"Invalid trigger price: '{trigger_price}'. Must be a number.")
            
        if trigger_val <= 0:
            raise ValidationError(f"Trigger price must be greater than zero. Provided: {trigger_val}")
        return trigger_val
    else:
        if trigger_price is not None and str(trigger_price).strip() != "":
            raise ValidationError(f"Trigger price should not be provided for {order_type} orders.")
        return 0.0

def validate_order_inputs(symbol, side, order_type, quantity, price=None, trigger_price=None):
    """Convenience helper to validate all order parameters at once."""
    valid_symbol = validate_symbol(symbol)
    valid_side = validate_side(side)
    valid_type = validate_order_type(order_type)
    valid_qty = validate_quantity(quantity)
    valid_price = validate_price(price, valid_type)
    valid_trigger = validate_trigger_price(trigger_price, valid_type)
    
    return {
        "symbol": valid_symbol,
        "side": valid_side,
        "type": valid_type,
        "quantity": valid_qty,
        "price": valid_price,
        "triggerPrice": valid_trigger
    }
