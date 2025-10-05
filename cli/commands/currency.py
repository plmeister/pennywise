"""Currency-related CLI commands"""
import typer
from decimal import Decimal
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from sqlalchemy import and_

from database import get_db
from modules.currencies.service import CurrencyService
from modules.currencies import initialize_currencies
from models.accounts import CurrencyType, ExchangeRate

app = typer.Typer()
console = Console()

@app.command()
def init():
    """Initialize the database with common currencies"""
    db = next(get_db())
    try:
        initialize_currencies(db)
        rprint("[green]Successfully initialized currencies[/green]")
    except Exception as e:
        rprint(f"[red]Error initializing currencies:[/red] {str(e)}")

@app.command()
def list(
    type: str = typer.Option(None, "--type", "-t", help="Filter by currency type (fiat/crypto)")
):
    """List all available currencies"""
    db = next(get_db())
    service = CurrencyService(db)
    
    curr_type = CurrencyType(type) if type else None
    currencies = service.list_currencies(curr_type)
    
    table = Table("Code", "Name", "Symbol", "Type", "Decimals", "Active")
    for curr in currencies:
        table.add_row(
            curr.code,
            curr.name,
            curr.symbol,
            curr.type.value,
            str(curr.decimals),
            "✓" if curr.is_active else "✗"
        )
    console.print(table)

@app.command()
def rates(
    base: str = typer.Option(..., "--base", "-b", help="Base currency code"),
    target: str = typer.Option(None, "--target", "-t", help="Target currency code (optional)"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days of history to show")
):
    """View exchange rates for a currency"""
    db = next(get_db())
    service = CurrencyService(db)
    
    try:
        base_currency = service.get_by_code(base)
        if not base_currency:
            rprint(f"[red]Currency not found:[/red] {base}")
            return
            
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        if target:
            target_currency = service.get_by_code(target)
            if not target_currency:
                rprint(f"[red]Currency not found:[/red] {target}")
                return
                
            table = Table("Date", f"1 {base} =", f"{target}")
            rates = service.db.query(ExchangeRate).filter(
                and_(
                    ExchangeRate.from_currency_id == base_currency.id,
                    ExchangeRate.to_currency_id == target_currency.id,
                    ExchangeRate.timestamp >= start_date,
                    ExchangeRate.timestamp <= end_date
                )
            ).order_by(ExchangeRate.timestamp.desc()).all()
            
            for rate in rates:
                table.add_row(
                    rate.timestamp.strftime("%Y-%m-%d"),
                    "=",
                    f"{rate.rate:.{target_currency.decimals}f}"
                )
            
            if not rates:
                rprint(f"[yellow]No exchange rates found for {base}/{target} in the last {days} days[/yellow]")
                return
                
            console.print(f"\nExchange rates for {base}/{target}:")
            console.print(table)
        else:
            table = Table("Currency", "Code", f"1 {base} =")
            currencies = service.list_currencies()
            
            for curr in currencies:
                if curr.id != base_currency.id:
                    rate = service.get_exchange_rate(base, curr.code)
                    if rate:
                        table.add_row(
                            curr.name,
                            curr.code,
                            f"{rate:.{curr.decimals}f}"
                        )
            
            console.print(f"\nLatest exchange rates for {base}:")
            console.print(table)
            
    except Exception as e:
        rprint(f"[red]Error getting exchange rates:[/red] {str(e)}")

@app.command()
def convert(
    amount: float = typer.Option(..., "--amount", "-a", help="Amount to convert"),
    from_currency: str = typer.Option(..., "--from", "-f", help="From currency code"),
    to_currency: str = typer.Option(..., "--to", "-t", help="To currency code")
):
    """Convert an amount between currencies"""
    db = next(get_db())
    service = CurrencyService(db)
    
    try:
        from_curr = service.get_by_code(from_currency)
        to_curr = service.get_by_code(to_currency)
        if not from_curr or not to_curr:
            rprint("[red]One or both currencies not found[/red]")
            return
            
        rate = service.get_exchange_rate(from_currency, to_currency)
        if rate is None:
            rprint(f"[red]No exchange rate found for {from_currency}/{to_currency}[/red]")
            return
            
        from_amount = Decimal(str(amount))
        to_amount = from_amount * rate
        
        rprint(f"\nCurrency Conversion:")
        rprint(f"{from_curr.symbol}{amount:.{from_curr.decimals}f} {from_curr.code} = "
               f"{to_curr.symbol}{to_amount:.{to_curr.decimals}f} {to_curr.code}")
        rprint(f"\nRate: 1 {from_curr.code} = {rate:.{to_curr.decimals}f} {to_curr.code}")
        
    except Exception as e:
        rprint(f"[red]Conversion failed:[/red] {str(e)}")

@app.command()
def set_rate(
    from_currency: str = typer.Option(..., "--from", "-f", help="From currency code"),
    to_currency: str = typer.Option(..., "--to", "-t", help="To currency code"),
    rate: float = typer.Option(..., "--rate", "-r", help="Exchange rate (1 FROM = x TO)"),
):
    """Set the exchange rate between two currencies"""
    db = next(get_db())
    service = CurrencyService(db)
    
    try:
        exchange_rate = service.set_exchange_rate(
            from_currency_code=from_currency,
            to_currency_code=to_currency,
            rate=Decimal(str(rate))
        )
        
        # Also set the inverse rate automatically
        inverse_rate = Decimal(1) / Decimal(str(rate))
        service.set_exchange_rate(
            from_currency_code=to_currency,
            to_currency_code=from_currency,
            rate=inverse_rate
        )
        
        rprint(f"[green]Set exchange rates:[/green]")
        rprint(f"1 {from_currency} = {rate} {to_currency}")
        rprint(f"1 {to_currency} = {inverse_rate:.8f} {from_currency}")
    except Exception as e:
        rprint(f"[red]Error setting exchange rate:[/red] {str(e)}")