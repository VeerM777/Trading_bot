import os
import sys
import io
import argparse
from typing import Dict, Any, Optional
from dotenv import load_dotenv

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from bot.logging_config import setup_logging, logger, LOG_FILE_PATH
from bot.validators import validate_order_inputs, ValidationError
from bot.client import BinanceFuturesClient, BinanceAPIError, BinanceNetworkError
from bot.orders import OrderManager

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import questionary

_DOTENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)

console = Console()


def print_banner():
    """Prints the application title banner."""
    console.print("\n [bold cyan]Binance Futures Trading Bot[/bold cyan]  [dim]| Testnet (USDT-M)[/dim]")
    console.print(" [dim]─────────────────────────────────────────[/dim]\n")


def check_credentials() -> tuple[Optional[str], Optional[str]]:
    """Loads API credentials from environment variables."""
    return os.getenv("BINANCE_API_KEY"), os.getenv("BINANCE_API_SECRET")


def display_order_summary(details: Dict[str, Any], is_mock: bool):
    """Renders a formatted table of order parameters before submission."""
    table = Table(title="Order Submission Details", show_header=True, header_style="bold magenta")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Symbol", details["symbol"])
    table.add_row("Order Side", details["side"])
    table.add_row("Order Type", details["type"])
    table.add_row("Quantity", str(details["quantity"]))

    if details["price"] is not None:
        table.add_row("Limit Price", f"{details['price']} USDT")
    if details["stop_price"] is not None:
        table.add_row("Stop Price", f"{details['stop_price']} USDT")

    table.add_row("Execution Environment", "MOCK (Dry Run)" if is_mock else "REAL (Binance Futures Testnet)")

    console.print(Panel(
        table,
        title="[bold yellow][CONFIRM] Order Details[/bold yellow]",
        border_style="yellow",
        expand=False
    ))


def display_response_card(response: Dict[str, Any], is_success: bool = True, error_msg: str = ""):
    """Renders the execution result as a formatted panel card."""
    if not is_success:
        console.print(Panel(
            f"[bold red][X] Order Placement Failed[/bold red]\n\n"
            f"[yellow]Error Details:[/yellow] {error_msg}\n\n"
            f"[grey62]Log file: [underline]{LOG_FILE_PATH}[/underline][/grey62]",
            title="[bold red]Execution Failure[/bold red]",
            border_style="red",
            expand=False
        ))
        return

    avg_price = response.get("avgPrice", "0.00")
    if avg_price == "0.00" or float(avg_price) == 0.0:
        avg_price = response.get("price", "N/A")

    table = Table(show_header=True, header_style="bold green")
    table.add_column("Response Field", style="cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Order ID", str(response.get("orderId", "N/A")))
    table.add_row("Symbol", response.get("symbol", "N/A"))
    table.add_row("Execution Status", f"[bold green]{response.get('status', 'N/A')}[/bold green]")
    table.add_row("Original Quantity", str(response.get("origQty", "0.000")))
    table.add_row("Executed Quantity", str(response.get("executedQty", "0.000")))
    table.add_row("Average/Limit Price", f"{avg_price} USDT")

    console.print(Panel(
        table,
        title="[bold green][OK] Order Executed Successfully[/bold green]",
        border_style="green",
        expand=False,
        subtitle=f"Log: [underline]{LOG_FILE_PATH}[/underline]"
    ))


