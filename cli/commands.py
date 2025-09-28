import typer
from typing import Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rich.console import Console
from rich.table import Table
from rich import print as rprint

# Import local modules
from database import Base, SessionLocal
from modules.accounts.service import AccountService
from modules.transactions.service import TransactionService
from modules.categories.service import CategoryService
from models.accounts import AccountType, Currency

app = typer.Typer()
console = Console()

# Create database engine and session
DATABASE_URL = "sqlite:///./budget.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Account Commands
@app.command()
def create_account(
    name: str = typer.Option(..., "--name", "-n", help="Account name"),
    balance: Decimal = typer.Option(Decimal('0.00'), "--balance", "-b", help="Initial balance"),
    type: str = typer.Option("current", "--type", "-t", 
                            help=f"Account type ({', '.join(t.value for t in AccountType)})"),
    currency: str = typer.Option("GBP", "--currency", "-c",
                                help=f"Currency ({', '.join(c.value for c in Currency)})")
):
    """Create a new account"""
    db = next(get_db())
    service = AccountService(db)
    try:
        account = service.create_account(
            name=name,
            initial_balance=balance,
            account_type=type,
            currency=currency
        )
        curr_symbol = Currency(currency).symbol
        rprint(f"[green]Created account:[/green] {account.name} (ID: {account.id}) [{currency}]")
        if balance > Decimal('0.00'):
            rprint(f"Initial balance: {curr_symbol}{balance:.2f}")
    except Exception as e:
        rprint(f"[red]Error creating account:[/red] {str(e)}")

@app.command()
def list_accounts():
    """List all accounts and their balances"""
    db = next(get_db())
    service = AccountService(db)
    accounts = service.get_all()
    
    table = Table("ID", "Name", "Type", "Currency", "Balance", "Pot Balance", "Available")
    for account in accounts:
        pots_count = len(account.pots) if account.pots else 0
        pot_balance = sum(
            TransactionService(db).get_pot_balance(pot.id) for pot in account.pots
        ) if account.pots else Decimal('0.00')
        available = account.balance - pot_balance
        symbol = account.currency.symbol

        table.add_row(
            str(account.id),
            account.name,
            account.type,
            account.currency.value,
            f"{symbol}{account.balance:.2f}",
            f"{symbol}{pot_balance:.2f}",
            f"{symbol}{available:.2f}"
        )
    console.print(table)

@app.command()
def create_pot(
    account_id: int = typer.Option(..., "--account", "-a", help="Parent account ID"),
    name: str = typer.Option(..., "--name", "-n", help="Pot name"),
    target: Optional[Decimal] = typer.Option(None, "--target", "-t", help="Savings target")
):
    """Create a new savings pot within an account"""
    db = next(get_db())
    service = AccountService(db)
    try:
        pot = service.create_pot(account_id, name, target_amount=target if target is not None else Decimal('0.00'))
        rprint(f"[green]Created pot:[/green] {pot.name} in account {account_id}")
    except Exception as e:
        rprint(f"[red]Error creating pot:[/red] {str(e)}")

@app.command()
def transfer(
    from_id: int = typer.Option(..., "--from", "-f", help="Source account ID"),
    to_id: int = typer.Option(..., "--to", "-t", help="Destination account ID"),
    amount: Decimal = typer.Option(..., "--amount", "-a", help="Amount to transfer"),
    description: str = typer.Option(None, "--desc", "-d", help="Transfer description")
):
    """Transfer money between accounts"""
    db = next(get_db())
    service = AccountService(db)
    try:
        service.transfer(
            from_id=from_id,
            to_id=to_id,
            amount=amount,
            description=description
        )
        rprint(f"[green]Successfully transferred[/green] {amount:.2f}")
    except Exception as e:
        rprint(f"[red]Transfer failed:[/red] {str(e)}")

@app.command()
def list_pots(
    account_id: Optional[int] = typer.Option(None, "--account", "-a", help="Filter by account ID")
):
    """List all savings pots and their balances"""
    db = next(get_db())
    account_service = AccountService(db)
    transaction_service = TransactionService(db)
    
    accounts = [account_service.get(account_id)] if account_id else account_service.get_all()
    
    for account in accounts:
        if account.pots:
            console.print(f"\n[bold]{account.name}[/bold]")
            table = Table("ID", "Name", "Target", "Current Amount", "Progress")
            for pot in account.pots:
                balance = transaction_service.get_pot_balance(pot.id)
                progress = f"{(balance / Decimal(str(pot.target_amount)) * 100):.1f}%" if pot.target_amount else "N/A"
                table.add_row(
                    str(pot.id),
                    pot.name,
                    f"{Decimal(str(pot.target_amount)):.2f}" if pot.target_amount else "No target",
                    f"{balance:.2f}",
                    progress
                )
            console.print(table)

