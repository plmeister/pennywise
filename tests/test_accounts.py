import pytest
from database import Base
from modules.accounts.service import AccountService
from models.accounts import AccountType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_create_account(db_session):
    service = AccountService(db_session)
    account = service.create_account(
        name="Test Account",
        account_type=AccountType.current,
        currency_id=1,
        )
    assert account.name == "Test Account"
    assert account.type == AccountType.current.value
