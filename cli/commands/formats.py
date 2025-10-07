"""CLI commands for managing import formats"""
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from modules.imports.formats import ImportFormatService
from modules.accounts.service import AccountService
from schemas.import_formats import ImportFormat

formats_app = typer.Typer()


class FormatContext:
    def __init__(self, db_path: str):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine(f"sqlite:///{db_path}")
        SessionLocal = sessionmaker(bind=engine)
        self.db = SessionLocal()
        self.console = Console()

@formats_app.callback()
def main(ctx: typer.Context, db_path: str = typer.Option("budget.db", help="Path to database file")):
    """Formats CLI group callback to set up DB/session."""
    ctx.obj = FormatContext(db_path)

def get_session() -> Session:
    """Get database session"""
    return next(get_db())

@formats_app.command()
def list(ctx: typer.Context):
    """List all import formats"""
    context: FormatContext = ctx.obj
    service = ImportFormatService(context.db)
    formats = service.list_formats()
    table = Table("ID", "Name", "Date Col", "Amount Col", "Desc Col", "Account")
    for fmt in formats:
        table.add_row(
            str(fmt.id),
            str(fmt.name),
            str(fmt.date_column),
            str(fmt.amount_column),
            str(fmt.description_column),
            str(fmt.account.name) if getattr(fmt, "account", None) else ""
        )
    context.console.print(table)

@formats_app.command()
def add(
    ctx: typer.Context,
    name: str = typer.Option(..., "--name", "-n", help="Format name"),
    columns: str = typer.Option(..., "--columns", "-c", help="Comma-separated columns")
):
    """Add a new import format"""
    context: FormatContext = ctx.obj
    service = ImportFormatService(context.db)
    try:
        col_list = columns.split(",")
        fmt = service.create({
            "name": name,
            "date_column": col_list[0] if len(col_list) > 0 else "",
            "amount_column": col_list[1] if len(col_list) > 1 else "",
            "description_column": col_list[2] if len(col_list) > 2 else ""
        })
        rprint(f"[green]Added format:[/green] {fmt.name}")
    except Exception as e:
        rprint(f"[red]Error adding format:[/red] {str(e)}")

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
