"""Account-related CLI commands"""
import typer
from decimal import Decimal
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import cast

from database import get_db
from modules.accounts.service import AccountService
from modules.transactions.service import TransactionService
from modules.currencies.service import CurrencyService
from models.accounts import AccountType

account_app = typer.Typer()

class AccountContext:
    def __init__(self, db_path: str):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)
        self.db = SessionLocal()
        self.console = Console()

@account_app.callback()
def main(ctx: typer.Context, db_path: str = typer.Option("budget.db", help="Path to database file")):
    """Account CLI group callback to set up DB/session."""
    ctx.obj = AccountContext(db_path)

@account_app.command()
def list(ctx: typer.Context):
    """List all accounts and their balances"""
    context: AccountContext = ctx.obj
    service = AccountService(context.db)
    accounts = service.get_all()
    table = Table(
        "ID", "Name", "Type", "Currency", "Balance", "Pot Balance", "Available"
    )
    for account in accounts:
        pot_balance = (
            sum(TransactionService(context.db).get_pot_balance(pot.id) for pot in account.pots)
            if account.pots
            else Decimal("0.00")
        )
        available = account.balance - pot_balance
        symbol = account.currency.symbol
        table.add_row(
            str(account.id),
            account.name,
            account.type,
            f"{account.currency.code} ({account.currency.type.value})",
            f"{symbol}{account.balance:.{account.currency.decimals}f}",
            f"{symbol}{float(pot_balance):.{account.currency.decimals}f}",
            f"{symbol}{float(available):.{account.currency.decimals}f}",
        )
    context.console.print(table)

@account_app.command()
def create(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Account name"),
    type: str = typer.Option("current", "--type", "-t", help=f"Account type ({', '.join(t.value for t in AccountType)})"),
    currency_code: str = typer.Option("GBP", "--currency", "-c", help="Currency code"),
    balance: float = typer.Option(0.0, "--balance", "-b", help="Initial balance"),
):
    """Create a new account"""
    context: AccountContext = ctx.obj
    account_service = AccountService(context.db)
    currency_service = CurrencyService(context.db)
    try:
        currency = currency_service.get_by_code(currency_code)
        if not currency:
            rprint(f"[red]Error:[/red] Currency {currency_code} not found")
            return
        account = account_service.create_account(
            name=name,
            account_type=type,
            currency_id=currency.id,
            initial_balance=Decimal(str(balance))
        )
        rprint(f"[green]Created account:[/green] {account.name} (ID: {account.id})")
        rprint(f"Currency: {currency.code} ({currency.symbol})")
        if balance > 0:
            rprint(f"Initial balance: {currency.symbol}{balance:.{currency.decimals}f}")
    except Exception as e:
        rprint(f"[red]Error creating account:[/red] {str(e)}")