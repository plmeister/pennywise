from modules.common.base_service import BaseService
from models.transactions import Transaction, TransactionLeg
from models.accounts import Account, Pot
from modules.currencies.service import CurrencyService
from sqlalchemy.orm import Session
from typing import cast, TypedDict, NotRequired, Optional
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
        self.currency_service = CurrencyService(db)

    def _convert_amount(self, 
                       amount: Decimal,
                       from_account: Account,
                       to_account: Account,
                       transaction_date: Optional[date] = None) -> tuple[Decimal, Decimal]:
        """
        Convert amount between account currencies if needed.
        Returns tuple of (from_amount, to_amount)
        """
        if from_account.currency_id == to_account.currency_id:
            return amount, amount
            
        # Convert amount using latest exchange rate
        datetime_for_rate = datetime.combine(
            transaction_date or datetime.now(timezone.utc).date(),
            datetime.min.time()
        )
        
        converted_amount = self.currency_service.convert_amount(
            amount=amount,
            from_currency_code=from_account.currency.code,
            to_currency_code=to_account.currency.code,
            at_time=datetime_for_rate
        )
        
        if converted_amount is None:
            raise ValueError(
                f"No exchange rate found from {from_account.currency.code} "
                f"to {to_account.currency.code}"
            )
            
        return amount, converted_amount

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
            
        tx_date = transaction_date or datetime.now(timezone.utc).date()

        # Convert amount if currencies differ
        from_amount, to_amount = self._convert_amount(
            amount=amount,
            from_account=from_account,
            to_account=to_account,
            transaction_date=tx_date
        )

        # Create the main transaction
        transaction = Transaction(
            description=description or 
                       f"Transfer {from_account.currency.symbol}{from_amount:.{from_account.currency.decimals}f} "
                       f"from {from_account.name} to {to_account.name} "
                       f"({to_account.currency.symbol}{to_amount:.{to_account.currency.decimals}f})",
            date=tx_date,
            currency_id=from_account.currency_id  # Use source account's currency for the transaction
        )
        self.db.add(transaction)
        self.db.flush()  # Get the transaction ID

        # Create the debit leg (money leaving the source account)
        debit_leg = TransactionLeg(
            transaction_id=transaction.id,
            account_id=from_account_id,
            debit=from_amount,
            credit=None,
            currency_id=from_account.currency_id,
            exchange_rate=Decimal('1.0')  # Since this is in the transaction's base currency
        )

        # Create the credit leg (money entering the destination account)
        credit_leg = TransactionLeg(
            transaction_id=transaction.id,
            account_id=to_account_id,
            debit=None,
            credit=to_amount,
            currency_id=to_account.currency_id,
            exchange_rate=(to_amount / from_amount) if from_amount != to_amount else Decimal('1.0')
        )

        # Update account balances
        from_account.balance = from_account.balance - from_amount
        to_account.balance = to_account.balance + to_amount

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

        # Get the first account to use its currency as the base currency for the transaction
        first_account = cast(Account, self.db.query(Account).get(legs[0]["account_id"]))
        if not first_account:
            raise ValueError("First account not found")

        # Create the main transaction using the first account's currency as base
        transaction = Transaction(
            description=description,
            date=transaction_date or datetime.now(timezone.utc).date(),
            currency_id=first_account.currency_id
        )
        self.db.add(transaction)
        self.db.flush()

        # Create all legs
        transaction_legs: list[TransactionLeg] = []
        for leg in legs:
            account = cast(Account, self.db.query(Account).get(leg["account_id"]))
            if not account:
                raise ValueError(f"Account {leg['account_id']} not found")

            # Calculate exchange rate if currencies differ
            exchange_rate = Decimal('1.0')
            if account.currency_id != first_account.currency_id:
                # Get the exchange rate for the transaction date
                datetime_for_rate = datetime.combine(
                    transaction_date or datetime.now(timezone.utc).date(),
                    datetime.min.time()
                )
                
                converted_amount = self.currency_service.get_exchange_rate(
                    from_currency_code=first_account.currency.code,
                    to_currency_code=account.currency.code,
                    at_time=datetime_for_rate
                )
                if converted_amount is None:
                    raise ValueError(
                        f"No exchange rate found from {first_account.currency.code} "
                        f"to {account.currency.code}"
                    )
                exchange_rate = converted_amount

            transaction_legs.append(
                TransactionLeg(
                    transaction_id=transaction.id,
                    account_id=leg["account_id"],
                    pot_id=leg.get("pot_id"),
                    debit=leg.get("debit"),
                    credit=leg.get("credit"),
                    currency_id=account.currency_id,
                    exchange_rate=exchange_rate
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
