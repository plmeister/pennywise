import typer

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# Import local modules
from database import get_db
from modules.accounts.service import AccountService
from modules.transactions.service import TransactionService

from models.accounts import AccountType, Currency
from typing import cast

app = typer.Typer()
console = Console()

# Create database engine and session
DATABASE_URL = "sqlite:///./budget.db"
engine = create_engine(DATABASE_URL)
# SessionLocal = get_db()

ACCOUNT_NAME = cast(str, typer.Option(..., "--name", "-n", help="Account name"))
ACCOUNT_TYPE = cast(
    AccountType,
    typer.Option(
        "current",
        "--type",
        "-t",
        help=f"Account type ({', '.join(t.value for t in AccountType)})",
    ),
)
ACCOUNT_CURRENCY = cast(
    Currency,
    typer.Option(
        "GBP",
        "--currency",
        "-c",
        help=f"Currency ({', '.join(c.value for c in Currency)})",
    ),
)


# Account Commands
@app.command()
def create_account(
    name: str = ACCOUNT_NAME,
    type: AccountType = ACCOUNT_TYPE,
    currency: Currency = ACCOUNT_CURRENCY,
):
    """Create a new account"""
    db = next(get_db())
    service = AccountService(db)
    try:
        account = service.create_account(
            name=name, account_type=type, currency=currency
        )
        # curr_symbol = Currency(currency).symbol
        rprint(
            f"[green]Created account:[/green] {account.name} (ID: {account.id}) [{currency}]"
        )
    except Exception as e:
        rprint(f"[red]Error creating account:[/red] {str(e)}")


@app.command()
def list_accounts():
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
            account.currency.value,
            f"{symbol}{account.balance:.2f}",
            f"{symbol}{pot_balance:.2f}",
            f"{symbol}{available:.2f}",
        )
    console.print(table)


DECIMAL_ZERO = Decimal(0.0)

ACCOUNT_ID = cast(int, typer.Option(..., "--account", "-a", help="Account ID"))
POT_NAME = cast(str, typer.Option(..., "--name", "-n", help="Pot name"))
TARGET_AMOUNT = cast(
    str,
    typer.Option(
        str(DECIMAL_ZERO),
        "--target",
        "-t",
        help="Savings target",
    ),
)


@app.command()
def create_pot(
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


FROM_ACCOUNT_ID = cast(int, typer.Option(..., "--from", "-f", help="Source account ID"))
TO_ACCOUNT_ID = cast(
    int, typer.Option(..., "--to", "-t", help="Destination account ID")
)
AMOUNT = cast(str, typer.Option("0.0", "--amount", "-a", help="Amount to transfer"))
DESCRIPTION = cast(str, typer.Option(None, "--desc", "-d", help="Transfer description"))


@app.command()
def transfer(
    from_id: int = FROM_ACCOUNT_ID,
    to_id: int = TO_ACCOUNT_ID,
    amount: str = AMOUNT,
    description: str = DESCRIPTION,
):
    """Transfer money between accounts"""
    db = next(get_db())
    service = AccountService(db)
    amount_decimal: Decimal = Decimal(amount)
    try:
        _ = service.transfer(
            from_id=from_id, to_id=to_id, amount=amount_decimal, description=description
        )
        rprint(f"[green]Successfully transferred[/green] {amount:.2f}")
    except Exception as e:
        rprint(f"[red]Transfer failed:[/red] {str(e)}")


@app.command()
def list_pots(account_id: int | None = ACCOUNT_ID):
    """List all savings pots and their balances"""
    db = next(get_db())
    account_service = AccountService(db)
    transaction_service = TransactionService(db)

    accounts = (
        [account_service.get(account_id)] if account_id else account_service.get_all()
    )

    for account in accounts:
        if account and account.pots:
            console.print(f"\n[bold]{account.name}[/bold]")
            table = Table("ID", "Name", "Target", "Current Amount", "Progress")
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
                    f"{Decimal(str(pot.target_amount)):.2f}"
                    if pot.target_amount
                    else "No target",
                    f"{balance:.2f}",
                    progress,
                )
            console.print(table)


POT_ID = cast(int, typer.Option(..., "--pot", "-p", help="Pot ID"))
POT_DIRECTION = cast(
    str, typer.Option(..., "--direction", "-d", help="'to_pot' or 'from_pot'")
)


