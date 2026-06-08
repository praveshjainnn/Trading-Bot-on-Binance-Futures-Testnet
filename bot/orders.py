from bot.validators import validate_order_inputs, ValidationError
from bot.client import BinanceFuturesClient, BinanceAPIException
from bot.logging_config import get_logger

logger = get_logger()

class OrderManager:
    """Manages order submission, validation, and response formatting."""
    def __init__(self, client: BinanceFuturesClient):
        self.client = client

    def place_order(self, symbol: str, side: str, order_type: str, quantity, price=None, trigger_price=None):
        """Validates inputs, places the order (standard or conditional), and parses the response."""
        # 1. Validate inputs
        try:
            val_params = validate_order_inputs(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                trigger_price=trigger_price
            )
            logger.info(
                f"Validation passed: {val_params['side']} {val_params['quantity']} "
                f"{val_params['symbol']} {val_params['type']}"
            )
        except ValidationError as e:
            logger.error(f"Input validation failed: {e}")
            raise

        # 2. Place the order
        try:
            # Print order request summary for logging and tracking
            req_summary = {
                "symbol": val_params["symbol"],
                "side": val_params["side"],
                "type": val_params["type"],
                "quantity": val_params["quantity"]
            }
            if val_params["type"] == "LIMIT":
                req_summary["price"] = val_params["price"]
            elif val_params["type"] == "STOP_MARKET":
                req_summary["trigger_price"] = val_params["triggerPrice"]

            logger.info(f"Submitting request to exchange: {req_summary}")

            if val_params["type"] == "STOP_MARKET":
                raw_response = self.client.place_stop_market_order(
                    symbol=val_params["symbol"],
                    side=val_params["side"],
                    trigger_price=val_params["triggerPrice"],
                    quantity=val_params["quantity"]
                )
            else:
                raw_response = self.client.place_order(
                    symbol=val_params["symbol"],
                    side=val_params["side"],
                    order_type=val_params["type"],
                    quantity=val_params["quantity"],
                    price=val_params["price"] if val_params["type"] == "LIMIT" else None
                )

            # 3. Format response details
            parsed_summary = self._parse_response(val_params["type"], raw_response)
            logger.info(f"Order executed successfully. ID: {parsed_summary['order_id']}, Status: {parsed_summary['status']}")
            
            return {
                "success": True,
                "request": req_summary,
                "response": parsed_summary,
                "raw": raw_response
            }

        except BinanceAPIException as e:
            logger.error(f"Exchange returned error: {e}")
            return {
                "success": False,
                "request": req_summary if 'req_summary' in locals() else None,
                "error": f"Binance API Error (code={e.code}): {e.message}"
            }
        except Exception as e:
            logger.error(f"Unexpected execution failure: {e}", exc_info=True)
            return {
                "success": False,
                "request": req_summary if 'req_summary' in locals() else None,
                "error": f"Unexpected error: {str(e)}"
            }

    def _parse_response(self, order_type: str, response: dict) -> dict:
        """Parses Binance response payload into a standard format."""
        if order_type == "STOP_MARKET":
            # Algo order schema: uses algoId, status: ACCEPTED, etc.
            return {
                "order_id": response.get("algoId", "N/A"),
                "status": response.get("status", "N/A"),
                "executed_qty": "0.0 (Trigger Order)",
                "avg_price": "N/A",
                "trigger_price": response.get("triggerPrice", "N/A"),
                "is_algo": True
            }
        else:
            # Standard order schema
            executed_qty = response.get("executedQty", "0.0")
            avg_price = response.get("avgPrice", "0.0")
            
            # Fallback checks
            if float(avg_price) == 0.0:
                avg_price = response.get("price", "0.0")
                
            return {
                "order_id": response.get("orderId", "N/A"),
                "status": response.get("status", "N/A"),
                "executed_qty": executed_qty,
                "avg_price": avg_price if float(avg_price) > 0 else "N/A",
                "is_algo": False
            }
