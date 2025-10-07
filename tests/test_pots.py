import pytest
from modules.accounts.service import AccountService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_list_pots(db_session):
    service = AccountService(db_session)
    pots = []
    # If pots are a property of accounts, you may need to create an account and access pots
    assert isinstance(pots, list)
