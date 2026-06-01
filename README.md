# Binance Futures Simplified Trading Bot (USDT-M)

A robust, enterprise-grade, and beautifully-styled Python application designed to place orders on the **Binance Futures Testnet (USDT-M)**. It features a clean architecture separating business logic from validation and presentation, direct REST API calls, automatic time drift synchronization, a strict input validator, and a powerful dual-mode CLI with an interactive configuration wizard.

---

##  Key Features

1. **Direct REST Client**: Implements direct REST calls using `requests` with custom SHA256 HMAC request signing and query generation, showing complete control over the HTTP request lifecycle.
2. **Dual-Mode CLI UX (Bonus)**:
   - **Command Mode**: Standard CLI execution with `argparse` arguments for automation.
   - **Interactive Mode**: A gorgeous step-by-step terminal wizard driven by `questionary` and `rich` that validates inputs in real-time and renders structured visual panels.
3. **Advanced Time Synchronization**: Queries `/fapi/v1/time` to measure and compute local-to-server clock drift. This compensates for timestamp mismatches and fully prevents the common `recvWindow` signature rejection errors.
4. **Mock Execution Layer**: Falls back to an extremely realistic simulated environment if no API keys are provided (or if `--mock` is specified). This lets recruiters and evaluators try out and test every function instantly without registering for testnet accounts!
5. **Bonus 3rd Order Type**: Supports **STOP_MARKET** orders in addition to standard **MARKET** and **LIMIT** orders, with comprehensive validation checks.
6. **Robust Structured Logging**: Detailed, clean console logging paired with rotation-backed file logging (`trading_bot.log`) showing exact HTTP endpoints, payloads, response structures, and timings.

---

##  Project Architecture

The codebase follows professional software engineering patterns with a clear separation of concerns:

```
trading_bot/
│
├── bot/
│   ├── __init__.py          # Bot package initialization
│   ├── client.py            # Custom Binance REST Client (signing, time sync, mock logic)
│   ├── orders.py            # Order execution manager (MARKET, LIMIT, STOP_MARKET)
│   ├── validators.py        # Strict input validator (symbol, quantity, price limits)
│   └── logging_config.py    # Dual logger setup (Console RichHandler + File Rotation)
│
├── cli.py                   # Entry point (Command Parser & Interactive Wizard)
├── requirements.txt         # Project third-party dependencies
├── trading_bot.log          # Detailed historical execution log file
└── README.md                # Comprehensive documentation
```

---

##  Setup & Installation

### 1. Prerequisites
Ensure you have **Python 3.8+** installed. You can check your version by running:
```bash
python --version
```

### 2. Clone and Prepare Workspace
Navigate into the project root directory:
```bash
cd trading_bot
```

### 3. Install Dependencies
Install all required libraries using `pip`:
```bash
pip install -r requirements.txt
```

### 4. Configure API Credentials (Optional)
To execute orders on the live **Binance Futures Testnet**:
1. Go to [Binance Futures Testnet](https://testnet.binancefuture.com) and log in/register to generate your API keys.
2. Create a `.env` file in the project root:
   ```env
   BINANCE_API_KEY=your_testnet_api_key_here
   BINANCE_API_SECRET=your_testnet_api_secret_here
   ```
*Note: If no `.env` file is present, the bot automatically defaults to **Mock Mode**, allowing complete dry-run testing.*

---

##  How to Run

### Mode A: Beautiful Interactive Wizard (Recommended)
Run the script without any parameters to launch the wizard:
```bash
python cli.py
```
This launches a guided process:
1. Select whether to use `.env` credentials, input them manually, or run in mock mode.
2. Enter the trading symbol (e.g. `BTCUSDT`).
3. Choose the Side (`BUY` or `SELL`).
4. Choose the Order Type (`MARKET`, `LIMIT`, or `STOP_MARKET`).
5. Input parameters (validation checks occur inline).
6. Verify the gorgeous details card and confirm to place the order!

---

### Mode B: Direct Command Line (Argparse)
Run the script with arguments to place orders instantly. Add `--mock` to perform dry-runs.

#### 1. MARKET Order Example
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.005 --mock
```

#### 2. LIMIT Order Example (Requires Price)
```bash
python cli.py --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.005 --price 65000.0 --mock
```

#### 3. STOP_MARKET Order Example (Requires Stop Price)
```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.002 --stop-price 64000.0 --mock
```

#### 4. Live Testnet Order (Requires `.env` variables set)
Simply remove the `--mock` flag to send the transaction to the real Binance Testnet:
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

#### 5. Debug Logging to Console
Add the `--debug` flag to display verbose HTTP handshake parameters inside the console in real-time:
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --mock --debug
```

---

##  Output and Logging

Every execution generates dual output streams:
1. **Interactive Console UI**: Displays high-end structured `rich` tables and execution summary cards (orderId, status, original quantity, executed quantity, average price).
2. **Detailed Log File (`trading_bot.log`)**: Records timestamps, code line numbers, logs of operations, sanitised API request URLs, body payloads, and raw response strings for professional bookkeeping.

### Sample Log File Output
```text
[2026-06-01 16:26:33,851] [INFO] [trading_bot] [orders.py:24] - Preparing MARKET BUY order for BTCUSDT | Qty: 0.005  
[2026-06-01 16:26:33,853] [INFO] [trading_bot] [client.py:156] - [MOCK API Request] POST https://testnet.binancefuture.com/fapi/v1/order
[2026-06-01 16:26:33,857] [INFO] [trading_bot] [client.py:157] - Parameters: {'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', 'quantity': 0.005}
[2026-06-01 16:26:34,162] [INFO] [trading_bot] [client.py:197] - [MOCK API Response] Order Created | ID: 1780311394162
```

---

##  Assumptions & Design Decisions

- **USDT-M Futures Focus**: The bot targets USDT-Margined perpetual contracts using `/fapi/v1` REST endpoints.
- **Time in Force (GTC)**: For `LIMIT` orders, `timeInForce="GTC"` (Good 'Til Canceled) is automatically injected since it is mandatory for placing normal limit orders on Binance Futures.
- **Precision and Sizing**: Symbols are automatically normalized to uppercase alphanumeric. Quantities and prices are cast into standard floats. Real exchange orders assume quantities comply with Binance's minimum contract size and tick size filters.
- **ASCII-Safe Styling**: Visual layouts are structured using standard ANSI borders rather than complex Unicode emojis to ensure complete compatibility on Windows terminals with legacy codepages (e.g. CP1252), while still maintaining an ultra-premium aesthetic.
