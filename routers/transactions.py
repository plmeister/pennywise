from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from database import get_db
from models.accounts import Account, Pot
from models.transactions import Transaction, TransactionLeg
from schemas.transactions import ExternalPaymentIn, PotTransferIn, TransferIn

router = APIRouter(prefix="/transactions", tags=["transactions"])

# --- Helpers ---

def verify_account(db: Session, account_id: int):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=403, detail="Account not found")
    return account

def verify_pot(db: Session, pot_id: int):
    pot = db.query(Pot).filter(Pot.id == pot_id).first()
    if not pot:
        raise HTTPException(status_code=403, detail="Pot not found")
    return pot

def verify_external_account(db: Session, external_account_id: int):
    external = db.query(Account).filter(Account.id == external_account_id, Account.is_external==True).first()
    if not external:
        raise HTTPException(status_code=404, detail="External account not found")
    return external


# --- Endpoints ---


@router.post("/transfer", status_code=201)
def transfer_funds(data: TransferIn, db: Session = Depends(get_db)):
    # Verify ownership
    from_acc = verify_account(db, data.from_account_id)
    to_acc = verify_account(db, data.to_account_id)
    if from_acc.id == to_acc.id:
        raise HTTPException(400, "From and To accounts cannot be the same")

    # Create Transaction with 2 legs
    txn = Transaction(description=data.description, date=data.date)
    db.add(txn)
    db.flush()

    leg_out = TransactionLeg(
        transaction_id=txn.id,
        account_id=from_acc.id,
        debit=data.amount,
        credit=None
    )
    leg_in = TransactionLeg(
        transaction_id=txn.id,
        account_id=to_acc.id,
        debit=None,
        credit=data.amount
    )

    db.add_all([leg_out, leg_in])

    from_acc.balance -= data.amount
    to_acc.balance += data.amount
    db.add(from_acc)
    db.add(to_acc)

    db.commit()
    return {"message": "Transfer completed"}


@router.post("/pot-transfer", status_code=201)
def pot_transfer(data: PotTransferIn, db: Session = Depends(get_db)):
    # Verify ownership
    account = verify_account(db, data.account_id)
    pot = verify_pot(db, data.pot_id)

    if pot.account_id != account.id:
        raise HTTPException(400, "Pot does not belong to specified account")

    txn = Transaction(note=f"Pot transfer {data.direction}")
    db.add(txn)
    db.flush()

    if data.direction == "to_pot":
        leg_account = TransactionLeg(
            transaction_id=txn.id,
            account_id=account.id,
            amount=-data.amount
        )
        leg_pot = TransactionLeg(
            transaction_id=txn.id,
            account_id=pot.id,
            amount=data.amount
        )
    else:  # from_pot
        leg_account = TransactionLeg(
            transaction_id=txn.id,
            account_id=account.id,
            amount=data.amount
        )
        leg_pot = TransactionLeg(
            transaction_id=txn.id,
            account_id=pot.id,
            amount=-data.amount
        )

    db.add_all([leg_account, leg_pot])
    db.commit()
    return {"message": "Pot transfer completed"}


@router.post("/external", status_code=201)
def external_payment(data: ExternalPaymentIn, db: Session = Depends(get_db)):
    internal_acc = verify_account(db, data.internal_account_id)
    external_acc = verify_external_account(db, data.external_account_id)

    txn = Transaction(note=data.note)
    db.add(txn)
    db.flush()

    if data.direction == "out":
        # money moves from internal account to external account
        leg_internal = TransactionLeg(
            transaction_id=txn.id,
            account_id=internal_acc.id,
            debit=data.amount,
            credit=None
        )
        leg_external = TransactionLeg(
            transaction_id=txn.id,
            account_id=external_acc.id,
            debit=None,
            credit=data.amount
        )
    else:
        # money moves from external to internal
        leg_internal = TransactionLeg(
            transaction_id=txn.id,
            account_id=internal_acc.id,
            credit=data.amount,
            debit=None
        )
        leg_external = TransactionLeg(
            transaction_id=txn.id,
            account_id=external_acc.id,
            credit=None,
            debit=data.amount
        )

    db.add_all([leg_internal, leg_external])
    db.commit()
    return {"message": "External payment recorded"}
