from modules.common.base_service import BaseService
from models.accounts import Account, Pot, AccountType, Currency
from models.transactions import Transaction
from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import date
from modules.transactions.service import TransactionService


class AccountService(BaseService[Account]):
    transaction_service: TransactionService

    def __init__(self, db: Session):
        super().__init__(Account, db)
        self.transaction_service = TransactionService(db)

    def create_account(
        self,
        name: str,
        account_type: str = "current",
        currency: str = "GBP",
    ) -> Account:
        # Create the account with zero balance
        account = Account(
            **{
                "name": name,
                "type": AccountType(account_type),
                "currency": Currency(currency),
                "balance": 0,
            }
        )

        return account

    def get_balance(self, account_id: int, as_of_date: date | None = None) -> Decimal:
        """Get the current balance for an account based on all transaction legs"""
        account = self.get(account_id)
        if not account:
            raise ValueError("Account not found")
        return self.transaction_service.get_account_balance(account_id, as_of_date)

    def transfer(
        self, from_id: int, to_id: int, amount: Decimal, description: str | None = None
    ) -> Transaction:
        """Transfer money between accounts"""
        # Verify accounts exist
        from_account = self.get(from_id)
        to_account = self.get(to_id)
        if not from_account or not to_account:
            raise ValueError("One or both accounts not found")

        # Check sufficient funds
        # if self.get_balance(from_id) < amount:
        #     raise ValueError("Insufficient funds")

        # Create the transfer transaction
        return self.transaction_service.create_transfer(
            from_account_id=from_id,
            to_account_id=to_id,
            amount=amount,
            description=description,
        )

    DEFAULT_POT_TARGET: Decimal = Decimal(0.0)
    DEFAULT_POT_AMOUNT: Decimal = Decimal(0.0)

    def create_pot(
        self,
        account_id: int,
        name: str,
        target_amount: Decimal = DEFAULT_POT_TARGET,
        initial_amount: Decimal = DEFAULT_POT_AMOUNT,
    ) -> Pot:
        """
        Create a new savings pot for an account.

        Args:
            account_id: The ID of the account to create the pot for
            name: Name of the pot
            target_amount: Optional target amount for the pot
            initial_amount: Optional initial amount to allocate to the pot. If provided,
                          will create a transfer from the parent account to this pot.

        Returns:
            The created Pot object

        Raises:
            ValueError: If account doesn't exist or has insufficient funds for initial amount
        """
        # Verify account exists
        account = self.get(account_id)
        if not account:
            raise ValueError("Account not found")

        # Check sufficient funds if initial amount provided
        if initial_amount > 0:
            current_balance = self.get_balance(account_id)
            if current_balance < initial_amount:
                raise ValueError("Insufficient funds in account for initial pot amount")

        # Create the pot
        pot = Pot(
            name=name,
            target_amount=target_amount,
            current_amount=0,  # Start at 0, will be updated by transfer
            account_id=account_id,
        )

        self.db.add(pot)
        self.db.commit()
        self.db.refresh(pot)

        # If initial amount provided, create a transfer transaction
        if initial_amount > 0:
            _ = self.transaction_service.create_multi_leg_transaction(
                legs=[
                    {"account_id": account_id, "debit": initial_amount},
                    {
                        "account_id": account_id,
                        "pot_id": pot.id,
                        "credit": initial_amount,
                    },
                ],
                description=f"Initial funding for pot: {name}",
            )

            # Update pot amount after transfer
            pot.current_amount = initial_amount
            self.db.commit()
            self.db.refresh(pot)

        return pot
