from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped
from database import Base


class Category(Base):
    __tablename__: str = "categories"

    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True
    )

    parent: Mapped["Category"] = relationship(
        "Category", remote_side=[Base.id], backref="children"
    )
