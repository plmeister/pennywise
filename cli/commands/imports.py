"""Command line interface for importing bank statements"""
from pathlib import Path
import logging
import sys
import json
import typer
from typing import Optional
from sqlalchemy.orm import Session
from rich import print
from rich.prompt import Prompt

from modules.imports.service import ImportService
from database import Base, get_db
from models.transactions import Transaction
from schemas.import_formats import ImportFormat

logger = logging.getLogger(__name__)
app = typer.Typer(help="Import bank statements")

def get_session() -> Session:
    """Get database session"""
    return next(get_db())

@app.command("format")
def create_format(
    name: str = typer.Option(..., "--name", "-n", help="Name for this import format"),
    db_save: bool = typer.Option(True, "--db-save/--no-db-save", help="Save format to database"),
    file_save: bool = typer.Option(True, "--file-save/--no-file-save", help="Save format to file"),
):
    """Create a new import format interactively"""
    fmt = ImportFormat(
        name=name,
        date_column=Prompt.ask("Date column name"),
        amount_column=Prompt.ask("Amount column name"),
        description_column=Prompt.ask("Description column name"),
        type_column=Prompt.ask("Type column name (optional)", default="") or None,
        balance_column=Prompt.ask("Balance column name (optional)", default="") or None,
        reference_column=Prompt.ask("Reference column name (optional)", default="") or None,
        date_format=Prompt.ask("Date format (e.g., %d/%m/%Y)", default="%Y-%m-%d"),
        thousands_separator=Prompt.ask("Thousands separator", default=","),
        decimal_separator=Prompt.ask("Decimal separator", default="."),
        encoding=Prompt.ask("File encoding", default="utf-8-sig"),
        notes=Prompt.ask("Notes about this format", default="") or None
    )
    
    print("\nFormat created:")
    print(fmt.model_dump_json(indent=2))
    
    if db_save:
        session = get_session()
        from modules.imports.formats import ImportFormatService
        service = ImportFormatService(session)
        try:
            service.create(fmt)
            print("\nSaved format to database")
        except Exception as e:
            print(f"\n[red]Error saving to database: {e}[/red]")
            db_save = False
    
    if file_save:
        # Save to formats directory
        formats_dir = Path("import_formats")
        formats_dir.mkdir(exist_ok=True)
        
        format_file = formats_dir / f"{fmt.name.lower().replace(' ', '_')}.json"
        format_file.write_text(fmt.model_dump_json(indent=2))
        print(f"\nSaved to {format_file}")
        
    return fmt

@app.command("import")
def import_statement(
    file_path: Path = typer.Argument(..., help="Path to bank statement file", 
                                   exists=True, file_okay=True, dir_okay=False),
    account_id: str = typer.Option(..., "--account", "-a", help="ID of the account to import into"),
    format_name: Optional[str] = typer.Option(None, "--format", "-f", 
                                            help="Name of format to use (from database)"),
    format_id: Optional[int] = typer.Option(None, "--format-id",
                                          help="ID of format to use (from database)"),
    format_file: Optional[Path] = typer.Option(None, "--format-file",
                                             help="Path to format JSON file")
):
    """Import transactions from a bank statement"""
    try:
        session = get_session()
        service = ImportService(model=Transaction, db=session)
        
        # Get format definition
        fmt = None
        if format_file:
            fmt = ImportFormat.model_validate_json(format_file.read_text())
        elif format_name:
            fmt = format_name  # Service will look up by name
        elif format_id:
            fmt = format_id  # Service will look up by ID
            
        statement = service.import_file(file_path, fmt=fmt, account_id=int(account_id))
        
        # Print summary
        print(f"Successfully imported {len(statement.transactions)} transactions")
        print(f"Date range: {statement.start_date.date()} to {statement.end_date.date()}")
        if statement.end_balance:
            print(f"Final balance: {statement.end_balance}")
            
    except Exception as e:
        print(f"[red]Error importing file: {str(e)}[/red]")
        raise typer.Exit(1)