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

app = typer.Typer()
console = Console()

# Common options
ACCOUNT_NAME = cast(str, typer.Option(..., "--name", "-n", help="Account name"))
ACCOUNT_TYPE = cast(
    str,
    typer.Option(
        "current",
        "--type",
        "-t",
        help=f"Account type ({', '.join(t.value for t in AccountType)})",
    ),
)

@app.command()
def create(
    name: str = ACCOUNT_NAME,
    type: str = ACCOUNT_TYPE,
    currency_code: str = typer.Option("GBP", "--currency", "-c", help="Currency code"),
    balance: float = typer.Option(0.0, "--balance", "-b", help="Initial balance"),
):
    """Create a new account"""
    db = next(get_db())
    account_service = AccountService(db)
    currency_service = CurrencyService(db)
    
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

@app.command()
def list():
    """List all accounts and their balances"""
    db = next(get_db())
    service = AccountService(db)
    accounts = service.get_all()

    table = Table(
        "ID", "Name", "Type", "Currency", "Balance", "Pot Balance", "Available"
    )
    for account in accounts:
        pot_balance = (
            sum(TransactionService(db).get_pot_balance(pot.id) for pot in account.pots)
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
    console.print(table)