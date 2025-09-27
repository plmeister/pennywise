from modules.common.base_service import BaseService
from .models import Account, Transaction
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from datetime import datetime

class AccountService(BaseService[Account]):
    def __init__(self, db: Session):
        super().__init__(Account, db)

    def create_account(self, name: str, initial_balance: Decimal = Decimal('0.00'), 
                      account_type: str = "current") -> Account:
        return self.create({
            "name": name,
            "balance": float(initial_balance),
            "account_type": account_type
        })

    def transfer(self, from_id: int, to_id: int, amount: Decimal, description: str = None) -> bool:
        from_account = self.get(from_id)
        to_account = self.get(to_id)

        if not from_account or not to_account:
            raise ValueError("One or both accounts not found")

        if from_account.balance < float(amount):
            raise ValueError("Insufficient funds")

        try:
            # Create transfer transaction
            transfer = Transaction(
                from_account_id=from_id,
                to_account_id=to_id,
                amount=float(amount),
                description=description or f"Transfer from {from_account.name} to {to_account.name}",
                date=datetime.utcnow()
            )
            
            # Update balances
            from_account.balance -= float(amount)
            to_account.balance += float(amount)
            
            self.db.add(transfer)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"Transfer failed: {str(e)}")

    def get_balance(self, account_id: int) -> Decimal:
        account = self.get(account_id)
        if not account:
            raise ValueError("Account not found")
        return Decimal(str(account.balance))

    def get_transactions(self, account_id: int, 
                        start_date: datetime = None, 
                        end_date: datetime = None) -> List[Transaction]:
        query = self.db.query(Transaction).filter(
            (Transaction.from_account_id == account_id) |
            (Transaction.to_account_id == account_id)
        )
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
            
        return query.order_by(Transaction.date.desc()).all()