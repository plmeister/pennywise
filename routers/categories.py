from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Category as CategoryModel
from schemas import category as schemas

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.post("/", response_model=schemas.CategoryOut)
def create_category(cat: schemas.CategoryCreate, db: Session = Depends(get_db)):
    db_cat = CategoryModel(**cat.dict())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.get("/", response_model=List[schemas.CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    cats = db.query(CategoryModel).all()
    # Optionally: build a tree from the flat list here
    return cats

@router.put("/{cat_id}", response_model=schemas.CategoryOut)
def update_category(cat_id: int, update: schemas.CategoryUpdate, db: Session = Depends(get_db)):
    cat = db.query(CategoryModel).get(cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    for key, value in update.dict(exclude_unset=True).items():
        setattr(cat, key, value)
    db.commit()
    db.refresh(cat)
    return cat

@router.delete("/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db)):
    cat = db.query(CategoryModel).get(cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    db.delete(cat)
    db.commit()
    return {"ok": True}
