from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.db.session import get_db
from app.models import Business, Category, Product, StockMovement
from app.schemas import ProductCreate, ProductResponse, ProductUpdate, StockAdjustment


router = APIRouter(prefix="/api/products", tags=["Produk"])


def owned_product(db: Session, business_id: int, product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id, Product.business_id == business_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    return product


def validate_category(db: Session, business_id: int, category_id: int | None) -> None:
    if category_id is not None and not db.query(Category.id).filter(
        Category.id == category_id, Category.business_id == business_id, Category.type == "product", Category.is_active.is_(True)
    ).first():
        raise HTTPException(status_code=422, detail="Kategori produk tidak ditemukan.")


@router.get("", response_model=list[ProductResponse])
def list_products(
    search: str = Query(default="", max_length=120),
    active: bool | None = None,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    query = db.query(Product).filter(Product.business_id == business.id)
    if active is not None:
        query = query.filter(Product.is_active.is_(active))
    if search.strip():
        query = query.filter(func.lower(Product.name).contains(search.strip().lower()))
    return query.order_by(Product.name).all()


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    validate_category(db, business.id, payload.category_id)
    if not payload.name.strip() or not payload.unit_label.strip():
        raise HTTPException(status_code=422, detail="Nama produk dan satuan wajib diisi.")
    if payload.sku and db.query(Product.id).filter(Product.business_id == business.id, func.lower(Product.sku) == payload.sku.lower()).first():
        raise HTTPException(status_code=409, detail="Kode SKU sudah digunakan.")
    values = payload.model_dump()
    values["name"] = payload.name.strip()
    values["unit_label"] = payload.unit_label.strip()
    values["sku"] = payload.sku.strip() or None if payload.sku else None
    product = Product(business_id=business.id, **values)
    db.add(product)
    db.flush()
    if product.stock > 0:
        db.add(StockMovement(
            business_id=business.id, product_id=product.id, movement_type="opening",
            quantity_change=product.stock, note="Stok awal",
        ))
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    product = owned_product(db, business.id, product_id)
    data = payload.model_dump(exclude_unset=True)
    for key in ("name", "unit_label", "selling_price", "cost_price", "minimum_stock", "is_active"):
        if key in data and data[key] is None:
            raise HTTPException(status_code=422, detail="Kolom wajib produk tidak boleh kosong.")
    if any(key in data and not data[key].strip() for key in ("name", "unit_label")):
        raise HTTPException(status_code=422, detail="Nama produk dan satuan wajib diisi.")
    if "category_id" in data:
        validate_category(db, business.id, data["category_id"])
    if data.get("sku") and db.query(Product.id).filter(
        Product.business_id == business.id, func.lower(Product.sku) == data["sku"].lower(), Product.id != product.id
    ).first():
        raise HTTPException(status_code=409, detail="Kode SKU sudah digunakan.")
    for key, value in data.items():
        if key in {"name", "unit_label", "sku"} and isinstance(value, str):
            value = value.strip()
            if key == "sku" and not value:
                value = None
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.post("/{product_id}/stock-adjustments", response_model=ProductResponse)
def adjust_stock(product_id: int, payload: StockAdjustment, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    product = db.query(Product).filter(Product.id == product_id, Product.business_id == business.id).with_for_update().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produk tidak ditemukan.")
    new_stock = product.stock + payload.quantity_change
    if new_stock < 0:
        raise HTTPException(status_code=422, detail="Stok tidak cukup untuk penyesuaian ini.")
    product.stock = new_stock
    db.add(StockMovement(
        business_id=business.id, product_id=product.id, movement_type="adjustment",
        quantity_change=payload.quantity_change, note=payload.note,
    ))
    db.commit()
    db.refresh(product)
    return product
