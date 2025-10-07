from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker, DeclarativeBase, mapped_column, Mapped


SQLALCHEMY_DATABASE_URL = "sqlite:///./budget.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)



from sqlalchemy import Column, Integer

class BaseModel:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

class Base(DeclarativeBase, BaseModel):
    __abstract__ = True


# Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import all models so they are registered with SQLAlchemy
    # import models.accounts
    # import models.categories
    # import models.transactions
    # import models.scheduled_transactions
    # import models.scenarios
    # import models.users

    Base.metadata.create_all(bind=engine)