def run_interactive():
    """Launches the step-by-step interactive terminal wizard."""
    print_banner()
    console.print("[bold white]Welcome to the Interactive Bot Configurator![/bold white]\n")

    api_key, api_secret = check_credentials()
    env_available = api_key is not None and api_secret is not None

    cred_choices = []
    if env_available:
        cred_choices.append("Use active .env API credentials")
    cred_choices.extend([
        "Enter new API credentials manually for this session",
        "Run in Mock Mode (No credentials required, safe dry-run)"
    ])

    cred_action = questionary.select("Choose your API Environment Setup:", choices=cred_choices).ask()

    is_mock = False
    if cred_action == "Run in Mock Mode (No credentials required, safe dry-run)":
        is_mock = True
    elif cred_action == "Enter new API credentials manually for this session":
        api_key = questionary.text("Enter your Binance Futures Testnet API Key:").ask()
        api_secret = questionary.password("Enter your Binance Futures Testnet API Secret:").ask()
        if not api_key or not api_secret:
            console.print("[bold yellow][!] No credentials provided. Defaulting to MOCK mode.[/bold yellow]")
            is_mock = True
    else:
        logger.info("Using API credentials loaded from the local environment.")

    with console.status("[bold yellow]Initializing Binance Futures Client...", spinner="dots"):
        try:
            client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret, mock=is_mock)
            is_mock = client.mock
            manager = OrderManager(client)
        except Exception as e:
            console.print(f"[bold red][X] Failed to initialize client: {e}[/bold red]")
            sys.exit(1)

    symbol = questionary.text(
        "Enter Trading Symbol (e.g., BTCUSDT):",
        default="BTCUSDT",
        validate=lambda text: len(text.strip()) >= 3 or "Symbol must be at least 3 chars."
    ).ask()

    side = questionary.select("Select Order Side:", choices=["BUY", "SELL"]).ask()

    order_type = questionary.select("Select Order Type:", choices=["MARKET", "LIMIT", "STOP_MARKET"]).ask()

    quantity = questionary.text(
        "Enter Quantity to Trade (e.g., 0.002):",
        validate=lambda text: (
            True if text.replace(".", "", 1).isdigit() and float(text) > 0
            else "Please enter a positive numeric quantity."
        )
    ).ask()

    price = None
    if order_type == "LIMIT":
        price = questionary.text(
            "Enter Limit Price (USDT):",
            validate=lambda text: (
                True if text.replace(".", "", 1).isdigit() and float(text) > 0
                else "Please enter a positive limit price."
            )
        ).ask()

    stop_price = None
    if order_type == "STOP_MARKET":
        stop_price = questionary.text(
            "Enter Stop Price (USDT):",
            validate=lambda text: (
                True if text.replace(".", "", 1).isdigit() and float(text) > 0
                else "Please enter a positive stop trigger price."
            )
        ).ask()

    try:
        validated = validate_order_inputs(
            symbol=symbol, side=side, order_type=order_type,
            quantity=quantity, price=price, stop_price=stop_price
        )
    except ValidationError as ve:
        console.print(f"\n[bold red][X] Validation Error: {ve}[/bold red]")
        sys.exit(1)

    console.print()
    display_order_summary(validated, is_mock)

    if not questionary.confirm("Are you sure you want to execute this order?", default=True).ask():
        console.print("[bold yellow][!] Order aborted by user. Exiting.[/bold yellow]")
        sys.exit(0)

    console.print()
    with console.status("[bold green]Transmitting order to Binance Futures...", spinner="dots"):
        try:
            response = manager.place_order(
                symbol=validated["symbol"], side=validated["side"],
                order_type=validated["type"], quantity=validated["quantity"],
                price=validated["price"], stop_price=validated["stop_price"]
            )
        except (BinanceAPIError, BinanceNetworkError) as err:
            display_response_card({}, is_success=False, error_msg=str(err))
            sys.exit(1)
        except Exception as e:
            display_response_card({}, is_success=False, error_msg=f"Unhandled error: {e}")
            sys.exit(1)

    display_response_card(response)


def run_command_line():
    """Executes a trade directly from CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Binance Futures Testnet (USDT-M) simplified trading bot."
    )
    parser.add_argument("--symbol", type=str, help="Trading symbol, e.g. BTCUSDT")
    parser.add_argument("--side", type=str, choices=["BUY", "SELL"], help="Order side")
    parser.add_argument("--type", type=str, choices=["MARKET", "LIMIT", "STOP_MARKET"], help="Order type")
    parser.add_argument("--quantity", type=float, help="Trade quantity")
    parser.add_argument("--price", type=float, default=None, help="Limit price (LIMIT orders only)")
    parser.add_argument("--stop-price", type=float, default=None, help="Stop trigger price (STOP_MARKET only)")
    parser.add_argument("--mock", action="store_true", help="Dry-run mode; no real orders placed")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging to console")

    args = parser.parse_args()
    setup_logging(debug=args.debug)

    if not (args.symbol and args.side and args.type and args.quantity is not None):
        logger.info("Missing required arguments. Launching interactive session...")
        run_interactive()
        return

    api_key, api_secret = check_credentials()
    is_mock = args.mock

    if not is_mock and (not api_key or not api_secret):
        logger.warning("No API credentials found. Falling back to MOCK mode.")
        is_mock = True

    try:
        validated = validate_order_inputs(
            symbol=args.symbol, side=args.side, order_type=args.type,
            quantity=args.quantity, price=args.price, stop_price=args.stop_price
        )
    except ValidationError as ve:
        logger.error(f"Validation failed: {ve}")
        console.print(f"[bold red][X] Validation Error: {ve}[/bold red]")
        sys.exit(1)

    try:
        client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret, mock=is_mock)
        manager = OrderManager(client)
    except Exception as e:
        logger.critical(f"Initialization error: {e}")
        console.print(f"[bold red][X] Initialization Failure: {e}[/bold red]")
        sys.exit(1)

    console.print()
    logger.info("Executing Order via Command Line...")
    display_order_summary(validated, is_mock)

    try:
        response = manager.place_order(
            symbol=validated["symbol"], side=validated["side"],
            order_type=validated["type"], quantity=validated["quantity"],
            price=validated["price"], stop_price=validated["stop_price"]
        )
        display_response_card(response)
    except (BinanceAPIError, BinanceNetworkError) as err:
        display_response_card({}, is_success=False, error_msg=str(err))
        sys.exit(1)
    except Exception as e:
        display_response_card({}, is_success=False, error_msg=f"Unhandled error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_interactive()
    else:
        run_command_line()
