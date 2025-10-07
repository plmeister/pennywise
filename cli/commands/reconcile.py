"""Command line interface for reconciling transactions"""
from datetime import datetime, date
import logging
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

from modules.imports.matching import TransactionMatcher
from models.transactions import Transaction
from database import get_db

logger = logging.getLogger(__name__)
app = typer.Typer(help="Reconcile transactions")
console = Console()

@app.command("match")
def match_transfers(
    from_date: datetime = typer.Option(None, "--from", "-f", help="Start date for matching"),
    to_date: datetime = typer.Option(None, "--to", "-t", help="End date for matching"),
    max_days: int = typer.Option(3, "--days", "-d", help="Maximum days between matching transactions"),
):
    """Find potential transfer matches between accounts"""
    try:
        db = next(get_db())
        matcher = TransactionMatcher()
        
        # Get transactions
        query = db.query(Transaction)
        if from_date:
            query = query.filter(Transaction.date >= from_date)
        if to_date:
            query = query.filter(Transaction.date <= to_date)
            
        transactions = query.all()
        
        if not transactions:
            console.print("No transactions found in date range")
            return
            
        # Find potential matches
        matches = matcher.find_transfer_matches(
            transactions,
            max_days_apart=max_days
        )
        
        if not matches:
            console.print("No potential transfer matches found")
            return
            
        # Display matches and prompt for confirmation
        for match in matches:
            # Create table for the match
            title = f"Potential {'Pot' if match.transfer_type == 'pot_transfer' else 'Account'} Transfer"
            table = Table(title=f"{title} ({match.days_apart} days apart)")
            
            table.add_column("Direction")
            table.add_column("Date")
            table.add_column("Amount")
            table.add_column("Type", style="cyan")
            table.add_column("Description")
            table.add_column("Account")
            
            # Get transaction types if available
            source_type = getattr(match.source_transaction, 'type', '')
            dest_type = getattr(match.dest_transaction, 'type', '')
            
            # Add source transaction
            table.add_row(
                "FROM",
                match.source_transaction.date.strftime("%Y-%m-%d"),
                f"{getattr(match.source_transaction, 'amount', 0)}",
                str(source_type),
                str(getattr(match.source_transaction, 'description', '')),
                f"Account {getattr(match.source_transaction, 'account_id', '?')}"
            )
            
            # Add destination transaction
            table.add_row(
                "TO",
                match.dest_transaction.date.strftime("%Y-%m-%d"),
                f"{getattr(match.dest_transaction, 'amount', 0)}",
                str(dest_type),
                str(getattr(match.dest_transaction, 'description', '')),
                f"Account {getattr(match.dest_transaction, 'account_id', '?')}"
            )
            
            console.print(table)
            
            action = "link" if match.transfer_type == "pot_transfer" else "mark as matching transfer"
            if Confirm.ask(f"{title}: {action}?"):
                # In this simple version, we just acknowledge the match
                # You can add transaction linking/status updates later if needed
                console.print("[green]Match confirmed[/green]")
            else:
                console.print("[yellow]Match skipped[/yellow]")
                
    except Exception as e:
        logger.error(f"Error during matching: {str(e)}")
        raise typer.Exit(1)