@app.command()
def pot_transfer(
    account_id: int = typer.Option(..., "--account", "-a", help="Account ID"),
    pot_id: int = typer.Option(..., "--pot", "-p", help="Pot ID"),
    amount: Decimal = typer.Option(..., "--amount", "-m", help="Amount to transfer"),
    direction: str = typer.Option(..., "--direction", "-d", help="'to_pot' or 'from_pot'"),
    description: Optional[str] = typer.Option(None, "--desc", help="Optional description")
):
    """Transfer money to/from a savings pot"""
    db = next(get_db())
    service = TransactionService(db)
    
    try:
        if direction == "to_pot":
            transaction = service.transfer_to_pot(
                account_id=account_id,
                pot_id=pot_id,
                amount=amount,
                description=description
            )
        elif direction == "from_pot":
            transaction = service.transfer_from_pot(
                account_id=account_id,
                pot_id=pot_id,
                amount=amount,
                description=description
            )
        else:
            raise ValueError("Direction must be either 'to_pot' or 'from_pot'")
            
        rprint(f"[green]Successfully transferred[/green] {amount:.2f} {direction.replace('_', ' ')}")
    except Exception as e:
        rprint(f"[red]Pot transfer failed:[/red] {str(e)}")

@app.command()
def pot_to_pot(
    account_id: int = typer.Option(..., "--account", "-a", help="Account ID"),
    from_pot: int = typer.Option(..., "--from", "-f", help="Source pot ID"),
    to_pot: int = typer.Option(..., "--to", "-t", help="Destination pot ID"),
    amount: Decimal = typer.Option(..., "--amount", "-m", help="Amount to transfer"),
    description: Optional[str] = typer.Option(None, "--desc", help="Optional description")
):
    """Transfer money between two pots in the same account"""
    db = next(get_db())
    service = TransactionService(db)
    
    try:
        transaction = service.transfer_between_pots(
            account_id=account_id,
            from_pot_id=from_pot,
            to_pot_id=to_pot,
            amount=amount,
            description=description
        )
        rprint(f"[green]Successfully transferred[/green] {amount:.2f} between pots")
    except Exception as e:
        rprint(f"[red]Pot transfer failed:[/red] {str(e)}")

@app.command()
def pot_transactions(
    pot_id: int = typer.Option(..., "--pot", "-p", help="Pot ID"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days of history to show")
):
    """Show transaction history for a specific pot"""
    db = next(get_db())
    service = TransactionService(db)
    account_service = AccountService(db)
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    transactions = service.get_pot_transactions(pot_id, start_date, end_date)
    
    if not transactions:
        rprint("[yellow]No transactions found for this pot in the specified time period[/yellow]")
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
                    "IN" if amount > Decimal('0.00') else "OUT"
                )
    console.print(table)

@app.command()
def list_transactions(
    account_id: Optional[int] = typer.Option(None, "--account", "-a", help="Filter by account ID"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days of history to show"),
    show_legs: bool = typer.Option(False, "--legs", "-l", help="Show transaction legs")
):
    """List recent transactions"""
    db = next(get_db())
    service = TransactionService(db)
    account_service = AccountService(db)
    
    end_date = datetime.now().date()
    start_date = end_date + timedelta(days=days)
    
    if account_id:
        transactions = service.get_account_transactions(account_id, start_date, end_date)
    else:
        transactions = service.get_all()
    
    if show_legs:
        # Show detailed view with all transaction legs
        for tx in transactions:
            console.print(f"\n[bold]{tx.date.strftime('%Y-%m-%d')} - {tx.description or 'No description'}[/bold]")
            legs_table = Table("Account", "Debit", "Credit")
            
            for leg in service.get_transaction_legs(tx.id):
                account = account_service.get(leg.account_id)
                legs_table.add_row(
                    account.name,
                    f"{Decimal(str(leg.debit)):.2f}" if leg.debit else "",
                    f"{Decimal(str(leg.credit)):.2f}" if leg.credit else ""
                )
            console.print(legs_table)
    else:
        # Show simplified view
        table = Table("Date", "Description", "Net Amount", "Accounts Involved")
        for tx in transactions:
            legs = service.get_transaction_legs(tx.id)
            
            # Calculate net amount from leg with most credit
            net_amount = max((Decimal(str(leg.credit or 0))) for leg in legs)
            if net_amount == Decimal('0.00'):
                net_amount = max((Decimal(str(leg.debit or 0))) for leg in legs)
                
            # Get account names
            account_names = []
            for leg in legs:
                account = account_service.get(leg.account_id)
                account_names.append(account.name)
                
            table.add_row(
                tx.date.strftime("%Y-%m-%d"),
                tx.description or "",
                f"{net_amount:.2f}",
                ", ".join(account_names)
            )
        console.print(table)

def main():
    app()

if __name__ == "__main__":
    main()