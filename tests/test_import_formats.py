import pytest
from modules.imports.formats import ImportFormatService
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()

def test_list_formats(db_session):
    service = ImportFormatService(db_session)
    formats = service.list_formats()
    assert isinstance(formats, list)
