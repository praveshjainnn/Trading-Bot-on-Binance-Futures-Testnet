# Binance Futures Testnet Trading Bot (USDT-M)

A robust, modern Python command-line trading bot for the Binance Futures (USDT-M) Testnet. This application supports placing **Market**, **Limit**, and **Stop-Market** orders, and includes advanced validation, detailed structured logging, and an interactive menu interface.

---

## Features

- **Multi-Order Support**: 
  - `MARKET`: Instant order execution at current market prices.
  - `LIMIT`: Places standard limit orders requiring a custom execution price.
  - `STOP_MARKET` *(Bonus Feature)*: Places conditional trigger orders using Binance's modern `/fapi/v1/algoOrder` service.
- **Double Sides**: Handles both `BUY` and `SELL` instructions.
- **Robust Verification & Fallbacks**:
  - Automatically queries the live public endpoint `GET /fapi/v1/ticker/price` to retrieve real-time prices for validation and calculations.
  - Automatically synchronizes local time drift with the Binance Server Time (`GET /fapi/v1/time`) before signing requests to prevent timestamp/window rejection errors (`-1021`/`-1022`).
- **Input Validation**: Strict client-side validation logic verifying symbols, quantities, order types, and prices before network submission.
- **Safe Dry-Run Mode**: Falls back safely to simulating order execution locally (using mock responses reflecting actual payload shapes) if API credentials are not set.
- **Enhanced CLI UX** *(Bonus Feature)*:
  - **Dynamic Interactive Mode**: Step-by-step prompts with live input verification loops if no CLI arguments are supplied.
  - **Color-Coded Result Cards**: Highlights order parameters, exchange receipt fields (like `orderId`, status, executQty, average price), and clear success/failure indicators using `colorama`.
- **Structured Logging**: Stores clean request signatures, header details (with masked API Keys), raw response payloads, and exception stacks inside `trading_bot.log`.

---

## Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Binance API wrapper (HMAC signer, time offset sync, dry-run)
    orders.py          # Order orchestrator (calls client and structures returns)
    validators.py      # Input validation functions & custom ValidationError
    logging_config.py  # Logger setups (Console colors + File logging)
  cli.py               # Main CLI interface (argument parsing & interactive menus)
  README.md
  requirements.txt
  .env.template
```

---

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher installed on your system.

### 2. Clone and Install Dependencies
Initialize a virtual environment (optional but recommended) and install the requirements:

```bash
# Create and activate virtual environment
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. API Credentials Setup
Create a `.env` file in the root directory and add your Binance Futures Testnet credentials:

```bash
cp .env.template .env
```
Edit `.env` and fill in your keys:
```env
BINANCE_API_KEY=your_binance_testnet_api_key_here
BINANCE_API_SECRET=your_binance_testnet_api_secret_here
```
*Note: If no `.env` file exists or keys are omitted, the bot will automatically fall back to **Dry-Run mode** for safe simulated testing.*

---

## How to Run Examples

You can run the bot in two modes: **Command Line Arguments** or **Interactive CLI Menu**.

### A. Interactive CLI Mode (Recommended)
Simply run the script with no arguments. The bot will launch a step-by-step menu asking you to input values, checking them in real-time.

```bash
python cli.py
```

### B. Direct Command Line Mode
Pass parameters directly as flags. If a flag is invalid or missing required values, validation errors are logged and displayed.

#### 1. Placing a MARKET Order (Dry-Run / Live)
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.005
```

#### 2. Placing a LIMIT Order (Requires `--price`)
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.002 --price 68250
```

#### 3. Placing a STOP_MARKET Order (Requires `--trigger-price`)
```bash
python cli.py --symbol ETHUSDT --side BUY --type STOP_MARKET --quantity 0.05 --trigger-price 3650
```

#### Extra CLI Options
- `--dry-run`: Forces dry-run local mock execution even if `.env` keys are configured.
- `--log-level [DEBUG|INFO|WARNING|ERROR]`: Controls the console log verbosity (default: `INFO`). Detailed file logs in `trading_bot.log` will always record at `DEBUG` level.

---

## Logging & Output Design

All executions generate two outputs:

### 1. Terminal Result Card
Provides a human-readable confirmation card highlighting success/failure, request summary, and response outputs.

### 2. Detailed Log File (`trading_bot.log`)
Outputs high-fidelity debug lines:
```text
2026-06-08 12:40:00 | INFO     | trading_bot | [client.py:46] | Time synced. Server offset: 12ms
2026-06-08 12:40:01 | INFO     | trading_bot | [orders.py:22] | Validation passed: BUY 0.005 BTCUSDT MARKET
2026-06-08 12:40:01 | DEBUG    | trading_bot | [client.py:90] | Request: POST https://testnet.binancefuture.com/fapi/v1/order | Params: {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': '0.005', 'timestamp': 1780908001012, 'signature': '124e930f6...'} | Headers: {'X-MBX-APIKEY': '...abc123'}
2026-06-08 12:40:01 | DEBUG    | trading_bot | [client.py:102] | Response Status Code: 200
2026-06-08 12:40:01 | DEBUG    | trading_bot | [client.py:107] | Response Payload: {'orderId': 987654321, 'symbol': 'BTCUSDT', 'status': 'FILLED', ...}
```

---

## Assumptions & Design Decisions
1. **USDT-M Focus**: Validations assume symbols map standard USDT, USDC, or BUSD collateral margins (defaulting to uppercase and suffix checks).
2. **Time Sync Requirement**: Binance Futures API rejected signed orders with timestamps outside a `5000ms` window. The implementation queries the server time directly and dynamically adjusts the Unix milliseconds stamp sent to standard endpoints.
3. **Algo Endpoint for STOP_MARKET**: Due to Binance API updates, conditional orders like `STOP_MARKET` placed via `/fapi/v1/order` will throw `-4120`. We routed `STOP_MARKET` to the correct Algo Order service `/fapi/v1/algoOrder` under the hood.