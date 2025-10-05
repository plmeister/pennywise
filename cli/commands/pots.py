"""Savings pot-related CLI commands"""
import typer
from decimal import Decimal
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import cast

from database import get_db
from modules.accounts.service import AccountService
from modules.transactions.service import TransactionService
from models.accounts import Pot

app = typer.Typer()
console = Console()

# Common options
DECIMAL_ZERO = Decimal(0.0)
ACCOUNT_ID = cast(int, typer.Option(..., "--account", "-a", help="Account ID"))
POT_NAME = cast(str, typer.Option(..., "--name", "-n", help="Pot name"))
POT_ID = cast(int, typer.Option(..., "--pot", "-p", help="Pot ID"))
TARGET_AMOUNT = cast(str, typer.Option(str(DECIMAL_ZERO), "--target", "-t", help="Savings target"))
AMOUNT = cast(str, typer.Option("0.0", "--amount", "-a", help="Amount to transfer"))
DESCRIPTION = cast(str, typer.Option(None, "--desc", "-d", help="Transfer description"))
FROM_POT = cast(int, typer.Option(..., "--from", "-f", help="Source pot ID"))
TO_POT = cast(int, typer.Option(..., "--to", "-t", help="Destination pot ID"))
POT_DIRECTION = cast(str, typer.Option(..., "--direction", "-d", help="'to_pot' or 'from_pot'"))

@app.command()
def create(
    account_id: int = ACCOUNT_ID,
    name: str = POT_NAME,
    target: str = TARGET_AMOUNT,
):
    """Create a new savings pot within an account"""
    db = next(get_db())
    service = AccountService(db)
    decimal_target: Decimal = Decimal(target)
    try:
        pot = service.create_pot(
            account_id,
            name,
            target_amount=decimal_target,
        )
        rprint(f"[green]Created pot:[/green] {pot.name} in account {account_id}")
    except Exception as e:
        rprint(f"[red]Error creating pot:[/red] {str(e)}")

@app.command()
def list(account_id: int | None = ACCOUNT_ID):
    """List all savings pots and their balances"""
    db = next(get_db())
    account_service = AccountService(db)
    transaction_service = TransactionService(db)

    accounts = (
        [account_service.get(account_id)] if account_id else account_service.get_all()
    )

    for account in accounts:
        if account and account.pots:
            console.print(f"\n[bold]{account.name}[/bold] ({account.currency.code})")
            table = Table("ID", "Name", "Target", "Current Amount", "Progress")
            
            decimals = account.currency.decimals
            symbol = account.currency.symbol
            
            for pot in account.pots:
                balance = transaction_service.get_pot_balance(pot.id)
                progress = (
                    f"{(balance / Decimal(str(pot.target_amount)) * 100):.1f}%"
                    if pot.target_amount
                    else "N/A"
                )
                table.add_row(
                    str(pot.id),
                    pot.name,
                    f"{symbol}{Decimal(str(pot.target_amount)):.{decimals}f}"
                    if pot.target_amount
                    else "No target",
                    f"{symbol}{balance:.{decimals}f}",
                    progress,
                )
            console.print(table)

@app.command()
def transfer(
    account_id: int = ACCOUNT_ID,
    pot_id: int = POT_ID,
    amount: str = AMOUNT,
    direction: str = POT_DIRECTION,
    description: str | None = DESCRIPTION,
):
    """Transfer money to/from a savings pot"""
    db = next(get_db())
    service = TransactionService(db)
    account_service = AccountService(db)
    amount_decimal: Decimal = Decimal(amount)
    
    try:
        account = account_service.get(account_id)
        if not account:
            raise ValueError("Account not found")
            
        decimals = account.currency.decimals
        symbol = account.currency.symbol
        
        if direction == "to_pot":
            transaction = service.transfer_to_pot(
                account_id=account_id,
                pot_id=pot_id,
                amount=amount_decimal,
                description=description,
            )
        elif direction == "from_pot":
            transaction = service.transfer_from_pot(
                account_id=account_id,
                pot_id=pot_id,
                amount=amount_decimal,
                description=description,
            )
        else:
            raise ValueError("Direction must be either 'to_pot' or 'from_pot'")

        rprint(
            f"[green]Successfully transferred[/green] "
            f"{symbol}{amount_decimal:.{decimals}f} {direction.replace('_', ' ')}"
        )
    except Exception as e:
        rprint(f"[red]Pot transfer failed:[/red] {str(e)}")

@app.command()
def transfer_between(
    account_id: int = ACCOUNT_ID,
    from_pot: int = FROM_POT,
    to_pot: int = TO_POT,
    amount: str = AMOUNT,
    description: str | None = DESCRIPTION,
):
    """Transfer money between two pots in the same account"""
    db = next(get_db())
    service = TransactionService(db)
    account_service = AccountService(db)
    amount_decimal: Decimal = Decimal(amount)
    
    try:
        account = account_service.get(account_id)
        if not account:
            raise ValueError("Account not found")
            
        decimals = account.currency.decimals
        symbol = account.currency.symbol
        
        transaction = service.transfer_between_pots(
            account_id=account_id,
            from_pot_id=from_pot,
            to_pot_id=to_pot,
            amount=amount_decimal,
            description=description,
        )
        rprint(
            f"[green]Successfully transferred[/green] "
            f"{symbol}{amount_decimal:.{decimals}f} between pots"
        )
    except Exception as e:
        rprint(f"[red]Pot transfer failed:[/red] {str(e)}")

@app.command()
def transactions(
    pot_id: int = POT_ID,
    days: int = typer.Option(30, "--days", "-d", help="Number of days of history to show"),
):
    """Show transaction history for a specific pot"""
    db = next(get_db())
    service = TransactionService(db)
    account_service = AccountService(db)

    try:
        pot = db.query(Pot).get(pot_id)
        if not pot:
            raise ValueError("Pot not found")
            
        account = account_service.get(pot.account_id)
        if not account:
            raise ValueError("Account not found")
            
        decimals = account.currency.decimals
        symbol = account.currency.symbol

        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        transactions = service.get_pot_transactions(pot_id, start_date, end_date)

        if not transactions:
            rprint(
                "[yellow]No transactions found for this pot in the specified time period[/yellow]"
            )
            return

        console.print(f"\nTransactions for pot: {pot.name}")
        console.print(f"Currency: {account.currency.code} ({symbol})")
        table = Table("Date", "Description", "Amount", "Type")
        
        for tx in transactions:
            for leg in service.get_transaction_legs(tx.id):
                if leg.pot_id == pot_id:
                    amount = leg.credit if leg.credit is not None else (-leg.debit if leg.debit is not None else Decimal("0"))
                    table.add_row(
                        tx.date.strftime("%Y-%m-%d"),
                        tx.description or "",
                        f"{symbol}{abs(amount):.{decimals}f}",
                        "IN" if amount > 0 else "OUT",
                    )
        console.print(table)
    except Exception as e:
        rprint(f"[red]Error:[/red] {str(e)}")