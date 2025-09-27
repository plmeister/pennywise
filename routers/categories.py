from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from modules.categories.service import CategoryService
from schemas import categories as schemas

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.post("/", response_model=schemas.CategoryOut)
def create_category(cat: schemas.CategoryCreate, db: Session = Depends(get_db)):
    service = CategoryService(db)
    try:
        return service.create_category(name=cat.name, parent_id=cat.parent_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[schemas.CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    service = CategoryService(db)
    return service.get_all()

@router.get("/hierarchy")
def get_category_hierarchy(db: Session = Depends(get_db)):
    service = CategoryService(db)
    return service.get_full_hierarchy()

@router.get("/{category_id}", response_model=schemas.CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    service = CategoryService(db)
    category = service.get(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@router.get("/{category_id}/children", response_model=List[schemas.CategoryOut])
def get_category_children(category_id: int, db: Session = Depends(get_db)):
    service = CategoryService(db)
    return service.get_children(category_id)

@router.put("/{category_id}", response_model=schemas.CategoryOut)
def update_category(
    category_id: int, 
    update: schemas.CategoryUpdate, 
    db: Session = Depends(get_db)
):
    service = CategoryService(db)
    try:
        category = service.update(category_id, update.dict(exclude_unset=True))
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    service = CategoryService(db)
    if not service.delete(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted successfully"}
