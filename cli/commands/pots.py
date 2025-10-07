"""Savings pot-related CLI commands"""
import typer
from decimal import Decimal
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import cast
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import get_db
from modules.accounts.service import AccountService
from modules.transactions.service import TransactionService
from models.accounts import Pot

pots_app = typer.Typer()



class PotContext:
    def __init__(self, db_path: str):
        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)
        self.db = SessionLocal()
        self.console = Console()

@pots_app.callback()
def main(ctx: typer.Context, db_path: str = typer.Option("budget.db", help="Path to database file")):
    """Account CLI group callback to set up DB/session."""
    ctx.obj = PotContext(db_path)

@pots_app.command()
def list(
    ctx: typer.Context,     
    account_id: int = typer.Option(..., "--account", "-a", help="Account ID"),
    ):
    """List all pots and their balances"""
    context: PotContext = ctx.obj
    service = AccountService(context.db)
    pots = service.get_pots(account_id)
    if not pots:
        rprint(f"[yellow]No pots found for account ID {account_id}[/yellow]")
        return
    table = Table(title=f"Pots for Account ID {account_id}")
    table.add_column("Pot ID", justify="right")
    table.add_column("Name")
    table.add_column("Balance", justify="right")
    for pot in pots:
        table.add_row(str(pot.id), pot.name, f"{pot.current_amount:.2f}")
    context.console.print(table)

    
@pots_app.command()
def create(
    ctx: typer.Context,     
    account_id: int = typer.Option(..., "--account", "-a", help="Account ID"),
    name: str = typer.Option(..., "--name", "-n", help="Name of the pot"),
    initial_amount: str = typer.Option(0.0, "--amount", "-m", help="Initial amount to add to the pot"),
    ):
    """Create a new pot"""
    context: PotContext = ctx.obj
    service = AccountService(context.db)
    p = service.create_pot(account_id, name, Decimal(initial_amount))
    rprint(f"[green]Created pot '{p.name}' with ID {p.id} and initial amount {p.current_amount:.2f}[/green]")
    
