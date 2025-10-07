import pytest
from modules.transactions.service import TransactionService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_list_transactions(db_session):
    service = TransactionService(db_session)
    transactions = service.get_all()
    assert isinstance(transactions, list)
