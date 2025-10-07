"""Main CLI entrypoint"""
import typer
from . import commands


app = typer.Typer()
app.add_typer(commands.accounts.account_app, name="account")
app.add_typer(commands.currency.currency_app, name="currency")
app.add_typer(commands.formats.formats_app, name="format")
app.add_typer(commands.pots.pots_app, name="pot")
app.add_typer(commands.transactions.transactions_app, name="tx")

def main():
    app()

if __name__ == "__main__":
    main()