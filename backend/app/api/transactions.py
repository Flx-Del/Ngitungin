from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_business
from app.db.session import get_db
from app.models import Business, Product, StockMovement, Transaction, TransactionItem
from app.schemas import IncomeCreate, SaleCreate, TransactionResponse


router = APIRouter(prefix="/api/transactions", tags=["Transaksi"])
CENT = Decimal("0.01")


@router.get("", response_model=list[TransactionResponse])
def list_transactions(
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
    business: Business = Depends(get_current_business),
):
    query = db.query(Transaction).filter(Transaction.business_id == business.id)
    if start:
        query = query.filter(Transaction.transaction_date >= start)
    if end:
        query = query.filter(Transaction.transaction_date <= end)
    return query.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).all()


@router.post("/sales", response_model=TransactionResponse, status_code=201)
def create_sale(payload: SaleCreate, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    quantities: dict[int, Decimal] = {}
    for item in payload.items:
        quantities[item.product_id] = quantities.get(item.product_id, Decimal("0")) + item.quantity
    products = db.query(Product).filter(
        Product.business_id == business.id, Product.id.in_(quantities), Product.is_active.is_(True)
    ).with_for_update().all()
    by_id = {p.id: p for p in products}
    if len(by_id) != len(quantities):
        raise HTTPException(status_code=422, detail="Pastikan semua produk masih aktif dan milik usaha Anda.")
    for product_id, quantity in quantities.items():
        if by_id[product_id].stock < quantity:
            raise HTTPException(status_code=422, detail=f"Stok {by_id[product_id].name} tidak mencukupi.")

    item_subtotals = [
        (item, (by_id[item.product_id].selling_price * item.quantity).quantize(CENT, rounding=ROUND_HALF_UP))
        for item in payload.items
    ]
    subtotal = sum((amount for _, amount in item_subtotals), Decimal("0.00"))
    if payload.discount > subtotal:
        raise HTTPException(status_code=422, detail="Diskon tidak boleh lebih besar dari subtotal.")
    total = subtotal - payload.discount
    transaction = Transaction(
        business_id=business.id,
        transaction_number=f"J-{payload.transaction_date:%Y%m%d}-{uuid4().hex[:8].upper()}",
        type="sale", status="posted", transaction_date=payload.transaction_date,
        subtotal=subtotal, discount=payload.discount, total=total,
        payment_method=payload.payment_method, notes=payload.notes,
    )
    db.add(transaction)
    db.flush()
    for item, line_total in item_subtotals:
        product = by_id[item.product_id]
        db.add(TransactionItem(
            transaction_id=transaction.id, product_id=product.id,
            product_name_snapshot=product.name, sku_snapshot=product.sku,
            quantity=item.quantity, price=product.selling_price,
            cost_per_unit=product.cost_price, subtotal=line_total,
        ))
        product.stock -= item.quantity
        db.add(StockMovement(
            business_id=business.id, product_id=product.id, transaction_id=transaction.id,
            movement_type="sale", quantity_change=-item.quantity,
            note=f"Penjualan {transaction.transaction_number}",
        ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(transaction)
    return transaction


@router.post("/incomes", response_model=TransactionResponse, status_code=201)
def create_other_income(payload: IncomeCreate, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    transaction = Transaction(
        business_id=business.id,
        transaction_number=f"MSK-{payload.transaction_date:%Y%m%d}-{uuid4().hex[:8].upper()}",
        type="other_income", status="posted", transaction_date=payload.transaction_date,
        subtotal=payload.amount, discount=Decimal("0"), total=payload.amount,
        payment_method=payload.payment_method, description=payload.description.strip(), notes=payload.notes,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_sale(transaction_id: int, payload: SaleCreate, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id, Transaction.business_id == business.id,
        Transaction.type == "sale",
    ).with_for_update().first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaksi penjualan tidak ditemukan.")
    if transaction.status != "posted":
        raise HTTPException(status_code=409, detail="Transaksi yang dibatalkan tidak dapat diedit.")

    old_items = db.query(TransactionItem).filter(TransactionItem.transaction_id == transaction.id).all()
    old_quantities: dict[int, Decimal] = {}
    for item in old_items:
        if item.product_id is not None:
            old_quantities[item.product_id] = old_quantities.get(item.product_id, Decimal("0")) + item.quantity
    new_quantities: dict[int, Decimal] = {}
    for item in payload.items:
        new_quantities[item.product_id] = new_quantities.get(item.product_id, Decimal("0")) + item.quantity

    all_ids = set(old_quantities) | set(new_quantities)
    products = db.query(Product).filter(Product.business_id == business.id, Product.id.in_(all_ids)).with_for_update().all()
    by_id = {product.id: product for product in products}
    if not set(old_quantities).issubset(by_id) or not set(new_quantities).issubset(by_id):
        raise HTTPException(status_code=422, detail="Produk transaksi tidak ditemukan pada usaha Anda.")
    for product_id, quantity in new_quantities.items():
        product = by_id[product_id]
        available = product.stock + old_quantities.get(product_id, Decimal("0"))
        if not product.is_active or available < quantity:
            raise HTTPException(status_code=422, detail=f"Stok {product.name} tidak mencukupi.")

    line_totals = [
        (item, (by_id[item.product_id].selling_price * item.quantity).quantize(CENT, rounding=ROUND_HALF_UP))
        for item in payload.items
    ]
    subtotal = sum((amount for _, amount in line_totals), Decimal("0.00"))
    if payload.discount > subtotal:
        raise HTTPException(status_code=422, detail="Diskon tidak boleh lebih besar dari subtotal.")

    for item in old_items:
        if item.product_id in by_id:
            product = by_id[item.product_id]
            product.stock += item.quantity
            db.add(StockMovement(
                business_id=business.id, product_id=product.id, transaction_id=transaction.id,
                movement_type="reversal", quantity_change=item.quantity,
                note=f"Koreksi transaksi {transaction.transaction_number}",
            ))
        db.delete(item)
    db.flush()
    transaction.transaction_date = payload.transaction_date
    transaction.subtotal = subtotal
    transaction.discount = payload.discount
    transaction.total = subtotal - payload.discount
    transaction.payment_method = payload.payment_method
    transaction.notes = payload.notes
    for item, line_total in line_totals:
        product = by_id[item.product_id]
        product.stock -= item.quantity
        db.add(TransactionItem(
            transaction_id=transaction.id, product_id=product.id,
            product_name_snapshot=product.name, sku_snapshot=product.sku,
            quantity=item.quantity, price=product.selling_price,
            cost_per_unit=product.cost_price, subtotal=line_total,
        ))
        db.add(StockMovement(
            business_id=business.id, product_id=product.id, transaction_id=transaction.id,
            movement_type="sale", quantity_change=-item.quantity,
            note=f"Perubahan transaksi {transaction.transaction_number}",
        ))
    db.commit()
    db.refresh(transaction)
    return transaction


@router.post("/{transaction_id}/void", response_model=TransactionResponse)
def void_sale(transaction_id: int, db: Session = Depends(get_db), business: Business = Depends(get_current_business)):
    transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id, Transaction.business_id == business.id
    ).with_for_update().first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan.")
    if transaction.status == "void":
        raise HTTPException(status_code=409, detail="Transaksi ini sudah dibatalkan.")
    items = db.query(TransactionItem).filter(TransactionItem.transaction_id == transaction.id).all()
    for item in items:
        if item.product_id is None:
            continue
        product = db.query(Product).filter(Product.id == item.product_id, Product.business_id == business.id).with_for_update().first()
        if product:
            product.stock += item.quantity
            db.add(StockMovement(
                business_id=business.id, product_id=product.id, transaction_id=transaction.id,
                movement_type="reversal", quantity_change=item.quantity,
                note=f"Pembatalan {transaction.transaction_number}",
            ))
    transaction.status = "void"
    db.commit()
    db.refresh(transaction)
    return transaction
