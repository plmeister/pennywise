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

app = typer.Typer()
console = Console()

# Common options
AMOUNT = cast(str, typer.Option("0.0", "--amount", "-a", help="Amount to transfer"))
DESCRIPTION = cast(str, typer.Option(None, "--desc", "-d", help="Transfer description"))
FROM_ACCOUNT_ID = cast(int, typer.Option(..., "--from", "-f", help="Source account ID"))
TO_ACCOUNT_ID = cast(int, typer.Option(..., "--to", "-t", help="Destination account ID"))
SHOW_LEGS = cast(bool, typer.Option(False, "--legs", "-l", help="Show transaction legs"))

@app.command()
def transfer(
    from_id: int = FROM_ACCOUNT_ID,
    to_id: int = TO_ACCOUNT_ID,
    amount: str = AMOUNT,
    description: str = DESCRIPTION,
):
    """Transfer money between accounts (with automatic currency conversion)"""
    db = next(get_db())
    account_service = AccountService(db)
    transaction_service = TransactionService(db)
    currency_service = CurrencyService(db)
    
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
        rprint(f"[red]Transfer failed:[/red] {str(e)}")

@app.command()
def list(
    account_id: int | None = typer.Option(None, "--account", "-a", help="Account ID"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days of history to show"),
    show_legs: bool = SHOW_LEGS,
):
    """List recent transactions"""
    db = next(get_db())
    service = TransactionService(db)
    account_service = AccountService(db)

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
            console.print(
                f"\n[bold]{tx.date.strftime('%Y-%m-%d')} - {tx.description or 'No description'}[/bold]"
            )
            legs_table = Table("Account", "Debit", "Credit")

            for leg in service.get_transaction_legs(tx.id):
                account = account_service.get(leg.account_id)
                if account:
                    legs_table.add_row(
                        account.name,
                        f"{Decimal(str(leg.debit)):.2f}" if leg.debit else "",
                        f"{Decimal(str(leg.credit)):.2f}" if leg.credit else "",
                    )
            console.print(legs_table)
    else:
        table = Table("Date", "Description", "Net Amount", "Accounts Involved")
        for tx in transactions:
            legs = service.get_transaction_legs(tx.id)

            net_amount = max((Decimal(str(leg.credit or 0))) for leg in legs)
            if net_amount == Decimal("0.00"):
                net_amount = max((Decimal(str(leg.debit or 0))) for leg in legs)

            account_names = []  # List[str]
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
        console.print(table)