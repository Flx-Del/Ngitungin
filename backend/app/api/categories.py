from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.db.session import get_db
from app.models import Business, Category


router = APIRouter(prefix="/api/categories", tags=["Kategori"])


class CategoryInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(pattern="^(product|expense)$")


@router.get("")
def list_categories(type: str | None = None, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    query = db.query(Category).filter(Category.business_id == business.id, Category.is_active.is_(True))
    if type:
        if type not in {"product", "expense"}:
            raise HTTPException(status_code=422, detail="Jenis kategori tidak dikenal.")
        query = query.filter(Category.type == type)
    return query.order_by(Category.name).all()


@router.post("", status_code=201)
def create_category(payload: CategoryInput, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Nama kategori wajib diisi.")
    if db.query(Category.id).filter(
        Category.business_id == business.id, Category.type == payload.type, Category.name.ilike(name)
    ).first():
        raise HTTPException(status_code=409, detail="Kategori dengan nama tersebut sudah ada.")
    category = Category(business_id=business.id, name=name, type=payload.type)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
