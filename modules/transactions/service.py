from modules.common.base_service import BaseService
from models.transactions import Transaction, TransactionLeg
from models.accounts import Account, Pot
from sqlalchemy.orm import Session
from typing import cast, TypedDict, NotRequired
from decimal import Decimal
from datetime import datetime, date, timezone


class DebitLeg(TypedDict):
    account_id: int
    pot_id: NotRequired[int | None]
    debit: Decimal


class CreditLeg(TypedDict):
    account_id: int
    pot_id: NotRequired[int | None]
    credit: Decimal


TransactionLegDict = CreditLeg | DebitLeg


class TransactionService(BaseService[Transaction]):
    def __init__(self, db: Session):
        super().__init__(Transaction, db)

    def create_transfer(
        self,
        from_account_id: int,
        to_account_id: int,
        amount: Decimal,
        description: str | None = None,
        transaction_date: date | None = None,
    ) -> Transaction:
        """Create a transfer between two accounts using double-entry accounting"""

        # Get accounts to update balances
        from_account = cast(Account, self.db.query(Account).get(from_account_id))
        to_account = cast(Account, self.db.query(Account).get(to_account_id))
        if not from_account or not to_account:
            raise ValueError("One or both accounts not found")

        # Create the main transaction
        transaction = Transaction(
            description=description
            or f"Transfer from {from_account.name} to {to_account.name}",
            date=transaction_date or datetime.now(timezone.utc).date(),
        )
        self.db.add(transaction)
        self.db.flush()  # Get the transaction ID

        # Create the debit leg (money leaving the source account)
        debit_leg = TransactionLeg(
            transaction_id=transaction.id,
            account_id=from_account_id,
            debit=amount,
            credit=None,
        )

        # Create the credit leg (money entering the destination account)
        credit_leg = TransactionLeg(
            transaction_id=transaction.id,
            account_id=to_account_id,
            debit=None,
            credit=amount,
        )

        # Update account balances
        from_account.balance = from_account.balance - amount
        to_account.balance = to_account.balance + amount

        self.db.add_all([debit_leg, credit_leg])
        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def create_multi_leg_transaction(
        self,
        legs: list[TransactionLegDict],
        description: str,
        transaction_date: date | None = None,
    ) -> Transaction:
        """
        Create a transaction with multiple legs.
        Each leg should be a dict with:
        - account_id: int
        - debit: Decimal (optional)
        - credit: Decimal (optional)
        """
        # Validate that debits and credits balance
        total_debits = sum((leg.get("debit", 0) or 0) for leg in legs)
        total_credits = sum((leg.get("credit", 0) or 0) for leg in legs)

        if abs(total_debits - total_credits) > 0:
            raise ValueError(
                "Transaction legs must balance - total debits must equal total credits"
            )

        # Create the main transaction
        transaction = Transaction(
            description=description,
            date=transaction_date or datetime.now(timezone.utc).date(),
        )
        self.db.add(transaction)
        self.db.flush()

        # Create all legs
        transaction_legs: list[TransactionLeg] = []
        for leg in legs:
            transaction_legs.append(
                TransactionLeg(
                    transaction_id=transaction.id,
                    account_id=leg["account_id"],
                    pot_id=leg.get("pot_id"),
                    debit=leg.get("debit"),
                    credit=leg.get("credit"),
                )
            )

        self.db.add_all(transaction_legs)
        self.db.commit()
        self.db.refresh(transaction)

        return transaction

    def get_account_transactions(
        self,
        account_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Transaction]:
        """Get all transactions involving a specific account"""
        query = (
            self.db.query(Transaction)
            .join(TransactionLeg)
            .filter(TransactionLeg.account_id == account_id)
        )

        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        return query.order_by(Transaction.date.desc()).all()

    def get_transaction_legs(self, transaction_id: int) -> list[TransactionLeg]:
        """Get all legs for a specific transaction"""
        return (
            self.db.query(TransactionLeg)
            .filter(TransactionLeg.transaction_id == transaction_id)
            .all()
        )

    def get_account_balance(
        self, account_id: int, as_of_date: date | None = None
    ) -> Decimal:
        """Calculate account balance based on all transaction legs"""
        query = (
            self.db.query(TransactionLeg)
            .join(Transaction)
            .filter(TransactionLeg.account_id == account_id)
        )

        if as_of_date:
            query = query.filter(Transaction.date <= as_of_date)

        legs = query.all()

        balance = Decimal("0.00")
        for leg in legs:
            if leg.credit:
                balance += Decimal(str(leg.credit))
            if leg.debit:
                balance -= Decimal(str(leg.debit))

        return balance

    def _validate_pot_ownership(self, pot_id: int, account_id: int) -> None:
        """
        Validate that a pot belongs to the specified account.
        Raises ValueError if validation fails.
        """
        pot = self.db.query(Pot).get(pot_id)
        if not pot:
            raise ValueError(f"Pot {pot_id} not found")
        if pot.account_id != account_id:
            raise ValueError(f"Pot {pot_id} does not belong to account {account_id}")

    def get_pot_balance(self, pot_id: int, as_of_date: date | None = None) -> Decimal:
        """
        Calculate pot balance based on all transaction legs involving this pot.
        """
        query = (
            self.db.query(TransactionLeg)
            .join(Transaction)
            .filter(TransactionLeg.pot_id == pot_id)
        )

        if as_of_date:
            query = query.filter(Transaction.date <= as_of_date)

        legs = query.all()

        balance = Decimal("0.00")
        for leg in legs:
            if leg.credit:
                balance += Decimal(str(leg.credit))
            if leg.debit:
                balance -= Decimal(str(leg.debit))

        return balance

    def transfer_to_pot(
        self,
        account_id: int,
        pot_id: int,
        amount: Decimal,
        description: str | None = None,
        transaction_date: date | None = None,
    ) -> Transaction:
        """
        Transfer money from an account to one of its pots.
        """
        # Validate pot belongs to account
        self._validate_pot_ownership(pot_id, account_id)

        # Validate sufficient funds
        if self.get_account_balance(account_id) < amount:
            raise ValueError("Insufficient funds in account")

        # Create the transfer transaction
        return self.create_multi_leg_transaction(
            legs=[
                {"account_id": account_id, "debit": amount},
                {"account_id": account_id, "pot_id": pot_id, "credit": amount},
            ],
            description=description or "Transfer to pot",
            transaction_date=transaction_date,
        )

    def transfer_from_pot(
        self,
        account_id: int,
        pot_id: int,
        amount: Decimal,
        description: str | None = None,
        transaction_date: date | None = None,
    ) -> Transaction:
        """
        Transfer money from a pot back to its parent account.
        """
        # Validate pot belongs to account
        self._validate_pot_ownership(pot_id, account_id)

        # Validate sufficient funds in pot
        if self.get_pot_balance(pot_id) < amount:
            raise ValueError("Insufficient funds in pot")

        # Create the transfer transaction
        return self.create_multi_leg_transaction(
            legs=[
                {"account_id": account_id, "pot_id": pot_id, "debit": amount},
                {"account_id": account_id, "credit": amount},
            ],
            description=description or "Transfer from pot",
            transaction_date=transaction_date,
        )

    def transfer_between_pots(
        self,
        account_id: int,
        from_pot_id: int,
        to_pot_id: int,
        amount: Decimal,
        description: str | None = None,
        transaction_date: date | None = None,
    ) -> Transaction:
        """
        Transfer money between two pots of the same account.
        """
        # Validate both pots belong to account
        self._validate_pot_ownership(from_pot_id, account_id)
        self._validate_pot_ownership(to_pot_id, account_id)

        # Validate sufficient funds in source pot
        if self.get_pot_balance(from_pot_id) < amount:
            raise ValueError("Insufficient funds in source pot")

        # Create the transfer transaction
        return self.create_multi_leg_transaction(
            legs=[
                {"account_id": account_id, "pot_id": from_pot_id, "debit": amount},
                {"account_id": account_id, "pot_id": to_pot_id, "credit": amount},
            ],
            description=description or "Transfer between pots",
            transaction_date=transaction_date,
        )

    def get_pot_transactions(
        self,
        pot_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Transaction]:
        """Get all transactions involving a specific pot"""
        query = (
            self.db.query(Transaction)
            .join(TransactionLeg)
            .filter(TransactionLeg.pot_id == pot_id)
        )

        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)

        return query.order_by(Transaction.date.desc()).all()
