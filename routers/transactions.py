from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
from decimal import Decimal

from database import get_db
from modules.transactions.service import TransactionService
from modules.accounts.service import AccountService
from schemas.transactions import ExternalPaymentIn, PotTransferIn, TransferIn, TransactionResponse

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/transfer", status_code=201)
def transfer_funds(data: TransferIn, db: Session = Depends(get_db)):
    service = TransactionService(db)
    account_service = AccountService(db)
    
    try:
        # Verify accounts exist
        from_acc = account_service.get(data.from_account_id)
        to_acc = account_service.get(data.to_account_id)
        if not from_acc or not to_acc:
            raise HTTPException(status_code=404, detail="Account not found")
        if from_acc.id == to_acc.id:
            raise HTTPException(status_code=400, detail="From and To accounts cannot be the same")
        
        transaction = service.create_transfer(
            from_account_id=data.from_account_id,
            to_account_id=data.to_account_id,
            amount=data.amount,
            description=data.description
        )
        
        return {"message": "Transfer completed", "transaction_id": transaction.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/pot-transfer", status_code=201)
def pot_transfer(data: PotTransferIn, db: Session = Depends(get_db)):
    service = TransactionService(db)
    account_service = AccountService(db)
    
    try:
        # Verify account and pot
        account = account_service.get(data.account_id)
        pot = account_service.get_pot(data.pot_id)
        
        if not account or not pot:
            raise HTTPException(status_code=404, detail="Account or pot not found")
        if pot.account_id != account.id:
            raise HTTPException(status_code=400, detail="Pot does not belong to specified account")

        amount = data.amount

        # Handle direction
        if data.direction == "to_pot":
            transaction = service.transfer_to_pot(
                account_id=data.account_id,
                pot_id=data.pot_id,
                amount=amount,
                description=None
            )
        else:
            transaction = service.transfer_from_pot(
                account_id=data.account_id,
                pot_id=data.pot_id,
                amount=amount,
                description=None
        )
        
        return {"message": "Pot transfer completed", "transaction_id": transaction.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/external", status_code=201)
def external_payment(data: ExternalPaymentIn, db: Session = Depends(get_db)):
    service = TransactionService(db)
    account_service = AccountService(db)
    
    try:
        # Verify accounts
        internal_acc = account_service.get(data.internal_account_id)
        external_acc = account_service.get(data.external_account_id)
        
        if not internal_acc:
            raise HTTPException(status_code=404, detail="Internal account not found")
        if not external_acc or not external_acc.is_external:
            raise HTTPException(status_code=404, detail="External account not found")

        amount = data.amount
        if data.direction == "out":
            from_id = data.internal_account_id
            to_id = data.external_account_id
        else:
            from_id = data.external_account_id
            to_id = data.internal_account_id

        transaction = service.create_transfer(
            amount=amount,
            from_account_id=from_id,
            to_account_id=to_id,
            description=data.note
        )
        
        account_service.transfer(
            from_id=from_id,
            to_id=to_id,
            amount=amount,
            description=data.note
        )
        
        return {"message": "External payment completed", "transaction_id": transaction.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    service = TransactionService(db)
    transaction = service.get(transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction

@router.get("/account/{account_id}")
def get_account_transactions(
    account_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: Session = Depends(get_db)
):
    service = TransactionService(db)
    try:
        transactions = service.get_account_transactions(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date
        )
        return transactions
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
