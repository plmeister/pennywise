from sqlalchemy.orm import Session
from typing import Generic, TypeVar

from database import Base


ModelType = TypeVar("ModelType")

class BaseService(Generic[ModelType]):
    model: type[ModelType]
    db: Session

    def __init__(self, model: type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: int) -> ModelType | None:
        return self.db.query(self.model).filter(Base.id == id).first()

    def get_all(self) -> list[ModelType]:
        return self.db.query(self.model).all()

    def update(self, id: int, data: dict) -> ModelType | None:
        instance = self.get(id)
        if instance:
            for key, value in data.items():
                setattr(instance, key, value)
            self.db.commit()
            self.db.refresh(instance)
        return instance

    def delete(self, id: int) -> bool:
        instance = self.get(id)
        if instance:
            self.db.delete(instance)
            self.db.commit()
            return True
        return False
