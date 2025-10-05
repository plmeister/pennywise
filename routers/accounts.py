from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from database import get_db
from modules.accounts.service import AccountService
from schemas.accounts import AccountCreate, AccountOut, PotCreate, PotOut

router = APIRouter(prefix="/accounts", tags=["accounts"])

DB_DEP: Session = Depends(get_db)


@router.post("/", response_model=AccountOut)
def create_account(account: AccountCreate, db: Session = DB_DEP):
    service = AccountService(db)
    try:
        return service.create_account(
            name=account.name,
            account_type=account.account_type,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = DB_DEP):
    service = AccountService(db)
    try:
        account = service.get(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        return account
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[AccountOut])
def get_accounts(db: Session = DB_DEP):
    service = AccountService(db)
    try:
        return service.get_all()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfer/")
def transfer_money(
    from_id: int,
    to_id: int,
    amount: Decimal,
    description: str | None = None,
    db: Session = DB_DEP,
):
    service = AccountService(db)
    try:
        _ = service.transfer(
            from_id=from_id, to_id=to_id, amount=amount, description=description
        )
        return {"message": "Transfer successful"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{account_id}/pots", response_model=PotOut)
def create_pot(account_id: int, pot: PotCreate, db: Session = DB_DEP):
    service = AccountService(db)
    account = service.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        pot_data = pot.model_dump()
        pot_data["account_id"] = account_id
        return service.create_pot(
            account_id, pot.name, pot.target_amount, pot.initial_amount
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
