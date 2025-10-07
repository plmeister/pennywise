"""Main CLI entrypoint"""
import typer
from .commands import *


app = typer.Typer()
app.add_typer(accounts.account_app, name="account")
app.add_typer(currency.currency_app, name="currency")
app.add_typer(formats.formats_app, name="format")
app.add_typer(pots.pots_app, name="pot")
app.add_typer(transactions.transactions_app, name="tx")

def main():
    app()

if __name__ == "__main__":
    main()