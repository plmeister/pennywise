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
