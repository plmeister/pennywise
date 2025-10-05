from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column, Mapped
from database import Base


class User(Base):
    __tablename__: str = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String)
