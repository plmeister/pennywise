from modules.common.base_service import BaseService
from models.categories import Category
from sqlalchemy.orm import Session
from typing import TypedDict


class CategoryNode(TypedDict):
    id: int
    name: str
    children: list["CategoryNode"]


class CategoryService(BaseService[Category]):
    def __init__(self, db: Session):
        super().__init__(Category, db)

    def create_category(self, name: str, parent_id: int | None = None) -> Category:
        return Category(**{"name": name, "parent_id": parent_id})

    def get_children(self, category_id: int) -> list[Category]:
        return self.db.query(Category).filter(Category.parent_id == category_id).all()

    def get_full_hierarchy(self) -> list[CategoryNode]:
        """Returns the full category hierarchy"""
        categories = self.db.query(Category).filter(Category.parent_id.is_(None)).all()
        return [self._build_hierarchy(cat) for cat in categories]

    def _build_hierarchy(self, category: Category) -> CategoryNode:
        """Recursively builds category hierarchy"""
        result: CategoryNode = {
            "id": category.id,
            "name": category.name,
            "children": [],
        }

        children = self.get_children(category.id)
        if children:
            result["children"] = [self._build_hierarchy(child) for child in children]

        return result
