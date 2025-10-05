"""Main CLI entrypoint"""
import typer
from . import commands

app = typer.Typer()

# Add sub-commands
app.add_typer(commands.accounts.app, name="account")
app.add_typer(commands.currency.app, name="currency")
app.add_typer(commands.pots.app, name="pot")
app.add_typer(commands.transactions.app, name="tx")

def main():
    app()

if __name__ == "__main__":
    main()