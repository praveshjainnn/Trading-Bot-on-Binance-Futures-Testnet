import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from bot.logging_config import get_logger

logger = get_logger()

class BinanceAPIException(Exception):
    """Exception raised for errors returned by the Binance API."""
    def __init__(self, message, code=-1):
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self):
        return f"BinanceAPIException(code={self.code}): {self.message}"

class BinanceFuturesClient:
    """HTTP client to interact with Binance Futures Testnet."""
    def __init__(self, api_key=None, api_secret=None, base_url="https://testnet.binancefuture.com", dry_run=False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip('/')
        self.dry_run = dry_run
        self.time_offset = 0

        # Enable dry-run if API credentials are not provided or contain placeholder template values
        is_placeholder = (
            (self.api_key and "your_binance_testnet" in self.api_key) or
            (self.api_secret and "your_binance_testnet" in self.api_secret)
        )

        if not self.dry_run and (not self.api_key or not self.api_secret or is_placeholder):
            logger.warning("API credentials (Key/Secret) are missing or set to placeholder values. Defaulting to SAFE DRY-RUN mode.")
            self.dry_run = True

        if self.dry_run:
            logger.info("Initializing in DRY-RUN mode. No orders will be executed on the exchange.")
        else:
            logger.info(f"Initializing Binance Futures Client on: {self.base_url}")
            try:
                self.sync_time()
            except Exception as e:
                logger.error(f"Failed to sync time with Binance server: {e}. Using local time.")

    def sync_time(self):
        """Fetches server time to adjust local time drift."""
        url = f"{self.base_url}/fapi/v1/time"
        logger.debug(f"Sending request: GET {url}")
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        server_time = response.json()['serverTime']
        local_time = int(time.time() * 1000)
        self.time_offset = server_time - local_time
        
        logger.info(f"Time synced. Server offset: {self.time_offset}ms")

    def _mask_headers(self, headers):
        """Masks API keys in logs for security."""
        masked = headers.copy()
        if 'X-MBX-APIKEY' in masked:
            key = masked['X-MBX-APIKEY']
            masked['X-MBX-APIKEY'] = f"...{key[-6:]}" if len(key) > 6 else "***"
        return masked

    def _send_request(self, method, endpoint, params=None, signed=False):
        """Sends an HTTP request to the Binance Futures API."""
        if params is None:
            params = {}

        # Handle Dry-Run orders locally
        if self.dry_run and endpoint in ('/fapi/v1/order', '/fapi/v1/algoOrder'):
            return self._handle_dry_run(method, endpoint, params)

        url = f"{self.base_url}{endpoint}"
        headers = {}

        # Add API Key Header
        if signed or self.api_key:
            headers['X-MBX-APIKEY'] = self.api_key

        # Calculate HMAC SHA256 Signature for signed endpoints
        if signed:
            if not self.api_secret:
                raise ValueError("API Secret is required for signed requests.")
            
            # Inject time offset to prevent timestamp errors
            params['timestamp'] = int(time.time() * 1000) + self.time_offset
            query_string = urlencode(params)
            
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            params['signature'] = signature

        # Log details of the outgoing request
        logger.debug(f"Request: {method} {url} | Params: {params} | Headers: {self._mask_headers(headers)}")

        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=15)
            elif method.upper() == "POST":
                # For POST endpoints, parameters are sent as query string/data
                response = requests.post(url, data=params, headers=headers, timeout=15)
            else:
                raise ValueError(f"HTTP method {method} is not supported.")

            logger.debug(f"Response Status Code: {response.status_code}")

            # Raise exceptions for HTTP errors (4xx/5xx)
            response.raise_for_status()

            response_json = response.json()
            logger.debug(f"Response Payload: {response_json}")
            return response_json

        except requests.exceptions.HTTPError as e:
            try:
                # Attempt to parse specific error message from Binance
                err_payload = response.json()
                msg = err_payload.get('msg', 'Unknown API error')
                code = err_payload.get('code', -1)
                logger.error(f"Binance API Error: Code {code} | Message: {msg}")
                raise BinanceAPIException(msg, code=code)
            except (ValueError, AttributeError):
                # Fallback to standard HTTP error logging
                logger.error(f"HTTP Error: {e} | Content: {response.text}")
                raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Network/Connection error encountered: {e}")
            raise

    def get_ticker_price(self, symbol):
        """Fetches the latest ticker price for a symbol."""
        # Even in dry-run, attempt to query the public API for live prices if possible
        try:
            url = f"{self.base_url}/fapi/v1/ticker/price"
            response = requests.get(url, params={'symbol': symbol}, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Failed to fetch live price in dry-run: {e}")

        # Dry-run fallback values if real API fails or is unreachable
        if self.dry_run:
            mock_prices = {
                "BTCUSDT": "68500.00",
                "ETHUSDT": "3500.00",
                "SOLUSDT": "150.00",
                "BNBUSDT": "580.00",
            }
            return {
                "symbol": symbol,
                "price": mock_prices.get(symbol.upper(), "10.00"),
                "time": int(time.time() * 1000)
            }
        
        # Raise standard error if we are not in dry-run
        raise

    def place_order(self, symbol, side, order_type, quantity, price=None, time_in_force="GTC"):
        """Places a standard Market or Limit order."""
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
        }
        
        if order_type.upper() == "LIMIT":
            if not price:
                raise ValueError("Price is required for LIMIT orders.")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        return self._send_request("POST", "/fapi/v1/order", params=params, signed=True)

    def place_stop_market_order(self, symbol, side, trigger_price, quantity, working_type="CONTRACT_PRICE"):
        """Places a Stop-Market conditional order using the Algo endpoint."""
        params = {
            "algoType": "CONDITIONAL",
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "STOP_MARKET",
            "triggerPrice": str(trigger_price),
            "quantity": str(quantity),
            "workingType": working_type
        }
        
        return self._send_request("POST", "/fapi/v1/algoOrder", params=params, signed=True)

    def _handle_dry_run(self, method, endpoint, params):
        """Generates realistic responses for trade execution during dry runs."""
        logger.info(f"[DRY-RUN] Intercepted {method} request to {endpoint}")
        symbol = params.get('symbol', 'BTCUSDT')
        side = params.get('side', 'BUY')
        qty = params.get('quantity', '0.0')

        if endpoint == '/fapi/v1/order':
            order_type = params.get('type', 'MARKET')
            price = params.get('price', '0.0')
            
            # If market order, get a mock/live current price
            avg_price = price
            if order_type == 'MARKET':
                ticker = self.get_ticker_price(symbol)
                avg_price = ticker.get('price', '68500.00')

            return {
                "orderId": 987654321,
                "symbol": symbol,
                "status": "FILLED" if order_type == "MARKET" else "NEW",
                "clientOrderId": "dry_run_client_order_id_xyz",
                "price": str(price),
                "avgPrice": str(avg_price),
                "origQty": str(qty),
                "executedQty": str(qty) if order_type == "MARKET" else "0",
                "cumQty": str(qty) if order_type == "MARKET" else "0",
                "cumQuote": "0",
                "timeInForce": params.get('timeInForce', 'GTC'),
                "type": order_type,
                "reduceOnly": False,
                "closePosition": False,
                "side": side,
                "positionSide": "BOTH",
                "stopPrice": "0",
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "origType": order_type,
                "updateTime": int(time.time() * 1000)
            }
            
        elif endpoint == '/fapi/v1/algoOrder':
            trigger_price = params.get('triggerPrice', '0.0')
            return {
                "algoId": 1234567,
                "symbol": symbol,
                "orderType": "STOP_MARKET",
                "side": side,
                "positionSide": "BOTH",
                "quantity": str(qty),
                "triggerPrice": str(trigger_price),
                "workingType": params.get('workingType', 'CONTRACT_PRICE'),
                "priceProtect": False,
                "timeInForce": "GTC",
                "status": "ACCEPTED"
            }
            
        return {}
