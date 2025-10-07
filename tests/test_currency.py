import pytest
from modules.currencies.service import CurrencyService
from models.accounts import CurrencyType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_list_currencies(db_session):
    service = CurrencyService(db_session)
    currencies = service.list_currencies()
    assert isinstance(currencies, list)