@app.command()
def pot_transfer(
    account_id: int = ACCOUNT_ID,
    pot_id: int = POT_ID,
    amount: str = AMOUNT,
    direction: str = POT_DIRECTION,
    description: str | None = DESCRIPTION,
):
    """Transfer money to/from a savings pot"""
    db = next(get_db())
    service = TransactionService(db)
    amount_decimal: Decimal = Decimal(amount)
    try:
        if direction == "to_pot":
            _ = service.transfer_to_pot(
                account_id=account_id,
                pot_id=pot_id,
                amount=amount_decimal,
                description=description,
            )
        elif direction == "from_pot":
            _ = service.transfer_from_pot(
                account_id=account_id,
                pot_id=pot_id,
                amount=amount_decimal,
                description=description,
            )
        else:
            raise ValueError("Direction must be either 'to_pot' or 'from_pot'")

        rprint(
            f"[green]Successfully transferred[/green] {amount_decimal:.2f} {direction.replace('_', ' ')}"
        )
    except Exception as e:
        rprint(f"[red]Pot transfer failed:[/red] {str(e)}")


FROM_POT = cast(int, typer.Option(..., "--from", "-f", help="Source pot ID"))
TO_POT = cast(int, typer.Option(..., "--to", "-t", help="Destination pot ID"))


@app.command()
def pot_to_pot(
    account_id: int = ACCOUNT_ID,
    from_pot: int = FROM_POT,
    to_pot: int = TO_POT,
    amount: str = AMOUNT,
    description: str | None = DESCRIPTION,
):
    """Transfer money between two pots in the same account"""
    db = next(get_db())
    service = TransactionService(db)
    amount_decimal = Decimal(amount)
    try:
        _ = service.transfer_between_pots(
            account_id=account_id,
            from_pot_id=from_pot,
            to_pot_id=to_pot,
            amount=amount_decimal,
            description=description,
        )
        rprint(
            f"[green]Successfully transferred[/green] {amount_decimal:.2f} between pots"
        )
    except Exception as e:
        rprint(f"[red]Pot transfer failed:[/red] {str(e)}")


DAYS = cast(
    int, typer.Option(30, "--days", "-d", help="Number of days of history to show")
)


@app.command()
def pot_transactions(
    pot_id: int = POT_ID,
    days: int = DAYS,
):
    """Show transaction history for a specific pot"""
    db = next(get_db())
    service = TransactionService(db)

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    transactions = service.get_pot_transactions(pot_id, start_date, end_date)

    if not transactions:
        rprint(
            "[yellow]No transactions found for this pot in the specified time period[/yellow]"
        )
        return

    table = Table("Date", "Description", "Amount", "Type")
    for tx in transactions:
        for leg in service.get_transaction_legs(tx.id):
            if leg.pot_id == pot_id:
                amount = Decimal(str(leg.credit or 0)) or -Decimal(str(leg.debit or 0))
                table.add_row(
                    tx.date.strftime("%Y-%m-%d"),
                    tx.description or "",
                    f"{abs(amount):.2f}",
                    "IN" if amount > Decimal("0.00") else "OUT",
                )
    console.print(table)


SHOW_LEGS = cast(
    bool, typer.Option(False, "--legs", "-l", help="Show transaction legs")
)


@app.command()
def list_transactions(
    account_id: int | None = ACCOUNT_ID,
    days: int = DAYS,
    show_legs: bool = SHOW_LEGS,
):
    """List recent transactions"""
    db = next(get_db())
    service = TransactionService(db)
    account_service = AccountService(db)

    end_date = datetime.now().date()
    start_date = end_date + timedelta(days=days)

    if account_id:
        transactions = service.get_account_transactions(
            account_id, start_date, end_date
        )
    else:
        transactions = service.get_all()

    if show_legs:
        # Show detailed view with all transaction legs
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
        # Show simplified view
        table = Table("Date", "Description", "Net Amount", "Accounts Involved")
        for tx in transactions:
            legs = service.get_transaction_legs(tx.id)

            # Calculate net amount from leg with most credit
            net_amount = max((Decimal(str(leg.credit or 0))) for leg in legs)
            if net_amount == Decimal("0.00"):
                net_amount = max((Decimal(str(leg.debit or 0))) for leg in legs)

            # Get account names
            account_names: list[str] = []
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


def main():
    app()


if __name__ == "__main__":
    main()
