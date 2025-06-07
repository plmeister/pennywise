from http.client import HTTPException
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models.accounts import Account, Pot
from schemas.accounts import AccountCreate, AccountOut, PotCreate, PotOut

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.post("/", response_model=AccountOut)
def create_account(account: AccountCreate, db: Session = Depends(get_db)):
    db_account = Account(**account.dict())
    db.add(db_account)
    db.commit()
    db.refresh(db_account)
    return db_account

@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return db_account

@router.get("/", response_model=list[AccountOut])
def get_accounts(db: Session = Depends(get_db)):
    accounts = db.query(Account).options(joinedload(Account.pots)).all()
    return accounts

@router.post("/{account_id}/pots", response_model=PotOut)
def create_pot(account_id: int, pot: PotCreate, db: Session = Depends(get_db)):
    db_account = db.query(Account).filter(Account.id == account_id).first()
    if db_account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    db_pot = Pot(**pot.dict())
    db.add(db_pot)
    db.commit()
    db.refresh(db_pot)
    return db_pot