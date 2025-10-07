"""Transaction-related CLI commands"""
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
from modules.currencies.service import CurrencyService

import traceback


transactions_app = typer.Typer()

class TransactionContext:
    def __init__(self, db_path: str):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)
        self.db = SessionLocal()
        self.console = Console()

@transactions_app.callback()
def main(ctx: typer.Context, db_path: str = typer.Option("budget.db", help="Path to database file")):
    """Transactions CLI group callback to set up DB/session."""
    ctx.obj = TransactionContext(db_path)

# Common options
AMOUNT = cast(str, typer.Option("0.0", "--amount", "-a", help="Amount to transfer"))
DESCRIPTION = cast(str, typer.Option(None, "--desc", "-d", help="Transfer description"))
FROM_ACCOUNT_ID = cast(int, typer.Option(..., "--from", "-f", help="Source account ID"))
TO_ACCOUNT_ID = cast(int, typer.Option(..., "--to", "-t", help="Destination account ID"))
SHOW_LEGS = cast(bool, typer.Option(False, "--legs", "-l", help="Show transaction legs"))

@transactions_app.command()
def transfer(
    ctx: typer.Context,
    from_id: int = typer.Option(..., "--from", "-f", help="Source account ID"),
    to_id: int = typer.Option(..., "--to", "-t", help="Destination account ID"),
    amount: str = typer.Option("0.0", "--amount", "-a", help="Amount to transfer"),
    description: str = typer.Option(None, "--desc", "-d", help="Transfer description"),
):
    """Transfer money between accounts (with automatic currency conversion)"""
    context: TransactionContext = ctx.obj
    account_service = AccountService(context.db)
    transaction_service = TransactionService(context.db)
    currency_service = CurrencyService(context.db)
    try:
        from_account = account_service.get(from_id)
        to_account = account_service.get(to_id)
        if not from_account or not to_account:
            raise ValueError("One or both accounts not found")
        amount_decimal = Decimal(amount)
        if from_account.currency_id != to_account.currency_id:
            rate = currency_service.get_exchange_rate(
                from_account.currency.code,
                to_account.currency.code
            )
            if rate is None:
                raise ValueError(
                    f"No exchange rate found from {from_account.currency.code} "
                    f"to {to_account.currency.code}"
                )
            converted_amount = amount_decimal * rate
            rprint(f"Exchange rate: 1 {from_account.currency.code} = "
                  f"{rate:.{to_account.currency.decimals}f} {to_account.currency.code}")
            rprint(f"Converting {from_account.currency.symbol}{amount_decimal:.{from_account.currency.decimals}f} to "
                  f"{to_account.currency.symbol}{converted_amount:.{to_account.currency.decimals}f}")
        transaction = transaction_service.create_transfer(
            from_id, to_id, amount_decimal, description
        )
        debit_legs = [leg for leg in transaction.legs if leg.debit is not None and leg.debit > 0]
        credit_legs = [leg for leg in transaction.legs if leg.credit is not None and leg.credit > 0]
        from_amount = debit_legs[0].debit if debit_legs else Decimal("0")
        to_amount = credit_legs[0].credit if credit_legs else Decimal("0")
        rprint(f"[green]Successfully transferred[/green] "
               f"{from_account.currency.symbol}{from_amount:.{from_account.currency.decimals}f} "
               f"from {from_account.name}")
        if from_account.currency_id != to_account.currency_id:
            rprint(f"[green]Received:[/green] "
                   f"{to_account.currency.symbol}{to_amount:.{to_account.currency.decimals}f} "
                   f"in {to_account.name}")
    except Exception as e:
        traceback.print_exc()
        rprint(f"[red]Transfer failed:[/red] {str(e)}")

@transactions_app.command()
def list(
    ctx: typer.Context,
    account_id: int = typer.Option(None, "--account", "-a", help="Account ID"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days of history to show"),
    show_legs: bool = typer.Option(False, "--legs", "-l", help="Show transaction legs"),
):
    """List recent transactions"""
    context: TransactionContext = ctx.obj
    service = TransactionService(context.db)
    account_service = AccountService(context.db)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    if account_id:
        transactions = service.get_account_transactions(
            account_id, start_date, end_date
        )
    else:
        transactions = service.get_all()
    if show_legs:
        for tx in transactions:
            context.console.print(
                f"\n[bold]{tx.date.strftime('%Y-%m-%d')} - {tx.description or 'No description'}[/bold]"
            )
            legs_table = Table("Date", "Description", "Account", "Debit", "Credit")
            first_leg = True
            for leg in service.get_transaction_legs(tx.id):
                account = account_service.get(leg.account_id)
                if account:
                    if first_leg:
                        first_leg = False
                        legs_table.add_row(
                            tx.date.strftime("%Y-%m-%d"),
                            tx.description or "",
                            account.name,
                            f"{Decimal(str(leg.debit)):.2f}" if leg.debit else "",
                            f"{Decimal(str(leg.credit)):.2f}" if leg.credit else "",
                        )
                    else:
                        legs_table.add_row(
                            "",
                            "",
                            account.name,
                            f"{Decimal(str(leg.debit)):.2f}" if leg.debit else "",
                            f"{Decimal(str(leg.credit)):.2f}" if leg.credit else "",
                        )
            context.console.print(legs_table)
    else:
        table = Table("Date", "Description", "Net Amount", "Accounts Involved")
        for tx in transactions:
            legs = service.get_transaction_legs(tx.id)
            net_amount = max((Decimal(str(leg.credit or 0))) for leg in legs)
            if net_amount == Decimal("0.00"):
                net_amount = max((Decimal(str(leg.debit or 0))) for leg in legs)
            account_names = []
            for leg in legs:
                account = account_service.get(leg.account_id)
                if account:
                    account_names.append(account.name)
            table.add_row(
                tx.date.strftime("%Y-%m-%d"),
                tx.description or "",
                f"{net_amount:.2f}",
                ", ".join(account_names),
            )
        context.console.print(table)