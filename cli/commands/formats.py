"""CLI commands for managing import formats"""
from pathlib import Path
import typer
from tabulate import tabulate
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from modules.imports.formats import ImportFormatService
from modules.accounts.service import AccountService
from schemas.import_formats import ImportFormat

app = typer.Typer()

def get_session() -> Session:
    """Get database session"""
    return next(get_db())

@app.command()
def list_formats():
    """List available import formats"""
    db = get_session()
    service = ImportFormatService(db)
    formats = service.list_formats()
    
    rows = []
    for fmt in formats:
        rows.append([
            fmt.id,
            fmt.name,
            fmt.date_column,
            fmt.amount_column,
            fmt.description_column,
            fmt.account.name if fmt.account else None
        ])
        
    if rows:
        print(tabulate(rows, headers=[
            "ID",
            "Name",
            "Date Column",
            "Amount Column",
            "Description Column",
            "Default Account"
        ]))
    else:
        print("No import formats found")

@app.command()
def create_format(
    name: str = typer.Argument(..., help="Name of the format"),
    date_column: str = typer.Option(..., help="Name of the date column"),
    amount_column: str = typer.Option(..., help="Name of the amount column"),
    description_column: str = typer.Option(..., help="Name of the description column"),
    type_column: Optional[str] = typer.Option(None, help="Name of the transaction type column"),
    balance_column: Optional[str] = typer.Option(None, help="Name of the balance column"),
    reference_column: Optional[str] = typer.Option(None, help="Name of the reference column"),
    date_format: str = typer.Option(..., help="Format string for parsing dates"),
    thousands_separator: str = typer.Option(",", help="Character used as thousands separator"),
    decimal_separator: str = typer.Option(".", help="Character used as decimal separator"),
    encoding: str = typer.Option("utf-8", help="File encoding"),
    notes: Optional[str] = typer.Option(None, help="Additional notes about the format")
):
    """Create a new import format"""
    db = get_session()
    service = ImportFormatService(db)
    # Check if format already exists
    if service.get_by_name(name):
        typer.echo(f"Error: Format with name '{name}' already exists")
        raise typer.Exit(1)
    fmt = ImportFormat(
        name=name,
        date_column=date_column,
        amount_column=amount_column,
        description_column=description_column,
        type_column=type_column,
        balance_column=balance_column,
        reference_column=reference_column,
        date_format=date_format,
        thousands_separator=thousands_separator,
        decimal_separator=decimal_separator,
        encoding=encoding,
        notes=notes
    )
    service.create(fmt)
    typer.echo(f"Created import format '{name}'")

@app.command()
def set_account_format(
    format_id: int = typer.Argument(..., help="ID of the format"),
    account_name: str = typer.Argument(..., help="Name of the account")
):
    """Set default format for an account"""
    db = get_session()
    format_service = ImportFormatService(db)
    account_service = AccountService(db)
    fmt = format_service.get(format_id)
    if not fmt:
        typer.echo(f"Error: Import format {format_id} not found")
        raise typer.Exit(1)
    account = account_service.get_by_name(account_name)
    if not account:
        typer.echo(f"Error: Account '{account_name}' not found")
        raise typer.Exit(1)
    format_service.set_account_format(account.id, format_id)
    typer.echo(f"Set import format '{fmt.name}' as default for account '{account_name}'")

@app.command()
def export_format(
    format_id: int = typer.Argument(..., help="ID of the format"),
    output_file: Path = typer.Argument(..., help="Output JSON file path")
):
    """Export import format to JSON file"""
    db = get_session()
    service = ImportFormatService(db)
    fmt = service.get(format_id)
    if not fmt:
        typer.echo(f"Error: Import format {format_id} not found")
        raise typer.Exit(1)
    service.export_json(format_id, output_file)
    typer.echo(f"Exported format '{fmt.name}' to {output_file}")

@app.command()
def import_format(
    input_file: Path = typer.Argument(..., help="Input JSON file path", exists=True)
):
    """Import format from JSON file"""
    db = get_session()
    service = ImportFormatService(db)
    try:
        fmt = service.import_json(input_file)
        typer.echo(f"Imported format '{fmt.name}'")
    except Exception as e:
        typer.echo(f"Error importing format: {e}")
        raise typer.Exit(1)