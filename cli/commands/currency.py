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


currency_app = typer.Typer()

class CurrencyContext:
    def __init__(self, db_path: str):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)
        self.db = SessionLocal()
        self.console = Console()

@currency_app.callback()
def main(ctx: typer.Context, db_path: str = typer.Option("budget.db", help="Path to database file")):
    """Currency CLI group callback to set up DB/session."""
    ctx.obj = CurrencyContext(db_path)

@currency_app.command()
def init(ctx: typer.Context):
    """Initialize the database with common currencies"""
    context: CurrencyContext = ctx.obj
    try:
        initialize_currencies(context.db)
        rprint("[green]Successfully initialized currencies[/green]")
    except Exception as e:
        rprint(f"[red]Error initializing currencies:[/red] {str(e)}")

@currency_app.command()
def list(
    ctx: typer.Context,
    type: str = typer.Option(None, "--type", "-t", help="Filter by currency type (fiat/crypto)")
):
    """List all available currencies"""
    context: CurrencyContext = ctx.obj
    service = CurrencyService(context.db)
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
    context.console.print(table)

@currency_app.command()
def rates(
    ctx: typer.Context,
    base: str = typer.Option(..., "--base", "-b", help="Base currency code"),
    target: str = typer.Option(None, "--target", "-t", help="Target currency code (optional)"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days of history to show")
):
    """View exchange rates for a currency"""
    context: CurrencyContext = ctx.obj
    service = CurrencyService(context.db)
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
                )
            ).all()
            for rate in rates:
                rate_date = getattr(rate, 'date', None) or getattr(rate, 'created_at', None) or getattr(rate, 'timestamp', None)
                date_str = rate_date.strftime("%Y-%m-%d") if rate_date else "?"
                table.add_row(
                    date_str,
                    f"{rate.rate:.{base_currency.decimals}f}",
                    f"{rate.rate:.{target_currency.decimals}f}"
                )
            context.console.print(table)
        else:
            rates = service.db.query(ExchangeRate).filter(
                ExchangeRate.from_currency_id == base_currency.id
            ).all()
            table = Table("Date", "To Currency", "Rate")
            for rate in rates:
                rate_date = getattr(rate, 'date', None) or getattr(rate, 'created_at', None) or getattr(rate, 'timestamp', None)
                date_str = rate_date.strftime("%Y-%m-%d") if rate_date else "?"
                to_curr = service.db.query(CurrencyType).get(rate.to_currency_id)
                table.add_row(
                    date_str,
                    to_curr.code if to_curr else str(rate.to_currency_id),
                    f"{rate.rate:.{base_currency.decimals}f}"
                )
            context.console.print(table)
    except Exception as e:
        rprint(f"[red]Error getting exchange rates:[/red] {str(e)}")
@currency_app.command()
def convert(
    ctx: typer.Context,
    from_currency: str = typer.Option(..., "--from", "-f", help="From currency code"),
    to_currency: str = typer.Option(..., "--to", "-t", help="To currency code"),
    amount: float = typer.Option(..., "--amount", "-a", help="Amount to convert")
):
    """Convert an amount between currencies"""
    context: CurrencyContext = ctx.obj
    service = CurrencyService(context.db)
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
        rprint(f"[red]Error converting currency:[/red] {str(e)}")
        
    @currency_app.command()
    def rates(
        ctx: typer.Context,
        base: str = typer.Option(..., "--base", "-b", help="Base currency code"),
        target: str = typer.Option(None, "--target", "-t", help="Target currency code (optional)"),
        days: int = typer.Option(7, "--days", "-d", help="Number of days of history to show")
    ):
        """View exchange rates for a currency"""
        context: CurrencyContext = ctx.obj
        service = CurrencyService(context.db)
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
                    )
                ).all()
                for rate in rates:
                    rate_date = getattr(rate, 'date', None) or getattr(rate, 'created_at', None) or getattr(rate, 'timestamp', None)
                    date_str = rate_date.strftime("%Y-%m-%d") if rate_date else "?"
                    table.add_row(
                        date_str,
                        f"{rate.rate:.{base_currency.decimals}f}",
                        f"{rate.rate:.{target_currency.decimals}f}"
                    )
                context.console.print(table)
            else:
                rates = service.db.query(ExchangeRate).filter(
                    ExchangeRate.from_currency_id == base_currency.id
                ).all()
                table = Table("Date", "To Currency", "Rate")
                for rate in rates:
                    rate_date = getattr(rate, 'date', None) or getattr(rate, 'created_at', None) or getattr(rate, 'timestamp', None)
                    date_str = rate_date.strftime("%Y-%m-%d") if rate_date else "?"
                    to_curr = service.db.query(CurrencyType).get(rate.to_currency_id)
                    table.add_row(
                        date_str,
                        to_curr.code if to_curr else str(rate.to_currency_id),
                        f"{rate.rate:.{base_currency.decimals}f}"
                    )
                context.console.print(table)
        except Exception as e:
            rprint(f"[red]Error getting exchange rates:[/red] {str(e)}")