from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.scheduled_transactions import ScheduledTransaction
from schemas.scheduled_transactions import ScheduledTransactionCreate, ScheduledTransactionRead

router = APIRouter(prefix="/scheduled", tags=["Scheduled Transactions"])

@router.post("/", response_model=ScheduledTransactionRead)
def create_scheduled_txn(txn: ScheduledTransactionCreate, db: Session = Depends(get_db)):
    db_txn = ScheduledTransaction(**txn.dict())
    db.add(db_txn)
    db.commit()
    db.refresh(db_txn)
    return db_txn

@router.get("/", response_model=list[ScheduledTransactionRead])
def list_scheduled_txns(db: Session = Depends(get_db)):
    return db.query(ScheduledTransaction).all()

@router.get("/{txn_id}", response_model=ScheduledTransactionRead)
def get_scheduled_txn(txn_id: int, db: Session = Depends(get_db)):
    txn = db.query(ScheduledTransaction).get(txn_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Scheduled transaction not found")
    return txn
