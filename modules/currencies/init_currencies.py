from modules.currencies.service import CurrencyService
from models.accounts import CurrencyType
from sqlalchemy.orm import Session

def initialize_currencies(db: Session):
    """Initialize the database with common currencies"""
    service = CurrencyService(db)
    
    # Common fiat currencies
    fiat_currencies = [
        ("USD", "US Dollar", "$", 2),
        ("GBP", "British Pound", "£", 2),
        ("EUR", "Euro", "€", 2),
        ("JPY", "Japanese Yen", "¥", 0),
        ("AUD", "Australian Dollar", "A$", 2),
        ("CAD", "Canadian Dollar", "C$", 2),
        ("CHF", "Swiss Franc", "Fr", 2),
        ("CNY", "Chinese Yuan", "¥", 2),
    ]
    
    # Common cryptocurrencies
    crypto_currencies = [
        ("BTC", "Bitcoin", "₿", 8),
        ("ETH", "Ethereum", "Ξ", 18),
        ("USDT", "Tether", "₮", 6),
        ("BNB", "Binance Coin", "BNB", 8),
        ("SOL", "Solana", "SOL", 9),
        ("ADA", "Cardano", "ADA", 6),
        ("DOT", "Polkadot", "DOT", 10),
        ("MATIC", "Polygon", "MATIC", 18),
        ("DOGE", "Dogecoin", "Ð", 8),
    ]
    
    # Add fiat currencies
    for code, name, symbol, decimals in fiat_currencies:
        if not service.get_by_code(code):
            service.create_currency(
                code=code,
                name=name,
                symbol=symbol,
                type=CurrencyType.fiat,
                decimals=decimals
            )
    
    # Add cryptocurrencies
    for code, name, symbol, decimals in crypto_currencies:
        if not service.get_by_code(code):
            service.create_currency(
                code=code,
                name=name,
                symbol=symbol,
                type=CurrencyType.crypto,
                decimals=decimals
            )