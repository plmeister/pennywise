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
from modules.currencies.service import CurrencyService
from modules.currencies import initialize_currencies

from models.accounts import AccountType, Currency, CurrencyType, Pot, ExchangeRate
from sqlalchemy import and_
from typing import cast, Optional

app = typer.Typer()
console = Console()

# Create database engine and session
DATABASE_URL = "sqlite:///./budget.db"
engine = create_engine(DATABASE_URL)
# SessionLocal = get_db()

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


# Currency Commands
@app.command()
def init_currencies():
    """Initialize the database with common currencies"""
    db = next(get_db())
    try:
        initialize_currencies(db)
        rprint("[green]Successfully initialized currencies[/green]")
    except Exception as e:
        rprint(f"[red]Error initializing currencies:[/red] {str(e)}")

@app.command()
def list_currencies(
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
        
        # If target currency specified, show rate history for that pair
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
            
        # Otherwise show latest rates for all currencies
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
        # Get currencies
        from_curr = service.get_by_code(from_currency)
        to_curr = service.get_by_code(to_currency)
        if not from_curr or not to_curr:
            rprint("[red]One or both currencies not found[/red]")
            return
            
        # Get conversion rate
        rate = service.get_exchange_rate(from_currency, to_currency)
        if rate is None:
            rprint(f"[red]No exchange rate found for {from_currency}/{to_currency}[/red]")
            return
            
        # Calculate conversion
        from_amount = Decimal(str(amount))
        to_amount = from_amount * rate
        
        # Show results
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

@app.command()
def set_exchange_rate(
    from_currency: str = typer.Option(..., "--from", "-f", help="From currency code"),
    to_currency: str = typer.Option(..., "--to", "-t", help="To currency code"),
    rate: float = typer.Option(..., "--rate", "-r", help="Exchange rate"),
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
        rprint(f"[green]Set exchange rate:[/green] 1 {from_currency} = {rate} {to_currency}")
    except Exception as e:
        rprint(f"[red]Error setting exchange rate:[/red] {str(e)}")

# Account Commands
@app.command()
def create_account(
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
        # Verify currency exists
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
            f"{account.currency.code} ({account.currency.type.value})",
            f"{symbol}{account.balance:.{account.currency.decimals}f}",
            f"{symbol}{float(pot_balance):.{account.currency.decimals}f}",
            f"{symbol}{float(available):.{account.currency.decimals}f}",
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
    """Transfer money between accounts (with automatic currency conversion)"""
    db = next(get_db())
    account_service = AccountService(db)
    transaction_service = TransactionService(db)
    currency_service = CurrencyService(db)
    
    try:
        # Get accounts to show currency info
        from_account = account_service.get(from_id)
        to_account = account_service.get(to_id)
        if not from_account or not to_account:
            raise ValueError("One or both accounts not found")
            
        amount_decimal = Decimal(amount)
            
        # If currencies differ, show exchange rate info
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
        
        # Perform transfer
        transaction = transaction_service.create_transfer(
            from_id, to_id, amount_decimal, description
        )
        
        # Show success message with proper currency symbols
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
            console.print(f"\n[bold]{account.name}[/bold] ({account.currency.code})")
            table = Table("ID", "Name", "Target", "Current Amount", "Progress")
            
            # Get currency details for formatting
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
    account_service = AccountService(db)
    amount_decimal: Decimal = Decimal(amount)
    
    try:
        # Get account and pot details for proper formatting
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
    account_service = AccountService(db)
    amount_decimal: Decimal = Decimal(amount)
    
    try:
        # Get account details for proper formatting
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
def pot_transactions(
    pot_id: int = POT_ID,
    days: int = typer.Option(30, "--days", "-d", help="Number of days of history to show"),
):
    """Show transaction history for a specific pot"""
    db = next(get_db())
    service = TransactionService(db)
    account_service = AccountService(db)

    try:
        # Get pot and account details for proper formatting
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


FROM_POT = cast(int, typer.Option(..., "--from", "-f", help="Source pot ID"))
TO_POT = cast(int, typer.Option(..., "--to", "-t", help="Destination pot ID"))





SHOW_LEGS = cast(
    bool, typer.Option(False, "--legs", "-l", help="Show transaction legs")
)


@app.command()
def list_transactions(
    account_id: int | None = ACCOUNT_ID,
    days: int = typer.Option(30, "--days", "-d", help="Number of days of history to show"),
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
