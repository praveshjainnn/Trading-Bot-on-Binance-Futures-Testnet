import os
import sys
import argparse
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Load package modules
from bot.logging_config import setup_logging, get_logger
from bot.client import BinanceFuturesClient
from bot.orders import OrderManager
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_trigger_price,
    ValidationError
)

# Initialize colorama
init(autoreset=True)

# Print ASCII Banner
def print_banner():
    banner = fr"""
{Fore.CYAN}{Style.BRIGHT}====================================================================
  ____  _                                    ______ _    _ _______ 
 |  _ \(_)                                  |  ____| |  | |__   __|
 | |_) |_ _ __   __ _ _ __   ___ ___        | |__  | |  | |  | |   
 |  _ <| | '_ \ / _` | '_ \ / __/ _ \       |  __| | |  | |  | |   
 | |_) | | | | | (_| | | | | (_|  __/       | |    | |__| |  | |   
 |____/|_|_| |_|\__,_|_| |_|\___\___|       |_|     \____/   |_|   
                                                                   
                  USDT-M FUTURES TRADING BOT (TESTNET)             
===================================================================={Style.RESET_ALL}"""
    print(banner)

def parse_args():
    parser = argparse.ArgumentParser(description="Binance Futures (USDT-M) Testnet Trading Bot")
    parser.add_argument("--symbol", type=str, help="Trading symbol (e.g., BTCUSDT)")
    parser.add_argument("--side", type=str, choices=["BUY", "SELL"], help="Order side (BUY/SELL)")
    parser.add_argument("--type", type=str, choices=["MARKET", "LIMIT", "STOP_MARKET"], help="Order type")
    parser.add_argument("--quantity", type=str, help="Order quantity (string/float, e.g., 0.001)")
    parser.add_argument("--price", type=str, help="Order price (required for LIMIT)")
    parser.add_argument("--trigger-price", type=str, help="Trigger price (required for STOP_MARKET)")
    parser.add_argument("--dry-run", action="store_true", help="Execute order in dry-run mode (no exchange connection)")
    parser.add_argument("--interactive", action="store_true", help="Force interactive prompts menu")
    parser.add_argument("--log-level", type=str, default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Console log level")
    return parser.parse_args()

def prompt_validated_input(prompt_text, validator_func, *args, **kwargs):
    """Repeatedly prompts the user until input passes validation."""
    while True:
        try:
            val = input(f"{Fore.WHITE}{Style.BRIGHT}{prompt_text}{Style.RESET_ALL}").strip()
            return validator_func(val, *args, **kwargs)
        except ValidationError as e:
            print(f"{Fore.RED}ValidationError: {e}{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
            sys.exit(0)

def prompt_menu_choice(prompt_title, options):
    """Prompts the user to select an option from a numbered menu."""
    print(f"\n{Fore.BLUE}{Style.BRIGHT}--- {prompt_title} ---{Style.RESET_ALL}")
    for idx, opt in enumerate(options, 1):
        print(f"  {idx}. {opt}")
    
    while True:
        try:
            choice = input(f"{Fore.WHITE}{Style.BRIGHT}Select an option (1-{len(options)}): {Style.RESET_ALL}").strip()
            if choice.isdigit():
                val = int(choice)
                if 1 <= val <= len(options):
                    return options[val - 1]
            print(f"{Fore.RED}Invalid selection. Please choose a number between 1 and {len(options)}.{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
            sys.exit(0)

def run_interactive_mode():
    """Runs a step-by-step interactive CLI interface to collect parameters."""
    print(f"{Fore.CYAN}Entering Interactive Mode... Please follow the prompts.{Style.RESET_ALL}")
    
    symbol = prompt_validated_input("Enter Symbol (e.g. BTCUSDT): ", validate_symbol)
    
    side = prompt_menu_choice("Order Side", ["BUY", "SELL"])
    
    order_type = prompt_menu_choice("Order Type", ["MARKET", "LIMIT", "STOP_MARKET"])
    
    quantity = prompt_validated_input(f"Enter Quantity for {symbol}: ", validate_quantity)
    
    price = None
    if order_type == "LIMIT":
        price = prompt_validated_input("Enter Limit Price: ", validate_price, order_type=order_type)
        
    trigger_price = None
    if order_type == "STOP_MARKET":
        trigger_price = prompt_validated_input("Enter Trigger Price: ", validate_trigger_price, order_type=order_type)
        
    return {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
        "price": price,
        "trigger_price": trigger_price
    }

def print_result_card(result):
    """Outputs the request/response execution summary cleanly as a terminal card."""
    print(f"\n{Fore.BLUE}{Style.BRIGHT}===================================================================={Style.RESET_ALL}")
    
    if result["success"]:
        print(f"  {Fore.GREEN}{Style.BRIGHT}ORDER STATUS: SUCCESS{Style.RESET_ALL}")
        print(f"{Fore.BLUE}--------------------------------------------------------------------{Style.RESET_ALL}")
        req = result["request"]
        res = result["response"]
        
        print(f"  {Style.BRIGHT}Order Request Summary:{Style.RESET_ALL}")
        print(f"    Symbol:         {req['symbol']}")
        print(f"    Side:           {req['side']}")
        print(f"    Order Type:     {req['type']}")
        print(f"    Quantity:       {req['quantity']}")
        if "price" in req:
            print(f"    Price:          {req['price']}")
        if "trigger_price" in req:
            print(f"    Trigger Price:  {req['trigger_price']}")
            
        print(f"\n  {Style.BRIGHT}Exchange Response Details:{Style.RESET_ALL}")
        id_label = "Algo ID (Trigger)" if res.get("is_algo") else "Order ID"
        print(f"    {id_label}:       {res['order_id']}")
        print(f"    Execution Status: {res['status']}")
        print(f"    Executed Qty:     {res['executed_qty']}")
        print(f"    Average Price:    {res['avg_price']}")
        if "trigger_price" in res:
            print(f"    Trigger Price:    {res['trigger_price']}")
            
    else:
        print(f"  {Fore.RED}{Style.BRIGHT}ORDER STATUS: FAILED{Style.RESET_ALL}")
        print(f"{Fore.BLUE}--------------------------------------------------------------------{Style.RESET_ALL}")
        if result.get("request"):
            req = result["request"]
            print(f"  {Style.BRIGHT}Order Request Summary:{Style.RESET_ALL}")
            print(f"    Symbol:   {req['symbol']}")
            print(f"    Side:     {req['side']}")
            print(f"    Type:     {req['type']}")
            print(f"    Quantity: {req['quantity']}")
        print(f"\n  {Fore.RED}{Style.BRIGHT}Error Details: {result['error']}{Style.RESET_ALL}")
        
    print(f"{Fore.BLUE}{Style.BRIGHT}===================================================================={Style.RESET_ALL}\n")

def main():
    # Load .env variables
    load_dotenv()
    
    args = parse_args()
    
    # Setup Logger
    level_num = getattr(get_logger().level.__class__, args.log_level, 20) # default INFO
    logger = setup_logging(level=level_num)
    
    print_banner()
    
    # 1. Resolve keys and determine modes
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    is_placeholder = (
        (api_key and "your_binance_testnet" in api_key) or
        (api_secret and "your_binance_testnet" in api_secret)
    )
    
    dry_run = args.dry_run
    if not api_key or not api_secret or is_placeholder:
        if not dry_run:
            print(f"{Fore.YELLOW}Warning: API credentials not found or set to placeholder values in .env.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Defaulting to SAFE DRY-RUN mode. To execute real orders, configure your '.env' file.{Style.RESET_ALL}\n")
            dry_run = True
            
    # 2. Determine if running interactive mode
    # Run interactive mode if explicitly specified OR if symbol/side/type/quantity are missing from args
    is_interactive = args.interactive or not (args.symbol or args.side or args.type or args.quantity)
    
    try:
        if is_interactive:
            order_params = run_interactive_mode()
        else:
            # Parse parameters passed via CLI args and run through validators to ensure format
            print(f"{Fore.CYAN}Parsing command line arguments...{Style.RESET_ALL}")
            symbol = validate_symbol(args.symbol)
            side = validate_side(args.side)
            order_type = validate_order_type(args.type)
            quantity = validate_quantity(args.quantity)
            
            price = None
            if order_type == "LIMIT":
                price = validate_price(args.price, order_type)
            elif args.price:
                print(f"{Fore.YELLOW}Warning: Price argument ignored. Not needed for {order_type}.{Style.RESET_ALL}")
                
            trigger_price = None
            if order_type == "STOP_MARKET":
                trigger_price = validate_trigger_price(args.trigger_price, order_type)
            elif args.trigger_price:
                print(f"{Fore.YELLOW}Warning: Trigger price argument ignored. Not needed for {order_type}.{Style.RESET_ALL}")
                
            order_params = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": quantity,
                "price": price,
                "trigger_price": trigger_price
            }
            
    except ValidationError as e:
        print(f"\n{Fore.RED}{Style.BRIGHT}Input Validation Error: {e}{Style.RESET_ALL}")
        sys.exit(1)
        
    # 3. Print Order Preview
    mode_tag = f"{Fore.YELLOW}{Style.BRIGHT}[DRY-RUN]{Style.RESET_ALL}" if dry_run else f"{Fore.GREEN}{Style.BRIGHT}[LIVE TESTNET]{Style.RESET_ALL}"
    print(f"\n{Fore.WHITE}{Style.BRIGHT}--- ORDER PREVIEW {mode_tag} ---{Style.RESET_ALL}")
    print(f"  Symbol:        {order_params['symbol']}")
    print(f"  Side:          {order_params['side']}")
    print(f"  Type:          {order_params['type']}")
    print(f"  Quantity:      {order_params['quantity']}")
    if order_params['price']:
        print(f"  Price:         {order_params['price']}")
    if order_params['trigger_price']:
        print(f"  Trigger Price: {order_params['trigger_price']}")
    print(f"{Fore.WHITE}{Style.BRIGHT}------------------------------------{Style.RESET_ALL}")
    
    # 4. Confirmation step
    try:
        confirm = input(f"{Fore.YELLOW}Proceed to place order? (y/N): {Style.RESET_ALL}").strip().lower()
        if confirm not in ('y', 'yes'):
            print(f"{Fore.RED}Order placement aborted.{Style.RESET_ALL}")
            sys.exit(0)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
        sys.exit(0)

    # 5. Initialize client and place order
    print(f"\n{Fore.CYAN}Initializing Binance client...{Style.RESET_ALL}")
    client = BinanceFuturesClient(
        api_key=api_key, 
        api_secret=api_secret, 
        dry_run=dry_run
    )
    
    order_manager = OrderManager(client)
    print(f"{Fore.CYAN}Sending order request...{Style.RESET_ALL}")
    
    result = order_manager.place_order(
        symbol=order_params["symbol"],
        side=order_params["side"],
        order_type=order_params["type"],
        quantity=order_params["quantity"],
        price=order_params["price"],
        trigger_price=order_params["trigger_price"]
    )
    
    # 6. Display Result
    print_result_card(result)

if __name__ == "__main__":
    main()
