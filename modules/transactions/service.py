from modules.common.base_service import BaseService
from models.transactions import Transaction
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from datetime import datetime

class TransactionService(BaseService[Transaction]):
    def __init__(self, db: Session):
        super().__init__(Transaction, db)

    def create_transaction(self, 
                         amount: Decimal,
                         description: str,
                         from_account_id: int = None,
                         to_account_id: int = None,
                         category_id: int = None,
                         date: datetime = None) -> Transaction:
        transaction_data = {
            "amount": float(amount),
            "description": description,
            "from_account_id": from_account_id,
            "to_account_id": to_account_id,
            "category_id": category_id,
            "date": date or datetime.utcnow()
        }
        return self.create(transaction_data)

    def get_account_transactions(self, 
                               account_id: int,
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

    def get_category_transactions(self,
                                category_id: int,
                                start_date: datetime = None,
                                end_date: datetime = None) -> List[Transaction]:
        query = self.db.query(Transaction).filter(Transaction.category_id == category_id)
        
        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
            
        return query.order_by(Transaction.date.desc()).all()