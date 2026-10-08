from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.db.session import get_db
from app.models import Business, Category, Expense
from app.schemas import ExpenseCreate, ExpenseResponse, ExpenseUpdate


router = APIRouter(prefix="/api/expenses", tags=["Pengeluaran"])


@router.get("", response_model=list[ExpenseResponse])
def list_expenses(start: date | None = None, end: date | None = None, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    query = db.query(Expense).filter(Expense.business_id == business.id)
    if start:
        query = query.filter(Expense.expense_date >= start)
    if end:
        query = query.filter(Expense.expense_date <= end)
    return query.order_by(Expense.expense_date.desc(), Expense.id.desc()).all()


@router.post("", response_model=ExpenseResponse, status_code=201)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    if payload.category_id is not None and not db.query(Category.id).filter(
        Category.id == payload.category_id, Category.business_id == business.id,
        Category.type == "expense", Category.is_active.is_(True),
    ).first():
        raise HTTPException(status_code=422, detail="Kategori pengeluaran tidak ditemukan.")
    expense = Expense(business_id=business.id, **payload.model_dump())
    if not payload.description.strip():
        raise HTTPException(status_code=422, detail="Deskripsi pengeluaran wajib diisi.")
    expense.description = payload.description.strip()
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.patch("/{expense_id}", response_model=ExpenseResponse)
def update_expense(expense_id: int, payload: ExpenseUpdate, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.business_id == business.id).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Pengeluaran tidak ditemukan.")
    if expense.status != "posted":
        raise HTTPException(status_code=409, detail="Pengeluaran yang dibatalkan tidak dapat diedit.")
    data = payload.model_dump(exclude_unset=True)
    for key in ("expense_date", "amount", "description", "payment_method"):
        if key in data and data[key] is None:
            raise HTTPException(status_code=422, detail="Tanggal, nominal, deskripsi, dan metode pembayaran wajib diisi.")
    if "category_id" in data and data["category_id"] is not None and not db.query(Category.id).filter(
        Category.id == data["category_id"], Category.business_id == business.id,
        Category.type == "expense", Category.is_active.is_(True),
    ).first():
        raise HTTPException(status_code=422, detail="Kategori pengeluaran tidak ditemukan.")
    for key, value in data.items():
        setattr(expense, key, value.strip() if key == "description" and isinstance(value, str) else value)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=204)
def void_expense(expense_id: int, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    expense = db.query(Expense).filter(Expense.id == expense_id, Expense.business_id == business.id).first()
    if expense is None:
        raise HTTPException(status_code=404, detail="Pengeluaran tidak ditemukan.")
    if expense.status == "void":
        raise HTTPException(status_code=409, detail="Pengeluaran ini sudah dibatalkan.")
    expense.status = "void"
    db.commit()
